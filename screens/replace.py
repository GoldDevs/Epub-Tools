# epub_editor_pro/screens/replace.py

import curses
import re
from typing import List, Dict, Tuple, Optional
from .base_screen import BaseScreen
from ..ui.material_components import MaterialCard, MaterialButton, MaterialTextField, MaterialChip
from ..core.search_engine import SearchResult

class ReplaceScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager, core_modules):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager, core_modules)
        self.name = "replace"
        
        # State
        self.find_pattern = ""
        self.replace_pattern = ""
        self.case_sensitive = False
        self.regex_mode = False
        self.whole_words = False
        self.current_match: Optional[SearchResult] = None
        self.last_search_position = {"file_path": None, "line_number": 0, "start_pos": 0}

        # UI Components
        self.find_field: Optional[MaterialTextField] = None
        self.replace_field: Optional[MaterialTextField] = None
        self.preview_card: Optional[MaterialCard] = None

    def on_create(self, data=None):
        """Initialize with data from search screen if available."""
        if data:
            self.find_pattern = data.get("find", "")
            self.case_sensitive = data.get("case_sensitive", False)
            self.regex_mode = data.get("regex_mode", False)
            self.whole_words = data.get("whole_words", False)
        super().on_create(data)

    def setup_components(self):
        """Create UI components for the replace screen."""
        main_region = self.layout.get_region("main")
        if not main_region: return
        
        y, x, h, w = main_region.y, main_region.x, main_region.height, main_region.width

        self.find_field = MaterialTextField(self.theme, LayoutRegion("find", y + 1, x + 2, 3, w - 20), "Find:", self.find_pattern, lambda t: setattr(self, 'find_pattern', t))
        self.replace_field = MaterialTextField(self.theme, LayoutRegion("replace", y + 4, x + 2, 3, w - 20), "Replace:", self.replace_pattern, lambda t: setattr(self, 'replace_pattern', t))
        
        self.add_component(self.find_field)
        self.add_component(self.replace_field)
        
        # Preview Card
        preview_y = y + 8
        preview_height = h - 13
        self.preview_card = MaterialCard(self.theme, LayoutRegion("preview", preview_y, x + 2, preview_height, w - 4), "Preview")
        self.add_component(self.preview_card)

        # Action Buttons
        button_y = y + h - 4
        self.add_component(MaterialButton(self.theme, LayoutRegion("b_find", button_y, x + 2, 3, 15), "Find Next", self.find_next_match))
        self.add_component(MaterialButton(self.theme, LayoutRegion("b_rep", button_y, x + 18, 3, 15), "Replace", self.replace_current))
        self.add_component(MaterialButton(self.theme, LayoutRegion("b_rep_find", button_y, x + 34, 3, 20), "Replace & Find", self.replace_and_find))
        self.add_component(MaterialButton(self.theme, LayoutRegion("b_rep_all", button_y, x + 55, 3, 15), "Replace All", self.replace_all))

        self.update_focusable_components()
        self.update_preview()

    def setup_input(self):
        super().setup_input()
        self.input_handler.register_key(curses.KEY_F3, self.find_next_match, self.name)
        self.input_handler.set_context(self.name)

    def find_next_match(self):
        """Finds the next occurrence of the pattern from the current position."""
        if not self.find_pattern:
            self.show_snackbar("Find pattern is empty.", "warning")
            return
        
        # This is a simplified sequential search. A real implementation would be more complex.
        # For this project, we'll just use the full search and pick the next result.
        all_results = self.core_modules.search_engine.search(self.find_pattern, self.case_sensitive, self.regex_mode, self.whole_words)
        
        if not all_results:
            self.current_match = None
            self.show_snackbar("No matches found.", "info")
        else:
            # Find the index of the current match to find the next one
            try:
                current_idx = all_results.index(self.current_match) if self.current_match else -1
                self.current_match = all_results[(current_idx + 1) % len(all_results)]
            except ValueError:
                self.current_match = all_results[0]
        
        self.update_preview()

    def replace_current(self):
        """Replaces the currently highlighted match."""
        if not self.current_match:
            self.show_snackbar("No match selected. Use 'Find Next' first.", "warning")
            return
            
        stats = self.core_modules.replace_engine.replace_by_results([self.current_match], self.replace_pattern)
        if stats.total_replacements > 0:
            self.show_snackbar("1 occurrence replaced.", "success")
            self.current_match = None # Invalidate current match
            self.update_preview()
        else:
            self.show_snackbar("Replacement failed.", "error")

    def replace_and_find(self):
        """Replaces the current match and automatically finds the next one."""
        if not self.current_match:
            self.find_next_match()
        else:
            self.replace_current()
            self.find_next_match()

    def replace_all(self):
        """Replaces all occurrences in the entire EPUB."""
        if not self.find_pattern:
            self.show_snackbar("Find pattern is empty.", "warning")
            return

        def on_confirm():
            stats = self.core_modules.replace_engine.pattern_replace(
                self.find_pattern, self.replace_pattern, self.case_sensitive, self.regex_mode, self.whole_words
            )
            self.show_snackbar(f"Replaced {stats.total_replacements} occurrences in {stats.files_modified} files.", "success")
            self.current_match = None
            self.update_preview()
        
        self.show_confirm_dialog(f"Replace all occurrences of '{self.find_pattern}'?", on_confirm)

    def update_preview(self):
        """Update the preview card to show the current match's context."""
        if not self.preview_card: return
        
        if self.current_match:
            res = self.current_match
            content = self.core_modules.content_manager.get_content(res.file_path)
            if content:
                lines = content.split('\n')
                line_idx = res.line_number - 1
                if 0 <= line_idx < len(lines):
                    line_content = lines[line_idx]
                    # Simple highlight for preview
                    highlighted_line = line_content[:res.start_pos] + ">>" + res.match_text + "<<" + line_content[res.end_pos:]
                    self.preview_card.title = f"Preview: {Path(res.file_path).name}:{res.line_number}"
                    self.preview_card.content = [highlighted_line.strip()]
                else:
                    self.preview_card.content = ["Line not found."]
            else:
                self.preview_card.content = ["File content not found."]
        else:
            self.preview_card.title = "Preview"
            self.preview_card.content = ["Use 'Find Next' to see a match preview."]

    def draw(self):
        """Draw the replace screen."""
        self.stdscr.erase()
        self.draw_header("Find and Replace")
        
        for component in self.components:
            component.draw(self.stdscr)

        self.draw_footer("F3: Find Next | Tab: Navigate | Enter: Action")