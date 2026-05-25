# fritzbox_mac_monitor - Spezifikation für Claude Code

## Projekt-Übersicht

**Projektname:** fritzbox_mac_monitor  
**Zweck:** Erkennt unbekannte Geräte im Heimnetz via Fritz!Box TR-064 API und sendet bei neuen unbekannten MACs einen Telegram-Alert.  
**Hauptfunktionen:**
- Aktive Geräte aus der Fritz!Box auslesen (TR-064, fritzconnection)
- MACs gegen Whitelist `known_macs.json` vergleichen
- Unbekannte MACs per Telegram melden (einmalig pro neuer MAC, kein Spam)
- Alle Läufe in Log-Datei protokollieren

**Zielumgebung:**
- Betriebssystem: Windows Server (HauServer), Entwicklung auf Windows 11 (AHMain)
- Python-Version: 3.12
- Deployment: HauServer `D:\dataserver\_Batchprozesse\fritzbox_mac_monitor\` – automatischer Start via Windows Task Scheduler (täglich)

---

## Deployment-Architektur

```
Entwicklung (AHMain):
  C:\Users\ah\Dev\fritzbox_mac_monitor\
        ↕ git push / pull
GitHub: Drahmue/fritzbox_mac_monitor (private)
        ↕ git pull
Produktion (HauServer):
  D:\dataserver\_Batchprozesse\fritzbox_mac_monitor\
        → täglich via Windows Task Scheduler
```

---

## Voraussetzungen

### System
- Fritz!Box 7580, FRITZ!OS 07.30, IP 192.168.178.1
- TR-064 aktiviert: Heimnetz → Netzwerk → Einstellungen → „Zugriff für Anwendungen zulassen"
- Python 3.12 im PATH (HauServer + AHMain)
- Telegram-Bot bereits vorhanden (Bot-Token + Chat-ID aus `notify_config.json` des Backup-Projekts)

### Externe Dependencies
- **fritzconnection**: TR-064 Client (FritzHosts)
- **requests**: Telegram Bot API

### requirements.txt
```
fritzconnection
requests
```

### Benutzer-Setup erforderlich
- [ ] `config/mac_monitor.ini` aus Template erstellen und Passwort eintragen
- [ ] Pfad zu `notify_config.json` in INI eintragen (zeigt auf Backup-Projekt-Config)
- [ ] `config/known_macs.json` mit initialer Whitelist befüllen (aus heimnetz-state.md)
- [ ] TR-064 in Fritz!Box aktivieren (siehe oben)

---

## Dateistruktur

```
fritzbox_mac_monitor/
├── src/
│   └── fritzbox_mac_monitor.py     # Hauptskript
├── config/
│   ├── mac_monitor.ini             # Echte Konfig (gitignored via *.ini)
│   ├── mac_monitor.ini.template    # Vorlage (committed)
│   └── known_macs.json             # MAC-Whitelist (committed, manuell gepflegt)
├── data/
│   └── alerted_macs.json           # Bereits gemeldete MACs (gitignored via /data/)
├── logs/                           # Log-Dateien (gitignored)
├── requirements.txt
├── SPECIFICATION.md
├── README.md
└── changelog.md
```

### Wichtig: Was committed ist, was nicht

| Datei | In Git? | Grund |
|-------|---------|-------|
| `known_macs.json` | ✅ JA | Keine Credentials, öffentlich unbedenklich |
| `mac_monitor.ini` | ❌ NEIN | Enthält Fritz!Box-Passwort |
| `alerted_macs.json` | ❌ NEIN | Laufzeit-State, gerätespezifisch |
| `logs/` | ❌ NEIN | Laufzeit-Output |

---

## Konfigurationsdateien

### mac_monitor.ini (gitignored)

```ini
[fritzbox]
ip = 192.168.178.1
password = DEIN_PASSWORT

[files]
log_file         = logs/mac_monitor.log
known_macs_file  = config/known_macs.json
alerted_macs_file = data/alerted_macs.json
notify_config    = S:\_Batchprozesse\Backup\notify_config.json

[settings]
; Nur aktive Geräte prüfen (True empfohlen)
active_only = True
```

### known_macs.json (committed, manuell gepflegt)

Enthält alle bekannten/dokumentierten MACs aus heimnetz-state.md. Bei neuen Geräten manuell ergänzen.

```json
{
  "comment": "MAC-Whitelist – Sync mit heimnetz-state.md. Stand: 2026-05-25",
  "known_macs": [
    "AA:BB:CC:DD:EE:FF",
    "..."
  ]
}
```

**Hinweis:** MACs in Großbuchstaben, Format `XX:XX:XX:XX:XX:XX`.  
Gastnetz-Geräte (Alexas etc.) ebenfalls eintragen, da sie regulär aktiv sind.

### alerted_macs.json (gitignored, automatisch erstellt)

Verhindert wiederholte Alerts für dieselbe MAC:

```json
{
  "alerted": {
    "AA:BB:CC:DD:EE:FF": {
      "first_seen": "2026-05-25T10:00:00",
      "name": "PC-192-168-178-99",
      "ip": "192.168.178.99"
    }
  }
}
```

### notify_config.json (im Backup-Projekt, geteilt)

Wird per Pfad in `mac_monitor.ini` referenziert – kein eigener Bot nötig.  
Relevante Felder: `telegram_bot_token`, `telegram_chat_id`, `notify_telegram`, `computername`.

---

## Kernlogik

### Ablauf pro Lauf

```
1. Konfiguration laden (mac_monitor.ini)
2. Logging einrichten
3. known_macs.json laden → Set bekannter MACs
4. alerted_macs.json laden → Set bereits gemeldeter MACs
5. Fritz!Box verbinden (FritzHosts via TR-064)
6. Aktive Geräte auslesen (get_hosts_info(), nur active=True)
7. Für jede aktive MAC:
   a. In known_macs? → OK, überspringen
   b. In alerted_macs? → bereits gemeldet, überspringen
   c. Sonst → Telegram-Alert senden + in alerted_macs eintragen
8. alerted_macs.json speichern
9. Zusammenfassung loggen
```

### Deduplication-Strategie

`alerted_macs.json` speichert alle bereits gemeldeten unbekannten MACs **dauerhaft**.  
Neue Meldung nur bei:
- MAC noch nie gemeldet (nicht in alerted_macs)
- MAC wurde manuell aus alerted_macs entfernt (z.B. nach Identifikation + Eintrag in known_macs)

**Kein automatisches Ablaufen** – bewusste Entscheidung, damit bekannte Problemfälle nicht täglich erneut gemeldet werden.

---

## Telegram-Nachrichtenformat

```
🚨 Unbekanntes Gerät im Heimnetz!

Name : PC-192-168-178-99
MAC  : AA:BB:CC:DD:EE:FF
IP   : 192.168.178.99
Zeit : 25.05.2026 10:00:05
Host : HauServer
```

Bei mehreren unbekannten MACs in einem Lauf: **eine Nachricht pro MAC** (nicht gebündelt), damit jede MAC separat behandelt werden kann.

Zusätzlich bei erfolgreichem Lauf ohne Befund (optional, konfigurierbar): kein Alert (kein Spam).

---

## Funktions-Spezifikationen

### 1. load_config(config_path: str) -> ConfigParser
Lädt INI, validiert Pflichtfelder, gibt ConfigParser zurück. Bei Fehler: sys.exit(1).

### 2. setup_logging(log_file: str) -> None
FileHandler UTF-8, INFO-Level. Verzeichnis wird bei Bedarf erstellt.

### 3. screen_and_log(message: str) -> None
Zentrale Ausgabefunktion: print() + logger.info(). Kein print() sonst im Code.

### 4. connect_to_fritzbox(ip: str, password: str) -> FritzHosts
FritzHosts-Instanz erstellen. FritzConnection intern über fh.fc.  
Error-Handling: FritzAuthorizationError, FritzConnectionException → logger.critical() + sys.exit(1).

### 5. get_active_hosts(fh: FritzHosts) -> list[dict]
Ruft `fh.get_hosts_info()` auf, filtert auf `status == True`.  
Gibt Liste von Dicts zurück: `{name, mac, ip}`.

### 6. load_known_macs(path: str) -> set[str]
Liest known_macs.json, gibt Set mit MACs in Großbuchstaben zurück.

### 7. load_alerted_macs(path: str) -> dict
Liest alerted_macs.json. Gibt leeres Dict zurück wenn Datei nicht existiert.

### 8. save_alerted_macs(path: str, alerted: dict) -> None
Schreibt alerted_macs.json (UTF-8, indent=2). Erstellt Verzeichnis bei Bedarf.

### 9. send_telegram(token: str, chat_id: str, message: str) -> bool
Sendet Nachricht via Telegram Bot API. Gibt True bei Erfolg zurück.  
Bei Fehler: logger.warning(), kein sys.exit() (Monitoring soll weiterlaufen).

### 10. check_unknown_macs(active_hosts, known_macs, alerted_macs) -> list[dict]
Vergleicht aktive MACs gegen Whitelist und bereits gemeldete MACs.  
Gibt Liste der neu unbekannten Hosts zurück.

### 11. main() -> None
Steuert Ablauf. Konfigurationspfad: sys.argv[1] oder Standard `config/mac_monitor.ini`.

---

## Technische Referenz: fritzconnection API

> Verifiziert in fritzapi-Projekt (fritzconnection 1.15.1).

```python
from fritzconnection.lib.fritzhosts import FritzHosts
fh = FritzHosts(address=ip, password=password)

# get_hosts_info() gibt Liste von Dicts zurück:
# 'mac', 'name', 'ip', 'status' (bool), 'interface_type', 'address_source', 'lease_time_remaining'
hosts = fh.get_hosts_info()
active = [h for h in hosts if h['status']]
```

**Kein SID/Lua-Auth nötig** – DHCP-Reservierungen werden hier nicht benötigt.

### Exception-Handling

```python
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
)
```

---

## Telegram API

Analog zum Backup-Projekt (`start_backup.ps1`):

```python
import requests

def send_telegram(token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    return resp.ok
```

notify_config.json wird eingelesen und `telegram_bot_token` / `telegram_chat_id` / `notify_telegram` ausgewertet.  
Wenn `notify_telegram == false`: kein Alert (nur Log).

---

## Initialbefüllung known_macs.json

Die initiale Whitelist wird aus `heimnetz-state.md` (Heimnetz-Projekt) abgeleitet.  
Quelle: alle dort dokumentierten Geräte-MACs (Hauptnetz + Gastnetz).  
**Nicht enthalten:** Temporäre/randomisierte MACs (I-07, gelöschte Einträge).

---

## Windows Task Scheduler (HauServer)

```
Aufgabe    : FritzboxMacMonitor
Trigger    : Täglich ab 08:00 Uhr, Wiederholung alle 1 Stunde, Dauer: Unbegrenzt
Aktion     : python src/fritzbox_mac_monitor.py
Startordner: D:\Dataserver\_Batchprozesse\fritzbox_mac_monitor\
Benutzer   : Service-Account (unabhängig von Benutzeranmeldung ausführen)
```

⚠️ Das „Starten in"-Feld ist zwingend erforderlich – relative Pfade (config/, logs/, data/) funktionieren sonst nicht.

---

## Test-Szenarien

### Szenario 1: Alle MACs bekannt
**Erwartung:** Kein Telegram-Alert. Log: „X aktive Geräte geprüft, 0 unbekannt."

### Szenario 2: Neue unbekannte MAC aktiv
**Erwartung:** Telegram-Alert mit MAC/Name/IP. Eintrag in alerted_macs.json.  
Beim nächsten Lauf: kein erneuter Alert für dieselbe MAC.

### Szenario 3: Fritz!Box nicht erreichbar
**Erwartung:** Log: KRITISCH. sys.exit(1). Kein Telegram-Alert (optional: Alert bei Verbindungsfehler).

### Szenario 4: known_macs.json fehlt
**Erwartung:** sys.exit(1) mit Fehlermeldung.

### Szenario 5: Telegram-Fehler
**Erwartung:** Warning im Log, Skript läuft weiter (alerted_macs.json wird trotzdem gespeichert).

---

## Versions-Historie

- **v1.0.1** - 2026-05-25: Task Scheduler auf stündlich aktualisiert; Deployment-Pfad korrigiert (D:\Dataserver\...)
- **v1.0.0** - 2026-05-25: Initiale Spezifikation erstellt
