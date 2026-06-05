"""
Smart Room Monitor ─ detection.py
Two-tier detection strategy:

  Tier 1 (local, every frame):
      OpenCV Haar Cascade → fast face bounding boxes for live overlay.

  Tier 2 (cloud, every N seconds):
      Groq Vision LLM → richer understanding:
        • Confirms human presence even without a frontal face
        • Identifies messy objects (bottle, cup, book, trash …)
        • Flags whether the room looks dirty/cluttered

The cloud tier runs on a background thread (see main.py) so it never
stalls the video loop.
"""
import base64
import json

import cv2
import numpy as np
from groq import Groq

import config


class DetectionEngine:
    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)

        # ── OpenCV cascade classifiers ───────────────────────────────────────
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.body_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_upperbody.xml"
        )
        if self.face_cascade.empty():
            raise RuntimeError("Haar cascade file not found — check your OpenCV install.")

    # ── Tier-1: Local face detection ────────────────────────────────────────

    def detect_faces(self, frame: np.ndarray) -> list[tuple]:
        """
        Return a list of (x, y, w, h) bounding boxes for each detected face.
        Falls back to upper-body detection when no frontal face is found.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        # Fall back to upper-body if no face found
        if len(faces) == 0:
            faces = self.body_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60)
            )

        return list(map(tuple, faces)) if len(faces) > 0 else []

    # ── Tier-2: Groq Vision analysis ────────────────────────────────────────

    def analyze_frame(self, frame: np.ndarray) -> dict:
        """
        Send *frame* to the Groq Vision API and return a structured result:

            {
              "human_present":  bool,
              "messy_objects":  list[str],   # e.g. ["bottle", "cup"]
              "room_messy":     bool,
            }

        On any error a safe default (all-False) is returned so the system
        degrades gracefully without crashing.
        """
        try:
            b64 = self._encode_frame(frame)

            response = self.client.chat.completions.create(
                model=config.GROQ_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}"
                                },
                            },
                            {"type": "text", "text": self._build_prompt()},
                        ],
                    }
                ],
                max_tokens=350,
                temperature=0.1,
            )

            raw = response.choices[0].message.content.strip()
            return self._parse_json(raw)

        except Exception as exc:
            print(f"[DETECT] Groq API error: {exc}")
            return self._default_result()

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _encode_frame(frame: np.ndarray) -> str:
        """Resize to 640×480 and JPEG-encode at 75 % quality for speed."""
        small = cv2.resize(frame, (640, 480))
        ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ok:
            raise ValueError("Frame encoding failed")
        return base64.b64encode(buf.tobytes()).decode("utf-8")

    @staticmethod
    def _build_prompt() -> str:
        return (
            "Analyze this webcam / room image.\n"
            "Reply with ONLY a JSON object — no markdown, no explanation:\n"
            "{\n"
            '  "human_present": true or false,\n'
            '  "messy_objects": ["bottle","cup","book","trash","clothes", ...],\n'
            '  "room_messy": true or false\n'
            "}\n\n"
            "Rules:\n"
            "  human_present → true if ANY person, face, or body is visible.\n"
            "  messy_objects → list every cluttered/scattered item you can identify.\n"
            "  room_messy    → true if there is visible clutter or scattered items."
        )

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Extract JSON from the LLM reply; strip markdown fences if present."""
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start == -1 or end <= start:
            print(f"[DETECT] No JSON found in response: {text[:80]!r}")
            return DetectionEngine._default_result()
        try:
            data = json.loads(text[start:end])
            return {
                "human_present": bool(data.get("human_present", False)),
                "messy_objects": list(data.get("messy_objects", [])),
                "room_messy":    bool(data.get("room_messy", False)),
            }
        except json.JSONDecodeError as exc:
            print(f"[DETECT] JSON parse error: {exc} — raw: {text[:80]!r}")
            return DetectionEngine._default_result()

    @staticmethod
    def _default_result() -> dict:
        return {"human_present": False, "messy_objects": [], "room_messy": False}
