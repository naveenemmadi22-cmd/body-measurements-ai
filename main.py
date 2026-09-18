from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import cv2
import numpy as np

from measurement import measure_body

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_bytes()

            # JPEG bytes → NumPy array
            np_data = np.frombuffer(data, np.uint8)

            # NumPy array → OpenCV image
            frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

            if frame is None:
                continue

            # AI / Computer Vision processing
            result = measure_body(frame)

            # Send measurements back to browser
            await websocket.send_json(result)

    except WebSocketDisconnect:
        print("Client disconnected")

    except Exception as e:
        print("WebSocket error:", e)