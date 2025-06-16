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

# Validate credentials
if not API_KEY or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logging.error("Missing API key or Telegram credentials in environment")
    raise SystemExit("Missing credentials. Please check .env file.")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,
    "Accept": "application/json"
}

# Caching team stats to minimize API calls
team_stats_cache = {}

def fetch_fixtures(today_str):
    logging.info(f"Fetching fixtures for date: {today_str}")
    url = f"{API_URL}/fixtures?date={today_str}&timezone=UTC"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        fixtures = res.json().get("response", [])
        logging.info(f"Found {len(fixtures)} fixtures")
        return fixtures
    except requests.RequestException as e:
        logging.error(f"Error fetching fixtures: {e}")
        return []

def fetch_team_avg_goals(team_id, league_id, season):
    cache_key = (team_id, league_id, season)
    if cache_key in team_stats_cache:
        logging.debug(f"Using cached goals for team {team_id}")
        return team_stats_cache[cache_key]

    url = f"{API_URL}/teams/statistics?team={team_id}&league={league_id}&season={season}"
    logging.info(f"Fetching average goals for team {team_id} in league {league_id}, season {season}")
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()

        # The actual response should be under data["response"]
        if not isinstance(data, dict):
            logging.error("Invalid data structure returned (not a dict).")
            return None

        response = data.get("response")
        if not isinstance(response, dict):
            logging.error("Expected 'response' to be a dict but got %s", type(response).__name__)
            return None

        avg_str = response.get("goals", {}).get("for", {}).get("average", {}).get("total")
        avg_float = float(avg_str) if avg_str not in [None, ""] else None

        team_stats_cache[cache_key] = avg_float
        logging.info(f"Team {team_id} average goals: {avg_float}")
        return avg_float

    except Exception as e:
        logging.error(f"Error fetching team stats for {team_id}: {e}")
        return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        logging.info("Sending Telegram message...")
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        logging.info("Telegram message sent successfully.")
    except requests.RequestException as e:
        logging.error(f"Failed to send Telegram message: {e}")

def main():
    today = date.today().isoformat()
    fixtures = fetch_fixtures(today)
    if not fixtures:
        logging.info(f"No fixtures found for today: {today}")
        return

    message_lines = []

    for item in fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})

        # Basic validation
        league_id = league.get("id")
        season = league.get("season")
        home = teams.get("home", {})
        away = teams.get("away", {})
        home_id, home_name = home.get("id"), home.get("name")
        away_id, away_name = away.get("id"), away.get("name")

        if not all([league_id, season, home_id, away_id]):
            logging.warning(f"Incomplete fixture data, skipping fixture ID: {fixture.get('id')}")
            continue

        # Get average goals scored
        home_avg = fetch_team_avg_goals(home_id, league_id, season)
        away_avg = fetch_team_avg_goals(away_id, league_id, season)

        if home_avg is None or away_avg is None:
            logging.warning(f"Missing average goals data for {home_name} or {away_name}, skipping.")
            continue

        if home_avg >= 1.5 or away_avg >= 1.5:
            logging.info(f"Skipping fixture due to goal average: {home_name} ({home_avg}) vs {away_name} ({away_avg})")
            continue

        # Format match info
        match_time_str = fixture.get("date")
        try:
            match_dt = datetime.fromisoformat(match_time_str.rstrip('Z'))
            time_formatted = match_dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            time_formatted = match_time_str or "Unknown time"

        line = f"{home_name} vs {away_name} – {league.get('name')} ({league.get('country')}) – {time_formatted}"
        message_lines.append(line)
        logging.info(f"Match added to message list: {line}")

    # Send message
    if message_lines:
        full_msg = "Today's low-scoring fixtures (Avg Goals < 1.5):\n" + "\n".join(message_lines)
        send_telegram_message(full_msg)
    else:
        logging.info("No matches found with both teams averaging under 1.5 goals.")

if __name__ == "__main__":
    main()
