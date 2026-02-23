"""
Centralized logging configuration.
Ensures logs are written to files and console.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(log_dir=None, app_name="Instagram"):
    """
    Configure logging for both file and console output.
    
    Args:
        log_dir: Directory to store logs (defaults to current directory)
        app_name: Name for the application (used in log file names)
    
    Returns:
        Root logger instance
    """
    if log_dir is None:
        log_dir = Path.cwd()
    else:
        log_dir = Path(log_dir)
    
    # Create logs directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file path with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"{app_name}_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Log the startup message
    root_logger.info(f"Logging initialized. Log file: {log_file}")
    
    return root_logger


def get_logger(name):
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
