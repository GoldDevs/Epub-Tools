import curses
import time
from typing import List, Tuple, Dict, Optional, Callable
from .layout_manager import LayoutRegion

class MaterialTheme:
    PRIMARY = 1
    SECONDARY = 2
    ERROR = 3
    WARNING = 4
    SUCCESS = 5
    SURFACE = 6
    TEXT_PRIMARY = 7
    TEXT_SECONDARY = 8
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.init_colors()
        
    def init_colors(self):
        """Initialize color pairs for Material Design"""
        if not curses.has_colors():
            return
            
        curses.start_color()
        curses.use_default_colors()
        
        # Material Design color palette
        curses.init_pair(self.PRIMARY, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(self.SECONDARY, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(self.ERROR, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(self.WARNING, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(self.SUCCESS, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(self.SURFACE, curses.COLOR_WHITE, curses.COLOR_BLACK) # Dark theme surface
        curses.init_pair(self.TEXT_PRIMARY, curses.COLOR_WHITE, curses.COLOR_BLACK) # Dark theme text
        curses.init_pair(self.TEXT_SECONDARY, curses.COLOR_CYAN, curses.COLOR_BLACK) # Dark theme secondary text
        
    def get_color(self, color_id):
        """Get color pair for component"""
        return curses.color_pair(color_id)
        
    def get_highlight_color(self, color_id):
        """Get highlighted version of color"""
        return curses.color_pair(color_id) | curses.A_REVERSE

class MaterialComponent:
    def __init__(self, theme: MaterialTheme, region: LayoutRegion):
        self.theme = theme
        self.region = region
        self.visible = True
        self.focused = False
        self.enabled = True
        
    def draw(self, stdscr):
        """Base draw method (override in subclasses)"""
        pass
        
    def handle_input(self, key):
        """Handle input (override in subclasses)"""
        return False
        
    def get_content_area(self) -> Tuple[int, int, int, int]:
        """Get content area within region"""
        x = self.region.x + self.region.padding
        y = self.region.y + self.region.padding
        width = max(0, self.region.width - self.region.padding * 2)
        height = max(0, self.region.height - self.region.padding * 2)
        return x, y, width, height

class MaterialButton(MaterialComponent):
    def __init__(self, theme, region, text, on_click=None, style=MaterialTheme.PRIMARY):
        super().__init__(theme, region)
        self.text = text
        self.on_click = on_click
        self.style = style
        self.elevated = True
        
    def draw(self, stdscr):
        if not self.visible:
            return
            
        x, y, width, height = self.region.x, self.region.y, self.region.width, self.region.height
        if width < 2 or height < 1:
            return
            
        color = self.theme.get_highlight_color(self.style) if self.focused else self.theme.get_color(self.style)
        
        stdscr.attron(color)
        for row in range(y, y + height):
            stdscr.addstr(row, x, " " * width)
        stdscr.attroff(color)
            
        text_x = x + (width - len(self.text)) // 2
        text_y = y + (height - 1) // 2
        if text_x >= x and text_y >= y:
            stdscr.addstr(text_y, text_x, self.text, color)
            
    def handle_input(self, key):
        if not self.visible or not self.enabled or not self.focused:
            return False
            
        if key == ord('\n') or key == curses.KEY_ENTER:
            if self.on_click:
                self.on_click()
            return True
        return False

class MaterialCard(MaterialComponent):
    def __init__(self, theme, region, title="", subtitle=""):
        super().__init__(theme, region)
        self.title = title
        self.subtitle = subtitle
        self.content: List[MaterialComponent] = []
        self.header_color = MaterialTheme.PRIMARY
        
    def add_component(self, component):
        """Add child component to card"""
        self.content.append(component)
        
    def draw(self, stdscr):
        if not self.visible:
            return
        
        r_x, r_y, r_w, r_h = self.region.x, self.region.y, self.region.width, self.region.height
        if r_w <= 0 or r_h <= 0:
            return

        # Draw card background
        bg_color = self.theme.get_color(MaterialTheme.SURFACE)
        stdscr.attron(bg_color)
        for i in range(r_h):
            stdscr.addstr(r_y + i, r_x, ' ' * r_w)
        stdscr.attroff(bg_color)

        # Draw border manually
        stdscr.attron(self.theme.get_color(MaterialTheme.SECONDARY))
        # Corners
        stdscr.addch(r_y, r_x, curses.ACS_ULCORNER)
        stdscr.addch(r_y, r_x + r_w - 1, curses.ACS_URCORNER)
        stdscr.addch(r_y + r_h - 1, r_x, curses.ACS_LLCORNER)
        stdscr.addch(r_y + r_h - 1, r_x + r_w - 1, curses.ACS_LRCORNER)
        # Lines
        stdscr.hline(r_y, r_x + 1, curses.ACS_HLINE, r_w - 2)
        stdscr.hline(r_y + r_h - 1, r_x + 1, curses.ACS_HLINE, r_w - 2)
        stdscr.vline(r_y + 1, r_x, curses.ACS_VLINE, r_h - 2)
        stdscr.vline(r_y + 1, r_x + r_w - 1, curses.ACS_VLINE, r_h - 2)
        stdscr.attroff(self.theme.get_color(MaterialTheme.SECONDARY))

        # Draw header using the component's padding
        cx, cy, cw, ch = self.get_content_area()

        if self.title:
            header_text = f" {self.title} "
            stdscr.addstr(cy, cx, header_text, self.theme.get_color(self.header_color))
            
        if self.subtitle:
            sub_y = cy + (1 if self.title else 0)
            sub_text = f"{self.subtitle}"
            stdscr.addstr(sub_y, cx, sub_text, self.theme.get_color(MaterialTheme.TEXT_SECONDARY))
            
        # Draw content components
        content_y_offset = (2 if self.title and self.subtitle else 1 if self.title or self.subtitle else 0)
        content_y = cy + content_y_offset
        
        for component in self.content:
            # Position child components relative to the card's content area
            component.region.x = cx
            component.region.y = content_y
            component.region.width = cw
            # component.region.height is assumed to be set by the screen
            component.draw(stdscr)
            content_y += component.region.height # Move to next line
            
    def handle_input(self, key):
        if not self.visible:
            return False
            
        for component in self.content:
            if component.focused and component.handle_input(key):
                return True
        return False

class MaterialTextField(MaterialComponent):
    def __init__(self, theme, region, label="", value="", on_change=None):
        super().__init__(theme, region)
        self.label = label
        self.value = value
        self.on_change = on_change
        self.cursor_pos = len(value)
        
    def draw(self, stdscr):
        if not self.visible:
            return

        x, y, width, height = self.get_content_area()
        
        if self.label:
            stdscr.addstr(y - 1, x, self.label, self.theme.get_color(MaterialTheme.TEXT_SECONDARY))

        bg_color = self.theme.get_highlight_color(MaterialTheme.SURFACE) if self.focused else self.theme.get_color(MaterialTheme.SURFACE)
        stdscr.addstr(y, x, ' ' * width, bg_color)
        
        # Display text, handling scrolling
        view_start = 0
        if len(self.value) >= width:
            view_start = max(0, self.cursor_pos - width + 1)
        
        display_text = self.value[view_start : view_start + width]
        stdscr.addstr(y, x, display_text, bg_color)
        
        if self.focused:
            cursor_x = x + self.cursor_pos - view_start
            if x <= cursor_x < x + width:
                stdscr.chgat(y, cursor_x, 1, curses.A_REVERSE)

    def handle_input(self, key):
        if not self.visible or not self.focused:
            return False
        
        if key == curses.KEY_BACKSPACE or key == 127:
            if self.cursor_pos > 0:
                self.value = self.value[:self.cursor_pos-1] + self.value[self.cursor_pos:]
                self.cursor_pos -= 1
        elif key == curses.KEY_DC:  # Delete key
            if self.cursor_pos < len(self.value):
                self.value = self.value[:self.cursor_pos] + self.value[self.cursor_pos+1:]
        elif key == curses.KEY_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.cursor_pos = min(len(self.value), self.cursor_pos + 1)
        elif key == curses.KEY_HOME:
            self.cursor_pos = 0
        elif key == curses.KEY_END:
            self.cursor_pos = len(self.value)
        elif 32 <= key <= 126:  # Printable characters
            self.value = self.value[:self.cursor_pos] + chr(key) + self.value[self.cursor_pos:]
            self.cursor_pos += 1
        else:
            return False # Unhandled key

        if self.on_change:
            self.on_change(self.value)
        return True

class MaterialList(MaterialComponent):
    def __init__(self, theme, region, items: Optional[List[str]] = None, on_select: Optional[Callable] = None):
        super().__init__(theme, region)
        self.items = items or []
        self.selected_index = 0 if self.items else -1
        self.on_select = on_select
        self.scroll_offset = 0
        
    def draw(self, stdscr):
        if not self.visible:
            return
            
        x, y, width, height = self.get_content_area()
        if height <= 0 or width <= 0: return

        for i in range(height):
            item_idx = self.scroll_offset + i
            if item_idx >= len(self.items):
                break
                
            item_text = self.items[item_idx]
            display_text = item_text.ljust(width)[:width]

            color = self.theme.get_color(MaterialTheme.SURFACE)
            if item_idx == self.selected_index:
                color = self.theme.get_highlight_color(MaterialTheme.PRIMARY)
                if self.focused:
                    color |= curses.A_BOLD
            
            stdscr.addstr(y + i, x, display_text, color)
        
        # Draw scrollbar
        if len(self.items) > height:
            bar_height = max(1, int(height * height / len(self.items)))
            bar_y = y + int(self.scroll_offset * height / len(self.items))
            for i in range(bar_height):
                if y <= bar_y + i < y + height:
                    stdscr.addch(bar_y + i, x + width - 1, curses.ACS_CKBOARD, self.theme.get_color(MaterialTheme.SECONDARY))

    def handle_input(self, key):
        if not self.visible or not self.focused or not self.items:
            return False
            
        _, _, _, height = self.get_content_area()
        
        if key == curses.KEY_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif key == curses.KEY_DOWN:
            self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
        elif key == curses.KEY_PPAGE: # Page Up
            self.selected_index = max(0, self.selected_index - height)
        elif key == curses.KEY_NPAGE: # Page Down
            self.selected_index = min(len(self.items) - 1, self.selected_index + height)
        elif key == curses.KEY_HOME:
            self.selected_index = 0
        elif key == curses.KEY_END:
            self.selected_index = len(self.items) - 1
        elif key == ord('\n') or key == curses.KEY_ENTER:
            if 0 <= self.selected_index < len(self.items) and self.on_select:
                self.on_select(self.selected_index, self.items[self.selected_index])
            return True
        else:
            return False

        # Adjust scroll position to keep selection in view
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + height:
            self.scroll_offset = self.selected_index - height + 1
        
        return True

class MaterialSnackbar:
    def __init__(self, theme, message, duration=3, style=MaterialTheme.SECONDARY):
        self.theme = theme
        self.message = message
        self.duration = duration
        self.style = style
        self.visible = False
        self.start_time = 0
        
    def show(self):
        self.visible = True
        self.start_time = time.time()
        
    def draw(self, stdscr):
        if not self.visible:
            return
        
        if time.time() - self.start_time > self.duration:
            self.visible = False
            return
            
        height, width = stdscr.getmaxyx()
        snack_width = min(len(self.message) + 4, width - 4)
        x = (width - snack_width) // 2
        y = height - 3
        
        stdscr.addstr(y, x, ' ' * snack_width, self.theme.get_color(self.style))
        stdscr.addstr(y, x + 2, self.message, self.theme.get_color(self.style))
            
    def _wrap_text(self, text, width):
        # Simple wrapper for single line snackbar
        return [text]

class MaterialProgress(MaterialComponent):
    def __init__(self, theme, region, value=0, max_value=100):
        super().__init__(theme, region)
        self.value = value
        self.max_value = max_value
        
    def draw(self, stdscr):
        if not self.visible:
            return
            
        x, y, width, height = self.get_content_area()
        if width <= 0 or height <= 0: return

        progress = 0
        if self.max_value > 0:
            progress = min(1.0, max(0.0, float(self.value) / self.max_value))
        
        bar_width = int(width * progress)
        
        # Draw progress bar
        stdscr.addstr(y, x, '█' * bar_width, self.theme.get_color(MaterialTheme.PRIMARY))
        stdscr.addstr(y, x + bar_width, ' ' * (width - bar_width), self.theme.get_color(MaterialTheme.SECONDARY))
            
        # Draw percentage text
        percent_text = f"{int(progress * 100)}%"
        text_x = x + (width - len(percent_text)) // 2
        if text_x >= x:
            stdscr.addstr(y, text_x, percent_text, self.theme.get_color(MaterialTheme.TEXT_PRIMARY))

class MaterialChip(MaterialComponent):
    def __init__(self, theme, region, text, on_click=None, style=MaterialTheme.SECONDARY):
        super().__init__(theme, region)
        self.text = text
        self.on_click = on_click
        self.style = style
        
    def draw(self, stdscr):
        if not self.visible:
            return

        x, y, width, height = self.region.x, self.region.y, self.region.width, self.region.height
        display_text = self.text.center(width)

        color = self.theme.get_highlight_color(self.style) if self.focused else self.theme.get_color(self.style)
        stdscr.addstr(y, x, display_text, color)
            
    def handle_input(self, key):
        if not self.visible or not self.focused:
            return False
            
        if (key == ord(' ') or key == ord('\n') or key == curses.KEY_ENTER) and self.on_click:
            self.on_click()
            return True
        return False