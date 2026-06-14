import sys
import threading
import time


class HotkeyManager:
    def __init__(self, on_pause, on_restore, on_toggle, on_error):
        self.on_pause = on_pause
        self.on_restore = on_restore
        self.on_toggle = on_toggle
        self.on_error = on_error
        self.keyboard = None
        self.bindings = []
        self.running = False
        self.hold_pressed = False
        self.backend = None
        self.poll_thread = None
        self.poll_stop = threading.Event()
        self.poll_keys = []
        self.poll_mode = "toggle"
        self.poll_down = False

    def final_key(self, hotkey):
        return hotkey.split("+")[-1].strip()

    def parse_windows_hotkey(self, hotkey):
        key_map = {
            "backspace": 0x08,
            "tab": 0x09,
            "enter": 0x0D,
            "return": 0x0D,
            "shift": 0x10,
            "ctrl": 0x11,
            "control": 0x11,
            "alt": 0x12,
            "pause": 0x13,
            "capslock": 0x14,
            "caps lock": 0x14,
            "esc": 0x1B,
            "escape": 0x1B,
            "space": 0x20,
            "pageup": 0x21,
            "page up": 0x21,
            "pagedown": 0x22,
            "page down": 0x22,
            "end": 0x23,
            "home": 0x24,
            "left": 0x25,
            "up": 0x26,
            "right": 0x27,
            "down": 0x28,
            "insert": 0x2D,
            "ins": 0x2D,
            "delete": 0x2E,
            "del": 0x2E,
            "win": 0x5B,
            "windows": 0x5B,
            "cmd": 0x5B,
            "menu": 0x5D,
        }

        for index in range(1, 25):
            key_map[f"f{index}"] = 0x70 + index - 1

        for index in range(10):
            key_map[str(index)] = 0x30 + index
            key_map[f"num {index}"] = 0x60 + index
            key_map[f"num{index}"] = 0x60 + index

        for letter in "abcdefghijklmnopqrstuvwxyz":
            key_map[letter] = ord(letter.upper())

        parts = [part.strip().lower() for part in hotkey.split("+") if part.strip()]
        if not parts:
            raise ValueError("empty hotkey")

        keys = []
        for part in parts:
            if part not in key_map:
                raise ValueError(f"unsupported key '{part}'")
            keys.append(key_map[part])

        return keys

    def available(self):
        try:
            import keyboard
        except Exception as exc:
            self.on_error(f"Global hotkeys unavailable: {exc}")
            return False

        self.keyboard = keyboard
        return True

    def windows_poll_available(self):
        if sys.platform != "win32":
            return False

        try:
            import ctypes
            self.user32 = ctypes.windll.user32
        except Exception as exc:
            self.on_error(f"Win32 hotkeys unavailable: {exc}")
            return False

        return True

    def start(self, hotkey, mode):
        self.stop()
        self.hold_pressed = False

        hotkey = (hotkey or "f8").strip().lower()
        mode = "hold" if mode == "hold" else "toggle"

        if self.windows_poll_available():
            try:
                return self.start_windows_poll(hotkey, mode)
            except Exception as exc:
                self.on_error(f"Win32 hotkey fallback failed for {hotkey}: {exc}")
                self.stop()

        if not self.available():
            return False

        try:
            if mode == "hold":
                press_binding = self.keyboard.add_hotkey(
                    hotkey,
                    self.handle_hold_press,
                    suppress=False,
                    trigger_on_release=False,
                )
                release_binding = self.keyboard.on_release_key(
                    self.final_key(hotkey),
                    self.handle_hold_release,
                    suppress=False,
                )
                self.bindings = [press_binding, release_binding]
            else:
                binding = self.keyboard.add_hotkey(
                    hotkey,
                    lambda: self.on_toggle("hotkey toggle"),
                    suppress=False,
                    trigger_on_release=False,
                )
                self.bindings = [binding]
        except Exception as exc:
            self.on_error(f"Could not bind hotkey {hotkey}: {exc}")
            self.bindings = []
            self.running = False
            return False

        self.running = True
        self.backend = "keyboard"
        return True

    def start_windows_poll(self, hotkey, mode):
        self.poll_keys = self.parse_windows_hotkey(hotkey)
        self.poll_mode = mode
        self.poll_down = False
        self.poll_stop.clear()
        self.poll_thread = threading.Thread(target=self.poll_hotkey, daemon=True)
        self.poll_thread.start()
        self.running = True
        self.backend = "win32-poll"
        return True

    def poll_hotkey(self):
        while not self.poll_stop.is_set():
            down = all(self.user32.GetAsyncKeyState(key) & 0x8000 for key in self.poll_keys)

            if self.poll_mode == "hold":
                if down and not self.poll_down:
                    self.handle_hold_press()
                elif not down and self.poll_down:
                    self.handle_hold_release(None)
            elif down and not self.poll_down:
                self.on_toggle("hotkey toggle")

            self.poll_down = down
            time.sleep(0.01)

    def handle_hold_press(self):
        if self.hold_pressed:
            return

        self.hold_pressed = True
        self.on_pause("hotkey hold press")

    def handle_hold_release(self, event):
        if not self.hold_pressed:
            return

        self.hold_pressed = False
        self.on_restore("hotkey hold release")

    def stop(self):
        if self.poll_thread:
            self.poll_stop.set()
            if self.poll_thread.is_alive():
                self.poll_thread.join(timeout=0.5)
            self.poll_thread = None

        if not self.keyboard:
            self.bindings = []
            self.running = False
            self.backend = None
            self.poll_down = False
            return

        for binding in self.bindings:
            try:
                self.keyboard.remove_hotkey(binding)
            except Exception:
                try:
                    self.keyboard.unhook(binding)
                except Exception:
                    pass

        self.bindings = []
        self.running = False
        self.hold_pressed = False
        self.backend = None
        self.poll_down = False
