import os
import base64
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import altair as alt
from PIL import Image
from pymongo import MongoClient

# ----------------------------
# Configuration
# ----------------------------
st.set_page_config(page_title="Sports Player Dashboard", layout="wide")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB", "sports_dashboard")

# ----------------------------
# Database helpers
# ----------------------------
@st.cache_resource
def get_db_client():
    client = MongoClient(MONGO_URI)
    return client

def get_collections():
    client = get_db_client()
    db = client[DB_NAME]
    return db.players, db.matches, db.practices, db.weight_history

# ----------------------------
# Utility functions
# ----------------------------
def img_to_b64(img: Image.Image) -> str:
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

def b64_to_img(b64: str) -> Image.Image:
    return Image.open(BytesIO(base64.b64decode(b64)))

def save_player(player_obj: dict, mode: str):
    players_col, _, _, weight_col = get_collections()
    if mode == "Create New Player":
        players_col.insert_one(player_obj)
    else:
        players_col.update_one({"player_id": player_obj["player_id"]}, {"$set": player_obj}, upsert=True)

    # also log weight history
    weight_entry = {"player_id": player_obj["player_id"], "date": datetime.utcnow(), "weight_kg": player_obj["weight_kg"]}
    weight_col.insert_one(weight_entry)
    return True

def save_match(match_obj: dict):
    _, matches_col, _, _ = get_collections()
    matches_col.insert_one(match_obj)
    return True

def save_practice(pr_obj: dict):
    _, _, practices_col, _ = get_collections()
    practices_col.insert_one(pr_obj)
    return True

# ----------------------------
# UI - Forms to add data
# ----------------------------
def add_new_record():
    st.header("Add / Update Player & Records")

    # Player form
    with st.form("player_form", clear_on_submit=False):
        mode = st.radio("Mode", ["Create New Player", "Update Existing Player"], horizontal=True)
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Player name", placeholder="e.g. A. Kumar")
            year = st.selectbox("Year", ["1st Year", "2nd Year", "3rd Year", "4th Year"])
            height_cm = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
            weight_kg = st.number_input("Weight (kg)", min_value=30, max_value=150, value=65)
        with col2:
            player_id = st.text_input("Player ID (unique)", placeholder="e.g. roll23")
            photo = st.file_uploader("Upload latest photo (jpg/png)", type=["jpg","jpeg","png"])
            notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Save Player")
        if submitted:
            if not player_id or not name:
                st.error("Please provide a unique Player ID and name.")
            else:
                photo_b64 = None
                if photo is not None:
                    img = Image.open(photo).convert("RGB")
                    img.thumbnail((800,800))
                    photo_b64 = img_to_b64(img)
                player_obj = {
                    "player_id": player_id,
                    "name": name,
                    "year": year,
                    "height_cm": float(height_cm),
                    "weight_kg": float(weight_kg),
                    "photo_b64": photo_b64,
                    "notes": notes,
                    "updated_at": datetime.utcnow()
                }
                save_player(player_obj, mode)
                st.success("Player saved ✅")

    st.markdown("---")

    # Shared Player ID for match + practice
    selected_pid = st.text_input("Enter Player ID for new records", key="main_pid")

    # Match form
    with st.form("match_form"):
        st.subheader("Add Match Record")

    # Shared inputs
        match_date = st.date_input("Match date", value=datetime.utcnow().date())
        sport = st.selectbox("Sport", ["Football", "Basketball", "Cricket", "Kabaddi"], key="sport_choice")
        opponent = st.text_input("Opponent / Event")

    # Conditional fields - auto-update when sport changes
        if sport == "Football":
            stat_value = st.number_input("Goals Scored", min_value=0, value=0)
        elif sport == "Basketball":
            stat_value = st.number_input("Points Scored", min_value=0, value=0)
        elif sport == "Cricket":
            role = st.selectbox("Role", ["Batting", "Bowling"], key="cricket_role")
            stat_value = st.number_input("Runs Scored" if role == "Batting" else "Wickets Taken", min_value=0, value=0)
        elif sport == "Kabaddi":
            role = st.selectbox("Role", ["Attacker", "Defender"], key="kabaddi_role")
            stat_value = st.number_input("Raid Points" if role == "Attacker" else "Tackle Points", min_value=0, value=0)

        score_against = st.number_input("Opponent Score", min_value=0, value=0)
        match_notes = st.text_input("Match notes")

        match_submit = st.form_submit_button("Save Match")
        if match_submit:
            if not selected_pid:
                st.error("Provide Player ID.")
            else:
                match_obj = {
                    "player_id": selected_pid,
                    "date": datetime.combine(match_date, datetime.min.time()),
                    "opponent": opponent,
                    "sport": sport,
                    "stat_value": stat_value,
                    "score_against": int(score_against),
                    "notes": match_notes,
                    "created_at": datetime.utcnow()
                }
                save_match(match_obj)
                st.success("Match record saved ✅")

    st.markdown("---")

    # Practice form
    with st.form("practice_form"):
        st.subheader("Add Practice Session")
        pcol1, pcol2, pcol3 = st.columns(3)
        with pcol1:
            pr_date = st.date_input("Practice date", value=datetime.utcnow().date())
        with pcol2:
            pr_time = st.time_input("Practice time", value=datetime.utcnow().time())
            duration_min = st.number_input("Duration (minutes)", min_value=1, value=60)
        with pcol3:
            focus = st.selectbox("Focus/Type", ["General", "Fitness", "Skill", "Tactics", "Recovery"])
            pr_notes = st.text_area("Notes")
        pr_submit = st.form_submit_button("Save Practice")
        if pr_submit:
            if not selected_pid:
                st.error("Provide Player ID.")
            else:
                pr_obj = {
                    "player_id": selected_pid,
                    "date": datetime.combine(pr_date, pr_time),
                    "duration_min": int(duration_min),
                    "focus": focus,
                    "notes": pr_notes,
                    "created_at": datetime.utcnow()
                }
                save_practice(pr_obj)
                st.success("Practice saved ✅")

# ----------------------------
# Data fetch helpers
# ----------------------------
def fetch_players_df():
    players_col, _, _, _ = get_collections()
    players = list(players_col.find({}))
    return pd.DataFrame(players) if players else pd.DataFrame()

def fetch_matches_df():
    _, matches_col, _, _ = get_collections()
    matches = list(matches_col.find({}))
    return pd.DataFrame(matches) if matches else pd.DataFrame()

def fetch_practices_df():
    _, _, practices_col, _ = get_collections()
    practices = list(practices_col.find({}))
    return pd.DataFrame(practices) if practices else pd.DataFrame()

def fetch_weights_df():
    _, _, _, weight_col = get_collections()
    weights = list(weight_col.find({}))
    return pd.DataFrame(weights) if weights else pd.DataFrame()

# ----------------------------
# Views
# ----------------------------
def view_progress():
    st.header("View Progress")
    player_id = st.text_input("Enter Player ID", key="view_pid")
    if not player_id:
        st.info("Type a Player ID to load the progress table (e.g. roll23)")
        return

    players_df = fetch_players_df()
    matches_df = fetch_matches_df()
    practices_df = fetch_practices_df()
    weights_df = fetch_weights_df()

    player_row = players_df[players_df["player_id"] == player_id]
    if player_row.empty:
        st.error("Player not found — add them in 'Add New Record' first.")
        return

    row = player_row.iloc[0]
    left, right = st.columns([1,2])
    with left:
        st.subheader(row.get("name"))
        st.write(f"Year: {row.get('year')}")
        st.write(f"Height: {row.get('height_cm')} cm")
        st.write(f"Weight: {row.get('weight_kg')} kg")
        if row.get("photo_b64"):
            img = b64_to_img(row.get("photo_b64"))
            st.image(img, use_column_width=True)
    with right:
        st.subheader("Latest Notes")
        st.write(row.get("notes", "—"))

    st.markdown("---")
    # Matches table
    player_matches = matches_df[matches_df["player_id"] == player_id].copy()
    if not player_matches.empty:
        player_matches["date"] = pd.to_datetime(player_matches["date"]).dt.date
        st.subheader("Matches")
        st.dataframe(player_matches.sort_values(by="date", ascending=False))
    else:
        st.info("No match records found.")

    st.markdown("---")
    # Practices table
    player_practices = practices_df[practices_df["player_id"] == player_id].copy()
    if not player_practices.empty:
        player_practices["date"] = pd.to_datetime(player_practices["date"])
        st.subheader("Practice Sessions")
        st.dataframe(player_practices.sort_values(by="date", ascending=False))
    else:
        st.info("No practice records found.")

    st.markdown("---")
    # Weight progress line graph
    pw = weights_df[weights_df["player_id"] == player_id].copy()
    if not pw.empty:
        pw["date"] = pd.to_datetime(pw["date"]).dt.date
        st.subheader("Weight Progress Over Time")
        weight_chart = alt.Chart(pw).mark_line(point=True).encode(
            x="date", y="weight_kg", tooltip=["date","weight_kg"])
        st.altair_chart(weight_chart, use_container_width=True)

# ----------------------------
# Analytics (Performance graphs)
# ----------------------------
def analytics():
    st.header("Analytics & Insights")
    players_df = fetch_players_df()
    matches_df = fetch_matches_df()

    if players_df.empty:
        st.info("No data to show.")
        return

    st.subheader("Player Performance Over Time")
    sel_pid = st.selectbox("Pick player", players_df["player_id"].tolist())
    p_matches = matches_df[matches_df["player_id"] == sel_pid].copy()
    if not p_matches.empty:
        p_matches["date"] = pd.to_datetime(p_matches["date"]).dt.date
        sports = p_matches["sport"].unique()
        if len(sports) > 1:
            sel_sport = st.selectbox("Select sport", sports)
            p_matches = p_matches[p_matches["sport"] == sel_sport]
        else:
            sel_sport = sports[0]
        metric = "stat_value"
        label = {
            "Football": "Goals Scored",
            "Basketball": "Points Scored",
            "Cricket": "Runs/Wickets",
            "Kabaddi": "Raid/Tackle Points"
        }.get(sel_sport, "Performance")
        perf_chart = alt.Chart(p_matches).mark_line(point=True).encode(
            x="date", y=metric, tooltip=["date","opponent",metric])
        st.altair_chart(perf_chart, use_container_width=True)
    else:
        st.info("No match data for selected player.")

# ----------------------------
# Main
# ----------------------------
def main():
    st.title("🏅 Sports Player Dashboard — Enhanced")
    menu = st.radio("Choose view", ["Add New Record", "View Progress", "Analytics"], horizontal=True)
    if menu == "Add New Record":
        add_new_record()
    elif menu == "View Progress":
        view_progress()
    elif menu == "Analytics":
        analytics()

if __name__ == '__main__':
    main()
