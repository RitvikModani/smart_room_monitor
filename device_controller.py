"""
Smart Room Monitor ─ device_controller.py
Now controls REAL ESP32 hardware via Serial.
"""

import serial
import time
import serial.tools.list_ports

class DeviceController:
    """Controls real LED and DC Motor via ESP32."""

    def __init__(self, port=None, baudrate=115200):
        self.light_on: bool = False
        self.fan_on:   bool = False
        self.serial = None
        
        self._connect_esp32(port, baudrate)

    def _connect_esp32(self, port=None, baudrate=115200):
        """Auto-detect or use provided port"""
        try:
            if port is None:
                ports = list(serial.tools.list_ports.comports())
                for p in ports:
                    if "USB" in p.description or "CP210" in p.description or "CH340" in p.description:
                        port = p.device
                        break
            
            if port:
                self.serial = serial.Serial(port, baudrate, timeout=1)
                time.sleep(2)  # Wait for ESP32 reset
                print(f"[DEVICE] Connected to ESP32 on {port}")
            else:
                print("[DEVICE] ⚠️  ESP32 not found. Running in simulation mode.")
        except Exception as e:
            print(f"[DEVICE] Serial connection failed: {e}")

    def _send_command(self, cmd: str):
        if self.serial and self.serial.is_open:
            try:
                self.serial.write((cmd + '\n').encode())
                # Optional: read response
                # response = self.serial.readline().decode().strip()
                # print(f"[ESP32] {response}")
            except Exception as e:
                print(f"[DEVICE] Send error: {e}")

    # ── Light ────────────────────────────────────────────────────────────────
    def turn_on_light(self) -> bool:
        if not self.light_on:
            self.light_on = True
            self._send_command("LIGHT_ON")
            print("[DEVICE] 💡 Light  →  ON")
            return True
        return False

    def turn_off_light(self) -> bool:
        if self.light_on:
            self.light_on = False
            self._send_command("LIGHT_OFF")
            print("[DEVICE] 💡 Light  →  OFF")
            return True
        return False

    # ── Fan ──────────────────────────────────────────────────────────────────
    def turn_on_fan(self) -> bool:
        if not self.fan_on:
            self.fan_on = True
            self._send_command("FAN_ON")
            print("[DEVICE] 🌀 Fan    →  ON")
            return True
        return False

    def turn_off_fan(self) -> bool:
        if self.fan_on:
            self.fan_on = False
            self._send_command("FAN_OFF")
            print("[DEVICE] 🌀 Fan    →  OFF")
            return True
        return False

    # ── Convenience ──────────────────────────────────────────────────────────
    def activate_all(self) -> bool:
        return self.turn_on_light() | self.turn_on_fan()

    def deactivate_all(self) -> bool:
        return self.turn_off_light() | self.turn_off_fan()

    @property
    def any_on(self) -> bool:
        return self.light_on or self.fan_on

    def status(self) -> dict:
        return {"light_on": self.light_on, "fan_on": self.fan_on}

    def __repr__(self) -> str:
        L = "ON" if self.light_on else "OFF"
        F = "ON" if self.fan_on   else "OFF"
        return f"<DeviceController light={L} fan={F}>"

    def close(self):
        if self.serial and self.serial.is_open:
            self.serial.close()