"""
ui/main_ui.py — MotionAI
All fixes:
  ✅ Counsellor mode responds properly
  ✅ Gesture camera overlay shown over transparent window
  ✅ Bye bye: speaks + kills process
  ✅ Weather answered instantly
  ✅ Interrupt AI mid-speech by speaking
  ✅ Real-time conversation (no delay)
  ✅ Text stays until TTS done
"""

import sys
import os
import math
import random
import threading
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QApplication,
    QLabel, QLineEdit, QSizePolicy, QVBoxLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, Slot
from PySide6.QtGui import (
    QPainter, QPen, QColor, QBrush,
    QLinearGradient, QFont, QImage, QPixmap
)

from core.event_bus import EventBus, Events
from core.config import USER_NAME

KILL_PHRASES = ["bye bye","bye-bye","goodbye","shut down motion","stop motion","exit motion"]
GOODBYE_TEXT = "Bye bye sir! Systems are shutting down!"


# ─── Bridge ───────────────────────────────────────────────────────────────────
class Bridge(QObject):
    wake          = Signal()
    speech        = Signal(str)
    response      = Signal(str)
    mode_change   = Signal(str)
    tts_start     = Signal(str)
    tts_done      = Signal()
    mic_active    = Signal(bool)
    gesture_frame = Signal(object)
    do_exit       = Signal()


# ─── Waveform ─────────────────────────────────────────────────────────────────
class WaveformData:
    BARS = 52
    def __init__(self):
        self.amplitudes = [0.06]*self.BARS
        self._t         = 0.0
        self._mic_on    = False
        self._speaking  = False
        self._targets   = [0.06]*self.BARS

    def set_mic(self, on: bool):      self._mic_on   = on
    def set_speaking(self, on: bool): self._speaking = on

    def tick(self):
        self._t += 0.10
        for i in range(self.BARS):
            if self._speaking:
                base = 0.42 + 0.38*math.sin(self._t*1.9 + i*0.27)
                self._targets[i] = min(1.0, base + random.uniform(0,0.18))
            elif self._mic_on:
                base = 0.22 + 0.22*math.sin(self._t*2.3 + i*0.34)
                self._targets[i] = min(1.0, base + random.uniform(0,0.14))
            else:
                self._targets[i] = 0.05 + 0.04*math.sin(self._t*0.55 + i*0.20)
            self.amplitudes[i] += 0.22*(self._targets[i] - self.amplitudes[i])


# ─── Canvas ───────────────────────────────────────────────────────────────────
class MotionCanvas(QWidget):
    def __init__(self, wave: WaveformData, parent=None):
        super().__init__(parent)
        self._wave       = wave
        self._glow_active= False
        self._glow_alpha = 0.0
        self._glow_grow  = True
        self._color      = QColor(0,230,170)

    def set_glow(self, on):   self._glow_active = on
    def set_color(self, c):   self._color = c

    def tick_glow(self):
        if not self._glow_active: return
        step = 0.025
        if self._glow_grow:
            self._glow_alpha = min(1.0, self._glow_alpha+step)
            if self._glow_alpha >= 1.0: self._glow_grow = False
        else:
            self._glow_alpha = max(0.20, self._glow_alpha-step)
            if self._glow_alpha <= 0.20: self._glow_grow = True

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0,0,w,h, QColor(0,0,0,0))
        self._paint_border(p,w,h)
        self._paint_wave(p,w,h)
        p.end()

    def _paint_border(self, p, w, h):
        r,g,b = self._color.red(), self._color.green(), self._color.blue()
        if not self._glow_active:
            p.setPen(QPen(QColor(r,g,b,22),1)); p.setBrush(Qt.NoBrush)
            p.drawRect(1,1,w-2,h-2); return
        a = self._glow_alpha
        layers = [(20,9,0.06),(16,7,0.10),(13,6,0.15),(10,5,0.22),
                  (8,4,0.30),(6,3,0.38),(4,2,0.48),(3,2,0.58),(2,1,0.72),(1,1,0.92)]
        p.setBrush(Qt.NoBrush)
        for inset,thick,am in layers:
            p.setPen(QPen(QColor(r,g,b,int(255*a*am)),thick))
            p.drawRect(inset,inset,w-inset*2,h-inset*2)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(r,g,b,int(200*a))))
        for cx,cy in [(0,0),(w,0),(0,h),(w,h)]:
            p.drawEllipse(cx-5,cy-5,10,10)

    def _paint_wave(self, p, w, h):
        bars = self._wave.BARS; amps = self._wave.amplitudes
        bw=3; gap=5; x0=(w-bars*(bw+gap))//2; cy=h-100; maxh=60
        r,g,b = self._color.red(),self._color.green(),self._color.blue()
        p.setPen(Qt.NoPen)
        for i,amp in enumerate(amps):
            bh = max(2,int(amp*maxh)); x = x0+i*(bw+gap)
            bright = 1.0-abs(i-bars//2)/(bars//2)*0.45
            gt = QLinearGradient(x,cy-bh,x,cy)
            gt.setColorAt(0,  QColor(r,g,b,int(35*bright)))
            gt.setColorAt(0.5,QColor(r,g,b,int(150*bright)))
            gt.setColorAt(1.0,QColor(r,g,b,int(230*bright)))
            p.setBrush(QBrush(gt)); p.drawRoundedRect(x,cy-bh,bw,bh,1,1)
            gb = QLinearGradient(x,cy,x,cy+bh)
            gb.setColorAt(0.0,QColor(r,g,b,int(230*bright)))
            gb.setColorAt(0.5,QColor(r,g,b,int(150*bright)))
            gb.setColorAt(1.0,QColor(r,g,b,int(35*bright)))
            p.setBrush(QBrush(gb)); p.drawRoundedRect(x,cy,bw,bh,1,1)


# ─── Gesture Camera Overlay ───────────────────────────────────────────────────
class GestureOverlay(QWidget):
    """
    Floating camera window — always on top, top-right corner.
    Shown when gesture mode is active.
    """
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setFixedSize(300, 240)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        # Position top-right
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width()-315, 15)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4,4,4,4)
        layout.setSpacing(3)

        # Camera frame
        self._cam_label = QLabel()
        self._cam_label.setFixedSize(292,210)
        self._cam_label.setAlignment(Qt.AlignCenter)
        self._cam_label.setStyleSheet(
            "background: rgba(0,0,0,0.85);"
            "border: 2px solid rgba(0,255,150,0.8);"
            "border-radius: 8px;"
            "color: rgba(0,255,150,0.6);"
            "font-size: 12px;"
        )
        self._cam_label.setText("📷  Camera loading...")

        # Status bar
        status = QLabel("GESTURE MODE  —  move your hand")
        status.setFont(QFont("Courier New", 8, QFont.Bold))
        status.setStyleSheet(
            "color: rgba(0,255,150,0.75); background: transparent; letter-spacing: 2px;"
        )
        status.setAlignment(Qt.AlignCenter)

        layout.addWidget(self._cam_label)
        layout.addWidget(status)
        self.hide()

    def update_frame(self, rgb_frame):
        if rgb_frame is None: return
        import numpy as np
        h,w,ch = rgb_frame.shape
        img = QImage(rgb_frame.data, w, h, ch*w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(292,210, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._cam_label.setPixmap(pix)


# ─── Main Window ─────────────────────────────────────────────────────────────
class MotionAIWindow(QMainWindow):

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.bus       = event_bus
        self._bridge   = Bridge()
        self._mode     = "normal"
        self._wave     = WaveformData()
        self._tts_busy = False

        self._init_modules()
        self._setup_window()
        self._setup_ui()
        self._setup_timers()
        self._connect_signals()
        self._subscribe_bus()

    # ── Modules ───────────────────────────────────────────────────────────────
    def _init_modules(self):
        from llm_client         import LLMClient
        from intent_executor    import IntentExecutor
        from tts_engine         import TTSEngine
        from gesture_controller import GestureController
        from counsellor_module  import CounsellorModule
        from wake_listener      import CommandListener

        self._llm        = LLMClient()
        self._executor   = IntentExecutor(self.bus)
        self._tts        = TTSEngine(self.bus)
        self._gesture    = GestureController(self.bus)
        self._counsellor = CounsellorModule(self.bus, self._llm)
        self._cmd        = CommandListener(self.bus)

    # ── Window ────────────────────────────────────────────────────────────────
    def _setup_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowTitle("MotionAI")
        self._sw, self._sh = screen.width(), screen.height()

    def _setup_ui(self):
        # Transparent canvas (border + waveform only)
        self._canvas = MotionCanvas(self._wave, self)
        self._canvas.setGeometry(0,0,self._sw,self._sh)
        self.setCentralWidget(self._canvas)

        # Status label — full width with word wrap
        lw = self._sw - 200
        self._label = QLabel(self._canvas)
        self._label.setGeometry(100, self._sh//2-70, lw, 140)
        self._label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._label.setWordWrap(True)
        font = QFont("Helvetica Neue", 18, QFont.Light)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
        self._label.setFont(font)
        self._label.setStyleSheet("color: rgba(210,255,240,0.92); background: transparent;")
        self._set_label(f'Say  "hello"  to  wake  me')

        # Text input (hidden)
        iw = min(620, self._sw-160)
        self._input = QLineEdit(self._canvas)
        self._input.setPlaceholderText("Type a command and press Enter...")
        self._input.setFont(QFont("Helvetica Neue",14))
        self._input.setGeometry((self._sw-iw)//2, self._sh-74, iw, 46)
        self._input.setStyleSheet("""
            QLineEdit {
                background: rgba(0,0,0,0.60);
                color: rgba(210,255,235,0.95);
                border: 1px solid rgba(0,230,170,0.45);
                border-radius: 23px; padding: 10px 22px;
            }
            QLineEdit:focus { border: 1px solid rgba(0,230,170,0.90); }
        """)
        self._input.hide()
        self._input.returnPressed.connect(self._on_typed)

        # Hint
        hint = QLabel("Double-click to type  ·  Space = listen  ·  ESC = hide", self._canvas)
        hint.setFont(QFont("Helvetica Neue",10))
        hint.setStyleSheet("color: rgba(140,200,170,0.30); background: transparent;")
        hint.setAlignment(Qt.AlignCenter)
        hint.setGeometry(0, self._sh-20, self._sw, 16)

        # Gesture overlay (separate floating window)
        self._gesture_overlay = GestureOverlay()

        self._canvas.mouseDoubleClickEvent = self._toggle_input

    # ── Timers ────────────────────────────────────────────────────────────────
    def _setup_timers(self):
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(40)

        self._clear_timer = QTimer()
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._maybe_clear)

    def _tick(self):
        self._wave.tick(); self._canvas.tick_glow(); self._canvas.update()

    def _maybe_clear(self):
        if not self._tts_busy: self._set_label("")

    # ── Signal wiring ─────────────────────────────────────────────────────────
    def _connect_signals(self):
        self._bridge.wake.connect(self._on_wake)
        self._bridge.speech.connect(self._on_speech)
        self._bridge.response.connect(self._on_response)
        self._bridge.mode_change.connect(self._on_mode_change)
        self._bridge.tts_start.connect(self._on_tts_start)
        self._bridge.tts_done.connect(self._on_tts_done)
        self._bridge.mic_active.connect(self._wave.set_mic)
        self._bridge.gesture_frame.connect(self._on_gesture_frame)
        self._bridge.do_exit.connect(self._final_exit)

    def _subscribe_bus(self):
        self.bus.subscribe(Events.WAKE_DETECTED,
            lambda d: self._bridge.wake.emit())
        self.bus.subscribe(Events.SPEECH_RECOGNIZED,
            lambda d: self._bridge.speech.emit(d["text"]))
        self.bus.subscribe(Events.ASSISTANT_RESPONSE,
            lambda d: self._bridge.response.emit(d.get("text","")))
        self.bus.subscribe(Events.MODE_CHANGE,
            lambda d: self._bridge.mode_change.emit(d["mode"]))
        self.bus.subscribe(Events.TTS_DONE,
            lambda d: self._bridge.tts_done.emit())
        self.bus.subscribe("tts_started",
            lambda d: self._bridge.tts_start.emit(d.get("text","")))
        self.bus.subscribe("mic_active",
            lambda d: self._bridge.mic_active.emit(d.get("active",False)))
        self.bus.subscribe("mic_listening",
            lambda d: self._bridge.mic_active.emit(d.get("active",False)))
        self.bus.subscribe(Events.GESTURE_FRAME,
            lambda d: self._bridge.gesture_frame.emit(d.get("frame")))
        self.bus.subscribe(Events.SYSTEM_EXIT,
            lambda d: self._bridge.do_exit.emit())

    # ── Handlers ──────────────────────────────────────────────────────────────
    @Slot()
    def _on_wake(self):
        self._canvas.set_glow(True)
        self._canvas.set_color(QColor(0,230,170))
        self._set_label(f"Hi {USER_NAME}!  Fetching weather...")

        def greet():
            from services.weather import build_greeting
            import subprocess
            from core.config import APP_PATHS

            greeting = build_greeting(USER_NAME)
            self._bridge.response.emit(greeting)
            self._tts.speak(greeting)

            username = os.getenv("USERNAME","User")
            for app in ["chrome","vscode","whatsapp"]:
                path = APP_PATHS.get(app,"").replace("{username}",username)
                try:
                    if path and os.path.exists(path): subprocess.Popen([path])
                except Exception as e:
                    print(f"[UI] {app}: {e}")

        threading.Thread(target=greet, daemon=True).start()

    @Slot(str)
    def _on_speech(self, text: str):
        print(f"[UI] Speech: '{text}'")
        self._set_label(f"You:  {text}")

        lower = text.lower().strip()
        for kp in KILL_PHRASES:
            if kp in lower:
                self._goodbye()
                return

        self._handle_command(text)

    @Slot(str)
    def _on_response(self, text: str):
        self._set_label(text)
        self._clear_timer.start(10000)

    @Slot(str)
    def _on_tts_start(self, text: str):
        self._tts_busy = True
        self._wave.set_speaking(True)
        self._canvas.set_color(QColor(0,190,255))
        self._clear_timer.stop()

    @Slot()
    def _on_tts_done(self):
        self._tts_busy = False
        self._wave.set_speaking(False)
        self._canvas.set_color(QColor(0,230,170))
        self._clear_timer.start(3000)

    @Slot(str)
    def _on_mode_change(self, mode: str):
        self._mode = mode
        colors = {"normal":QColor(0,230,170),"gesture":QColor(0,255,120),"counsellor":QColor(160,100,255)}
        labels = {"normal":"Ready","gesture":"Gesture mode — move your hand","counsellor":"I'm here for you. What's on your mind?"}
        self._canvas.set_color(colors.get(mode, QColor(0,230,170)))
        self._set_label(labels.get(mode,""))

        if mode == "gesture":
            self._gesture.start()
            self._gesture_overlay.show()
        else:
            self._gesture.stop()
            self._gesture_overlay.hide()

        # Counsellor: speak opening line
        if mode == "counsellor":
            def opening():
                msg = self._counsellor.get_opening_message()
                self._bridge.response.emit(msg)
                self._tts.speak(msg)
            threading.Thread(target=opening, daemon=True).start()

    @Slot(object)
    def _on_gesture_frame(self, frame):
        """Update gesture camera overlay."""
        if frame is not None:
            self._gesture_overlay.update_frame(frame)

    # ── Command pipeline ──────────────────────────────────────────────────────
    def _handle_command(self, text: str):
        def process():
            try:
                from llm_client import local_intent_parse

                # Counsellor mode: route to LLM directly
                if self._mode == "counsellor":
                    response = self._llm.chat(text, mode="counsellor")
                    if response:
                        self._bridge.response.emit(response)
                        self._tts.speak(response)
                    return

                # Emotional trigger → switch to counsellor
                if self._counsellor.check_emotional_trigger(text):
                    self.bus.publish(Events.MODE_CHANGE, {"mode": "counsellor"})
                    return

                # Local intent (instant)
                local_action = local_intent_parse(text)
                if local_action:
                    spoken = self._quick_reply(local_action, text)

                    # Weather and time actions publish their own response
                    if local_action["type"] in ("get_weather","get_time"):
                        self._executor.execute(local_action)
                        return

                    self._bridge.response.emit(spoken)
                    self._tts.speak(spoken)
                    self._executor.execute(local_action)
                    return

                # LLM for everything else
                print(f"[UI] → LLM: '{text}'")
                response = self._llm.chat(text, mode="normal")
                print(f"[UI] ← LLM: '{response[:100]}'")
                clean  = self._llm.clean_response(response)
                action = self._llm.extract_action(response)

                if clean:
                    self._bridge.response.emit(clean)
                    self._tts.speak(clean)
                if action:
                    self._executor.execute(action)

            except Exception as e:
                import traceback
                print(f"[UI] Pipeline error: {e}")
                traceback.print_exc()

        threading.Thread(target=process, daemon=True).start()

    def _quick_reply(self, action: dict, original: str) -> str:
        t = action.get("type",""); p = action.get("params",{})
        app = p.get("app","").replace("vscode","VS Code").replace("chrome","Chrome").replace("apple_music","Apple Music")
        replies = {
            "open_app":      lambda: f"Opening {app.title()} for you.",
            "search_web":    lambda: f"Searching for {p.get('query','that')}.",
            "open_url":      lambda: f"Opening {p.get('url','')}.",
            "send_whatsapp": lambda: f"Sending message to {p.get('contact','them')} on WhatsApp.",
            "volume_up":     lambda: "Turning up the volume.",
            "volume_down":   lambda: "Turning down the volume.",
            "scroll_up":     lambda: "Scrolling up.",
            "scroll_down":   lambda: "Scrolling down.",
            "screenshot":    lambda: "Screenshot taken.",
            "shutdown":      lambda: "Shutting down in 10 seconds.",
            "restart":       lambda: "Restarting in 10 seconds.",
            "mode_change":   lambda: f"Switching to {p.get('mode','normal')} mode.",
            "media_control": lambda: f"{p.get('action','playing').capitalize()}.",
            "media_play_song": lambda: f"Searching for {p.get('song','')}.",
        }
        fn = replies.get(t)
        return fn() if fn else "Done."

    # ── Goodbye ───────────────────────────────────────────────────────────────
    def _goodbye(self):
        """Speak goodbye, show on screen, then kill the process completely."""
        self._set_label(GOODBYE_TEXT)
        self._canvas.set_color(QColor(200,150,255))
        self._wave.set_speaking(True)

        def do_exit():
            import time
            # Speak the goodbye
            self._tts.speak(GOODBYE_TEXT)
            # Wait for it to finish (max 5s)
            deadline = time.time() + 5
            while self._tts.is_speaking and time.time() < deadline:
                time.sleep(0.1)
            time.sleep(0.3)
            # Hard kill — terminates terminal + process
            print("[MotionAI] 👋 Goodbye!")
            os._exit(0)

        threading.Thread(target=do_exit, daemon=True).start()

    @Slot()
    def _final_exit(self):
        """Called via SYSTEM_EXIT bus event."""
        self._goodbye()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _set_label(self, text: str):
        self._label.setText(text)

    def _toggle_input(self, _):
        if self._input.isVisible():
            self._input.hide(); self._input.clear()
        else:
            self._input.show(); self._input.setFocus()

    def _on_typed(self):
        text = self._input.text().strip()
        if text:
            self._input.clear(); self._input.hide()
            self._bridge.speech.emit(text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self._input.isVisible(): self._input.hide()
            else: self._canvas.set_glow(False); self._set_label("")
        elif event.key() == Qt.Key_Space and not self._input.isVisible():
            # Interrupt AI + listen
            self.bus.publish(Events.TTS_INTERRUPT, {})
            self._set_label("🎤  Listening...")
            threading.Thread(target=self._cmd.listen_once, daemon=True).start()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self._tts.stop()
        self._gesture.stop()
        self._gesture_overlay.hide()
        event.accept()
        os._exit(0)