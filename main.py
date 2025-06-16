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

# Check credentials
if not API_KEY or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logging.error("Missing API key or Telegram credentials in environment")
    raise SystemExit("Missing credentials. Please check .env file.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)

API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
    "Accept": "application/json"
}

# Caches
h2h_cache = {}

def fetch_fixtures(today_str):
    url = f"{API_URL}/fixtures?date={today_str}&timezone=UTC"
    logging.info(f"Fetching fixtures for {today_str}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", [])
    except requests.RequestException as e:
        logging.error("Error fetching fixtures: %s", e)
        return []

def fetch_h2h_avg_goals(home_id, away_id):
    cache_key = (home_id, away_id)
    if cache_key in h2h_cache:
        logging.debug(f"Using cached H2H for {home_id} vs {away_id}")
        return h2h_cache[cache_key]

    url = f"{API_URL}/fixtures/headtohead?h2h={home_id}-{away_id}&last=5"
    logging.info(f"Fetching H2H stats for {home_id} vs {away_id}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        matches = data.get("response", [])
        if not matches:
            logging.warning(f"No H2H data found for teams {home_id} vs {away_id}")
            return None

        total_goals = 2
        for match in matches:
            goals = match.get("goals", {})
            total_goals += (goals.get("home", 2) or 2) + (goals.get("away", 2) or 2)

        avg_goals = total_goals / len(matches)
        h2h_cache[cache_key] = avg_goals
        logging.info(f"Average H2H goals for {home_id} vs {away_id}: {avg_goals:.2f}")
        return avg_goals

    except Exception as e:
        logging.error(f"Error fetching H2H stats for {home_id} vs {away_id}: {e}")
        return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        logging.info("Telegram message sent successfully.")
    except requests.RequestException as e:
        logging.error("Failed to send Telegram message: %s", e)

def main():
    today = date.today().isoformat()
    fixtures = fetch_fixtures(today)
    if not fixtures:
        logging.info("No fixtures found for today: %s", today)
        return

    message_lines = []

    for item in fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})

        league_name = league.get("name")
        league_country = league.get("country")
        season = league.get("season")

        home = teams.get("home", {})
        away = teams.get("away", {})
        home_id, home_name = home.get("id"), home.get("name")
        away_id, away_name = away.get("id"), away.get("name")

        if not all([home_id, away_id, league_name, league_country]):
            logging.warning("Incomplete fixture data, skipping.")
            continue

        h2h_avg = fetch_h2h_avg_goals(home_id, away_id)
        if h2h_avg is None:
            logging.warning(f"Missing H2H average goals data for {home_name} vs {away_name}, skipping.")
            continue

        if h2h_avg >= 1.5:
            logging.info(f"Skipping {home_name} vs {away_name}, H2H avg goals {h2h_avg:.2f} >= 1.5")
            continue

        match_time_str = fixture.get("date")
        try:
            match_dt = datetime.fromisoformat(match_time_str.rstrip('Z'))
            time_formatted = match_dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            time_formatted = match_time_str or "Unknown time"

        line = f"{home_name} vs {away_name} – {league_name} ({league_country}) – {time_formatted} – H2H Avg Goals: {h2h_avg:.2f}"
        message_lines.append(line)
        logging.info("Match added: %s", line)

    if message_lines:
        message_text = "Today's fixtures with H2H avg goals under 1.5:\n\n" + "\n".join(message_lines)
        send_telegram_message(message_text)
    else:
        logging.info("No low-goal H2H matches found for today.")

if __name__ == "__main__":
    main()
