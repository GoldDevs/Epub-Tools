import curses
import json
import time
from typing import List, Dict, Tuple, Optional
from ..ui.material_components import MaterialCard, MaterialButton, MaterialList, MaterialTextField, MaterialChip, MaterialProgress
from ..ui.layout_manager import LayoutRegion
from .base_screen import BaseScreen
from ..core.replace_engine import ReplaceEngine, ReplacementStats

class BatchOperationsScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager)
        self.name = "batch_ops"
        self.operations = []
        self.current_operation = None
        self.templates = []
        self.active_template = None
        self.progress = 0
        self.total_operations = 0
        self.current_file = ""
        self.is_processing = False
        self.last_template_load = 0
        self.template_dir = Path("templates")
        
    def on_create(self, data=None):
        """Initialize batch operations screen"""
        self.load_templates()
        self.setup_components()
        self.setup_input()
        
    def setup_components(self):
        """Create UI components"""
        main_region = self.layout.get_region("main")
        if not main_region:
            return
            
        # Create templates card
        templates_card = MaterialCard(
            self.theme, LayoutRegion("templates", 5, 3, main_region.width - 10, 8),
            "Operation Templates"
        )
        
        # Create template list
        self.template_list = MaterialList(
            self.theme, LayoutRegion("template_list", 0, 0, main_region.width - 15, 5),
            [t["name"] for t in self.templates], self.on_template_select
        )
        templates_card.add_component(self.template_list)
        
        # Template actions
        templates_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_load", 0, 6, 12, 1),
            "Load", self.load_selected_template
        ))
        templates_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_save", 15, 6, 12, 1),
            "Save", self.save_as_template
        ))
        templates_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_delete", 30, 6, 12, 1),
            "Delete", self.delete_template
        ))
        
        self.add_component(templates_card)
        
        # Create operations card
        self.operations_card = MaterialCard(
            self.theme, LayoutRegion("operations", 5, 12, main_region.width - 10, 10),
            "Batch Operations"
        )
        
        # Operations list
        self.operations_list = MaterialList(
            self.theme, LayoutRegion("ops_list", 0, 0, main_region.width - 15, 8),
            self.get_operation_display(), self.on_operation_select
        )
        self.operations_card.add_component(self.operations_list)
        
        # Operation actions
        self.operations_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_add", 0, 9, 12, 1),
            "Add", self.add_operation
        ))
        self.operations_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_edit", 15, 9, 12, 1),
            "Edit", self.edit_operation
        ))
        self.operations_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_delete", 30, 9, 12, 1),
            "Remove", self.remove_operation
        ))
        
        self.add_component(self.operations_card)
        
        # Create progress area
        self.progress_card = MaterialCard(
            self.theme, LayoutRegion("progress", 5, 23, main_region.width - 10, 8),
            "Progress"
        )
        self.add_component(self.progress_card)
        
        # Progress bar
        self.progress_bar = MaterialProgress(
            self.theme, LayoutRegion("progress_bar", 5, 2, main_region.width - 20, 1),
            0, 100
        )
        self.progress_card.add_component(self.progress_bar)
        
        # Status text
        self.status_chip = MaterialChip(
            self.theme, LayoutRegion("status", 5, 4, main_region.width - 20, 1),
            "Ready to process"
        )
        self.progress_card.add_component(self.status_chip)
        
        # Action buttons
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_validate", 5, 32, 15, 1),
            "Validate", self.validate_operations
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_run", 25, 32, 15, 1),
            "Run Batch", self.run_batch
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_clear", 45, 32, 15, 1),
            "Clear All", self.clear_operations
        ))
        
    def setup_input(self):
        """Set up input handlers"""
        self.input_handler.register_key(ord('a'), self.add_operation)
        self.input_handler.register_key(ord('e'), self.edit_operation)
        self.input_handler.register_key(ord('d'), self.remove_operation)
        self.input_handler.register_key(ord('v'), self.validate_operations)
        self.input_handler.register_key(ord('r'), self.run_batch)
        self.input_handler.register_key(ord('c'), self.clear_operations)
        
        # Register swipe gestures
        self.input_handler.enable_swipe_navigation(
            left_action=self.screen_manager.go_back,
            right_action=self.run_batch,
            up_action=self.scroll_up,
            down_action=self.scroll_down
        )
        
    def load_templates(self):
        """Load operation templates"""
        self.template_dir.mkdir(exist_ok=True)
        self.templates = []
        
        for template_file in self.template_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template = json.load(f)
                    template["file"] = template_file.name
                    self.templates.append(template)
            except json.JSONDecodeError:
                continue
                
        # Sort by name
        self.templates.sort(key=lambda t: t["name"])
        
    def on_template_select(self, index, item):
        """Handle template selection"""
        if 0 <= index < len(self.templates):
            self.active_template = self.templates[index]
            
    def load_selected_template(self):
        """Load selected template"""
        if not self.active_template:
            self.status_chip.text = "No template selected"
            return
            
        try:
            template_file = self.template_dir / self.active_template["file"]
            with open(template_file, 'r') as f:
                self.operations = json.load(f)
                self.status_chip.text = f"Loaded template: {self.active_template['name']}"
                self.update_operations_list()
        except (OSError, json.JSONDecodeError):
            self.status_chip.text = "Error loading template"
            
    def save_as_template(self):
        """Save current operations as template"""
        if not self.operations:
            self.status_chip.text = "No operations to save"
            return
            
        # Show input dialog for template name
        self.screen_manager.show_input_dialog(
            "Template name:",
            self.save_template_with_name
        )
        
    def save_template_with_name(self, name):
        """Save template with given name"""
        if not name:
            self.status_chip.text = "Template name required"
            return
            
        # Create safe filename
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-")
        if not safe_name:
            safe_name = "template"
            
        filename = f"{safe_name}.json"
        template_path = self.template_dir / filename
        
        try:
            with open(template_path, 'w') as f:
                json.dump(self.operations, f, indent=2)
                
            # Add to templates
            self.templates.append({
                "name": name,
                "file": filename
            })
            self.template_list.items = [t["name"] for t in self.templates]
            self.status_chip.text = f"Template saved: {name}"
        except OSError:
            self.status_chip.text = "Error saving template"
            
    def delete_template(self):
        """Delete selected template"""
        if not self.active_template:
            self.status_chip.text = "No template selected"
            return
            
        template_file = self.template_dir / self.active_template["file"]
        if template_file.exists():
            try:
                template_file.unlink()
                self.templates = [t for t in self.templates if t["file"] != self.active_template["file"]]
                self.template_list.items = [t["name"] for t in self.templates]
                self.active_template = None
                self.status_chip.text = "Template deleted"
            except OSError:
                self.status_chip.text = "Error deleting template"
                
    def get_operation_display(self) -> List[str]:
        """Format operations for display"""
        display = []
        for i, op in enumerate(self.operations):
            find = op.get("find", "")
            replace = op.get("replace", "")
            display.append(f"{i+1}. '{find}' → '{replace}'")
        return display
        
    def update_operations_list(self):
        """Update operations list display"""
        if self.operations_list:
            self.operations_list.items = self.get_operation_display()
            
    def on_operation_select(self, index, item):
        """Handle operation selection"""
        if 0 <= index < len(self.operations):
            self.current_operation = self.operations[index]
            
    def add_operation(self):
        """Add a new operation"""
        self.screen_manager.show_dialog(
            OperationDialog(
                self.stdscr, self.theme, self.layout, self.input_handler, self,
                None, self.add_operation_callback
            )
        )
        
    def add_operation_callback(self, op):
        """Callback for adding operation"""
        if op:
            self.operations.append(op)
            self.update_operations_list()
            
    def edit_operation(self):
        """Edit selected operation"""
        if not self.current_operation:
            self.status_chip.text = "No operation selected"
            return
            
        self.screen_manager.show_dialog(
            OperationDialog(
                self.stdscr, self.theme, self.layout, self.input_handler, self,
                self.current_operation, self.edit_operation_callback
            )
        )
        
    def edit_operation_callback(self, op):
        """Callback for editing operation"""
        if op and self.current_operation in self.operations:
            index = self.operations.index(self.current_operation)
            self.operations[index] = op
            self.current_operation = op
            self.update_operations_list()
            
    def remove_operation(self):
        """Remove selected operation"""
        if not self.current_operation:
            self.status_chip.text = "No operation selected"
            return
            
        if self.current_operation in self.operations:
            self.operations.remove(self.current_operation)
            self.current_operation = None
            self.update_operations_list()
            
    def clear_operations(self):
        """Clear all operations"""
        self.operations = []
        self.current_operation = None
        self.update_operations_list()
        
    def validate_operations(self):
        """Validate batch operations"""
        if not self.operations:
            self.status_chip.text = "No operations to validate"
            return
            
        errors = []
        for i, op in enumerate(self.operations):
            find = op.get("find", "")
            if not find:
                errors.append(f"Operation {i+1}: Missing find pattern")
                
            # Check regex validity
            if op.get("regex", False):
                try:
                    re.compile(find)
                except re.error as e:
                    errors.append(f"Operation {i+1}: Invalid regex - {str(e)}")
                    
        if errors:
            error_text = "\n".join(errors[:3])  # Show first 3 errors
            if len(errors) > 3:
                error_text += f"\n... and {len(errors)-3} more"
            self.status_chip.text = error_text
        else:
            self.status_chip.text = "All operations are valid"
            
    def run_batch(self):
        """Run batch operations"""
        if not self.operations:
            self.status_chip.text = "No operations to run"
            return
            
        if self.is_processing:
            self.status_chip.text = "Batch already running"
            return
            
        # Start processing
        self.is_processing = True
        self.progress = 0
        self.total_operations = len(self.operations)
        self.progress_bar.value = 0
        self.status_chip.text = "Starting batch processing..."
        
        # Process operations
        for i, op in enumerate(self.operations):
            self.progress = (i + 1) / self.total_operations * 100
            self.progress_bar.value = int(self.progress)
            self.status_chip.text = f"Processing operation {i+1}/{self.total_operations}: '{op['find']}' → '{op['replace']}'"
            self.draw()
            
            # Perform replacement
            replace_engine = ReplaceEngine(self.screen_manager.app.editor.content_manager)
            stats = replace_engine.pattern_replace(
                op["find"],
                op["replace"],
                op.get("case_sensitive", False),
                op.get("regex", False),
                op.get("whole_words", False)
            )
            
            # Update status
            self.status_chip.text = f"Replaced {stats.total_replacements} in {stats.files_modified} files"
            
            # Small delay to show progress
            time.sleep(0.1)
            
        # Final update
        self.is_processing = False
        self.screen_manager.app.editor.modifications_made = True
        self.status_chip.text = f"Batch complete! {self.total_operations} operations processed"
        self.progress_bar.value = 100
        
    def draw(self):
        """Draw batch operations screen"""
        super().draw()
        
        # Draw header
        header = "Batch Operations"
        self.stdscr.addstr(1, (curses.COLS - len(header)) // 2, header, 
                          self.theme.get_highlight_color(self.theme.PRIMARY))
        
        # Draw stats
        stats = f"Operations: {len(self.operations)} | Templates: {len(self.templates)}"
        self.stdscr.addstr(2, (curses.COLS - len(stats)) // 2, stats,
                          self.theme.get_color(self.theme.TEXT_SECONDARY))
        
        # Draw help
        help_text = "A: Add  E: Edit  D: Delete  V: Validate  R: Run  C: Clear"
        self.stdscr.addstr(curses.LINES - 2, (curses.COLS - len(help_text)) // 2, help_text,
                          self.theme.get_color(self.theme.TEXT_SECONDARY))
        
    def get_state(self):
        """Get current screen state"""
        return {
            "operations": self.operations,
            "templates": self.templates,
            "active_template": self.active_template
        }
        
    def set_state(self, state):
        """Restore screen state"""
        self.operations = state.get("operations", [])
        self.templates = state.get("templates", [])
        self.active_template = state.get("active_template", None)
        
        self.update_operations_list()
        if self.template_list:
            self.template_list.items = [t["name"] for t in self.templates]

class OperationDialog(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, parent_screen, operation, callback):
        super().__init__(stdscr, theme, layout, input_handler, None)
        self.parent_screen = parent_screen
        self.operation = operation or {}
        self.callback = callback
        self.name = "operation_dialog"
        self.setup_components()
        
    def setup_components(self):
        """Create dialog components"""
        # Create a centered dialog region
        width = 60
        height = 18
        x = (curses.COLS - width) // 2
        y = (curses.LINES - height) // 3
        
        self.dialog_region = LayoutRegion("dialog", x, y, width, height)
        
        # Create dialog card
        title = "Edit Operation" if self.operation else "Add Operation"
        self.dialog_card = MaterialCard(
            self.theme, LayoutRegion("dialog_card", 0, 0, width, height),
            title
        )
        
        # Find pattern field
        self.find_field = MaterialTextField(
            self.theme, LayoutRegion("find", 5, 3, width - 10, 3),
            "Find pattern:", self.operation.get("find", ""), None
        )
        self.dialog_card.add_component(self.find_field)
        
        # Replace pattern field
        self.replace_field = MaterialTextField(
            self.theme, LayoutRegion("replace", 5, 6, width - 10, 3),
            "Replace with:", self.operation.get("replace", ""), None
        )
        self.dialog_card.add_component(self.replace_field)
        
        # Options
        options_y = 9
        self.case_chip = MaterialChip(
            self.theme, LayoutRegion("case", 5, options_y, 20, 1), 
            "Case Sensitive", self.toggle_case
        )
        self.case_chip.selected = self.operation.get("case_sensitive", False)
        self.dialog_card.add_component(self.case_chip)
        
        self.regex_chip = MaterialChip(
            self.theme, LayoutRegion("regex", 27, options_y, 10, 1), 
            "Regex", self.toggle_regex
        )
        self.regex_chip.selected = self.operation.get("regex", False)
        self.dialog_card.add_component(self.regex_chip)
        
        self.words_chip = MaterialChip(
            self.theme, LayoutRegion("words", 39, options_y, 15, 1), 
            "Whole Words", self.toggle_whole_words
        )
        self.words_chip.selected = self.operation.get("whole_words", False)
        self.dialog_card.add_component(self.words_chip)
        
        # Buttons
        buttons_y = options_y + 3
        self.dialog_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_ok", 10, buttons_y, 12, 1),
            "OK", self.save_operation
        ))
        self.dialog_card.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_cancel", 38, buttons_y, 12, 1),
            "Cancel", self.close_dialog
        ))
        
        # Focus the first field
        self.find_field.focused = True
        
    def toggle_case(self):
        self.case_chip.selected = not self.case_chip.selected
        
    def toggle_regex(self):
        self.regex_chip.selected = not self.regex_chip.selected
        
    def toggle_whole_words(self):
        self.words_chip.selected = not self.words_chip.selected
        
    def save_operation(self):
        """Save operation and close dialog"""
        operation = {
            "find": self.find_field.value,
            "replace": self.replace_field.value,
            "case_sensitive": self.case_chip.selected,
            "regex": self.regex_chip.selected,
            "whole_words": self.words_chip.selected
        }
        
        if self.callback:
            self.callback(operation)
            
        self.close_dialog()
        
    def close_dialog(self):
        """Close this dialog"""
        if self.parent_screen:
            self.parent_screen.screen_manager.close_dialog()
            
    def draw(self):
        """Draw dialog screen"""
        # Clear background with transparency effect
        self.stdscr.attron(curses.A_DIM)
        self.parent_screen.draw()
        self.stdscr.attroff(curses.A_DIM)
        
        # Draw dialog
        self.dialog_card.region = self.dialog_region
        self.dialog_card.draw(self.stdscr)
        
    def handle_input(self):
        """Handle input for dialog"""
        key = self.stdscr.getch()
        
        if key == 27:  # ESC
            self.close_dialog()
        elif key == 9:  # Tab
            # Toggle focus between fields
            if self.find_field.focused:
                self.find_field.focused = False
                self.replace_field.focused = True
            elif self.replace_field.focused:
                self.replace_field.focused = False
                self.find_field.focused = True
        elif key == curses.KEY_ENTER or key == 10:
            self.save_operation()
        else:
            # Pass to focused component
            if self.find_field.focused:
                self.find_field.handle_input(key)
            elif self.replace_field.focused:
                self.replace_field.handle_input(key)