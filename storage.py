import pandas as pd
import numpy as np
import os
import talib
from datetime import datetime



# Function to store ticker data
def store_ticker_data(data: pd.DataFrame, ticker: str, storage_dir: str = "ticker_data"):
    """
    Stores the ticker data into a CSV file for later use.

    Args:
        data (pd.DataFrame): The data to store (should have 1000 rows, typical OHLCV format).
        ticker (str): The symbol of the ticker (e.g., 'BTCUSDT').
        storage_dir (str): Directory to store the files. Default is "ticker_data".
    """
    os.makedirs(storage_dir, exist_ok=True)
    file_path = os.path.join(storage_dir, f"{ticker}.csv")
    data.to_csv(file_path, index=False)
    # print(f"Data for {ticker} stored successfully at {file_path}.")

# Function to get ticker data
def get_ticker_data(ticker: str, storage_dir: str = "ticker_data") -> pd.DataFrame:
    """
    Retrieves the stored ticker data as a DataFrame.

    Args:
        ticker (str): The symbol of the ticker to retrieve (e.g., 'BTCUSDT').
        storage_dir (str): Directory where the files are stored. Default is "ticker_data".

    Returns:
        pd.DataFrame: The requested ticker data.
    """
    file_path = os.path.join(storage_dir, f"{ticker}.csv")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No data found for {ticker} in {storage_dir}.")
    
    return pd.read_csv(file_path)

def initialize_dataframe(candlesticks):
    """
    Initializes and populates a DataFrame with OHLCV data and calculates EMA indicators.

    Args:
        candlesticks (list): A list of candlestick data. Each candlestick should have:
            [0]: Open time (in milliseconds),
            [1]: Open price,
            [2]: High price,
            [3]: Low price,
            [4]: Close price,
            [7]: Volume.

    Returns:
        pd.DataFrame: DataFrame containing OHLCV data and EMA values.
    """
    # Initialize lists to collect OHLC data
    data = {
        "time": [],
        "open": [],
        "high": [],
        "low": [],
        "close": [],
        "volume": [],
    }

    # Populate the data lists
    for candlestick in candlesticks:
        open_time = datetime.fromtimestamp(int(candlestick[0]) / 1000)  # Convert milliseconds to readable time
        open_price = float(candlestick[1])
        high_price = float(candlestick[2])
        low_price = float(candlestick[3])
        close_price = float(candlestick[4])
        volume = float(candlestick[7])

        data["time"].append(open_time)
        data["open"].append(open_price)
        data["high"].append(high_price)
        data["low"].append(low_price)
        data["close"].append(close_price)
        data["volume"].append(volume)

    # Convert the lists into a pandas DataFrame
    df = pd.DataFrame(data)

    # Calculate EMAs
    df["ema8"] = talib.EMA(df["close"], timeperiod=8)
    df["ema21"] = talib.EMA(df["close"], timeperiod=21)
    df["ema55"] = talib.EMA(df["close"], timeperiod=55)

    return df