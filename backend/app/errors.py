"""Application-level exception hierarchy (same pattern as Tangent).

Each exception carries an HTTP status code and a human-readable detail, in
French since the app speaks French. The global handler in `main.py`
translates instances to JSON responses.
"""

# A service we depend on failed. Not 502: Cloudflare replaces 502/504 from
# the origin with its own page and the reason never reaches the app.
UPSTREAM_DOWN = 503


class AppError(Exception):
    """Base for all expected, recoverable errors. Carries an HTTP status."""

    status_code: int = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class InvalidRequestError(AppError):
    status_code = 422


class LLMUnavailableError(AppError):
    """No API key, Anthropic overloaded, or the model answered something unusable."""

    status_code = UPSTREAM_DOWN


class BudgetExceededError(AppError):
    """The global daily LLM cap is reached (ADR-015 of Tangent)."""

    status_code = UPSTREAM_DOWN
