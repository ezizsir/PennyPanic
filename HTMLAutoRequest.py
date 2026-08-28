import requests
import time
import threading
import os
from logger_config import logger
import orders
import helperFunction

# Public kline endpoints don't require a key; set one only if you need signed calls.
api_key = os.environ.get('BINANCE_API_KEY', '')

repeat = True       # set TRUE and fix indentation to loop over the tickers again

interval = '15m'    # MUST USE 5MIN FOR COMPATIBILITY WITH CONVERSION TO OTHER TIME INTERVALS
limit = 300         # USE A NUMBER DEVISIBLE BY 6 AND GREATER THAN 180 TO BE CONVERTIBLE TO DIFFERENT TIMEFRAMES

high_volume = ['BTCUSDT', 'SOLUSDT', 'ETHUSDT', 'YFIUSDT', "AVAXUSDT", "AAVEUSDT"]         # ignored due to being high volume tickers
active_positions = []                                              # ignored to not reenter the same position twice
temporary_ignore = []

def get_weight_per_request(limit):
    # Check which range the limit falls into and assign the corresponding weight
    if 1 <= limit < 100:
        return 1
    elif 100 <= limit < 500:
        return 2
    elif 500 <= limit <= 1000:
        return 5
    elif limit > 1000:
        return 10
    else:
        raise ValueError("Limit must be a positive integer.")
    
weightPerRequest = get_weight_per_request(limit)

headers = {
    'X-MBX-APIKEY': api_key
}

tickerCount = 0

# Endpoint URL for Binance Index Price Kline (candlestick) data
url = "https://fapi.binance.com/fapi/v1/klines"

weightLimit =  orders.getWeightLimit()

# helperFunction.wait_for_new_candlestick()

def reset_counter():
    global total_used_weight
    total_used_weight = 0
    print("Counter reset to 0")
    
    # Schedule the reset function to run again after 60 seconds
    threading.Timer(60, reset_counter).start()

# Start the reset cycle
reset_counter()

while repeat:
    with open('futures.txt') as file:
        for line in file:
            tickerCount += 1
            Ticker = line.strip()

            if Ticker in high_volume:           # Ignore ticker due to being high volume
                continue

            gotAResponse = False

            position_entry_weight = 0

            print(f"\nRequesting {tickerCount}: {Ticker}")

            # Define the parameters for the request
            params = {
                'symbol': Ticker, 
                'interval': interval,
                'limit': limit
            }


            while (total_used_weight > weightLimit):
                logger.warning("Exceeded per minute rate")
                time.sleep(1)

            start_time = time.time()

            # Make a request
            while not gotAResponse:
                try:

                    response = requests.get(url, headers=headers, params=params)
                    gotAResponse = True

                    # End time to check function speed
                    end_time = time.time()

                    # Calculate the time difference in milliseconds
                    execution_time = (end_time - start_time) * 1000  # Convert seconds to milliseconds

                    print(f"Internet dealay: {execution_time:.2f} ms")

                except requests.exceptions.RequestException as e:
                    print(f"Request failed: {e}")
                    time.sleep(1)
            
            if response.status_code == 200 or response.status_code == 429 or response.status_code == 418:
                # If request is successful, break the loop and process data
                candlesticks = response.json()

                total_used_weight += weightPerRequest

                weight = helperFunction.analyze(
                    Ticker, 
                    candlesticks, 
                    active_positions,
                    temporary_ignore, 
                    interval
                )
                
                if weight is not None:
                    total_used_weight += weight

                print(f"Total Used Weight: \033[91m{total_used_weight}\033[0m")

                if len(active_positions) != 0:
                    if any(position['ticker'] == Ticker for position in active_positions):

                        logger.info(f"Processing active positions for {Ticker}. Total active positions: {len(active_positions)}")
                        ohlc = helperFunction.get_last_candlestick(candlesticks)
                        logger.debug(f"Latest OHLC data for {Ticker}: {ohlc}")

                        orders.process_active_positions(
                            active_positions,
                            Ticker
                        )
                        
                        '''
                        orders.update_stop_loss(
                            active_positions,
                            Ticker,
                            ohlc
                        )
                        '''
                if response.status_code == 429 or response.status_code == 418:

                    # 429 error handling - rate limit exceeded
                    retry_after = int(response.headers.get("Retry-After", 60))  # Default to 60 seconds if not specified
                    print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
                    logger.info("Rate limit exceeded. Retrying after %s seconds.", retry_after)
                    time.sleep(retry_after + 1) 
                

            else:
                # Other error responses
                print("Error:", response.status_code, response.text)
                logger.error("HTTP error occurred: status_code=%s, response_text=%s", response.status_code, response.text)
