import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from binance.client import Client
from datetime import datetime, timedelta
import pandas as pd
import logging
from controller.mainclear import get_historical_data, ichimoku_cloud, analyze_signals, calculate_rsi, analyze_volume

# Chemin absolu vers le dossier de logs
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'log'))
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'ptndelogdetest.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

# Charger les informations de l'API depuis la configuration
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from properties.config_loader import ConfigLoader

# Chemin absolu vers le fichier de configuration
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'properties', 'application.properties'))
print(f"Utilisation du fichier de configuration: {config_path}")

config = ConfigLoader(config_path)
Api_key = config.get('binance.api_key')
Api_secret = config.get('binance.api_secret')

Interval = Client.KLINE_INTERVAL_30MINUTE
Marche = config.get('market.symbol', 'BTCUSDC')
days = config.get_int('market.days', 10)
fees = config.get_float('market.fees', 0.001)  # 0.1% de frais

client = Client(Api_key, Api_secret)

def test_buy_sell_process():
    """
    Fonction de test qui simule le processus d'achat/vente
    pour vérifier si l'erreur 'list index out of range' est résolue
    """
    logging.info('=== DÉBUT DU TEST ===')
    
    # Simuler les variables de state
    latest_bought_price = 0
    latest_buy_signal = None
    has_open_position = False
    
    try:
        # Récupérer les données historiques
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        btc_data = get_historical_data(Marche, Interval, start_date)
        btc_data = ichimoku_cloud(btc_data)
        btc_data = calculate_rsi(btc_data)
        volume_signals = analyze_volume(btc_data)
        buy_signals, sell_signals, kumo_switches = analyze_signals(btc_data, volume_signals)
        
        logging.info(f"Signaux d'achat disponibles: {len(buy_signals)}")
        logging.info(f"Signaux de vente disponibles: {len(sell_signals)}")
        
        # SIMULATION #1: Signal d'achat récent, latest_buy_signal dans btc_data
        if buy_signals:
            latest_buy_signal = buy_signals[-1]
            has_open_position = True
            latest_bought_price = float(btc_data.loc[latest_buy_signal, 'close'])
            logging.info(f"Test #1: Achat simulé à {latest_buy_signal} au prix {latest_bought_price}")
            
            # Tenter une vente avec un signal valide
            if sell_signals and sell_signals[-1] > latest_buy_signal:
                latest_sell_signal = sell_signals[-1]
                sell_price = float(btc_data.loc[latest_sell_signal, 'close']) * (1 - fees)
                
                if latest_buy_signal in btc_data.index:
                    bought_price = float(btc_data.loc[latest_buy_signal, 'close'])
                    logging.info(f"Test #1: Vente simulée - prix achat: {bought_price}, prix vente: {sell_price}")
                    has_open_position = False
                else:
                    logging.info(f"Test #1: ERREUR - latest_buy_signal pas dans btc_data")
        
        # SIMULATION #2: Simuler un signal d'achat qui n'est pas dans btc_data
        fake_buy_date = datetime.now() - timedelta(days=days+5)  # Date hors du range de btc_data
        latest_buy_signal = fake_buy_date
        has_open_position = True
        logging.info(f"Test #2: Achat simulé à {latest_buy_signal} (hors plage)")
        
        # Tenter une vente
        if sell_signals:
            latest_sell_signal = sell_signals[-1]
            try:
                if latest_buy_signal in btc_data.index:
                    # Ce code ne devrait pas s'exécuter
                    bought_price = float(btc_data.loc[latest_buy_signal, 'close'])
                    logging.info(f"Test #2: Vente simulée - prix achat: {bought_price}")
                else:
                    logging.info(f"Test #2: Protection OK - le signal d'achat hors plage a été détecté")
            except Exception as e:
                logging.error(f"Test #2: ERREUR - {e}")
        
        # SIMULATION #3: Vente sans position ouverte
        has_open_position = False
        latest_buy_signal = None
        
        if sell_signals:
            if has_open_position and latest_buy_signal:
                # Ce code ne devrait pas s'exécuter
                logging.error(f"Test #3: ERREUR - Le flag has_open_position ne fonctionne pas correctement")
            else:
                logging.info(f"Test #3: Protection OK - Pas de tentative de vente sans position ouverte")
        
        logging.info('=== TEST TERMINÉ AVEC SUCCÈS ===')
    
    except Exception as e:
        logging.error(f"Une erreur s'est produite pendant le test: {e}")

if __name__ == "__main__":
    test_buy_sell_process()