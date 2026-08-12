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
        h1 { font-size: 1.75rem !important; margin-bottom: 0.2rem !important; }
        h3 { font-size: 1.2rem !important; margin-top: 0.8rem !important; margin-bottom: 0.15rem !important; }
        p, div { font-size: 1.02rem !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }
        .stCaption { font-size: 0.9rem !important; }
    </style>
""", unsafe_allow_html=True)

st.title("Sports Tool")
st.caption("Best Odds + Weather")

API_KEY = st.secrets["API_KEY"]

SPORTS = {
    "NFL": "americanfootball_nfl",
    "College Football": "americanfootball_ncaaf",
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
    "MLB": "baseball_mlb",
    "UFC": "mma_mixed_martial_arts"
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
        suffixes = ["Chiefs","Eagles","Cowboys","49ers","Packers","Bears","Lions","Vikings","Saints",
                    "Buccaneers","Panthers","Falcons","Ravens","Steelers","Browns","Bengals","Bills",
                    "Dolphins","Jets","Patriots","Chargers","Raiders","Broncos","Colts","Jaguars",
                    "Titans","Texans","Commanders","Giants","Cardinals","Seahawks","Rams","Lakers",
                    "Celtics","Warriors","Bucks","Nets","Heat","Suns","Nuggets","Mavericks","Clippers",
                    "Sixers","Knicks","Bulls","Hawks","Raptors","Jazz","Thunder","Timberwolves",
                    "Pelicans","Kings","Spurs","Rockets","Pacers","Magic","Hornets","Pistons",
                    "Wizards","Grizzlies","Blazers","Maple Leafs","Canadiens","Bruins","Rangers",
                    "Penguins","Capitals","Lightning","Hurricanes","Devils","Islanders","Flyers",
                    "Blue Jackets","Red Wings","Sabres","Senators","Canucks","Flames","Oilers",
                    "Kraken","Jets","Wild","Blackhawks","Blues","Predators","Stars","Avalanche",
                    "Golden Knights","Ducks","Sharks","Coyotes","Yankees","Red Sox","Dodgers",
                    "Cubs","Mets","Cardinals","Braves","Astros","Phillies","Padres","Mariners",
                    "Twins","Guardians","White Sox","Tigers","Royals","Orioles","Rays","Blue Jays",
                    "Angels","Athletics","Rockies","Diamondbacks","Pirates","Reds","Brewers",
                    "Nationals","Marlins"]
        for word in suffixes:
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
    st.error("Could not load games. Some sports may be out of season.")
else:
    now = datetime.now(timezone.utc)
    # Eastern Time offset (handles EDT/EST roughly as -4 hours for summer)
    eastern_offset = timedelta(hours=-4)
    
    filtered = []
    for game in data:
        try:
            start = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00"))
            if time_filter == "All games" or (start - now) < timedelta(hours=24):
                filtered.append((start, game))
        except:
            filtered.append((now, game))
    
    filtered.sort(key=lambda x: x[0])
    st.success(f"{len(filtered)} games")
    
    for start, game in filtered:
        home = game["home_team"]
        away = game["away_team"]
        
        # Convert to Eastern Time for display
        start_et = start + eastern_offset
        start_str = start_et.strftime("%a %b %d • %I:%M %p ET")
        
        st.markdown(f"### {away}")
        st.markdown(f"**@ {home}**")
        st.caption(start_str)
        
        if sport != "UFC":
            weather = get_weather_for_team(home)
            if weather and weather.get("temp") is not None:
                st.write(f"🌤 **{weather['temp']}°F** · Wind {weather['wind']} mph")
            else:
                st.caption("Weather unavailable")
        
        b = best_odds(game)
        
        st.write("")  # small spacer
        st.markdown("**Moneyline**")
        if b["ml_away"]:
            st.write(f"{away}: **{b['ml_away'][0]}**  ·  {b['ml_away'][1]}")
        if b["ml_home"]:
            st.write(f"{home}: **{b['ml_home'][0]}**  ·  {b['ml_home'][1]}")
        
        if sport != "UFC":
            st.markdown("**Spread**")
            if b["spread_away"]:
                st.write(f"{away} {b['spread_away'][1]}: **{b['spread_away'][0]}**  ·  {b['spread_away'][2]}")
            if b["spread_home"]:
                st.write(f"{home} {b['spread_home'][1]}: **{b['spread_home'][0]}**  ·  {b['spread_home'][2]}")
            
            st.markdown("**Total**")
            if b["over"]:
                st.write(f"Over {b['over'][1]}: **{b['over'][0]}**  ·  {b['over'][2]}")
            if b["under"]:
                st.write(f"Under {b['under'][1]}: **{b['under'][0]}**  ·  {b['under'][2]}")
        
        st.divider()
