import requests
import json
import sys
import datetime

# --- KONFIGURATION ---
PACKAGE_ID = "com.olaf.rereminder"
OUTPUT_FILE = "fdroid-shield.json"

# Basis-URLs und Server aus getdata_apps.py
BASE_URL = "https://fdroid.gitlab.io/metrics"
SERVERS = [
    "http01.fdroid.net",
    "http02.fdroid.net",
    "http03.fdroid.net",
    "originserver.f-droid.org"
]

# Konstanten aus analyzer_apps.py
REPO_PREFIX = "/repo/"
API_PACKAGES_PREFIX = "/api/v1/packages/"

# Wie viele Wochen zurückblicken? 
# 52 Wochen = 1 Jahr. Wenn du ALLES willst, setze es höher (z.B. 200), 
# aber das Script läuft dann länger.
LOGS_TO_CHECK = 52 

def format_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}k"
    return str(num)

def parse_log_file(mirror, filename):
    """
    Lädt ein Log und extrahiert Downloads mit der Logik aus analyzer_apps.py
    """
    url = f"{BASE_URL}/{mirror}/{filename}"
    downloads = 0
    api_hits = 0
    versions_found = {}

    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return 0, 0, {}
        
        data = r.json()
        paths = data.get("paths", {})

        for path, path_data in paths.items():
            # Hits extrahieren (kann int oder dict sein)
            hits = path_data.get("hits", 0) if isinstance(path_data, dict) else path_data
            if hits == 0:
                continue

            # --- LOGIK AUS analyzer_apps.py get_package_downloads ---
            
            # 1. APK Downloads prüfen
            if path.startswith(REPO_PREFIX) and path.endswith(".apk"):
                # Bereinigen
                clean_name = path.replace(REPO_PREFIX, "").replace(".apk", "").strip("/")
                
                # Query Params entfernen (z.B. &pxdate=...)
                if "&" in clean_name:
                    clean_name = clean_name.split("&")[0]
                
                # Split am letzten Unterstrich (Paketname_Version)
                if "_" in clean_name:
                    parts = clean_name.rsplit("_", 1)
                    if len(parts) == 2:
                        pkg_name, version = parts
                        
                        # MATCH!
                        if pkg_name == PACKAGE_ID:
                            downloads += hits
                            versions_found[version] = versions_found.get(version, 0) + hits

            # 2. API Hits prüfen (Metadaten-Abrufe durch F-Droid Client)
            elif path == f"{API_PACKAGES_PREFIX}{PACKAGE_ID}":
                api_hits += hits

    except Exception as e:
        print(f"    Fehler in {filename}: {e}")
        return 0, 0, {}

    return downloads, api_hits, versions_found

def main():
    grand_total_downloads = 0
    grand_total_api = 0
    
    print(f"🚀 Starte Analyse für: {PACKAGE_ID}")
    print(f"   Zeitraum: Letzte {LOGS_TO_CHECK} verfügbaren Logs pro Server")

    for server in SERVERS:
        print(f"\n🌍 Server: {server}")
        try:
            # Index holen
            r = requests.get(f"{BASE_URL}/{server}/index.json", timeout=15)
            if r.status_code != 200:
                print("   ⚠️ Index nicht erreichbar.")
                continue
            
            file_list = r.json()
            file_list.sort()
            
            # Wir nehmen die letzten X Dateien
            recent_files = file_list[-LOGS_TO_CHECK:]
            print(f"   📂 Scanne {len(recent_files)} Logs...")

            server_downloads = 0
            
            for filename in recent_files:
                if not filename.endswith(".json"): continue
                
                dl, api, vers = parse_log_file(server, filename)
                
                if dl > 0 or api > 0:
                    server_downloads += dl
                    grand_total_downloads += dl
                    grand_total_api += api
                    # Optional: Debug Output pro Treffer
                    # print(f"     + {filename}: {dl} DLs (v{list(vers.keys())})")

            print(f"   ✅ Zwischensumme {server}: {server_downloads} Downloads")

        except Exception as e:
            print(f"   ❌ Kritischer Fehler bei {server}: {e}")

    print("\n" + "="*40)
    print(f"📦 ERGEBNIS FÜR {PACKAGE_ID}")
    print(f"📥 APK Downloads: {grand_total_downloads}")
    print(f"ℹ️ API Aufrufe:   {grand_total_api}")
    print("="*40)

    # JSON schreiben
    # Wir nehmen APK Downloads als Hauptzahl, da das "echte" Installationen/Updates sind.
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    shield_data = {
        "schemaVersion": 1,
        "label": "F-Droid Downloads",
        "message": format_number(grand_total_downloads),
        "color": "blue" if grand_total_downloads > 0 else "inactive",
        "cacheSeconds": 3600,
        "lastUpdated": now
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(shield_data, f, indent=2)
        
    print(f"💾 {OUTPUT_FILE} gespeichert.")

if __name__ == "__main__":
    main()
