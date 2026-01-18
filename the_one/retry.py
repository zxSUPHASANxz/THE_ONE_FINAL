import time
import logging
from functools import wraps
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


def retry_on_exception(max_retries: int = 3, exceptions: Tuple[Type[BaseException], ...] = (Exception,), backoff_factor: float = 1.5):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_retries:
                        logger.exception("Function %s failed after %d attempts", func.__name__, attempt)
                        raise
                    wait = backoff_factor ** (attempt - 1)
                    logger.warning("%s failed (attempt %d/%d): %s. Retrying in %.1fs...", func.__name__, attempt, max_retries, str(e)[:200], wait)
                    time.sleep(wait)
            # Should not reach here
            raise last_exc
        return wrapper
    return decorator
