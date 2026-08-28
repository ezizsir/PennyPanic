import logging
from datetime import datetime, timedelta

class TimezoneFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        record.created += 5 * 3600  # Add 5 hours in seconds
        return super().formatTime(record, datefmt)

# Create a logger instance
logger = logging.getLogger('trading_bot')
logger.setLevel(logging.DEBUG)  # Set the logging level

# Create handlers
file_handler = logging.FileHandler('trading_bot.log')  # Log to file
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()  # Log to console
console_handler.setLevel(logging.INFO)

# Create a formatter and add it to handlers
formatter = TimezoneFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)
