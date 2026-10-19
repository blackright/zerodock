"""Sample mock serverless function for ZeroDock local testing."""


def lambda_handler(event, context=None):
    """Simple greeting handler accepting query parameters."""
    query_params = event.get("queryStringParameters") or event.get("query_params") or {}
    name = query_params.get("name", "World")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": {
            "message": f"Hello, {name}! Sent natively from ZeroDock."
        }
    }
