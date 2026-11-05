"""Retry decorator for transient Anthropic overload errors (529/503) — as Tangent.

Only safe on calls rejected before any token is consumed (`batches.create`).
"""

from __future__ import annotations

import logging

from anthropic import APIStatusError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def is_anthropic_overloaded(exc: BaseException) -> bool:
    return isinstance(exc, APIStatusError) and exc.status_code in (503, 529)


retry_on_overload = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception(is_anthropic_overloaded),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
