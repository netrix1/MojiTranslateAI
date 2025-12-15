import logging
import sys
import json
from loguru import logger

class InterceptHandler(logging.Handler):
    """
    Redirect standard logging to Loguru.
    """
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logging():
    # Intercept everything (uvicorn, fastapi, etc)
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Configure Loguru
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "serialize": True, # JSON output
                "format": "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
                "level": "INFO", 
                # If serialize=True, format is largely ignored for valid JSON structure unless custom
            }
        ]
    )
    
    logger.info("Structured logging initialized")
