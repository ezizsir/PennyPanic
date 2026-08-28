from datetime import datetime
from smartmoneyconcepts import smc
import BacktestFunctions
import pandas as pd
import talib
import numpy
from logger_config import logger

# SL/TP % percentage values
STOPLOSS = 5
TAKEPROFIT = 2

STOPLOSS = STOPLOSS/100
TAKEPROFIT = TAKEPROFIT/100 

# BoS && ema21/8 = ChekcJackpot
def CheckJackpot(candlesticks, KlineInterval, Ticker):

    USD_per_position = 10

    # Initialize lists to collect OHLC data and later convert them to NumPy arrays
    DataFrameList = {
        "time": [],
        "open": [],
        "high": [],
        "low": [],
        "close": [],
        "volume": [],
        "ema55": [],        
        "ema21": [],
        "ema8": []
    }

    for candlestick in candlesticks:
        open_time = datetime.fromtimestamp(candlestick[0] / 1000)  # Convert milliseconds to readable time
        open_price = float(candlestick[1])
        high_price = float(candlestick[2])
        low_price = float(candlestick[3])
        close_price = float(candlestick[4])
        volume = float(candlestick[7])

        # Append the data to the lists
        DataFrameList['time'].append(open_time)
        DataFrameList['open'].append(open_price)
        DataFrameList['high'].append(high_price)
        DataFrameList['low'].append(low_price)
        DataFrameList['close'].append(close_price)
        DataFrameList['volume'].append(volume)

    # Convert the lists to numpy arrays
    DataFrameList['open'] = numpy.array(DataFrameList['open'])
    DataFrameList['high'] = numpy.array(DataFrameList['high'])
    DataFrameList['low'] = numpy.array(DataFrameList['low'])
    DataFrameList['close'] = numpy.array(DataFrameList['close'])
    DataFrameList['volume'] = numpy.array(DataFrameList['volume'])

    # Calculate EMA and append to the lists
    DataFrameList['ema8'] = talib.EMA(DataFrameList['close'], 8)
    DataFrameList['ema21'] = talib.EMA(DataFrameList['close'], 21)
    DataFrameList["ema55"] = talib.EMA(DataFrameList["close"], 55)


    # Convert into a pandas data frame for ease
    ohlc_df = pd.DataFrame(DataFrameList)

    dimension = ohlc_df.shape
    lastRow = dimension[0]          # not actually last row, its the number of total rows in the dataframe

    swings_df = smc.swing_highs_lows(ohlc_df, swing_length = 3)

    BoS = smc.bos_choch(ohlc_df, swings_df, close_break = True)
    

    # Detect if the most recent Candle has BoS or ChoCh
    # Iterates through each row to see if any Bos Or ChoCh occurs in the last candle
    for index, row in BoS.iterrows():
        # print(f"Index: {index}, Row: {row.to_dict()}, Time:{DataFrameList['time'][index]}")

        if row.to_dict()['BrokenIndex'] == lastRow - 1:
            # 
            print(f"BoS for {Ticker} checking other conditions")

            # Drop will be set true if candles ever dropped below ema21 for longs 
            #                                       peaked above ema21 for short
            drop = False

            # inbetween will be set true if the ema8 is above ema21 and closing price falls between them
            #                         or if the ema8 is below ema21 and closing proce falls between them
            inbetween = False

            # proper order of ema 8 and 21 means switchEMA = FALSE
            switchEma = False

            # inorder will be set true if the ema's are in order in ascending or descending order
            inorder = True

            extreme_since_crossover = False

            # From the candle of the starting point (index) checks untill the final candle (lastRow) 
            for i in range(index, lastRow):
                # Check if the pattern is Positive or Negative
                if row.to_dict()['BOS'] == 1:

                    if ohlc_df.iloc[i]['ema55'] > ohlc_df.iloc[i]['ema21']:
                        inorder = False
                        break

                    # Check if the closing price ever drops below the ema21
                    if ohlc_df.iloc[i]['close'] < ohlc_df.iloc[i]['ema21']:
                        drop = True
                        break

                    # Check if the ema8 is above ema21 and closing price falls between them
                    if ohlc_df.iloc[i]['ema8'] > ohlc_df.iloc[i]['close'] and ohlc_df.iloc[i]['close'] > ohlc_df.iloc[i]['ema21']:
                        inbetween = True
                    
                    # Check if the ema8 ever drops below ema21
                    if ohlc_df.iloc[i]['ema8'] < ohlc_df.iloc[i]['ema21']:
                        switchEma = True
                        break
                        
                elif row.to_dict()['BOS'] == -1:

                    if ohlc_df.iloc[i]['ema55'] < ohlc_df.iloc[i]['ema21']:
                        inorder = False
                        break 

                    #check if the closing price ever rises above the ema21                    
                    if ohlc_df.iloc[i]['close'] > ohlc_df.iloc[i]['ema21']:
                        drop = True
                        break

                    if ohlc_df.iloc[i]['ema8'] < ohlc_df.iloc[i]['close'] and ohlc_df.iloc[i]['close'] < ohlc_df.iloc[i]['ema21']:
                        inbetween = True

                    # Check if the ema8 ever rises above ema21
                    if ohlc_df.iloc[i]['ema8'] > ohlc_df.iloc[i]['ema21']:
                        switchEma = True
                        break

            if switchEma:
                continue
            
            if drop == False and inbetween == True and inorder == True:

                last_crossover = BacktestFunctions.crossover_check(ohlc_df, lastRow)
                
                if row.to_dict()['BOS'] == 1:
                    BosValue = ohlc_df.iloc[index]['high']
                    previous_high = ohlc_df['high'].iloc[last_crossover : lastRow - 1].max()
                    
                    if BosValue == previous_high:
                        extreme_since_crossover = True
                
                else:
                    BosValue = ohlc_df.iloc[index]['low']
                    previous_low = ohlc_df['low'].iloc[last_crossover : lastRow - 1].min()
                    
                    if BosValue == previous_low:
                        extreme_since_crossover = True

                if extreme_since_crossover == False:
                    logger.info(f"Extreme condition not met since last crossover for {Ticker}")
                    continue

                # Get the max/min value inside the break of structure AKA stopLoss Value
                if row.to_dict()['BOS'] == 1:
                    position = "LONG"
                    extreme = ohlc_df['low'].iloc[index : lastRow].min()

                    # BosValue is the value that cause the break of structure
                    BosValue = ohlc_df.iloc[index]['high']

                    # Calculating leverage
                    leverage = 0.02 / (1 - (extreme / BosValue))
                    stopLoss = BosValue * (1 - STOPLOSS / leverage)
                    takeProfit = (1 + TAKEPROFIT / leverage) * BosValue                    
                    
                else:
                    position = "SHORT"
                    extreme = ohlc_df['high'].iloc[index : lastRow].max()

                    BosValue = ohlc_df.iloc[index]['low']

                    # Calculating leverage by deviding extreme from the BoS value
                    leverage = 0.02 / ((extreme / BosValue) - 1)
                    stopLoss = BosValue * (1 + STOPLOSS / leverage)
                    takeProfit = (1 - TAKEPROFIT / leverage) * BosValue                    

                leveraged_USDx10 = USD_per_position * leverage * 10

                if (leverage < 1 or leverage > 5):
                    logger.info(f"Leverage of {leverage}x prevented the position entry")
                    continue

                if ohlc_df['volume'].iloc[index:lastRow].min() < leveraged_USDx10:
                    logger.info(f"Volume of {ohlc_df['volume'].iloc[index:lastRow].min()}$ prevented the position entry")
                    continue
                
                currentPrice = ohlc_df.iloc[lastRow - 1]['close']

                
                message = "{} min interval: {} {}  at x{:.2f} leverage\nStop loss: {}\nTake profit: {}".format(KlineInterval, position, Ticker, leverage, stopLoss, takeProfit)
                print(f"\033[1;37;40m{message}\n\033[0;37;40m")
                
                message = [Ticker, position, currentPrice, leverage, stopLoss, takeProfit, BosValue]
                print(message)
                return message
            else:
                # Debugging to see what prevented jackpot. Drop condition and/or inbetween condition
                print(f"""Drop/rise ema21:               \033[96m {drop}\033[00m,
closed between ema8 and ema21: \033[96m {inbetween}\033[00m\n""")
                
            return
