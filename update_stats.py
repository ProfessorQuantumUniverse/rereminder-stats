import requests
import json
import sys
from datetime import datetime

# Konfiguration
BASE_URL = "https://fdroid.gitlab.io/metrics/"
INDEX_URL = f"{BASE_URL}index.json"
PACKAGE_NAME = "com.olaf.rereminder"
OUTPUT_FILE = "fdroid-shield.json"

def format_number(num):
    """Formatiert Zahlen wie 1500 zu 1.5k"""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}k"
    return str(num)

def get_latest_metrics_url():
    """Lädt index.json und ermittelt die URL der neuesten Metrik-Datei"""
    print(f"Lade Index von: {INDEX_URL}")
    try:
        r = requests.get(INDEX_URL)
        r.raise_for_status()
        files = r.json()
        
        # Annahme: index.json ist eine Liste von Strings (Dateinamen/Pfade)
        # Wir sortieren sie, um den aktuellsten Eintrag zu finden (meist Datumsformat YYYY-MM-DD)
        if not files:
            print("Keine Dateien im Index gefunden.")
            sys.exit(1)
            
        # Sortieren (Datums-Strings sortieren sich lexikalisch korrekt)
        files.sort()
        latest_file = files[-1]
        
        # Falls die Endung .json fehlt, fügen wir sie hinzu (je nach F-Droid Struktur)
        if not latest_file.endswith(".json"):
            latest_file += ".json"
            
        print(f"Neueste Datei identifiziert: {latest_file}")
        return f"{BASE_URL}{latest_file}"
    except Exception as e:
        print(f"Fehler beim Laden des Index: {e}")
        sys.exit(1)

def main():
    # 1. URL der neuesten Daten holen
    metrics_url = get_latest_metrics_url()
    
    # 2. Metriken laden
    print(f"Lade Metriken von: {metrics_url}")
    try:
        r = requests.get(metrics_url)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Fehler beim Laden der Metriken: {e}")
        sys.exit(1)

    # 3. Daten für das Paket suchen und summieren
    total_downloads = 0
    
    if PACKAGE_NAME in data:
        package_stats = data[PACKAGE_NAME]
        print(f"Paket '{PACKAGE_NAME}' gefunden. Verarbeite Daten...")
        
        # Die Struktur ist oft: "YYYY-MM-DD": download_count
        # Wir summieren alle numerischen Werte in diesem Dictionary
        if isinstance(package_stats, dict):
            for key, value in package_stats.items():
                if isinstance(value, (int, float)):
                    total_downloads += int(value)
        elif isinstance(package_stats, int):
            # Falls die Struktur vereinfacht ist und direkt die Summe enthält
            total_downloads = package_stats
    else:
        print(f"WARNUNG: Paket '{PACKAGE_NAME}' nicht in der aktuellen Metrik-Datei gefunden.")
        # Wir setzen 0 oder behalten den alten Wert (hier 0 für clean slate)

    print(f"Downloads (letzter Zeitraum): {total_downloads}")

    # 4. JSON für Shields.io erstellen
    shield_data = {
        "schemaVersion": 1,
        "label": "F-Droid Downloads",
        "message": format_number(total_downloads),
        "color": "blue"  # oder "brightgreen", etc.
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(shield_data, f, indent=2)
    
    print(f"Datei '{OUTPUT_FILE}' erfolgreich erstellt.")

if __name__ == "__main__":
    main()
