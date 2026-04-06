# 🤖 MotionAI – AI Gesture & Voice Controlled Assistant

MotionAI is a **modular AI-based desktop assistant** that combines:

* 🖐️ Gesture Control (Computer Vision)
* 🎙️ Voice Interaction (TTS + Wake Word)
* 🧠 Intent Processing System
* ⚙️ Modular AI Services

It allows users to control their system using **hand gestures + voice commands**, creating a fully touchless AI experience.

---

## 🚀 Key Capabilities

### 🖐️ Gesture Control

* Cursor movement
* Click / Right Click / Double Click
* Drag & Drop
* Scrolling
* Volume control

Handled via:

```
gesture_controller.py
```

---

### 🎙️ Voice Assistant System

* Wake word detection
* Speech-to-text processing
* Text-to-speech response

Core files:

```
wake_listener.py
tts_engine.py
assistant.py
```

---

### 🧠 AI Intent Engine

* Processes commands intelligently
* Routes tasks to appropriate modules

Core files:

```
intent_executor.py
llm_client.py
event_bus.py
```

---

### 🧩 Services Layer

Handles external integrations and utilities

```
services/
 └── weather.py
```

---

### 🖥️ UI Layer

Basic interface for system interaction

```
ui/
 └── main_ui.py
```

---

## 🧠 Architecture Overview

```
User (Voice / Gesture)
        ↓
Wake Listener / Gesture Controller
        ↓
Assistant Core
        ↓
Intent Executor
        ↓
Services / System Actions
        ↓
Response via TTS / UI
```

---

## 📁 Project Structure

```
MotionAI/
│
├── core/
│   ├── assistant.py
│   ├── config.py
│   └── event_bus.py
│
├── services/
│   └── weather.py
│
├── ui/
│   └── main_ui.py
│
├── gesture_controller.py
├── counsellor_module.py
├── intent_executor.py
├── llm_client.py
├── tts_engine.py
├── wake_listener.py
├── startup_helper.py
├── main.py
│
├── requirements.txt
├── install.bat
├── build_exe.bat
├── MotionAI.spec
│
├── .env.template
├── .gitignore
└── assets/
```

---

## ⚙️ Requirements

* **Python 3.10 (STRICTLY REQUIRED)**
* Webcam (for gesture control)
* Microphone (for voice input)
* Windows OS (recommended)

---

## 📦 Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Allen1406/MotionAI.git
cd MotionAI
```

---

### 2️⃣ Create Virtual Environment (Python 3.10)

```bash
python3.10 -m venv venv
```

Activate:

```bash
venv\Scripts\activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### ⚠️ MediaPipe Fix

If installation fails:

```bash
pip install mediapipe==0.10.7
```

---

## ▶️ Run the System

```bash
python main.py
```

---

## 🧩 Core Modules Explained

### `main.py`

Entry point of the system — initializes all components.

---

### `gesture_controller.py`

Handles all hand tracking and gesture-based interactions.

---

### `wake_listener.py`

Continuously listens for activation keyword.

---

### `tts_engine.py`

Converts system responses into speech.

---

### `intent_executor.py`

Executes commands based on detected intent.

---

### `llm_client.py`

Handles AI/LLM-based reasoning or responses.

---

### `assistant.py`

Central orchestrator connecting all modules.

---

### `event_bus.py`

Manages communication between modules (decoupled architecture).

---

### `counsellor_module.py`

Special conversational or advisory AI mode.

---

### `startup_helper.py`

Handles system initialization and startup tasks.

---

## ⚠️ Important Notes

* ❌ Do NOT upload `venv/` to GitHub
* ✅ Use `.env.template` for environment variables
* 🎥 Ensure proper lighting for gesture detection
* 🎤 Ensure microphone permissions are enabled

---

## 🛠 Build Executable (Optional)

```bash
build_exe.bat
```

Uses:

```
MotionAI.spec
```

---

## 🔮 Future Scope

* AI-based gesture learning
* Multi-device sync
* Advanced UI dashboard
* Emotion-aware assistant
* Offline LLM integration

---

## 👨‍💻 Author

**Allen**

---

## ⭐ Support

If you found this project useful, give it a ⭐ on GitHub!
