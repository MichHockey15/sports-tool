import streamlit as st
import requests

st.set_page_config(
    page_title="Sports Tool",
    layout="centered",          # better for phones
    initial_sidebar_state="collapsed"
)

# Make text bigger and more readable on mobile
st.markdown("""
    <style>
        .stApp {
            max-width: 100%;
        }
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.3rem !important;
        }
        h3 {
            font-size: 1.3rem !important;
            margin-top: 1.2rem !important;
            margin-bottom: 0.3rem !important;
        }
        p, div {
            font-size: 1.05rem !important;
        }
        .stCaption {
            font-size: 0.95rem !important;
        }
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Sports Tool")
st.caption("NFL + College Football • Best Odds")

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
    st.error("Could not load games. Try again in a minute.")
else:
    st.success(f"{len(data)} games • Best available odds")
    
    for game in data:
        home = game["home_team"]
        away = game["away_team"]
        commence = game.get("commence_time", "")[:16].replace("T", " ")
        
        st.markdown(f"### {away}")
        st.markdown(f"### @ {home}")
        st.caption(f"Start: {commence} UTC")
        
        b = best_odds(game)
        
        # Moneyline
        st.markdown("**Moneyline**")
        if b["ml_away"]:
            st.write(f"{away}: **{b['ml_away'][0]}** ({b['ml_away'][1]})")
        if b["ml_home"]:
            st.write(f"{home}: **{b['ml_home'][0]}** ({b['ml_home'][1]})")
        
        # Spread
        st.markdown("**Spread**")
        if b["spread_away"]:
            st.write(f"{away} {b['spread_away'][1]}: **{b['spread_away'][0]}** ({b['spread_away'][2]})")
        if b["spread_home"]:
            st.write(f"{home} {b['spread_home'][1]}: **{b['spread_home'][0]}** ({b['spread_home'][2]})")
        
        # Total
        st.markdown("**Total**")
        if b["over"]:
            st.write(f"Over {b['over'][1]}: **{b['over'][0]}** ({b['over'][2]})")
        if b["under"]:
            st.write(f"Under {b['under'][1]}: **{b['under'][0]}** ({b['under'][2]})")
        
        st.divider()
