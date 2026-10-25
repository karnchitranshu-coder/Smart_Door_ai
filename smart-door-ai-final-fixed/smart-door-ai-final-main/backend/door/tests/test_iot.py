from django.test import override_settings
from door.iot import get_controller, reset_controller
from .base import BaseAPITest


class IoTTests(BaseAPITest):
    def test_manual_unlock_lock(self):
        self.assertEqual(self.client.post("/api/door/unlock", {"duration": 5}, format="json").data["state"], "unlocked")
        self.assertEqual(self.client.post("/api/door/lock").data["state"], "locked")

    def test_command_and_heartbeat(self):
        self.client.post("/api/iot/command", {"action": "unlock"}, format="json")
        self.assertEqual(self.client.get("/api/door/status").data["state"], "unlocked")
        bad = self.client.post("/api/iot/heartbeat", {"device_id": "d1"}, format="json")
        self.assertEqual(bad.status_code, 401)
        ok = self.client.post("/api/iot/heartbeat", {"device_id": "d1"}, format="json", HTTP_X_DEVICE_KEY="esp32-shared-secret")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(len(self.client.get("/api/iot/devices").data), 1)

    @override_settings(IOT_MODE="serial", SERIAL_PORT="COM_TEST_NONE")
    def test_serial_controller_unlock_and_lock(self):
        reset_controller()
        ctl = get_controller()
        st = ctl.unlock(3)
        self.assertEqual(st["mode"], "serial")
        self.assertEqual(st["state"], "unlocked")
        st_locked = ctl.lock()
        self.assertEqual(st_locked["state"], "locked")
        reset_controller()

    def test_health_includes_database_and_ai_status(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn("database", r.data)
        self.assertIn("backend", r.data["database"])
        self.assertTrue(r.data["face_recognition_available"])
