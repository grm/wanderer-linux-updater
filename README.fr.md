# Wanderer Linux Updater

Un outil de mise à jour de firmware pour les appareils Wanderer Astro, avec sélection manuelle d'appareils et synchronisation de firmware via GitHub.

## Fonctionnalités

- **Configuration YAML** : Configuration centralisée et flexible
- **Sélection manuelle d'appareils** : Interface utilisateur pour choisir le type d'appareil
- **Détection de ports USB** : Détection automatique des ports série disponibles
- **Synchronisation automatique** : GitHub Actions pour synchroniser les firmwares
- **Hébergement GitHub Pages** : Firmwares hébergés de manière fiable
- **Support multi-appareils** : Tous les appareils Wanderer supportés

## Installation

1. Clonez le repository :
```bash
git clone https://github.com/your-username/wanderer-linux-updater.git
cd wanderer-linux-updater
```

2. Installez avrdude (requis pour les mises à jour de firmware) :

**Sur Ubuntu/Debian :**
```bash
sudo apt-get install avrdude
```

**Sur Arch Linux :**
```bash
sudo pacman -S avrdude
```

3. Installez les dépendances :
```bash
pipenv install
```

## Utilisation

### Mise à jour interactive (recommandé)

```bash
# Lancer l'outil de mise à jour interactif
pipenv run python updater.py
```

L'outil vous guidera à travers les étapes suivantes :
1. **Sélection du type d'appareil** : Choisissez parmi les appareils configurés
2. **Sélection du port série** : Choisissez parmi les ports USB disponibles
3. **Test de connexion** : Vérification optionnelle de la présence de l'appareil
4. **Sélection du firmware** : Choisissez la version de firmware à installer
5. **Mise à jour** : Exécution de la mise à jour

### Options supplémentaires

```bash
# Utiliser un fichier de configuration personnalisé
pipenv run python updater.py --config my-config.yml

# Mode dry-run (affiche la commande sans l'exécuter)
pipenv run python updater.py --dry-run

# Mode debug
pipenv run python updater.py --debug
```

## Scripts utilitaires

### Lister les appareils configurés

```bash
# Afficher tous les appareils configurés avec leurs paramètres
pipenv run python list_devices.py
```

### Tester la détection de ports USB

```bash
# Tester la détection des ports série disponibles
pipenv run python test_ports.py
```

### Tester la détection automatique (optionnel)

```bash
# Tester la détection automatique d'appareils via handshake
pipenv run python test_detection.py
```

## Synchronisation automatique

Le workflow GitHub Actions synchronise automatiquement les firmwares :

1. **Activation** : Le workflow s'exécute toutes les 6 heures
2. **Téléchargement** : Récupère la liste des firmwares depuis l'URL configurée
3. **Hébergement** : Les firmwares sont hébergés sur GitHub Pages
4. **Index** : Un fichier JSON index est généré avec les métadonnées

### Configuration GitHub Pages

1. Allez dans Settings > Pages
2. Source : "Deploy from a branch"
3. Branch : `main` (ou votre branche principale)
4. Folder : `/ (root)`

## Structure des fichiers

```
wanderer-linux-updater/
├── .github/workflows/sync-firmware.yml  # Workflow GitHub Actions
├── scripts/sync_firmware.py             # Script de synchronisation
├── config.yml                           # Configuration principale
├── config_manager.py                    # Gestionnaire de configuration
├── device_detector.py                   # Détection d'appareils (pour tests)
├── updater.py                          # Script principal interactif
├── test_detection.py                   # Test de détection automatique
├── test_ports.py                       # Test de détection de ports
├── list_devices.py                     # Liste des appareils configurés
├── firmware/                           # Firmwares (auto-généré)
├── firmware_index.json                 # Index des firmwares (auto-généré)
└── README.md
```

## Appareils supportés

- WandererBoxPlusV3 
- WandererBoxProV3 (Tested ✔️)
- WandererCoverV3
- WandererCover V4/V4Pro (Tested ✔️)
- WandererDewTerminator
- WandererEclipse
- WandererRotatorLiteV1/V2
- WandererRotatorMini (Tested ✔️)
- WandererRotatorProV1/V2
- WandererETA54

## Configuration avancée

### Ajouter un nouvel appareil

Ajoutez une nouvelle entrée dans la section `devices` de `config.yml` :

```yaml
devices:
  MonNouvelAppareil:
    avr_device: "m328p"
    programmer: "arduino"
    baud_rate: 115200
    handshake_baud_rate: 19200
    handshake_command: "MaCommande"     # Optionnel : commande à envoyer
    handshake_response: "MaReponse"     # Requis : réponse attendue
```

### Configuration du handshake

Chaque appareil peut avoir un comportement de handshake spécifique :

- **`handshake_command`** : Commande optionnelle à envoyer à l'appareil
- **`handshake_response`** : Réponse attendue requise de l'appareil
- **`handshake_baud_rate`** : Vitesse de baud optionnelle pour le handshake (utilise `baud_rate` par défaut)

### Configuration de détection d'appareils

```yaml
device_detection:
  handshake_timeout: 5        # Timeout pour les opérations de handshake (secondes)
  port_detection_timeout: 3   # Timeout pour la détection de ports (secondes)
```

## Dépannage

### Aucun port détecté

1. Vérifiez que l'appareil est connecté via USB
2. Testez avec `pipenv run python test_ports.py`
3. Vérifiez les permissions sur `/dev/tty*` (Linux)
4. Installez les drivers USB appropriés

### Erreurs de configuration

```bash
# Valider la configuration
pipenv run python -c "from config_manager import ConfigManager; ConfigManager().validate_config()"
```

### Problèmes de mise à jour

1. Vérifiez que l'appareil est en mode bootloader
2. Assurez-vous que `avrdude` est installé
3. Vérifiez les permissions sur le port série
4. Testez avec le mode `--dry-run` d'abord

### Erreurs de téléchargement de firmware

1. Vérifiez la connectivité internet
2. Vérifiez l'URL du firmware dans la configuration
3. Vérifiez que le repository GitHub est correctement configuré

## Contribution

1. Fork le repository
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Poussez vers la branche
5. Créez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails. 