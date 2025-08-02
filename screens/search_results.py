import curses
import re
import time
from typing import List, Dict, Tuple, Optional
from ..ui.material_components import MaterialList, MaterialButton, MaterialCard, MaterialChip
from ..ui.layout_manager import LayoutRegion
from .base_screen import BaseScreen
from ..core.search_engine import SearchResult

class SearchResultsScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager)
        self.name = "search_results"
        self.results = []
        self.current_index = 0
        self.search_pattern = ""
        self.context_size = 3  # Lines of context to show
        self.file_filter = ""
        self.filtered_results = []
        self.last_scroll_time = 0
        self.scroll_delay = 0.2  # Seconds between scrolls
        self.preview_content = ""
        self.preview_file = ""
        
    def on_create(self, data=None):
        """Initialize search results screen"""
        if data and "search" in data:
            self.search_pattern = data["search"].get("pattern", "")
            
        editor = self.screen_manager.app.editor
        self.results = editor.search_results
        self.filtered_results = self.results[:]
        
        self.setup_components()
        self.setup_input()
        
    def on_resume(self, data=None):
        """Refresh when returning to this screen"""
        # Update results if new search was performed
        if data and "search" in data:
            self.search_pattern = data["search"].get("pattern", "")
            self.results = self.screen_manager.app.editor.search_results
            self.filtered_results = self.results[:]
            self.current_index = 0
            self.update_results_list()
            
    def setup_components(self):
        """Create UI components"""
        main_region = self.layout.get_region("main")
        if not main_region:
            return
            
        # Create filter field
        self.filter_field = MaterialTextField(
            self.theme, LayoutRegion("filter", 5, 2, main_region.width - 10, 3),
            "Filter files:", self.file_filter, self.on_filter_changed
        )
        self.add_component(self.filter_field)
        
        # Create results list
        list_height = main_region.height - 14
        self.results_list = MaterialList(
            self.theme, LayoutRegion("results", 5, 5, main_region.width - 10, list_height),
            self.get_display_results(), self.on_result_selected
        )
        self.add_component(self.results_list)
        
        # Create context preview card
        self.preview_card = MaterialCard(
            self.theme, LayoutRegion("preview", 5, list_height + 7, main_region.width - 10, 5),
            "Match Preview"
        )
        self.add_component(self.preview_card)
        
        # Create action buttons
        actions_y = list_height + 13
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_prev", 5, actions_y, 12, 1),
            "← Previous", self.prev_result
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_replace", 20, actions_y, 15, 1),
            "Replace", self.replace_current
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_replace_all", 38, actions_y, 18, 1),
            "Replace All", self.replace_all
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_next", 59, actions_y, 10, 1),
            "Next →", self.next_result
        ))
        
        # Update preview
        self.update_preview()
        
    def setup_input(self):
        """Set up input handlers"""
        self.input_handler.register_key(curses.KEY_UP, self.prev_result)
        self.input_handler.register_key(curses.KEY_DOWN, self.next_result)
        self.input_handler.register_key(curses.KEY_LEFT, self.prev_result)
        self.input_handler.register_key(curses.KEY_RIGHT, self.next_result)
        self.input_handler.register_key(ord('r'), self.replace_current)
        self.input_handler.register_key(ord('a'), self.replace_all)
        self.input_handler.register_key(ord('f'), self.focus_filter)
        
        # Register swipe gestures
        self.input_handler.enable_swipe_navigation(
            left_action=self.prev_result,
            right_action=self.next_result,
            up_action=self.scroll_up,
            down_action=self.scroll_down
        )
        
    def get_display_results(self) -> List[str]:
        """Format results for display"""
        display_items = []
        for i, result in enumerate(self.filtered_results):
            # Highlight current item
            prefix = ">> " if i == self.current_index else f"{i+1:2d}. "
            
            # Format file and line info
            file_name = Path(result.file_path).name
            if len(file_name) > 20:
                file_name = file_name[:17] + "..."
                
            display = f"{prefix}{file_name}:{result.line_number} - {result.context[:40]}"
            display_items.append(display)
            
        return display_items
        
    def on_result_selected(self, index, item):
        """Handle result selection from list"""
        if 0 <= index < len(self.filtered_results):
            self.current_index = index
            self.update_preview()
            
    def on_filter_changed(self, new_filter):
        """Handle file filter changes"""
        self.file_filter = new_filter.lower()
        self.apply_filter()
        self.current_index = 0
        self.update_results_list()
        self.update_preview()
        
    def apply_filter(self):
        """Apply file name filter"""
        if not self.file_filter:
            self.filtered_results = self.results[:]
            return
            
        self.filtered_results = [
            r for r in self.results
            if self.file_filter in r.file_path.lower()
        ]
        
    def prev_result(self):
        """Navigate to previous result"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_selection()
            
    def next_result(self):
        """Navigate to next result"""
        if self.current_index < len(self.filtered_results) - 1:
            self.current_index += 1
            self.update_selection()
            
    def update_selection(self):
        """Update UI for current selection"""
        self.update_results_list()
        self.update_preview()
        self.ensure_visible()
        
    def update_results_list(self):
        """Update results list display"""
        if self.results_list:
            self.results_list.items = self.get_display_results()
            self.results_list.selected_index = self.current_index
            
    def update_preview(self):
        """Update match preview"""
        if not self.filtered_results or self.current_index >= len(self.filtered_results):
            self.preview_card.content = ["No results to display"]
            return
            
        result = self.filtered_results[self.current_index]
        self.preview_file = result.file_path
        content = self.screen_manager.app.editor.files_content.get(result.file_path, "")
        lines = content.split('\n')
        
        # Get surrounding context
        start_line = max(0, result.line_number - 1 - self.context_size)
        end_line = min(len(lines), result.line_number + self.context_size)
        
        preview_lines = []
        for i in range(start_line, end_line):
            # Highlight current line
            if i + 1 == result.line_number:
                # Highlight match within line
                line = lines[i]
                preview_line = line[:result.column] + ">>" + line[result.column:result.column+len(result.match_text)] + "<<" + line[result.column+len(result.match_text):]
                preview_lines.append(f"{i+1:4d}: {preview_line}")
            else:
                preview_lines.append(f"{i+1:4d}: {lines[i]}")
                
        self.preview_card.content = preview_lines
        
    def ensure_visible(self):
        """Ensure current result is visible in list"""
        if not self.results_list:
            return
            
        # Calculate visible range
        list_height = self.results_list.region.height
        visible_start = self.results_list.scroll_offset
        visible_end = visible_start + list_height - 1
        
        # Adjust scroll if needed
        if self.current_index < visible_start:
            self.results_list.scroll_offset = self.current_index
        elif self.current_index >= visible_end:
            self.results_list.scroll_offset = self.current_index - list_height + 1
            
        self.update_results_list()
        
    def replace_current(self):
        """Replace current match"""
        if not self.filtered_results or self.current_index >= len(self.filtered_results):
            return
            
        result = self.filtered_results[self.current_index]
        
        # Show replace dialog
        self.screen_manager.show_input_dialog(
            "Replace with:",
            lambda text: self.perform_replace(result, text)
        )
        
    def perform_replace(self, result, replace_text):
        """Perform the replacement"""
        editor = self.screen_manager.app.editor
        
        # Get current content
        content = editor.files_content.get(result.file_path, "")
        lines = content.split('\n')
        
        # Check if line still exists
        if result.line_number - 1 >= len(lines):
            self.screen_manager.show_snackbar("Error: Line not found")
            return
            
        line = lines[result.line_number - 1]
        
        # Check if match is still at same position
        if (result.column + len(result.match_text) > len(line) or \
           line[result.column:result.column+len(result.match_text)] != result.match_text:
            self.screen_manager.show_snackbar("Error: Content changed")
            return
            
        # Perform replacement
        new_line = line[:result.column] + replace_text + line[result.column+len(result.match_text):]
        lines[result.line_number - 1] = new_line
        editor.files_content[result.file_path] = '\n'.join(lines)
        editor.modifications_made = True
        
        # Remove this result
        if result in editor.search_results:
            editor.search_results.remove(result)
        if result in self.results:
            self.results.remove(result)
            
        # Update filtered results
        self.apply_filter()
        
        # Adjust current index
        if self.current_index >= len(self.filtered_results):
            self.current_index = max(0, len(self.filtered_results) - 1)
            
        # Show feedback
        self.screen_manager.show_snackbar("Replacement successful")
        self.update_results_list()
        self.update_preview()
        
    def replace_all(self):
        """Replace all matches"""
        if not self.filtered_results:
            return
            
        # Show confirmation dialog
        self.screen_manager.show_confirm_dialog(
            f"Replace all {len(self.filtered_results)} matches?",
            self.perform_replace_all
        )
        
    def perform_replace_all(self):
        """Perform replace all operation"""
        if not self.filtered_results:
            return
            
        editor = self.screen_manager.app.editor
        pattern = self.search_pattern
        
        # Show input dialog
        self.screen_manager.show_input_dialog(
            "Replace all with:",
            lambda text: self.do_batch_replace(text)
        )
        
    def do_batch_replace(self, replace_text):
        """Execute batch replace"""
        editor = self.screen_manager.app.editor
        
        # Count replacements per file
        file_counts = {}
        for result in self.filtered_results:
            file_counts[result.file_path] = file_counts.get(result.file_path, 0) + 1
            
        # Perform replacements
        for file_path, count in file_counts.items():
            content = editor.files_content[file_path]
            
            # Simple text replacement
            if not editor.regex_mode and not editor.whole_words:
                new_content = content.replace(self.search_pattern, replace_text)
            else:
                # Regex replacement
                flags = re.IGNORECASE if not editor.case_sensitive else 0
                if editor.whole_words:
                    pattern = r'\b' + re.escape(self.search_pattern) + r'\b'
                else:
                    pattern = self.search_pattern
                    
                try:
                    regex = re.compile(pattern, flags)
                    new_content = regex.sub(replace_text, content)
                except re.error:
                    self.screen_manager.show_snackbar("Regex error in replacement")
                    return
                    
            editor.files_content[file_path] = new_content
            
        # Update status
        total = len(self.filtered_results)
        editor.modifications_made = True
        self.screen_manager.show_snackbar(f"Replaced {total} occurrences")
        
        # Clear results
        editor.search_results = [r for r in editor.search_results if r not in self.filtered_results]
        self.results = editor.search_results
        self.filtered_results = []
        self.current_index = 0
        self.update_results_list()
        self.update_preview()
        
    def focus_filter(self):
        """Set focus to filter field"""
        if self.filter_field:
            self.filter_field.focused = True
            
    def scroll_up(self):
        """Scroll results list up"""
        current_time = time.time()
        if current_time - self.last_scroll_time > self.scroll_delay:
            if self.results_list and self.results_list.scroll_offset > 0:
                self.results_list.scroll_offset -= 1
                self.update_results_list()
                self.last_scroll_time = current_time
                
    def scroll_down(self):
        """Scroll results list down"""
        current_time = time.time()
        if current_time - self.last_scroll_time > self.scroll_delay:
            if self.results_list and self.results_list.scroll_offset < len(self.results_list.items) - self.results_list.region.height:
                self.results_list.scroll_offset += 1
                self.update_results_list()
                self.last_scroll_time = current_time
                
    def draw(self):
        """Draw search results screen"""
        super().draw()
        
        # Draw header
        header = f"Search Results: {len(self.filtered_results)} matches"
        if self.file_filter:
            header += f" (filtered)"
        self.stdscr.addstr(1, (curses.COLS - len(header)) // 2, header, 
                          self.theme.get_highlight_color(self.theme.PRIMARY))
        
        # Draw match info
        if self.filtered_results and self.current_index < len(self.filtered_results):
            result = self.filtered_results[self.current_index]
            match_info = f"Match {self.current_index+1}/{len(self.filtered_results)} in {Path(result.file_path).name}"
            self.stdscr.addstr(3, 5, match_info[:curses.COLS-10], self.theme.get_color(self.theme.TEXT_SECONDARY))
        
        # Draw help
        help_text = "↑↓: Navigate  R: Replace  A: Replace All  F: Filter  ←→: Prev/Next"
        self.stdscr.addstr(curses.LINES - 2, (curses.COLS - len(help_text)) // 2, help_text,
                          self.theme.get_color(self.theme.TEXT_SECONDARY))
        
    def get_state(self):
        """Get current screen state"""
        return {
            "current_index": self.current_index,
            "file_filter": self.file_filter,
            "search_pattern": self.search_pattern
        }
        
    def set_state(self, state):
        """Restore screen state"""
        self.current_index = state.get("current_index", 0)
        self.file_filter = state.get("file_filter", "")
        self.search_pattern = state.get("search_pattern", "")
        
        self.apply_filter()
        self.update_results_list()
        self.update_preview()
        self.ensure_visible()