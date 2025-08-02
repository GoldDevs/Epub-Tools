import curses
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from .base_screen import BaseScreen
from ..ui.material_components import MaterialCard, MaterialButton, MaterialList, MaterialChip
from ..ui.layout_manager import LayoutRegion

class DashboardScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager, core_modules):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager, core_modules)
        self.name = "dashboard"
        self.cards: List[MaterialCard] = []
        self.recent_files: List[str] = []
        self.file_stats: Dict[str, Dict] = {}
        self.last_update_time = 0
        self.update_interval = 30  # Seconds between auto-updates
        
    def on_create(self, data=None):
        """Initialize dashboard components"""
        super().on_create(data)
        self.refresh_data()
        
    def setup_input(self):
        """Register input handlers for the dashboard."""
        self.input_handler.register_key(ord('1'), lambda: self.navigate_to("file_manager"))
        self.input_handler.register_key(ord('2'), lambda: self.navigate_to("search"))
        self.input_handler.register_key(ord('3'), lambda: self.navigate_to("batch_ops"))
        self.input_handler.register_key(ord('4'), lambda: self.navigate_to("settings"))
        self.input_handler.register_key(ord('5'), self.save_current)
        self.input_handler.register_key(ord('q'), self.request_exit)
        self.input_handler.set_context(self.name)

    def on_resume(self, data=None):
        """Refresh data when returning to dashboard."""
        super().on_resume(data)
        if time.time() - self.last_update_time > self.update_interval:
            self.refresh_data()
        else:
            self.create_cards() # Recreate cards to reflect state changes
        
    def refresh_data(self):
        """Refresh all dynamic dashboard data."""
        self.last_update_time = time.time()
        self.load_recent_files()
        self.update_file_stats()
        self.create_cards()
        
    def load_recent_files(self):
        """Load recent files from a history file."""
        history_path = Path("history/recent_files.json")
        self.recent_files = []
        if history_path.exists():
            try:
                with history_path.open('r') as f:
                    # Filter out files that no longer exist
                    self.recent_files = [f for f in json.load(f) if Path(f).exists()]
            except (json.JSONDecodeError, OSError):
                pass
        self.recent_files = self.recent_files[:5]
        
    def update_file_stats(self):
        """Update statistics for the currently loaded file."""
        self.file_stats.clear()
        epub_path_str = self.core_modules.epub_path
        if epub_path_str:
            try:
                stats = os.stat(epub_path_str)
                self.file_stats[epub_path_str] = {
                    "size": stats.st_size,
                    "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
                }
            except OSError:
                pass
                
    def create_cards(self):
        """Create and populate the dashboard cards."""
        self.clear_components()
        
        # File Info Card
        epub_path = self.core_modules.epub_path
        file_info_card = MaterialCard(self.theme, LayoutRegion("file_info", 0, 0, 0, 8), 
                                     "Current EPUB", Path(epub_path).name if epub_path else "No file loaded")
        if epub_path:
            stats = self.file_stats.get(epub_path, {})
            size_mb = f"{stats.get('size', 0) / (1024*1024):.2f} MB"
            file_info_card.add_component(MaterialChip(self.theme, LayoutRegion("size", 0, 0, 20, 1), f"Size: {size_mb}"))
            if self.core_modules.content_manager.has_modifications():
                file_info_card.add_component(MaterialChip(self.theme, LayoutRegion("modified_status", 0, 0, 20, 1), "UNSAVED CHANGES"))

        self.add_component(file_info_card)
        
        # Quick Actions Card
        actions_card = MaterialCard(self.theme, LayoutRegion("actions", 0, 0, 0, 8), "Quick Actions")
        actions = [
            ("1. Load EPUB", lambda: self.navigate_to("file_manager")),
            ("2. Search", lambda: self.navigate_to("search")),
            ("3. Batch Ops", lambda: self.navigate_to("batch_ops")),
            ("4. Settings", lambda: self.navigate_to("settings")),
            ("5. Save", self.save_current),
            ("Q. Quit", self.request_exit)
        ]
        for i, (label, action) in enumerate(actions):
            actions_card.add_component(MaterialButton(self.theme, LayoutRegion(f"btn{i}", 0, 0, len(label) + 4, 1), label, action))
        self.add_component(actions_card)

        # Recent Files Card
        if self.recent_files:
            recent_card = MaterialCard(self.theme, LayoutRegion("recent", 0, 0, 0, 8), "Recent Files")
            file_list_items = [Path(p).name for p in self.recent_files]
            recent_list = MaterialList(self.theme, LayoutRegion("recent_list", 0, 0, 0, len(file_list_items) + 2), file_list_items, self.on_recent_file_select)
            recent_card.add_component(recent_list)
            self.add_component(recent_card)
        
        # Status Card
        status_card = MaterialCard(self.theme, LayoutRegion("status", 0, 0, 0, 5), "System Status")
        mem_usage_mb = self.core_modules.content_manager.get_memory_usage() / (1024*1024)
        status_card.add_component(MaterialChip(self.theme, LayoutRegion("memory", 0, 0, 30, 1), f"Memory: {mem_usage_mb:.1f} MB"))
        self.add_component(status_card)
            
    def on_recent_file_select(self, index, item):
        """Handle recent file selection."""
        if 0 <= index < len(self.recent_files):
            file_path = self.recent_files[index]
            self.show_loading(f"Loading {Path(file_path).name}...")
            self.core_modules.load_epub(file_path)
            self.refresh_data()
                
    def save_current(self):
        """Save the current EPUB file."""
        if self.core_modules.epub_path:
            success, message = self.core_modules.epub_saver.save_epub(Path(self.core_modules.epub_path))
            self.show_snackbar(message)
            self.create_cards() # Refresh cards to remove "UNSAVED" chip
        else:
            self.show_snackbar("No file loaded to save.")
            
    def request_exit(self):
        """Request to exit the application, confirming if there are unsaved changes."""
        if self.core_modules.content_manager.has_modifications():
            self.show_confirm_dialog(
                "You have unsaved changes. Exit anyway?",
                on_confirm=lambda: self.screen_manager.stop()
            )
        else:
            self.screen_manager.stop()

    def draw(self):
        """Draw dashboard screen."""
        self.stdscr.erase()
        main_region = self.layout.get_region("main")
        if not main_region or not main_region.visible:
            return

        self.draw_header("EPUB Editor Pro Dashboard")
        
        y_pos = main_region.y + self.region.padding
        card_x = main_region.x + self.region.padding
        card_width = main_region.width - self.region.padding * 2
        
        for card in self.components:
            if isinstance(card, MaterialCard):
                card.region.x = card_x
                card.region.y = y_pos
                card.region.width = card_width
                
                # Check if card fits before drawing
                if y_pos + card.region.height < main_region.y + main_region.height:
                    card.draw(self.stdscr)
                    y_pos += card.region.height + 1 # Add spacing
                
        self.draw_footer("1-5, Q: Actions | ↑↓: Select | Enter: Action")