
# GestureOS — Hand Gesture Control System

GestureOS is a real-time, touch-free computer control system that uses a webcam and hand gestures to control the mouse and selected system functions.

The system detects hand landmarks using **MediaPipe Hands**, interprets predefined gestures, and performs corresponding computer actions using **PyAutoGUI** and other system-control libraries.

---

## 🚀 Features

GestureOS provides **14 gesture-based commands**:

| Gesture | Action |
|---|---|
| ☝️ Index Finger | Cursor Movement |
| 👆 Index + Middle | Left Click |
| ✌️ Index + Middle + Ring | Double Click |
| 🤟 Index + Middle + Ring + Pinky | Right Click |
| ☝️ Index + Ring | Scroll Up |
| 🤘 Middle + Ring | Scroll Down |
| 🤌 Middle + Ring — Far | Zoom In |
| 🤌 Middle + Ring — Near | Zoom Out |
| 🤙 Index + Pinky — Far | Volume Up |
| 🤙 Index + Pinky — Near | Volume Down |
| ✋ Four Fingers — Far | Brightness Up |
| ✋ Four Fingers — Near | Brightness Down |
| 🖐️ All Fingers | Screenshot |
| ✊ Closed Hand | Lock System |

> Gesture recognition uses hand landmark positions and finger-state detection. Near/Far gestures use the calculated distance between selected hand landmarks.

---

## 🧠 How It Works

GestureOS follows a simple real-time processing pipeline:

```text
Webcam
   ↓
OpenCV
   ↓
MediaPipe Hands
   ↓
21 Hand Landmarks
   ↓
Finger / Gesture Detection
   ↓
Gesture Mapping
   ↓
System Action
````

The web interface communicates with the Python backend using Socket.IO:

```text
┌───────────────┐
│   index.html  │
│ Web Interface │
└───────┬───────┘
        │
        │ Socket.IO
        ↓
┌───────────────┐
│    app.py     │
│ Flask Server  │
└───────┬───────┘
        │
        ↓
┌────────────────────┐
│ gesture_engine.py  │
│ Gesture Processing │
└─────────┬──────────┘
          │
          ↓
    Computer/System
       Controls
```

---

## 🛠️ Technologies Used

### Programming Language

* Python

### Computer Vision & Gesture Recognition

* OpenCV
* MediaPipe Hands

### Computer Control

* PyAutoGUI

### System Controls

* Pycaw
* Screen Brightness Control
* Windows system commands

### Backend

* Flask
* Flask-SocketIO

### Frontend

* HTML
* CSS
* JavaScript
* Socket.IO

---

## 📁 Project Structure

```text
GestureOS/
│
├── .gitignore
├── app.py
├── gesture_engine.py
├── index.html
├── pyvenv.cfg
├── README.md
└── requirements.txt
```

### File Description

| File                | Description                                      |
| ------------------- | ------------------------------------------------ |
| `app.py`            | Flask and Socket.IO server                       |
| `gesture_engine.py` | Main gesture detection and system-control engine |
| `index.html`        | GestureOS web interface                          |
| `requirements.txt`  | Required Python packages                         |
| `pyvenv.cfg`        | Python virtual-environment configuration         |
| `.gitignore`        | Git ignored-file configuration                   |
| `README.md`         | Project documentation                            |

---

## ⚙️ Requirements

* Windows operating system
* Python
* Working webcam
* Internet connection for installing dependencies

The project uses the following Python packages:

```text
opencv-python
mediapipe
pyautogui
pycaw
comtypes
screen-brightness-control
flask
flask-socketio
```

---

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/praveenkumar12334/GestureOS.git
```

### 2. Open the Project

```bash
cd GestureOS
```

### 3. Create a Virtual Environment

```bash
python -m venv gesture_env
```

### 4. Activate the Virtual Environment

On Windows PowerShell:

```powershell
gesture_env\Scripts\Activate.ps1
```

If PowerShell execution policy prevents activation, the environment can also be activated using Command Prompt:

```cmd
gesture_env\Scripts\activate
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Run GestureOS

```bash
python app.py
```

### 7. Open the Web Interface

Open a browser and visit:

```text
http://localhost:5000
```

---

## 🎥 Camera Setup

Before starting GestureOS:

1. Connect a working webcam.
2. Make sure no other application is currently using the camera.
3. Start the Flask application.
4. Open the GestureOS web interface.
5. Enable gesture control.
6. Position your hand clearly in front of the camera.

---

## 🎯 Gesture Detection

GestureOS uses **MediaPipe Hands** to detect hand landmarks.

Each detected hand contains:

```text
21 Hand Landmarks
```

The gesture engine analyzes the positions of the fingers using selected landmarks to determine whether fingers are extended or folded.

For gestures requiring depth-like detection, GestureOS calculates the distance between hand landmarks to classify the hand as **Near** or **Far**.

---

## 🖱️ Mouse Control

GestureOS can control the mouse using hand movements.

The cursor position is calculated from the detected hand position and mapped to the computer screen.

Supported mouse functions include:

* Cursor movement
* Left click
* Double click
* Right click
* Scroll up
* Scroll down

---

## 🔊 System Controls

GestureOS also provides gesture-based system controls:

### Volume

* Volume Up
* Volume Down

### Brightness

* Brightness Up
* Brightness Down

### Other Controls

* Zoom In
* Zoom Out
* Screenshot
* Lock System

---

## 📸 Screenshot

The screenshot gesture captures the current screen and saves it as a timestamped PNG file.

Example:

```text
screenshot_<timestamp>.png
```

---

## 🖥️ Platform

GestureOS is currently designed for:

```text
Windows
```

Some system-control functions depend on Windows-specific functionality.

---

## 🔒 Permissions & Security

GestureOS interacts directly with the computer's:

* Camera
* Mouse
* Screen
* Volume
* Brightness
* System lock functionality

Use the application only on a computer where you have permission to perform these actions.

---

## 🧪 Project Highlights

* Real-time hand tracking
* Webcam-based interaction
* 21-point hand landmark detection
* Finger-state based gesture recognition
* Near/Far gesture classification
* Touch-free mouse control
* System-level computer controls
* Flask + Socket.IO communication
* Interactive web-based control interface

---

## 🔮 Future Enhancements

Possible future improvements include:

* Custom gesture configuration
* User-defined gestures
* Multi-hand gesture support
* Improved gesture accuracy
* Gesture sensitivity controls
* Cross-platform system controls
* Gesture training/customization
* Performance optimization
* Additional accessibility features

---

## 👨‍💻 Project

**Project Name:** GestureOS
**Type:** Academic Project
**Domain:** Computer Vision / Human-Computer Interaction
**Language:** Python

---
