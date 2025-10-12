import logging

def setup_logging(name: str = "bot"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    return logging.getLogger(name)
