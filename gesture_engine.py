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

# ─────────────────────────────────────────────
# STRICT finger detection using 3 landmarks:
#   tip (lm[n]), pip (lm[n-1]), mcp (lm[n-2])
# A finger is UP only when:
#   tip is clearly above pip AND pip is above mcp
# This prevents pinky from being misread as index
# ─────────────────────────────────────────────
def is_finger_up(lm, tip_id):
    tip = lm[tip_id]
    pip = lm[tip_id - 1]
    mcp = lm[tip_id - 2]
    return tip.y < pip.y and pip.y < mcp.y  # strict: all joints in upward chain

def is_finger_down(lm, tip_id):
    tip = lm[tip_id]
    pip = lm[tip_id - 1]
    mcp = lm[tip_id - 2]
    # Finger is DOWN when tip is below or same as pip
    return tip.y >= pip.y - 0.01

def get_fingers(lm):
    # Returns [index, middle, ring, pinky] using strict 3-point check
    return [
        1 if is_finger_up(lm, 8)  else 0,   # index
        1 if is_finger_up(lm, 12) else 0,   # middle
        1 if is_finger_up(lm, 16) else 0,   # ring
        1 if is_finger_up(lm, 20) else 0,   # pinky
    ]

def run(socketio, is_running_fn):
    global _stop_flag, _cap
    _stop_flag = False

    _cap = cv2.VideoCapture(0)
    if not _cap.isOpened():
        socketio.emit('gesture_event', {'gesture': 'ERROR', 'message': 'Camera not found'})
        return

    screen_w, screen_h = pyautogui.size()

    # ── Audio setup ──────────────────────────
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

    # ── State variables ──────────────────────
    click_times          = []
    last_screenshot_time = 0
    screenshot_cooldown  = 2
    lock_hold_start      = None
    last_emitted_gesture = None
    last_brightness_time = 0
    brightness_cooldown  = 0.6
    last_zoom_time       = 0
    zoom_cooldown        = 0.25

    # ── Depth thresholds (hand_size = wrist→middle_mcp distance) ──
    # hand_size > NEAR  → hand is close to camera
    # hand_size < FAR   → hand is far from camera
    # Gap between NEAR and FAR avoids accidental triggers
    NEAR = 0.25    # hand clearly close
    FAR  = 0.13    # hand clearly far  (raised from 0.11 → easier to reach)

    socketio.emit('engine_status', {'camera': True, 'mediapipe': True, 'engine': True})

    while is_running_fn() and not _stop_flag:
        ret, frame = _cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        hands_model = mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.75,   # slightly higher = less noise
            min_tracking_confidence=0.6
        )
        result = hands_model.process(rgb)
        hands_model.close()

        hands_detected = len(result.multi_hand_landmarks) if result.multi_hand_landmarks else 0
        socketio.emit('hands_count', {'count': hands_detected})

        current_gesture = None

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                lm = hand_landmarks.landmark

                # ── Key tip landmarks ────────────────────
                thumb_tip  = lm[4]
                index_tip  = lm[8]
                middle_tip = lm[12]
                ring_tip   = lm[16]
                pinky_tip  = lm[20]

                # ── Strict finger states ─────────────────
                fingers = get_fingers(lm)
                # fingers[0]=index, [1]=middle, [2]=ring, [3]=pinky

                # ── Distances ────────────────────────────
                thumb_index_dist = math.hypot(
                    thumb_tip.x - index_tip.x,
                    thumb_tip.y - index_tip.y
                )

                # ── Hand size = wrist → middle MCP ───────
                # Larger = closer to camera (near)
                # Smaller = farther from camera (far)
                wrist      = lm[0]
                middle_mcp = lm[9]
                hand_size  = math.hypot(
                    wrist.x - middle_mcp.x,
                    wrist.y - middle_mcp.y
                )

                # ── Display hand_size for calibration ────
                cv2.putText(frame, f"hand_size: {hand_size:.3f}", (10, frame.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)
                cv2.putText(frame, f"fingers: {fingers}", (10, frame.shape[0] - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

                now = time.time()

                # ═══════════════════════════════════════════
                # 1. CURSOR MOVEMENT — Index ONLY up
                #    Strict: index up + middle/ring/pinky all down
                # ═══════════════════════════════════════════
                if (fingers[0] == 1 and
                    fingers[1] == 0 and
                    fingers[2] == 0 and
                    fingers[3] == 0 and
                    thumb_index_dist > 0.06):   # thumb NOT touching index
                    screen_x = int(index_tip.x * screen_w)
                    screen_y = int(index_tip.y * screen_h)
                    pyautogui.moveTo(screen_x, screen_y, duration=0.05)
                    current_gesture = 'Cursor Move'
                    cv2.putText(frame, "Cursor Move", (10, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 0), 2)

                # ═══════════════════════════════════════════
                # 2 & 3. SINGLE / DOUBLE CLICK
                #    Thumb touches index, all fingers down
                # ═══════════════════════════════════════════
                elif (thumb_index_dist < 0.05 and
                      fingers[0] == 0 and
                      fingers[1] == 0 and
                      fingers[2] == 0 and
                      fingers[3] == 0):
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

                # ═══════════════════════════════════════════
                # 4. RIGHT CLICK — Middle ONLY up
                #    Strict: middle up + index/ring/pinky all down
                # ═══════════════════════════════════════════
                elif (fingers[0] == 0 and
                      fingers[1] == 1 and
                      fingers[2] == 0 and
                      fingers[3] == 0):
                    pyautogui.rightClick()
                    current_gesture = 'Right Click'
                    cv2.putText(frame, "Right Click", (10, 100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)
                    time.sleep(0.4)

                # ═══════════════════════════════════════════
                # 5 & 6. SCROLL UP / DOWN
                #    Index + Middle up, ring + pinky down
                #    Near camera = scroll up, Far = scroll down
                # ═══════════════════════════════════════════
                elif (fingers[0] == 1 and
                      fingers[1] == 1 and
                      fingers[2] == 0 and
                      fingers[3] == 0):
                    if hand_size > NEAR:
                        pyautogui.scroll(40)
                        current_gesture = 'Scroll Up'
                        cv2.putText(frame, "Scroll Up", (10, 130),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    elif hand_size < FAR:
                        pyautogui.scroll(-40)
                        current_gesture = 'Scroll Down'
                        cv2.putText(frame, "Scroll Down", (10, 130),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 100, 255), 2)

                # ═══════════════════════════════════════════
                # 7 & 8. ZOOM IN / OUT
                #    Middle + Ring up, index + pinky down
                #    Near = zoom in, Far = zoom out
                # ═══════════════════════════════════════════
                elif (fingers[0] == 0 and
                      fingers[1] == 1 and
                      fingers[2] == 1 and
                      fingers[3] == 0):
                    if now - last_zoom_time > zoom_cooldown:
                        if hand_size > NEAR:
                            pyautogui.hotkey('ctrl', '+')
                            current_gesture = 'Zoom In'
                            cv2.putText(frame, "Zoom In", (10, 160),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 200), 2)
                            last_zoom_time = now
                        elif hand_size < FAR:
                            pyautogui.hotkey('ctrl', '-')
                            current_gesture = 'Zoom Out'
                            cv2.putText(frame, "Zoom Out", (10, 160),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 255), 2)
                            last_zoom_time = now

                # ═══════════════════════════════════════════
                # 9 & 10. VOLUME UP / DOWN
                #    Index + Pinky up, middle + ring down
                #    Near = volume up, Far = volume down
                # ═══════════════════════════════════════════
                elif (fingers[0] == 1 and
                      fingers[1] == 0 and
                      fingers[2] == 0 and
                      fingers[3] == 1 and
                      audio_available):
                    depth = max(FAR, min(hand_size, NEAR))
                    vol   = min_vol + ((depth - FAR) / (NEAR - FAR)) * (max_vol - min_vol)
                    vol   = max(min_vol, min(vol, max_vol))
                    volume.SetMasterVolumeLevel(vol, None)
                    if hand_size > NEAR:
                        current_gesture = 'Volume Up'
                        cv2.putText(frame, "Volume Up", (10, 190),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 200), 2)
                    elif hand_size < FAR:
                        current_gesture = 'Volume Down'
                        cv2.putText(frame, "Volume Down", (10, 190),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 0), 2)
                    else:
                        current_gesture = 'Volume Adjust'
                        cv2.putText(frame, "Volume Adjust", (10, 190),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 0), 2)

                # ═══════════════════════════════════════════
                # 11 & 12. BRIGHTNESS UP / DOWN
                #    Pinky ONLY up — index/middle/ring all down
                #    Strict 3-point check prevents confusion with cursor
                #    Near = brightness up, Far = brightness down
                # ═══════════════════════════════════════════
                elif (fingers[0] == 0 and
                      fingers[1] == 0 and
                      fingers[2] == 0 and
                      fingers[3] == 1 and
                      is_finger_down(lm, 8)  and   # extra: index tip confirmed down
                      is_finger_down(lm, 12) and   # extra: middle tip confirmed down
                      is_finger_down(lm, 16)):      # extra: ring tip confirmed down
                    if now - last_brightness_time > brightness_cooldown:
                        if hand_size > NEAR:
                            sbc.set_brightness(
                                min(100, sbc.get_brightness(display=0)[0] + 10)
                            )
                            current_gesture = 'Brightness Up'
                            cv2.putText(frame, "Brightness Up", (10, 220),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 200), 2)
                            last_brightness_time = now
                        elif hand_size < FAR:
                            sbc.set_brightness(
                                max(10, sbc.get_brightness(display=0)[0] - 10)
                            )
                            current_gesture = 'Brightness Down'
                            cv2.putText(frame, "Brightness Down", (10, 220),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 255), 2)
                            last_brightness_time = now

                # ═══════════════════════════════════════════
                # 13. SCREENSHOT — All 4 fingers open
                # ═══════════════════════════════════════════
                elif fingers == [1, 1, 1, 1]:
                    if now - last_screenshot_time > screenshot_cooldown:
                        pyautogui.screenshot(f"screenshot_{int(now)}.png")
                        current_gesture = 'Screenshot'
                        cv2.putText(frame, "Screenshot Taken", (10, 250),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        last_screenshot_time = now

                # ═══════════════════════════════════════════
                # 14. LOCK SYSTEM — Closed fist, hold 2s
                # ═══════════════════════════════════════════
                elif (fingers == [0, 0, 0, 0] and
                      thumb_index_dist > 0.06):   # not a click pose
                    if lock_hold_start is None:
                        lock_hold_start = now
                    hold_time = now - lock_hold_start
                    remaining = max(0.0, 2.0 - hold_time)
                    cv2.putText(frame, f"Hold to Lock: {remaining:.1f}s", (10, 280),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    if hold_time > 2.0:
                        current_gesture = 'System Locked'
                        os.system("rundll32.exe user32.dll,LockWorkStation")
                        time.sleep(2)
                        lock_hold_start = None

                else:
                    lock_hold_start = None

        else:
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