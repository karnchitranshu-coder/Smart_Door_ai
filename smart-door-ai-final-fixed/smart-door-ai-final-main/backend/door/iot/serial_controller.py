"""PySerial ESP32 controller (matches Engineering Clinic Synopsis: Python -> PySerial -> ESP32 -> Servo Lock).
Sends 'UNLOCK:<duration>\\n' or 'LOCK\\n' over USB Serial and tracks auto-relock timer.
"""
import threading
import time
from datetime import datetime, timezone
from django.conf import settings
from .controller import IoTController


class SerialController(IoTController):
    def __init__(self):
        self.device_id = getattr(settings, "MQTT_DEVICE_ID", "esp32-serial")
        self.port = getattr(settings, "SERIAL_PORT", "COM3")
        self.baud = int(getattr(settings, "SERIAL_BAUD", 115200))
        self._lock = threading.RLock()
        self._state = "locked"
        self._connection = "offline"
        self._until = 0.0
        self._timer = None
        self._ser = None
        self._connect()

    def _connect(self):
        try:
            import serial
            self._ser = serial.Serial(self.port, self.baud, timeout=1.0)
            self._connection = "online"
            self._sync_device_row("online", self._state)
        except Exception:
            self._ser = None
            self._connection = "offline"

    def _sync_device_row(self, conn_status: str, door_state: str):
        try:
            from ..models import IoTDevice
            IoTDevice.objects.update_or_create(
                device_id=self.device_id,
                defaults={
                    "name": f"ESP32 Serial ({self.port})",
                    "connection_status": conn_status,
                    "door_state": door_state,
                    "last_heartbeat": datetime.now(timezone.utc),
                    "firmware": "serial-servo-1.0",
                },
            )
        except Exception:
            pass

    def _send(self, command: str) -> bool:
        with self._lock:
            if self._ser is None or not getattr(self._ser, "is_open", False):
                self._connect()
            if self._ser is not None:
                try:
                    self._ser.write((command.strip() + "\n").encode("utf-8"))
                    self._ser.flush()
                    self._connection = "online"
                    return True
                except Exception:
                    self._connection = "offline"
                    self._ser = None
            return False

    def unlock(self, duration: int = 5) -> dict:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._send(f"UNLOCK:{int(duration)}")
            self._state = "unlocked"
            self._until = time.time() + duration
            self._timer = threading.Timer(duration, self._relock)
            self._timer.daemon = True
            self._timer.start()
            self._sync_device_row(self._connection, "unlocked")
        return self.status()

    def _relock(self):
        with self._lock:
            self._send("LOCK")
            self._state = "locked"
            self._until = 0.0
            self._sync_device_row(self._connection, "locked")

    def lock(self) -> dict:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._relock()
        return self.status()

    def status(self) -> dict:
        with self._lock:
            remaining = max(0, round(self._until - time.time(), 1)) if self._state == "unlocked" else 0
            return {
                "mode": "serial",
                "device_id": self.device_id,
                "port": self.port,
                "connection": self._connection,
                "state": self._state,
                "seconds_remaining": remaining,
            }
