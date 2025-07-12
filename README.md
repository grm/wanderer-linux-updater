# Wanderer Linux Updater

Un outil de mise à jour de firmware pour les appareils Wanderer Astro, avec détection automatique d'appareils et synchronisation de firmware via GitHub.

## Fonctionnalités

- **Configuration YAML** : Configuration centralisée et flexible
- **Détection automatique d'appareils** : Handshake pour identifier les appareils connectés
- **Synchronisation automatique** : GitHub Actions pour synchroniser les firmwares
- **Hébergement GitHub Pages** : Firmwares hébergés de manière fiable
- **Support multi-appareils** : Tous les appareils Wanderer supportés

## Installation

1. Clonez le repository :
```bash
git clone https://github.com/your-username/wanderer-linux-updater.git
cd wanderer-linux-updater
```

2. Installez les dépendances :
```bash
pipenv install
```

3. Configurez votre fichier `config.yml` (voir section Configuration)

## Configuration

Le fichier `config.yml` contient toute la configuration :

```yaml
# Configuration des firmwares
firmware:
  source_url: "https://od.lk/d/MzNfMzIzNTQ2OTNf/FirmwareDownloadList.txt"
  github_repo: "your-username/wanderer-linux-updater"
  sync_interval_hours: 6

# Configuration de détection d'appareils
device_detection:
  handshake_timeout: 5
  baud_rates: [115200, 57600, 9600]
  handshake_commands: ["VERSION", "DEVICE", "ID"]

# Définitions des appareils
devices:
  WandererBoxPlusV3:
    avr_device: "m168p"
    programmer: "arduino"
    baud_rate: 115200
    handshake_string: "WandererBoxPlusV3"
```

## Utilisation

### Mode GitHub (recommandé)

```bash
# Utiliser les firmwares hébergés sur GitHub
python updater.py --github your-username/wanderer-linux-updater
```

### Mode URL

```bash
# Utiliser une liste de firmwares depuis une URL
python updater.py --url https://your-url.com/firmware-list.txt
```

### Mode fichier local

```bash
# Utiliser un fichier firmware local
python updater.py --file firmware.hex
```

### Options supplémentaires

```bash
# Utiliser un fichier de configuration personnalisé
python updater.py --github your-username/repo --config my-config.yml

# Mode dry-run (affiche la commande sans l'exécuter)
python updater.py --github your-username/repo --dry-run
```

## Détection d'appareils

Le système peut détecter automatiquement les appareils connectés via handshake :

```bash
# Tester la détection d'appareils
python test_detection.py
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
├── device_detector.py                   # Détection d'appareils
├── updater.py                          # Script principal
├── test_detection.py                   # Test de détection
├── firmware/                           # Firmwares (auto-généré)
├── firmware_index.json                 # Index des firmwares (auto-généré)
└── README.md
```

## Appareils supportés

- WandererBoxPlusV3
- WandererBoxProV3
- WandererCoverV3/V4/V4Pro
- WandererDewTerminator
- WandererEclipse
- WandererRotatorLiteV1/V2
- WandererRotatorMini
- WandererRotatorProV1/V2
- WandererETA54

## Configuration avancée

### Handshake personnalisé

Vous pouvez personnaliser les commandes de handshake dans `config.yml` :

```yaml
device_detection:
  handshake_commands:
    - "VERSION"
    - "DEVICE"
    - "ID"
    - "WHOAMI"
```

### Réponses d'appareils

Définissez les réponses attendues pour chaque appareil :

```yaml
device_detection:
  device_responses:
    WandererBoxPlusV3: ["WandererBoxPlusV3", "BoxPlusV3", "V3"]
    WandererRotatorLiteV1: ["WandererRotatorLiteV1", "RotatorLiteV1"]
```

### Configuration de mise à jour

```yaml
update:
  auto_detect: true          # Détection automatique d'appareils
  auto_detect_port: true     # Détection automatique de port
  confirm_update: true        # Demander confirmation avant mise à jour
  dry_run: false             # Mode dry-run
```

## Dépannage

### Aucun appareil détecté

1. Vérifiez que l'appareil est connecté
2. Testez avec `python test_detection.py`
3. Ajustez les commandes de handshake dans `config.yml`
4. Vérifiez les taux de baud dans `config.yml`

### Erreurs de configuration

```bash
# Valider la configuration
python -c "from config_manager import ConfigManager; ConfigManager().validate_config()"
```

### Problèmes de port série

```bash
# Lister les ports disponibles
python -c "from device_detector import DeviceDetector; from config_manager import ConfigManager; print(DeviceDetector(ConfigManager()).get_available_ports())"
```

## Contribution

1. Fork le repository
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Poussez vers la branche
5. Créez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
