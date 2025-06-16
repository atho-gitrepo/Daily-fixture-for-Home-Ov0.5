import os
import requests
import logging
from datetime import date, datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv('API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not API_KEY or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logging.error("Missing credentials in .env file.")
    raise SystemExit("Missing credentials. Check your .env file.")

# Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
    "Accept": "application/json"
}

def fetch_fixtures(today_str):
    url = f"{API_URL}/fixtures?date={today_str}&timezone=UTC"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return res.json().get("response", [])
    except Exception as e:
        logging.error("Error fetching fixtures: %s", e)
        return []

def fetch_standings(league_id, season):
    url = f"{API_URL}/standings?league={league_id}&season={season}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        standings_data = res.json().get("response", [])
        if standings_data:
            return standings_data[0]["league"]["standings"][0]
    except Exception as e:
        logging.error("Error fetching standings for league %s: %s", league_id, e)
    return []

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        logging.info("✅ Message sent to Telegram.")
    except Exception as e:
        logging.error("❌ Failed to send Telegram message: %s", e)

def main():
    today = date.today().isoformat()
    fixtures = fetch_fixtures(today)
    if not fixtures:
        logging.info("No fixtures found for today.")
        return

    standings_cache = {}
    message_lines = []

    for item in fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})

        league_id = league.get("id")
        season = league.get("season")
        home_id = teams.get("home", {}).get("id")
        away_id = teams.get("away", {}).get("id")
        home_name = teams.get("home", {}).get("name")
        away_name = teams.get("away", {}).get("name")

        if not all([league_id, season, home_id, away_id]):
            continue

        cache_key = (league_id, season)
        if cache_key not in standings_cache:
            standings_cache[cache_key] = fetch_standings(league_id, season)

        standings = standings_cache[cache_key]
        if not standings:
            continue

        ranked_team_ids = [entry["team"]["id"] for entry in standings]
        top3 = ranked_team_ids[:3]
        bottom3 = ranked_team_ids[-3:]

        if home_id in top3 or home_id in bottom3 or away_id in top3 or away_id in bottom3:
            match_time = fixture.get("date")
            try:
                match_dt = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
                time_str = match_dt.strftime("%Y-%m-%d %H:%M UTC")
            except:
                time_str = match_time or "Unknown time"

            line = f"{home_name} vs {away_name} – {league.get('name')} ({league.get('country')}) – {time_str}"
            message_lines.append(line)

    if message_lines:
        message = "📊 Today's Top/Bottom 3 Fixtures:\n" + "\n".join(message_lines)
        send_telegram_message(message)
    else:
        logging.info("No top/bottom 3 team matches found.")

if __name__ == "__main__":
    main()
