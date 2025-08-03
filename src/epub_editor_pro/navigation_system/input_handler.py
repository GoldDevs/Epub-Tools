# epub_editor_pro/navigation_system/input_handler.py

import curses
import time
import json
from collections import deque
from pathlib import Path
from typing import Dict, Callable, List, Tuple, Optional

class InputHandler:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        # The primary store for key actions, separated by context
        self.contextual_actions: Dict[str, Dict[int, Callable]] = {"global": {}}
        self.current_context = "global"
        
        # Gesture handling
        self.gesture_map: Dict[str, Callable] = {}
        self.touch_start: Optional[Tuple[int, int]] = None
        self.touch_start_time: float = 0
        self.gesture_threshold = 5
        self.long_press_time = 0.5
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        
        # Key repeat handling
        self.last_key_press_time: float = 0
        self.last_key_pressed: int = -1
        self.key_repeat_delay = 0.4
        self.key_repeat_interval = 0.08

        self.input_history = deque(maxlen=100)
        
    def register_key(self, key: int, action: Callable, context: str = "global"):
        """Register a key action for a specific context."""
        if context not in self.contextual_actions:
            self.contextual_actions[context] = {}
        self.contextual_actions[context][key] = action
        
    def register_gesture(self, gesture: str, action: Callable):
        """Register a gesture action."""
        self.gesture_map[gesture] = action
        
    def set_context(self, context: str):
        """Set the current input context."""
        self.current_context = context
        
    def process_input(self):
        """Process pending keyboard and mouse/touch input in a non-blocking way."""
        # --- Keyboard Input ---
        key = self.stdscr.getch() # This is non-blocking due to nodelay(True) in main loop

        if key != -1:
            self.last_key_press_time = time.time()
            self.last_key_pressed = key
            self._execute_key_action(key)
        elif self.last_key_pressed != -1:
            # --- Key Repeat Logic ---
            now = time.time()
            # Check if we should start repeating
            if now - self.last_key_press_time > self.key_repeat_delay:
                # Check if it's time for the next repeat based on the interval
                time_since_last_action = now - self.input_history[-1][1] if self.input_history else self.key_repeat_interval
                if time_since_last_action >= self.key_repeat_interval:
                    self._execute_key_action(self.last_key_pressed)
        
        # --- Mouse/Touch Input ---
        self._process_touch_events()

    def _execute_key_action(self, key: int):
        """Finds and executes the action for a given key."""
        self.input_history.append((key, time.time()))

        action = self.contextual_actions.get(self.current_context, {}).get(key)
        if action is None:
            action = self.contextual_actions.get("global", {}).get(key)
        
        if action:
            action()
            
    def map_gesture(self, start: Tuple[int, int], end: Tuple[int, int], duration: float) -> str:
        """Map touch coordinates to a gesture string."""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # Check for tap or long press
        if abs(dx) < self.gesture_threshold and abs(dy) < self.gesture_threshold:
            return "long_press" if duration > self.long_press_time else "tap"
        
        # Check for swipe
        if abs(dx) > abs(dy):
            return "swipe_right" if dx > 0 else "swipe_left"
        else:
            return "swipe_down" if dy > 0 else "swipe_up"
                
    def _process_touch_events(self):
        """Process touch events non-blockingly."""
        try:
            # CRITICAL: getmouse() is blocking by default. We rely on the main loop's nodelay(True).
            mouse_event = self.stdscr.getmouse()
            
            # Unpack mouse event data
            _, x, y, _, bstate = mouse_event
            
            if bstate & curses.BUTTON1_PRESSED:
                self.touch_start = (x, y)
                self.touch_start_time = time.time()
            elif bstate & curses.BUTTON1_RELEASED and self.touch_start:
                duration = time.time() - self.touch_start_time
                gesture = self.map_gesture(self.touch_start, (x, y), duration)
                if gesture in self.gesture_map:
                    self.gesture_map[gesture]() # Call the registered action
                self.touch_start = None
        except curses.error:
            # This exception is raised if no mouse event is in the queue, which is normal.
            self.touch_start = None # Invalidate touch start on error
            pass
            
    def save_keymap(self, file_path: Path, action_registry: Dict[str, Callable]):
        """Save the current key mapping to a file."""
        serializable_map = {}
        for context, actions in self.contextual_actions.items():
            # Invert the action registry to find names from functions
            name_map = {v: k for k, v in action_registry.items()}
            serializable_map[context] = {key: name_map.get(func) for key, func in actions.items() if name_map.get(func)}
        
        try:
            with file_path.open('w') as f:
                json.dump(serializable_map, f, indent=2)
            return True
        except OSError:
            return False
            
    def load_keymap(self, file_path: Path, action_registry: Dict[str, Callable]):
        """Load a key mapping from a file."""
        if not file_path.exists(): return False
        try:
            with file_path.open('r') as f:
                config = json.load(f)
            
            self.contextual_actions = {"global": {}}
            for context, keymap in config.items():
                for key_str, action_name in keymap.items():
                    if action_name in action_registry:
                        self.register_key(int(key_str), action_registry[action_name], context)
            return True
        except (OSError, json.JSONDecodeError, KeyError):
            return False
            
    def enable_swipe_navigation(self, left: Optional[Callable] = None, right: Optional[Callable] = None, up: Optional[Callable] = None, down: Optional[Callable] = None):
        """Convenience method to register common swipe gestures."""
        if left: self.register_gesture("swipe_left", left)
        if right: self.register_gesture("swipe_right", right)
        if up: self.register_gesture("swipe_up", up)
        if down: self.register_gesture("swipe_down", down)