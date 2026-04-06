# MotionAI.spec
# PyInstaller build configuration for MotionAI Windows executable
# Build with: pyinstaller MotionAI.spec

import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# ─── Collect all data/binaries from key packages ─────────────────────────────
mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all('mediapipe')
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all('cv2')
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')
speech_datas, speech_binaries, speech_hiddenimports = collect_all('speech_recognition')

# ─── Hidden imports list ─────────────────────────────────────────────────────
hidden_imports = [
    # PySide6
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtMultimedia',

    # OpenCV
    'cv2',
    'cv2.cv2',

    # MediaPipe
    'mediapipe',
    'mediapipe.python.solutions.hands',
    'mediapipe.python.solutions.drawing_utils',

    # Speech
    'speech_recognition',
    'pyaudio',

    # TTS
    'pyttsx3',
    'pyttsx3.drivers',
    'pyttsx3.drivers.sapi5',  # Windows SAPI
    'gtts',
    'playsound',

    # Networking
    'requests',
    'urllib3',
    'certifi',

    # System
    'pyautogui',
    'keyboard',
    'win32api',
    'win32con',
    'win32gui',

    # Utilities
    'numpy',
    'PIL',
    'PIL.Image',
    'json',
    'threading',
    'queue',
    'subprocess',
    'webbrowser',

    # MotionAI modules
    'core.config',
    'core.event_bus',
    'llm_client',
    'intent_executor',
    'tts_engine',
    'gesture_controller',
    'counsellor_module',
    'wake_listener',
    'services.weather',
    'ui.main_ui',
]

hidden_imports += mediapipe_hiddenimports
hidden_imports += cv2_hiddenimports
hidden_imports += speech_hiddenimports

# ─── Data files ──────────────────────────────────────────────────────────────
datas = [
    ('assets', 'assets'),      # UI assets
    ('core', 'core'),          # Core modules
    ('services', 'services'),  # Services
    ('ui', 'ui'),              # UI modules
]

datas += mediapipe_datas
datas += cv2_datas
datas += speech_datas

# ─── Analysis ────────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=mediapipe_binaries + cv2_binaries + pyside6_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',        # Not needed
        'matplotlib',     # Not needed
        'scipy',          # Not needed
        'pandas',         # Not needed
        'IPython',        # Not needed
        'jupyter',        # Not needed
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ─── PYZ archive ─────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ─── EXE ─────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MotionAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # ← No console window (GUI mode)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/motionai.ico',  # App icon
    version='version_info.txt',        # Windows version metadata
)

# ─── COLLECT (folder distribution) ───────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MotionAI',
)
