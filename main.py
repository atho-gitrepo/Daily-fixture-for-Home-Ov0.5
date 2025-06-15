import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import telegram

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}

BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"

def get_today_fixtures():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    url = f"{BASE_URL}/fixtures"
    params = {"date": today}
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code != 200:
        print("Error fetching fixtures:", res.text)
        return []
    return res.json().get("response", [])

def get_team_stats(team_id, league_id, season):
    url = f"{BASE_URL}/teams/statistics"
    params = {
        "team": team_id,
        "league": league_id,
        "season": season
    }
    res = requests.get(url, headers=HEADERS, params=params)
    if res.status_code != 200:
        return None
    return res.json().get("response", {})

def filter_fixtures_with_high_home_goals(fixtures):
    filtered = []
    for match in fixtures:
        home_team_id = match['teams']['home']['id']
        league_id = match['league']['id']
        season = match['league']['season']
        team_stats = get_team_stats(home_team_id, league_id, season)

        if not team_stats:
            continue

        home_avg_goals = team_stats.get('goals', {}).get('for', {}).get('average', {}).get('home')
        try:
            if home_avg_goals and float(home_avg_goals) > 1.5:
                filtered.append({
                    "home": match['teams']['home']['name'],
                    "away": match['teams']['away']['name'],
                    "time": match['fixture']['date'],
                    "avg_home_goals": home_avg_goals
                })
        except (ValueError, TypeError):
            continue
    return filtered

def send_to_telegram(matches):
    if not matches:
        message = "⚽ No high-scoring home team matches today."
    else:
        message = "🔥 *Today's Matches with Home Avg Goals > 1.5:*\n\n"
        for match in matches:
            time_str = datetime.fromisoformat(match['time'][:-1]).strftime('%H:%M UTC')
            message += f"🏟 {match['home']} vs {match['away']} at {time_str}\n⚽ Home Avg Goals: {match['avg_home_goals']}\n\n"

    bot = telegram.Bot(token=BOT_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN)

if __name__ == "__main__":
    fixtures = get_today_fixtures()
    high_scoring_matches = filter_fixtures_with_high_home_goals(fixtures)
    send_to_telegram(high_scoring_matches)
