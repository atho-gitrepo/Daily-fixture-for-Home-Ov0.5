import requests
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {'x-apisports-key': API_KEY}
BASE_URL = 'https://v3.football.api-sports.io'

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        print("✅ Telegram message sent.")
    else:
        print(f"❌ Telegram error: {response.status_code} - {response.text}")

def get_today_fixtures():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    url = f"{BASE_URL}/fixtures?date={today}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"❌ Fixture API error: {res.status_code}")
        return []
    return res.json().get("response", [])

def get_league_standings(league_id, season):
    url = f"{BASE_URL}/standings"
    params = {
        "league": league_id,
        "season": season
    }
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code != 200:
        print(f"❌ Standings API error: {res.status_code} - {res.text}")
        return []

    try:
        standings = res.json().get("response", [])[0]["league"]["standings"][0]
        return standings
    except Exception as e:
        print(f"❌ Error parsing standings: {e}")
        return []

def send_top_bottom_team_fixtures():
    fixtures = get_today_fixtures()
    if not fixtures:
        send_telegram("⚽ No fixtures found for today.")
        return

    # Cache league standings to avoid redundant API calls
    league_cache = {}

    messages = []

    for fixture in fixtures:
        try:
            home_team = fixture["teams"]["home"]
            away_team = fixture["teams"]["away"]
            league_id = fixture["league"]["id"]
            season = fixture["league"]["season"]
            match_time = fixture["fixture"]["date"]

            # Use league standings cache
            key = f"{league_id}-{season}"
            if key not in league_cache:
                league_cache[key] = get_league_standings(league_id, season)
            
            standings = league_cache[key]

            # Find top 3 and bottom 3 team IDs
            top_3_ids = [t["team"]["id"] for t in standings[:3]]
            bottom_3_ids = [t["team"]["id"] for t in standings[-3:]]

            if home_team["id"] in top_3_ids or home_team["id"] in bottom_3_ids or \
               away_team["id"] in top_3_ids or away_team["id"] in bottom_3_ids:

                dt = datetime.fromisoformat(match_time.replace('Z', ''))
                if match_time.endswith('Z'):
                    dt = dt.replace(tzinfo=timezone.utc)
                time_str = dt.strftime('%H:%M UTC')

                messages.append(
                    f"🏟 {home_team['name']} vs {away_team['name']} at {time_str}\n"
                    f"🏆 {fixture['league']['name']} ({fixture['league']['country']})"
                )

        except Exception as e:
            print(f"⚠️ Error processing fixture: {e}")
            continue

    # Send message
    if messages:
        send_telegram("🔥 Today's Fixtures (Top/Bottom 3 Teams)\n\n" + "\n\n".join(messages))
    else:
        send_telegram("ℹ️ No fixtures today with top/bottom 3 teams.")

if __name__ == "__main__":
    send_top_bottom_team_fixtures()