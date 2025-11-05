# 依存関係: pip install flask
# Dependencies: pip install flask
import threading
import time

from flask import Flask, Response, abort, render_template_string, request

app = Flask(__name__)

# Share the latest frame and metadata (thread-safe)
latest = {
    'jpeg': None,  # Latest frame bytes (assumed JPEG)
    'ts': 0.0,  # Reception timestamp (epoch)
    'count': 0,  # Received frame counter
}
cond = threading.Condition()

# ---- Config values (adjust as needed) ----------------------------
BOUNDARY = b'frame'  # Boundary name for MJPEG multipart
ACCEPT_CONTENT_TYPES = {'image/jpeg', 'image/jpg'}  # Accepted MIME types
# ------------------------------------------------------------------


@app.post('/frame_receiver')
def receive_frame():
    """
    Endpoint for external sender to upload a single frame (mainly JPEG).
    Receive HTTP request and Update latest_frame
    """
    # Retreive files of HTTP request
    img_f = request.files.get('image')
    # meta_f = request.files.get("meta")

    # Operations on image
    if not img_f:
        abort(
            400,
            "Please provide image file in 'image' field of multipart/form-data.",
        )

    ## MIME check
    if img_f.mimetype and img_f.mimetype.lower() not in ACCEPT_CONTENT_TYPES:
        abort(415, f'Unsupported Content-Type: {img_f.mimetype}. JPEG recommended.')

    ## Read data of file
    data = img_f.read()
    if not data:
        abort(400, 'Empty files are not accepted.')

    # Operations on meta
    # if meta_f:
    #    try:
    #        raw = meta_f.read()
    #        if raw:
    #            meta = json.loads(raw.decode("utf-8"))
    #    except Exception as e:
    #        abort(400, f"Fail to analyze json of meta: {e}")

    # Overwrite the latest frame and notify waiting viewers
    with cond:
        latest['jpeg'] = data
        latest['ts'] = time.time()
        latest['count'] += 1
        cond.notify_all()

    return {'count': latest['count']}, 200


def mjpeg_generator():
    """
    Generator streaming JPEG via multipart/x-mixed-replace to viewers, using each received frame.
    “Latest overwrite & new-only delivery” prevents delay accumulation.
    """
    last_sent_ts = -1.0
    boundary = BOUNDARY

    while True:
        with cond:
            # Wait until new frame arrives (wake periodically for keep-alive)
            if (latest['jpeg'] is None) or (latest['ts'] <= last_sent_ts):
                cond.wait(timeout=1.0)

            # Take frame if new
            frame = latest['jpeg']
            ts = latest['ts']

        # If no new frame, short sleep to avoid busy loop
        if ts <= last_sent_ts:
            time.sleep(0.05)
            continue

        last_sent_ts = ts

        # Generate one multipart section (one frame)
        yield (
            b'--' + boundary + b'\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Cache-Control: no-cache, no-store, must-revalidate\r\n'
            b'Pragma: no-cache\r\n'
            b'Expires: 0\r\n\r\n' + frame + b'\r\n'
        )


@app.get('/video')
def video():
    """
    Returns MJPEG stream.
    Viewable directly from browser via <img src="/video">
    """
    return Response(
        mjpeg_generator(),
        mimetype=f'multipart/x-mixed-replace; boundary={BOUNDARY.decode()}',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
        },
    )


@app.get('/viewer')
def viewer():
    """
    Simple viewer (only <img>).
    Add CSS/JS here if you want to extend the UI.
    """
    return render_template_string(
        """<!doctype html>
            <html>
            <head>
            <meta charset="utf-8">
            <title>MJPEG Viewer</title>
            <style>
                body {
                    margin: 0;                  /* remove default margin */
                    background: #111;           /* dark background */
                    display: grid;              /* center align */
                    place-items: center;
                    height: 100vh;              /* full viewport height */
                }
                img {
                    max-width: 100vw;           /* fit horizontally */
                    max-height: 100vh;          /* fit vertically */
                }
            </style>
            </head>
            <body>
                <img src="/video" alt="stream">
            </body>
            </html>"""
    )


@app.get('/health')
def health():
    """
    Health check for monitoring.
    - last_ts: last received timestamp
    - count:   total received frames
    """
    return {
        'ok': True,
        'last_ts': latest['ts'],
        'count': latest['count'],
        'has_frame': latest['jpeg'] is not None,
    }


if __name__ == '__main__':
    # Listen on 0.0.0.0 for external access; use 127.0.0.1 if local only.
    app.run(host='0.0.0.0', port=8000, threaded=True)  # noqa: S104
