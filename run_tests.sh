#!/bin/bash

# Script pour exécuter tous les tests avant de lancer l'application
echo "=== EXÉCUTION DES TESTS ==="
echo

# Création du dossier de logs s'il n'existe pas
mkdir -p log

# Test des alertes par email
echo "1. Test des alertes par email..."
python test/test_email_alerts.py
if [ $? -eq 0 ]; then
    echo "✅ Test des alertes par email réussi"
else
    echo "❌ Test des alertes par email échoué"
    exit 1
fi
echo

# Test de la correction des erreurs
echo "2. Test de la correction des erreurs 'list index out of range'..."
python test/test_error_fix.py
if [ $? -eq 0 ]; then
    echo "✅ Test de la correction des erreurs réussi"
    grep -q "=== TEST TERMINÉ AVEC SUCCÈS ===" log/ptndelogdetest.log
    if [ $? -eq 0 ]; then
        echo "✅ Vérification du log de test réussie"
    else
        echo "❌ Vérification du log de test échouée"
        exit 1
    fi
else
    echo "❌ Test de la correction des erreurs échoué"
    exit 1
fi
echo

# Test de la configuration
echo "3. Vérification de la configuration..."
python -c "from properties.config_loader import ConfigLoader; config = ConfigLoader(); print('✅ Configuration chargée avec succès: ' + config.get('market.symbol'))"
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors du chargement de la configuration"
    exit 1
fi
echo

echo "=== TOUS LES TESTS ONT RÉUSSI ==="
echo
echo "Vous pouvez maintenant lancer l'application avec ./start_bot.sh"
echo

# Demander à l'utilisateur s'il souhaite lancer l'application
read -p "Voulez-vous lancer l'application maintenant? (o/n): " reponse
if [[ "$reponse" == "o" || "$reponse" == "O" || "$reponse" == "oui" ]]; then
    echo "Lancement de l'application..."
    ./start_bot.sh
fi