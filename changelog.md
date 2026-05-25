## [1.0.2] - 2026-05-25
- Task Scheduler: Aufgabe im Ordner „AHSkripts" angelegt

## [1.0.1] - 2026-05-25
- Fix: `ConfigParser` mit `inline_comment_prefixes` – Kommentare hinter INI-Werten werden korrekt ignoriert
- Fix: Kritische Verbindungsfehler (Fritz!Box) werden jetzt auch auf der Konsole ausgegeben
- Fix: `requirements.txt` korrigiert (nur `fritzconnection` und `requests`)
- known_macs.json: Fritz!Mesh-Repeater-MACs und Fritz!Box-eigene MAC ergänzt (166 Einträge)

## [1.0.0] - 2026-05-25
- Initiale Implementierung (`src/fritzbox_mac_monitor.py`)
- MAC-Whitelist `config/known_macs.json` mit 157 bekannten Geräten (aus heimnetz-state.md + heimnetz-shelly.md)
- Konfigurationstemplate `config/mac_monitor.ini.template`
- Deployment auf HauServer (`D:\Dataserver\_Batchprozesse\fritzbox_mac_monitor\`)
- Erster erfolgreicher Testlauf auf AHMain und HauServer: 0 unbekannte MACs
