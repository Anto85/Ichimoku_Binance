import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from binance.client import Client
from datetime import datetime, timedelta
import pandas as pd
from MainclearTEST import get_historical_data, ichimoku_cloud, get_account_balance, get_btc_price, analyze_signals, calculate_rsi, analyze_volume

Api_key = "*****"
Api_secret ="*****"

Interval = Client.KLINE_INTERVAL_30MINUTE
Marche = "BTCUSDC"
days = 10

client = Client(Api_key, Api_secret)

# datetime(2015,2,10)

def plot_ichimoku_cloud():
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    btc_data = get_historical_data(Marche, Interval, start_date)
    btc_data = ichimoku_cloud(btc_data)
    btc_data = calculate_rsi(btc_data)
    volume_signals = analyze_volume(btc_data)
    sell_signals,buy_signals, kumo_switches, last_analysed_signal = analyze_signals(btc_data, volume_signals)

    print(f"Last analysed signal: {last_analysed_signal}")
    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(btc_data.index, btc_data['close'], label='Close Price', color='black')
    ax.plot(btc_data.index, btc_data['tenkan_sen'], label='Tenkan-sen', color='red')
    ax.plot(btc_data.index, btc_data['kijun_sen'], label='Kijun-sen', color='blue')
    ax.plot(btc_data.index, btc_data['senkou_span_a'], label='Senkou Span A', color='green')
    ax.plot(btc_data.index, btc_data['senkou_span_b'], label='Senkou Span B', color='brown')
    ax.fill_between(btc_data.index, btc_data['senkou_span_a'], btc_data['senkou_span_b'], where=btc_data['senkou_span_a'] >= btc_data['senkou_span_b'], facecolor='green', alpha=0.5)
    ax.fill_between(btc_data.index, btc_data['senkou_span_a'], btc_data['senkou_span_b'], where=btc_data['senkou_span_a'] < btc_data['senkou_span_b'], facecolor='red', alpha=0.5)
    ax.plot(btc_data.index, btc_data['chikou_span'], label='Chikou Span', color='purple')

    # Ajouter les signaux d'achat et de vente
    for signal in buy_signals:
        ax.annotate('Buy', xy=(signal, btc_data.loc[signal, 'close']), xytext=(signal, btc_data.loc[signal, 'close'] + 500),
                    arrowprops=dict(facecolor='green', shrink=0.05), fontsize=12, color='green')
    for signal in sell_signals:
        ax.annotate('Sell', xy=(signal, btc_data.loc[signal, 'close']), xytext=(signal, btc_data.loc[signal, 'close'] - 500),
                    arrowprops=dict(facecolor='red', shrink=0.05), fontsize=12, color='red')

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    plt.title('Ichimoku Cloud')
    plt.legend()
    plt.grid(True)

    # Ajouter les soldes
    balances = get_account_balance()
    usdc_balance = next((item for item in balances if 'USDC' in item), None)
    btc_balance = next((item for item in balances if 'BTC' in item), None)
    plt.figtext(0.15, 0.85, f"USDC Balance: {usdc_balance['USDC']['free']}", fontsize=12, color='blue')
    plt.figtext(0.15, 0.80, f"BTC Balance: {btc_balance['BTC']['free']}", fontsize=12, color='blue')

    # Enregistrer le graphique
    plt.savefig('ichimoku_cloud.png')
    plt.show()

if __name__ == "__main__":
    plot_ichimoku_cloud()
