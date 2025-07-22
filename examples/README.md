# Datastar Python SDK Examples

## Running Examples with `uv`

All examples (except Django) include Inline Script Metadata (PEP 723), allowing them to be run with [uv](https://docs.astral.sh/uv/) without first installing dependencies.

### General Instructions

Navigate to the specific example directory and run:

```sh
uv run <script-name>
```

For example:
- `cd examples/fastapi && uv run app.py`
- `cd examples/fasthtml && uv run simple.py`
- `cd examples/sanic && uv run app.py`

### Django

The Django example has its own `pyproject.toml` with dependencies. Navigate to the Django directory and run:

```sh
uv run manage.py runserver
```

## Alternative: Running with `pip`

If you prefer using `pip`, you can create a virtual environment and install the dependencies listed in each script's metadata comments manually:

```sh
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install datastar-py <other-dependencies-from-script>
python <script-name>
```

Refer to the `# dependencies = [...]` section at the top of each example script to see what packages to install.
