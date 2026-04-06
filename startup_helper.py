"""
startup_helper.py
Optional: Register MotionAI to start with Windows.
Run this script once to add MotionAI to startup.
"""

import os
import sys
import winreg
import subprocess


def add_to_startup(exe_path: str = None):
    """Add MotionAI.exe to Windows startup registry."""
    if exe_path is None:
        # Detect: are we running from .exe or .py?
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath("main.py")

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "MotionAI", 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        print(f"[Startup] MotionAI added to startup: {exe_path}")
        return True
    except Exception as e:
        print(f"[Startup] Failed to add startup entry: {e}")
        return False


def remove_from_startup():
    """Remove MotionAI from Windows startup."""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "MotionAI")
        winreg.CloseKey(key)
        print("[Startup] MotionAI removed from startup")
        return True
    except FileNotFoundError:
        print("[Startup] MotionAI was not in startup")
        return False
    except Exception as e:
        print(f"[Startup] Error removing startup entry: {e}")
        return False


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "add"
    if action == "remove":
        remove_from_startup()
    else:
        add_to_startup()