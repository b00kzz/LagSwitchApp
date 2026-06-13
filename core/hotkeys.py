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

    def final_key(self, hotkey):
        return hotkey.split("+")[-1].strip()

    def available(self):
        try:
            import keyboard
        except Exception as exc:
            self.on_error(f"Global hotkeys unavailable: {exc}")
            return False

        self.keyboard = keyboard
        return True

    def start(self, hotkey, mode):
        self.stop()
        self.hold_pressed = False
        if not self.available():
            return False

        hotkey = (hotkey or "f8").strip().lower()
        mode = "hold" if mode == "hold" else "toggle"

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
        return True

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
        if not self.keyboard:
            self.bindings = []
            self.running = False
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
