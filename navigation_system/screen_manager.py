# epub_editor_pro/navigation_system/screen_manager.py

import curses
import time
from pathlib import Path
from typing import Dict, List, Callable, Optional, Any, Type

# Import components and base screen for internal use
from ..ui.material_components import MaterialSnackbar, MaterialCard, MaterialButton
from ..screens.base_screen import BaseScreen

# Forward declarations for type hinting to avoid circular imports
if False:
    from .input_handler import InputHandler
    from ..ui.layout_manager import LayoutManager
    from ..ui.material_components import MaterialTheme

class ScreenManager:
    def __init__(self, stdscr, theme: 'MaterialTheme', input_handler: 'InputHandler', core_modules: Any):
        self.stdscr = stdscr
        self.theme = theme
        self.input_handler = input_handler
        self.core_modules = core_modules
        self.layout = self.core_modules.layout
        
        self.screen_cache: Dict[str, 'BaseScreen'] = {} # Cache to store screen instances
        self.screen_stack: List['BaseScreen'] = []
        self.current_screen: Optional['BaseScreen'] = None
        self.dialog_stack: List['BaseScreen'] = []
        
        self.screen_classes: Dict[str, Type['BaseScreen']] = {}
        self.snackbar: Optional['MaterialSnackbar'] = None
        self.running = True

    def stop(self):
        """Signals the main application loop to terminate."""
        self.running = False

    def navigate_to(self, screen_name: str, data: Any = None):
        """Navigate to a screen. Uses a cached instance or creates a new one."""
        if self.current_screen:
            if self.current_screen.name == screen_name: return # Avoid navigating to self
            self.current_screen.on_pause()
            self.screen_stack.append(self.current_screen)
            
        # Check cache for an existing screen instance
        if screen_name in self.screen_cache:
            self.current_screen = self.screen_cache[screen_name]
            self.current_screen.on_resume(data)
        else:
            self._load_screen(screen_name, data)
        
    def go_back(self):
        """Navigate back to the previous screen on the stack."""
        if not self.screen_stack:
            self.show_snackbar("No previous screen.", style="warning")
            return

        if self.current_screen:
            self.current_screen.on_pause()
            
        self.current_screen = self.screen_stack.pop()
        self.current_screen.on_resume()

    def _load_screen(self, screen_name: str, data: Any):
        """Instantiates, caches, and sets up a new screen."""
        if screen_name in self.screen_classes:
            screen_class = self.screen_classes[screen_name]
            instance = screen_class(
                self.stdscr, self.theme, self.layout, self.input_handler, self, self.core_modules
            )
            self.current_screen = instance
            self.screen_cache[screen_name] = instance # Add to cache
            instance.on_create(data)
        else:
            self.show_snackbar(f"Error: Screen '{screen_name}' not found!", style="error")

    def get_active_screen(self) -> Optional['BaseScreen']:
        """Returns the active dialog or the current screen."""
        return self.dialog_stack[-1] if self.dialog_stack else self.current_screen

    def handle_input(self):
        """CORRECTED: Delegates to the InputHandler, which then calls the active screen."""
        self.input_handler.process_input()
        
    def update(self):
        """Updates the logic of the active screen or dialog."""
        active_screen = self.get_active_screen()
        if active_screen and hasattr(active_screen, 'update'):
            active_screen.update()

    def draw(self):
        """Draws the UI. The main loop is responsible for refresh()."""
        # The active screen handles clearing its own area
        active_screen = self.get_active_screen()
        if active_screen:
            active_screen.draw()

        if self.snackbar and self.snackbar.visible:
            self.snackbar.draw(self.stdscr)

    def show_snackbar(self, message: str, style: str = "secondary", duration: int = 3):
        """Displays a global snackbar message."""
        from ..ui.material_components import MaterialSnackbar # Local import
        style_map = {"error": self.theme.ERROR, "warning": self.theme.WARNING, "success": self.theme.SUCCESS}
        style_id = style_map.get(style, self.theme.SECONDARY)
        self.snackbar = MaterialSnackbar(self.theme, message, duration, style_id)
        self.snackbar.show()

    def show_confirm_dialog(self, message: str, on_confirm: Callable, on_cancel: Optional[Callable] = None):
        """Shows a confirmation dialog by pushing it onto the dialog stack."""
        dialog_data = {"message": message, "on_confirm": on_confirm, "on_cancel": on_cancel}
        dialog = ConfirmDialogScreen(self.stdscr, self.theme, self.layout, self.input_handler, self, self.core_modules, dialog_data)
        dialog.on_create()
        self.dialog_stack.append(dialog)
        self.input_handler.set_context(dialog.name)

    def close_dialog(self):
        """Closes the topmost dialog."""
        if self.dialog_stack:
            self.dialog_stack.pop()
            active_screen = self.get_active_screen()
            if active_screen:
                self.input_handler.set_context(active_screen.name)

# --- Self-Contained Dialog Screen ---
# NOTE: In a larger project, this would be moved to its own file (e.g., screens/dialogs.py)
class ConfirmDialogScreen(BaseScreen):
    """A simple modal dialog for Yes/No confirmations."""
    def on_create(self, data=None):
        self.name = "confirm_dialog"
        self.message = data.get("message", "Are you sure?")
        self.on_confirm = data.get("on_confirm", lambda: None)
        self.on_cancel = data.get("on_cancel", lambda: None)
        super().on_create(data)

    def setup_components(self):
        h, w = self.stdscr.getmaxyx()
        dialog_h, dialog_w = 7, max(40, len(self.message) + 4)
        dialog_y, dialog_x = (h - dialog_h) // 2, (w - dialog_w) // 2
        
        region = self.layout.regions['modal'] = type("Region", (), {'y': dialog_y, 'x': dialog_x, 'height': dialog_h, 'width': dialog_w})()
        
        self.dialog_card = MaterialCard(self.theme, region, "Confirmation")
        self.confirm_btn = MaterialButton(self.theme, type("Region", (), {'y': region.y + 4, 'x': region.x + 5, 'height': 1, 'width': 8})(), "Confirm", self.confirm_action)
        self.cancel_btn = MaterialButton(self.theme, type("Region", (), {'y': region.y + 4, 'x': region.x + dialog_w - 13, 'height': 1, 'width': 8})(), "Cancel", self.cancel_action)
        
        self.add_component(self.dialog_card)
        self.add_component(self.confirm_btn)
        self.add_component(self.cancel_btn)

    def handle_input(self, key):
        if key == curses.KEY_LEFT or key == curses.KEY_RIGHT or key == 9: # Tab
            self.confirm_btn.focused, self.cancel_btn.focused = self.cancel_btn.focused, self.confirm_btn.focused
        elif self.confirm_btn.focused:
            self.confirm_btn.handle_input(key)
        elif self.cancel_btn.focused:
            self.cancel_btn.handle_input(key)

    def confirm_action(self):
        self.screen_manager.close_dialog()
        self.on_confirm()

    def cancel_action(self):
        self.screen_manager.close_dialog()
        if self.on_cancel: self.on_cancel()

    def draw(self):
        # Dim the background screen (optional, creates a modal effect)
        if self.screen_manager.current_screen:
            # This is a simple way to dim; a more advanced way would use color pairs
            self.stdscr.attron(curses.A_DIM)
            self.screen_manager.current_screen.draw()
            self.stdscr.attroff(curses.A_DIM)
        
        # Draw the dialog on top
        self.dialog_card.draw(self.stdscr)
        self.stdscr.addstr(self.dialog_card.region.y + 2, self.dialog_card.region.x + 2, self.message)
        self.confirm_btn.draw(self.stdscr)
        self.cancel_btn.draw(self.stdscr)