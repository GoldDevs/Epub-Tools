import curses
import time
import pickle
from pathlib import Path
from typing import Dict, List, Callable, Optional, Any, Type
from .input_handler import InputHandler
from ..ui.layout_manager import LayoutManager
from ..ui.material_components import MaterialTheme
from ..screens import (DashboardScreen, FileManagerScreen, SearchScreen, 
                      SearchResultsScreen, ReplaceScreen, BatchOperationsScreen,
                      SettingsScreen, HelpScreen)

class ScreenState:
    def __init__(self, screen_name: str, data: Any = None):
        self.screen_name = screen_name
        self.data = data
        self.timestamp = time.time()

class ScreenManager:
    def __init__(self, stdscr, theme: MaterialTheme, input_handler: InputHandler):
        self.stdscr = stdscr
        self.theme = theme
        self.input_handler = input_handler
        self.layout = LayoutManager(stdscr)
        self.screen_stack: List[ScreenState] = []
        self.screen_cache: Dict[str, Any] = {}
        self.current_screen = None
        self.screen_classes: Dict[str, Type] = {
            "dashboard": DashboardScreen,
            "file_manager": FileManagerScreen,
            "search": SearchScreen,
            "search_results": SearchResultsScreen,
            "replace": ReplaceScreen,
            "batch_ops": BatchOperationsScreen,
            "settings": SettingsScreen,
            "help": HelpScreen
        }
        self.transition_in_progress = False
        self.state_dir = Path("state_cache")
        self.state_dir.mkdir(exist_ok=True)
        self.init_navigation_shortcuts()
        
    def init_navigation_shortcuts(self):
        """Register common navigation shortcuts"""
        self.input_handler.register_key(curses.KEY_BACKSPACE, self.go_back, "global")
        self.input_handler.register_key(27, self.go_back)  # ESC key
        self.input_handler.register_key(ord('b'), self.go_back)
        
        # Swipe gestures for navigation
        self.input_handler.enable_swipe_navigation(
            left_action=self.go_back,
            right_action=None,  # Not used for back navigation
            up_action=self.scroll_up,
            down_action=self.scroll_down
        )
        
    def navigate_to(self, screen_name: str, data: Any = None, save_current: bool = True):
        """Navigate to a new screen"""
        if self.transition_in_progress:
            return
            
        self.transition_in_progress = True
        
        # Save current screen state
        if save_current and self.current_screen:
            self.cache_screen_state()
            
        # Push current state to stack
        if self.current_screen:
            self.screen_stack.append(ScreenState(
                self.current_screen.name,
                self.current_screen.get_state()
            ))
            
        # Clear input queue during transition
        self.input_handler.input_queue.clear()
        
        # Load new screen
        self.load_screen(screen_name, data)
        self.transition_in_progress = False
        
    def load_screen(self, screen_name: str, data: Any = None):
        """Load a screen by name"""
        # Check cache first
        if screen_name in self.screen_cache:
            self.current_screen = self.screen_cache[screen_name]
            self.current_screen.on_resume(data)
            return
            
        # Create new screen instance
        if screen_name in self.screen_classes:
            screen_class = self.screen_classes[screen_name]
            self.current_screen = screen_class(
                self.stdscr,
                self.theme,
                self.layout,
                self.input_handler,
                self
            )
            self.current_screen.name = screen_name
            
            # Try to load saved state
            state = self.load_screen_state(screen_name)
            if state:
                self.current_screen.set_state(state)
                
            self.current_screen.on_create(data)
            self.screen_cache[screen_name] = self.current_screen
        else:
            # Fallback to dashboard
            self.navigate_to("dashboard")
            
        # Update input context
        self.input_handler.set_context(screen_name)
        
    def go_back(self):
        """Navigate back to previous screen"""
        if len(self.screen_stack) == 0 or self.transition_in_progress:
            return
            
        self.transition_in_progress = True
        
        # Cache current screen state
        self.cache_screen_state()
        
        # Get previous screen state
        prev_state = self.screen_stack.pop()
        
        # Load previous screen
        self.load_screen(prev_state.screen_name, prev_state.data)
        self.transition_in_progress = False
        
    def go_home(self):
        """Navigate to dashboard clearing history"""
        self.screen_stack.clear()
        self.navigate_to("dashboard", save_current=False)
        
    def scroll_up(self):
        """Scroll up in current screen"""
        if self.current_screen and hasattr(self.current_screen, 'scroll_up'):
            self.current_screen.scroll_up()
            
    def scroll_down(self):
        """Scroll down in current screen"""
        if self.current_screen and hasattr(self.current_screen, 'scroll_down'):
            self.current_screen.scroll_down()
            
    def cache_screen_state(self):
        """Save current screen state to cache"""
        if not self.current_screen:
            return
            
        # Get current state
        state = self.current_screen.get_state()
        if state:
            self.screen_cache[self.current_screen.name] = self.current_screen
            
        # Persist to disk
        self.save_screen_state(self.current_screen.name, state)
        
    def save_screen_state(self, screen_name: str, state: Any):
        """Save screen state to disk"""
        state_path = self.state_dir / f"{screen_name}.pkl"
        try:
            with open(state_path, 'wb') as f:
                pickle.dump(state, f)
        except OSError:
            pass
            
    def load_screen_state(self, screen_name: str) -> Optional[Any]:
        """Load screen state from disk"""
        state_path = self.state_dir / f"{screen_name}.pkl"
        if state_path.exists():
            try:
                with open(state_path, 'rb') as f:
                    return pickle.load(f)
            except (OSError, pickle.UnpicklingError):
                return None
        return None
        
    def clear_cache(self, screen_name: str = None):
        """Clear screen cache"""
        if screen_name:
            if screen_name in self.screen_cache:
                # Call cleanup method if exists
                if hasattr(self.screen_cache[screen_name], 'on_destroy'):
                    self.screen_cache[screen_name].on_destroy()
                del self.screen_cache[screen_name]
                
            # Delete state file
            state_path = self.state_dir / f"{screen_name}.pkl"
            if state_path.exists():
                state_path.unlink()
        else:
            # Clear all cached screens
            for name, screen in list(self.screen_cache.items()):
                if hasattr(screen, 'on_destroy'):
                    screen.on_destroy()
                del self.screen_cache[name]
                
            # Clear all state files
            for state_file in self.state_dir.glob("*.pkl"):
                state_file.unlink()
                
    def draw(self):
        """Draw current screen"""
        if not self.current_screen:
            return
            
        # Update layout if screen size changed
        if self.layout.needs_redraw():
            self.layout.update_layout()
            self.current_screen.on_resize()
            
        # Draw screen content
        self.current_screen.draw()
        
    def update(self):
        """Update current screen logic"""
        if self.current_screen and hasattr(self.current_screen, 'update'):
            self.current_screen.update()
            
    def handle_input(self):
        """Handle input for current screen"""
        if self.current_screen:
            # Process input through handler
            self.input_handler.process_input()
            
            # Pass to screen-specific handler
            if hasattr(self.current_screen, 'handle_input'):
                self.current_screen.handle_input()
                
    def get_current_screen_name(self) -> str:
        """Get name of current screen"""
        return self.current_screen.name if self.current_screen else ""
        
    def get_navigation_history(self) -> List[str]:
        """Get navigation history as screen names"""
        return [state.screen_name for state in self.screen_stack]
        
    def show_dialog(self, dialog_component):
        """Show a modal dialog"""
        # Save current screen reference
        self.screen_stack.append(ScreenState(
            self.current_screen.name,
            self.current_screen.get_state()
        ))
        
        # Create dialog screen
        self.current_screen = dialog_component
        self.layout.show_modal()
        
    def close_dialog(self):
        """Close current dialog"""
        if len(self.screen_stack) == 0:
            return
            
        # Restore previous screen
        prev_state = self.screen_stack.pop()
        self.load_screen(prev_state.screen_name, prev_state.data)
        self.layout.hide_modal()
        
    def preload_screen(self, screen_name: str):
        """Preload a screen in background"""
        if screen_name not in self.screen_cache and screen_name in self.screen_classes:
            screen_class = self.screen_classes[screen_name]
            screen = screen_class(
                self.stdscr,
                self.theme,
                self.layout,
                self.input_handler,
                self
            )
            screen.name = screen_name
            self.screen_cache[screen_name] = screen
            
    def get_screen_instance(self, screen_name: str) -> Optional[Any]:
        """Get screen instance by name"""
        return self.screen_cache.get(screen_name)
        
    def reset_navigation(self):
        """Reset navigation stack and cache"""
        self.screen_stack.clear()
        self.clear_cache()
        
    def save_navigation_state(self):
        """Save entire navigation state"""
        state = {
            "stack": [(s.screen_name, s.data) for s in self.screen_stack],
            "current": self.current_screen.name if self.current_screen else "",
            "current_data": self.current_screen.get_state() if self.current_screen else None
        }
        
        try:
            with open(self.state_dir / "navigation_state.pkl", 'wb') as f:
                pickle.dump(state, f)
        except OSError:
            pass
            
    def load_navigation_state(self) -> bool:
        """Load navigation state from disk"""
        state_path = self.state_dir / "navigation_state.pkl"
        if not state_path.exists():
            return False
            
        try:
            with open(state_path, 'rb') as f:
                state = pickle.load(f)
                
            # Restore stack
            self.screen_stack = [ScreenState(name, data) for name, data in state["stack"]]
            
            # Restore current screen
            if state["current"]:
                self.load_screen(state["current"], state["current_data"])
                
            return True
        except (OSError, pickle.UnpicklingError):
            return False