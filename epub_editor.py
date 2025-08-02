#!/usr/bin/env python3
"""
EPUB Editor Pro - Main Application
Terminal-based EPUB editor optimized for Android Termux
"""

import os
import sys
import curses
import signal
import traceback
from pathlib import Path
from datetime import datetime
from navigation_system.screen_manager import ScreenManager
from ui.layout_manager import LayoutManager
from ui.color_manager import ColorManager
from navigation_system.input_handler import InputHandler
from core.epub_loader import EPUBLoader
from core.content_manager import ContentManager
from core.search_engine import SearchEngine
from core.replace_engine import ReplaceEngine
from core.epub_saver import EPUBSaver
from screens.dashboard import DashboardScreen
from screens.file_manager import FileManagerScreen
from screens.search import SearchScreen
from screens.search_results import SearchResultsScreen
from screens.replace import ReplaceScreen
from screens.batch_operations import BatchOperationsScreen
from screens.settings import SettingsScreen
from screens.help import HelpScreen

class EPUBEditorPro:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.start_time = time.time()
        
        # Initialize framework components
        self.theme = ColorManager(stdscr)
        self.layout = LayoutManager(stdscr)
        self.input_handler = InputHandler(stdscr)
        self.screen_manager = ScreenManager(stdscr, self.theme, self.input_handler)
        
        # Initialize core modules
        self.content_manager = ContentManager()
        self.epub_loader = EPUBLoader()
        self.search_engine = SearchEngine(self.content_manager)
        self.replace_engine = ReplaceEngine(self.content_manager)
        self.epub_saver = EPUBSaver(self.content_manager)
        
        # Application state
        self.epub_path = None
        self.modifications_made = False
        self.last_activity = time.time()
        self.idle_timeout = 300  # 5 minutes
        
        # Register screens
        self.register_screens()
        
        # Set initial screen
        self.screen_manager.navigate_to("dashboard")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
    def register_screens(self):
        """Register all application screens"""
        self.screen_manager.screen_classes = {
            "dashboard": DashboardScreen,
            "file_manager": FileManagerScreen,
            "search": SearchScreen,
            "search_results": SearchResultsScreen,
            "replace": ReplaceScreen,
            "batch_ops": BatchOperationsScreen,
            "settings": SettingsScreen,
            "help": HelpScreen
        }
        
    def load_epub(self, file_path):
        """Load an EPUB file"""
        try:
            # Validate EPUB
            if not self.epub_loader.validate_epub(Path(file_path)):
                return False, "Invalid EPUB file format"
                
            # Load content
            if not self.epub_loader.load_epub(Path(file_path)):
                return False, "Failed to load EPUB content"
                
            # Add files to content manager
            for file_path, content in self.epub_loader.content_map.items():
                self.content_manager.add_file(file_path, content)
                
            self.epub_path = file_path
            self.modifications_made = False
            return True, f"Loaded {len(self.epub_loader.content_map)} files"
        except Exception as e:
            return False, f"Error loading EPUB: {str(e)}"
            
    def save_epub(self, output_path=None):
        """Save EPUB file"""
        if not self.epub_path:
            return False, "No EPUB file loaded"
            
        if not self.modifications_made:
            return True, "No changes to save"
            
        success, message = self.epub_saver.save_epub(Path(self.epub_path), Path(output_path) if output_path else None)
        if success:
            self.modifications_made = False
        return success, message
        
    def search_text(self, pattern, case_sensitive=False, regex_mode=False, whole_words=False):
        """Search for text in EPUB"""
        if not self.content_manager.content_map:
            return [], "No EPUB content loaded"
            
        results = self.search_engine.search(
            pattern, 
            case_sensitive, 
            regex_mode, 
            whole_words
        )
        return results, f"Found {len(results)} matches"
        
    def replace_text(self, find_pattern, replace_pattern, case_sensitive=False, 
                   regex_mode=False, whole_words=False, replace_all=False):
        """Replace text in EPUB"""
        if not self.content_manager.content_map:
            return 0, "No EPUB content loaded"
            
        count = self.replace_engine.replace_text(
            find_pattern, 
            replace_pattern,
            case_sensitive,
            regex_mode,
            whole_words,
            replace_all
        )
        
        if count > 0:
            self.modifications_made = True
            
        return count, f"Made {count} replacements"
        
    def handle_signal(self, signum, frame):
        """Handle termination signals"""
        self.running = False
        if self.modifications_made:
            # Try to save before exiting
            self.save_epub()
        self.exit_app()
        
    def exit_app(self):
        """Cleanup before exiting"""
        # Save navigation state
        self.screen_manager.save_navigation_state()
        
        # Close any open files
        self.content_manager.clear()
        
        # Restore terminal settings
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        
    def run(self):
        """Main application loop"""
        last_frame_time = time.time()
        frame_interval = 0.1  # 10 FPS for mobile efficiency
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check for inactivity
                if current_time - self.last_activity > self.idle_timeout:
                    self.screen_manager.go_home()
                    self.last_activity = current_time
                
                # Process input
                self.input_handler.process_input()
                
                # Update screens
                if self.screen_manager.current_screen:
                    self.screen_manager.current_screen.update()
                
                # Draw if needed
                if current_time - last_frame_time > frame_interval:
                    self.screen_manager.draw()
                    self.stdscr.refresh()
                    last_frame_time = current_time
                
                # Sleep briefly to reduce CPU usage
                time.sleep(0.01)
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                # Handle and log unexpected errors
                self.handle_error(e)
                
    def handle_error(self, exception):
        """Handle application errors gracefully"""
        # Save error to log file
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        with open(log_file, "w") as f:
            f.write(f"EPUB Editor Pro Crash Report\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Error: {str(exception)}\n\n")
            f.write("Traceback:\n")
            traceback.print_exc(file=f)
            
        # Show error to user
        self.screen_manager.show_error_dialog(
            f"Application Error: {str(exception)}\n"
            f"Details saved to: {log_file}\n\n"
            "Press any key to continue..."
        )

def main(stdscr):
    """Main application entry point"""
    # Basic terminal setup
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()
    
    # Create application instance
    app = EPUBEditorPro(stdscr)
    
    # Run main loop
    app.run()

if __name__ == "__main__":
    # Create logs directory if not exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run application with curses wrapper
    try:
        curses.wrapper(main)
    except Exception as e:
        # Handle any top-level exceptions
        with open("logs/startup_error.log", "w") as f:
            f.write(f"EPUB Editor Pro Startup Error\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Error: {str(e)}\n\n")
            f.write("Traceback:\n")
            traceback.print_exc(file=f)
        
        print(f"Application failed to start: {str(e)}")
        print("Details saved to logs/startup_error.log")