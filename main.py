import os
import requests
import logging
from datetime import date, datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv('API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Check credentials
if not API_KEY or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logging.error("Missing credentials in .env file.")
    raise SystemExit("Missing credentials. Please check your .env file.")

API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
    "Accept": "application/json"
}

def fetch_fixtures(today_str):
    url = f"{API_URL}/fixtures?date={today_str}&timezone=UTC"
    logging.info(f"Fetching fixtures for {today_str} from {url}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json().get("response", [])
        logging.info(f"✅ {len(data)} fixtures retrieved.")
        return data
    except Exception as e:
        logging.error(f"❌ Error fetching fixtures: {e}")
        return []

def fetch_standings(league_id, season):
    url = f"{API_URL}/standings?league={league_id}&season={season}"
    logging.info(f"Fetching standings for League ID: {league_id}, Season: {season}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        standings_data = res.json().get("response", [])
        if standings_data:
            logging.info(f"✅ Standings fetched for League {league_id}")
            return standings_data[0]["league"]["standings"][0]
        else:
            logging.warning(f"No standings found for League ID {league_id}, Season {season}")
    except Exception as e:
        logging.error(f"❌ Error fetching standings: {e}")
    return []

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    logging.info("Sending message to Telegram...")
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        logging.info("✅ Message successfully sent to Telegram.")
    except Exception as e:
        logging.error(f"❌ Failed to send Telegram message: {e}")

def main():
    today = date.today().isoformat()
    logging.info(f"Script started for date: {today}")

    fixtures = fetch_fixtures(today)
    if not fixtures:
        logging.info("No fixtures available for today. Exiting.")
        return

    standings_cache = {}
    message_lines = []

    for item in fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})

        league_id = league.get("id")
        season = league.get("season")
        home = teams.get("home", {})
        away = teams.get("away", {})
        home_id, home_name = home.get("id"), home.get("name")
        away_id, away_name = away.get("id"), away.get("name")

        fixture_id = fixture.get("id")
        logging.info(f"Processing fixture ID {fixture_id}: {home_name} vs {away_name} (League ID {league_id})")

        if not all([league_id, season, home_id, away_id]):
            logging.warning(f"Incomplete data for fixture ID {fixture_id}, skipping.")
            continue

        cache_key = (league_id, season)
        if cache_key not in standings_cache:
            logging.info(f"Standings not cached for League {league_id}, Season {season}. Fetching...")
            standings_cache[cache_key] = fetch_standings(league_id, season)

        standings = standings_cache[cache_key]
        if not standings:
            logging.warning(f"No standings available for fixture ID {fixture_id}, skipping.")
            continue

        ranked_ids = [entry["team"]["id"] for entry in standings if "team" in entry]
        if len(ranked_ids) < 6:
            logging.warning(f"Less than 6 teams in standings for League {league_id}, skipping fixture.")
            continue

        top3 = ranked_ids[:3]
        bottom3 = ranked_ids[-3:]

        if home_id in top3 or home_id in bottom3 or away_id in top3 or away_id in bottom3:
            match_time = fixture.get("date")
            try:
                match_dt = datetime.fromisoformat(match_time.replace("Z", "+00:00"))
                time_str = match_dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception as e:
                logging.warning(f"Failed to parse time for fixture ID {fixture_id}: {e}")
                time_str = match_time or "Unknown time"

            line = f"{home_name} vs {away_name} – {league.get('name')} ({league.get('country')}) – {time_str}"
            logging.info(f"✅ Match added: {line}")
            message_lines.append(line)
        else:
            logging.info(f"Fixture {fixture_id} does not involve Top/Bottom 3 teams.")

    if message_lines:
        message = "📊 Today's Fixtures with Top/Bottom 3 Teams:\n" + "\n".join(message_lines)
        logging.info(f"Total matches to notify: {len(message_lines)}")
        send_telegram_message(message)
    else:
        logging.info("No qualifying matches to notify today.")

if __name__ == "__main__":
    main()
