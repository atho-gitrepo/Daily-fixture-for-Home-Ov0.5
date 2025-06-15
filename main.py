import requests
from dotenv import load_dotenv
import os
from datetime import datetime

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
    today = datetime.utcnow().strftime('%Y-%m-%d')
    url = f"{BASE_URL}/fixtures?date={today}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"❌ Fixture API error: {res.status_code}")
        return []
    return res.json().get("response", [])

def get_home_team_avg_goals(team_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics"
    params = {
        "team": team_id,
        "league": league_id,
        "season": season
    }
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code != 200:
        print(f"❌ Stats API error for team {team_id}: {res.text}")
        return 0.0
    try:
        data = res.json()["response"]
        return float(data["goals"]["for"]["average"]["home"] or 0)
    except Exception as e:
        print(f"❌ Error parsing average goals: {e}")
        return 0.0

def send_daily_home_goal_alert():
    fixtures = get_today_fixtures()
    qualified_matches = []

    for fixture in fixtures:
        home_team = fixture["teams"]["home"]["name"]
        away_team = fixture["teams"]["away"]["name"]
        team_id = fixture["teams"]["home"]["id"]
        league_id = fixture["league"]["id"]
        season = fixture["league"]["season"]
        match_time = fixture["fixture"]["date"]

        avg_goals = get_home_team_avg_goals(team_id, league_id, season)
        if avg_goals > 1.5:
            time_utc = datetime.fromisoformat(match_time[:-1]).strftime('%H:%M UTC')
            qualified_matches.append(
                f"🏟 {home_team} vs {away_team} at {time_utc}\n⚽ Avg Home Goals: {avg_goals:.2f}"
            )

    if qualified_matches:
        message = "🔥 Today's Matches (Home Avg Goals > 1.5):\n\n" + "\n\n".join(qualified_matches)
    else:
        message = "⚽ No matches found today with home avg goals over 1.5."

    send_telegram(message)

if __name__ == "__main__":
    send_daily_home_goal_alert()