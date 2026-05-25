#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fritzbox_mac_monitor.py

Erkennt unbekannte Geraete im Heimnetz via Fritz!Box TR-064 API
und sendet bei neuen unbekannten MACs einen Telegram-Alert.

Ablauf:
  1. Konfiguration laden (mac_monitor.ini)
  2. Logging einrichten
  3. known_macs.json laden -> Set bekannter MACs
  4. alerted_macs.json laden -> bereits gemeldete MACs
  5. Fritz!Box verbinden (FritzHosts via TR-064)
  6. Aktive Geraete auslesen
  7. Unbekannte, noch nicht gemeldete MACs per Telegram melden
  8. alerted_macs.json speichern
"""

import json
import logging
import os
import socket
import sys
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

import requests
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
)
from fritzconnection.lib.fritzhosts import FritzHosts

# Arbeitsverzeichnis auf Projektwurzel setzen (parent von src/)
os.chdir(Path(__file__).parent.parent)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> ConfigParser:
    """
    Laedt die INI-Konfigurationsdatei und validiert Pflichtfelder.

    Args:
        config_path (str): Pfad zur INI-Datei.

    Returns:
        ConfigParser: Geladene Konfiguration.

    Raises:
        SystemExit: Bei fehlender Datei oder fehlendem Pflichtfeld.
    """
    path = Path(config_path)
    if not path.exists():
        print(f"FEHLER: Konfigurationsdatei nicht gefunden: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = ConfigParser(inline_comment_prefixes=("#", ";"))
    config.read(path, encoding="utf-8")

    required = {
        "fritzbox": ["ip", "password"],
        "files": ["log_file", "known_macs_file", "alerted_macs_file", "notify_config"],
        "settings": ["active_only"],
    }
    for section, keys in required.items():
        if not config.has_section(section):
            print(f"FEHLER: Abschnitt [{section}] fehlt in {config_path}", file=sys.stderr)
            sys.exit(1)
        for key in keys:
            if not config.has_option(section, key):
                print(f"FEHLER: Schluessel '{key}' fehlt in [{section}] in {config_path}", file=sys.stderr)
                sys.exit(1)

    return config


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(log_file: str) -> None:
    """
    Richtet das Logging mit FileHandler (UTF-8, INFO-Level) ein.
    Das Verzeichnis wird bei Bedarf erstellt.

    Args:
        log_file (str): Pfad zur Log-Datei.
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def screen_and_log(message: str) -> None:
    """
    Zentrale Ausgabefunktion: gibt die Nachricht auf der Konsole aus
    und schreibt sie ins Log (INFO-Level).

    Args:
        message (str): Auszugebende Nachricht.
    """
    print(message)
    logger.info(message)


# ---------------------------------------------------------------------------
# Fritz!Box
# ---------------------------------------------------------------------------

def connect_to_fritzbox(ip: str, password: str) -> FritzHosts:
    """
    Stellt eine Verbindung zur Fritz!Box her und gibt ein FritzHosts-Objekt zurueck.

    Args:
        ip (str): IP-Adresse der Fritz!Box.
        password (str): Passwort fuer den TR-064-Zugriff.

    Returns:
        FritzHosts: Verbundenes FritzHosts-Objekt.

    Raises:
        SystemExit: Bei Authentifizierungs- oder Verbindungsfehlern.
    """
    try:
        fh = FritzHosts(address=ip, password=password)
        # Verbindung durch ersten API-Aufruf validieren
        _ = fh.get_hosts_info()
        return fh
    except FritzAuthorizationError:
        screen_and_log(f"KRITISCH: Fritz!Box Authentifizierung fehlgeschlagen (falsches Passwort?). IP: {ip}")
        logger.critical("Fritz!Box Authentifizierung fehlgeschlagen. IP: %s", ip)
        sys.exit(1)
    except FritzConnectionException as exc:
        screen_and_log(f"KRITISCH: Fritz!Box nicht erreichbar unter {ip}: {exc}")
        logger.critical("Fritz!Box nicht erreichbar unter %s: %s", ip, exc)
        sys.exit(1)


def get_active_hosts(fh: FritzHosts) -> list[dict]:
    """
    Liest alle aktiven Geraete aus der Fritz!Box aus.

    Args:
        fh (FritzHosts): Verbundenes FritzHosts-Objekt.

    Returns:
        list[dict]: Liste mit Dicts {name, mac, ip} fuer aktive Geraete.
    """
    all_hosts = fh.get_hosts_info()
    active = []
    for host in all_hosts:
        if host.get("status"):
            mac = (host.get("mac") or "").upper()
            if mac:
                active.append({
                    "name": host.get("name", ""),
                    "mac": mac,
                    "ip": host.get("ip", ""),
                })
    return active


# ---------------------------------------------------------------------------
# JSON-Dateien
# ---------------------------------------------------------------------------

def load_known_macs(path: str) -> set[str]:
    """
    Laedt die MAC-Whitelist aus known_macs.json.

    Args:
        path (str): Pfad zu known_macs.json.

    Returns:
        set[str]: Set der bekannten MACs in Grossbuchstaben.

    Raises:
        SystemExit: Wenn die Datei fehlt oder ungueltiges JSON enthaelt.
    """
    json_path = Path(path)
    if not json_path.exists():
        logger.critical("known_macs.json nicht gefunden: %s", path)
        sys.exit(1)
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return {mac.upper() for mac in data.get("known_macs", [])}
    except (json.JSONDecodeError, KeyError) as exc:
        logger.critical("Fehler beim Lesen von %s: %s", path, exc)
        sys.exit(1)


def load_alerted_macs(path: str) -> dict:
    """
    Laedt bereits gemeldete MACs aus alerted_macs.json.
    Gibt ein leeres Dict zurueck, wenn die Datei nicht existiert.

    Args:
        path (str): Pfad zu alerted_macs.json.

    Returns:
        dict: Dict der bereits gemeldeten MACs (Schluessel: MAC-Adresse).
    """
    json_path = Path(path)
    if not json_path.exists():
        return {}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return data.get("alerted", {})
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Fehler beim Lesen von %s, starte mit leerem Stand: %s", path, exc)
        return {}


def save_alerted_macs(path: str, alerted: dict) -> None:
    """
    Speichert die gemeldeten MACs in alerted_macs.json.
    Das Verzeichnis wird bei Bedarf erstellt.

    Args:
        path (str): Pfad zu alerted_macs.json.
        alerted (dict): Dict der gemeldeten MACs.
    """
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps({"alerted": alerted}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(token: str, chat_id: str, message: str) -> bool:
    """
    Sendet eine Nachricht ueber die Telegram Bot API.

    Args:
        token (str): Telegram Bot-Token.
        chat_id (str): Ziel-Chat-ID.
        message (str): Zu sendende Nachricht.

    Returns:
        bool: True bei Erfolg, False bei Fehler.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        if not resp.ok:
            logger.warning("Telegram-Fehler: HTTP %s – %s", resp.status_code, resp.text)
            return False
        return True
    except requests.RequestException as exc:
        logger.warning("Telegram konnte nicht erreicht werden: %s", exc)
        return False


def load_notify_config(path: str) -> dict:
    """
    Laedt die geteilte Benachrichtigungskonfiguration (notify_config.json).

    Args:
        path (str): Pfad zu notify_config.json.

    Returns:
        dict: Geparste JSON-Daten. Leeres Dict bei Fehler.
    """
    notify_path = Path(path)
    if not notify_path.exists():
        logger.warning("notify_config.json nicht gefunden: %s – kein Telegram-Alert", path)
        return {}
    try:
        return json.loads(notify_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning("Fehler beim Lesen von notify_config.json: %s – kein Telegram-Alert", exc)
        return {}


def build_telegram_message(host: dict, hostname: str) -> str:
    """
    Erstellt die Telegram-Alertnachricht fuer ein unbekanntes Geraet.

    Args:
        host (dict): Host-Dict mit name, mac, ip.
        hostname (str): Name des ausfuehrenden Rechners.

    Returns:
        str: Formatierte Nachricht.
    """
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    return (
        f"\U0001f6a8 Unbekanntes Geraet im Heimnetz!\n\n"
        f"Name : {host['name']}\n"
        f"MAC  : {host['mac']}\n"
        f"IP   : {host['ip']}\n"
        f"Zeit : {now}\n"
        f"Host : {hostname}"
    )


# ---------------------------------------------------------------------------
# Kernlogik
# ---------------------------------------------------------------------------

def check_unknown_macs(
    active_hosts: list[dict],
    known_macs: set[str],
    alerted_macs: dict,
) -> list[dict]:
    """
    Vergleicht aktive MACs gegen Whitelist und bereits gemeldete MACs.

    Args:
        active_hosts (list[dict]): Aktive Geraete von der Fritz!Box.
        known_macs (set[str]): Whitelist bekannter MACs.
        alerted_macs (dict): Bereits gemeldete MACs.

    Returns:
        list[dict]: Liste der neu unbekannten Hosts (noch nicht in known_macs und alerted_macs).
    """
    unknown = []
    for host in active_hosts:
        mac = host["mac"]
        if mac in known_macs:
            continue
        if mac in alerted_macs:
            continue
        unknown.append(host)
    return unknown


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Steuert den Gesamtablauf des MAC-Monitors.
    Konfigurationspfad: sys.argv[1] oder Standard config/mac_monitor.ini.
    """
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/mac_monitor.ini"

    config = load_config(config_path)

    log_file = config.get("files", "log_file")
    setup_logging(log_file)

    screen_and_log("=" * 60)
    screen_and_log("fritzbox_mac_monitor gestartet")
    screen_and_log(f"Konfiguration: {config_path}")

    # JSON-Dateien laden
    known_macs_file = config.get("files", "known_macs_file")
    alerted_macs_file = config.get("files", "alerted_macs_file")
    notify_config_file = config.get("files", "notify_config")

    known_macs = load_known_macs(known_macs_file)
    alerted_macs = load_alerted_macs(alerted_macs_file)

    screen_and_log(f"Bekannte MACs geladen: {len(known_macs)}")
    screen_and_log(f"Bereits gemeldete MACs: {len(alerted_macs)}")

    # Fritz!Box verbinden
    fritz_ip = config.get("fritzbox", "ip")
    fritz_pw = config.get("fritzbox", "password")

    screen_and_log(f"Verbinde mit Fritz!Box ({fritz_ip}) ...")
    fh = connect_to_fritzbox(fritz_ip, fritz_pw)
    screen_and_log("Fritz!Box verbunden.")

    # Aktive Geraete auslesen
    active_hosts = get_active_hosts(fh)
    screen_and_log(f"Aktive Geraete gefunden: {len(active_hosts)}")

    # Unbekannte MACs ermitteln
    unknown_hosts = check_unknown_macs(active_hosts, known_macs, alerted_macs)
    screen_and_log(f"Unbekannte MACs (neu): {len(unknown_hosts)}")

    if not unknown_hosts:
        screen_and_log("Alle aktiven Geraete bekannt – kein Alert.")
    else:
        # Telegram-Konfiguration laden
        notify_cfg = load_notify_config(notify_config_file)
        telegram_enabled = str(notify_cfg.get("notify_telegram", "false")).lower() == "true"
        token = notify_cfg.get("telegram_bot_token", "")
        chat_id = str(notify_cfg.get("telegram_chat_id", ""))
        hostname = socket.gethostname()

        for host in unknown_hosts:
            screen_and_log(
                f"UNBEKANNT: Name={host['name']}  MAC={host['mac']}  IP={host['ip']}"
            )

            # alerted_macs sofort eintragen (auch wenn Telegram fehlschlaegt)
            alerted_macs[host["mac"]] = {
                "first_seen": datetime.now().isoformat(timespec="seconds"),
                "name": host["name"],
                "ip": host["ip"],
            }

            if telegram_enabled and token and chat_id:
                message = build_telegram_message(host, hostname)
                success = send_telegram(token, chat_id, message)
                if success:
                    screen_and_log(f"Telegram-Alert gesendet fuer MAC {host['mac']}")
                else:
                    screen_and_log(f"Telegram-Alert FEHLGESCHLAGEN fuer MAC {host['mac']}")
            else:
                screen_and_log("Telegram deaktiviert oder nicht konfiguriert – nur Log.")

    # alerted_macs.json speichern
    save_alerted_macs(alerted_macs_file, alerted_macs)
    screen_and_log("alerted_macs.json gespeichert.")
    screen_and_log("fritzbox_mac_monitor beendet.")
    screen_and_log("=" * 60)


if __name__ == "__main__":
    main()
