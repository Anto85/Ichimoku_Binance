import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
import sys
# Ajouter le chemin racine pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from properties.config_loader import ConfigLoader

# Configuration du logger pour le mailer
logging.basicConfig(filename='log/mailer.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

class EmailSender:
    def __init__(self, config_file='properties/application.properties'):
        """
        Initialise le service d'envoi d'emails
        
        Args:
            config_file (str): Chemin vers le fichier de configuration
        """
        self.config = ConfigLoader(config_file)
        
        # Charger les configurations
        self.smtp_server = self.config.get('email.smtp_server', 'smtp.gmail.com')
        self.port = self.config.get_int('email.port', 587)
        
        # Demander les informations si elles ne sont pas renseignées
        self.sender_email = self.config.get_or_ask('email.user', 
                                                  "Entrez votre adresse email: ")
        self.password = self.config.get_or_ask('email.password', 
                                              "Entrez votre mot de passe d'application: ", 
                                              is_secret=True)
        recipients = self.config.get_or_ask('email.recipients', 
                                         "Entrez les adresses email des destinataires (séparées par des virgules): ")
        self.recipients = [r.strip() for r in recipients.split(',')]
        
    def send_email(self, subject, body, recipients=None):
        """
        Envoie un email
        
        Args:
            subject (str): Sujet de l'email
            body (str): Corps du message
            recipients (list): Liste des destinataires (optionnel)
            
        Returns:
            bool: True si l'envoi a réussi, False sinon
        """
        if recipients is None:
            recipients = self.recipients
            
        # Création du message
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        
        # Ajout du corps du message
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            # Connexion au serveur SMTP
            server = smtplib.SMTP(self.smtp_server, self.port)
            server.starttls()  # Sécuriser la connexion
            server.login(self.sender_email, self.password)
            
            # Envoi du message
            server.send_message(msg)
            server.quit()
            logging.info(f"Email envoyé avec succès à {recipients}")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi de l'email: {e}")
            return False
    
    def send_buy_signal_alert(self, signal_time, price, quantity, market):
        """
        Envoie une alerte pour un signal d'achat
        
        Args:
            signal_time: Horodatage du signal
            price: Prix au moment du signal
            quantity: Quantité achetée
            market: Marché concerné (ex: BTCUSDC)
        """
        subject = f"🟢 Signal d'ACHAT détecté sur {market}"
        body = f"""
Un signal d'achat a été détecté sur {market} !

Détails:
- Date/heure: {signal_time}
- Prix: {price}
- Quantité: {quantity}

Ce message a été envoyé automatiquement par votre bot de trading Ichimoku.
        """
        return self.send_email(subject, body)
    
    def send_sell_signal_alert(self, signal_time, price, quantity, market, profit):
        """
        Envoie une alerte pour un signal de vente
        
        Args:
            signal_time: Horodatage du signal
            price: Prix au moment du signal
            quantity: Quantité vendue
            market: Marché concerné (ex: BTCUSDC)
            profit: Profit réalisé (en pourcentage)
        """
        profit_emoji = "🟢" if profit > 0 else "🔴"
        subject = f"{profit_emoji} Signal de VENTE détecté sur {market}"
        body = f"""
Un signal de vente a été détecté sur {market} !

Détails:
- Date/heure: {signal_time}
- Prix: {price}
- Quantité: {quantity}
- Profit: {profit:.2f}%

Ce message a été envoyé automatiquement par votre bot de trading Ichimoku.
        """
        return self.send_email(subject, body)
    
    def send_error_alert(self, error_message):
        """
        Envoie une alerte en cas d'erreur critique
        
        Args:
            error_message: Description de l'erreur
        """
        subject = "⚠️ ERREUR critique sur votre bot de trading"
        body = f"""
Une erreur critique s'est produite sur votre bot de trading Ichimoku:

{error_message}

Veuillez vérifier les logs et corriger le problème dès que possible.
        """
        return self.send_email(subject, body)

# Exemple d'utilisation
if __name__ == "__main__":
    # Pour tester l'envoi d'email
    mailer = EmailSender()
    mailer.send_buy_signal_alert("2025-05-14 17:45:00", 
                                 "68000 USDC", 
                                 "0.05 BTC", 
                                 "BTCUSDC")