import time
from datetime import datetime, timedelta
import threading
from logger_config import logger
from CheckJackpot_ema55 import CheckJackpot
import orders

USD_PER_ENTRY = 6

def wait_for_new_candlestick():
    """
    Waits until a new 15-minute candlestick has started.
    """
    while True:
        # Get the current time
        now = datetime.utcnow()

        # Calculate the time for the next 15-minute interval
        next_interval = (now + timedelta(minutes=15 - now.minute % 15)).replace(second=0, microsecond=0)

        # Calculate the time difference
        time_to_wait = (next_interval - now).total_seconds()

        if time_to_wait >= 885:
            print("\rNew candlestick started!                  ")  # Clear previous output
            break  # A new candlestick has just started
        
        # Update output on the same line
        print(f"\rWaiting for the next candlestick... ({time_to_wait:.2f} seconds remaining)", end="")
        time.sleep(min(time_to_wait, 1))  # Check frequently, but sleep for at least 1 second to reduce CPU usage


def delayed_remove(array, ticker):
    """
    Non-blocking version of wait_for_new_candlestick using threading.

    Args:
        callback (function): The function to execute once the new candlestick starts.
    """
    def worker():
        now = datetime.utcnow()

        # Calculate the time for the next 15-minute interval
        next_interval = (now + timedelta(minutes=15 - now.minute % 15)).replace(second=0, microsecond=0)

        # Calculate the time difference
        time_to_wait = (next_interval - now).total_seconds()

        # Add another 30 minutes to simulate a candle closure 
        time_to_wait += 1800

        # Sleep until the new candlestick starts
        time.sleep(time_to_wait)

        # Execute the callback function
        array.remove(ticker)

    # Start the worker thread
    threading.Thread(target=worker, daemon=True).start()

def remove_specific_instance(dict_list, criteria):
    """
    Remove the first dictionary matching the criteria from the list.

    Args:
        dict_list (list): List of dictionaries.
        criteria (dict): Dictionary containing fields and values to match.

    Returns:
        list: Updated list with the first matching dictionary removed.
    """

    for i, d in enumerate(dict_list):
        if all(d[key] == value for key, value in criteria.items()):
            del dict_list[i]
            break
    return dict_list

def remove_all_instances(dict_list, ticker):
    """
    Remove all dictionaries containing the specified ticker from the list.

    Args:
        dict_list (list): List of dictionaries.
        ticker (str): The ticker name to match.

    Returns:
        list: Updated list with all matching dictionaries removed.
    """
    return [d for d in dict_list if d.get('ticker') != ticker]

def get_last_candlestick(candlesticks):
    """
    Extract the last candlestick data from the candlesticks response.

    Args:
        candlesticks (list): List of candlestick data, where each candlestick is a list.

    Returns:
        dict: A dictionary containing the last candlestick data with meaningful keys.
    """
    if not candlesticks or not isinstance(candlesticks, list):
        raise ValueError("Candlesticks data is invalid or empty.")

    # Extract the last candlestick (the last list entry)
    last_candlestick = candlesticks[-1]

    # Map the candlestick data to a dictionary with meaningful keys
    return {
        "open_time": last_candlestick[0],
        "open": float(last_candlestick[1]),
        "high": float(last_candlestick[2]),
        "low": float(last_candlestick[3]),
        "close": float(last_candlestick[4]),
        "volume": float(last_candlestick[5])
    }

def is_duplicate_entry(active_positions, new_position):
    """
    Check if a position with the same ticker and stop loss already exists.
    
    Args:
        active_positions (list): List of active positions (dict).
        new_position (dict): The position to enter with 'ticker' and 'stop_loss'.
    
    Returns:
        bool: True if a duplicate exists, False otherwise.
    """
    for position in active_positions:
        if (
            position['ticker'] == new_position['ticker'] and
            position.get('stop_loss') == new_position.get('stop_loss')
        ):
            return True
    return False


def analyze(Ticker, candlesticks, active_positions, temporary_ignore, interval):
    if Ticker not in temporary_ignore:
        print(f"Analyzing {Ticker}")

        position_to_enter = CheckJackpot(candlesticks, interval, Ticker)
        if position_to_enter is None:
            print(f"{Ticker}: No position to enter.")
            return 0

        # See if its a dublicate entry by comparing ticker and sl
        new_position = {'ticker': Ticker, 'stop_loss': position_to_enter[4]}
        if is_duplicate_entry(active_positions, new_position):
            logger.info(f"{Ticker}: Skiping double entry")
            return 0

        position_to_enter.append(USD_PER_ENTRY)
        logger.info(f"{Ticker}: Attempting to place order.")

        try:
            feedback = orders.combo(position_to_enter)  # Used weight: 9
            if 'error' in feedback:
                logger.error(f"{Ticker}: Order failed with error: {feedback['error']}")
                return 0

            active_positions.append(feedback)
            logger.info(f"{Ticker}: Order placed successfully. Feedback: {feedback}")
            logger.debug(f"Appended {Ticker} to active positions{active_positions}")


        except Exception as e:
            logger.error(f"{Ticker}: Error placing order - {e}")

        temporary_ignore.append(Ticker)
        logger.info(f"{Ticker}: Added to temporary_ignore list: {temporary_ignore}")

        delayed_remove(temporary_ignore, Ticker)
        logger.info(f"{Ticker}: Scheduled for delayed removal from temporary_ignore.")

        position_entry_weight = 9

        return position_entry_weight
