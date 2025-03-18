from binance.client import Client
from datetime import datetime, timedelta
import time
import pandas as pd
import logging

# Configurer le logger
logging.basicConfig(filename='ptndelogdetest.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Importer les fonctions nécessaires depuis main.py
from mainclear import get_historical_data, ichimoku_cloud, analyze_signals, calculate_rsi, analyze_volume, place_order, get_account_balance, get_btc_price, get_lot_size, adjust_quantity, get_min_notional

Api_key = "*****"
Api_secret = "*****"

Interval = Client.KLINE_INTERVAL_1MINUTE
Marche = "BTCUSDC"
days = 1
fees = 0.001  # 0.1% de frais

client = Client(Api_key, Api_secret)

def main_loop():
    latest_bought_price = 0
    latest_buy_signal = datetime.now() - timedelta(days=1)
    latest_sell_signal = datetime.now() - timedelta(days=1)
    
    while True:
        logging.info('System running correctly')
        try:
            start_date = (datetime.now() - timedelta(hours=10)).strftime('%Y-%m-%d')
            btc_data = get_historical_data(Marche, Interval, start_date)
            btc_data = ichimoku_cloud(btc_data)
            btc_data = calculate_rsi(btc_data)
            volume_signals = analyze_volume(btc_data)
            sell_signals,buy_signals, kumo_switches, latest_analysed_signal = analyze_signals(btc_data, volume_signals)


            logging.info(f"Last analysed signal: {latest_analysed_signal}")
            
            quantity = get_account_balance()
            current_price = float(get_btc_price())

            # Trouver la quantité de USDC et BTC disponible
            USDC_balance = next((item for item in quantity if 'USDC' in item), None)
            btc_balance = next((item for item in quantity if 'BTC' in item), None)

            logging.info(f"USDC balance: {USDC_balance['USDC']['free']}, BTC balance: {btc_balance['BTC']['free']}")
            
            if buy_signals and USDC_balance['USDC']['free'] > 6 :
                latest_buy_signal = buy_signals[-1]
                if latest_sell_signal > datetime.now() - timedelta(minutes=30):
                    if USDC_balance['USDC']['free'] > 12:
                        quantity_2_buy = USDC_balance['USDC']['free'] * 0.5 / current_price
                    else:
                        quantity_2_buy = USDC_balance['USDC']['free'] * 1 / current_price
                    min_qty, step_size = get_lot_size(Marche)
                    if min_qty and step_size:
                        quantity_2_buy = adjust_quantity(quantity_2_buy, min_qty, step_size)
                        logging.info(f"Signal d'achat détecté à {latest_buy_signal}")
                        # Placer un ordre d'achat
                        latest_bought_price = btc_data.loc[latest_buy_signal, 'close']
                        # order = place_order(Marche, Client.SIDE_BUY, quantity_2_buy)
                        # logging.info(f"Ordre d'achat placé: {order}")
                        
                else:
                    logging.info("Signal d'achat dépassé")

            if sell_signals and btc_balance['BTC']['free'] > 0.00006:
                latest_sell_signal = sell_signals[-1]
                if latest_sell_signal > datetime.now() - timedelta(minutes=30):
                    if btc_balance['BTC']['free'] > 0.00012:
                        quantity_2_sell = btc_balance['BTC']['free'] * 0.5
                    else:
                        quantity_2_sell = btc_balance['BTC']['free'] * 1
                    min_qty, step_size = get_lot_size(Marche)
                    if min_qty and step_size:
                        quantity_2_sell = adjust_quantity(quantity_2_sell, min_qty, step_size)
                        logging.info(f"Signal de vente détecté à {latest_sell_signal}")
                        # Vérifier si la vente est rentable après les frais
                        sell_price = current_price * (1 - fees)
                                                    
                        # if sell_price > latest_bought_price:
                            # Placer un ordre de vente
                            # order = place_order(Marche, Client.SIDE_SELL, quantity_2_sell)
                            # logging.info(f"Ordre de vente placé: {order}")
                else:
                    logging.info("Signal de vente dépassé")

            # Attendre jusqu'à la prochaine heure ou demi-heure
            now = datetime.now()
            # next_run = now + timedelta(minutes=30 - now.minute % 30, seconds=-now.second, microseconds=-now.microsecond)
            next_run = now + timedelta(minutes=1, seconds=-now.second, microseconds=-now.microsecond)
            sleep_time = (next_run - now).total_seconds()  # Attendre 5 secondes supplémentaires
            time.sleep(sleep_time)
        except Exception as e:
            logging.error(f"Une erreur s'est produite: {e}")
            time.sleep(60)  # Attendre 60 secondes avant de réessayer

if __name__ == "__main__":
    main_loop()
