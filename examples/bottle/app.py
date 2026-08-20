import time
from datetime import datetime
from bottle import route, run, template
from datastar_py.bottle import ServerSentEventGenerator, datastar_response


html = """\
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <title>DATASTAR on Bottle (WSGI)</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
            <script type="module" src="https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.2/bundles/datastar.js"></script>
            <style>
            html, body { height: 100%; width: 100%; }
            body { background-image: linear-gradient(to right bottom, oklch(0.424958 0.052808 253.972015), oklch(0.189627 0.038744 264.832977)); }
            .container { display: grid; place-content: center; }
            .time { padding: 2rem; border-radius: 8px; margin-top: 3rem; font-family: monospace, sans-serif; background-color: oklch(0.916374 0.034554 90.5157); color: oklch(0.265104 0.006243 0.522862 / 0.6); font-weight: 600; }
            </style>
        </head>
        <body
            data-signals="{currentTime: 'CURRENT_TIME'}"
        >
        <div class="container">
            <div
            class="time"
            data-init="@get('/updates/')"
            >
            Current time from element: <span id="currentTime">CURRENT_TIME</span>
            </div>
            <div
            class="time"
            >
            Current time from signal: <span data-text="$currentTime">CURRENT_TIME</span>
            </div>
        </div>
        </body>
    </html>
"""


@route("/")
def home():
    return template(html.replace("CURRENT_TIME", f"{datetime.isoformat(datetime.now())}"))


@route("/updates/")
@datastar_response
def updates():
    while True:
        yield ServerSentEventGenerator.patch_elements(
            f"""<span id="currentTime">{datetime.now().isoformat()}"""
        )

        time.sleep(0.5)

        yield ServerSentEventGenerator.patch_signals({"currentTime": datetime.now().isoformat()})

        time.sleep(0.5)


if __name__ == "__main__":
    run(host="localhost", port=8080)
