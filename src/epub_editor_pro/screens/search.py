# epub_editor_pro/screens/search.py

import curses
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from .base_screen import BaseScreen
from ..ui.material_components import MaterialCard, MaterialButton, MaterialTextField, MaterialChip

class SearchScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager, core_modules):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager, core_modules)
        self.name = "search"
        self.search_pattern = ""
        self.case_sensitive = False
        self.regex_mode = False
        self.whole_words = False
        
        # Asynchronous search handling
        self.is_searching = False
        self.search_future = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.loading_animation_frame = 0

    def setup_components(self):
        """Create UI components for the search screen."""
        main_region = self.layout.get_region("main")
        if not main_region: return

        y_pos, x_pos, h, w = main_region.y, main_region.x, main_region.height, main_region.width

        # Search pattern field
        self.pattern_field = MaterialTextField(
            self.theme, LayoutRegion("pattern", y_pos + 2, x_pos + 5, 3, w - 10),
            "Search for:", self.search_pattern, lambda text: setattr(self, 'search_pattern', text)
        )
        self.add_component(self.pattern_field)
        
        # Options
        options_y = y_pos + 6
        self.case_chip = MaterialChip(self.theme, LayoutRegion("case", options_y, x_pos + 5, 1, 22), "[C]ase Sensitive", self.toggle_case)
        self.regex_chip = MaterialChip(self.theme, LayoutRegion("regex", options_y, x_pos + 28, 1, 13), "[R]egex", self.toggle_regex)
        self.words_chip = MaterialChip(self.theme, LayoutRegion("words", options_y, x_pos + 42, 1, 18), "[W]hole Words", self.toggle_whole_words)
        self.add_component(self.case_chip)
        self.add_component(self.regex_chip)
        self.add_component(self.words_chip)
        
        # Action buttons
        button_y = options_y + 4
        self.add_component(MaterialButton(self.theme, LayoutRegion("btn_search", button_y, x_pos + 5, 3, 15), "Search", self.execute_search))
        self.add_component(MaterialButton(self.theme, LayoutRegion("btn_replace", button_y, x_pos + 22, 3, 20), "Go to Replace", self.go_to_replace))

        self.update_option_chips()
        self.update_focusable_components()
        self.focus_first_component()

    def setup_input(self):
        super().setup_input()
        self.input_handler.register_key(ord('\n'), self.execute_search, self.name)
        self.input_handler.register_key(curses.KEY_ENTER, self.execute_search, self.name)
        self.input_handler.register_key(ord('c'), self.toggle_case, self.name)
        self.input_handler.register_key(ord('r'), self.toggle_regex, self.name)
        self.input_handler.register_key(ord('w'), self.toggle_whole_words, self.name)
        self.input_handler.set_context(self.name)
        
    def toggle_case(self): self.case_sensitive = not self.case_sensitive; self.update_option_chips()
    def toggle_regex(self): self.regex_mode = not self.regex_mode; self.update_option_chips()
    def toggle_whole_words(self): self.whole_words = not self.whole_words; self.update_option_chips()

    def update_option_chips(self):
        if self.case_chip: self.case_chip.style = self.theme.PRIMARY if self.case_sensitive else self.theme.SECONDARY
        if self.regex_chip: self.regex_chip.style = self.theme.PRIMARY if self.regex_mode else self.theme.SECONDARY
        if self.words_chip: self.words_chip.style = self.theme.PRIMARY if self.whole_words else self.theme.SECONDARY

    def execute_search(self):
        """Initiates the search asynchronously."""
        if self.is_searching: return
        if not self.search_pattern or not self.core_modules.content_manager.content_map:
            self.show_snackbar("Enter a search pattern and load an EPUB first.", style="error")
            return
            
        self.is_searching = True
        self.search_future = self.executor.submit(
            self.core_modules.search_engine.search,
            self.search_pattern, self.case_sensitive, self.regex_mode, self.whole_words
        )

    def on_search_complete(self, results):
        """Callback function for when the search thread finishes."""
        self.is_searching = False
        self.core_modules.last_search_results = results
        
        if results:
            self.navigate_to("search_results", {"pattern": self.search_pattern})
        else:
            self.show_snackbar("No matches found.", style="warning")
            
    def go_to_replace(self):
        self.navigate_to("replace", data={"find": self.search_pattern})

    def update(self):
        """Called every frame. Checks for the result of the async search."""
        if self.is_searching and self.search_future and self.search_future.done():
            results = self.search_future.result()
            self.on_search_complete(results)

    def draw(self):
        self.stdscr.erase()
        self.draw_header("Search EPUB Content")
        
        if self.is_searching:
            # Draw a loading animation if searching
            animation_chars = ['-', '\\', '|', '/']
            frame = animation_chars[self.loading_animation_frame % len(animation_chars)]
            self.loading_animation_frame += 1
            y, x, h, w = self.layout.get_content_area("main")
            self.stdscr.addstr(y + h // 2, x + w // 2 - 5, f"Searching {frame}")
        else:
            # Draw normal components if not searching
            for component in self.components:
                component.draw(self.stdscr)
        
        self.draw_footer("Enter: Search | C/R/W: Toggle | Tab: Navigate")