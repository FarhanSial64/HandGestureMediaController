import cv2
import mediapipe as mp
import pyautogui
import time
import math

# Mediapipe setup
mp_hands = mp.solutions.hands
# Increased min_detection_confidence slightly for more stable detections, can be adjusted
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75) 
mp_draw = mp.solutions.drawing_utils

# Constants
# Finger tip landmarks: Index, Middle, Ring, Pinky
finger_tips = [8, 12, 16, 20]
# Thumb tip landmark
thumb_tip = 4
# Stores the last detected gesture to prevent rapid re-triggering
gesture_last = ""
# Timestamp of the last gesture action to control rate
gesture_time = time.time()
# For FPS calculation
p_time = 0

cap = cv2.VideoCapture(0)

# Utility: distance between two points (using landmark objects directly)
def distance(point1, point2):
    return math.sqrt((point1.x - point2.x)**2 + (point1.y - point2.y)**2)

# Determine if thumb is extended (straightened out from the palm)
def is_thumb_extended_new(hand_landmarks):
    return distance(hand_landmarks.landmark[thumb_tip], hand_landmarks.landmark[5]) > 0.09 


# Thumb up or down based on its vertical position relative to the wrist
def is_thumb_up_down_new(hand_landmarks):
    thumb_tip_point = hand_landmarks.landmark[thumb_tip]
    wrist_point = hand_landmarks.landmark[0]

    # Check if the thumb is broadly "extended" (splayed out) before determining up/down.
    if not is_thumb_extended_new(hand_landmarks):
        return None

    # Determine vertical direction relative to wrist (Y-axis in image)
    # Remember: smaller Y means higher on the screen.
    
    # If thumb tip is significantly higher than wrist
    if thumb_tip_point.y < wrist_point.y - 0.1: # Tuned threshold, make it slightly more strict
        return "up"
    # If thumb tip is significantly lower than wrist
    elif thumb_tip_point.y > wrist_point.y + 0.1: # Tuned threshold, make it slightly more strict
        return "down"
    return None

# Check other fingers (Index, Middle, Ring, Pinky) are extended
def get_finger_status(hand_landmarks):
    status = []
    # Loop through the tip landmark of each finger (8, 12, 16, 20)
    for tip in finger_tips:
        # Check if the tip of the finger (e.g., landmark 8 for index finger) is higher (smaller Y-coordinate)
        # than its corresponding PIP joint (e.g., landmark 6 for index finger).
        # If tip.y < pip.y, the finger is extended.
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[tip - 2].y:
            status.append(1) # Extended
        else:
            status.append(0) # Curled
    return status

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera not found.")
        break

    frame = cv2.flip(frame, 1) # Flip horizontally for natural mirror view
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # Corrected: cv2.COLOR_BGR2RGB
    result = hands.process(rgb)

    gesture = ""
    action_text = ""

    if result.multi_hand_landmarks:
        for handLms in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)
            
            thumb_is_extended = is_thumb_extended_new(handLms)
            thumb_direction = is_thumb_up_down_new(handLms)
            other_fingers_status = get_finger_status(handLms)
            finger_count = sum(other_fingers_status) # Number of extended non-thumb fingers

            # --- Decision Logic (Order Matters!) ---
            # Prioritize distinct gestures like Thumb Up/Down if the thumb is key.
            # Then handle gestures based on finger counts.

            # 1. Thumb Up: Thumb extended UP, and ALL other fingers CURLED.
            if thumb_direction == "up" and finger_count == 0:
                gesture = "Thumb Up"
                action_text = "Volume Up"
                if gesture != gesture_last or time.time() - gesture_time > 1.0: # 1 second cooldown
                    pyautogui.press('volumeup')
                    gesture_time = time.time()

            # 2. Thumb Down: Thumb extended DOWN, and ALL other fingers CURLED.
            elif thumb_direction == "down" and finger_count == 0:
                gesture = "Thumb Down"
                action_text = "Volume Down"
                if gesture != gesture_last or time.time() - gesture_time > 1.0: # 1 second cooldown
                    pyautogui.press('volumedown')
                    gesture_time = time.time()
            
            # 3. All 5 fingers extended (Open Palm) - Previous Media
            elif finger_count == 4 and thumb_is_extended: # All 4 non-thumb fingers + thumb extended
                gesture = "5 Fingers (Open Palm)"
                action_text = "Previous Media"
                if gesture != gesture_last or time.time() - gesture_time > 2.0: # Cooldown
                    # This might require a combination of keys, e.g., Alt+Left or Ctrl+Left
                    # For general media players, 'prevtrack' is often supported.
                    # Or 'left' if it's a browser video player that responds to arrow keys.
                    pyautogui.press('prevtrack') 
                    # If 'prevtrack' doesn't work, consider: pyautogui.hotkey('alt', 'left') or similar
                    gesture_time = time.time()

            # 4. Four Fingers extended - Next Media
            # This covers cases where thumb is curled, or where the "open palm" is not perfectly aligned for 5 fingers.
            # Best to make this distinct, so let's say 4 fingers (index, middle, ring, pinky) extended and thumb NOT up/down.
            elif finger_count == 4 and thumb_direction is None: # Only 4 non-thumb fingers extended, thumb not dictating up/down
                gesture = "4 Fingers"
                action_text = "Next Media"
                if gesture != gesture_last or time.time() - gesture_time > 2.0: # Cooldown
                    pyautogui.press('nexttrack')
                    # If 'nexttrack' doesn't work, consider: pyautogui.hotkey('alt', 'right') or similar
                    gesture_time = time.time()

            # 5. Two Fingers: Only Index and Middle extended for 5 seconds forward
            # We assume finger_count == 2 means index and middle are extended.
            # This should be checked after thumb gestures and 4/5 finger gestures.
            elif finger_count == 2 and thumb_direction is None: # And thumb is not in a specific up/down state
                gesture = "2 Fingers"
                action_text = "5 Seconds Forward"
                if gesture != gesture_last or time.time() - gesture_time > 0.5: # Shorter cooldown for quick skips
                    pyautogui.press('right') # Often used for forward in media players
                    gesture_time = time.time()

            # 6. Three Fingers: Only Index, Middle, Ring extended for 5 seconds backward
            elif finger_count == 3 and thumb_direction is None: # And thumb is not in a specific up/down state
                gesture = "3 Fingers"
                action_text = "5 Seconds Backward"
                if gesture != gesture_last or time.time() - gesture_time > 0.5: # Shorter cooldown for quick skips
                    pyautogui.press('left') # Often used for backward in media players
                    gesture_time = time.time()
            
            # 7. Fist: ALL fingers (including thumb implicitly) are curled.
            # This should be the last check to avoid conflicts.
            elif not thumb_is_extended and finger_count == 0:
                gesture = "Fist"
                action_text = "Play/Pause"
                if gesture != gesture_last or time.time() - gesture_time > 2.0: # 2 second cooldown
                    pyautogui.press('space')
                    gesture_time = time.time()
            
            # If no specific gesture is detected, reset gesture_last so new gestures can be detected faster
            # This is implicitly handled by `gesture = ""` at the start of the loop
            # if gesture is not set, `gesture_last` will effectively be empty until a new gesture occurs.
            
            # Update the last detected gesture
            # It's better to update gesture_last *only* if a specific gesture was recognized,
            # otherwise, it keeps triggering the previous gesture's cooldown, preventing new ones.
            # Let's adjust this: if no gesture is matched, reset `gesture_last` to allow immediate detection.
            if gesture != "": # Only update if a gesture was actually found in this frame
                gesture_last = gesture
            else:
                gesture_last = "" # Reset if no valid gesture detected, to enable new detections
                
    # Overlay UI
    cv2.rectangle(frame, (0, 0), (640, 40), (50, 50, 50), -1)
    cv2.putText(frame, f"Gesture: {gesture} | Action: {action_text}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

    # FPS counter
    c_time = time.time()
    fps = 1 / (c_time - p_time) if (c_time - p_time) > 0 else 0
    p_time = c_time
    cv2.putText(frame, f"FPS: {int(fps)}", (500, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100,255,100), 2)

    cv2.imshow("Gesture Media Controller", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()