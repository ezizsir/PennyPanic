from datetime import datetime
from smartmoneyconcepts import smc
from ExcelOutput import ExcelOutput
import pandas as pd
import storage
import BacktestFunctions
import talib
import numpy
import time

'''
HAS LOGIC TO KEEP TRACK OF BOTTOM BEFORE TP
'''


'''
ENTERS POSITION AFTER CONFIRMED BOS
IF CONDITIONS ABOUT EMA55 AND CHOCK ALSO ALLIGN
'''

# SL/TP % percentage values
STOPLOSS = 2
TAKEPROFIT = 5

STOPLOSS = STOPLOSS/100
TAKEPROFIT = TAKEPROFIT/100 

def HistoryCheck(ohlc_df, Ticker, KlineInterval, USD_per_position):

    if 'ema55' not in ohlc_df.columns:
        ohlc_df["ema55"] = talib.EMA(ohlc_df["close"], timeperiod=55)


    swings_df = smc.swing_highs_lows(ohlc_df, swing_length = 3)

    BoS = smc.bos_choch(ohlc_df, swings_df, close_break = True)
    
    dimension = ohlc_df.shape

    # Detect if the most recent Candle has BoS or ChoCh
    # Iterates through each row to see if any Bos Or ChoCh occurs in the last candle

    all_crossovers = BacktestFunctions.crossover_list(ohlc_df)

    for index, row in BoS.iterrows():

        if (not pd.isna(row.to_dict()['BrokenIndex'])):
            brokenIndex = int(row.to_dict()['BrokenIndex'])

            # Drop will be set true if candles ever dropped below ema21 for longs 
            #                                       peaked above ema21 for short
            drop = False

            # inbetween will be set true if the ema8 is above ema21 and closing price falls between them
            #                         or if the ema8 is below ema21 and closing proce falls between them
            inbetween = False

            # inorder will be set true if the ema's are in order in ascending or descending order
            inorder = True

            extreme_since_crossover = False

            # From the candle of the starting point (index) checks untill the final candle (40) 
            for i in range(index, brokenIndex):
                
                # Check if the pattern is Positive or Negative
                if row.to_dict()['BOS'] == 1:
                    
                    if ohlc_df.iloc[i]['ema55'] > ohlc_df.iloc[i]['ema21']:
                        inorder = False
                        break
                
                    #check if the closing price ever drops below the ema21
                    if ohlc_df.iloc[i]['close'] < ohlc_df.iloc[i]['ema21']:
                        drop = True
                        break
                    # Check if the ema8 is above ema21 and closing proce falls between them
                    if ohlc_df.iloc[i]['ema8'] > ohlc_df.iloc[i]['close'] and ohlc_df.iloc[i]['close'] > ohlc_df.iloc[i]['ema21']:
                        inbetween = True
                        
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

            if drop == False and inbetween == True and inorder == True:

                last_crossover = BacktestFunctions.last_crossover(all_crossovers, brokenIndex)

                if row.to_dict()['BOS'] == 1:
                    BosValue = ohlc_df.iloc[index]['high']
                    previous_high = ohlc_df['high'].iloc[last_crossover:brokenIndex].max()
                    
                    if BosValue == previous_high:
                        extreme_since_crossover = True
                
                else:
                    BosValue = ohlc_df.iloc[index]['low']
                    previous_low = ohlc_df['low'].iloc[last_crossover:brokenIndex].min()
                    
                    if BosValue == previous_low:
                        extreme_since_crossover = True

                if extreme_since_crossover == False:
                    continue
                
                boughtPrice = ohlc_df.iloc[brokenIndex]['close']

                # Get the max/min value inside the break of structure AKA stopLoss Value
                if row.to_dict()['BOS'] == 1:
                    position = "LONG"
                    extreme = ohlc_df['low'].iloc[index:brokenIndex + 1].min()

                    # Calculating leverage
                    leverage = 0.02 / (1 - (extreme / BosValue))
                    stopLoss = BosValue * (1 - STOPLOSS / leverage)

                    takeProfit = (1 + TAKEPROFIT / leverage) * BosValue

                    win = (takeProfit / boughtPrice - 1) * leverage
                    loss = (stopLoss / boughtPrice - 1) * leverage
                    
                else:
                    position = "SHORT"
                    extreme = ohlc_df['high'].iloc[index:brokenIndex + 1].max()

                    # Calculating leverage by deviding extreme from the BoS value
                    leverage = 0.02 / ((extreme / BosValue) - 1)
                    stopLoss = BosValue * (1 + STOPLOSS / leverage)

                    takeProfit = (1 - TAKEPROFIT / leverage) * BosValue

                    win = (1 - takeProfit / boughtPrice) * leverage
                    loss = (1 - stopLoss / boughtPrice) * leverage

                leveraged_USDx10 = USD_per_position * leverage * 10

                if (leverage < 1 or leverage > 5):
                    continue

                if ohlc_df['volume'].iloc[index:brokenIndex].min() < leveraged_USDx10:
                    continue

                winloss = 0

                # See if prediction was successfull 
                for i in range(brokenIndex, dimension[0]):
                    if position == 'LONG':

                        if ohlc_df.iloc[i]['high'] > takeProfit:
                            winloss = win

                            break

                        elif ohlc_df.iloc[i]['low'] < stopLoss:
                            winloss = loss

                            break
                        if i == dimension[0] - 1:
                            
                            break      
                    else:
                        if ohlc_df.iloc[i]['low'] < takeProfit:
                            winloss = win

                            break
                        elif ohlc_df.iloc[i]['high'] > stopLoss:
                            winloss = loss
                            break
                        if i == dimension[0] - 1:

                            break

                # conservative outputData
                outputData = [
                    ohlc_df.iloc[brokenIndex]["time"],       # Time at the brokenIndex
                    Ticker,                                  # Ticker symbol
                    round(winloss, 4),                        # Win or loss status
                ]

                ExcelOutput(outputData)

        else:
            continue

def isConfirmedBos(bos, position, close) -> bool: 
    if position == 'LONG':
        if close > bos:
            return True
        else:
            return False
        
    else:
        if close < bos:
            return True
        else:
            return False
