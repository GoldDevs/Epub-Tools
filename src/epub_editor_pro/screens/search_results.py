# epub_editor_pro/screens/search_results.py

import curses
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from .base_screen import BaseScreen
from ..ui.material_components import MaterialList, MaterialButton, MaterialCard, MaterialChip
from ..core.search_engine import SearchResult

class SearchResultsScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager, core_modules):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager, core_modules)
        self.name = "search_results"
        self.search_params: Dict = {}
        self.all_results: List[SearchResult] = []
        self.filtered_results: List[SearchResult] = []
        
        self.results_list_comp: Optional[MaterialList] = None
        self.preview_card_comp: Optional[MaterialCard] = None

    def on_create(self, data=None):
        """Initialize with search results and parameters."""
        if data:
            self.search_params = data.get("search_params", {})
            self.all_results = data.get("results", [])
            self.filtered_results = self.all_results[:]
        super().on_create(data)
        
    def setup_components(self):
        """Create UI components for displaying search results."""
        main_region = self.layout.get_region("main")
        if not main_region: return

        list_height = main_region.height - 8
        self.results_list_comp = MaterialList(
            self.theme, LayoutRegion("results", main_region.y + 1, main_region.x + 2, list_height, main_region.width - 4),
            self.get_display_results(), self.on_result_selected
        )
        self.add_component(self.results_list_comp)

        preview_y = main_region.y + list_height + 2
        preview_height = main_region.height - list_height - 3
        self.preview_card_comp = MaterialCard(
            self.theme, LayoutRegion("preview", preview_y, main_region.x + 2, preview_height, main_region.width - 4), "Preview"
        )
        self.add_component(self.preview_card_comp)
        
        self.update_preview()
        self.update_focusable_components()

    def setup_input(self):
        super().setup_input()
        self.input_handler.register_key(ord('r'), self.replace_current, self.name)
        self.input_handler.register_key(ord('a'), self.replace_all_visible, self.name)
        self.input_handler.register_key(curses.KEY_ENTER, self.on_result_selected, self.name)
        self.input_handler.set_context(self.name)

    def get_display_results(self) -> List[str]:
        """Format results for display in the MaterialList."""
        display_items = []
        for result in self.filtered_results:
            file_name = Path(result.file_path).name
            line_preview = result.context_before + result.match_text + result.context_after
            display = f"{file_name}:{result.line_number} | {line_preview.strip()}"
            display_items.append(display)
        return display_items

    def on_result_selected(self, index=None, item=None):
        """Update the preview when a result is selected."""
        self.update_preview()

    def update_preview(self):
        """Update the match preview card."""
        if not self.results_list_comp or not self.preview_card_comp: return
        
        selected_idx = self.results_list_comp.selected_index
        if not (0 <= selected_idx < len(self.filtered_results)):
            self.preview_card_comp.content = ["No result selected."]
            return

        result = self.filtered_results[selected_idx]
        content = self.core_modules.content_manager.get_content(result.file_path)
        if not content: 
            self.preview_card_comp.content = ["Could not load file content for preview."]
            return

        lines = content.split('\n')
        line_idx = result.line_number - 1
        if 0 <= line_idx < len(lines):
            self.preview_card_comp.content = [f"{result.line_number}: {lines[line_idx].strip()}"]
        else:
            self.preview_card_comp.content = ["Line not found (content may have changed)."]

    def replace_current(self):
        """Replace only the currently selected match."""
        if not self.results_list_comp: return
        selected_idx = self.results_list_comp.selected_index
        
        if not (0 <= selected_idx < len(self.filtered_results)):
            self.show_snackbar("No result selected to replace.", "warning")
            return

        replace_pattern = self.search_params.get("replace", "")
        if not replace_pattern:
            # In a real app, you would prompt for the replacement text here.
            self.show_snackbar("No replacement text provided.", "error")
            return

        result_to_replace = self.filtered_results[selected_idx]
        
        # Use the safe, reverse-order replacement engine method
        stats = self.core_modules.replace_engine.replace_by_results([result_to_replace], replace_pattern)
        
        if stats.total_replacements > 0:
            self.show_snackbar(f"Replaced 1 occurrence.", "success")
            # Remove the now-invalid result from the list and refresh
            self.all_results.remove(result_to_replace)
            self.filtered_results.pop(selected_idx)
            self.results_list_comp.items = self.get_display_results()
            self.results_list_comp.selected_index = min(selected_idx, len(self.filtered_results) - 1)
            self.update_preview()
        else:
            self.show_snackbar("Replacement failed. Content may have changed.", "error")
            
    def replace_all_visible(self):
        """Replace all results currently visible in the list."""
        if not self.filtered_results:
            self.show_snackbar("No results to replace.", "warning")
            return

        replace_pattern = self.search_params.get("replace", "")
        if not replace_pattern:
            self.show_snackbar("No replacement text provided.", "error")
            return
            
        stats = self.core_modules.replace_engine.replace_by_results(self.filtered_results, replace_pattern)
        
        if stats.total_replacements > 0:
            self.show_snackbar(f"Replaced {stats.total_replacements} occurrences in {stats.files_modified} files.", "success")
            # Clear results and go back, as they are all invalid now
            self.core_modules.last_search_results = []
            self.go_back()
        else:
            self.show_snackbar("No occurrences were replaced.", "warning")

    def draw(self):
        """Draw the search results screen."""
        self.stdscr.erase()
        self.draw_header(f"Results for: '{self.search_params.get('pattern', '')}' ({len(self.filtered_results)})")
        
        for component in self.components:
            component.draw(self.stdscr)
            
        self.draw_footer("↑↓: Select | Enter: Preview | R: Replace | A: Replace All")