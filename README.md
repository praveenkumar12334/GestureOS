# GestureOS — Hand Gesture Control System

## Project Structure

```
GestureOS/
├── app.py              ← Flask + SocketIO backend server
├── gesture_engine.py   ← Gesture detection engine (your main.py refactored)
├── index.html          ← Website frontend (control panel)
├── requirements.txt    ← Python dependencies
└── README.md
```

## How It Works

```
index.html  ←→  Socket.IO  ←→  app.py  ←→  gesture_engine.py
 (Website)      (Real-time)   (Flask)      (Camera + MediaPipe)
```

- The website toggle button sends a signal to Flask via Socket.IO
- Flask starts/stops the gesture engine in a background thread
- The gesture engine sends live events back to the website in real-time
- The website displays current gesture, session time, hands detected, etc.

## Setup & Run

### 1. Create virtual environment
```
python -m venv gesture_env
gesture_env\Scripts\activate
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Run the server
```
python app.py
```

### 4. Open the website
Open your browser and go to:
```
http://localhost:5000
```

### 5. Use the toggle
- Click the toggle button on the website to START the gesture engine
- The camera window will open
- All gesture events will show live on the website
- Click toggle again to STOP

## Gestures Reference

| Gesture         | Hand Position                              |
|-----------------|--------------------------------------------|
| Cursor Move     | Index finger only pointing up              |
| Single Click    | Thumb tip touches Index tip                |
| Double Click    | Thumb + Index touch twice < 0.4s           |
| Right Click     | Middle finger only pointing up             |
| Scroll Up       | Index + Middle up, hand raised high        |
| Scroll Down     | Index + Middle up, hand lowered            |
| Zoom In         | Middle + Ring up, spread far apart         |
| Zoom Out        | Middle + Ring up, held close together      |
| Volume Up       | Index + Pinky up, spread far apart         |
| Volume Down     | Index + Pinky up, held close together      |
| Brightness Up   | Pinky only up, thumb far from pinky        |
| Brightness Down | Pinky only up, thumb close to pinky        |
| Screenshot      | All 4 fingers up                           |
| Lock System     | Closed fist, hold 2 seconds                |

## Notes
- Works on Windows only (pycaw for volume, rundll32 for lock)
- Camera must not be in use by another app
- Press Q in the camera window to stop manually
