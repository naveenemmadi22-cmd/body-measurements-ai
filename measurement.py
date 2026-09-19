import cv2
import mediapipe as mp
import math
import os


# =========================================================
# HELPER
# =========================================================

def distance(p1, p2):
    return math.sqrt(
        (p1[0] - p2[0]) ** 2 +
        (p1[1] - p2[1]) ** 2
    )


# =========================================================
# MEDIAPIPE
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


landmarker = PoseLandmarker.create_from_options(
    options
)


# =========================================================
# CALIBRATION
# =========================================================

CALIBRATION_LENGTH_CM = 25.0


def calculate_calibration(point1, point2):

    pixel_length = distance(
        point1,
        point2
    )

    if pixel_length <= 0:
        return None

    cm_per_pixel = (
        CALIBRATION_LENGTH_CM /
        pixel_length
    )

    return {

        "pixel_length":
            round(pixel_length, 2),

        "real_length_cm":
            CALIBRATION_LENGTH_CM,

        "cm_per_pixel":
            cm_per_pixel
    }


# =========================================================
# LANDMARK → IMAGE PIXEL
# =========================================================

def landmark_to_pixel(
    landmark,
    width,
    height
):

    return (
        int(landmark.x * width),
        int(landmark.y * height)
    )


# =========================================================
# CHECK VISIBILITY
# =========================================================

def visible(landmark, threshold=0.60):

    return (
        landmark.visibility is not None
        and landmark.visibility >= threshold
    )


# =========================================================
# BODY MEASUREMENT
# =========================================================

def measure_body(
    frame,
    cm_per_pixel
):

    # -----------------------------------------------------
    # Calibration check
    # -----------------------------------------------------

    if (
        cm_per_pixel is None
        or cm_per_pixel <= 0
    ):

        return {

            "height_cm": None,
            "shoulder_cm": None,
            "hip_cm": None,

            "status":
                "Calibration required"
        }


    # -----------------------------------------------------
    # Image dimensions
    # -----------------------------------------------------

    height, width, _ = frame.shape


    # -----------------------------------------------------
    # BGR → RGB
    # -----------------------------------------------------

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # -----------------------------------------------------
    # MediaPipe image
    # -----------------------------------------------------

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )


    # -----------------------------------------------------
    # Pose detection
    # -----------------------------------------------------

    results = landmarker.detect(
        mp_image
    )


    if not results.pose_landmarks:

        return {

            "height_cm": None,
            "shoulder_cm": None,
            "hip_cm": None,

            "status":
                "No person detected"
        }


    landmarks = results.pose_landmarks[0]


    # =====================================================
    # LANDMARKS
    # =====================================================

    nose = landmarks[0]

    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]

    left_hip = landmarks[23]
    right_hip = landmarks[24]

    left_knee = landmarks[25]
    right_knee = landmarks[26]

    left_ankle = landmarks[27]
    right_ankle = landmarks[28]

    left_heel = landmarks[29]
    right_heel = landmarks[30]

    left_foot = landmarks[31]
    right_foot = landmarks[32]


    # =====================================================
    # SHOULDER WIDTH
    # =====================================================

    shoulder_cm = None

    if (
        visible(left_shoulder)
        and
        visible(right_shoulder)
    ):

        ls = landmark_to_pixel(
            left_shoulder,
            width,
            height
        )

        rs = landmark_to_pixel(
            right_shoulder,
            width,
            height
        )

        shoulder_pixels = distance(
            ls,
            rs
        )

        shoulder_cm = (
            shoulder_pixels *
            cm_per_pixel
        )


    # =====================================================
    # HIP WIDTH
    # =====================================================

    hip_cm = None

    if (
        visible(left_hip)
        and
        visible(right_hip)
    ):

        lh = landmark_to_pixel(
            left_hip,
            width,
            height
        )

        rh = landmark_to_pixel(
            right_hip,
            width,
            height
        )

        hip_pixels = distance(
            lh,
            rh
        )

        hip_cm = (
            hip_pixels *
            cm_per_pixel
        )


    # =====================================================
    # HEIGHT
    # =====================================================
    #
    # IMPORTANT:
    #
    # MediaPipe has no actual "top of head"
    # landmark.
    #
    # We therefore estimate the top using
    # visible facial landmarks.
    #
    # The bottom uses the lowest reliable
    # foot/heel landmark.
    # =====================================================


    # -----------------------------------------------------
    # Find visible upper-body landmarks
    # -----------------------------------------------------

    upper_points = []


    # Nose
    if visible(nose):

        upper_points.append(
            landmark_to_pixel(
                nose,
                width,
                height
            )
        )


    # Ears
    left_ear = landmarks[7]
    right_ear = landmarks[8]


    if visible(left_ear):

        upper_points.append(
            landmark_to_pixel(
                left_ear,
                width,
                height
            )
        )


    if visible(right_ear):

        upper_points.append(
            landmark_to_pixel(
                right_ear,
                width,
                height
            )
        )


    # -----------------------------------------------------
    # Estimate top of head
    # -----------------------------------------------------

    top_of_head = None


    if len(upper_points) >= 2:

        # Use the highest facial landmark
        # as the reference point.

        highest_y = min(
            point[1]
            for point in upper_points
        )


        # Estimate head crown above
        # the highest facial landmark.

        face_width = None


        if (
            visible(left_ear)
            and
            visible(right_ear)
        ):

            le = landmark_to_pixel(
                left_ear,
                width,
                height
            )

            re = landmark_to_pixel(
                right_ear,
                width,
                height
            )

            face_width = distance(
                le,
                re
            )


        if face_width is not None:

            # Approximate crown offset.
            #
            # This is still an estimate because
            # MediaPipe Pose does not provide a
            # crown landmark.

            crown_offset = (
                face_width * 0.65
            )

            top_of_head = (
                int(
                    (
                        upper_points[0][0]
                        +
                        upper_points[-1][0]
                    ) / 2
                ),
                int(
                    highest_y -
                    crown_offset
                )
            )

        else:

            top_of_head = min(
                upper_points,
                key=lambda p: p[1]
            )


    # =====================================================
    # FIND BOTTOM OF BODY
    # =====================================================

    bottom_points = []


    # Ankles

    if visible(left_ankle):

        bottom_points.append(
            landmark_to_pixel(
                left_ankle,
                width,
                height
            )
        )


    if visible(right_ankle):

        bottom_points.append(
            landmark_to_pixel(
                right_ankle,
                width,
                height
            )
        )


    # Heels

    if visible(left_heel):

        bottom_points.append(
            landmark_to_pixel(
                left_heel,
                width,
                height
            )
        )


    if visible(right_heel):

        bottom_points.append(
            landmark_to_pixel(
                right_heel,
                width,
                height
            )
        )


    # Foot tips

    if visible(left_foot):

        bottom_points.append(
            landmark_to_pixel(
                left_foot,
                width,
                height
            )
        )


    if visible(right_foot):

        bottom_points.append(
            landmark_to_pixel(
                right_foot,
                width,
                height
            )
        )


    # -----------------------------------------------------
    # Calculate height
    # -----------------------------------------------------

    height_cm = None


    if (
        top_of_head is not None
        and
        len(bottom_points) > 0
    ):

        bottom_of_body = max(
            bottom_points,
            key=lambda p: p[1]
        )


        height_pixels = distance(
            top_of_head,
            bottom_of_body
        )


        height_cm = (
            height_pixels *
            cm_per_pixel
        )


    # =====================================================
    # RETURN RESULTS
    # =====================================================

    return {

        "height_cm":
            round(height_cm, 2)
            if height_cm is not None
            else None,

        "shoulder_cm":
            round(shoulder_cm, 2)
            if shoulder_cm is not None
            else None,

        "hip_cm":
            round(hip_cm, 2)
            if hip_cm is not None
            else None,

        "status":
            "Person detected"
    }