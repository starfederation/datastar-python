<p align="center"><img width="150" height="150" src="https://data-star.dev/static/images/rocket-512x512.png"></p>

# Datastar Python SDK

The `datastar-py` package provides a Python SDK for working with [Datastar](https://data-star.dev).

Datastar sends responses back to the browser using SSE. This allows the backend to
send any number of events, from zero to infinity in response to a single request.

`datastar-py` has helpers for creating those responses, formatting the events,
reading signals from the frontend, and generating the data-* HTML attributes.

The event generator can be used with any framework. There are also custom
helpers included for the following frameworks:

* [Django](https://www.djangoproject.com/)
* [FastAPI](https://fastapi.tiangolo.com/)
* [FastHTML](https://fastht.ml/)
* [Litestar](https://litestar.dev/)
* [Quart](https://quart.palletsprojects.com/en/stable/)
* [Sanic](https://sanic.dev/en/)
* [Starlette](https://www.starlette.io/)

## Event Generation Helpers

To use `datastar-py`, import the SSE generator in your app and then use
it in your route handler:

```python
import asyncio

from datastar_py import ServerSentEventGenerator as SSE
from datastar_py.sse import SSE_HEADERS
from quart import Quart, make_response
from datetime import datetime

app = Quart(__name__)

# Import frontend library via Content Distribution Network, create targets for Server Sent Events
@app.route("/")
def index():
    return '''
    <script type="module" src="https://cdn.jsdelivr.net/gh/starfederation/datastar@main/bundles/datastar.js"></script>
    <span data-on-load="@get('/updates')" id="currentTime"></span><br><span data-text="$currentTime"></div>
    '''


@app.route("/updates")
async def updates():
    async def time_updates():
        while True:
            yield SSE.patch_elements(
                f"""<span id="currentTime">{datetime.now().isoformat()}"""
            )
            await asyncio.sleep(1)
            yield SSE.patch_signals({"currentTime": f"{datetime.now().isoformat()}"})
            await asyncio.sleep(1)

    response = await make_response(time_updates(), SSE_HEADERS)
    response.timeout = None
    return response


app.run()
```

The example above is for the Quart framework, and is only using the event generation helpers.

## Response Helpers

A datastar response consists of 0..N datastar events. There are response
classes included to make this easy in all of the supported frameworks.

The following examples will work across all supported frameworks when the
response class is imported from the appropriate framework package.
e.g. `from datastar_py.quart import DatastarResponse` The containing functions
are not shown here, as they will differ per framework.

```python
# per framework Response import, eg:
# from datastar_py.fastapi import DatastarResponse
from datastar_py import ServerSentEventGenerator as SSE

# 0 events, a 204
@app.get("zero")
def zero_event():
    return DatastarResponse()
# 1 event
@app.get("one")
def one_event():
    return DatastarResponse(SSE.patch_elements("<div id='mydiv'></div>"))
# 2 events
@app.get("two")
def two_event():
    return DatastarResponse([
        SSE.patch_elements("<div id='mydiv'></div>"),
        SSE.patch_signals({"mysignal": "myval"}),
    ])

# N events, a long lived stream (for all frameworks but sanic)

@app.get("/updates")
async def updates():
    async def _():
        while True:
            yield SSE.patch_elements("<div id='mydiv'></div>")
            await asyncio.sleep(1)
    return DatastarResponse(_())

# A long lived stream for sanic
@app.get("/updates")
async def updates(request):
    response = await datastar_respond(request)
    # which is just a helper for the following
    # response = await request.respond(DatastarResponse())
    while True:
        await response.send(SSE.patch_elements("<div id='mydiv'></div>"))
        await asyncio.sleep(1)
```

### Response Decorator
To make returning a `DatastarResponse` simpler, there is a decorator
`datastar_response` available that automatically wraps a function result in
`DatastarResponse`. It works on async and regular functions and generator
functions. The main use case is when using a generator function, as you can
avoid a second generator function inside your response function. The decorator
works the same for any of the supported frameworks, and should be used under
any routing decorator from the framework.

```python
from datastar_py.sanic import datastar_response, ServerSentEventGenerator as SSE

@app.get('/my_route')
@datastar_response
def my_route(request):
    while True:
        yield SSE.patch_elements("<div id='mydiv'></div>")
        await asyncio.sleep(1)
```

## Signal Helpers
The current state of the datastar signals is included by default in every
datastar request. A helper is included to load those signals for each
framework. `read_signals`

```python
from datastar_py.quart import read_signals

@app.route("/updates")
async def updates():
    signals = await read_signals()
```

## Attribute Generation Helper
Datastar allows HTML generation to be done on the backend. datastar-py includes
a helper to generate data-* attributes in your HTML with IDE completion and
type checking. It can be used with many different HTML generation libraries.

```python
from datastar_py import attribute_generator as data

# htpy
button(data.on("click", "console.log('clicked')").debounce(1000).stop)["My Button"]
# FastHTML
Button("My Button", data.on("click", "console.log('clicked')").debounce(1000).stop)
Button(data.on("click", "console.log('clicked')").debounce(1000).stop)("My Button")
# f-strings
f"<button {data.on("click", "console.log('clicked')").debounce(1000).stop}>My Button</button>"
# Jinja, but no editor completion :(
<button {{data.on("click", "console.log('clicked')").debounce(1000).stop}}>My Button</button>
```

When using datastar with a different alias, you can instantiate the class yourself.

```python
from datastar_py.attributes import AttributeGenerator

data = AttributeGenerator(alias="data-star-")

# htmy (htmy will transform _ into - unless the attribute starts with _, which will be stripped)
data = AttributeGenerator(alias="_data-")
html.button("My Button", **data.on("click", "console.log('clicked')").debounce("1s").stop)
```
