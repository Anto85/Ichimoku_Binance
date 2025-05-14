#!/bin/bash

# Script de lancement pour le bot de trading Ichimoku avec nohup

# Création des dossiers de logs s'ils n'existent pas
mkdir -p log

# Lancer le bot en arrière-plan avec nohup
echo "Démarrage du bot de trading Ichimoku en arrière-plan..."
nohup python real_Time_trading.py > log/output.log 2>&1 &

# Récupérer le PID du processus
BOT_PID=$!
echo "Bot démarré avec le PID: $BOT_PID"
echo "PID $BOT_PID" > log/bot_pid.txt
echo "Les logs seront disponibles dans log/output.log et log/ptndelog.log"
echo "Pour arrêter le bot: kill $BOT_PID"