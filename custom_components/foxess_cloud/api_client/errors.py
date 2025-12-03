"""Custom exceptions for the FoxESS Cloud API client."""

class FoxESSCloudApiError(Exception):
    """Raised when the FoxESS Cloud API returns an error response."""


class FoxESSCloudAuthError(FoxESSCloudApiError):
    """Raised when authentication fails (invalid API key)."""


class FoxESSCloudConnectionError(FoxESSCloudApiError):
    """Raised when the API cannot be reached."""
