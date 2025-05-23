from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import sys

# Ajouter le chemin racine pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from properties.config_loader import ConfigLoader

# Charger la configuration
config = ConfigLoader()

# Récupérer les paramètres de configuration
Api_key = config.get('binance.api_key')
Api_secret = config.get('binance.api_secret')

days = config.get_int('market.days', 10)
tenkan_sen_high = config.get_int('ichimoku.tenkan_period', 18)
kijun_sen_high = config.get_int('ichimoku.kijun_period', 52)
senkou_span_high = 2*kijun_sen_high
k = 10**-5

# Conversion de l'intervalle du fichier de configuration en constante Binance
interval_str = config.get('market.interval', '30MINUTE')
if interval_str == '30MINUTE':
    Interval = Client.KLINE_INTERVAL_30MINUTE
elif interval_str == '1HOUR':
    Interval = Client.KLINE_INTERVAL_1HOUR
elif interval_str == '4HOUR':
    Interval = Client.KLINE_INTERVAL_4HOUR
elif interval_str == '1DAY':
    Interval = Client.KLINE_INTERVAL_1DAY
else:
    # Valeur par défaut si l'intervalle n'est pas reconnu
    Interval = Client.KLINE_INTERVAL_30MINUTE
    print(f"Intervalle '{interval_str}' non reconnu, utilisation de 30MINUTE par défaut")

window = 20
Marche = config.get('market.symbol', 'BTCUSDC')
volume_threshold = config.get_float('ichimoku.volume_threshold', 1.5)
rsi_threshold = config.get_int('ichimoku.rsi_threshold', 50)

start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

client = Client(Api_key, Api_secret)

def get_account_balance():
    try:
        account_info = client.get_account()
        balances = account_info['balances']
        money_traded = []
        for balance in balances:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            if free > 0 or locked > 0:
                money_traded.append({asset: {'free': free, 'locked': locked}})
        return money_traded
    except Exception as e:
        return(f"An error occurred: {e}")

def get_btc_price():
    try:
        btc_price = client.get_symbol_ticker(symbol="BTCUSDC")
        return btc_price['price']
    except Exception as e:
        return(f"An error occurred: {e}")

def get_historical_data(symbol, interval, start_str, end_str=None, limit=1000):
    klines = client.get_historical_klines(symbol, interval, start_str, end_str, limit)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms') + timedelta(hours=2)
    df.set_index('timestamp', inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume']]

btc_data = get_historical_data(Marche, Interval, start_date)

def ichimoku_cloud(df):
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    
    high_tenkan = df['high'].rolling(window=tenkan_sen_high).max()
    low_tenkan = df['low'].rolling(window=tenkan_sen_high).min()
    df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2

    high_kijun = df['high'].rolling(window=kijun_sen_high).max()
    low_kijun = df['low'].rolling(window=kijun_sen_high).min()
    df['kijun_sen'] = (high_kijun + low_kijun) / 2

    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(kijun_sen_high)

    high_senkou = df['high'].rolling(window=senkou_span_high).max()
    low_senkou = df['low'].rolling(window=senkou_span_high).min()
    df['senkou_span_b'] = ((high_senkou + low_senkou) / 2).shift(kijun_sen_high)

    df['chikou_span'] = df['close'].shift(-kijun_sen_high)

    return df

btc_data = ichimoku_cloud(btc_data)

def analyze_signals(df, volume_signals, rsi_threshold=50):
    buy_signals = []
    sell_signals = []
    kumo_switches = []

    for i in range(1, len(df)):
        if (df['tenkan_sen'].iloc[i] > df['kijun_sen'].iloc[i] and 
            df['close'].iloc[i] > df['senkou_span_a'].iloc[i] and 
            df['close'].iloc[i] > df['senkou_span_b'].iloc[i] and 
            df.index[i] in volume_signals and 
            df['senkou_span_a'].iloc[i] >= df['senkou_span_b'].iloc[i] and
            df['rsi'].iloc[i] < rsi_threshold):
            buy_signals.append(df.index[i])
        elif (df['tenkan_sen'].iloc[i] < df['kijun_sen'].iloc[i] and 
              df['close'].iloc[i] < df['senkou_span_a'].iloc[i] and 
              df['close'].iloc[i] < df['senkou_span_b'].iloc[i] and 
              df.index[i] in volume_signals and 
              df['senkou_span_a'].iloc[i] < df['senkou_span_b'].iloc[i] and
              df['rsi'].iloc[i] > 100 - rsi_threshold):
            sell_signals.append(df.index[i])
        
        if ((df['senkou_span_a'].iloc[i] > df['senkou_span_b'].iloc[i] and 
             df['senkou_span_a'].iloc[i-1] < df['senkou_span_b'].iloc[i-1]) or 
            (df['senkou_span_a'].iloc[i] < df['senkou_span_b'].iloc[i] and 
             df['senkou_span_a'].iloc[i-1] > df['senkou_span_b'].iloc[i-1])):
            kumo_switches.append(df.index[i])

    return sell_signals, buy_signals, kumo_switches

def place_order(symbol, side, quantity):
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity,
        )
        return order
    except Exception as e:
        return f"An error occurred: {e}"

def get_min_notional(symbol):
    try:
        info = client.get_symbol_info(symbol)
        for filt in info['filters']:
            if filt['filterType'] == 'NOTIONAL':
                return float(filt['minNotional'])
    except Exception as e:
        return f"An error occurred: {e}"


def get_lot_size(symbol):
    try:
        info = client.get_symbol_info(symbol)
        for filt in info['filters']:
            if filt['filterType'] == 'LOT_SIZE':
                return float(filt['minQty']), float(filt['stepSize'])
    except Exception as e:
        return f"An error occurred: {e}"

def adjust_quantity(quantity, min_qty, step_size):
    """
    Ajuste la quantité pour qu'elle respecte les contraintes de Binance.
    """
    if quantity < min_qty:
        return min_qty
    # Arrondir la quantité au multiple le plus proche de step_size
    return float(format(quantity - (quantity % step_size), f'.{len(str(step_size).split(".")[1])}f'))

def calculate_rsi(df, period=14):
    delta = df['close'].astype(float).diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def analyze_volume(df, threshold=1.5):
    volume_signals = []
    df['volume'] = df['volume'].astype(float)
    avg_volume = df['volume'].rolling(window=20).mean()
    for i in range(len(df)):
        if df['volume'].iloc[i] > threshold * avg_volume.iloc[i]:
            volume_signals.append(df.index[i])
    return volume_signals
