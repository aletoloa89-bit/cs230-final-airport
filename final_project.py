"""
Name: Alessandro Tolo
CS230: Section 8
Data: Airports Around the World (airport-codes.csv + wikipedia-iso-country-codes.csv)

Description:
This program is an interactive Airport World Explorer built with Streamlit.
Users can explore airports worldwide by filtering by continent and airport type.
The app displays a world map, charts, and data tables to answer questions like:
    - Which countries have the most airports?
    - How are airports distributed by elevation?
    - Where are airports located around the world?
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pydeck as pdk

# page config and custom styling [ST4]
st.set_page_config(page_title="Airport Explorer", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
        h1, h2, h3 { color: #1a3c5e; }
    </style>
""", unsafe_allow_html=True)

# load both csv files [PY3]
@st.cache_data
def load_data():
    try:
        airports = pd.read_csv("airport-codes.csv", encoding="utf-8")
        countries = pd.read_csv("wikipedia-iso-country-codes.csv", encoding="utf-8")
    except Exception as e:  # [PY3]
        st.error(f"Could not load data files: {e}")
        st.stop()
    return airports, countries

airports_raw, countries_df = load_data()

# clean the data [DA1]
def clean_airports(df):
    """Clean airports: parse coordinates, convert elevation, drop bad rows."""  # [DA1]
    df = df.copy()
    coords = df["coordinates"].str.split(",", expand=True)
    df["longitude"] = pd.to_numeric(coords[0], errors="coerce")
    df["latitude"]  = pd.to_numeric(coords[1], errors="coerce")
    df["elevation_ft"] = pd.to_numeric(df["elevation_ft"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude", "iso_country"])
    df = df[df["type"] != "closed"]
    df = df[df["elevation_ft"] <= 25000]  # remove clearly bad elevation entries [DA1]
    return df

airports = clean_airports(airports_raw)

# Merge full country names [DA7] — adds country_name column to the DataFrame
countries_df = countries_df.rename(columns={
    "English short name lower case": "country_name",
    "Alpha-2 code": "iso_country"
})
airports = airports.merge(countries_df[["iso_country", "country_name"]], on="iso_country", how="left")

# helper functions
def filter_airports(df, continent="All", airport_type="All"):  # [PY1] default values
    """Filter airports by continent and type. Defaults to showing all."""
    result = df.copy()
    if continent != "All":
        result = result[result["continent"] == continent]
    if airport_type != "All":
        result = result[result["type"] == airport_type]
    return result

def get_stats(df):  # [PY2] returns more than one value
    """Return count and average elevation for a DataFrame."""
    count = len(df)
    avg_elev = round(df["elevation_ft"].mean(), 1)
    return count, avg_elev

# sidebar widgets
st.sidebar.title("✈️ Airport Explorer")
st.sidebar.markdown("---")

# [ST1] Dropdown — continent
continents = ["All"] + sorted(airports["continent"].dropna().unique().tolist())
selected_continent = st.sidebar.selectbox("Select Continent", continents)

# [ST2] Dropdown — airport type
types = ["All"] + sorted(airports["type"].unique().tolist())
selected_type = st.sidebar.selectbox("Select Airport Type", types)

# [ST3] Slider — top N for bar chart
top_n = st.sidebar.slider("Top N Countries (Bar Chart)", min_value=5, max_value=20, value=10)

st.sidebar.markdown("---")
st.sidebar.caption("Data: OurAirports.com + Wikipedia")

# apply filters
# Called with user selections (no defaults used)
filtered = filter_airports(airports, continent=selected_continent, airport_type=selected_type)

# Called with defaults — for a global comparison metric  [PY1] second call using defaults
all_airports = filter_airports(airports)

# page header and summary metrics
st.title("✈️ Airport World Explorer")

count, avg_elev = get_stats(filtered)  # [PY2] unpack two return values
total, _ = get_stats(all_airports)

col1, col2, col3 = st.columns(3)
col1.metric("Airports in View", f"{count:,}")
col2.metric("Avg Elevation (ft)", f"{avg_elev:,}")
col3.metric("Total Airports (Global)", f"{total:,}")

st.markdown("---")

# map section [MAP]
st.header("🗺️ Airport Map")
st.write("Each dot is an airport. Hover to see its name, type, country, and IATA code.")

# [PY5] Dictionary mapping airport type to dot color
type_colors = {
    "large_airport":  [30, 100, 200, 200],
    "medium_airport": [255, 140, 0,   180],
    "small_airport":  [50, 180, 80,   160],
    "heliport":       [200, 50, 50,   160],
    "seaplane_base":  [180, 50, 200,  160],
}

map_df = filtered[["latitude", "longitude", "name", "type", "country_name", "iata_code", "elevation_ft"]].dropna(subset=["latitude", "longitude"]).copy()

# [PY4] List comprehension — assign color based on type dictionary
map_df["color"] = [type_colors.get(t, [120, 120, 120, 160]) for t in map_df["type"]]

map_df = map_df.sample(min(6000, len(map_df)), random_state=42)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position=["longitude", "latitude"],
    get_fill_color="color",
    get_radius=15000,
    pickable=True,
)

tooltip = {
    "html": "<b>{name}</b><br>Type: {type}<br>Country: {country_name}<br>IATA: {iata_code}<br>Elevation: {elevation_ft} ft",
    "style": {"backgroundColor": "#1a3c5e", "color": "white"}
}

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=pdk.ViewState(latitude=20, longitude=0, zoom=1.2),
    tooltip=tooltip,
))
st.markdown("---")

# bar chart [VIZ1]
st.header("📊 Top Countries by Airport Count")

# [DA2] Sort by count
top_countries = (
    filtered["country_name"]
    .value_counts()
    .head(top_n)
    .reset_index()
)
top_countries.columns = ["Country", "Count"]
top_countries = top_countries.sort_values("Count", ascending=True)  # [DA2]

fig1, ax1 = plt.subplots(figsize=(9, 5))
ax1.barh(top_countries["Country"], top_countries["Count"], color="#2c7bb6")
ax1.set_xlabel("Number of Airports")
ax1.set_title(f"Top {top_n} Countries by Airport Count", fontweight="bold", color="#1a3c5e")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
st.pyplot(fig1)
st.markdown("---")

# pie chart [VIZ2]
st.header("🥧 Airport Type Breakdown")

type_counts = filtered["type"].value_counts()

# [PY4] List comprehension for pie chart labels
labels = [t.replace("_", " ").title() for t in type_counts.index]

fig2, ax2 = plt.subplots(figsize=(6, 5))
ax2.pie(
    type_counts.values,
    labels=labels,
    autopct="%1.1f%%",
    colors=["#1a3c5e", "#2c7bb6", "#4dac26", "#fdae61", "#d7191c", "#abd9e9"][:len(type_counts)],
    startangle=140,
    wedgeprops={"edgecolor": "white"}
)
ax2.set_title("Airport Type Distribution", fontweight="bold", color="#1a3c5e")
st.pyplot(fig2)
st.markdown("---")

# elevation histogram [VIZ3]
st.header("⛰️ Elevation Distribution")

fig3, ax3 = plt.subplots(figsize=(9, 4))
ax3.hist(filtered["elevation_ft"].dropna(), bins=40, color="#2c7bb6", edgecolor="white")
ax3.set_xlabel("Elevation (ft)")
ax3.set_ylabel("Number of Airports")
ax3.set_title("Airport Elevation Distribution", fontweight="bold", color="#1a3c5e")
ax3.spines["top"].set_visible(False)
ax3.spines["right"].set_visible(False)
st.pyplot(fig3)
st.markdown("---")

# data tables
st.header("📋 Data Table")

# [DA3] Top 10 highest airports
st.subheader("Top 10 Highest Airports")
top10 = filtered.nlargest(10, "elevation_ft")[["name", "type", "country_name", "elevation_ft", "iata_code"]]  # [DA3]
top10.columns = ["Airport", "Type", "Country", "Elevation (ft)", "IATA"]

# [DA9] Add elevation in meters to the top 10 table
top10["Elev (m)"] = (top10["Elevation (ft)"] * 0.3048).round(1)  # [DA9]

st.dataframe(top10.reset_index(drop=True), use_container_width=True)

# [DA4] Filter: only airports with an IATA code
st.subheader("Airports With IATA Codes")
has_iata = filtered[filtered["iata_code"].notna() & (filtered["iata_code"] != "")]  # [DA4]
st.write(f"{len(has_iata):,} airports in the current filter have an IATA code.")

# [DA5] Filter: large airports above 5,000 ft
st.subheader("High-Altitude Large Airports (≥ 5,000 ft)")
high_large = filtered[(filtered["type"] == "large_airport") & (filtered["elevation_ft"] >= 5000)]  # [DA5]
high_large = high_large[["name", "country_name", "elevation_ft", "iata_code"]].sort_values("elevation_ft", ascending=False)
high_large.columns = ["Airport", "Country", "Elevation (ft)", "IATA"]

if len(high_large) > 0:
    st.dataframe(high_large.reset_index(drop=True), use_container_width=True)
else:
    st.info("No results with current filters.")

st.markdown("---")
st.caption("✈️ Airport World Explorer | CS 230 Final Project | Data: OurAirports.com")
