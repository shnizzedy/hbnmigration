"""Test that module was installed."""

from hbnmigration import __version__


def test_version() -> None:
    """Test that module loads and includes a version string."""
    assert __version__ is not None
    assert isinstance(__version__, str)
