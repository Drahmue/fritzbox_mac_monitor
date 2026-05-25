# fritzbox_mac_monitor

Erkennt unbekannte Geräte im Heimnetz via Fritz!Box TR-064 API und sendet bei neuen unbekannten MACs einen Telegram-Alert.

## Funktionen

- Aktive Geräte aus der Fritz!Box auslesen (TR-064, fritzconnection)
- MACs gegen Whitelist `config/known_macs.json` vergleichen
- Unbekannte MACs einmalig per Telegram melden (kein Spam bei wiederholten Läufen)
- Alle Läufe in Log-Datei protokollieren

## Installation

```bash
git clone https://github.com/Drahmue/fritzbox_mac_monitor.git
cd fritzbox_mac_monitor
python -m pip install -r requirements.txt
cp config/mac_monitor.ini.template config/mac_monitor.ini
# mac_monitor.ini anpassen: Passwort + Pfad zu notify_config.json
```

## Konfiguration

`config/mac_monitor.ini` (nicht in Git):

| Parameter | Beschreibung |
|-----------|-------------|
| `[fritzbox] ip` | IP-Adresse der Fritz!Box (Standard: 192.168.178.1) |
| `[fritzbox] password` | Fritz!Box-Passwort |
| `[files] notify_config` | Pfad zur `notify_config.json` des Backup-Projekts |
| `[files] known_macs_file` | Pfad zur MAC-Whitelist (Standard: config/known_macs.json) |
| `[files] alerted_macs_file` | Pfad zur Deduplication-Datei (Standard: data/alerted_macs.json) |
| `[files] log_file` | Pfad zur Log-Datei (Standard: logs/mac_monitor.log) |

`config/known_macs.json` (in Git, manuell gepflegt):
Alle bekannten MACs im Format `XX:XX:XX:XX:XX:XX` (Großbuchstaben).
Bei neuen Geräten manuell ergänzen und committen.

## Verwendung

```bash
python src/fritzbox_mac_monitor.py
# oder mit explizitem Konfigurationspfad:
python src/fritzbox_mac_monitor.py pfad/zur/config.ini
```

## Deployment (HauServer)

```
D:\Dataserver\_Batchprozesse\fritzbox_mac_monitor\
```

Windows Task Scheduler: stündlich, Startordner = Projektverzeichnis.

## Logs

Logs werden in `logs/` gespeichert (gitignored).
`data/alerted_macs.json` verhindert wiederholte Alerts für dieselbe MAC (gitignored).
