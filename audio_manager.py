"""
Smart Room Monitor ─ audio_manager.py
Thread-safe MP3 playback with per-event cooldown and playback policies.
"""
import os
import time
import threading

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    _PYGAME_OK = True
except Exception as _err:
    print(f"[AUDIO] pygame init failed ({_err}). Audio will be skipped.")
    _PYGAME_OK = False


class AudioManager:
    """Play MP3 files with per-event cooldown guards and execution priorities."""

    def __init__(self, default_cooldown: int = 30):
        self._default_cooldown = default_cooldown          # seconds
        self._last_played: dict[str, float] = {}           # event_key → timestamp
        self._state_lock  = threading.Lock()               # guards _last_played
        self._play_lock   = threading.Lock()               # only one sound at a time

    # ── Public API ──────────────────────────────────────────────────────────

    def play(
        self, 
        filepath: str, 
        event_key: str, 
        cooldown: int | None = None, 
        policy: str = "queue"
    ) -> bool:
        """
        Play *filepath* for the given *event_key*, subject to cooldown.

        Policies:
          - "queue"     : Wait until the current audio finishes playing.
          - "interrupt" : Stop current audio immediately and play this now.
          - "skip"      : If audio hardware is busy, discard this playback request.
        """
        if not _PYGAME_OK:
            print(f"[AUDIO] (skipped — pygame unavailable) event={event_key}")
            return False

        if not os.path.isfile(filepath):
            print(f"[AUDIO] File not found: {filepath}")
            return False

        # 1. Policy check
        if policy == "skip" and self._play_lock.locked():
            print(f"[AUDIO] ⏭ Skip policy active. Hardware busy, dropping: {event_key}")
            return False

        cooldown = cooldown if cooldown is not None else self._default_cooldown

        # 2. Cooldown check
        with self._state_lock:
            now  = time.monotonic()
            last = self._last_played.get(event_key, 0.0)
            if now - last < cooldown:
                return False
            self._last_played[event_key] = now

        # 3. Handle Interruption
        if policy == "interrupt" and self._play_lock.locked():
            print(f"[AUDIO] ⚠️ Interrupt triggered by {event_key}. Stopping current track.")
            pygame.mixer.music.stop()

        # 4. Dispatch Thread
        threading.Thread(
            target=self._play_blocking,
            args=(filepath,),
            daemon=True,
            name=f"audio-{event_key}",
        ).start()
        
        print(f"[AUDIO] ▶ {event_key} ({os.path.basename(filepath)}) [Policy: {policy}]")
        return True

    def reset(self, event_key: str) -> None:
        with self._state_lock:
            self._last_played.pop(event_key, None)

    def shutdown(self) -> None:
        if _PYGAME_OK:
            pygame.mixer.quit()

    # ── Internal ────────────────────────────────────────────────────────────

    def _play_blocking(self, filepath: str) -> None:
        with self._play_lock:
            try:
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
            except Exception as exc:
                print(f"[AUDIO] Playback error ({filepath}): {exc}")