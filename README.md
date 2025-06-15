# Daily-fixture-for-Home-Ov0.5
Daily Telegram alert listing football fixtures where the **home team averages more than 1.5 goals per match
# ⚽ Goal Alert Bot

This project sends a daily Telegram alert listing football fixtures where the **home team averages more than 1.5 goals per match**, using [API-Football](https://rapidapi.com/api-sports/api/api-football).

## 🔧 Features

- ✅ Fetches today’s fixtures from API-Football
- ✅ Filters matches where the home team has avg goals > 1.5
- ✅ Sends formatted summary to Telegram
- ✅ Supports local CRON or cloud-based triggers (UptimeRobot + Render)

---

## 📦 Requirements

- Python 3.8+
- API-Football API Key (via [RapidAPI](https://rapidapi.com/api-sports/api/api-football))
- Telegram Bot token and Chat ID

---

## 🚀 Setup

1. Clone this repo:

```bash
git clone https://github.com/yourusername/goal-alert-bot.git
cd goal-alert-bot
