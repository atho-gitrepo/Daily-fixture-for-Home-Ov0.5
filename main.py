import os
import requests
import logging
from datetime import date, datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv('API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Check for required credentials
if not API_KEY or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    logging.error("Missing API key or Telegram credentials in environment")
    raise SystemExit("Missing credentials. Please check .env file.")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY,   # API-Football (API-Sports) v3 auth header
    "Accept": "application/json"
}

def fetch_fixtures(today_str):
    """Fetch fixtures for the given date (YYYY-MM-DD)."""
    url = f"{API_URL}/fixtures?date={today_str}&timezone=UTC"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", [])
    except requests.RequestException as e:
        logging.error("Error fetching fixtures: %s", e)
        return []

def fetch_standings(league_id, season):
    """Fetch league standings for a given league ID and season."""
    url = f"{API_URL}/standings?league={league_id}&season={season}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Navigate to the list of standings: response[0]["league"]["standings"][0]
        resp_list = data.get("response")
        if not resp_list:
            logging.warning("No standings returned for league %s, season %s", league_id, season)
            return []
        standings = resp_list[0].get("league", {}).get("standings", [])
        return standings[0] if standings else []
    except requests.RequestException as e:
        logging.error("Error fetching standings for league %s: %s", league_id, e)
        return []

def send_telegram_message(text):
    """Send a message via Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        logging.info("Telegram message sent successfully.")
    except requests.RequestException as e:
        logging.error("Failed to send Telegram message: %s", e)

def main():
    today = date.today().isoformat()  # YYYY-MM-DD
    fixtures = fetch_fixtures(today)
    if not fixtures:
        logging.info("No fixtures found for today: %s", today)
        return

    standings_cache = {}  # Cache standings by (league_id, season)
    message_lines = []

    for item in fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})

        # Extract league and team info
        league_id = league.get("id")
        league_name = league.get("name")
        league_country = league.get("country")
        season = league.get("season")
        home = teams.get("home", {})
        away = teams.get("away", {})
        home_id, home_name = home.get("id"), home.get("name")
        away_id, away_name = away.get("id"), away.get("name")

        if not all([league_id, season, home_id, away_id]):
            logging.warning("Incomplete data for fixture ID %s, skipping.", fixture.get("id"))
            continue

        # Get or fetch standings for this league and season
        cache_key = (league_id, season)
        if cache_key not in standings_cache:
            standings = fetch_standings(league_id, season)
            standings_cache[cache_key] = standings
        else:
            standings = standings_cache[cache_key]

        if not standings:
            continue

        # Identify top 3 and bottom 3 team IDs
        team_ids = [entry.get("team", {}).get("id") for entry in standings if entry.get("team")]
        if len(team_ids) < 3:
            continue  # Not enough teams to determine top/bottom 3
        top3 = team_ids[:3]
        bottom3 = team_ids[-3:]

        # Check if home or away is in top/bottom 3
        if (home_id in top3 or home_id in bottom3 or
            away_id in top3 or away_id in bottom3):
            # Format match info
            match_time_str = fixture.get("date")
            try:
                # Parse and format UTC time
                match_dt = datetime.fromisoformat(match_time_str.rstrip('Z'))
                time_formatted = match_dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                time_formatted = match_time_str or "Unknown time"

            line = f"{home_name} vs {away_name} – {league_name} ({league_country}) – {time_formatted}"
            message_lines.append(line)
            logging.info("Match added to message: %s", line)

    # Send results via Telegram if any matches found
    if message_lines:
        message_text = "Today's fixtures with Top/Bottom 3 teams:\n" + "\n".join(message_lines)
        send_telegram_message(message_text)
    else:
        logging.info("No matches today with a team in the top 3 or bottom 3 of their table.")

if __name__ == "__main__":
    main()