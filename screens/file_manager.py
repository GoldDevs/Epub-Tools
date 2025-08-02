# epub_editor_pro/screens/file_manager.py

import os
import curses
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from .base_screen import BaseScreen
from ..ui.material_components import MaterialList, MaterialButton, MaterialCard, MaterialTextField
from ..ui.layout_manager import LayoutRegion
from ..core.epub_loader import EPUBLoader

class FileManagerScreen(BaseScreen):
    def __init__(self, stdscr, theme, layout, input_handler, screen_manager, core_modules):
        super().__init__(stdscr, theme, layout, input_handler, screen_manager, core_modules)
        self.name = "file_manager"
        self.current_dir = Path.home()
        # This list stores the actual Path objects, parallel to the display list.
        self.path_items: List[Path] = []
        self.file_list: Optional[MaterialList] = None
        self.path_label: Optional[MaterialCard] = None
        self.favorites_dir = Path("history")
        self.favorites_file = self.favorites_dir / "favorites.json"
        self.favorites: List[Path] = []
        self.sort_by = "name"  # name, size, date
        self.sort_asc = True
        
    def on_create(self, data=None):
        """Initialize file manager and scan the initial directory."""
        self.favorites_dir.mkdir(exist_ok=True)
        self.load_favorites()
        if data and "path" in data and Path(data["path"]).is_dir():
            self.current_dir = Path(data["path"])
        
        super().on_create(data)
        self.scan_directory()
        
    def setup_components(self):
        """Create UI components for the file manager."""
        main_region = self.layout.get_region("main")
        if not main_region: return

        # Path display (non-editable for simplicity, acts as a label)
        self.path_label = MaterialCard(self.theme, LayoutRegion("path", main_region.y + 1, main_region.x + 2, 3, main_region.width - 4), "Current Path")
        self.add_component(self.path_label)

        # File list
        list_y = self.path_label.region.y + self.path_label.region.height
        list_height = main_region.height - (list_y - main_region.y) - 5
        self.file_list = MaterialList(self.theme, LayoutRegion("file_list", list_y, main_region.x + 2, list_height, main_region.width - 4), on_select=self.on_list_item_activated)
        self.add_component(self.file_list)
        
        # Action buttons
        button_y = self.file_list.region.y + self.file_list.region.height + 1
        self.add_component(MaterialButton(self.theme, LayoutRegion("btn_up", button_y, main_region.x + 2, 3, 10), "Up", self.go_up))
        self.add_component(MaterialButton(self.theme, LayoutRegion("btn_home", button_y, main_region.x + 13, 3, 10), "Home", self.go_home))
        self.add_component(MaterialButton(self.theme, LayoutRegion("btn_fav", button_y, main_region.x + 24, 3, 14), "☆ Favorite", self.toggle_favorite))

        self.update_path_display()
        
    def setup_input(self):
        """Set up input handlers for the file manager."""
        super().setup_input() # Inherit base navigation
        self.input_handler.register_key(ord('\n'), self.on_list_item_activated)
        self.input_handler.register_key(curses.KEY_ENTER, self.on_list_item_activated)
        self.input_handler.register_key(curses.KEY_RIGHT, self.on_list_item_activated)
        self.input_handler.register_key(curses.KEY_LEFT, self.go_up)
        self.input_handler.register_key(ord('f'), self.toggle_favorite)
        self.input_handler.set_context(self.name)
        
    def scan_directory(self):
        """Scan the current directory and prepare items for display."""
        try:
            # Use more efficient and modern Path.iterdir()
            items = list(self.current_dir.iterdir())
        except (PermissionError, FileNotFoundError) as e:
            items = []
            self.show_snackbar(f"Error: {e}", style="error")
        
        dirs = sorted([p for p in items if p.is_dir() and not p.name.startswith('.')], key=lambda p: p.name.lower())
        files = sorted([p for p in items if p.is_file() and p.suffix.lower() == '.epub'], key=lambda p: p.name.lower())
        
        # Build the list of Path objects that backs the display list
        self.path_items = []
        # Add parent directory if not at root
        if self.current_dir.parent != self.current_dir:
            self.path_items.append(self.current_dir.parent)
        self.path_items.extend(dirs)
        self.path_items.extend(files)

        self.refresh_list_items()
        self.update_path_display()
        
    def refresh_list_items(self):
        """Update the visual list component with formatted names."""
        if not self.file_list: return
        
        display_items = []
        for path in self.path_items:
            # Format display string based on type
            if path.is_dir():
                prefix = "📁"
                # Special case for parent directory
                if self.current_dir.parent == path and self.current_dir != path:
                    display_items.append(f"{prefix} ..")
                    continue
            else: # is_file
                prefix = "📄"
            
            is_fav = path in self.favorites
            fav_marker = "★ " if is_fav else ""
            display_items.append(f"{prefix} {fav_marker}{path.name}")
        
        self.file_list.items = display_items
        self.file_list.selected_index = 0 if display_items else -1
        self.file_list.scroll_offset = 0

    def update_path_display(self):
        """Update the path label card."""
        if self.path_label:
            # Truncate long paths for display
            path_str = str(self.current_dir)
            max_width = self.path_label.region.width - self.path_label.region.padding * 2
            if len(path_str) > max_width:
                path_str = "..." + path_str[-(max_width-3):]
            self.path_label.subtitle = path_str

    def on_list_item_activated(self, index=None, item=None):
        """Handle activating a list item (enter key or click)."""
        selected_idx = self.file_list.selected_index if self.file_list else -1
        if 0 <= selected_idx < len(self.path_items):
            selected_path = self.path_items[selected_idx]
            if selected_path.is_dir():
                self.current_dir = selected_path
                self.scan_directory()
            elif selected_path.is_file():
                self.load_file(selected_path)

    def load_file(self, file_path: Path):
        """Load the selected EPUB file."""
        self.show_loading(f"Loading {file_path.name}...")
        success, message = self.core_modules.load_epub(str(file_path))
        if success:
            # Add to recent files via dashboard method
            dashboard_screen = self.screen_manager.get_screen_instance("dashboard")
            if dashboard_screen:
                 dashboard_screen.save_recent_file(str(file_path))
            self.navigate_to("dashboard")
        else:
            self.show_snackbar(f"Error: {message}", style="error")

    def go_up(self):
        """Navigate to the parent directory."""
        if self.current_dir.parent != self.current_dir:
            self.current_dir = self.current_dir.parent
            self.scan_directory()

    def go_home(self):
        """Navigate to the user's home directory."""
        self.current_dir = Path.home()
        self.scan_directory()

    def toggle_favorite(self):
        """Add or remove the selected item from favorites."""
        if self.file_list and 0 <= self.file_list.selected_index < len(self.path_items):
            selected_path = self.path_items[self.file_list.selected_index]
            if selected_path in self.favorites:
                self.favorites.remove(selected_path)
                self.show_snackbar(f"Removed '{selected_path.name}' from favorites.")
            else:
                self.favorites.append(selected_path)
                self.show_snackbar(f"Added '{selected_path.name}' to favorites.")
            self.save_favorites()
            self.refresh_list_items() # Refresh list to show star icon

    def load_favorites(self):
        """Load favorite paths from a JSON file."""
        if not self.favorites_file.exists():
            return
        try:
            with self.favorites_file.open('r') as f:
                paths = json.load(f)
                # Ensure favorites still exist before adding
                self.favorites = [Path(p) for p in paths if Path(p).exists()]
        except (json.JSONDecodeError, OSError):
            self.favorites = [] # Reset on corrupt file

    def save_favorites(self):
        """Save the current list of favorites to a JSON file."""
        try:
            with self.favorites_file.open('w') as f:
                json.dump([str(p) for p in self.favorites], f)
        except OSError as e:
            self.show_snackbar(f"Error saving favorites: {e}", style="error")

    def draw(self):
        """Draw the file manager screen."""
        self.stdscr.erase()
        self.draw_header("File Manager")
        
        for component in self.components:
            component.draw(self.stdscr)

        self.draw_footer("↑↓: Select | →/Enter: Open | ←: Up | F: Favorite")