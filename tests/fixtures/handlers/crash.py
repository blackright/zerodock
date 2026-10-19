"""Handler fixture that intentionally raises an exception for testing."""


def lambda_handler(event, context=None):
    """Fails immediately to test exception handling and traceback reporting."""
    raise ValueError("Simulated crash for debugging")
