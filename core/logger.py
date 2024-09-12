import os
import sys
import logging
import signal
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import io

# Create logs directories if they don't exist
api_log_dir = "logs/api"
system_log_dir = "logs/system"
os.makedirs(api_log_dir, exist_ok=True)
os.makedirs(system_log_dir, exist_ok=True)

# Get today's date
log_file_date = datetime.now().strftime("%d_%m_%Y")

# Create formatters
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Set up System log handlers
system_file_handler = TimedRotatingFileHandler(os.path.join(system_log_dir, f"{log_file_date}.txt"), when="midnight", backupCount=30)
system_file_handler.setFormatter(file_formatter)
system_console_handler = logging.StreamHandler(sys.stdout)
system_console_handler.setFormatter(console_formatter)

# Configure the System logger
system_logger = logging.getLogger("system_logger")
system_logger.setLevel(logging.DEBUG)
system_logger.addHandler(system_file_handler)
system_logger.addHandler(system_console_handler)
system_logger.propagate = False

# Set up API log handlers
api_file_handler = TimedRotatingFileHandler(os.path.join(api_log_dir, f"{log_file_date}.txt"), when="midnight", backupCount=30)
api_file_handler.setFormatter(file_formatter)

# Configure the API logger
api_logger = logging.getLogger("api_logger")
api_logger.setLevel(logging.INFO)
api_logger.addHandler(api_file_handler)
api_logger.propagate = False


# Redirect stderr to capture early exceptions
class StderrCatcher(io.StringIO):
    def write(self, txt):
        if txt.strip():  # Only log non-empty lines
            system_logger.error("EARLY EXCEPTION: %s", txt.rstrip())
        super().write(txt)


sys.stderr = StderrCatcher()

original_stdout = sys.stdout


class StdoutCatcher(io.StringIO):
    def write(self, txt):
        if txt.strip():  # Only log non-empty lines
            system_logger.info(txt.rstrip())
        original_stdout.write(txt)


sys.stdout = StdoutCatcher()


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        system_logger.info("Server stopped by user (KeyboardInterrupt)")
    elif issubclass(exc_type, SystemExit):
        system_logger.info(f"Application exiting with SystemExit: {exc_value}")
    else:
        system_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def signal_handler(signum, frame):
    system_logger.info(f"Received signal {signum}. Shutting down.")
    raise SystemExit(0)


def setup_exception_logging():
    sys.excepthook = handle_exception

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# Add a test log message
system_logger.debug("Logging system initialized")


# This function should be called in your main.py
def setup_uvicorn_logging():
    # Remove default handlers
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = []
    uvicorn_logger.propagate = True

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = []
    uvicorn_access_logger.propagate = True

    # Adjust the log level of uvicorn loggers
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Capture any exceptions that occurred before logger was set up
if hasattr(sys.stderr, 'getvalue'):
    early_exceptions = sys.stderr.getvalue()
    if early_exceptions:
        system_logger.error("Exceptions occurred before logger was fully set up:\n%s", early_exceptions)