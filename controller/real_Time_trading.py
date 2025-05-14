from binance.client import Client
from datetime import datetime, timedelta
import time
import pandas as pd
import logging
import os
import sys

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importer notre système d'email et le gestionnaire de configuration
from mailer import EmailSender
from properties.config_loader import ConfigLoader

# Configurer le logger avec des chemins absolus
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'log'))
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'ptndelog.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

# Importer les fonctions nécessaires depuis mainclear.py
from controller.mainclear import get_historical_data, ichimoku_cloud, analyze_signals, calculate_rsi, analyze_volume, place_order, get_account_balance, get_btc_price, get_lot_size, adjust_quantity, get_min_notional

# Charger la configuration avec un chemin absolu
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'properties', 'application.properties'))
config = ConfigLoader(config_path)

# Récupérer les paramètres de configuration
Api_key = config.get('binance.api_key')
Api_secret = config.get('binance.api_secret')

Interval = config.get('market.interval', Client.KLINE_INTERVAL_30MINUTE)
Marche = config.get('market.symbol', 'BTCUSDC')
days = config.get_int('market.days', 10)
fees = config.get_float('market.fees', 0.001)  # 0.1% de frais par défaut

min_usdc = config.get_float('trading.min_usdc', 6)
min_btc = config.get_float('trading.min_btc', 0.00006)

client = Client(Api_key, Api_secret)

# Initialiser le mailer
mailer = EmailSender()

def main_loop():
    latest_bought_price = 0
    latest_buy_signal = None  # datetime of last buy, None if no position
    has_open_position = False  # flag to indicate position open
    latest_sell_signal = datetime.now() - timedelta(days=1)
    
    # Notifications déjà envoyées
    notified_buy_signals = set()
    notified_sell_signals = set()
    
    while True:
        logging.info('System running correctly')
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            btc_data = get_historical_data(Marche, Interval, start_date)
            # Attendre que les données soient à jour pour le palier 30min
            desired_ts = datetime.now().replace(minute=(datetime.now().minute // 30) * 30, second=0, microsecond=0)
            while btc_data.index[-1] != desired_ts:
                time.sleep(60)
                btc_data = get_historical_data(Marche, Interval, start_date)
                logging.info(f"Données pas à jour, dernier point: {btc_data.index[-1]}, cible: {desired_ts}")
            btc_data = ichimoku_cloud(btc_data)
            btc_data = calculate_rsi(btc_data)
            volume_signals = analyze_volume(btc_data)
            buy_signals, sell_signals, kumo_switches = analyze_signals(btc_data, volume_signals)
            logging.info(f"Last sell signal: {sell_signals[-1] if sell_signals else None}, Last buy signal: {buy_signals[-1] if buy_signals else None}")
            quantity = get_account_balance()
            try:
                current_price = float(get_btc_price())
            except Exception as e:
                logging.error(f"Impossible d'obtenir le prix BTC: {e}")
                continue

            # Trouver la quantité de USDC et BTC disponible
            USDC_balance = next((item for item in quantity if 'USDC' in item), None)
            btc_balance = next((item for item in quantity if 'BTC' in item), None)

            logging.info(f"USDC balance: {USDC_balance['USDC']['free']}, BTC balance: {btc_balance['BTC']['free']}")
            
            # Vérifier les nouveaux signaux d'achat pour notifications
            if buy_signals:
                latest_signal = buy_signals[-1]
                # Envoyer un email pour les nouveaux signaux non notifiés récents
                if (latest_signal not in notified_buy_signals and 
                    latest_signal > datetime.now() - timedelta(minutes=40)):
                    try:
                        signal_price = float(btc_data.loc[latest_signal, 'close'])
                        # Calculer la quantité potentielle
                        potential_quantity = (USDC_balance['USDC']['free'] * 0.5 / signal_price 
                                            if USDC_balance['USDC']['free'] > 12 
                                            else USDC_balance['USDC']['free'] / signal_price)
                        
                        min_qty, step_size = get_lot_size(Marche)
                        if min_qty and step_size:
                            potential_quantity = adjust_quantity(potential_quantity, min_qty, step_size)
                            
                        # Envoyer l'alerte
                        mailer.send_buy_signal_alert(
                            str(latest_signal),
                            f"{signal_price:.2f} USDC",
                            f"{potential_quantity:.8f} BTC",
                            Marche
                        )
                        notified_buy_signals.add(latest_signal)
                        logging.info(f"Notification d'achat envoyée pour le signal de {latest_signal}")
                    except Exception as e:
                        logging.error(f"Erreur lors de l'envoi de l'email d'achat: {e}")
            
            # Traitement des signaux d'achat
            if buy_signals and USDC_balance['USDC']['free'] > min_usdc:
                latest_buy_signal = buy_signals[-1]
                has_open_position = True
                if latest_buy_signal > datetime.now() - timedelta(minutes=40):
                    if USDC_balance['USDC']['free'] > min_usdc * 2:
                        quantity_2_buy = USDC_balance['USDC']['free'] * 0.5 / current_price
                    else:
                        quantity_2_buy = USDC_balance['USDC']['free'] * 1 / current_price
                    min_qty, step_size = get_lot_size(Marche)
                    if min_qty and step_size:
                        quantity_2_buy = adjust_quantity(quantity_2_buy, min_qty, step_size)
                        # Vérifier min_notional
                        min_not = get_min_notional(Marche)
                        if quantity_2_buy * current_price < min_not:
                            quantity_2_buy = adjust_quantity(min_not / current_price, min_qty, step_size)
                            logging.info(f"Quantité ajustée pour respecter min_notional {min_not}")
                        logging.info(f"Signal d'achat détecté à {latest_buy_signal}")
                        # Placer un ordre d'achat
                        order = place_order(Marche, Client.SIDE_BUY, quantity_2_buy)
                        logging.info(f"Ordre d'achat placé: {order}")
                        
                else:
                    logging.info("Signal d'achat dépassé")

            # Vérifier les nouveaux signaux de vente pour notifications
            if sell_signals:
                latest_signal = sell_signals[-1]
                # Envoyer un email pour les nouveaux signaux non notifiés récents
                if (latest_signal not in notified_sell_signals and 
                    latest_signal > datetime.now() - timedelta(minutes=40)):
                    try:
                        signal_price = float(btc_data.loc[latest_signal, 'close'])
                        
                        # Calculer la quantité potentielle
                        potential_quantity = (btc_balance['BTC']['free'] * 0.5 
                                            if btc_balance['BTC']['free'] > min_btc * 2 
                                            else btc_balance['BTC']['free'])
                        
                        # Calculer le profit potentiel si on a un prix d'achat
                        profit = 0
                        if latest_buy_signal and latest_buy_signal in btc_data.index:
                            buy_price = float(btc_data.loc[latest_buy_signal, 'close'])
                            profit = ((signal_price - buy_price) / buy_price) * 100
                            
                        # Envoyer l'alerte
                        mailer.send_sell_signal_alert(
                            str(latest_signal),
                            f"{signal_price:.2f} USDC",
                            f"{potential_quantity:.8f} BTC",
                            Marche,
                            profit
                        )
                        notified_sell_signals.add(latest_signal)
                        logging.info(f"Notification de vente envoyée pour le signal de {latest_signal}")
                    except Exception as e:
                        logging.error(f"Erreur lors de l'envoi de l'email de vente: {e}")

            # Traitement des signaux de vente
            if sell_signals and has_open_position and btc_balance['BTC']['free'] > min_btc:
                latest_sell_signal = sell_signals[-1]
                if latest_sell_signal > datetime.now() - timedelta(minutes=40):
                    if btc_balance['BTC']['free'] > min_btc * 2:
                        quantity_2_sell = btc_balance['BTC']['free'] * 0.5
                    else:
                        quantity_2_sell = btc_balance['BTC']['free'] * 1
                    min_qty, step_size = get_lot_size(Marche)
                    if min_qty and step_size:
                        quantity_2_sell = adjust_quantity(quantity_2_sell, min_qty, step_size)
                        logging.info(f"Signal de vente détecté à {latest_sell_signal}")
                        # Vérifier si la vente est rentable après les frais
                        sell_price = current_price * (1 - fees)
                        # récupérer le prix d'achat si signal valide
                        if latest_buy_signal in btc_data.index:
                            latest_bought_price = float(btc_data.loc[latest_buy_signal, 'close'])
                            if sell_price > latest_bought_price:
                                # Placer un ordre de vente
                                order = place_order(Marche, Client.SIDE_SELL, quantity_2_sell)
                                logging.info(f"Ordre de vente placé: {order}")
                                has_open_position = False  # Réinitialiser le flag après la vente
                        else:
                            logging.info("Pas de prix d'achat valide disponible")
                else:
                    logging.info("Signal de vente dépassé")

            # Attendre jusqu'à la prochaine heure ou demi-heure
            now = datetime.now()
            next_run = now + timedelta(minutes=30 - now.minute % 30, seconds=-now.second, microseconds=-now.microsecond)
            sleep_time = (next_run - now).total_seconds()
            time.sleep(sleep_time)
        except Exception as e:
            error_msg = f"Une erreur s'est produite: {e}"
            logging.error(error_msg)
            
            # Envoyer une alerte par email en cas d'erreur
            try:
                mailer.send_error_alert(error_msg)
                logging.info("Alerte d'erreur envoyée par email")
            except Exception as email_err:
                logging.error(f"Impossible d'envoyer l'alerte par email: {email_err}")
                
            time.sleep(60)  # Attendre 60 secondes avant de réessayer

if __name__ == "__main__":    
    # Démarrer la boucle principale
    main_loop()
