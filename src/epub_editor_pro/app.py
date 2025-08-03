#!/usr/bin/env python3

import curses
import time
import os
import traceback
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Any, Optional, Tuple

# All imports must now be relative to the package root
from .core.epub_loader import EPUBLoader
from .core.content_manager import ContentManager
from .core.search_engine import SearchEngine
from .core.replace_engine import ReplaceEngine
from .core.epub_saver import EPUBSaver
from .navigation_system.screen_manager import ScreenManager
from .ui.layout_manager import LayoutManager
from .ui.color_manager import ColorManager
from .navigation_system.input_handler import InputHandler
from .screens.dashboard import DashboardScreen
from .screens.file_manager import FileManagerScreen
from .screens.search import SearchScreen
from .screens.search_results import SearchResultsScreen
from .screens.replace import ReplaceScreen
from .screens.batch_operations import BatchOperationsScreen
# from .screens.settings import SettingsScreen
# from .screens.help import HelpScreen

@dataclass
class CoreModules:
    """A container for all core logic and shared state."""
    layout: LayoutManager
    epub_path: Optional[str] = None
    last_search_results: List[Any] = field(default_factory=list)
    content_manager: ContentManager = field(default_factory=ContentManager)
    search_engine: SearchEngine = field(init=False)
    replace_engine: ReplaceEngine = field(init=False)
    epub_saver: EPUBSaver = field(init=False)

    def __post_init__(self):
        # Engines depend on the content_manager, so initialize them here.
        self.search_engine = SearchEngine(self.content_manager)
        self.replace_engine = ReplaceEngine(self.content_manager)
        self.epub_saver = EPUBSaver(self.content_manager)

    def load_epub(self, file_path: str) -> Tuple[bool, str]:
        """Helper method to load an EPUB, resetting the core state."""
        self.content_manager = ContentManager()
        self.__post_init__() # Re-initialize engines with the new manager

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
        theme = ColorManager(stdscr)
        input_handler = InputHandler(stdscr)
        layout = LayoutManager(stdscr)
        self.core_modules = CoreModules(layout=layout)
        self.screen_manager = ScreenManager(stdscr, theme, input_handler, self.core_modules)
        self.register_screens()
        
    def register_screens(self):
        """Register all application screens."""
        self.screen_manager.screen_classes = {
            "dashboard": DashboardScreen, "file_manager": FileManagerScreen,
            "search": SearchScreen, "search_results": SearchResultsScreen,
            "replace": ReplaceScreen, "batch_ops": BatchOperationsScreen,
        }

    def run(self):
        """Main application loop."""
        self.stdscr.nodelay(True)
        self.screen_manager.navigate_to("dashboard")
        
        while self.screen_manager.running:
            try:
                self.screen_manager.handle_input()
                self.screen_manager.update()
                self.screen_manager.draw()
                self.stdscr.refresh()
                time.sleep(1 / 30) # 30 FPS target
            except Exception as e:
                self.handle_error(e)
        self.exit_app()

    def handle_error(self, exception):
        self.screen_manager.running = False # Stop the loop on error
        # Error logging should go to the user's data directory
        with open("logs/runtime_error.log", "w") as f:
            f.write(f"Timestamp: {datetime.now()}\n")
            traceback.print_exc(file=f)

    def exit_app(self):
        curses.nocbreak(); self.stdscr.keypad(False); curses.echo(); curses.endwin()

def start_app(stdscr):
    """Main application logic, wrapped by curses."""
    curses.curs_set(0)
    app = EPUBEditorPro(stdscr)
    app.run()

def start():
    """The application entry point defined in pyproject.toml."""
    # User data should be stored in a consistent, user-owned location.
    home_dir = Path.home()
    app_data_dir = home_dir / ".config" / "epub_editor_pro"
    
    for dir_name in ["config", "templates", "history", "backups", "logs", "state_cache"]:
        (app_data_dir / dir_name).mkdir(parents=True, exist_ok=True)
    
    os.chdir(app_data_dir)

    try:
        curses.wrapper(start_app)
    except Exception as e:
        print("--- EPUB Editor Pro failed to start ---")
        print(f"ERROR: {e}")
        with open("logs/startup_error.log", "w") as f:
            traceback.print_exc(file=f)
