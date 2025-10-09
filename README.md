# 🧭 Tuya IOT Core Reminder Add-on

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Addon-blue.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![Supervisor API](https://img.shields.io/badge/Uses-Supervisor%20API-orange.svg?style=for-the-badge)]()
[![Python](https://img.shields.io/badge/Built%20with-Python%203.9+-blue.svg?style=for-the-badge&logo=python)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)]()

> A lightweight Home Assistant add-on to remind about **Tuya IoT Core** subscription expiry.  
> Sends mobile push notifications directly via the **Home Assistant Supervisor API** — no cloud, no credentials.

---

**This project was created for self-improvement and exploring the Homeassistant API for sending push notifications to mobile devices. It can be used as a reminder for specific dates or as part of a larger project responsible for sending push notifications.**

---

## ✨ Features

- ⏰ Notifies about subscription expiry (30, 14, 7, 3, and 1 day before expiry)
- 📱 Automatically lists available `notify.mobile_app_*` services in the log
- 🔍 Debug mode for detailed network and scheduling output
- 🔒 Uses built-in Supervisor authentication (`SUPERVISOR_TOKEN`)

---

## ⚙️ Installation

1. In **Home Assistant**:
   - Go to **Settings → Add-ons → Repositories**
   - Click **Add repository** and paste this repo URL
   - Install **Tuya IOT Core Reminder** from your repository list

2. Configure your options in the **add-on configuration UI**

---

## 🧩 Configuration Options

| Option               | Type    | Default                        | Description                                                                 |
|----------------------|---------|--------------------------------|-----------------------------------------------------------------------------|
| `expiry_date`        | string  | `"31/12/2030"`                 | Subscription expiry date (format depends on `date_format`).                |
| `expiry_time`        | string  | `"12:00"`                      | Time of the day for expiry (24h format, UTC).                              |
| `date_format`        | string  | `"auto"`                       | Date format: `"auto"`, `"us"`, `"eu"`, `"iso"`.                            |
| `notify_service`     | string  | `"notify.mobile_app_myphone"`  | Target notification service (`notify.mobile_app_*`).                       |
| `push_count`         | int     | `1`                            | How many times to repeat the push notification.                            |
| `push_interval_min`  | int     | `60`                           | Interval between repeated notifications (in minutes).                      |
| `debug`              | bool    | `false`                        | Enable debug logging (detailed network and scheduling info).               |

---

## 🚀 Usage

When the add-on starts, the log will show:

    ✅ Loaded configuration values

    📅 Remaining days until subscription expiry

    📱 List of available mobile apps (copy one into notify_service)

Notifications are sent automatically according to the schedule:

advance_days = [30, 14, 7, 3, 1]

## 🧾 Example Log Output

      INFO: Loaded config: expiry=2025-12-31 12:00:00+00:00, notify=notify.mobile_app_myphone, debug=False
      INFO: Available mobile apps:
      INFO:   notify.mobile_app_sm_a715f
      INFO:   notify.mobile_app_redmi_s2
      INFO:   notify.mobile_app_sm_a505fn
      INFO: Initialized NotificationScheduler using Supervisor API authentication.
      INFO: Tuya IOT Core expires in 85 days
      INFO: Notification sent successfully (1/1)

To select a mobile app, copy one of the notify.mobile_app_* services from the log and paste it into the notify_service option.

## 📝 Notes

    Mobile app services are automatically detected and listed in the log.

    Debug logging can be enabled via the debug option in the configuration.

    The add-on uses only Supervisor-level access — safe for both Home Assistant OS and Core installations.

    Notifications repeat automatically if configured with push_count > 1.

## 💡 Tips

    Combine this add-on with Home Assistant Automations or a dashboard card to visualize your Tuya IoT Core expiry.

    Works offline — no external cloud connections.

