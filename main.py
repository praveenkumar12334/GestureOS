import cv2
import mediapipe as mp
import pyautogui
import time
import math
import os

# Volume Control
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Brightness Control
import screen_brightness_control as sbc

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

_stop_flag = False
_cap = None

def stop():
    global _stop_flag, _cap
    _stop_flag = True
    if _cap:
        _cap.release()
        _cap = None

def run(socketio, is_running_fn):
    global _stop_flag, _cap
    _stop_flag = False

    _cap = cv2.VideoCapture(0)

    if not _cap.isOpened():
        socketio.emit('gesture_event', {'gesture': 'ERROR', 'message': 'Camera not found'})
        return

    screen_w, screen_h = pyautogui.size()

    # Setup audio
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        vol_range = volume.GetVolumeRange()
        min_vol, max_vol = vol_range[0], vol_range[1]
        audio_available = True
    except Exception:
        audio_available = False
        min_vol, max_vol = -65.0, 0.0
        volume = None

    click_times = []
    last_screenshot_time = 0
    screenshot_cooldown = 2
    lock_hold_start = None
    last_emitted_gesture = None

    # Scroll: track movement direction
    prev_scroll_y = None
    scroll_move_threshold = 0.015  # min Y delta to trigger scroll

    # Brightness cooldown to avoid rapid firing
    last_brightness_time = 0
    brightness_cooldown = 0.5

    socketio.emit('engine_status', {
        'camera': True,
        'mediapipe': True,
        'engine': True
    })

    while is_running_fn() and not _stop_flag:
        ret, frame = _cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        hands_model = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        result = hands_model.process(rgb)
        hands_model.close()

        hands_detected = len(result.multi_hand_landmarks) if result.multi_hand_landmarks else 0
        socketio.emit('hands_count', {'count': hands_detected})

        current_gesture = None

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                lm = hand_landmarks.landmark
                thumb_tip  = lm[4]
                index_tip  = lm[8]
                middle_tip = lm[12]
                ring_tip   = lm[16]
                pinky_tip  = lm[20]

                # fingers[0]=index, fingers[1]=middle, fingers[2]=ring, fingers[3]=pinky
                # 1 = up, 0 = down
                fingers = [
                    1 if lm[tip].y < lm[tip - 2].y else 0
                    for tip in [8, 12, 16, 20]
                ]

                # Distances (2D in normalized coords)
                thumb_index_dist = math.hypot(thumb_tip.x - index_tip.x,  thumb_tip.y - index_tip.y)
                middle_ring_dist = math.hypot(middle_tip.x - ring_tip.x,  middle_tip.y - ring_tip.y)
                index_pinky_dist = math.hypot(index_tip.x - pinky_tip.x,  index_tip.y - pinky_tip.y)

                # Hand size = wrist to middle-finger-MCP distance
                # Larger value = hand is CLOSER to camera (near)
                # Smaller value = hand is FARTHER from camera (far)
                wrist      = lm[0]
                middle_mcp = lm[9]
                hand_size  = math.hypot(wrist.x - middle_mcp.x, wrist.y - middle_mcp.y)

                # Normalize distances by hand_size to make them depth-independent
                # For zoom/volume: compare finger spread relative to hand size
                # For brightness: hand_size itself tells distance from camera

                # -----------------------------------------------
                # 1. CURSOR MOVEMENT — Index finger only up
                # -----------------------------------------------
                if fingers == [1, 0, 0, 0]:
                    screen_x = int(index_tip.x * screen_w)
                    screen_y = int(index_tip.y * screen_h)
                    pyautogui.moveTo(screen_x, screen_y, duration=0.05)
                    current_gesture = 'Cursor Move'
                    cv2.putText(frame, "Cursor Move", (10, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 0), 2)

                # -----------------------------------------------
                # 2. SINGLE CLICK / 3. DOUBLE CLICK
                # Thumb tip touches Index tip, other fingers down
                # -----------------------------------------------
                elif thumb_index_dist < 0.05 and fingers == [0, 0, 0, 0]:
                    now = time.time()
                    click_times.append(now)
                    click_times = [t for t in click_times if now - t < 1.0]

                    if len(click_times) >= 2 and click_times[-1] - click_times[-2] < 0.4:
                        pyautogui.doubleClick()
                        current_gesture = 'Double Click'
                        cv2.putText(frame, "Double Click", (10, 70),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        click_times = []
                    else:
                        pyautogui.click()
                        current_gesture = 'Single Click'
                        cv2.putText(frame, "Single Click", (10, 70),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    time.sleep(0.3)

                # -----------------------------------------------
                # 4. RIGHT CLICK — Middle finger only up
                # -----------------------------------------------
                elif fingers == [0, 1, 0, 0]:
                    pyautogui.rightClick()
                    current_gesture = 'Right Click'
                    cv2.putText(frame, "Right Click", (10, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)
                    time.sleep(0.4)

                # -----------------------------------------------
                # 5. SCROLL UP / 6. SCROLL DOWN
                # Index + Middle up — detect actual movement direction
                # -----------------------------------------------
                elif fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0:
                    current_y = (index_tip.y + middle_tip.y) / 2
                    if prev_scroll_y is not None:
                        delta_y = current_y - prev_scroll_y
                        if delta_y < -scroll_move_threshold:
                            pyautogui.scroll(5)
                            current_gesture = 'Scroll Up'
                            cv2.putText(frame, "Scroll Up", (10, 130),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        elif delta_y > scroll_move_threshold:
                            pyautogui.scroll(-5)
                            current_gesture = 'Scroll Down'
                            cv2.putText(frame, "Scroll Down", (10, 130),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 100, 255), 2)
                    prev_scroll_y = current_y

                # -----------------------------------------------
                # 7. ZOOM IN  — Middle + Ring up, hand NEAR camera (hand looks big)
                # 8. ZOOM OUT — Middle + Ring up, hand FAR from camera (hand looks small)
                # Uses hand_size as depth proxy: big hand_size = near, small = far
                # -----------------------------------------------
                elif fingers == [0, 1, 1, 0]:
                    if hand_size > 0.22:           # hand near camera = zoom in
                        pyautogui.hotkey('ctrl', '+')
                        current_gesture = 'Zoom In'
                        cv2.putText(frame, f"Zoom In (near)", (10, 160),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 200), 2)
                    elif hand_size < 0.14:         # hand far from camera = zoom out
                        pyautogui.hotkey('ctrl', '-')
                        current_gesture = 'Zoom Out'
                        cv2.putText(frame, f"Zoom Out (far)", (10, 160),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 255), 2)
                    time.sleep(0.25)

                # -----------------------------------------------
                # 9. VOLUME UP   — Index + Pinky up, hand NEAR camera (big)
                # 10. VOLUME DOWN — Index + Pinky up, hand FAR from camera (small)
                # hand_size scales with camera distance: near=large, far=small
                # Map hand_size range [0.10 .. 0.30] → volume range
                # -----------------------------------------------
                elif fingers == [1, 0, 0, 1] and audio_available:
                    # Clamp hand_size to [0.10, 0.30] and map to volume
                    depth = max(0.10, min(hand_size, 0.30))
                    vol = min_vol + ((depth - 0.10) / 0.20) * (max_vol - min_vol)
                    vol = max(min_vol, min(vol, max_vol))
                    volume.SetMasterVolumeLevel(vol, None)
                    if hand_size > 0.20:
                        current_gesture = 'Volume Up'
                        cv2.putText(frame, f"Volume Up (near)", (10, 190),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 200), 2)
                    else:
                        current_gesture = 'Volume Down'
                        cv2.putText(frame, f"Volume Down (far)", (10, 190),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 0), 2)

                # -----------------------------------------------
                # 11. BRIGHTNESS UP   — Pinky only up, hand NEAR camera (big hand_size)
                # 12. BRIGHTNESS DOWN — Pinky only up, hand FAR from camera (small hand_size)
                # Only pinky finger raised — no thumb distance used
                # -----------------------------------------------
                elif fingers == [0, 0, 0, 1]:
                    now = time.time()
                    if now - last_brightness_time > brightness_cooldown:
                        if hand_size > 0.22:       # hand near camera → brightness up
                            sbc.set_brightness(min(100, sbc.get_brightness(display=0)[0] + 10))
                            current_gesture = 'Brightness Up'
                            cv2.putText(frame, "Brightness Up (near)", (10, 220),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 200), 2)
                            last_brightness_time = now
                        elif hand_size < 0.14:     # hand far from camera → brightness down
                            sbc.set_brightness(max(10, sbc.get_brightness(display=0)[0] - 10))
                            current_gesture = 'Brightness Down'
                            cv2.putText(frame, "Brightness Down (far)", (10, 220),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 255), 2)
                            last_brightness_time = now

                # -----------------------------------------------
                # 13. SCREENSHOT — All 4 fingers open
                # -----------------------------------------------
                elif fingers == [1, 1, 1, 1]:
                    now = time.time()
                    if now - last_screenshot_time > screenshot_cooldown:
                        pyautogui.screenshot(f"screenshot_{int(now)}.png")
                        current_gesture = 'Screenshot'
                        cv2.putText(frame, "Screenshot Taken", (10, 250),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        last_screenshot_time = now

                # -----------------------------------------------
                # 14. LOCK SYSTEM — Closed fist, hold 2 seconds
                # -----------------------------------------------
                elif fingers == [0, 0, 0, 0]:
                    if lock_hold_start is None:
                        lock_hold_start = time.time()
                    hold_time = time.time() - lock_hold_start
                    remaining = max(0.0, 2.0 - hold_time)
                    cv2.putText(frame, f"Hold to Lock: {remaining:.1f}s", (10, 280),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    if hold_time > 2.0:
                        current_gesture = 'System Locked'
                        os.system("rundll32.exe user32.dll,LockWorkStation")
                        time.sleep(2)
                        lock_hold_start = None

                else:
                    # Reset stateful trackers when no matching gesture
                    prev_scroll_y = None
                    lock_hold_start = None

        else:
            # No hand in frame — reset all stateful tracking
            prev_scroll_y = None
            lock_hold_start = None

        # Emit gesture to website only when it changes
        if current_gesture and current_gesture != last_emitted_gesture:
            socketio.emit('gesture_event', {'gesture': current_gesture})
            last_emitted_gesture = current_gesture
        elif not current_gesture:
            last_emitted_gesture = None

        cv2.imshow("GestureOS — Hand Gesture Control", frame)
        if cv2.waitKey(1) == ord('q'):
            break

    _cap.release()
    cv2.destroyAllWindows()
    socketio.emit('engine_status', {'camera': False, 'mediapipe': False, 'engine': False})