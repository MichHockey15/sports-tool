import streamlit as st
import requests
from datetime import datetime, timezone, timedelta

st.set_page_config(
    page_title="Sports Tool",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
        h1 { font-size: 1.8rem !important; }
        h3 { font-size: 1.25rem !important; margin-top: 1.1rem !important; }
        p, div { font-size: 1.05rem !important; }
        .block-container { padding-top: 1.2rem !important; }
    </style>
""", unsafe_allow_html=True)

st.title("Sports Tool")
st.caption("NFL + College Football • Best Odds + Weather")

API_KEY = st.secrets["API_KEY"]

SPORTS = {
    "NFL": "americanfootball_nfl",
    "College Football": "americanfootball_ncaaf"
}

sport = st.selectbox("Sport", list(SPORTS.keys()))
time_filter = st.radio("Show", ["All games", "Next 24 hours"], horizontal=True)

@st.cache_data(ttl=180)
def get_game_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    r = requests.get(url, params=params, timeout=15)
    return r.json() if r.status_code == 200 else None

def get_weather_for_team(team_name):
    try:
        clean_name = team_name
        for word in ["Chiefs", "Eagles", "Cowboys", "49ers", "Packers", "Bears",
                     "Lions", "Vikings", "Saints", "Buccaneers", "Panthers", "Falcons",
                     "Ravens", "Steelers", "Browns", "Bengals", "Bills", "Dolphins",
                     "Jets", "Patriots", "Chargers", "Raiders", "Broncos", "Colts",
                     "Jaguars", "Titans", "Texans", "Commanders", "Giants", "Cardinals",
                     "Seahawks", "Rams", "Bulldogs", "Tigers", "Crimson Tide", "Sooners",
                     "Longhorns", "Buckeyes", "Wolverines", "Nittany Lions", "Seminoles",
                     "Gators", "Volunteers", "Wildcats", "Hurricanes", "Trojans", "Bruins"]:
            clean_name = clean_name.replace(word, "").strip()
        clean_name = clean_name.replace("University of", "").replace("State", "").strip()
        if len(clean_name) < 3:
            clean_name = team_name

        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": clean_name, "count": 1, "language": "en", "format": "json"},
            timeout=6
        ).json()
        if not geo.get("results"):
            return None
        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]
        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,wind_speed_10m",
                "temperature_unit": "fahrenheit", "wind_speed_unit": "mph"
            },
            timeout=6
        ).json()
        current = w.get("current", {})
        return {"temp": current.get("temperature_2m"), "wind": current.get("wind_speed_10m")}
    except Exception:
        return None

def best_odds(game):
    best = {"ml_home": None, "ml_away": None, "spread_home": None, "spread_away": None, "over": None, "under": None}
    home, away = game["home_team"], game["away_team"]
    for book in game.get("bookmakers", []):
        for market in book.get("markets", []):
            if market["key"] == "h2h":
                for o in market["outcomes"]:
                    if o["name"] == home and (best["ml_home"] is None or o["price"] > best["ml_home"][0]):
                        best["ml_home"] = (o["price"], book["title"])
                    elif o["name"] == away and (best["ml_away"] is None or o["price"] > best["ml_away"][0]):
                        best["ml_away"] = (o["price"], book["title"])
            elif market["key"] == "spreads":
                for o in market["outcomes"]:
                    point = o.get("point")
                    if o["name"] == home and (best["spread_home"] is None or o["price"] > best["spread_home"][0]):
                        best["spread_home"] = (o["price"], point, book["title"])
                    elif o["name"] == away and (best["spread_away"] is None or o["price"] > best["spread_away"][0]):
                        best["spread_away"] = (o["price"], point, book["title"])
            elif market["key"] == "totals":
                for o in market["outcomes"]:
                    point = o.get("point")
                    if o["name"] == "Over" and (best["over"] is None or o["price"] > best["over"][0]):
                        best["over"] = (o["price"], point, book["title"])
                    elif o["name"] == "Under" and (best["under"] is None or o["price"] > best["under"][0]):
                        best["under"] = (o["price"], point, book["title"])
    return best

data = get_game_odds(SPORTS[sport])

if not data:
    st.error("Could not load games.")
else:
    now = datetime.now(timezone.utc)
    filtered = []
    for game in data:
        try:
            start = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
            if time_filter == "All games" or (start - now) < timedelta(hours=24):
                filtered.append((start, game))
        except:
            filtered.append((now, game))
    
    filtered.sort(key=lambda x: x[0])
    
    st.success(f"{len(filtered)} games shown")
    
    for start, game in filtered:
        home = game["home_team"]
        away = game["away_team"]
        start_str = start.strftime("%b %d, %I:%M %p UTC")
        
        st.markdown(f"### {away}")
        st.markdown(f"### @ {home}")
        st.caption(f"Start: {start_str}")
        
        weather = get_weather_for_team(home)
        if weather and weather.get("temp") is not None:
            st.write(f"Weather: **{weather['temp']}°F**, wind **{weather['wind']} mph**")
        else:
            st.caption("Weather unavailable")
        
        b = best_odds(game)
        
        st.markdown("**Moneyline**")
        if b["ml_away"]:
            st.write(f"{away}: **{b['ml_away'][0]}** ({b['ml_away'][1]})")
        if b["ml_home"]:
            st.write(f"{home}: **{b['ml_home'][0]}** ({b['ml_home'][1]})")
        
        st.markdown("**Spread**")
        if b["spread_away"]:
            st.write(f"{away} {b['spread_away'][1]}: **{b['spread_away'][0]}** ({b['spread_away'][2]})")
        if b["spread_home"]:
            st.write(f"{home} {b['spread_home'][1]}: **{b['spread_home'][0]}** ({b['spread_home'][2]})")
        
        st.markdown("**Total**")
        if b["over"]:
            st.write(f"Over {b['over'][1]}: **{b['over'][0]}** ({b['over'][2]})")
        if b["under"]:
            st.write(f"Under {b['under'][1]}: **{b['under'][0]}** ({b['under'][2]})")
        
        st.divider()
