"""Fixture handler for testing successful execution."""


def lambda_handler(event, context=None):
    """Echoes query parameters or name in greeting."""
    query_params = event.get("queryStringParameters") or event.get("query_params") or {}
    name = query_params.get("name", "TestUser")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "X-ZeroDock-Test": "True"},
        "body": {
            "message": f"Hello, {name}!",
            "requestId": context.request_id if context else "unknown",
        },
    }
