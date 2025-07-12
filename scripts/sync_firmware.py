#!/usr/bin/env python3
"""
Firmware sync script for Wanderer devices.
Downloads firmware files and creates an index for GitHub Pages hosting.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from config_manager import ConfigManager

def generate_index_from_local_firmwares():
    config_manager = ConfigManager()
    firmware_dir = Path(config_manager.firmware_config.firmware_dir)
    index_file = Path(config_manager.firmware_config.index_file)
    github_repo = config_manager.firmware_config.github_repo

    # Build index without last_updated first
    index = {
        'source_url': None,
        'devices': {}
    }
    if github_repo:
        index['base_url'] = f"https://{github_repo.split('/')[0]}.github.io/{github_repo.split('/')[1]}/firmwares/"

    for file in firmware_dir.glob('*.hex'):
        filename = file.name
        match = re.match(r'^([^-]+)-(\d{8})\.hex$', filename)
        if match:
            device_name = match.group(1)
            version_date = match.group(2)
            try:
                version = datetime.strptime(version_date, '%Y%m%d').strftime('%Y-%m-%d')
            except Exception:
                version = version_date
            size = file.stat().st_size
            if device_name not in index['devices']:
                index['devices'][device_name] = []
            url = f"{index['base_url']}{filename}" if 'base_url' in index else filename
            index['devices'][device_name].append({
                'filename': filename,
                'version': version,
                'version_date': version_date,
                'size': size,
                'url': url,
                'original_url': None,
                'device_config': {
                    'avr_device': config_manager.get_device(device_name).avr_device if config_manager.get_device(device_name) else '',
                    'programmer': config_manager.get_device(device_name).programmer if config_manager.get_device(device_name) else '',
                    'baud_rate': config_manager.get_device(device_name).baud_rate if config_manager.get_device(device_name) else ''
                }
            })
    # Sort by version_date descending (most recent first)
    for device in index['devices']:
        index['devices'][device].sort(key=lambda x: x['version_date'], reverse=True)

    # Compare with existing index file (excluding last_updated)
    new_index_json = json.dumps(index, indent=2, sort_keys=True)
    if index_file.exists():
        with open(index_file, 'r') as f:
            old_index = json.load(f)
        # Remove last_updated from old index for comparison
        if 'last_updated' in old_index:
            del old_index['last_updated']
        old_index_json = json.dumps(old_index, indent=2, sort_keys=True)
        if new_index_json == old_index_json:
            print("No change in firmware index. Skipping file write and last_updated update.")
            return
    # Only now add last_updated and write the file
    index['last_updated'] = datetime.now().isoformat()
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print(f"Index generated with {sum(len(v) for v in index['devices'].values())} firmwares in {len(index['devices'])} models.")
    print(f"Index file: {index_file.resolve()}")

def download_firmware_file(url, filename, firmware_dir):
    """Download a firmware file only if it does not already exist."""
    file_path = firmware_dir / filename
    if file_path.exists():
        print(f"[SKIP] {filename} already exists, skipping download.")
        return file_path.stat().st_size
    try:
        print(f"Downloading: {filename}")
        import requests
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path.stat().st_size
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return None

if __name__ == "__main__":
    generate_index_from_local_firmwares() 