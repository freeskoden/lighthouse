import io
import logging
from PIL import Image
import mss
from pynput import keyboard, mouse

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SPECIAL_KEYS = {
    "enter": keyboard.Key.enter,
    "space": keyboard.Key.space,
    "backspace": keyboard.Key.backspace,
    "tab": keyboard.Key.tab,
    "shift": keyboard.Key.shift,
    "ctrl": keyboard.Key.ctrl,
    "alt": keyboard.Key.alt,
    "esc": keyboard.Key.esc,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "caps_lock": keyboard.Key.caps_lock,
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
}

BUTTONS = {
    "left": mouse.Button.left,
    "right": mouse.Button.right,
    "middle": mouse.Button.middle,
}

class ScreenCapture:
    @staticmethod
    def capture(quality=60, scale=0.8):
        """
        Captures the primary monitor screen, resizes it according to scale,
        and returns compressed JPEG bytes.
        """
        try:
            with mss.mss() as sct:
                # monitor[1] is the primary screen
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                
                # Convert raw BGRA data to RGB PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                if scale < 1.0:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.Resampling.BILINEAR)
                
                # Save to JPEG bytes in-memory
                out_bytes = io.BytesIO()
                img.save(out_bytes, format="JPEG", quality=quality)
                return out_bytes.getvalue()
        except Exception as e:
            logging.error(f"Failed to capture screen: {e}")
            return None


class InputSimulator:
    def __init__(self):
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

    def simulate_event(self, data):
        """
        Receives an event dict and simulates it on the host system.
        """
        event_type = data.get("event")
        if not event_type:
            return

        try:
            if event_type == "mouse_move":
                x_norm = data.get("x", 0.0)
                y_norm = data.get("y", 0.0)
                self.execute_mouse_move(x_norm, y_norm)

            elif event_type == "mouse_click":
                button_str = data.get("button", "left")
                pressed = data.get("pressed", True)
                self.execute_mouse_click(button_str, pressed)

            elif event_type == "mouse_scroll":
                dx = data.get("dx", 0)
                dy = data.get("dy", 0)
                self.execute_mouse_scroll(dx, dy)

            elif event_type == "key":
                key_str = data.get("key")
                pressed = data.get("pressed", True)
                if key_str:
                    self.execute_key_event(key_str, pressed)
        except Exception as e:
            logging.error(f"Error in simulate_event: {e}")

    def execute_mouse_move(self, x_norm, y_norm):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                target_x = monitor["left"] + int(x_norm * monitor["width"])
                target_y = monitor["top"] + int(y_norm * monitor["height"])
                self.mouse_controller.position = (target_x, target_y)
        except Exception as e:
            logging.error(f"Error executing mouse move: {e}")

    def execute_mouse_click(self, button_str, pressed):
        try:
            button = BUTTONS.get(button_str, mouse.Button.left)
            if pressed:
                self.mouse_controller.press(button)
            else:
                self.mouse_controller.release(button)
        except Exception as e:
            logging.error(f"Error executing mouse click: {e}")

    def execute_mouse_scroll(self, dx, dy):
        try:
            self.mouse_controller.scroll(dx, dy)
        except Exception as e:
            logging.error(f"Error executing mouse scroll: {e}")

    def execute_key_event(self, key_str, pressed):
        try:
            # Handle special names
            if key_str in SPECIAL_KEYS:
                key = SPECIAL_KEYS[key_str]
            elif len(key_str) == 1:
                key = keyboard.KeyCode.from_char(key_str)
            else:
                # Fallback for dynamic pynput keys
                key_attr = getattr(keyboard.Key, key_str, None)
                if key_attr:
                    key = key_attr
                else:
                    logging.warning(f"Key '{key_str}' not recognized.")
                    return

            if pressed:
                self.keyboard_controller.press(key)
            else:
                self.keyboard_controller.release(key)
        except Exception as e:
            logging.error(f"Error executing key event for '{key_str}': {e}")
