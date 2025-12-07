def test_smoke():
    """Basic smoke test to ensure test runner works and imports are valid."""
    from src.main import main  # noqa: F401
    assert True
