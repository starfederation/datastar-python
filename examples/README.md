# Datastar Python SDK Examples

## How to Run These Examples with `uv`

All of the examples here (except Django) include Inline Script Metadata (PEP 723), allowing them to be run with [uv](https://docs.astral.sh/uv/) without first installing dependencies.

The following commands assume you are running them from the root of the repository.

### Django

We use the `--with` argument to declare depdencies to run our Django app.

```sh
uv run --with django --with daphne ./examples/django/manage.py runserver
```

### FastAPI

```sh
uv run ./examples/fastapi/app.py
```

### FastHTML

```sh
uv run ./examples/fasthtml/simple.py
```

```sh
uv run ./examples/fasthtml/advanced.py
```

### Litestar

```sh
uv run ./examples/litestar/app.py
```

### Quart

```sh
uv run ./examples/quart/app.py
```

### Sanic

```sh
uv run ./examples/sanic/app.py
```

## How to Run These Examples with `pip`

### Setup

```sh
python -m venv .venv
```

```sh
source .venv/bin/activate
```

### Django

```sh
pip install . daphne django
```

```sh
python ./examples/django/manage.py runserver
```

### FastAPI

```sh
pip install . uvicorn fastapi
```

```sh
python ./examples/fastapi/app.py
```

### FastHTML

```sh
pip install . python-fasthtml
```

```sh
python ./examples/fasthtml/simple.py
```

```sh
pip install . python-fasthtml great-tables pandas polars
```

```sh
python ./examples/fasthtml/advanced.py
```

### Litestar

```sh
pip install . uvicorn litestar
```

```sh
python ./examples/litestar/app.py
```

### Quart

```sh
pip install . quart
```

```sh
python ./examples/quart/app.py
```

### Sanic

```sh
pip install . sanic
```

```sh
python ./examples/sanic/app.py
```
