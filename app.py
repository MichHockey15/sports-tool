import streamlit as st
import requests

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

@st.cache_data(ttl=180)
def get_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        return None
    return r.json()

def get_weather_for_team(team_name):
    """Approximate weather by cleaning the team name first"""
    try:
        # Clean the name: remove common mascot words
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
        
        # Also remove "University of" / "State" noise
        clean_name = clean_name.replace("University of", "").replace("State", "").strip()
        
        if len(clean_name) < 3:
            clean_name = team_name  # fallback
        
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": clean_name, "count": 1, "language": "en", "format": "json"}
        geo = requests.get(geo_url, params=geo_params, timeout=6).json()
        
        if not geo.get("results"):
            return None
        
        lat = geo["results"][0]["latitude"]
        lon = geo["results"][0]["longitude"]
        
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph"
        }
        w = requests.get(weather_url, params=weather_params, timeout=6).json()
        current = w.get("current", {})
        
        return {
            "temp": current.get("temperature_2m"),
            "wind": current.get("wind_speed_10m")
        }
    except:
        return None
        
        return {
            "temp": current.get("temperature_2m"),
            "wind": current.get("wind_speed_10m")
        }
    except:
        return None

def best_odds(game):
    best = {
        "ml_home": None, "ml_away": None,
        "spread_home": None, "spread_away": None,
        "over": None, "under": None
    }
    home = game["home_team"]
    away = game["away_team"]
    
    for book in game.get("bookmakers", []):
        for market in book.get("markets", []):
            if market["key"] == "h2h":
                for o in market["outcomes"]:
                    if o["name"] == home:
                        if best["ml_home"] is None or o["price"] > best["ml_home"][0]:
                            best["ml_home"] = (o["price"], book["title"])
                    elif o["name"] == away:
                        if best["ml_away"] is None or o["price"] > best["ml_away"][0]:
                            best["ml_away"] = (o["price"], book["title"])
            elif market["key"] == "spreads":
                for o in market["outcomes"]:
                    point = o.get("point")
                    if o["name"] == home:
                        if best["spread_home"] is None or o["price"] > best["spread_home"][0]:
                            best["spread_home"] = (o["price"], point, book["title"])
                    elif o["name"] == away:
                        if best["spread_away"] is None or o["price"] > best["spread_away"][0]:
                            best["spread_away"] = (o["price"], point, book["title"])
            elif market["key"] == "totals":
                for o in market["outcomes"]:
                    point = o.get("point")
                    if o["name"] == "Over":
                        if best["over"] is None or o["price"] > best["over"][0]:
                            best["over"] = (o["price"], point, book["title"])
                    elif o["name"] == "Under":
                        if best["under"] is None or o["price"] > best["under"][0]:
                            best["under"] = (o["price"], point, book["title"])
    return best

sport = st.selectbox("Choose sport", list(SPORTS.keys()))

data = get_odds(SPORTS[sport])

if not data:
    st.error("Could not load games.")
else:
    st.success(f"{len(data)} games • Best odds + weather")
    
    for game in data:
        home = game["home_team"]
        away = game["away_team"]
        commence = game.get("commence_time", "")[:16].replace("T", " ")
        
        st.markdown(f"### {away}")
        st.markdown(f"### @ {home}")
        st.caption(f"Start: {commence} UTC")
        
        # Weather (approximate)
        weather = get_weather_for_team(home)
        if weather and weather.get("temp") is not None:
            st.write(f"Weather (approx): **{weather['temp']}°F**, wind **{weather['wind']} mph**")
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
