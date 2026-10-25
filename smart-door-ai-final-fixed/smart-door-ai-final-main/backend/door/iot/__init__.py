import threading

from django.conf import settings

_controller = None
_lock = threading.Lock()


def get_controller():
    """Singleton chosen by IOT_MODE ('demo' | 'serial' | 'real')."""
    global _controller
    if _controller is None:
        with _lock:
            if _controller is None:
                mode = getattr(settings, "IOT_MODE", "demo")
                if mode in ("real", "mqtt"):
                    from .mqtt_controller import MQTTController
                    _controller = MQTTController()
                elif mode == "serial":
                    from .serial_controller import SerialController
                    _controller = SerialController()
                else:
                    from .demo_controller import DemoController
                    _controller = DemoController()
    return _controller


def reset_controller():
    global _controller
    _controller = None
