# epub_editor_pro/navigation_system/breadcrumb_manager.py

import curses
import json
from pathlib import Path
from collections import deque
from typing import List, Tuple, Dict, Callable, Optional, Any

# Assume MaterialComponent and MaterialChip are in this path
from ..ui.material_components import MaterialComponent, MaterialChip, MaterialTheme
from ..ui.layout_manager import LayoutRegion

class BreadcrumbManager(MaterialComponent):
    def __init__(self, theme: 'MaterialTheme', region: LayoutRegion, on_crumb_click: Callable[[str], None]):
        super().__init__(theme, region)
        self.breadcrumbs: deque[Tuple[str, str, Any]] = deque(maxlen=7) # (name, path, data)
        self.chips: List[MaterialChip] = []
        self.on_crumb_click = on_crumb_click
        self.home_icon = "🏠"
        self.separator = "›"

    def add_crumb(self, name: str, path: str, data: Any = None):
        """Add a new breadcrumb to the trail."""
        # Avoid adding duplicate consecutive paths
        if self.breadcrumbs and self.breadcrumbs[-1][1] == path:
            return
            
        self.breadcrumbs.append((name, path, data))
        self._update_chips()
        
    def go_back(self, steps: int = 1) -> Optional[Tuple[str, str, Any]]:
        """
        Removes the last 'steps' crumbs and returns the new last crumb.
        Returns None if the trail becomes empty.
        """
        for _ in range(steps):
            if self.breadcrumbs:
                self.breadcrumbs.pop()
        
        self._update_chips()
        return self.breadcrumbs[-1] if self.breadcrumbs else None
        
    def reset(self):
        """Reset the breadcrumb trail completely."""
        self.breadcrumbs.clear()
        self._update_chips()

    def _update_chips(self):
        """Re-creates the chip components based on the current breadcrumbs."""
        self.chips.clear()
        
        # Home Chip
        home_chip = MaterialChip(self.theme, LayoutRegion("crumb_home", 0, 0, 1, len(self.home_icon) + 2), self.home_icon, lambda: self.on_crumb_click("/"))
        self.chips.append(home_chip)
        
        # Path Chips
        for i, (name, path, _) in enumerate(self.breadcrumbs):
            # Truncate long names
            display_name = name if len(name) <= 15 else name[:14] + "…"
            
            chip = MaterialChip(
                self.theme, 
                LayoutRegion(f"crumb_{i}", 0, 0, 1, len(display_name) + 4),
                f"{self.separator} {display_name}", 
                # Use a lambda to capture the correct path for the click handler
                lambda p=path: self.on_crumb_click(p)
            )
            self.chips.append(chip)
            
    def draw(self, stdscr):
        """Draws the breadcrumb chips horizontally within the component's region."""
        if not self.visible:
            return

        x, y, width, _ = self.region.x, self.region.y, self.region.width, self.region.height
        current_x = x
        
        for chip in self.chips:
            chip_width = chip.region.width
            # Check if the chip will fit in the remaining space
            if current_x + chip_width < x + width:
                chip.region.x = current_x
                chip.region.y = y
                chip.draw(stdscr)
                current_x += chip_width
            else:
                # No more space, stop drawing chips
                break
                
    def handle_input(self, key: Any) -> bool:
        """Handle mouse clicks to see if a breadcrumb chip was clicked."""
        if not isinstance(key, tuple) or key[0] != curses.KEY_MOUSE:
            return False

        _, mx, my, _, bstate = key
        
        if bstate & curses.BUTTON1_CLICKED:
            for chip in self.chips:
                cx, cy, cw, ch = chip.region.x, chip.region.y, chip.region.width, chip.region.height
                if cy <= my < cy + ch and cx <= mx < cx + cw:
                    if chip.on_click:
                        chip.on_click()
                        return True # Input was handled
        return False