import requests
import time
from HistoryCheckFunc import HistoryCheck
import threading
import orders

def pretty_print_margin_info(d):
    pretty_dict = '{\n'
    
    # Print total values
    for key, value in d.items():
        if isinstance(value, dict):
            pretty_dict += f'    "{key}": {{\n'
            for sub_key, sub_value in value.items():
                pretty_dict += f'        "{sub_key}": "{sub_value}",\n'
            pretty_dict = pretty_dict.rstrip(",\n") + '\n'  # Remove last comma
            pretty_dict += '    },\n'
        elif isinstance(value, list):
            pretty_dict += f'    "{key}": [\n'
            for item in value:
                pretty_dict += '        {\n'
                for item_key, item_value in item.items():
                    pretty_dict += f'            "{item_key}": "{item_value}",\n'
                pretty_dict = pretty_dict.rstrip(",\n") + '\n'  # Remove last comma
                pretty_dict += '        },\n'
            pretty_dict = pretty_dict.rstrip(",\n") + '\n'  # Remove last comma
            pretty_dict += '    ],\n'
        else:
            pretty_dict += f'    "{key}": "{value}",\n'

    pretty_dict = pretty_dict.rstrip(",\n") + '\n'  # Remove last comma
    pretty_dict += '}'

    return pretty_dict

###############################################################

tickerCount = 0

weightLimit = orders.getWeightLimit()

walletData = orders.get_all_asset_info()
print(pretty_print_margin_info(walletData.json()))

weightPerRequest = 5

def reset_counter():
    global total_used_weight
    total_used_weight = 0
    print("Counter reset to 0")
    
    # Schedule the reset function to run again after 60 seconds
    threading.Timer(60, reset_counter).start()

# Start the reset cycle
reset_counter()

i = 1
# while repeat:
with open('futuresSample.txt') as file:
    for line in file:
        tickerCount += 1
        Ticker = line.strip()
        gotAResponse = False


        while (total_used_weight > weightLimit):
            print("Exceeded per minute rate")
            time.sleep(1)

        start_time = time.time()

        # Make a request
        while not gotAResponse:
            try:
                print(f"{i}: Changing leverage for {line}")
                leverage_response = orders.set_leverage(Ticker, 20)

                gotAResponse = True

                # End time to check function speed
                end_time = time.time()

                # Calculate the time difference in milliseconds
                execution_time = (end_time - start_time) * 1000  # Convert seconds to milliseconds

                print(f"Internet dealay: {execution_time:.2f} ms")

            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
                # time.sleep(5)
        i += 1
        if leverage_response.status_code == 200:

            total_used_weight += weightPerRequest

            print(f"Total Used Weight: \033[91m{total_used_weight}\033[0m \n")
            

        elif leverage_response.status_code == 429 or leverage_response.status_code == 418:

            total_used_weight += weightPerRequest

            print(f"Total Used Weight: \033[91m{total_used_weight}\033[0m \n")


            # 429 error handling - rate limit exceeded
            retry_after = int(leverage_response.headers.get("Retry-After", 60))  # Default to 60 seconds if not specified
            print(f"Rate limit exceeded. Retrying after {retry_after} seconds.")
            time.sleep(retry_after + 1) 


        else:
            # Other error responses
            print("Error:", leverage_response.status_code, leverage_response.text)
            '''
            print("Retrying in 1 seconds")
            time.sleep(1)
            '''
