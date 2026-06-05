"""
Smart Room Monitor ─ ui_renderer.py
Draws the HUD overlay (status panel, bounding boxes, control hints) on top
of the live webcam frame using only OpenCV primitives.

All colour constants are in BGR order (OpenCV convention).
"""
import cv2
import numpy as np

# ── Colour palette (BGR) ────────────────────────────────────────────────────
_GREEN  = (  0, 210,   0)
_RED    = (  0,  55, 220)
_YELLOW = (  0, 200, 255)
_ORANGE = (  0, 140, 255)
_WHITE  = (255, 255, 255)
_GREY   = (140, 140, 140)
_BLACK  = (  0,   0,   0)
_CYAN   = (200, 200,   0)


class UIRenderer:
    # Panel geometry
    PANEL_X  = 10
    PANEL_Y  = 10
    PANEL_W  = 300
    PANEL_H  = 230
    PAD      = 18    # left text margin inside panel

    # ── Main entry point ────────────────────────────────────────────────────

    def render(
        self,
        frame:         np.ndarray,
        light_on:      bool,
        fan_on:        bool,
        human_present: bool,
        override_mode: bool,
        countdown:     int,
        messy_objects: list[str],
    ) -> np.ndarray:
        """Compose all HUD elements onto *frame* and return it."""
        frame = self._draw_panel_background(frame)
        frame = self._draw_status_rows(
            frame, light_on, fan_on, human_present,
            override_mode, countdown, messy_objects
        )
        frame = self._draw_hint_bar(frame)
        return frame

    def draw_bounding_boxes(
        self, frame: np.ndarray, detections: list[tuple]
    ) -> np.ndarray:
        """Draw a green rectangle + label for each (x, y, w, h) detection."""
        for x, y, w, h in detections:
            cv2.rectangle(frame, (x, y), (x + w, y + h), _GREEN, 2)
            label_y = max(y - 8, 16)
            cv2.putText(
                frame, "Person",
                (x + 4, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, _GREEN, 2,
            )
        return frame

    # ── Panel background ────────────────────────────────────────────────────

    def _draw_panel_background(self, frame: np.ndarray) -> np.ndarray:
        overlay = frame.copy()
        x1, y1 = self.PANEL_X, self.PANEL_Y
        x2, y2 = x1 + self.PANEL_W, y1 + self.PANEL_H
        cv2.rectangle(overlay, (x1, y1), (x2, y2), _BLACK, cv2.FILLED)
        # 55 % opaque panel
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
        # thin border
        cv2.rectangle(frame, (x1, y1), (x2, y2), _GREY, 1)
        return frame

    # ── Text rows ───────────────────────────────────────────────────────────

    def _draw_status_rows(
        self, frame, light_on, fan_on, human_present,
        override_mode, countdown, messy_objects
    ) -> np.ndarray:
        x = self.PANEL_X + self.PAD
        y = self.PANEL_Y + 34
        step = 34

        # ── Row 1: Mode ──────────────────────────────────────────────────────
        if override_mode:
            self._text(frame, "OVERRIDE MODE", x, y, _YELLOW, 0.70, 2)
        else:
            self._text(frame, "AUTO MODE", x, y, _GREEN, 0.70, 2)

        # Separator line
        y += 10
        cv2.line(
            frame,
            (self.PANEL_X + 8, y),
            (self.PANEL_X + self.PANEL_W - 8, y),
            _GREY, 1,
        )
        y += 18

        # ── Row 2: Light ─────────────────────────────────────────────────────
        light_label = "LIGHT :  ON " if light_on else "LIGHT :  OFF"
        light_color = _YELLOW if light_on else _RED
        self._text(frame, light_label, x, y, light_color, 0.64, 2)
        y += step

        # ── Row 3: Fan ───────────────────────────────────────────────────────
        fan_label = "FAN   :  ON " if fan_on else "FAN   :  OFF"
        fan_color = _GREEN if fan_on else _RED
        self._text(frame, fan_label, x, y, fan_color, 0.64, 2)
        y += step

        # ── Row 4: Presence ──────────────────────────────────────────────────
        if human_present:
            self._text(frame, "PERSON : DETECTED", x, y, _GREEN, 0.56, 2)
        else:
            self._text(frame, "PERSON : NOT FOUND", x, y, _RED, 0.56, 2)
        y += 28

        # ── Row 5: Messy alert ───────────────────────────────────────────────
        if messy_objects:
            label = "MESSY: " + ", ".join(messy_objects[:3])
            if len(messy_objects) > 3:
                label += " …"
            self._text(frame, label, x, y, _ORANGE, 0.48, 1)
        else:
            self._text(frame, "Room : Clean", x, y, _GREY, 0.48, 1)
        y += 24

        # ── Row 6: Countdown ─────────────────────────────────────────────────
        self._text(frame, f"Next scan : {countdown}s", x, y, _GREY, 0.44, 1)

        return frame

    # ── Bottom hint bar ─────────────────────────────────────────────────────

    def _draw_hint_bar(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 32), (w, h), _BLACK, cv2.FILLED)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
        self._text(
            frame,
            "SPACE: Toggle Override       Q / ESC: Quit",
            10, h - 10,
            _WHITE, 0.44, 1,
        )
        return frame

    # ── Helper ──────────────────────────────────────────────────────────────

    @staticmethod
    def _text(
        frame, text: str, x: int, y: int,
        color: tuple, scale: float, thickness: int
    ) -> None:
        cv2.putText(
            frame, text, (x, y),
            cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness,
            cv2.LINE_AA,
        )
