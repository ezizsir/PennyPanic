import requests
import time
import hashlib
import hmac
import json
import os
from logger_config import logger
import math
import helperFunction


# Credentials come from the environment — never hardcode keys.
# See .env.example
API_KEY = os.environ.get('BINANCE_API_KEY', '')
API_SECRET = os.environ.get('BINANCE_API_SECRET', '')
BASE_URL = 'https://fapi.binance.com'  # Base URL for Binance Futures

priceCalculation = 'CONTRACT_PRICE'          # Choose between 'MARK_PRICE' OR 'CONTRACT_PRICE'
 

def sign_params(params):
    query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{query_string}&signature={signature}"

def create_signature(params):
    """Creates HMAC SHA256 signature for the request."""
    query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
    return hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def set_leverage(symbol, leverage):
    endpoint = '/fapi/v1/leverage'
    url = f"{BASE_URL}{endpoint}"

    params = {
        'symbol': symbol,
        'leverage': leverage,
        'timestamp': int(time.time() * 1000)
    }
    
    signed_params = sign_params(params)
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        response = requests.post(url, headers=headers, params=signed_params)
        response_data = response.json()
        
        if response.status_code == 200:
            logger.info(f"Leverage set to {leverage} for {symbol}. Response: {response_data}")
        else:
            logger.warning(f"Failed to set leverage. Status Code: {response.status_code}, Response: {response_data}")
        
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while setting leverage: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return e


def place_market_order(symbol, side, quantity):
    endpoint = '/fapi/v1/order'
    url = f"{BASE_URL}{endpoint}"

    params = {
        'symbol': symbol,
        'side': side,  
        'type': 'MARKET',
        'quantity': quantity,
        'newOrderRespType': 'RESULT',
        'timestamp': int(time.time() * 1000)
    }
    
    signed_params = sign_params(params)
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        response = requests.post(url, headers=headers, params=signed_params)
        response_data = response.json()
        
        if response.status_code == 200:
            logger.info(f"Market order placed: Symbol={symbol}, Side={side}, Quantity={quantity}.")
        else:
            logger.warning(f"Failed to place market order: Status Code={response.status_code}, Response={response_data}")
        
        return response

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while placing market order: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return e

def place_limit_order(symbol, side, price, quantity):
    """
    Place a limit order at a specific price on Binance Futures.

    Args:
        symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
        side (str): 'BUY' to buy, 'SELL' to sell.
        price (float): Price at which to place the order.
        quantity (float): Amount of the asset to buy/sell.

    Returns:
        Response: The non-JSON response object from Binance API.
    """
    endpoint = "/fapi/v1/order"
    url = f"{BASE_URL}{endpoint}"

    headers = {
        'X-MBX-APIKEY': API_KEY
    }

    order_payload = {
        'symbol': symbol,
        'side': side,
        'type': 'LIMIT',
        'price': f"{price:.8f}",
        'quantity': f"{quantity:.6f}",
        'newOrderRespType': 'RESULT',
        'reduceOnly': True,
        'timeInForce': 'GTC',
        'timestamp': int(time.time() * 1000)
    }

    signed_payload = sign_params(order_payload)

    try:
        response = requests.post(url, headers=headers, params=signed_payload)
        response_data = response.json()

        if response.status_code == 200:
            logger.info(f"Limit order placed: {response_data}")
        else:
            logger.warning(f"Failed to place limit order: Status Code={response.status_code}, Response={response_data}")

        return response  # Return the non-JSON response object

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while placing limit order: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return e


def place_take_limit_order(symbol, side, stop_price, limit_price, quantity):
    """
    Place a stop-limit order on Binance Futures with error handling and logger.

    Args:
        symbol (str): Trading pair (e.g., 'BTCUSDT').
        side (str): 'BUY' or 'SELL'.
        stop_price (float): Trigger price.
        limit_price (float): Execution price.
        quantity (float): Amount to trade.

    Returns:
        Response object: Response from the Binance API.
    """
    endpoint = '/fapi/v1/order'
    url = f"{BASE_URL}{endpoint}"

    params = {
        'symbol': symbol,
        'side': side,
        'type': 'STOP',            # Stop order type
        'stopPrice': stop_price,   # Trigger price
        'price': limit_price,      # Limit price for execution
        'quantity': quantity,      # Quantity of the order
        'reduceOnly': True,
        'workingType': priceCalculation,
        'timestamp': int(time.time() * 1000)
    }

    headers = {'X-MBX-APIKEY': API_KEY}

    try:
        signed_params = sign_params(params)
        response = requests.post(url, headers=headers, params=signed_params)
        # response.raise_for_status()  # Raise an error for non-2xx status codes
        
        # Log success
        logger.info(f"Stop-limit order placed successfully: {response.json()}")
        
        # Return the raw response object
        return response

    except requests.exceptions.RequestException as e:
        # Log any request-related errors
        logger.error(f"Failed to place stop-limit order: {e}")
        return None

    except Exception as e:
        # Log any other unexpected errors
        logger.error(f"An unexpected error occurred: {e}")
        return None


def set_stop_loss_take_profit(symbol, side, quantity, stop_price, take_profit_price):
    """
    Set stop loss and take profit for all long or short contracts on a specific ticker.
    
    Args:
        symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
        side (str): 'BUY' to close short positions, 'SELL' to close long positions.
        stop_price (float): Price to trigger the stop-loss order.
        take_profit_price (float): Price to trigger the take-profit order.

    Returns:
        tuple: (stop_response, take_profit_response)
    """

    endpoint = '/fapi/v1/order'
    url = f"{BASE_URL}{endpoint}"
    headers = {'X-MBX-APIKEY': API_KEY}

    try:
        stop_order = {
            'symbol': symbol,
            'side': side, 
            'type': 'STOP_MARKET',
            'stopPrice': stop_price,
            'quantity': quantity, 
            'newOrderRespType': 'RESULT',
            'workingType': priceCalculation,
            'reduceOnly': True,
            'timestamp': int(time.time() * 1000)
        }
        signed_stop_order = sign_params(stop_order)
        stop_response = requests.post(url, headers=headers, params=signed_stop_order)
        stop_data = stop_response.json()

        if stop_response.status_code == 200:
            logger.info(f"Stop-loss order placed: {stop_data}")
        else:
            logger.warning(f"Failed to place stop-loss order: Status Code={stop_response.status_code}, Response={stop_data}")
            raise Exception("Failed to place stop-loss order")

        # Take-profit order
        take_profit_order = {
            'symbol': symbol,
            'side': side,
            'type': 'TAKE_PROFIT_MARKET',
            'stopPrice': take_profit_price,
            'quantity': quantity, 
            'newOrderRespType': 'RESULT',
            'workingType': priceCalculation,
            'reduceOnly': True,
            'timestamp': int(time.time() * 1000)
        }
        signed_take_profit_order = sign_params(take_profit_order)
        take_profit_response = requests.post(url, headers=headers, params=signed_take_profit_order)
        take_profit_data = take_profit_response.json()

        if take_profit_response.status_code == 200:
            logger.info(f"Take-profit order placed: {take_profit_data}")
        else:
            logger.warning(f"Failed to place take-profit order: Status Code={take_profit_response.status_code}, Response={take_profit_data}")

        return stop_response, take_profit_response

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while placing orders: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return e


def set_stop_market(symbol, side, quantity, stop_price):
    """
    Set stop loss for all long or short contracts on a specific ticker.
    
    Args:
        symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
        side (str): 'BUY' to close short positions, 'SELL' to close long positions.
        stop_price (float): Price to trigger the stop-loss order.

    Returns:
        stop_response
    """

    endpoint = '/fapi/v1/order'
    url = f"{BASE_URL}{endpoint}"
    headers = {'X-MBX-APIKEY': API_KEY}

    try:
        stop_order = {
            'symbol': symbol,
            'side': side, 
            'type': 'STOP_MARKET',
            'stopPrice': stop_price,
            'quantity': quantity, 
            'newOrderRespType': 'RESULT',
            'workingType': priceCalculation,
            'reduceOnly': True,
            'timestamp': int(time.time() * 1000)
        }

        signed_stop_order = sign_params(stop_order)
        stop_response = requests.post(url, headers=headers, params=signed_stop_order)
        stop_response.raise_for_status()
        stop_data = stop_response.json()

        if stop_response.status_code == 200:
            logger.info(f"Stop-loss order placed: {stop_data}")
        else:
            logger.warning(f"Failed to place stop-loss order: Status Code={stop_response.status_code}, Response={stop_data}")
            raise Exception("Failed to place stop-loss order")
            
        
        return stop_response

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while placing orders: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return e

def cancel_order(symbol, orderID):
    endpoint = '/fapi/v1/order'
    url = f"{BASE_URL}{endpoint}"

    params = {
        'symbol': symbol,
        'orderId': orderID,  
        'timestamp': int(time.time() * 1000)
    }
    
    signed_params = sign_params(params)
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        response = requests.delete(url, headers=headers, params=signed_params)
        response.raise_for_status()
        response_data = response.json()

        if response.status_code == 200:
            logger.info(f"Order {orderID} cancelled successfully: {response_data}")
        else:
            logger.warning(f"Failed to cancel order {orderID}: Status Code={response.status_code}, Response={response_data}")
        
        return response  # Return the non-JSON response object

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while cancelling order {orderID}: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error while cancelling order {orderID}: {e}")
        return e


def hedge_mode(isHedge):
    """
    Change the position mode on Binance Futures.
    
    Args:
        hedge_mode (bool): True for Hedge mode, False for One-way mode.
    """
    endpoint = "/fapi/v1/positionSide/dual"
    url = f"{BASE_URL}{endpoint}"
    
    headers = {'X-MBX-APIKEY': API_KEY}

    mode = isHedge
    position_mode_payload = {
        'dualSidePosition': str(mode).lower(),
        'timestamp': int(time.time() * 1000)
    }
    
    # Sign the parameters using your sign_params() function
    signed_payload = sign_params(position_mode_payload)
    
    try:
        # Send the request with signed payload as query parameters
        response = requests.post(url, headers=headers, params=signed_payload)
        response_data = response.json()

        if response.status_code == 200:
            logger.info(f"Position mode changed successfully: {response_data}")
        else:
            logger.warning(f"Failed to change position mode: Status Code={response.status_code}, Response={response_data}")

        return response  # Return the non-JSON response object

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while changing position mode: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error while changing position mode: {e}")
        return e


def cross_margin(symbol, isCross):
    """
    Toggle the margin type between 'CROSSED' and 'ISOLATED' for a symbol on Binance Futures.
    
    Args:
        symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
        margin_type (str): 'CROSSED' for Crossed margin, 'ISOLATED' for Isolated margin.
    """
    endpoint = "/fapi/v1/marginType"
    url = f"{BASE_URL}{endpoint}"

    headers = {'X-MBX-APIKEY': API_KEY}

    margin_type = 'CROSSED' if isCross else 'ISOLATED'
    margin_payload = {
        'symbol': symbol,
        'marginType': margin_type,
        'timestamp': int(time.time() * 1000)
    }

    # Sign the parameters using your sign_params() function
    signed_payload = sign_params(margin_payload)
    
    try:
        # Send the request with signed payload as query parameters
        response = requests.post(url, headers=headers, params=signed_payload)
        response_data = response.json()

        if response.status_code == 200:
            logger.info(f"Margin type changed to {margin_type} for {symbol}: {response_data}")
        else:
            logger.warning(f"Failed to change margin type for {symbol}: Status Code={response.status_code}, Response={response_data}")

        return response  # Return the non-JSON response object

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while changing margin type for {symbol}: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error while changing margin type for {symbol}: {e}")
        return e


def get_all_asset_info():
    """Fetches all asset information from the account."""
    endpoint = '/fapi/v3/account'
    params = {
        'timestamp': int(time.time() * 1000)
    }
    params['signature'] = create_signature(params)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
        response_data = response.json()

        if response.status_code == 200:
            logger.info(f"Asset info fetched successfully")
        else:
            logger.warning(f"Failed to fetch asset info: Status Code={response.status_code}, Response={response_data}")

        return response  # Return the non-JSON response object

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching asset info: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error while fetching asset info: {e}")
        return e

def get_wallet_balance():
    """Fetches all asset information from the account, and returns avalible wallet balance"""
    endpoint = '/fapi/v3/account'
    params = {
        'timestamp': int(time.time() * 1000)
    }
    params['signature'] = create_signature(params)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
        response_data = response.json()

        if response.status_code == 200:
            logger.info(f"Asset info fetched successfully")
        else:
            logger.warning(f"Failed to fetch asset info: Status Code={response.status_code}, Response={response_data}")

        walletData = response.json() 
        balance = walletData['availableBalance']

        return balance

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching asset info: {e}")
        return e
    except Exception as e:
        logger.error(f"Unexpected error while fetching asset info: {e}")
        return e
    
    
def get_binance_ticker_info():
    """
    Fetch exchange information from Binance and pretty print the full ticker info.
    """
    endpoint = "/fapi/v1/exchangeInfo"

    try:
        logger.info("Fetching Binance ticker information.")

        response = requests.get(BASE_URL + endpoint)
        response.raise_for_status()  # Raise an error for non-2xx responses
        exchange_info = response.json()

        pretty_output = json.dumps(exchange_info, indent=4)
        print(pretty_output)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching exchange info: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

def get_current_price(ticker):
    """
    Fetch the current price of a specific ticker from Binance.

    Args:
        ticker (str): The symbol of the trading pair (e.g., 'BTCUSDT').

    Returns:
        float: Current price of the ticker.
    """
    endpoint = f"/fapi/v1/ticker/price?symbol={ticker}"

    try:
        response = requests.get(BASE_URL + endpoint)
        response.raise_for_status()
        data = response.json()
        price = float(data['price'])
        logger.info(f"Fetched price for {ticker}: {price}")
        return price
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        return None
    
def check_position(symbol):
    """
    Checks if a futures position is closed or how much is still open.

    Args:
        symbol (str): The trading pair, e.g., "BTCUSDT".

    Returns:
        dict: Information about the position (size, entry price, etc.).
    """
    try:
        # Use the pre-defined sign_params function
        params = sign_params({'timestamp': int(time.time() * 1000)})

        headers = {'X-MBX-APIKEY': API_KEY}

        # Make the request
        response = requests.get(f"{BASE_URL}/fapi/v2/account", headers=headers, params=params)
        response.raise_for_status()

        # Parse the response
        account_data = response.json()
        for position in account_data.get('positions', []):
            if position.get('symbol') == symbol:
                position_amt = float(position.get('positionAmt', 0))
                entry_price = float(position.get('entryPrice', 0))
                unrealized_pnl = float(position.get('unrealizedProfit', 0))

                if position_amt == 0:
                    logger.info(f"Position for {symbol} is closed.")
                    return {"status": "closed", "message": f"Position for {symbol} is closed."}
                else:
                    logger.debug(f"Position for {symbol} is open with amount: {position_amt}, entry price: {entry_price}, unrealized PnL: {unrealized_pnl}")
                    return {
                        "status": "open",
                        "positionAmt": position_amt,
                        "entryPrice": entry_price,
                        "unrealizedPnL": unrealized_pnl
                    }

        logger.warning(f"No position found for {symbol}.")
        return {"status": "not_found", "message": f"No position found for {symbol}."}

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error occurred: {e}")
        return e
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return e

def get_precision(ticker):
    """
    Fetch the tickSize and stepSize based on Binance's futures exchange info.

    Args:
        ticker (str): The trading pair, e.g., "BTCUSDT".

    Returns:
        dict: tickSize and stepSize values.
    """
    endpoint = "/fapi/v1/exchangeInfo"
    
    try:
        response = requests.get(BASE_URL + endpoint)
        response.raise_for_status()
        exchange_info = response.json()

        for symbol_data in exchange_info['symbols']:
            if symbol_data['symbol'] == ticker:
                # Extract tickSize and stepSize
                tick_size = None
                step_size = None

                for f in symbol_data['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        tick_size = float(f['tickSize'])
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                
                if tick_size is not None and step_size is not None:
                    return {
                        "tickSize": tick_size,
                        "stepSize": step_size
                    }

        logger.warning(f"Ticker {ticker} not found in exchange info.")
        return {"error": "Ticker not found"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching exchange info: {e}")
        return {"error": f"HTTP error: {e}"}
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return {"error": f"Unexpected error: {e}"}


def getWeightLimit():
    # Define the Binance API URL for Futures exchange info
    infoURL = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
    
    try:
        # Make the GET request
        response = requests.get(infoURL)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            
            # Extract and return the weight limit from rateLimits
            if 'rateLimits' in data:
                for rate_limit in data['rateLimits']:
                    if rate_limit['rateLimitType'] == 'REQUEST_WEIGHT':
                        weightLimit = rate_limit['limit']
                        logger.info(f"Successfully retrieved weight limit: {weightLimit}")
                        return weightLimit
                    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed with error: {str(e)}")
        return 2400
    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return 2400

def get_first_significant_position(value):
    """
    Get the position of the first significant figure for a float.

    Args:
        value (float): The input float.

    Returns:
        int: The position of the first significant figure.
    """
    if value == 0:
        raise ValueError("Value must be non-zero")
    
    # Get the absolute value to handle negative numbers
    abs_value = abs(value)
    
    # Calculate the position
    position = math.floor(math.log10(abs_value))

    position = position * -1

    return position

def combo(orderData):
    try:
        logger.info("combo function called with orderData: %s", orderData)

        ticker = orderData[0]
        side = orderData[1]
        currentPrice = orderData[2]
        leverage = orderData[3]
        stopLoss = orderData[4]
        takeProfit = orderData[5]
        bosPrice = orderData[6]
        usdPerEntry = orderData[7]

        side = 'BUY' if side == 'LONG' else 'SELL'

        logger.debug("Parsed orderData: ticker=%s, side=%s, currentPrice=%s, leverage=%s, stopLoss=%s, takeProfit=%s, usdPerEntry=%s",
                     ticker, side, currentPrice, leverage, stopLoss, takeProfit, usdPerEntry)

        # Fetch wallet balance
        result = get_wallet_balance()
        if isinstance(result, Exception):
            logger.error("Error fetching wallet balance: %s", result)
            return {"error": 'Error fetching wallet balance'}
        
        logger.debug("Wallet balance retrieved: %s", result)

        if float(result) < usdPerEntry:
            logger.warning("Wallet balance is too low: balance=%s, usdPerEntry=%s", result, usdPerEntry)
            return {"error": 'Error, Wallet balance is too low'}

        quantity = leverage * usdPerEntry / currentPrice
        logger.debug("Calculated quantity: %s", quantity)

        # Get precision
        precisions = get_precision(ticker)
        if 'error' in precisions:
            logger.error("Error getting precisions for ticker=%s", ticker)
            return {"error": 'Error getting precisions'}

        price_precision = get_first_significant_position(precisions['tickSize'])
        quantity_precision = get_first_significant_position(precisions['stepSize'])

        adjusted_quantity = round(quantity, quantity_precision)
        adjusted_stopLoss = round(stopLoss, price_precision)
        adjusted_takeProfit = round(takeProfit, price_precision)

        logger.debug("Adjusted values: quantity=%s, stopLoss=%s, takeProfit=%s", adjusted_quantity, adjusted_stopLoss, adjusted_takeProfit)

        if adjusted_quantity <= 0:
            logger.warning("Quantity is too low: %s", adjusted_quantity)
            return {"error": 'Error, Quantity is too low'}

        if side == 'BUY':
            close_side = 'SELL'
            adjusted_noLoss = round(currentPrice * 1.001, price_precision)
            noLoss_activation_price = round(currentPrice * 1.011, price_precision)
        else:
            close_side = 'BUY'
            adjusted_noLoss = round(currentPrice * 0.999, price_precision)
            noLoss_activation_price = round(currentPrice * 0.989, price_precision)

        logger.debug("Calculated close_side=%s, adjusted_noLoss=%s, noLoss_activation_price=%s",
                     close_side, adjusted_noLoss, noLoss_activation_price)

        # Place SL/TP
        result = set_stop_loss_take_profit(ticker, close_side, adjusted_quantity, adjusted_stopLoss, adjusted_takeProfit)
        if isinstance(result, Exception):
            logger.error("Error placing SL/TP for ticker=%s", ticker)
            return {"error": 'Error placing SL/TP'}

        logger.debug("SL/TP placed successfully: %s", result)

        JSON_result = [result[0].json(), result[1].json()]
        stop_loss_ID = JSON_result[0]['orderId']
        take_profit_ID = JSON_result[1]['orderId']

        # Place market order
        result = place_market_order(ticker, side, adjusted_quantity)
        if isinstance(result, Exception):
            logger.error("Error placing market order for ticker=%s, cancelling SL/TP orders", ticker)
            cancel_order(ticker, stop_loss_ID)
            cancel_order(ticker, take_profit_ID)
            return {"error": 'Error placing market order'}

        return {
            "ticker": ticker,
            "close_side": close_side,
            "stop_loss_ID": stop_loss_ID,
            "take_profit_ID": take_profit_ID,
            "position_volume": adjusted_quantity,
            "updated_stopLoss_price": adjusted_noLoss,
            "activation_price": noLoss_activation_price,
            "stop_loss": adjusted_stopLoss,
            "take_profit": adjusted_takeProfit,
            "bosPrice": bosPrice,
            "updated_stop_loss": False
        }
    except Exception as e:
        logger.exception("Unexpected error in combo function: %s", e)
        return {"error": "Unexpected error occurred"}


def update_stop_loss(active_positions, Ticker, ohlc):
    """
    Updates the stop loss for active positions if activation criteria are met.

    Parameters:
        active_positions (list): List of active position dictionaries.
        Ticker (str): The ticker symbol for the current position.
        ohlc (dict): The current OHLC (Open, High, Low, Close) data.

    Returns:
        None
    """
    for d in active_positions:
        if d['ticker'] != Ticker:
            continue

        if not d['updated_stop_loss']:
            logger.debug(f"{Ticker}: Checking updated stop loss for position. Details: {d}")

            if d['close_side'] == 'SELL':
                logger.debug(f"{Ticker}: Position is LONG. Activation price: {d['activation_price']}, OHLC high: {ohlc['high']}")

                if ohlc['high'] >= d['activation_price']:
                    logger.info(f"{Ticker}: Activation price reached for LONG position. Setting stop market.")
                    logger.debug(f"{Ticker}: Stop market parameters - Close side: {d['close_side']}, Updated stop loss price: {d['updated_stopLoss_price']}")

                    reaction = set_stop_market(
                        Ticker,
                        d['close_side'],
                        d['position_volume'],
                        d['updated_stopLoss_price']
                    )

                    if isinstance(reaction, Exception):
                        logger.error(f"{Ticker}: Error setting stop market for LONG position - {reaction}")
                        continue

                    d['updated_stop_loss'] = True
                    logger.info(f"{Ticker}: Stop loss updated for LONG position.")

                    logger.debug(f"{Ticker}: Attempting to cancel old stop loss order with ID {d['stop_loss_ID']}")
                    reaction2 = cancel_order(Ticker, d['stop_loss_ID'])
                    if isinstance(reaction2, Exception):
                        logger.error(f"{Ticker}: Error canceling old stop loss order - {reaction2}")
                        continue

                    JSON_result = reaction.json()
                    d['stop_loss_ID'] = JSON_result['orderId']
                    d['stop_loss'] = d['updated_stopLoss_price']
                    logger.info(f"{Ticker}: Old stop loss order canceled. New stop loss set with ID {d['stop_loss_ID']}.")

            else:
                logger.debug(f"{Ticker}: Position is SHORT. Activation price: {d['activation_price']}, OHLC low: {ohlc['low']}")

                if ohlc['low'] <= d['activation_price']:
                    logger.info(f"{Ticker}: Activation price reached for SHORT position. Setting stop market.")
                    logger.debug(f"{Ticker}: Stop market parameters - Close side: {d['close_side']}, Updated stop loss: {d['updated_stopLoss_price']}")

                    reaction = set_stop_market(
                        Ticker,
                        d['close_side'],
                        d['position_volume'],
                        d['updated_stopLoss_price']
                    )

                    if isinstance(reaction, Exception):
                        logger.error(f"{Ticker}: Error setting stop market for SHORT position - {reaction}")
                        continue

                    d['updated_stop_loss'] = True
                    logger.info(f"{Ticker}: Stop loss updated for SHORT position.")

                    logger.debug(f"{Ticker}: Attempting to cancel old stop loss order with ID {d['stop_loss_ID']}")
                    reaction2 = cancel_order(Ticker, d['stop_loss_ID'])
                    if isinstance(reaction2, Exception):
                        logger.error(f"{Ticker}: Error canceling old stop loss order - {reaction2}")
                        continue

                    JSON_result = reaction.json()
                    logger.debug(f"{Ticker}: Reaction JSON result: {JSON_result}")
                    d['stop_loss_ID'] = JSON_result['orderId']
                    d['stop_loss'] = d['updated_stopLoss_price']
                    logger.info(f"{Ticker}: Old stop loss order canceled. New stop loss set with ID {d['stop_loss_ID']}.")

def process_active_positions(active_positions, Ticker):
    """
    Processes active positions for a given ticker. Removes positions that are closed or not found.

    Parameters:
        active_positions (list): List of active position dictionaries.
        Ticker (str): The ticker symbol for the positions.

    Returns:
        None
    """

    positions_to_remove = []  # Track positions to remove after processing

    for d in active_positions[:]:  # Iterate over a copy of the list
        if d['ticker'] != Ticker:
            continue

        logger.info(f"Checking position status for {Ticker} with details: {d}")

        # Check the position's status
        reaction = check_position(Ticker)
        if isinstance(reaction, Exception):
            logger.error(f"Error checking position for {Ticker}: {reaction}")
            continue

        # If the position is not found or closed, cancel associated orders
        if reaction['status'] in ('not_found', 'closed'):
            logger.info(f"Position for {Ticker} is {reaction['status']}. Proceeding to cancel associated orders.")

            stop_loss_id = d.get('stop_loss_ID')
            take_profit_id = d.get('take_profit_ID')

            # Cancel stop-loss order
            if stop_loss_id:
                logger.info(f"Attempting to cancel stop-loss order for {Ticker} with ID {stop_loss_id}")
                sl_response = cancel_order(Ticker, stop_loss_id)
                if isinstance(sl_response, Exception):
                    logger.error(f"Error canceling stop-loss for {Ticker}: {sl_response}")
                else:
                    logger.info(f"Stop-loss order for {Ticker} with ID {stop_loss_id} canceled successfully.")

            # Cancel take-profit order
            if take_profit_id:
                logger.info(f"Attempting to cancel take-profit order for {Ticker} with ID {take_profit_id}")
                tp_response = cancel_order(Ticker, take_profit_id)
                if isinstance(tp_response, Exception):
                    logger.error(f"Error canceling take-profit for {Ticker}: {tp_response}")
                else:
                    logger.info(f"Take-profit order for {Ticker} with ID {take_profit_id} canceled successfully.")

            # Mark this position for removal
            logger.info(f"Marking position for {Ticker} for removal: {d}")
            positions_to_remove.append(d)

    # Remove all marked positions
    for position in positions_to_remove:
        logger.info(f"Removing position for {Ticker}: {position}")
        active_positions.remove(position)
