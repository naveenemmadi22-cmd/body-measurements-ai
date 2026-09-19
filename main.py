from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import cv2
import numpy as np
import json
import base64

from measurement import (
    calculate_calibration,
    measure_body
)


app = FastAPI()


# =========================================================
# STATIC FILES
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
async def home():
    return FileResponse("static/index.html")


# =========================================================
# WEBSOCKET
# =========================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    print("WebSocket client connected")

    cm_per_pixel = None

    try:

        while True:

            raw_message = await websocket.receive()

            message_type = raw_message.get("type")


            # -------------------------------------------------
            # DISCONNECT
            # -------------------------------------------------

            if message_type == "websocket.disconnect":

                print("Client disconnected")

                break


            # -------------------------------------------------
            # GET MESSAGE DATA
            # -------------------------------------------------

            text_data = raw_message.get("text")
            bytes_data = raw_message.get("bytes")


            if text_data is not None:

                json_data = text_data

            elif bytes_data is not None:

                try:

                    json_data = bytes_data.decode(
                        "utf-8"
                    )

                except UnicodeDecodeError:

                    print(
                        "Received invalid binary data"
                    )

                    continue

            else:

                continue


            # -------------------------------------------------
            # JSON
            # -------------------------------------------------

            try:

                message = json.loads(
                    json_data
                )

            except json.JSONDecodeError:

                print(
                    "Invalid JSON received"
                )

                continue


            message_type = message.get(
                "type"
            )


            # =================================================
            # CALIBRATION
            # =================================================

            if message_type == "calibrate":

                try:

                    point1 = tuple(
                        message["point1"]
                    )

                    point2 = tuple(
                        message["point2"]
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError
                ):

                    await websocket.send_json({

                        "type":
                            "calibration_result",

                        "success":
                            False,

                        "status":
                            "Invalid calibration points"

                    })

                    continue


                calibration = calculate_calibration(
                    point1,
                    point2
                )


                if calibration is None:

                    await websocket.send_json({

                        "type":
                            "calibration_result",

                        "success":
                            False,

                        "status":
                            "Invalid calibration points"

                    })

                    continue


                cm_per_pixel = (
                    calibration["cm_per_pixel"]
                )


                print(
                    "Calibration successful:",
                    calibration
                )


                await websocket.send_json({

                    "type":
                        "calibration_result",

                    "success":
                        True,

                    "real_length_cm":
                        calibration[
                            "real_length_cm"
                        ],

                    "pixel_length":
                        calibration[
                            "pixel_length"
                        ],

                    "cm_per_pixel":
                        round(
                            cm_per_pixel,
                            6
                        ),

                    "status":
                        "Calibration successful"

                })


                continue


            # =================================================
            # FRAME
            # =================================================

            if message_type == "frame":

                if cm_per_pixel is None:

                    await websocket.send_json({

                        "type":
                            "measurement_result",

                        "height_cm":
                            None,

                        "shoulder_cm":
                            None,

                        "hip_cm":
                            None,

                        "status":
                            "Please calibrate first"

                    })

                    continue


                image_data = message.get(
                    "image"
                )


                if not image_data:

                    continue


                # Remove data URL prefix

                if "," in image_data:

                    image_data = image_data.split(
                        ",",
                        1
                    )[1]


                # Base64 → bytes

                try:

                    image_bytes = base64.b64decode(
                        image_data
                    )

                except Exception:

                    continue


                # Bytes → NumPy

                np_data = np.frombuffer(
                    image_bytes,
                    np.uint8
                )


                # NumPy → OpenCV

                frame = cv2.imdecode(
                    np_data,
                    cv2.IMREAD_COLOR
                )


                if frame is None:

                    continue


                # -------------------------------------------------
                # COMPUTER VISION
                # -------------------------------------------------

                result = measure_body(
                    frame,
                    cm_per_pixel
                )


                result["type"] = (
                    "measurement_result"
                )


                await websocket.send_json(
                    result
                )

                continue


            # =================================================
            # UNKNOWN MESSAGE
            # =================================================

            print(
                "Unknown message type:",
                message_type
            )


    except WebSocketDisconnect:

        print(
            "WebSocket disconnected"
        )


    except Exception as e:

        print(
            "WebSocket error:",
            repr(e)
        )