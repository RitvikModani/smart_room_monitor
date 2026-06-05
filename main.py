"""
Smart Room Monitor ─ main.py
Entry point. Orchestrates all modules.
"""
import sys
import time
import queue
import threading

import cv2

import config
from detection       import DetectionEngine
from device_controller import DeviceController
from audio_manager   import AudioManager
from ui_renderer     import UIRenderer


class SmartRoomMonitor:
    def __init__(self):
        print("[INIT] Starting Smart Room Monitor …")

        self.detector  = DetectionEngine()
        self.devices   = DeviceController(port="COM6")
        self.audio     = AudioManager(default_cooldown=config.AUDIO_COOLDOWN)
        self.ui        = UIRenderer()

        self.human_present:   bool = False
        self.override_mode:   bool = False
        self.messy_objects:   list = []

        self._welcome_played: bool = False
        self._warning_played: bool = False

        self._hw_start:    float = time.monotonic()
        self._hw_reminded: bool  = False

        self._last_analysis:  float        = 0.0
        self._analyzing:      bool         = False
        self._result_q: queue.Queue[dict]  = queue.Queue(maxsize=1)

        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not self.cap.isOpened():
            print(f"[ERROR] Cannot open webcam (index {config.CAMERA_INDEX}).")
            sys.exit(1)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        print("[INIT] ✔ System ready — press SPACE to toggle override, Q/ESC to quit.")

    def run(self) -> None:
        while True:
            ok, frame = self.cap.read()
            if not ok:
                print("[ERROR] Frame capture failed.")
                break

            frame = cv2.flip(frame, 1)
            local_faces = self.detector.detect_faces(frame)
            frame = self.ui.draw_bounding_boxes(frame, local_faces)

            now       = time.monotonic()
            elapsed   = now - self._last_analysis
            countdown = max(0, int(config.DETECTION_INTERVAL - elapsed))

            if not self._analyzing and elapsed >= config.DETECTION_INTERVAL:
                self._last_analysis = now
                self._launch_analysis(frame.copy())

            self._consume_analysis_result()
            self._check_homework_reminder()

            frame = self.ui.render(
                frame,
                light_on      = self.devices.light_on,
                fan_on        = self.devices.fan_on,
                human_present = self.human_present,
                override_mode = self.override_mode,
                countdown     = countdown,
                messy_objects = self.messy_objects,
            )

            cv2.imshow("Smart Room Monitor", frame)

            key = cv2.waitKey(1) & 0xFF
            if not self._handle_key(key):
                break

        self._shutdown()

    def _launch_analysis(self, frame) -> None:
        self._analyzing = True
        print("[DETECT] → Sending frame to Groq …")

        def _worker():
            result = self.detector.analyze_frame(frame)
            try:
                self._result_q.put_nowait(result)
            except queue.Full:
                pass
            finally:
                self._analyzing = False

        threading.Thread(target=_worker, daemon=True, name="groq-worker").start()

    def _consume_analysis_result(self) -> None:
        try:
            result = self._result_q.get_nowait()
        except queue.Empty:
            return

        new_human    = result["human_present"]
        messy_objs   = result["messy_objects"]
        room_messy   = result["room_messy"]

        print(f"[DETECT] human={new_human}  messy={room_messy}  objects={messy_objs}")

        if new_human != self.human_present:
            if new_human:
                self._on_person_entered()
            else:
                self._on_person_left()

        self.human_present = new_human
        self.messy_objects = messy_objs

        if not self.override_mode:
            self._apply_device_logic()
            self._apply_cleanliness_logic(room_messy, messy_objs)

    # ════════════════════════════════════════════════════════════════════════
    # Event Handlers (No Volume Parameter)
    # ════════════════════════════════════════════════════════════════════════

    def _on_person_entered(self) -> None:
        print("[EVENT] ✔  Person entered.")
        if not self.override_mode and not self._welcome_played:
            self.audio.play(config.AUDIO_WELCOME, "welcome", cooldown=60, policy="skip")
            self._welcome_played = True
        self._warning_played = False

    def _on_person_left(self) -> None:
        print("[EVENT] ✘  Person left.")
        self._welcome_played = False
        self._warning_played = False

    # ── Device logic ────────────────────────────────────────────────────────

    def _apply_device_logic(self) -> None:
        if self.human_present:
            self.devices.activate_all()
        else:
            # ONLY play the empty warning if the lights are still currently on
            if self.devices.light_on and not self._warning_played:
                self.audio.play(config.AUDIO_WARNING, "warning", policy="interrupt")
                self._warning_played = True
                
            self.devices.deactivate_all()

    # ── Cleanliness logic ────────────────────────────────────────────────────

    def _apply_cleanliness_logic(self, room_messy: bool, objects: list) -> None:
        if room_messy or objects:
            obj_str = ", ".join(objects) or "clutter"
            print(f"[ALERT] Messy room detected: {obj_str}")
            self.audio.play(config.AUDIO_CLEAN_ROOM, "clean_room", cooldown=60, policy="skip")

    # ── Homework reminder ────────────────────────────────────────────────────

    def _check_homework_reminder(self) -> None:
        if self._hw_reminded:
            return
        elapsed = time.monotonic() - self._hw_start
        if elapsed >= config.HOMEWORK_REMINDER:
            print(f"[REMINDER] Homework reminder triggered ({elapsed:.0f}s elapsed).")
            if not self.override_mode:
                self.audio.play(
                    config.AUDIO_HOMEWORK, "homework",
                    cooldown=config.HOMEWORK_REMINDER,
                    policy="queue"
                )
            self._hw_reminded = True

    def _handle_key(self, key: int) -> bool:
        if key in (ord("q"), 27):
            return False
        if key == ord(" "):
            self.override_mode = not self.override_mode
            state = "ON  (automation suspended)" if self.override_mode else "OFF (automation active)"
            print(f"[OVERRIDE] Override → {state}")
        return True

    def _shutdown(self) -> None:
        print("[SHUTDOWN] Releasing resources …")
        self.cap.release()
        cv2.destroyAllWindows()
        self.audio.shutdown()
        print("[SHUTDOWN] Goodbye! 👋")


if __name__ == "__main__":
    SmartRoomMonitor().run()