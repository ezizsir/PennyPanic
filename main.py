import time
from HistoryCheckEMA55_conf_1year import HistoryCheck
import storage
from BacktestFunctions import print_progress_bar


KlineInterval = 15
USD_PER_ENTRY = 100

class Stopwatch:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    def elapsed_time(self):
        if self.start_time is None or self.end_time is None:
            raise ValueError("Stopwatch has not been started or stopped.")
        return self.end_time - self.start_time

if __name__ == "__main__":
    stopwatch = Stopwatch()
    stopwatch.start()

    tickerCount = 0

    with open('futures.txt') as file:
        line_count = sum(1 for _ in file)

    with open('futures.txt') as file:
        for line in file:
            tickerCount += 1
            Ticker = line.strip()

            storage_dir = "yearData"  # per-ticker CSVs cached by the data pipeline

            dataframe = storage.get_ticker_data(Ticker, storage_dir)

            try:
                HistoryCheck(dataframe, Ticker, KlineInterval, USD_PER_ENTRY)
            except Exception as e:
                print(f"An error occurred while processing {Ticker}: {e}")

            print_progress_bar(tickerCount, line_count)

    stopwatch.stop()
    print(f"Elapsed time: {stopwatch.elapsed_time()} seconds")