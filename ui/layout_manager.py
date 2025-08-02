import curses
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass

@dataclass
class LayoutRegion:
    name: str
    y: int
    x: int
    height: int
    width: int
    padding: int = 1
    visible: bool = True
    scroll_offset: int = 0
    content_height: int = 0

class LayoutManager:
    def __init__(self, stdscr: curses.window):
        self.stdscr = stdscr
        self.regions: Dict[str, LayoutRegion] = {}
        self.current_focus: Optional[str] = None
        self.last_size: Tuple[int, int] = (0, 0)
        self.orientation: str = "portrait"  # Mobile default
        self.header_height: int = 3
        self.footer_height: int = 2
        self.update_layout()
        
    def update_layout(self) -> None:
        """Update layout based on current screen size"""
        height, width = self.stdscr.getmaxyx()
        if (height, width) == self.last_size:
            return

        self.last_size = (height, width)
        
        # Determine orientation
        self.orientation = "portrait" if height > width * 1.2 else "landscape"
        
        # Clear existing regions
        self.regions.clear()
        
        # Define regions based on orientation
        if self.orientation == "portrait":
            self._create_portrait_layout(height, width)
            self.current_focus = "main" # Sensible default focus
        else:
            self._create_landscape_layout(height, width)
            self.current_focus = "left_panel" # Sensible default focus
        
    def _create_portrait_layout(self, height: int, width: int) -> None:
        """Create layout for portrait mode (mobile default)"""
        main_height = max(1, height - self.header_height - self.footer_height)
        
        self.regions["header"] = LayoutRegion("header", 0, 0, self.header_height, width)
        self.regions["main"] = LayoutRegion("main", self.header_height, 0, main_height, width)
        self.regions["footer"] = LayoutRegion("footer", height - self.footer_height, 0, self.footer_height, width)
        
        # Hidden panels by default
        self.regions["left_panel"] = LayoutRegion("left_panel", 0, 0, 0, 0, visible=False)
        self.regions["right_panel"] = LayoutRegion("right_panel", 0, 0, 0, 0, visible=False)
        self.regions["modal"] = LayoutRegion("modal", 0, 0, 0, 0, visible=False)
        
    def _create_landscape_layout(self, height: int, width: int) -> None:
        """Create layout for landscape mode"""
        left_width = int(width * 0.3)
        main_width = width - left_width
        panel_height = max(1, height - self.header_height - self.footer_height)

        self.regions["header"] = LayoutRegion("header", 0, 0, self.header_height, width)
        self.regions["left_panel"] = LayoutRegion("left_panel", self.header_height, 0, panel_height, left_width)
        self.regions["main"] = LayoutRegion("main", self.header_height, left_width, panel_height, main_width)
        self.regions["footer"] = LayoutRegion("footer", height - self.footer_height, 0, self.footer_height, width)

        # Hidden panels by default
        self.regions["right_panel"] = LayoutRegion("right_panel", 0, 0, 0, 0, visible=False)
        self.regions["modal"] = LayoutRegion("modal", 0, 0, 0, 0, visible=False)
        
    def get_region(self, name: str) -> Optional[LayoutRegion]:
        """Get layout region by name"""
        return self.regions.get(name)
        
    def get_content_area(self, region_name: str) -> Tuple[int, int, int, int]:
        """Get content area within a region (accounting for padding)"""
        region = self.get_region(region_name)
        if not region or not region.visible:
            return (0, 0, 0, 0)
            
        y = region.y + region.padding
        x = region.x + region.padding
        height = max(0, region.height - region.padding * 2)
        width = max(0, region.width - region.padding * 2)
        
        return (y, x, height, width)
        
    def get_max_scroll(self, region_name: str) -> int:
        """Get maximum scroll offset for a region"""
        region = self.get_region(region_name)
        if not region:
            return 0
            
        content_height = region.content_height
        _, _, height, _ = self.get_content_area(region_name)
        return max(0, content_height - height)
        
    def scroll_region(self, region_name: str, delta: int) -> None:
        """Scroll a region by delta lines"""
        region = self.get_region(region_name)
        if not region:
            return
            
        max_scroll = self.get_max_scroll(region_name)
        region.scroll_offset = max(0, min(max_scroll, region.scroll_offset + delta))
        
    def set_content_height(self, region_name: str, height: int) -> None:
        """Set content height for a scrollable region"""
        region = self.get_region(region_name)
        if region:
            region.content_height = height
            # Ensure scroll offset is within bounds
            self.scroll_region(region_name, 0) # This re-clamps the value
                
    def toggle_region_visibility(self, region_name: str, visible: Optional[bool] = None) -> None:
        """Toggle or set visibility of a region."""
        region = self.regions.get(region_name)
        if region:
            region.visible = not region.visible if visible is None else visible
    
    def show_modal(self, height_ratio: float = 0.5, width_ratio: float = 0.8) -> None:
        """Show a modal dialog, centered."""
        screen_height, screen_width = self.last_size
        modal_height = int(screen_height * height_ratio)
        modal_width = int(screen_width * width_ratio)
        modal_y = (screen_height - modal_height) // 2
        modal_x = (screen_width - modal_width) // 2

        self.regions["modal"] = LayoutRegion("modal", modal_y, modal_x, modal_height, modal_width, visible=True)
        self.set_focus("modal")
        
    def hide_modal(self) -> None:
        """Hide modal dialog."""
        if self.regions.get("modal"):
            self.regions["modal"].visible = False
            # Return focus to where it was before, or a default
            self.set_focus("main")

    def set_focus(self, region_name: str) -> bool:
        """Set focus to a specific region"""
        if region_name in self.regions and self.regions[region_name].visible:
            self.current_focus = region_name
            return True
        return False
        
    def get_focused_region(self) -> Optional[LayoutRegion]:
        """Get currently focused region"""
        return self.regions.get(self.current_focus) if self.current_focus else None
        
    def needs_redraw(self) -> bool:
        """Check if screen size has changed requiring redraw"""
        height, width = self.stdscr.getmaxyx()
        return (height, width) != self.last_size
        
    def draw_borders(self) -> None:
        """Draw borders around visible regions (for debugging)."""
        for name, region in self.regions.items():
            if region.visible and region.width > 0 and region.height > 0:
                try:
                    # Create a sub-window to safely draw the border
                    win = self.stdscr.subwin(region.height, region.width, region.y, region.x)
                    win.attron(curses.color_pair(1))
                    win.box()
                    win.addstr(0, 2, f" {name} ")
                    win.attroff(curses.color_pair(1))
                    win.noutrefresh() # Use noutrefresh for performance
                except curses.error:
                    # Ignore errors if window is too small
                    pass