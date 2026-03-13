import sys
from loguru import logger

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # Add standardized JSON or colorized output
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # File logging for critical errors
    logger.add(
        "logs/error.log",
        rotation="10 MB",
        level="ERROR",
        compression="zip"
    )

    # Dedicated log for Autonomous Decisions
    logger.add(
        "logs/autonomous.log",
        rotation="1 day",
        level="INFO",
        # filter=lambda record: any(tag in record["message"] for tag in ["Director:", "Council:", "Discovery", "SUCCESS", "EXECUTED", "FAILED"])
    )

setup_logging()
