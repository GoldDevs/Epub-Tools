import curses
import json
from pathlib import Path
from typing import Dict, Tuple, Optional, List

class ColorManager:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_theme_name = "material_dark"
        self.themes: Dict[str, Dict] = {}
        # Caching mechanism for (fg, bg) -> pair_id
        self.color_pair_cache: Dict[Tuple[int, int], int] = {}
        self.next_pair_id = 1  # Start custom color pairs from 1

        self.init_curses_colors()
        self.load_themes()
        self.set_theme(self.current_theme_name)
        
    def init_curses_colors(self):
        """Initialize basic color settings if supported."""
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
        
    def _get_or_create_pair(self, fg: int, bg: int) -> int:
        """
        Get the ID of an existing color pair or create a new one.
        This is the correct, safe way to manage color pairs.
        """
        if (fg, bg) in self.color_pair_cache:
            return self.color_pair_cache[(fg, bg)]

        if self.next_pair_id < curses.COLOR_PAIRS:
            pair_id = self.next_pair_id
            curses.init_pair(pair_id, fg, bg)
            self.color_pair_cache[(fg, bg)] = pair_id
            self.next_pair_id += 1
            return pair_id
        
        # Fallback to pair 0 (default) if we run out of pairs
        return 0

    def load_themes(self):
        """Load themes from configuration file."""
        config_path = Path("config/themes.json")
        if not config_path.exists():
            self.create_default_themes()
            return
            
        try:
            with open(config_path, 'r') as f:
                self.themes = json.load(f)
                
            if not isinstance(self.themes, dict) or not all("colors" in v for v in self.themes.values()):
                raise json.JSONDecodeError("Invalid theme structure", "", 0)

        except (json.JSONDecodeError, OSError) as e:
            # Don't overwrite user's file, just use defaults and log error
            print(f"Warning: Could not load themes from {config_path}: {e}. Using default themes.")
            self.create_default_themes(save_to_file=False)
            
    def create_default_themes(self, save_to_file: bool = True):
        """Create default themes if config is missing or invalid."""
        self.themes = {
            "material_dark": {
                "description": "Material Design Dark Theme",
                "colors": {
                    "primary": (curses.COLOR_CYAN, curses.COLOR_BLACK),
                    "secondary": (curses.COLOR_BLUE, curses.COLOR_BLACK),
                    "error": (curses.COLOR_RED, curses.COLOR_BLACK),
                    "warning": (curses.COLOR_YELLOW, curses.COLOR_BLACK),
                    "success": (curses.COLOR_GREEN, curses.COLOR_BLACK),
                    "surface": (curses.COLOR_WHITE, 234), # Dark grey background
                    "text_primary": (curses.COLOR_WHITE, -1),
                    "text_secondary": (curses.COLOR_CYAN, -1)
                }
            },
            "material_light": {
                "description": "Material Design Light Theme",
                "colors": {
                    "primary": (curses.COLOR_BLUE, curses.COLOR_WHITE),
                    "secondary": (curses.COLOR_CYAN, curses.COLOR_WHITE),
                    "error": (curses.COLOR_RED, curses.COLOR_WHITE),
                    "warning": (curses.COLOR_YELLOW, curses.COLOR_BLACK),
                    "success": (curses.COLOR_GREEN, curses.COLOR_WHITE),
                    "surface": (curses.COLOR_BLACK, 252), # Light grey background
                    "text_primary": (curses.COLOR_BLACK, -1),
                    "text_secondary": (curses.COLOR_BLUE, -1)
                }
            }
        }
        if save_to_file:
            self.save_themes()
        
    def save_themes(self):
        """Save themes to configuration file."""
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        try:
            with open(config_dir / "themes.json", 'w') as f:
                json.dump(self.themes, f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save themes file: {e}")
            
    def set_theme(self, theme_name: str):
        """Set current theme and initialize its color pairs."""
        if theme_name in self.themes:
            self.current_theme_name = theme_name
            theme = self.themes[theme_name]
            for color_name, (fg, bg) in theme.get("colors", {}).items():
                self._get_or_create_pair(fg, bg)
                
    def get_current_theme(self) -> Dict:
        """Get current theme configuration."""
        return self.themes.get(self.current_theme_name, {})
        
    def get_theme_names(self) -> List[str]:
        """Get available theme names."""
        return list(self.themes.keys())
        
    def get_color(self, color_name: str) -> int:
        """Get curses color pair for a semantic color name from the current theme."""
        theme = self.get_current_theme()
        if theme and color_name in theme.get("colors", {}):
            fg, bg = theme["colors"][color_name]
            pair_id = self._get_or_create_pair(fg, bg)
            return curses.color_pair(pair_id)

        # Fallback for missing colors in theme or missing theme
        fallback_map = {
            "primary": (curses.COLOR_WHITE, curses.COLOR_BLUE),
            "secondary": (curses.COLOR_BLACK, curses.COLOR_CYAN),
            "error": (curses.COLOR_WHITE, curses.COLOR_RED),
            "text_primary": (curses.COLOR_WHITE, -1),
        }
        fg, bg = fallback_map.get(color_name, (curses.COLOR_WHITE, -1))
        return curses.color_pair(self._get_or_create_pair(fg, bg))

    def get_highlight_color(self, color_name: str) -> int:
        """Get highlighted version of a color."""
        base_color = self.get_color(color_name)
        # A_REVERSE is a more reliable highlight than A_BOLD
        return base_color | curses.A_REVERSE
        
    def export_theme(self, theme_name: str, file_path: Path) -> bool:
        """Export theme to a file."""
        if theme_name not in self.themes:
            return False
            
        try:
            with open(file_path, 'w') as f:
                json.dump({theme_name: self.themes[theme_name]}, f, indent=2)
            return True
        except OSError:
            return False
            
    def import_theme(self, file_path: Path) -> bool:
        """Import theme from a file."""
        try:
            with open(file_path, 'r') as f:
                theme_data = json.load(f)

            if not isinstance(theme_data, dict) or len(theme_data) != 1:
                return False

            name, data = list(theme_data.items())[0]

            # Generate a unique name if it already exists
            new_name = name
            counter = 1
            while new_name in self.themes:
                new_name = f"{name}_{counter}"
                counter += 1
                
            self.themes[new_name] = data
            self.save_themes()
            self.set_theme(new_name) # Apply the newly imported theme
            return True
        except (OSError, json.JSONDecodeError, IndexError):
            return False