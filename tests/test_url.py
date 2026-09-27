import pytest

import datastar_py


@pytest.mark.parametrize(
    ("version", "ref"),
    (
        ("", ""),
        ("1", "@v1"),
        ("v1", "@v1"),
        ("1.0", "@v1.0"),
        ("v1.0", "@v1.0"),
        ("1.0.4", "@v1.0.4"),
        ("v1.0.4", "@v1.0.4"),
        ("1.0.0-RC.7", "@v1.0.0-RC.7"),
        ("v1.0.0-RC.7", "@v1.0.0-RC.7"),
    ),
)
def test_url_versions(version, ref):
    assert datastar_py.url(version) == (
        f"https://cdn.jsdelivr.net/gh/starfederation/datastar{ref}/bundles/datastar.js"
    )


def test_url_default():
    assert datastar_py.url() == (
        "https://cdn.jsdelivr.net/gh/starfederation/datastar/bundles/datastar.js"
    )


@pytest.mark.parametrize(
    "version",
    (
        "v",
        "v1.",
        "1..0",
        "1.0.4.1",
        "1-RC.7",
        "1.0-RC.7",
        "1.0.4-",
        "1.0.4-RC.",
        "latest",
        "v1/something",
        "v1?x=1",
        "v1#fragment",
    ),
)
def test_url_rejects_invalid_versions(version):
    with pytest.raises(ValueError, match="version"):
        datastar_py.url(version)


@pytest.mark.parametrize("version", (1, 1.0, True, b"v1", [], {}))
def test_url_rejects_invalid_types(version):
    with pytest.raises(TypeError, match="version must be a string or None"):
        datastar_py.url(version)
