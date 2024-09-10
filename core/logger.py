import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

# Create logs directories if they don't exist
api_log_dir = "logs/api"
sql_log_dir = "logs/sql"
system_log_dir = "logs/system"
os.makedirs(api_log_dir, exist_ok=True)
os.makedirs(sql_log_dir, exist_ok=True)
os.makedirs(system_log_dir, exist_ok=True)

# Get today's date
log_file_date = datetime.now().strftime("%d_%m_%Y")

# Create formatters
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Set up API log handlers
api_file_handler = TimedRotatingFileHandler(os.path.join(api_log_dir, f"{log_file_date}.txt"), when="midnight", backupCount=30)
api_file_handler.setFormatter(file_formatter)
api_console_handler = logging.StreamHandler(sys.stdout)
api_console_handler.setFormatter(console_formatter)

# Set up SQL log handler (file only)
sql_file_handler = TimedRotatingFileHandler(os.path.join(sql_log_dir, f"{log_file_date}.txt"), when="midnight", backupCount=30)
sql_file_handler.setFormatter(file_formatter)

# Set up System log handlers
system_file_handler = TimedRotatingFileHandler(os.path.join(system_log_dir, f"{log_file_date}.txt"), when="midnight", backupCount=30)
system_file_handler.setFormatter(file_formatter)
system_console_handler = logging.StreamHandler(sys.stdout)
system_console_handler.setFormatter(console_formatter)

# Configure the API logger
api_logger = logging.getLogger("api_logger")
api_logger.setLevel(logging.INFO)
api_logger.handlers = [api_file_handler, api_console_handler]
api_logger.propagate = False

# Configure the SQL logger (file only)
sql_logger = logging.getLogger("sqlalchemy.engine")
sql_logger.setLevel(logging.INFO)
sql_logger.handlers = [sql_file_handler]
sql_logger.propagate = False

# Configure the System logger
system_logger = logging.getLogger("system_logger")
system_logger.setLevel(logging.ERROR)
system_logger.handlers = [system_file_handler, system_console_handler]
system_logger.propagate = False


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    system_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception
