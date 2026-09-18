from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
import threading

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'gestureos_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")  # removed async_mode

gesture_thread  = None
gesture_running = False

import gesture_engine as ge

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@socketio.on('connect')
def on_connect():
    print("Client connected")
    emit('status', {'active': False, 'message': 'Connected to GestureOS server'})

@socketio.on('disconnect')
def on_disconnect():
    global gesture_running
    gesture_running = False
    ge.stop()

@socketio.on('toggle_gesture')
def handle_toggle(data):
    global gesture_thread, gesture_running
    print(f"Toggle received: {data}")   # ← debug print

    if data.get('active'):
        if not gesture_running:
            gesture_running = True
            gesture_thread = threading.Thread(
                target=ge.run,
                args=(socketio, lambda: gesture_running),
                daemon=True
            )
            gesture_thread.start()
            emit('status', {'active': True, 'message': 'Gesture engine started'})
    else:
        gesture_running = False
        ge.stop()
        emit('status', {'active': False, 'message': 'Gesture engine stopped'})

if __name__ == '__main__':
    print("=" * 45)
    print("  GestureOS Server")
    print("  Open browser → http://localhost:5000")
    print("=" * 45)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)