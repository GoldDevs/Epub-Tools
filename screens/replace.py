import curses
import re
import time
from typing import List, Dict, Tuple, Optional
from ..ui.material_components import MaterialCard, MaterialButton, MaterialTextField, MaterialChip
from ..ui.layout_manager import LayoutRegion
from .base_screen import BaseScreen
from ..core.replace_engine import ReplaceEngine, ReplacementStats

class ReplaceScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager)
        self.name = "replace"
        self.find_pattern = ""
        self.replace_pattern = ""
        self.case_sensitive = False
        self.regex_mode = False
        self.whole_words = False
        self.preview_content = ""
        self.preview_file = ""
        self.preview_matches = []
        self.current_preview_index = 0
        self.last_search_time = 0
        self.replace_history = []
        self.max_history = 5
        
    def on_create(self, data=None):
        """Initialize replace screen"""
        if data:
            self.find_pattern = data.get("find", "")
            self.replace_pattern = data.get("replace", "")
            self.case_sensitive = data.get("case_sensitive", False)
            self.regex_mode = data.get("regex_mode", False)
            self.whole_words = data.get("whole_words", False)
            
        self.setup_components()
        self.setup_input()
        
    def setup_components(self):
        """Create UI components"""
        main_region = self.layout.get_region("main")
        if not main_region:
            return
            
        # Create find pattern field
        self.find_field = MaterialTextField(
            self.theme, LayoutRegion("find", 5, 3, main_region.width - 10, 3),
            "Find:", self.find_pattern, self.on_find_changed
        )
        self.add_component(self.find_field)
        
        # Create replace pattern field
        self.replace_field = MaterialTextField(
            self.theme, LayoutRegion("replace", 5, 6, main_region.width - 10, 3),
            "Replace with:", self.replace_pattern, self.on_replace_changed
        )
        self.add_component(self.replace_field)
        
        # Create options card
        options_card = MaterialCard(
            self.theme, LayoutRegion("options", 5, 9, main_region.width - 10, 6),
            "Replace Options"
        )
        
        # Create option chips
        self.case_chip = MaterialChip(
            self.theme, LayoutRegion("case", 0, 0, 20, 1), 
            "Case Sensitive: OFF", self.toggle_case
        )
        self.case_chip.selected = self.case_sensitive
        self.update_case_chip()
        
        self.regex_chip = MaterialChip(
            self.theme, LayoutRegion("regex", 0, 0, 20, 1), 
            "Regex: OFF", self.toggle_regex
        )
        self.regex_chip.selected = self.regex_mode
        self.update_regex_chip()
        
        self.words_chip = MaterialChip(
            self.theme, LayoutRegion("words", 0, 0, 20, 1), 
            "Whole Words: OFF", self.toggle_whole_words
        )
        self.words_chip.selected = self.whole_words
        self.update_words_chip()
        
        options_card.add_component(self.case_chip)
        options_card.add_component(self.regex_chip)
        options_card.add_component(self.words_chip)
        self.add_component(options_card)
        
        # Create preview card
        self.preview_card = MaterialCard(
            self.theme, LayoutRegion("preview", 5, 16, main_region.width - 10, 8),
            "Preview"
        )
        self.add_component(self.preview_card)
        
        # Create action buttons
        actions_y = 25
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_preview", 5, actions_y, 15, 1),
            "Preview Matches", self.preview_matches_action
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_replace", 25, actions_y, 15, 1),
            "Replace", self.execute_replace
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_replace_all", 45, actions_y, 15, 1),
            "Replace All", self.execute_replace_all
        ))
        self.add_component(MaterialButton(
            self.theme, LayoutRegion("btn_history", 65, actions_y, 15, 1),
            "History", self.show_history
        ))
        
        # Create status chip
        self.status_chip = MaterialChip(
            self.theme, LayoutRegion("status", 5, actions_y + 2, main_region.width - 10, 1),
            "Enter find and replace patterns"
        )
        self.add_component(self.status_chip)
        
    def setup_input(self):
        """Set up input handlers"""
        self.input_handler.register_key(ord('c'), self.toggle_case)
        self.input_handler.register_key(ord('r'), self.toggle_regex)
        self.input_handler.register_key(ord('w'), self.toggle_whole_words)
        self.input_handler.register_key(ord('p'), self.preview_matches_action)
        self.input_handler.register_key(ord(' '), self.next_preview)
        
        # Register swipe gestures
        self.input_handler.enable_swipe_navigation(
            left_action=self.prev_preview,
            right_action=self.next_preview,
            up_action=self.scroll_up,
            down_action=self.scroll_down
        )
        
    def on_find_changed(self, new_pattern):
        """Handle find pattern changes"""
        self.find_pattern = new_pattern
        self.update_preview()
        
    def on_replace_changed(self, new_pattern):
        """Handle replace pattern changes"""
        self.replace_pattern = new_pattern
        self.update_preview()
        
    def toggle_case(self):
        """Toggle case sensitivity"""
        self.case_sensitive = not self.case_sensitive
        self.update_case_chip()
        self.update_preview()
        
    def update_case_chip(self):
        """Update case chip display"""
        if self.case_chip:
            state = "ON" if self.case_sensitive else "OFF"
            self.case_chip.text = f"Case Sensitive: {state}"
            self.case_chip.selected = self.case_sensitive
            
    def toggle_regex(self):
        """Toggle regex mode"""
        self.regex_mode = not self.regex_mode
        self.update_regex_chip()
        self.update_preview()
        
    def update_regex_chip(self):
        """Update regex chip display"""
        if self.regex_chip:
            state = "ON" if self.regex_mode else "OFF"
            self.regex_chip.text = f"Regex: {state}"
            self.regex_chip.selected = self.regex_mode
            
    def toggle_whole_words(self):
        """Toggle whole words mode"""
        self.whole_words = not self.whole_words
        self.update_words_chip()
        self.update_preview()
        
    def update_words_chip(self):
        """Update whole words chip display"""
        if self.words_chip:
            state = "ON" if self.whole_words else "OFF"
            self.words_chip.text = f"Whole Words: {state}"
            self.words_chip.selected = self.whole_words
            
    def preview_matches_action(self):
        """Preview matches action"""
        if not self.find_pattern:
            self.status_chip.text = "Error: No find pattern entered"
            return
            
        self.preview_matches()
        
    def update_preview(self):
        """Update preview content"""
        if not self.find_pattern:
            self.preview_card.content = ["Enter a find pattern to see preview"]
            return
            
        # Get sample content from first HTML file
        editor = self.screen_manager.app.editor
        html_files = [f for f in editor.files_content if f.endswith(('.html', '.xhtml'))]
        
        if not html_files:
            self.preview_card.content = ["No content files available for preview"]
            return
            
        self.preview_file = html_files[0]
        content = editor.files_content[self.preview_file]
        
        # Find first match
        try:
            if self.regex_mode:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                regex = re.compile(self.find_pattern, flags)
                match = regex.search(content)
            else:
                if self.case_sensitive:
                    match_text = self.find_pattern
                else:
                    match_text = self.find_pattern.lower()
                    content = content.lower()
                    
                pos = content.find(match_text)
                if pos != -1:
                    match = type('Match', (), {'start': lambda: pos, 'end': lambda: pos + len(match_text)})
                else:
                    match = None
        except re.error:
            self.preview_card.content = ["Invalid regular expression"]
            return
            
        if not match:
            self.preview_card.content = ["No matches found in sample file"]
            return
            
        # Extract context
        start = max(0, match.start() - 50)
        end = min(len(content), match.end() + 50)
        context = content[start:end]
        
        # Highlight match
        if self.regex_mode and self.replace_pattern:
            # Show replacement preview
            preview = regex.sub(self.replace_pattern, context)
            preview = preview.replace('\n', ' ')  # Remove newlines for display
            display_text = [preview]
        else:
            # Show match highlight
            match_start = match.start() - start
            match_end = match.end() - start
            preview = context[:match_start] + ">>" + context[match_start:match_end] + "<<" + context[match_end:]
            preview = preview.replace('\n', ' ')  # Remove newlines for display
            display_text = [preview]
            
        self.preview_card.content = display_text
        
    def preview_matches(self):
        """Preview matches across files"""
        if not self.find_pattern:
            return
            
        editor = self.screen_manager.app.editor
        
        # Perform search
        results = editor.search_text(
            self.find_pattern,
            self.case_sensitive,
            self.regex_mode,
            self.whole_words
        )
        
        if not results:
            self.status_chip.text = "No matches found"
            return
            
        self.status_chip.text = f"Found {len(results)} matches in {len(editor.files_content)} files"
        
        # Group results by file
        file_results = {}
        for result in results:
            if result.file_path not in file_results:
                file_results[result.file_path] = []
            file_results[result.file_path].append(result)
            
        # Create preview content
        preview_lines = []
        for file_path, matches in list(file_results.items())[:3]:  # Show first 3 files
            file_name = Path(file_path).name
            preview_lines.append(f"📄 {file_name}: {len(matches)} matches")
            for i, match in enumerate(matches[:3]):  # Show first 3 matches per file
                context = match.context[:50] + "..." if len(match.context) > 50 else match.context
                preview_lines.append(f"  {i+1}. Line {match.line_number}: {context}")
                
        self.preview_card.content = preview_lines
        
    def execute_replace(self):
        """Execute the replace operation"""
        if not self.find_pattern or not self.replace_pattern:
            self.status_chip.text = "Error: Find and replace patterns required"
            return
            
        editor = self.screen_manager.app.editor
        if not editor.files_content:
            self.status_chip.text = "Error: No EPUB file loaded"
            return
            
        # Show confirmation dialog
        self.screen_manager.show_confirm_dialog(
            "Replace next occurrence?",
            self.perform_replace
        )
        
    def perform_replace(self):
        """Perform the replace operation"""
        editor = self.screen_manager.app.editor
        
        # Find next occurrence
        results = editor.search_text(
            self.find_pattern,
            self.case_sensitive,
            self.regex_mode,
            self.whole_words
        )
        
        if not results:
            self.status_chip.text = "No matches found"
            return
            
        # Get first result
        result = results[0]
        
        # Perform replacement
        content = editor.files_content.get(result.file_path, "")
        lines = content.split('\n')
        
        # Check if line still exists
        if result.line_number - 1 >= len(lines):
            self.status_chip.text = "Error: Line not found"
            return
            
        line = lines[result.line_number - 1]
        
        # Check if match is still at same position
        if (result.column + len(result.match_text) > len(line) or \
           line[result.column:result.column+len(result.match_text)] != result.match_text:
            self.status_chip.text = "Error: Content changed"
            return
            
        # Perform replacement
        new_line = line[:result.column] + self.replace_pattern + line[result.column+len(result.match_text):]
        lines[result.line_number - 1] = new_line
        editor.files_content[result.file_path] = '\n'.join(lines)
        editor.modifications_made = True
        
        # Show feedback
        self.status_chip.text = f"Replaced at line {result.line_number} in {Path(result.file_path).name}"
        self.save_to_history()
        
    def execute_replace_all(self):
        """Execute replace all operation"""
        if not self.find_pattern or not self.replace_pattern:
            self.status_chip.text = "Error: Find and replace patterns required"
            return
            
        editor = self.screen_manager.app.editor
        if not editor.files_content:
            self.status_chip.text = "Error: No EPUB file loaded"
            return
            
        # Show confirmation dialog
        self.screen_manager.show_confirm_dialog(
            "Replace ALL occurrences?",
            self.perform_replace_all
        )
        
    def perform_replace_all(self):
        """Perform replace all operation"""
        editor = self.screen_manager.app.editor
        replace_engine = ReplaceEngine(editor.content_manager)
        
        # Perform replacement
        stats = replace_engine.pattern_replace(
            self.find_pattern,
            self.replace_pattern,
            self.case_sensitive,
            self.regex_mode,
            self.whole_words
        )
        
        # Update status
        if stats.files_modified > 0:
            editor.modifications_made = True
            self.status_chip.text = f"Replaced {stats.total_replacements} occurrences in {stats.files_modified} files"
            self.save_to_history()
            self.screen_manager.show_snackbar("Replace all completed")
        else:
            self.status_chip.text = "No replacements made"
            
    def save_to_history(self):
        """Save current replace to history"""
        history_item = {
            "find": self.find_pattern,
            "replace": self.replace_pattern,
            "case": self.case_sensitive,
            "regex": self.regex_mode,
            "whole": self.whole_words,
            "timestamp": time.time()
        }
        
        # Add to history
        self.replace_history.append(history_item)
        
        # Limit history size
        self.replace_history = self.replace_history[-self.max_history:]
        
    def show_history(self):
        """Show replace history"""
        if not self.replace_history:
            self.status_chip.text = "No replace history"
            return
            
        # Create history display
        history_lines = []
        for i, item in enumerate(reversed(self.replace_history)):
            history_lines.append(f"{i+1}. {item['find']} → {item['replace']}")
            
        self.preview_card.content = history_lines
        
    def next_preview(self):
        """Navigate to next preview item"""
        if self.preview_card and len(self.preview_card.content) > 1:
            self.current_preview_index = (self.current_preview_index + 1) % len(self.preview_card.content)
            # In a real implementation, we'd update the preview display
            
    def prev_preview(self):
        """Navigate to previous preview item"""
        if self.preview_card and len(self.preview_card.content) > 1:
            self.current_preview_index = (self.current_preview_index - 1) % len(self.preview_card.content)
            # In a real implementation, we'd update the preview display
            
    def draw(self):
        """Draw replace screen"""
        super().draw()
        
        # Draw header
        header = "Find and Replace"
        self.stdscr.addstr(1, (curses.COLS - len(header)) // 2, header, 
                          self.theme.get_highlight_color(self.theme.PRIMARY))
        
        # Draw help
        help_text = "C: Case  R: Regex  W: Words  P: Preview  Space: Next  ←→: Navigate"
        self.stdscr.addstr(curses.LINES - 2, (curses.COLS - len(help_text)) // 2, help_text,
                          self.theme.get_color(self.theme.TEXT_SECONDARY))
        
    def get_state(self):
        """Get current screen state"""
        return {
            "find_pattern": self.find_pattern,
            "replace_pattern": self.replace_pattern,
            "case_sensitive": self.case_sensitive,
            "regex_mode": self.regex_mode,
            "whole_words": self.whole_words,
            "history": self.replace_history
        }
        
    def set_state(self, state):
        """Restore screen state"""
        self.find_pattern = state.get("find_pattern", "")
        self.replace_pattern = state.get("replace_pattern", "")
        self.case_sensitive = state.get("case_sensitive", False)
        self.regex_mode = state.get("regex_mode", False)
        self.whole_words = state.get("whole_words", False)
        self.replace_history = state.get("history", [])
        
        # Update fields
        if self.find_field:
            self.find_field.value = self.find_pattern
        if self.replace_field:
            self.replace_field.value = self.replace_pattern
        self.update_case_chip()
        self.update_regex_chip()
        self.update_words_chip()
        self.update_preview()