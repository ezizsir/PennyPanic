import pandas as pd
import time

EMA8 = 'ema8'
EMA21 = 'ema21'
EMA55 = 'ema55'

END_DATE = '2025-01-01'

def get_binance_time_intervals(start_date, interval_minutes=15):
    """
    Generate a list of time intervals for Binance API requests.

    Parameters:
    start_date (str): The start date in 'YYYY-MM-DD' format.
    interval_minutes (int): The interval in minutes for each kline. Default is 15 minute.

    Returns:
    list: A list of tuples containing the start and end timestamps for each interval.
    """

    end_timestamp = int(pd.Timestamp(END_DATE).timestamp() * 1000)

    intervals = []
    start_timestamp = int(pd.Timestamp(start_date).timestamp() * 1000)
    interval_ms = interval_minutes * 60 * 1000
    max_klines = 1500

    while start_timestamp <= end_timestamp:
        next_timestamp = start_timestamp + (max_klines * interval_ms)
        intervals.append((start_timestamp))
        start_timestamp = next_timestamp             # Move to the next interval

    return intervals

def crossover_list(df):
    """
    For live testing:
        Gotta provide enough historic data to first generate ema55 and then
        for crossovers to actually occur

    Check for crossover points between EMA21 and EMA55 columns in the DataFrame.

    This function iterates through the DataFrame and identifies the indexes where
    the EMA21 column crosses above or below the EMA55 column.

    Parameters:
    df (pandas.DataFrame): The DataFrame containing the EMA21 and EMA55 columns.
    index int: index to be checked before

    Returns:
    list: an index closes to but smaller than 
    """
    
    indexes = []
    for i in range(1, len(df)):
        if (df[EMA21].iloc[i] > df[EMA55].iloc[i] and df[EMA21].iloc[i-1] <= df[EMA55].iloc[i-1]) or \
           (df[EMA21].iloc[i] < df[EMA55].iloc[i] and df[EMA21].iloc[i-1] >= df[EMA55].iloc[i-1]):
            indexes.append(i)

    return indexes


def last_crossover(indexes, analyzingIndex):

    if not indexes:
        return None

    left, right = 0, len(indexes) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if indexes[mid] < analyzingIndex:
            left = mid + 1
        else:
            right = mid - 1

    return indexes[right] if right >= 0 else None

def unnecessary_BoS(df, ohlc):

    """
    This function removed unnessecary BoS signals from the DataFrame. it detect them by checking 
    if there is a ChoCh between the BoS start and finish.

    Args:
        df (pandas.DataFrame): The input DataFrame containing columns 'BOS' and 'BrokenIndex'.

    Returns:
        pandas.DataFrame: The same DataFrame with potential modifications to the 'BOS' column.
    """

    '''
    pd.set_option('display.max_rows', None)  # Display all rows
    pd.set_option('display.max_columns', None)  # Display all columns
    print(df)
    '''

    for index, row in df.iterrows():
        if not pd.isna(row['BOS']):
            print(f"{row} at: {ohlc.iloc[index]['time']}")
            checkBetween = row['BrokenIndex']

            for j, choch in df.iterrows():
                if not pd.isna(choch['CHOCH']):

                    if choch['BrokenIndex'] > index and choch['BrokenIndex'] < checkBetween:
                        df.at[index, 'BOS'] = pd.NA

                        checkBetween = int(checkBetween)
                
                        print(f"Unnecessary_BoS at: {ohlc.iloc[checkBetween]['time']}")
                        print(f"Choch at index: {j} - {choch['BrokenIndex']}")

    return df

def print_progress_bar(iteration, total, prefix='Progress', suffix='', decimals=1, length=70, fill='█', print_end="\r"):
    """
    Call in a loop to create terminal progress bar
    
    Parameters:
    iteration (int): current iteration
    total (int): total iterations
    prefix (str): prefix string
    suffix (str): suffix string
    decimals (int): positive number of decimals in percent complete
    length (int): character length of bar
    fill (str): bar fill character
    print_end (str): end character (e.g. "\r", "\r\n")
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # Print New Line on Complete
    if iteration == total: 
        print()
