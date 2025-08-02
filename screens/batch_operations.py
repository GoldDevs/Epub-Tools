# epub_editor_pro/screens/batch_operations.py

import curses
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from .base_screen import BaseScreen
from ..ui.material_components import MaterialCard, MaterialButton, MaterialList, MaterialTextField, MaterialChip, MaterialProgress

class BatchOperationsScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager, core_modules):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager, core_modules)
        self.name = "batch_ops"
        
        # State
        self.operations: List[Dict] = []
        self.templates: List[Dict] = []
        self.template_dir = Path("templates")
        
        # UI Components
        self.ops_list_comp: Optional[MaterialList] = None
        self.progress_bar_comp: Optional[MaterialProgress] = None
        self.status_chip_comp: Optional[MaterialChip] = None
        
        # Asynchronous processing
        self.is_processing = False
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.progress_info = {"current": 0, "total": 0, "message": "Ready"}

    def on_create(self, data=None):
        """Initialize batch operations screen and load templates."""
        self.template_dir.mkdir(exist_ok=True)
        self.load_templates()
        super().on_create(data)

    def setup_components(self):
        """Create UI components."""
        main_region = self.layout.get_region("main")
        if not main_region: return
        y, x, h, w = main_region.y, main_region.x, main_region.height, main_region.width

        # Operations List Card
        ops_card_height = h - 10
        ops_card = MaterialCard(self.theme, LayoutRegion("ops_card", y + 1, x + 2, ops_card_height, w - 4), "Operations Queue")
        self.ops_list_comp = MaterialList(self.theme, LayoutRegion("ops_list", y + 2, x + 4, ops_card_height - 2, w - 8), [])
        self.add_component(ops_card)
        self.add_component(self.ops_list_comp)

        # Progress Card
        progress_y = y + ops_card_height + 1
        progress_card = MaterialCard(self.theme, LayoutRegion("prog_card", progress_y, x + 2, h - ops_card_height - 2, w - 4), "Progress")
        self.progress_bar_comp = MaterialProgress(self.theme, LayoutRegion("prog_bar", progress_y + 2, x + 4, 1, w - 8))
        self.status_chip_comp = MaterialChip(self.theme, LayoutRegion("status_chip", progress_y + 4, x + 4, 1, w - 8), "Ready")
        self.add_component(progress_card)
        self.add_component(self.progress_bar_comp)
        self.add_component(self.status_chip_comp)
        
        self.refresh_operations_list()

    def setup_input(self):
        super().setup_input()
        self.input_handler.register_key(ord('a'), self.add_operation, self.name)
        self.input_handler.register_key(ord('d'), self.remove_operation, self.name)
        self.input_handler.register_key(ord('r'), self.run_batch, self.name)
        self.input_handler.register_key(ord('c'), self.clear_operations, self.name)
        self.input_handler.set_context(self.name)

    def add_operation(self):
        """Adds a new operation. In a real app, this would open a new screen/dialog."""
        # For this correction, we'll simulate adding a pre-defined operation.
        new_op = {
            "find": f"SampleFind{len(self.operations) + 1}", 
            "replace": "SampleReplace", 
            "case_sensitive": False, "regex": False, "whole_words": False
        }
        self.operations.append(new_op)
        self.refresh_operations_list()
        self.show_snackbar("Simulated: Added a new sample operation.")

    def remove_operation(self):
        """Remove the selected operation from the queue."""
        if self.ops_list_comp and 0 <= self.ops_list_comp.selected_index < len(self.operations):
            selected_index = self.ops_list_comp.selected_index
            self.operations.pop(selected_index)
            self.refresh_operations_list()
            self.ops_list_comp.selected_index = min(selected_index, len(self.operations) - 1)

    def clear_operations(self):
        """Clear all operations from the queue."""
        self.operations.clear()
        self.refresh_operations_list()

    def refresh_operations_list(self):
        """Update the list component with the current operations."""
        if self.ops_list_comp:
            self.ops_list_comp.items = [f"'{op['find']}' → '{op['replace']}'" for op in self.operations]

    def run_batch(self):
        """Run all operations in the queue asynchronously."""
        if not self.operations:
            self.show_snackbar("No operations in the queue.", "warning")
            return
        if self.is_processing: return

        self.is_processing = True
        self.progress_info['total'] = len(self.operations)
        self.executor.submit(self._batch_worker)

    def _batch_worker(self):
        """The background worker function for processing the batch."""
        total_ops = len(self.operations)
        for i, op in enumerate(self.operations):
            self.progress_info['current'] = i
            self.progress_info['message'] = f"Op {i+1}/{total_ops}: Replacing '{op['find']}'"
            
            # This call is blocking, but it's in a background thread.
            self.core_modules.replace_engine.pattern_replace(
                op["find"], op["replace"], op.get("case_sensitive", False),
                op.get("regex", False), op.get("whole_words", False)
            )
            time.sleep(0.1) # small delay to make progress visible

        self.progress_info['current'] = total_ops
        self.progress_info['message'] = "Batch processing complete."
        self.is_processing = False

    def load_templates(self):
        """Load operation templates from files."""
        # This part can be expanded with a UI for template management.
        pass 

    def update_progress_ui(self):
        """Update progress bar and status text based on worker state."""
        if not self.progress_bar_comp or not self.status_chip_comp: return

        if self.is_processing:
            self.progress_bar_comp.max_value = self.progress_info['total']
            self.progress_bar_comp.value = self.progress_info['current']
            self.status_chip_comp.text = self.progress_info['message']
        else:
            self.progress_bar_comp.value = 0
            self.status_chip_comp.text = self.progress_info.get('message', "Ready")

    def draw(self):
        """Draw the screen and update progress UI."""
        self.stdscr.erase()
        self.draw_header("Batch Operations")
        
        self.update_progress_ui()
        
        for component in self.components:
            component.draw(self.stdscr)
            
        self.draw_footer("A: Add | D: Delete | R: Run | C: Clear")