import os
import sys
# Ajouter le chemin racine pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mailer import EmailSender
from datetime import datetime
from properties.config_loader import ConfigLoader

def test_email_alerts():
    """
    Script de test pour vérifier que le système d'alerte par email fonctionne correctement.
    """
    print("Test du système d'alerte par email")
    
    # Chemin absolu vers le fichier de configuration pour éviter les problèmes de chemins relatifs
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'properties', 'application.properties'))
    print(f"Utilisation du fichier de configuration: {config_path}")
    
    # Charger la configuration
    config = ConfigLoader(config_path)
    
    # Récupérer les paramètres de configuration
    market_symbol = config.get('market.symbol', 'BTCUSDC')
    recipient_email = config.get('email.recipients', 'anto.urbain@gmail.com')
    
    # Initialiser le mailer avec la configuration
    mailer = EmailSender(config_path)
    
    # Tester l'alerte d'achat
    print(f"\nTest 1: Envoi d'une alerte d'achat à {recipient_email}...")
    result1 = mailer.send_buy_signal_alert(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "67500.00 USDC",
        "0.00150000 BTC",
        market_symbol
    )
    print(f"Résultat: {'Succès' if result1 else 'Échec'}")
    
    # Tester l'alerte de vente avec profit
    print("\nTest 2: Envoi d'une alerte de vente avec profit...")
    result2 = mailer.send_sell_signal_alert(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "68200.00 USDC",
        "0.00150000 BTC",
        market_symbol,
        1.04
    )
    print(f"Résultat: {'Succès' if result2 else 'Échec'}")
    
    # Tester l'alerte de vente avec perte
    print("\nTest 3: Envoi d'une alerte de vente avec perte...")
    result3 = mailer.send_sell_signal_alert(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "67000.00 USDC",
        "0.00150000 BTC",
        market_symbol,
        -0.74
    )
    print(f"Résultat: {'Succès' if result3 else 'Échec'}")
    
    # Tester l'alerte d'erreur
    print("\nTest 4: Envoi d'une alerte d'erreur...")
    result4 = mailer.send_error_alert(
        "Erreur critique: Impossible de se connecter à l'API Binance"
    )
    print(f"Résultat: {'Succès' if result4 else 'Échec'}")
    
    print("\nTests terminés.")

if __name__ == "__main__":
    test_email_alerts()