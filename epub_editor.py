#!/usr/bin/env python3
"""
EPUB Editor Pro - Main Application
Terminal-based EPUB editor optimized for Android Termux
"""

import curses
import time
import traceback
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

# Core Modules
from .core.epub_loader import EPUBLoader
from .core.content_manager import ContentManager
from .core.search_engine import SearchEngine
from .core.replace_engine import ReplaceEngine
from .core.epub_saver import EPUBSaver

# UI and Navigation
from .navigation_system.screen_manager import ScreenManager
from .ui.layout_manager import LayoutManager
from .ui.color_manager import ColorManager
from .navigation_system.input_handler import InputHandler

# Screen Imports
from .screens.dashboard import DashboardScreen
from .screens.file_manager import FileManagerScreen
from .screens.search import SearchScreen
from .screens.search_results import SearchResultsScreen
from .screens.replace import ReplaceScreen
from .screens.batch_operations import BatchOperationsScreen
# from .screens.settings import SettingsScreen  # NOTE: This file is missing, commented out
# from .screens.help import HelpScreen      # NOTE: This file is missing, commented out

@dataclass
class CoreModules:
    """A container for all core logic and shared state."""
    # Core logic
    epub_loader: EPUBLoader
    content_manager: ContentManager
    search_engine: SearchEngine
    replace_engine: ReplaceEngine
    epub_saver: EPUBSaver
    
    # Shared UI managers
    layout: LayoutManager
    
    # Shared application state
    epub_path: Optional[str] = None
    last_search_results: List[Any] = None

    def load_epub(self, file_path: str) -> Tuple[bool, str]:
        """Helper method to load an EPUB into the core modules."""
        self.content_manager = ContentManager() # Reset content on new load
        self.search_engine = SearchEngine(self.content_manager)
        self.replace_engine = ReplaceEngine(self.content_manager)
        self.epub_saver = EPUBSaver(self.content_manager)

        loader = EPUBLoader()
        if not loader.load_epub(Path(file_path)):
            return False, "Failed to load EPUB content."
        
        for path, content in loader.content_map.items():
            self.content_manager.add_file(path, content)
            
        self.epub_path = file_path
        return True, f"Loaded {len(loader.content_map)} files."

class EPUBEditorPro:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        
        # Initialize framework components
        theme = ColorManager(stdscr)
        input_handler = InputHandler(stdscr)
        layout = LayoutManager(stdscr)

        # Create the central container for core modules and state
        self.core_modules = CoreModules(
            epub_loader=EPUBLoader(),
            content_manager=ContentManager(),
            search_engine=SearchEngine(ContentManager()), # Initial empty manager
            replace_engine=ReplaceEngine(ContentManager()),
            epub_saver=EPUBSaver(ContentManager()),
            layout=layout
        )

        # The ScreenManager gets the core modules to pass to screens
        self.screen_manager = ScreenManager(stdscr, theme, input_handler, self.core_modules)
        
        # Register all available screens with the manager
        self.register_screens()
        
    def register_screens(self):
        """Register all application screens."""
        self.screen_manager.screen_classes = {
            "dashboard": DashboardScreen,
            "file_manager": FileManagerScreen,
            "search": SearchScreen,
            "search_results": SearchResultsScreen,
            "replace": ReplaceScreen,
            "batch_ops": BatchOperationsScreen,
            # "settings": SettingsScreen, # Add when created
            # "help": HelpScreen,        # Add when created
        }

    def run(self):
        """Main application loop."""
        # Set curses to be non-blocking
        self.stdscr.nodelay(True)
        
        # Navigate to the initial screen
        self.screen_manager.navigate_to("dashboard")
        
        while self.screen_manager.running:
            try:
                # 1. Handle Input
                self.screen_manager.handle_input()
                
                # 2. Update State
                self.screen_manager.update()
                
                # 3. Draw UI
                # The manager handles drawing the active screen and any dialogs/snackbars
                self.screen_manager.draw()
                # The refresh call should only be here, in the main loop
                self.stdscr.refresh()
                
                # Sleep briefly to reduce CPU usage and achieve target frame rate
                time.sleep(1 / 30) # 30 FPS target
                
            except Exception as e:
                self.handle_error(e)

        self.exit_app()

    def handle_error(self, exception):
        """Handle application errors gracefully."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        with open(log_file, "w") as f:
            f.write("EPUB Editor Pro Crash Report\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Error: {str(exception)}\n\n")
            f.write("Traceback:\n")
            traceback.print_exc(file=f)

        # Attempt to show an error in the UI before exiting
        self.screen_manager.show_snackbar(f"FATAL ERROR: {exception}", style="error", duration=5)
        self.screen_manager.draw()
        self.stdscr.refresh()
        time.sleep(5)
        self.screen_manager.running = False

    def exit_app(self):
        """Cleanup before exiting."""
        # Restore terminal settings
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()

def main(stdscr):
    """Main application entry point, wrapped by curses."""
    curses.curs_set(0) # Hide the cursor
    
    app = EPUBEditorPro(stdscr)
    app.run()

if __name__ == "__main__":
    # Ensure necessary directories exist
    for dir_name in ["logs", "history", "templates", "backups", "state_cache"]:
        Path(dir_name).mkdir(exist_ok=True)
    
    try:
        curses.wrapper(main)
    except Exception as e:
        # This will catch errors during curses initialization
        print("--- EPUB Editor Pro failed to start ---")
        print(f"ERROR: {e}")
        print("A traceback has been saved to logs/startup_error.log")
        with open("logs/startup_error.log", "w") as f:
            traceback.print_exc(file=f)