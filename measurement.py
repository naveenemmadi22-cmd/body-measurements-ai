import cv2
import mediapipe as mp
import math
import os


# =========================================================
# HELPER FUNCTION
# =========================================================

def distance(p1, p2):
    return math.sqrt(
        (p1[0] - p2[0]) ** 2 +
        (p1[1] - p2[1]) ** 2
    )


# =========================================================
# MEDIAPIPE POSE
# =========================================================

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode


MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "pose_landmarker_full.task"
)

options = PoseLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path=MODEL_PATH
    ),
    running_mode=VisionRunningMode.IMAGE,
    num_poses=1
)


landmarker = PoseLandmarker.create_from_options(options)


# =========================================================
# MAIN BODY MEASUREMENT FUNCTION
# =========================================================

def measure_body(frame):

    # -----------------------------------------------------
    # Frame dimensions
    # -----------------------------------------------------

    height, width, _ = frame.shape


    # -----------------------------------------------------
    # OpenCV BGR → RGB
    # -----------------------------------------------------

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # -----------------------------------------------------
    # Create MediaPipe image
    # -----------------------------------------------------

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )


    # -----------------------------------------------------
    # Detect pose
    # -----------------------------------------------------

    results = landmarker.detect(mp_image)


    # -----------------------------------------------------
    # No person detected
    # -----------------------------------------------------

    if not results.pose_landmarks:

        return {
            "height": None,
            "shoulder": None,
            "waist": None,
            "status": "No person detected"
        }


    # -----------------------------------------------------
    # Get first detected person
    # -----------------------------------------------------

    landmarks = results.pose_landmarks[0]


    # =====================================================
    # SHOULDERS
    # =====================================================

    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]

    ls = (
        int(left_shoulder.x * width),
        int(left_shoulder.y * height)
    )

    rs = (
        int(right_shoulder.x * width),
        int(right_shoulder.y * height)
    )

    shoulder_pixels = distance(
        ls,
        rs
    )


    # =====================================================
    # HIPS
    # =====================================================

    left_hip = landmarks[23]
    right_hip = landmarks[24]

    lh = (
        int(left_hip.x * width),
        int(left_hip.y * height)
    )

    rh = (
        int(right_hip.x * width),
        int(right_hip.y * height)
    )

    hip_pixels = distance(
        lh,
        rh
    )


    # =====================================================
    # ANKLES
    # =====================================================

    left_ankle = landmarks[27]
    right_ankle = landmarks[28]

    la = (
        int(left_ankle.x * width),
        int(left_ankle.y * height)
    )

    ra = (
        int(right_ankle.x * width),
        int(right_ankle.y * height)
    )


    # =====================================================
    # TOP OF HEAD
    # =====================================================

    # MediaPipe does not provide an actual crown landmark.
    # We estimate the top of the head using both ears.

    left_ear = landmarks[7]
    right_ear = landmarks[8]

    le = (
        int(left_ear.x * width),
        int(left_ear.y * height)
    )

    re = (
        int(right_ear.x * width),
        int(right_ear.y * height)
    )


    # Middle of ears

    head_center_x = int(
        (le[0] + re[0]) / 2
    )


    ear_y = int(
        (le[1] + re[1]) / 2
    )


    # Distance between ears

    ear_width = distance(
        le,
        re
    )


    # Estimate crown

    crown_y = int(
        ear_y - (ear_width * 0.75)
    )


    top_of_head = (
        head_center_x,
        crown_y
    )


    # =====================================================
    # BOTTOM OF BODY
    # =====================================================

    bottom_of_body = max(
        la,
        ra,
        key=lambda p: p[1]
    )


    # =====================================================
    # HEIGHT IN PIXELS
    # =====================================================

    height_pixels = distance(
        top_of_head,
        bottom_of_body
    )


    # =====================================================
    # WAIST ESTIMATION
    # =====================================================

    shoulder_y = (
        ls[1] + rs[1]
    ) / 2


    hip_y = (
        lh[1] + rh[1]
    ) / 2


    waist_y = int(
        shoulder_y * 0.45 +
        hip_y * 0.55
    )


    # Approximate waist width

    waist_pixels = (
        shoulder_pixels * 0.35 +
        hip_pixels * 0.65
    )


    # =====================================================
    # RETURN RESULTS
    # =====================================================

    return {
        "height": round(height_pixels, 2),
        "shoulder": round(shoulder_pixels, 2),
        "waist": round(waist_pixels, 2),
        "status": "Person detected"
    }