"""
gesture_controller.py
Hand gesture tracking using MediaPipe Hands.
Controls mouse movement, clicking, scrolling, and dragging.
"""

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import threading
import time
from core.event_bus import EventBus, Events
from core.config import GESTURE_CAMERA_INDEX, GESTURE_SENSITIVITY, GESTURE_SCROLL_SPEED

# Disable PyAutoGUI fail-safe (move to corner to stop)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


class GestureController:
    """
    Webcam-based hand gesture controller.
    Replaces mouse with hand movements.

    Gestures:
    - Index finger up         → Move cursor
    - Index + Middle up       → Click (when close together)
    - Thumb + Index pinch     → Drag
    - Open hand               → Scroll (vertical hand movement)
    - Fist                    → Stop / neutral
    """

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._running = False
        self._thread: threading.Thread = None

        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.75,
            min_tracking_confidence=0.6,
        )

        # Screen dimensions
        self.screen_w, self.screen_h = pyautogui.size()

        # State tracking
        self._prev_x, self._prev_y = 0, 0
        self._click_cooldown = 0
        self._dragging = False
        self._frame_buffer = None  # Latest frame for UI display

        # Smoothing
        self._smooth_x, self._smooth_y = 0, 0
        self._smooth_factor = 0.4

        # Frame dimensions (set on first capture)
        self._frame_w, self._frame_h = 640, 480

    def start(self):
        """Start gesture tracking in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Gesture] Started")

    def stop(self):
        """Stop gesture tracking."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[Gesture] Stopped")

    @property
    def current_frame(self):
        """Latest annotated camera frame for display."""
        return self._frame_buffer

    def _loop(self):
        cap = cv2.VideoCapture(GESTURE_CAMERA_INDEX)
        if not cap.isOpened():
            print("[Gesture] Camera not available")
            self.bus.publish(Events.ERROR, {"message": "Gesture camera unavailable"})
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        self._frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            # Flip horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_drawing.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(0, 255, 180), thickness=2, circle_radius=4),
                        self.mp_drawing.DrawingSpec(color=(0, 180, 255), thickness=2)
                    )
                    self._process_hand(hand_landmarks, frame)

            # Add gesture mode overlay
            self._draw_overlay(frame)

            # Store frame for UI widget
            self._frame_buffer = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.bus.publish(Events.GESTURE_FRAME, {"frame": self._frame_buffer})

        cap.release()

    def _process_hand(self, landmarks, frame):
        """Analyze landmark positions and execute gesture actions."""
        lm = landmarks.landmark

        # Key landmarks
        index_tip  = lm[8]
        index_pip  = lm[6]
        middle_tip = lm[12]
        middle_pip = lm[10]
        thumb_tip  = lm[4]
        ring_tip   = lm[16]
        pinky_tip  = lm[20]
        wrist      = lm[0]

        # Detect which fingers are up
        index_up  = index_tip.y  < index_pip.y
        middle_up = middle_tip.y < middle_pip.y
        ring_up   = ring_tip.y   < lm[14].y
        pinky_up  = pinky_tip.y  < lm[18].y

        # Convert index tip to screen coordinates
        x = int(index_tip.x * self._frame_w)
        y = int(index_tip.y * self._frame_h)

        # Map to screen with scaling
        screen_x = int(np.interp(x, [50, self._frame_w - 50], [0, self.screen_w]))
        screen_y = int(np.interp(y, [50, self._frame_h - 50], [0, self.screen_h]))

        # Smooth cursor
        self._smooth_x += self._smooth_factor * (screen_x - self._smooth_x)
        self._smooth_y += self._smooth_factor * (screen_y - self._smooth_y)
        sx, sy = int(self._smooth_x), int(self._smooth_y)

        # ─── Gesture Detection ───────────────────────────────────────────

        # GESTURE 1: Move cursor (only index finger up)
        if index_up and not middle_up:
            pyautogui.moveTo(sx, sy)
            self._draw_cursor_indicator(frame, x, y, (0, 255, 100))
            self.bus.publish(Events.GESTURE_ACTION, {"action": "move", "x": sx, "y": sy})

        # GESTURE 2: Click (index + middle up, fingers close together)
        elif index_up and middle_up:
            dist = abs(index_tip.x - middle_tip.x) + abs(index_tip.y - middle_tip.y)
            if dist < 0.04 and self._click_cooldown == 0:
                pyautogui.click(sx, sy)
                self._click_cooldown = 15
                self._draw_cursor_indicator(frame, x, y, (0, 100, 255))
                self.bus.publish(Events.GESTURE_ACTION, {"action": "click", "x": sx, "y": sy})
            else:
                pyautogui.moveTo(sx, sy)

        # GESTURE 3: Scroll (4 fingers up)
        elif index_up and middle_up and ring_up and pinky_up:
            dy = self._prev_y - y
            scroll_amount = int(dy / 10 * GESTURE_SCROLL_SPEED)
            if abs(scroll_amount) > 1:
                pyautogui.scroll(scroll_amount)
                self.bus.publish(Events.GESTURE_ACTION, {"action": "scroll", "amount": scroll_amount})

        # GESTURE 4: Drag (thumb + index pinch)
        elif not index_up and not middle_up:
            pinch_dist = abs(thumb_tip.x - index_tip.x) + abs(thumb_tip.y - index_tip.y)
            if pinch_dist < 0.05:
                if not self._dragging:
                    pyautogui.mouseDown(sx, sy)
                    self._dragging = True
                else:
                    pyautogui.moveTo(sx, sy)
            elif self._dragging:
                pyautogui.mouseUp()
                self._dragging = False

        self._prev_x, self._prev_y = x, y
        if self._click_cooldown > 0:
            self._click_cooldown -= 1

    def _draw_cursor_indicator(self, frame, x, y, color):
        cv2.circle(frame, (x, y), 15, color, -1)
        cv2.circle(frame, (x, y), 20, (255, 255, 255), 2)

    def _draw_overlay(self, frame):
        h, w = frame.shape[:2]
        # Glowing border effect
        cv2.rectangle(frame, (0, 0), (w-1, h-1), (0, 255, 180), 2)
        cv2.putText(frame, "GESTURE MODE", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 180), 2)

        # Gesture guide
        guide = [
            "Index Up   → Move",
            "2 Fingers  → Click",
            "4 Fingers  → Scroll",
            "Pinch      → Drag",
        ]
        for i, g in enumerate(guide):
            cv2.putText(frame, g, (10, h - 80 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 255, 255), 1)