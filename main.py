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
        data = res.json()["response"]  # This is a dict, not a list for /teams/statistics
        return float(data["goals"]["for"]["average"]["home"] or 0)
    except Exception as e:
        print(f"❌ Error parsing average goals for team {team_id}: {e}")
        return 0.0

def send_daily_home_goal_alert():
    """Main function to find and alert on high-scoring home teams"""
    try:
        fixtures = get_today_fixtures()
        if not fixtures:
            send_telegram("⚽ No fixtures found for today.")
            return

        qualified_matches = []
        
        for fixture in fixtures:
            try:
                # Extract match data
                home_team = fixture["teams"]["home"]["name"]
                away_team = fixture["teams"]["away"]["name"]
                team_id = fixture["teams"]["home"]["id"]
                league_id = fixture["league"]["id"]
                season = fixture["league"]["season"]
                match_time = fixture["fixture"]["date"]

                # Get average goals
                avg_goals = get_home_team_avg_goals(team_id, league_id, season)
                
                if avg_goals > 1.5:
                    # Format match time
                    dt = datetime.fromisoformat(match_time.replace('Z', ''))
                    if match_time.endswith('Z'):
                        dt = dt.replace(tzinfo=timezone.utc)
                    time_str = dt.strftime('%H:%M UTC')
                    
                    # Add match info
                    qualified_matches.append(
                        f"🏟 {home_team} vs {away_team} at {time_str}\n"
                        f"⚽ Avg Home Goals: {avg_goals:.2f}\n"
                        f"🏆 League: {fixture['league']['name']}\n"
                        f"🔗 Fixture ID: {fixture['fixture']['id']}"
                    )
                    
            except KeyError as e:
                print(f"⚠ Missing key in fixture data: {e}")
                continue
            except Exception as e:
                print(f"⚠ Error processing fixture: {e}")
                continue

        # Send results
        if qualified_matches:
            message = ("🔥 Today's Matches (Home Avg Goals > 1.5)\n\n" + 
                      "\n\n".join(qualified_matches))
        else:
            message = "⚽ No matches today with home avg goals > 1.5"
            
        send_telegram(message)
        
    except Exception as e:
        error_msg = f"❌ Critical error in daily alert: {str(e)}"
        print(error_msg)
        send_telegram(error_msg)

if __name__ == "__main__":
    send_daily_home_goal_alert()
