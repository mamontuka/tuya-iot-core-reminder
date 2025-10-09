#!/usr/bin/env python3
import asyncio
import json
import os
import logging
import requests
from datetime import datetime, timezone, time
from math import ceil
from dateutil import parser as dtparser
import pytz
import re
import time  # for synchronous sleep in retries

OPTIONS_PATH = "/data/options.json"
ADVANCE_DAYS_DEFAULT = [30, 14, 7, 3, 1]
SUPERVISOR_URL = "http://supervisor/core/api"

# ==================== Helpers ====================
def parse_expiry_date(date_str: str, time_str: str, tz_name: str = "UTC", date_format: str = "auto"):
    """Parse a date and time string into a timezone-aware datetime object."""
    tz = pytz.timezone(tz_name)
    s = date_str.strip()
    t = (time_str or "00:00").strip()
    dt = None

    # Try ISO parse first
    try:
        dt = dtparser.isoparse(s)
    except Exception:
        dt = None

    if dt is None:
        try:
            if date_format == "iso":
                dt = datetime.strptime(s, "%Y-%m-%d")
            elif date_format in ("us", "eu"):
                fmt = "%m/%d/%Y" if date_format == "us" else "%d/%m/%Y"
                dt = datetime.strptime(s, fmt)
            else:  # auto
                parts = re.split(r"[./-]", s)
                p0 = int(parts[0])
                p1 = int(parts[1])
                dayfirst = p0 > 12 or (p0 <= 12 and p1 <= 12)
                dt = dtparser.parse(s, dayfirst=dayfirst)
        except Exception:
            dt = None

    if dt is None:
        raise ValueError(f"Cannot parse date: {date_str}")

    # Parse time
    try:
        hhmm = datetime.strptime(t, "%H:%M").time()
    except Exception:
        hhmm = time(0, 0)

    dt = datetime(dt.year, dt.month, dt.day, hhmm.hour, hhmm.minute)
    dt = tz.localize(dt)
    return dt

# ==================== Scheduler ====================
class NotificationScheduler:
    """Scheduler to send notifications based on remaining days."""

    def __init__(self, config, logger):
        self.config = config
        self._LOGGER = logger
        self.hass_token = os.getenv("SUPERVISOR_TOKEN")
        self.notify_service = config.get("notify_service", "notify.mobile_app_myphone")
        self.push_count = config.get("push_count", 1)
        self.push_interval_min = config.get("push_interval_min", 60)
        self.advance_days = config.get("advance_days", [])
        self.expiry_dt = config.get("_expiry_dt")

        if not self.hass_token:
            self._LOGGER.error("SUPERVISOR_TOKEN is missing! Cannot send notifications.")
        if not self.notify_service:
            self._LOGGER.warning("No notify_service configured!")

        self._LOGGER.info("Initialized NotificationScheduler using Supervisor API authentication.")

    async def schedule_notifications(self):
        """Main loop to schedule notifications."""
        if not self.hass_token:
            self._LOGGER.error("Cannot send notifications: missing SUPERVISOR_TOKEN.")
            return

        # Send notification immediately on startup
        await self.send_current_status_notification()

        # Continuous check for advance_days
        while True:
            now = datetime.now(timezone.utc)
            remaining_days_total = ceil((self.expiry_dt - now).total_seconds() / 86400)

            for days_before in self.advance_days:
                if remaining_days_total == days_before:
                    await self.send_notification(days_before)

            await asyncio.sleep(3600)  # check every hour

    async def send_current_status_notification(self):
        """Send notification with remaining days at startup."""
        now = datetime.now(timezone.utc)
        remaining_days_total = ceil((self.expiry_dt - now).total_seconds() / 86400)
        message = self._compose_message(remaining_days_total)
        await self._send_push(message)

    async def send_notification(self, days_before: int):
        """Send notification for specific advance_days."""
        message = self._compose_message(days_before)
        await self._send_push(message)

    def _compose_message(self, days):
        """Compose the notification message based on remaining days."""
        if days < 0:
            return "Tuya IOT expired"
        elif days == 0:
            return "Tuya IOT expires today"
        else:
            return f"Tuya IOT expires in {days} days"

    async def _send_push(self, message: str):
        """Send push notification via Supervisor API."""
        if not self.hass_token or not self.notify_service:
            self._LOGGER.error("Cannot send notification: missing token or notify_service")
            return

        domain, service = self.notify_service.split(".")
        url = f"http://supervisor/core/api/services/{domain}/{service}"
        headers = {
            "Authorization": f"Bearer {self.hass_token}",
            "Content-Type": "application/json",
        }
        payload = {"message": message}

        if self.config.get("debug"):
            self._LOGGER.debug("Sending notification: %s", payload)
            self._LOGGER.debug("POST URL: %s", url)
            self._LOGGER.debug("Auth header: Bearer %s...<truncated>", self.hass_token[:10])

        for i in range(self.push_count):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=10)
                if self.config.get("debug"):
                    self._LOGGER.debug("HTTP status: %s, response: %s", r.status_code, r.text)

                if r.status_code == 401:
                    self._LOGGER.error("Supervisor token rejected (401 Unauthorized).")
                elif r.status_code >= 400:
                    self._LOGGER.error("Failed to send notification: %s %s", r.status_code, r.text)
                else:
                    self._LOGGER.info("Notification sent successfully (%d/%d)", i + 1, self.push_count)
            except Exception as e:
                self._LOGGER.exception("Exception while sending notification: %s", e)

            if i < self.push_count - 1:
                await asyncio.sleep(self.push_interval_min * 60)

# ==================== Main ====================
def load_config():
    """Load configuration from options.json."""
    cfg = {}
    if os.path.exists(OPTIONS_PATH):
        with open(OPTIONS_PATH, "r") as f:
            try:
                cfg = json.load(f)
            except Exception as e:
                raise RuntimeError(f"Failed to parse {OPTIONS_PATH}: {e}")

    cfg.setdefault("expiry_date", "31/12/2025")
    cfg.setdefault("expiry_time", "12:00")
    cfg.setdefault("date_format", "auto")
    cfg.setdefault("notify_service", "notify.mobile_app_myphone")
    cfg.setdefault("push_count", 1)
    cfg.setdefault("push_interval_min", 60)
    cfg.setdefault("debug", False)
    cfg["advance_days"] = ADVANCE_DAYS_DEFAULT

    cfg["_expiry_dt"] = parse_expiry_date(
        cfg["expiry_date"], cfg["expiry_time"],
        tz_name="UTC", date_format=cfg.get("date_format", "auto")
    )
    return cfg

def setup_logging(debug: bool):
    """Setup logging for the add-on."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s]: %(message)s"
    )
    return logging.getLogger(__name__)

def list_mobile_apps(logger):
    """Query Supervisor API to list available mobile notify services with retry."""
    token = os.getenv("SUPERVISOR_TOKEN")
    if not token:
        logger.warning("SUPERVISOR_TOKEN missing, cannot list mobile apps")
        return []

    headers = {"Authorization": f"Bearer {token}"}
    max_attempts = 5
    base_delay = 5
    attempt = 1
    while attempt <= max_attempts:
        try:
            r = requests.get(f"{SUPERVISOR_URL}/services", headers=headers, timeout=10)
            r.raise_for_status()
            services = r.json()
            mobile_services = [
                f"notify.{s}" for svc in services
                if svc.get("domain") == "notify"
                for s in svc.get("services", [])
                if s.startswith("mobile_app_")
            ]
            if mobile_services:
                logger.info("Available mobile apps:")
                for s in mobile_services:
                    logger.info("  %s", s)
            else:
                logger.info("No mobile apps found.")
            return mobile_services
        except requests.exceptions.RequestException as e:
            logger.warning(
                "Attempt %d/%d: Supervisor API not ready (%s). Retrying in %ds...",
                attempt, max_attempts, e, base_delay * attempt
            )
            time.sleep(base_delay * attempt)  # synchronous sleep to avoid asyncio.run() issue
            attempt += 1
        except Exception as e:
            logger.exception("Unexpected error while querying Supervisor services: %s", e)
            break
    logger.error("Supervisor API unavailable after %d attempts.", max_attempts)
    return []

async def main():
    """Main entry point for the add-on."""
    config = load_config()
    logger = setup_logging(config.get("debug", False))

    logger.info(
        "Loaded config: expiry=%s, advance_days=%s, notify=%s, debug=%s",
        config["_expiry_dt"], config["advance_days"],
        config.get("notify_service"), config.get("debug")
    )

    list_mobile_apps(logger)

    scheduler = NotificationScheduler(config, logger)

    now = datetime.now(timezone.utc)
    remaining_days_total = ceil((config["_expiry_dt"] - now).total_seconds() / 86400)
    logger.info("Tuya IOT Core expires in %d days", remaining_days_total)

    await scheduler.schedule_notifications()

if __name__ == "__main__":
    asyncio.run(main())
