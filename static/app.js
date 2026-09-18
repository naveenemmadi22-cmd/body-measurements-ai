const video = document.getElementById("camera");
const results = document.getElementById("results");

let socket;
let frameTimer;


// =========================================
// OPEN PHONE CAMERA
// =========================================

async function startCamera() {

    try {

        const stream = await navigator.mediaDevices.getUserMedia({

            video: {
                facingMode: "environment",
                width: {
                    ideal: 1280
                },
                height: {
                    ideal: 720
                }
            },

            audio: false
        });

        video.srcObject = stream;

        console.log("Camera started");

        results.innerText = "Camera started. Connecting to server...";

        connectWebSocket();

    } catch (error) {

        console.error("Camera error:", error);

        results.innerText =
            "Camera permission denied or unavailable.";

    }
}


// =========================================
// CONNECT TO PYTHON SERVER
// =========================================

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

    console.log("WebSocket URL:", wsUrl);

    socket = new WebSocket(wsUrl);


    // -----------------------------------------
    // CONNECTION SUCCESS
    // -----------------------------------------

    socket.onopen = () => {

        console.log("WebSocket CONNECTED");

        results.innerText =
            "Connected to server. Sending camera frames...";

        startSendingFrames();
    };


    // -----------------------------------------
    // RECEIVE MEASUREMENTS
    // -----------------------------------------

    socket.onmessage = (event) => {

        try {

            const data = JSON.parse(event.data);

            console.log("Server result:", data);


            // No person detected

            if (
                data.status === "No person detected" ||
                data.height === null
            ) {

                results.innerText =
                    "Person not detected";

                return;
            }


            // Person detected

            results.innerHTML =
                "Height: " +
                data.height +
                " pixels<br>" +

                "Shoulder: " +
                data.shoulder +
                " pixels<br>" +

                "Waist: " +
                data.waist +
                " pixels";

        } catch (error) {

            console.error(
                "Error reading server response:",
                error
            );

        }
    };


    // -----------------------------------------
    // WEBSOCKET ERROR
    // -----------------------------------------

    socket.onerror = (error) => {

        console.error(
            "WebSocket ERROR:",
            error
        );

        results.innerText =
            "WebSocket connection failed.";

    };


    // -----------------------------------------
    // WEBSOCKET CLOSED
    // -----------------------------------------

    socket.onclose = (event) => {

        console.log(
            "WebSocket CLOSED:",
            event.code,
            event.reason
        );

        if (frameTimer) {

            clearInterval(frameTimer);

            frameTimer = null;
        }

        results.innerText =
            "Server connection closed.";

    };
}


// =========================================
// SEND CAMERA FRAMES
// =========================================

function startSendingFrames() {

    const canvas =
        document.createElement("canvas");

    const context =
        canvas.getContext("2d");


    // Send approximately 5 frames per second

    frameTimer = setInterval(() => {

        // Check WebSocket

        if (
            !socket ||
            socket.readyState !== WebSocket.OPEN
        ) {

            return;
        }


        // Check video

        if (
            video.readyState < 2 ||
            !video.videoWidth ||
            !video.videoHeight
        ) {

            return;
        }


        // -----------------------------------------
        // SET CANVAS SIZE
        // -----------------------------------------

        canvas.width = 640;

        canvas.height =
            Math.round(
                video.videoHeight /
                video.videoWidth *
                640
            );


        // -----------------------------------------
        // COPY VIDEO FRAME TO CANVAS
        // -----------------------------------------

        context.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height
        );


        // -----------------------------------------
        // CONVERT FRAME TO JPEG
        // -----------------------------------------

        canvas.toBlob(
            (blob) => {

                if (
                    blob &&
                    socket &&
                    socket.readyState === WebSocket.OPEN
                ) {

                    socket.send(blob);

                }

            },
            "image/jpeg",
            0.7
        );

    }, 200);
}


// =========================================
// START APPLICATION
// =========================================

startCamera();