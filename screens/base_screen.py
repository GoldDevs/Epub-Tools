# epub_editor_pro/screens/base_screen.py

import curses
import time
from typing import Any, Dict, List, Optional, Callable

# Forward declarations for type hinting to avoid circular imports
if False:
    from ..navigation_system.screen_manager import ScreenManager
    from ..navigation_system.input_handler import InputHandler
    from ..ui.layout_manager import LayoutManager
    from ..ui.material_components import MaterialTheme

class BaseScreen:
    def __init__(self, stdscr: curses.window, theme: 'MaterialTheme', layout: 'LayoutManager', 
                input_handler: 'InputHandler', screen_manager: 'ScreenManager', core_modules: Any):
        self.stdscr = stdscr
        self.theme = theme
        self.layout = layout
        self.input_handler = input_handler
        self.screen_manager = screen_manager
        self.core_modules = core_modules
        self.name = "base"
        self.visible = True
        
        # Component and Focus Management
        self.components: List[Any] = []
        self.focusable_components: List[Any] = []
        self.focused_component_idx: int = -1
        
        # State and Lifecycle
        self.state: Dict[str, Any] = {}
        self.initialized = False

        # --- SCROLLING ATTRIBUTES (Merged from previous version) ---
        self.scroll_offset = 0
        self.content_height = 0
        self.max_scroll = 0
        
    def on_create(self, data: Any = None):
        """Called when screen is first created. Setup components and input here."""
        if not self.initialized:
            self.setup_components()
            self.update_focusable_components()
            self.setup_input()
            self.focus_first_component()
            self.initialized = True
        
    def on_resume(self, data: Any = None):
        """Called when returning to this screen. Refresh content."""
        self.input_handler.set_context(self.name)
        self.refresh_content()
        
    def on_pause(self):
        """Called when leaving this screen. Save important state."""
        self.save_state()
        
    def on_destroy(self):
        """Called when screen is being destroyed. Perform cleanup."""
        self.clear_components()
        
    def on_resize(self):
        """Called when screen size changes."""
        self.layout.update_layout()
        self.calculate_scroll_limit()
        self.refresh_content()
        
    # --- Methods to be overridden by subclasses ---
    def setup_components(self): pass
    def refresh_content(self): pass
    def get_state(self) -> Dict: 
        state = self.state.copy()
        state['scroll_offset'] = self.scroll_offset
        return state
    def set_state(self, state: Dict): 
        self.state = state
        self.scroll_offset = state.get('scroll_offset', 0)

    def setup_input(self):
        """(Override) Set up screen-specific input handlers."""
        # This provides default navigation behavior for all screens
        self.input_handler.register_key(curses.KEY_DOWN, self.navigate_components_or_scroll)
        self.input_handler.register_key(curses.KEY_UP, lambda: self.navigate_components_or_scroll(backward=True))
        self.input_handler.register_key(curses.KEY_NPAGE, lambda: self.scroll_down(5)) # Page Down
        self.input_handler.register_key(curses.KEY_PPAGE, lambda: self.scroll_up(5)) # Page Up

    def handle_input(self, key: int):
        """Passes input to the currently focused component. Called by the main loop."""
        focused_component = self.get_focused_component()
        if focused_component:
            # Let the component handle the key first
            if focused_component.handle_input(key):
                return
        
        # If component didn't handle it, use a global keymap for the screen
        if key in self.input_handler.contextual_actions.get(self.name, {}):
             self.input_handler.contextual_actions[self.name][key]()

    # --- Drawing Helpers ---
    def draw(self):
        """Draws all visible components on the screen."""
        if not self.visible:
            return
        
        self.stdscr.erase()
        for component in self.components:
            if component.visible:
                # Adjust component position for scrolling before drawing
                original_y = component.region.y
                component.region.y -= self.scroll_offset
                component.draw(self.stdscr)
                component.region.y = original_y # Restore original y for logic

    # --- SCROLLING LOGIC (Merged from previous version) ---
    def calculate_scroll_limit(self):
        """Calculate maximum scroll offset based on content and main region height."""
        main_region = self.layout.get_region("main")
        if not main_region:
            self.max_scroll = 0
            return
        
        region_height = main_region.height - (main_region.padding * 2)
        self.max_scroll = max(0, self.content_height - region_height)
        self.scroll_offset = min(self.scroll_offset, self.max_scroll)

    def scroll_up(self, lines=1):
        """Scroll content up."""
        self.scroll_offset = max(0, self.scroll_offset - lines)

    def scroll_down(self, lines=1):
        """Scroll content down."""
        self.calculate_scroll_limit() # Recalculate in case content changed
        self.scroll_offset = min(self.max_scroll, self.scroll_offset + lines)

    def navigate_components_or_scroll(self, backward: bool = False):
        """Smart navigation: moves between components, but scrolls the page if at the edge."""
        self.handle_component_navigation(backward)

    # --- Component & Focus Management ---
    def add_component(self, component: Any):
        self.components.append(component)

    def update_focusable_components(self):
        self.focusable_components = [c for c in self.components if hasattr(c, 'focused') and c.visible and c.enabled]

    def get_focused_component(self) -> Optional[Any]:
        if 0 <= self.focused_component_idx < len(self.focusable_components):
            return self.focusable_components[self.focused_component_idx]
        return None

    def focus_first_component(self):
        self.update_focusable_components()
        if self.focusable_components:
            if self.focused_component_idx != -1 and self.focused_component_idx < len(self.focusable_components):
                 self.focusable_components[self.focused_component_idx].focused = False
            self.focused_component_idx = 0
            self.focusable_components[0].focused = True

    def handle_component_navigation(self, backward: bool = False):
        self.update_focusable_components()
        if not self.focusable_components:
            # If no focusable components, fall back to scrolling
            self.scroll_down() if not backward else self.scroll_up()
            return

        current_focused = self.get_focused_component()
        if current_focused:
            current_focused.focused = False

        direction = -1 if backward else 1
        self.focused_component_idx = (self.focused_component_idx + direction) % len(self.focusable_components)
        self.focusable_components[self.focused_component_idx].focused = True

    def clear_components(self):
        self.components.clear()
        self.focusable_components.clear()
        self.focused_component_idx = -1
        
    def save_state(self):
        self.state = self.get_state()
        
    # --- UI Helpers (Delegated) ---
    def show_loading(self, message: str = "Loading..."):
        self.stdscr.erase()
        self.draw_header(message) # A simple header is a good loading indicator
        self.stdscr.refresh()
        
    def show_snackbar(self, message: str, style: str = "secondary", duration: int = 3):
        if self.screen_manager:
            self.screen_manager.show_snackbar(message, style, duration)

    def show_confirm_dialog(self, message: str, on_confirm: Callable, on_cancel: Optional[Callable] = None):
        if self.screen_manager:
            self.screen_manager.show_confirm_dialog(message, on_confirm, on_cancel)

    def navigate_to(self, screen_name: str, data: Any = None):
        if self.screen_manager:
            self.screen_manager.navigate_to(screen_name, data)