"""
intent_executor.py
All system actions including:
- Apple Music / media controls (Windows: uses keyboard media keys + iTunes COM)
- Weather answered directly
- Time answered directly
- Proper app launching
- WhatsApp Desktop only
"""

import os
import sys
import subprocess
import time
import webbrowser
import urllib.parse
import pyautogui
from datetime import datetime
from core.config import APP_PATHS, USER_NAME
from core.event_bus import EventBus, Events

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0.05


class IntentExecutor:

    def __init__(self, event_bus: EventBus):
        self.bus       = event_bus
        self._username = os.getenv("USERNAME", "User")

    def execute(self, action: dict) -> str:
        t = action.get("type", "")
        p = action.get("params", {})

        handlers = {
            "open_app":        self._open_app,
            "open_file":       self._open_file,
            "search_file":     self._search_file,
            "open_url":        self._open_url,
            "search_web":      self._search_web,
            "send_whatsapp":   self._send_whatsapp,
            "volume_up":       self._volume_up,
            "volume_down":     self._volume_down,
            "scroll_up":       self._scroll_up,
            "scroll_down":     self._scroll_down,
            "shutdown":        self._shutdown,
            "restart":         self._restart,
            "screenshot":      self._screenshot,
            "type_text":       self._type_text,
            "mode_change":     self._mode_change,
            "media_control":   self._media_control,
            "media_play_song": self._media_play_song,
            "get_weather":       self._get_weather,
            "get_time":          self._get_time,
            "show_capabilities": self._show_capabilities,
            "get_news":          self._get_news,
            "read_screen":       self._read_screen,
        }

        handler = handlers.get(t)
        if handler:
            try:
                result = handler(p)
                print(f"[Executor] ✅ {t}: {result}")
                return result
            except Exception as e:
                msg = f"Failed {t}: {e}"
                print(f"[Executor] ❌ {msg}")
                self.bus.publish(Events.ERROR, {"message": msg})
                return msg
        return f"Unknown action: {t}"

    # ── Apps ──────────────────────────────────────────────────────────────────
    def _open_app(self, p: dict) -> str:
        name = p.get("app", "").lower()
        path = APP_PATHS.get(name, "").replace("{username}", self._username)

        if name == "explorer":
            subprocess.Popen(["explorer", p.get("folder","")] if p.get("folder") else ["explorer"])
            return "Opened File Explorer"

        if name == "apple_music":
            return self._open_apple_music()

        if path and os.path.exists(path):
            subprocess.Popen([path])
            return f"Opened {name}"

        try:
            subprocess.Popen(name, shell=True)
            return f"Launched {name}"
        except Exception as e:
            return f"Could not open {name}: {e}"

    def _open_apple_music(self) -> str:
        """Open Apple Music on Windows (Microsoft Store app)."""
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA",""),
                         "Microsoft","WindowsApps","AppleInc.AppleMusicWin_nzyj5cx40ttqa","AppleMusic.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                subprocess.Popen([c])
                return "Opening Apple Music"

        # Try via Windows Store package
        try:
            result = subprocess.run(
                ["powershell","-c",
                 "Get-AppxPackage *AppleMusic* | Select-Object -ExpandProperty InstallLocation"],
                capture_output=True, text=True, timeout=5
            )
            loc = result.stdout.strip()
            if loc:
                exe = os.path.join(loc,"AppleMusic.exe")
                if os.path.exists(exe):
                    subprocess.Popen([exe])
                    return "Opening Apple Music"
        except Exception: pass

        # Last resort: start via URI
        os.startfile("itmss://")
        return "Trying to open Apple Music"

    # ── Media controls ────────────────────────────────────────────────────────
    def _media_control(self, p: dict) -> str:
        action = p.get("action","play")
        key_map = {
            "play":     "playpause",
            "pause":    "playpause",
            "next":     "nexttrack",
            "previous": "prevtrack",
        }
        key = key_map.get(action, "playpause")
        pyautogui.press(key)
        return f"Media: {action}"

    def _media_play_song(self, p: dict) -> str:
        song = p.get("song","")
        # Search and play via Spotify web (works cross-app)
        encoded = urllib.parse.quote_plus(song)
        webbrowser.open(f"https://open.spotify.com/search/{encoded}")
        return f"Searching for: {song}"

    # ── Weather & Time (answered directly) ────────────────────────────────────
    def _get_weather(self, p: dict) -> str:
        from services.weather import get_weather_answer
        answer = get_weather_answer()
        # Publish as response so UI shows and TTS speaks it
        self.bus.publish(Events.ASSISTANT_RESPONSE, {"text": answer})
        self.bus.publish(Events.TTS_SPEAK, {"text": answer})
        return "Weather fetched"

    def _get_time(self, p: dict) -> str:
        now    = datetime.now()
        ts     = now.strftime("%I:%M %p")
        answer = f"The current time is {ts}."
        self.bus.publish(Events.ASSISTANT_RESPONSE, {"text": answer})
        self.bus.publish(Events.TTS_SPEAK, {"text": answer})
        return "Time fetched"

    def _show_capabilities(self, p: dict) -> str:
        from llm_client import CAPABILITIES_ANSWER
        self.bus.publish(Events.ASSISTANT_RESPONSE, {"text": CAPABILITIES_ANSWER})
        self.bus.publish(Events.TTS_SPEAK, {"text": CAPABILITIES_ANSWER})
        return "Capabilities shown"

    def _get_news(self, p: dict) -> str:
        from services.news import build_headlines_answer
        category = p.get("category", "general")
        self.bus.publish(Events.ASSISTANT_RESPONSE,
            {"text": f"Fetching {category} news..."})
        # Run in thread so it doesn't block
        import threading
        def fetch():
            answer = build_headlines_answer(category=category, count=5)
            self.bus.publish(Events.ASSISTANT_RESPONSE, {"text": answer})
            self.bus.publish(Events.TTS_SPEAK, {"text": answer})
        threading.Thread(target=fetch, daemon=True).start()
        return "Fetching news"

    def _read_screen(self, p: dict) -> str:
        from services.screen_reader import read_screen
        question = p.get("question", "")
        self.bus.publish(Events.ASSISTANT_RESPONSE,
            {"text": "Reading your screen..."})
        import threading
        def do_read():
            result = read_screen(question=question)
            self.bus.publish(Events.ASSISTANT_RESPONSE, {"text": result})
            self.bus.publish(Events.TTS_SPEAK, {"text": result})
        threading.Thread(target=do_read, daemon=True).start()
        return "Reading screen"

    # ── File System ───────────────────────────────────────────────────────────
    def _open_file(self, p: dict) -> str:
        path = p.get("path","")
        if os.path.exists(path):
            os.startfile(path)
            return f"Opened {path}"
        return f"File not found: {path}"

    def _search_file(self, p: dict) -> str:
        query = p.get("query","")
        root  = p.get("dir", os.path.expanduser("~"))
        found = []
        for r, _, files in os.walk(root):
            for f in files:
                if query.lower() in f.lower():
                    found.append(os.path.join(r,f))
                if len(found)>=10: break
        if found:
            self.bus.publish(Events.ASSISTANT_RESPONSE,
                {"text": f"Found {len(found)} file(s): " + ", ".join(found[:3])})
            return f"Found {len(found)} files"
        return f"No files found for '{query}'"

    # ── Browser ───────────────────────────────────────────────────────────────
    def _open_url(self, p: dict) -> str:
        url = p.get("url","")
        if not url.startswith("http"): url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url}"

    def _search_web(self, p: dict) -> str:
        q = p.get("query","")
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}")
        return f"Searched: {q}"

    # ── WhatsApp Desktop ──────────────────────────────────────────────────────
    def _send_whatsapp(self, p: dict) -> str:
        contact = p.get("contact","").strip()
        message = p.get("message","").strip()
        if not contact or not message:
            return "Missing contact or message"

        wa_path = self._find_whatsapp()
        if not wa_path:
            return "WhatsApp Desktop not found"

        if not self._is_running("WhatsApp.exe"):
            subprocess.Popen([wa_path])
            time.sleep(5)
        else:
            time.sleep(1)

        self._focus_window("WhatsApp")
        time.sleep(1)

        pyautogui.hotkey("ctrl","f")
        time.sleep(0.8)
        pyautogui.hotkey("ctrl","a")
        pyautogui.press("delete")
        time.sleep(0.2)
        pyautogui.typewrite(contact, interval=0.07)
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("tab")
        time.sleep(0.3)

        for ch in message:
            pyautogui.typewrite(ch, interval=0.04)
        pyautogui.press("enter")
        return f"Message sent to {contact}"

    def _find_whatsapp(self) -> str | None:
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA",""), "Microsoft","WindowsApps","WhatsApp.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA",""), "WhatsApp","WhatsApp.exe"),
            os.path.join(os.environ.get("APPDATA",""),      "WhatsApp","WhatsApp.exe"),
            APP_PATHS.get("whatsapp","").replace("{username}", self._username),
        ]
        for c in candidates:
            if c and os.path.exists(c): return c
        try:
            r = subprocess.run(
                ["powershell","-c",
                 "Get-AppxPackage *WhatsApp* | Select-Object -ExpandProperty InstallLocation"],
                capture_output=True, text=True, timeout=5)
            loc = r.stdout.strip()
            if loc:
                c = os.path.join(loc,"WhatsApp.exe")
                if os.path.exists(c): return c
        except: pass
        return None

    def _is_running(self, name: str) -> bool:
        try:
            r = subprocess.run(["tasklist","/FI",f"IMAGENAME eq {name}"],
                               capture_output=True, text=True)
            return name.lower() in r.stdout.lower()
        except: return False

    def _focus_window(self, title_keyword: str):
        try:
            import win32gui, win32con
            hwnds = []
            def cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    if title_keyword.lower() in win32gui.GetWindowText(hwnd).lower():
                        hwnds.append(hwnd)
            win32gui.EnumWindows(cb, None)
            if hwnds:
                win32gui.ShowWindow(hwnds[0], win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnds[0])
        except Exception as e:
            print(f"[Executor] Focus error: {e}")

    # ── Volume ────────────────────────────────────────────────────────────────
    def _volume_up(self, p: dict) -> str:
        for _ in range(p.get("steps",5)): pyautogui.press("volumeup")
        return "Volume up"

    def _volume_down(self, p: dict) -> str:
        for _ in range(p.get("steps",5)): pyautogui.press("volumedown")
        return "Volume down"

    def _scroll_up(self, p: dict) -> str:
        pyautogui.scroll(p.get("clicks",5)); return "Scrolled up"

    def _scroll_down(self, p: dict) -> str:
        pyautogui.scroll(-p.get("clicks",5)); return "Scrolled down"

    # ── System ────────────────────────────────────────────────────────────────
    def _shutdown(self, p: dict) -> str:
        d = p.get("delay_seconds",10)
        subprocess.run(["shutdown","/s","/t",str(d)])
        return f"Shutdown in {d}s"

    def _restart(self, p: dict) -> str:
        d = p.get("delay_seconds",10)
        subprocess.run(["shutdown","/r","/t",str(d)])
        return f"Restart in {d}s"

    def _screenshot(self, p: dict) -> str:
        path = p.get("path", os.path.join(os.path.expanduser("~"),"Desktop","screenshot.png"))
        pyautogui.screenshot().save(path)
        return f"Screenshot: {path}"

    def _type_text(self, p: dict) -> str:
        pyautogui.typewrite(p.get("text",""), interval=0.04)
        return "Typed"

    def _mode_change(self, p: dict) -> str:
        mode = p.get("mode","normal")
        self.bus.publish(Events.MODE_CHANGE, {"mode": mode})
        return f"Mode: {mode}"