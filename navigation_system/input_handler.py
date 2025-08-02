import curses
import time
from collections import deque
from typing import Dict, Callable, List, Tuple, Optional

class InputHandler:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.key_map: Dict[int, Callable] = {}
        self.gesture_map: Dict[str, Callable] = {}
        self.input_queue = deque()
        self.last_key_time = 0
        self.combo_timeout = 0.3  # Seconds for combo detection
        self.touch_start = None
        self.touch_start_time = 0
        self.gesture_threshold = 5  # Minimum pixels for gesture
        self.long_press_time = 0.5  # Seconds for long press
        self.input_history = deque(maxlen=100)  # Store recent inputs
        self.accessibility_mode = False
        self.key_repeat_delay = 0.3
        self.key_repeat_interval = 0.05
        self.last_key_repeat = 0
        self.repeating_key = None
        self.contextual_actions: Dict[str, Dict[int, Callable]] = {}
        self.current_context = "global"
        
    def register_key(self, key: int, action: Callable, context: str = "global"):
        """Register a key action for a specific context"""
        if context not in self.contextual_actions:
            self.contextual_actions[context] = {}
        self.contextual_actions[context][key] = action
        
    def register_gesture(self, gesture: str, action: Callable):
        """Register a gesture action"""
        self.gesture_map[gesture] = action
        
    def set_context(self, context: str):
        """Set current input context"""
        self.current_context = context
        
    def enable_accessibility(self, enabled: bool):
        """Enable accessibility features"""
        self.accessibility_mode = enabled
        if enabled:
            self.key_repeat_delay = 0.5
            self.key_repeat_interval = 0.1
            self.gesture_threshold = 10  # Larger threshold for accessibility
            self.long_press_time = 1.0  # Longer press time
            
    def process_input(self):
        """Process all pending input"""
        self.stdscr.nodelay(True)
        while True:
            try:
                key = self.stdscr.getch()
                if key == -1:
                    break
                    
                current_time = time.time()
                self.input_history.append((key, current_time))
                
                # Handle key repeats
                if key == self.repeating_key:
                    if current_time - self.last_key_repeat > self.key_repeat_interval:
                        self.last_key_repeat = current_time
                        self._execute_key_action(key)
                else:
                    self.repeating_key = key
                    self.last_key_repeat = current_time
                    self._execute_key_action(key)
                    
            except curses.error:
                break
                
        # Handle key repeat timing
        if self.repeating_key and time.time() - self.last_key_time > self.key_repeat_delay:
            if time.time() - self.last_key_repeat > self.key_repeat_interval:
                self.last_key_repeat = time.time()
                self._execute_key_action(self.repeating_key)
                
        # Process touch input if any
        self._process_touch_events()
        
    def _execute_key_action(self, key: int):
        """Execute action for a key press"""
        self.last_key_time = time.time()
        
        # Check current context first
        if self.current_context in self.contextual_actions:
            if key in self.contextual_actions[self.current_context]:
                self.contextual_actions[self.current_context][key]()
                return
                
        # Check global context
        if key in self.contextual_actions.get("global", {}):
            self.contextual_actions["global"][key]()
            
    def get_key_combo(self) -> Optional[List[int]]:
        """Detect key combos within timeout"""
        if not self.input_history:
            return None
            
        current_time = time.time()
        combo = []
        
        # Work backwards through history
        for key, timestamp in reversed(self.input_history):
            if current_time - timestamp > self.combo_timeout:
                break
            combo.insert(0, key)
            
        return combo if len(combo) > 1 else None
        
    def map_gesture(self, start: Tuple[int, int], end: Tuple[int, int], duration: float) -> str:
        """Map touch coordinates to a gesture"""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # Determine primary direction
        if abs(dx) > abs(dy):
            # Horizontal gesture
            if abs(dx) < self.gesture_threshold:
                return "tap"
            elif dx > 0:
                return "swipe_right"
            else:
                return "swipe_left"
        else:
            # Vertical gesture
            if abs(dy) < self.gesture_threshold:
                if duration > self.long_press_time:
                    return "long_press"
                return "tap"
            elif dy > 0:
                return "swipe_down"
            else:
                return "swipe_up"
                
    def handle_touch_start(self, y: int, x: int):
        """Record touch start position and time"""
        self.touch_start = (x, y)
        self.touch_start_time = time.time()
        
    def handle_touch_end(self, y: int, x: int):
        """Process touch end as gesture"""
        if not self.touch_start:
            return
            
        end = (x, y)
        duration = time.time() - self.touch_start_time
        gesture = self.map_gesture(self.touch_start, end, duration)
        
        # Execute gesture action if registered
        if gesture in self.gesture_map:
            self.gesture_map[gesture](self.touch_start, end, duration)
            
        self.touch_start = None
        
    def _process_touch_events(self):
        """Process touch events if supported"""
        # Check if touch events are available
        if not hasattr(curses, 'BUTTON1_PRESSED'):
            return
            
        # Process all touch events
        while True:
            try:
                event = self.stdscr.get_touch_event()
                if event is None:
                    break
                    
                _, x, y, _, bstate = event
                
                # Handle different touch states
                if bstate & curses.BUTTON1_PRESSED:
                    self.handle_touch_start(y, x)
                elif bstate & curses.BUTTON1_RELEASED:
                    self.handle_touch_end(y, x)
                elif bstate & curses.BUTTON1_CLICKED:
                    # Treat as tap if no movement
                    if not self.touch_start:
                        self.handle_touch_start(y, x)
                    self.handle_touch_end(y, x)
                    
            except curses.error:
                break
                
    def get_key_mapping(self) -> Dict[int, str]:
        """Get current key mapping for display"""
        mapping = {}
        
        # Add global mappings
        if "global" in self.contextual_actions:
            for key, action in self.contextual_actions["global"].items():
                mapping[key] = self._key_name(key)
                
        # Add context-specific mappings
        if self.current_context in self.contextual_actions:
            for key, action in self.contextual_actions[self.current_context].items():
                mapping[key] = self._key_name(key)
                
        return mapping
        
    def _key_name(self, key: int) -> str:
        """Get display name for a key"""
        if 32 <= key <= 126:
            return chr(key)
        elif key == curses.KEY_UP:
            return "↑"
        elif key == curses.KEY_DOWN:
            return "↓"
        elif key == curses.KEY_LEFT:
            return "←"
        elif key == curses.KEY_RIGHT:
            return "→"
        elif key == curses.KEY_ENTER or key == 10:
            return "Enter"
        elif key == curses.KEY_BACKSPACE or key == 127:
            return "Backspace"
        elif key == curses.KEY_DC:
            return "Delete"
        elif key == 27:  # ESC
            return "ESC"
        elif key == 9:  # Tab
            return "Tab"
        else:
            return f"Key#{key}"
            
    def get_gesture_mapping(self) -> Dict[str, str]:
        """Get current gesture mapping for display"""
        return {gesture: gesture for gesture in self.gesture_map.keys()}
        
    def remap_key(self, old_key: int, new_key: int, context: str = "global"):
        """Remap a key to a different function"""
        if context in self.contextual_actions and old_key in self.contextual_actions[context]:
            action = self.contextual_actions[context].pop(old_key)
            self.contextual_actions[context][new_key] = action
            return True
        return False
        
    def save_keymap(self, file_path: str):
        """Save key mapping to file"""
        config = {
            "global": {key: action.__name__ for key, action in self.contextual_actions.get("global", {}).items()},
            "contexts": {}
        }
        
        for context, keymap in self.contextual_actions.items():
            if context == "global":
                continue
            config["contexts"][context] = {key: action.__name__ for key, action in keymap.items()}
            
        try:
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except OSError:
            return False
            
    def load_keymap(self, file_path: str, action_registry: Dict[str, Callable]):
        """Load key mapping from file"""
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
                
            # Clear existing keymaps
            self.contextual_actions.clear()
            
            # Load global mappings
            if "global" in config:
                for key_str, action_name in config["global"].items():
                    key = int(key_str)
                    if action_name in action_registry:
                        self.register_key(key, action_registry[action_name], "global")
                        
            # Load context mappings
            if "contexts" in config:
                for context, keymap in config["contexts"].items():
                    for key_str, action_name in keymap.items():
                        key = int(key_str)
                        if action_name in action_registry:
                            self.register_key(key, action_registry[action_name], context)
                            
            return True
        except (OSError, json.JSONDecodeError, KeyError):
            return False
            
    def get_input_history(self, max_items: int = 10) -> List[Tuple[str, float]]:
        """Get recent input history with timestamps"""
        history = []
        for key, timestamp in list(self.input_history)[-max_items:]:
            history.append((self._key_name(key), timestamp))
        return history
        
    def create_keyboard_shortcut(self, keys: List[int], action: Callable, context: str = "global"):
        """Create multi-key shortcut"""
        def shortcut_wrapper():
            # Check if the last keys match the shortcut
            last_keys = [key for key, _ in list(self.input_history)[-len(keys):]]
            if last_keys == keys:
                action()
                
        # Register the last key in the sequence as the trigger
        self.register_key(keys[-1], shortcut_wrapper, context)
        
    def enable_swipe_navigation(self, left_action: Callable, right_action: Callable, 
                                up_action: Callable, down_action: Callable):
        """Enable common swipe navigation gestures"""
        self.register_gesture("swipe_left", lambda s, e, d: left_action())
        self.register_gesture("swipe_right", lambda s, e, d: right_action())
        self.register_gesture("swipe_up", lambda s, e, d: up_action())
        self.register_gesture("swipe_down", lambda s, e, d: down_action())
        
    def enable_tap_actions(self, tap_action: Callable, long_press_action: Callable):
        """Enable tap and long press actions"""
        self.register_gesture("tap", lambda s, e, d: tap_action())
        self.register_gesture("long_press", lambda s, e, d: long_press_action())