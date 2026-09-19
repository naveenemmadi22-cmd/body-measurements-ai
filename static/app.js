const video = document.getElementById("camera");
const results = document.getElementById("results");

let socket = null;
let frameTimer = null;

let calibrationPoints = [];
let calibrated = false;


// =========================================================
// CALIBRATION MESSAGE
// =========================================================

const calibrationMessage = document.createElement("div");

calibrationMessage.style.margin = "10px 0";
calibrationMessage.style.fontSize = "16px";
calibrationMessage.style.fontWeight = "bold";

calibrationMessage.innerText =
    "Starting camera...";

results.parentNode.insertBefore(
    calibrationMessage,
    results
);


// =========================================================
// CALIBRATION CANVAS
// =========================================================

const calibrationCanvas =
    document.createElement("canvas");

calibrationCanvas.style.position = "absolute";
calibrationCanvas.style.left = "0";
calibrationCanvas.style.top = "0";
calibrationCanvas.style.width = "100%";
calibrationCanvas.style.height = "100%";
calibrationCanvas.style.zIndex = "10";
calibrationCanvas.style.pointerEvents = "auto";


const videoContainer = video.parentElement;

if (videoContainer) {

    videoContainer.style.position = "relative";

    videoContainer.appendChild(
        calibrationCanvas
    );
}


// =========================================================
// RESIZE CALIBRATION CANVAS
// =========================================================

function resizeCalibrationCanvas() {

    if (!video.videoWidth || !video.videoHeight) {
        return;
    }

    calibrationCanvas.width =
        video.clientWidth;

    calibrationCanvas.height =
        video.clientHeight;

    drawCalibrationPoints();
}


// =========================================================
// DRAW CALIBRATION POINTS
// =========================================================

function drawCalibrationPoints() {

    const ctx =
        calibrationCanvas.getContext("2d");

    ctx.clearRect(
        0,
        0,
        calibrationCanvas.width,
        calibrationCanvas.height
    );


    calibrationPoints.forEach(
        (point, index) => {

            ctx.beginPath();

            ctx.arc(
                point.x,
                point.y,
                9,
                0,
                Math.PI * 2
            );

            ctx.fillStyle = "red";

            ctx.fill();

            ctx.font =
                "bold 18px Arial";

            ctx.fillStyle = "white";

            ctx.fillText(
                index === 0 ? "1" : "2",
                point.x + 12,
                point.y - 12
            );
        }
    );


    if (calibrationPoints.length === 2) {

        const p1 =
            calibrationPoints[0];

        const p2 =
            calibrationPoints[1];

        ctx.beginPath();

        ctx.moveTo(
            p1.x,
            p1.y
        );

        ctx.lineTo(
            p2.x,
            p2.y
        );

        ctx.lineWidth = 4;

        ctx.strokeStyle = "red";

        ctx.stroke();
    }
}


// =========================================================
// GET TAP COORDINATES
// =========================================================

function getVideoCoordinates(event) {

    const rect =
        calibrationCanvas.getBoundingClientRect();

    let clientX;
    let clientY;


    if (
        event.touches &&
        event.touches.length > 0
    ) {

        clientX =
            event.touches[0].clientX;

        clientY =
            event.touches[0].clientY;

    } else {

        clientX =
            event.clientX;

        clientY =
            event.clientY;
    }


    return {

        x:
            clientX - rect.left,

        y:
            clientY - rect.top

    };
}


// =========================================================
// CALIBRATION TAP
// =========================================================

function handleCalibrationTap(event) {

    event.preventDefault();

    if (calibrated) {
        return;
    }

    if (calibrationPoints.length >= 2) {
        return;
    }


    const point =
        getVideoCoordinates(event);


    calibrationPoints.push(point);

    drawCalibrationPoints();


    if (calibrationPoints.length === 1) {

        calibrationMessage.innerText =
            "Now tap the other end of the 25 cm object.";

        return;
    }


    if (calibrationPoints.length === 2) {

        calibrationMessage.innerText =
            "Calibrating...";

        sendCalibration();
    }
}


calibrationCanvas.addEventListener(
    "click",
    handleCalibrationTap
);


calibrationCanvas.addEventListener(
    "touchstart",
    handleCalibrationTap,
    {
        passive: false
    }
);


// =========================================================
// SEND CALIBRATION
// =========================================================

function sendCalibration() {

    if (
        !socket ||
        socket.readyState !== WebSocket.OPEN
    ) {

        calibrationMessage.innerText =
            "Server is not connected.";

        return;
    }


    const p1 =
        calibrationPoints[0];

    const p2 =
        calibrationPoints[1];


    const message = {

        type: "calibrate",

        point1: [
            p1.x,
            p1.y
        ],

        point2: [
            p2.x,
            p2.y
        ]

    };


    console.log(
        "SENDING CALIBRATION:",
        message
    );


    socket.send(
        JSON.stringify(message)
    );
}


// =========================================================
// START CAMERA
// =========================================================

async function startCamera() {

    try {

        const stream =
            await navigator.mediaDevices.getUserMedia({

                video: {

                    facingMode: {
                        ideal: "environment"
                    },

                    width: {
                        ideal: 1280
                    },

                    height: {
                        ideal: 720
                    }

                },

                audio: false
            });


        video.srcObject =
            stream;


        await video.play();


        console.log(
            "Camera started"
        );


        calibrationMessage.innerText =
            "Camera started. Connecting to server...";


        resizeCalibrationCanvas();


        connectWebSocket();


    } catch (error) {

        console.error(
            "Camera error:",
            error
        );


        results.innerText =
            "Camera permission denied or unavailable.";
    }
}


// =========================================================
// WEBSOCKET
// =========================================================

function connectWebSocket() {

    const protocol =
        window.location.protocol === "https:"
            ? "wss:"
            : "ws:";


    const wsUrl =
        protocol +
        "//" +
        window.location.host +
        "/ws";


    console.log(
        "WebSocket URL:",
        wsUrl
    );


    socket =
        new WebSocket(wsUrl);


    socket.onopen = () => {

        console.log(
            "WebSocket CONNECTED"
        );


        calibrationMessage.innerText =
            "Connected. Place the 25 cm calibration object in view.";


        results.innerText =
            "Tap the two ends of the 25 cm object.";
    };


    socket.onmessage = (event) => {

        try {

            const data =
                JSON.parse(event.data);


            console.log(
                "SERVER RESPONSE:",
                data
            );


            // =========================================
            // CALIBRATION RESULT
            // =========================================

            if (
                data.type ===
                "calibration_result"
            ) {

                if (!data.success) {

                    calibrationMessage.innerText =
                        "Calibration failed. Try again.";

                    calibrationPoints = [];

                    drawCalibrationPoints();

                    return;
                }


                calibrated = true;


                calibrationMessage.innerText =
                    "Calibration successful. Stand in front of the camera.";


                results.innerHTML =
                    "Calibration object: " +
                    data.real_length_cm +
                    " cm<br>" +

                    "Object pixels: " +
                    data.pixel_length +
                    "<br><br>" +

                    "Waiting for person...";


                calibrationCanvas.style.pointerEvents =
                    "none";


                startSendingFrames();

                return;
            }


            // =========================================
            // MEASUREMENT RESULT
            // =========================================

            if (
                data.type ===
                "measurement_result"
            ) {

                if (
                    data.status ===
                    "No person detected"
                ) {

                    results.innerText =
                        "Stand fully in view.";

                    return;
                }


                if (
                    data.height_cm === null
                ) {

                    results.innerText =
                        data.status;

                    return;
                }


                results.innerHTML =

                    "<strong>Body Measurements</strong><br><br>" +

                    "Height: " +
                    data.height_cm +
                    " cm<br>" +

                    "Shoulder: " +
                    data.shoulder_cm +
                    " cm<br>" +

                    "Hip: " +
                    data.hip_cm +
                    " cm";

                return;
            }


            // =========================================
            // ERROR
            // =========================================

            if (
                data.type === "error"
            ) {

                results.innerText =
                    data.status;
            }

        } catch (error) {

            console.error(
                "Response parsing error:",
                error
            );
        }
    };


    socket.onerror = (error) => {

        console.error(
            "WebSocket ERROR:",
            error
        );

        calibrationMessage.innerText =
            "WebSocket connection failed.";
    };


    socket.onclose = (event) => {

        console.log(
            "WebSocket CLOSED:",
            event.code,
            event.reason
        );


        stopSendingFrames();
    };
}


// =========================================================
// SEND CAMERA FRAMES
// =========================================================

function startSendingFrames() {

    if (frameTimer) {
        return;
    }


    const canvas =
        document.createElement("canvas");

    const context =
        canvas.getContext("2d");


    frameTimer =
        setInterval(
            () => {

                if (
                    !socket ||
                    socket.readyState !==
                        WebSocket.OPEN
                ) {

                    return;
                }


                if (
                    video.readyState < 2 ||
                    !video.videoWidth ||
                    !video.videoHeight
                ) {

                    return;
                }


                canvas.width = 640;

                canvas.height =
                    Math.round(
                        video.videoHeight /
                        video.videoWidth *
                        640
                    );


                context.drawImage(
                    video,
                    0,
                    0,
                    canvas.width,
                    canvas.height
                );


                // =====================================
                // IMPORTANT
                // =====================================

                const image =
                    canvas.toDataURL(
                        "image/jpeg",
                        0.7
                    );


                const message = {

                    type: "frame",

                    image: image

                };


                // SEND JSON STRING — NOT BLOB

                socket.send(
                    JSON.stringify(message)
                );


            },
            333
        );
}


// =========================================================
// STOP FRAME SENDING
// =========================================================

function stopSendingFrames() {

    if (frameTimer) {

        clearInterval(
            frameTimer
        );

        frameTimer = null;
    }
}


// =========================================================
// RESIZE
// =========================================================

window.addEventListener(
    "resize",
    () => {

        resizeCalibrationCanvas();

    }
);


// =========================================================
// START
// =========================================================

startCamera();