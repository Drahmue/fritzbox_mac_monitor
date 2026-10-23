## [1.1.0] - 2026-10-23
- Telegram ueber zentrale Bibliothek `D:\Dataserver\_Batchprozesse\_shared\notify_telegram.py` (Standard CS-028): eigene `send_telegram`/`load_notify_config` entfernt, ebenso der UNC-Verweis auf `Backup\notify_config.json` (Fehlerquelle aus 1.0.6) und die direkte `requests`-Nutzung
- `[files] notify_config` in `mac_monitor.ini` nicht mehr noetig (Pflichtfeld entfernt, Vorlage + README angepasst)
- Fehlgeschlagene Alerts landen zusaetzlich in `_Batchprozesse\logs\notify_failed.log`; Abstuerze meldet der zentrale `task_watchdog` (taeglich), nicht der Monitor selbst (stuendlicher Lauf -> sonst Meldungsflut)

## [1.0.7] - 2026-08-31
- known_macs.json: `AHFold` (`7A:68:0D:E2:EF:5D`, .58) und `shellyfloodHebe` (`EC:64:C9:C1:E5:7D`, .60) als legitime Geraete whitelisted – beide waren seit 29./30.08.2026 wiederholt als unbekannt geflaggt worden, User hat sie als bekannt bestaetigt (176 Eintraege)
- alerted_macs.json bereinigt: `AHFold`-Eintrag entfernt, der als "bereits gemeldet" markiert war, obwohl der zugehoerige Telegram-Alert wegen des in 1.0.6 gefixten Pfad-Bugs nie tatsaechlich zugestellt wurde
- Fix verifiziert: Testlauf zeigt "Bekannte MACs geladen: 176", "Bereits gemeldete MACs: 0", "Unbekannte MACs (neu): 0"

## [1.0.6] - 2026-08-31
- Fix: `notify_config` in `mac_monitor.ini` zeigte auf falschen UNC-Pfad (`\\hauserver\_Batchprozesse\Backup\...`, Freigabe-Segment `Dataserver` fehlte) – Telegram-Alerting lief seit Einrichtung ins Leere, Monitor loggte unbekannte Geraete nur, ohne zu benachrichtigen
- Korrigiert auf `\\hauserver\Dataserver\_Batchprozesse\Backup\notify_config.json`, ebenso im Platzhalter `config/mac_monitor.ini.template`
- Fix verifiziert: Pfad ueber ConfigParser aufgeloest, notify_config.json lesbar, `notify_telegram=true`, Bot-Token/Chat-ID vorhanden
- Abschluss-Check: Die 4 Dauer-Tasks im Ordner `AHSkripts`, die unter dem Service-Konto laufen (DSL Speedtest Monitoring, Zaehler Monitoring, Stock Monitoring Service, Status Web App), wurden auf Funktionsfaehigkeit geprueft – alle liefen durchgehend und griffen erfolgreich per UNC-Pfad auf die Netzwerkfreigabe zu; keine Anpassung der Zugangsdaten noetig, da das neue Service-Konto-Passwort identisch zum alten gesetzt wurde

## [1.0.5] - 2026-08-29
- Fix: `fritzconnection` fehlte im globalen Python-3.12-Interpreter (`C:\Program Files\Python312`), den der Task Scheduler nutzt (kein eigenes venv wie z.B. bei `depot`) – Modul nachinstalliert (`pip install fritzconnection`, jetzt 1.15.1)
- Ursache war ein `ModuleNotFoundError` beim Import ganz oben im Skript, noch vor der Logging-Initialisierung – dadurch blieb `mac_monitor.log` seit 15.07.2026 09:10 unverändert, obwohl der Task seither jede volle Stunde mit `LastTaskResult=1` fehlschlug
- Fix per manuellem Testlauf verifiziert: `LastTaskResult=0`, neuer Logeintrag 2026-08-29 10:18 (1 neues unbekanntes Gerät erkannt: `AHFold`)
- Offen (behoben in 1.0.6): Telegram-Alerting war zu diesem Zeitpunkt noch inaktiv (`notify_config.json` unter `\\hauserver\_Batchprozesse\Backup\` nicht gefunden) – Monitor loggte nur, versendete keine Alerts

## [1.0.4] - 2026-07-22
- Task Scheduler: Prüfintervall von 5 Minuten auf 60 Minuten erhöht (Trigger-Wiederholung geändert, Start weiterhin 05:00 Uhr)
- README/SPECIFICATION: Dokumentation an tatsächlichen Task-Scheduler-Trigger angepasst (Start 05:00 statt 08:00)

## [1.0.3] - 2026-07-09
- known_macs.json: MAC `B0:81:84:A1:67:50` (shelly1g3VorgartenBrunnen, .221) wiederhergestellt – wurde am 07.07.2026 fälschlicherweise als alte Pool-Shelly-MAC entfernt; gehört zu shelly1g3VorgartenBrunnen (aktiv seit April 2025)
- alerted_macs.json: Eintrag für `B0:81:84:A1:67:50` bereinigt
- Stand-Datum auf 2026-07-09 aktualisiert

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
