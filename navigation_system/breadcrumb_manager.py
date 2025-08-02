import curses
from collections import deque
from pathlib import Path
from typing import List, Tuple, Dict, Callable, Optional
from ..ui.material_components import MaterialTheme, MaterialChip

class BreadcrumbManager:
    def __init__(self, theme: MaterialTheme, max_items: int = 5, max_length: int = 15):
        self.theme = theme
        self.breadcrumbs = deque(maxlen=max_items)
        self.max_length = max_length
        self.chip_components = []
        self.click_handlers = {}
        self.home_icon = "🏠"
        self.separator = "›"
        self.current_path = []
        self.custom_names = {}
        self.history_file = Path("breadcrumb_history.json")
        self.load_history()
        
    def add_crumb(self, name: str, path: str, data: Any = None):
        """Add a new breadcrumb to the trail"""
        # Truncate long names for mobile display
        display_name = self._truncate_name(name)
        
        # Remove duplicate consecutive crumbs
        if self.breadcrumbs and self.breadcrumbs[-1][1] == path:
            return
            
        self.breadcrumbs.append((display_name, path, data))
        self.current_path = self._path_to_list(path)
        self._create_chips()
        self.save_history()
        
    def go_back(self, steps: int = 1):
        """Navigate back in history"""
        if steps >= len(self.breadcrumbs):
            self.breadcrumbs.clear()
            return None
            
        # Remove current crumbs
        for _ in range(steps):
            if self.breadcrumbs:
                self.breadcrumbs.pop()
                
        # Return target crumb
        if self.breadcrumbs:
            self._create_chips()
            self.save_history()
            return self.breadcrumbs[-1]
        return None
        
    def get_current_path(self) -> str:
        """Get current path as string"""
        return "/".join(self.current_path)
        
    def get_full_trail(self) -> List[Tuple[str, str]]:
        """Get full breadcrumb trail"""
        return list(self.breadcrumbs)
        
    def set_custom_name(self, path: str, name: str):
        """Set a custom display name for a path"""
        self.custom_names[path] = name
        
    def reset_trail(self):
        """Reset breadcrumb trail"""
        self.breadcrumbs.clear()
        self.current_path = []
        self._create_chips()
        
    def draw(self, stdscr, y: int, x: int):
        """Draw breadcrumbs at specified position"""
        if not self.chip_components:
            return
            
        current_x = x
        for chip in self.chip_components:
            # Only draw if space available
            if current_x + chip.region.width < stdscr.getmaxyx()[1] - 2:
                chip.region.x = current_x
                chip.region.y = y
                chip.draw(stdscr)
                current_x += chip.region.width + 1
                
    def handle_click(self, y: int, x: int) -> Optional[str]:
        """Handle click event on breadcrumbs"""
        for chip, (_, path, _) in zip(self.chip_components, self.breadcrumbs):
            if (chip.region.y <= y < chip.region.y + chip.region.height and
                chip.region.x <= x < chip.region.x + chip.region.width):
                return path
        return None
        
    def register_click_handler(self, path: str, handler: Callable):
        """Register handler for breadcrumb click"""
        self.click_handlers[path] = handler
        
    def save_history(self):
        """Save breadcrumb history to file"""
        history = {
            "trail": list(self.breadcrumbs),
            "custom_names": self.custom_names,
            "current_path": self.current_path
        }
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except OSError:
            pass
            
    def load_history(self):
        """Load breadcrumb history from file"""
        if not self.history_file.exists():
            return
            
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
                
            self.breadcrumbs = deque(history.get("trail", []), maxlen=self.breadcrumbs.maxlen)
            self.custom_names = history.get("custom_names", {})
            self.current_path = history.get("current_path", [])
            self._create_chips()
        except (OSError, json.JSONDecodeError):
            pass
            
    def _create_chips(self):
        """Create chip components for breadcrumbs"""
        self.chip_components = []
        
        # Always add home chip
        home_chip = MaterialChip(self.theme, LayoutRegion("home", 0, 0, len(self.home_icon) + 4, 1), 
                                self.home_icon, None)
        self.chip_components.append(home_chip)
        
        # Add path chips
        for name, path, _ in self.breadcrumbs:
            # Use custom name if set
            display_name = self.custom_names.get(path, name)
            truncated_name = self._truncate_name(display_name)
            
            # Create chip with click handler
            chip = MaterialChip(self.theme, LayoutRegion(path, 0, 0, len(truncated_name) + 4, 1),
                               truncated_name, None)
            self.chip_components.append(chip)
            
    def _truncate_name(self, name: str) -> str:
        """Truncate long names for mobile display"""
        if len(name) > self.max_length:
            return name[:self.max_length-1] + "…"
        return name
        
    def _path_to_list(self, path: str) -> List[str]:
        """Convert path string to list of components"""
        return path.strip('/').split('/')
        
    def get_path_components(self) -> List[Tuple[str, str]]:
        """Get current path as list of (name, path) tuples"""
        components = []
        current_path = ""
        
        for part in self.current_path:
            current_path += "/" + part
            display_name = self.custom_names.get(current_path, part)
            components.append((display_name, current_path))
            
        return components
        
    def navigate_to_path(self, path: str):
        """Navigate to a specific path in the hierarchy"""
        path_list = self._path_to_list(path)
        self.current_path = path_list
        
        # Rebuild breadcrumbs for this path
        self.breadcrumbs.clear()
        current_path = ""
        
        for part in path_list:
            current_path += "/" + part
            display_name = self.custom_names.get(current_path, part)
            self.add_crumb(display_name, current_path)
            
    def get_short_path(self) -> str:
        """Get shortened path for mobile display"""
        if not self.current_path:
            return "Home"
            
        if len(self.current_path) <= 2:
            return "/".join(self.current_path)
            
        return f"{self.current_path[0]}/.../{self.current_path[-1]}"
        
    def create_context_menu(self, y: int, x: int) -> List[Tuple[str, Callable]]:
        """Create context menu for breadcrumb interactions"""
        menu = []
        
        # Add option for each crumb
        for name, path, _ in self.breadcrumbs:
            menu.append((f"Go to {name}", lambda p=path: self.click_handlers.get(p, lambda: None)()))
            
        # Add management options
        menu.append(("Clear History", self.reset_trail))
        menu.append(("Set Custom Name", self._set_custom_name_dialog))
        menu.append(("Save History", self.save_history))
        
        return menu
        
    def _set_custom_name_dialog(self):
        """Show dialog to set custom name (stub)"""
        # Implementation would show a text input dialog
        pass
        
    def get_recent_paths(self, max_items: int = 5) -> List[str]:
        """Get recently visited paths"""
        return [path for _, path, _ in list(self.breadcrumbs)[-max_items:]]
        
    def get_most_visited(self, max_items: int = 5) -> List[Tuple[str, int]]:
        """Get most frequently visited paths"""
        path_counts = {}
        for _, path, _ in self.breadcrumbs:
            path_counts[path] = path_counts.get(path, 0) + 1
            
        return sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:max_items]