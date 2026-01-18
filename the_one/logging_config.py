import logging


def setup_logging(level: str = "INFO") -> None:
    level_val = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level_val,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
