"""
MotionAI - Main Entry Point
Launches the UI and initializes all subsystems.
"""

import sys
import os
import threading
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure local imports work when packaged
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from ui.main_ui import MotionAIWindow
from wake_listener import WakeListener
from core.event_bus import EventBus


def main():

    app = QApplication(sys.argv)
    app.setApplicationName("MotionAI")
    app.setOrganizationName("MotionAI")

    # Global event bus for inter-module communication
    bus = EventBus()

    # Main window
    window = MotionAIWindow(event_bus=bus)
    window.show()

    # Start wake listener in background thread
    wake = WakeListener(event_bus=bus)
    wake_thread = threading.Thread(target=wake.listen, daemon=True)
    wake_thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()