import math
import re
import os
from urllib.parse import quote_plus

import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

YOUR_API_KEY = os.getenv("GEOAPIFY_API_KEY", "")
TIMEOUT_SECONDS = 12

DEFAULT_FUEL_PRICES_RSD = {
    "Dizel": 212.0,
    "Benzin (BMB 95)": 198.0,
    "Metan (CNG)": 110.0,
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_city_suggestions(query):
    if len(query.strip()) < 2:
        return []

    url = (
        "https://api.geoapify.com/v1/geocode/autocomplete?"
        f"text={quote_plus(query)}&type=city&lang=sr&limit=8&apiKey={YOUR_API_KEY}"
    )
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    features = response.json().get("features", [])
    suggestions = []
    for feature in features:
        props = feature.get("properties", {})
        city = props.get("city") or props.get("name") or ""
        country = props.get("country") or ""
        formatted = props.get("formatted") or ""

        if city and country:
            suggestions.append(f"{city}, {country}")
        elif formatted:
            suggestions.append(formatted)

    return list(dict.fromkeys(suggestions))


@st.cache_data(ttl=3600, show_spinner=False)
def get_coordinates(query):
    url = (
        "https://api.geoapify.com/v1/geocode/search?"
        f"text={quote_plus(query)}&limit=1&apiKey={YOUR_API_KEY}"
    )
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    features = response.json().get("features", [])
    if not features:
        raise ValueError(f"Nisu pronadjene koordinate za: {query}")
    return features[0]["geometry"]["coordinates"]  # [lon, lat]


@st.cache_data(ttl=600, show_spinner=False)
def get_route(start_coords, end_coords):
    # Geoapify Routing API vraca GeoJSON geometriju (LineString).
    url = (
        "https://api.geoapify.com/v1/routing?"
        f"waypoints={start_coords[1]},{start_coords[0]}|{end_coords[1]},{end_coords[0]}"
        f"&mode=drive&apiKey={YOUR_API_KEY}"
    )
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    features = response.json().get("features", [])
    if not features:
        raise ValueError("Ruta nije pronadjena za izabrana odredista.")
    return features[0]


def extract_route_coordinates(route_feature):
    geometry = route_feature.get("geometry", {})
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "LineString":
        return coordinates

    if geometry_type == "MultiLineString":
        merged = []
        for segment in coordinates:
            if isinstance(segment, list):
                merged.extend(segment)
        return merged

    return []


def calculate_fuel_cost(mean_consumption, distance_km, fuel_price_rsd):
    return math.ceil((mean_consumption * distance_km / 100) * fuel_price_rsd)


def city_input_with_suggestions(label, field_key, placeholder):
    pending_key = f"{field_key}_pending"
    if field_key not in st.session_state:
        st.session_state[field_key] = ""

    # Vrednost iz klika na sugestiju se primenjuje pre kreiranja text_input widget-a.
    if pending_key in st.session_state and st.session_state[pending_key]:
        st.session_state[field_key] = st.session_state[pending_key]
        st.session_state[pending_key] = ""

    typed_value = st.text_input(
        label,
        key=field_key,
        placeholder=placeholder,
    )

    suggestions = get_city_suggestions(typed_value) if typed_value else []

    # Sugestije se prikazuju odmah ispod istog input polja.
    if suggestions:
        st.caption("Predlozi (klikni da automatski popunis polje):")
        cols = st.columns(min(2, len(suggestions)))
        for i, suggestion in enumerate(suggestions):
            with cols[i % len(cols)]:
                if st.button(suggestion, key=f"{field_key}_s_{i}", use_container_width=True):
                    st.session_state[pending_key] = suggestion
                    st.rerun()
    return typed_value


def try_fetch_fuel_prices_from_web():
    sources = [
        "https://www.nispetrol.rs/sr_RS/cene-goriva-na-danasnji-dan.html",
        "https://www.amss.org.rs/sve-za-vozace/cene-goriva",
    ]
    extracted_prices = {}
    number_pattern = re.compile(r"(\d{2,3}[,.]\d{1,2})")
    fuel_keywords = {
        "Dizel": ["dizel", "diesel", "evrodizel"],
        "Benzin (BMB 95)": ["benzin", "bmb 95", "eurosuper", "euro premium"],
        "Metan (CNG)": ["metan", "cng"],
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    for url in sources:
        try:
            response = requests.get(url, timeout=TIMEOUT_SECONDS, headers=headers)
            response.raise_for_status()
            text = response.text.lower()
            lines = re.split(r"[\r\n]+", text)
            for fuel_name, keywords in fuel_keywords.items():
                if fuel_name in extracted_prices:
                    continue
                for line in lines:
                    if any(keyword in line for keyword in keywords):
                        match = number_pattern.search(line)
                        if match:
                            extracted_prices[fuel_name] = float(match.group(1).replace(",", "."))
                            break
        except requests.RequestException:
            continue
    return extracted_prices


def render_route_map(route_coordinates, start_coords, end_coords):
    if not route_coordinates:
        st.info("Ruta nema koordinate za prikaz mape.")
        return

    # Leaflet + Geoapify raster tiles iz docs:
    # https://apidocs.geoapify.com/docs/maps/map-tiles/
    route_latlng = [[coord[1], coord[0]] for coord in route_coordinates]
    start_latlng = [start_coords[1], start_coords[0]]
    end_latlng = [end_coords[1], end_coords[0]]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <style>
        html, body, #map {{
          margin: 0;
          padding: 0;
          width: 100%;
          height: 520px;
          border-radius: 10px;
        }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <script>
        const routeLatLng = {route_latlng};
        const startLatLng = {start_latlng};
        const endLatLng = {end_latlng};

        const map = L.map('map').setView(startLatLng, 7);
        const isRetina = L.Browser.retina;
        const baseUrl = "https://maps.geoapify.com/v1/tile/osm-bright/{{z}}/{{x}}/{{y}}.png?apiKey={YOUR_API_KEY}";
        const retinaUrl = "https://maps.geoapify.com/v1/tile/osm-bright/{{z}}/{{x}}/{{y}}@2x.png?apiKey={YOUR_API_KEY}";

        L.tileLayer(isRetina ? retinaUrl : baseUrl, {{
          maxZoom: 20,
          attribution: 'Powered by <a href="https://www.geoapify.com/" target="_blank">Geoapify</a> | <a href="https://openmaptiles.org/" target="_blank">© OpenMapTiles</a> <a href="https://www.openstreetmap.org/copyright" target="_blank">© OpenStreetMap contributors</a>'
        }}).addTo(map);

        const polyline = L.polyline(routeLatLng, {{
          color: '#1565C0',
          weight: 5
        }}).addTo(map);

        L.marker(startLatLng).addTo(map).bindPopup('Polaziste');
        L.marker(endLatLng).addTo(map).bindPopup('Odrediste');

        map.fitBounds(polyline.getBounds(), {{ padding: [25, 25] }});
      </script>
    </body>
    </html>
    """
    st.caption("Geoapify tile mapa (Leaflet).")
    components.html(html, height=530)


st.set_page_config(page_title="Kalkulator troskova goriva", page_icon="⛽", layout="wide")
st.title("Kalkulator troskova goriva")
st.caption("Interaktivni unos gradova, prikaz rute na mapi i izracunavanje troskova goriva.")

if not YOUR_API_KEY:
    st.error(
        "Nedostaje GEOAPIFY_API_KEY. Dodaj API kljuc u .env fajl i restartuj aplikaciju."
    )
    st.stop()

if "fuel_prices" not in st.session_state:
    st.session_state["fuel_prices"] = DEFAULT_FUEL_PRICES_RSD.copy()

left_col, right_col = st.columns([1.15, 1])

with left_col:
    st.subheader("Relacija")
    polazno_odrediste = city_input_with_suggestions(
        "Polazno mesto",
        "origin",
        "npr. Beograd, Srbija",
    )
    krajnje_odrediste = city_input_with_suggestions(
        "Odredisno mesto",
        "destination",
        "npr. Novi Sad, Srbija",
    )
    mean_consumption = st.number_input(
        "Prosecna potrosnja (L/100 km)",
        min_value=0.0,
        value=6.0,
        step=0.1,
    )

with right_col:
    st.subheader("Gorivo")
    fuel_type = st.selectbox("Tip goriva", list(st.session_state["fuel_prices"].keys()))

    if st.button("Povuci cene sa interneta", use_container_width=True):
        fetched = try_fetch_fuel_prices_from_web()
        if fetched:
            st.session_state["fuel_prices"].update(fetched)
            st.success("Cene su uspesno osvezene.")
        else:
            st.warning("Automatsko preuzimanje cena nije uspelo. Rucni unos je i dalje dostupan.")

    default_price = float(st.session_state["fuel_prices"].get(fuel_type, 200.0))
    fuel_price = st.number_input(
        "Cena goriva (RSD/l ili RSD/kg)",
        min_value=0.0,
        value=default_price,
        step=0.1,
        key=f"fuel_price_{fuel_type}",
    )
    st.caption("Napomena: automatsko preuzimanje cena je eksperimentalno.")

calculate = st.button("Izracunaj trosak", type="primary", use_container_width=True)

if calculate:
    try:
        start_coords = get_coordinates(polazno_odrediste)
        end_coords = get_coordinates(krajnje_odrediste)
        route_feature = get_route(start_coords, end_coords)

        route_properties = route_feature.get("properties", {})
        distance_km = route_properties["distance"] / 1000
        travel_seconds = route_properties.get("time", 0)
        has_toll = route_properties.get("toll", False)
        fuel_needed = mean_consumption * distance_km / 100
        total_cost = calculate_fuel_cost(mean_consumption, distance_km, fuel_price)
        travel_hours = travel_seconds / 3600 if travel_seconds else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Ukupna razdaljina", f"{distance_km:.2f} km")
        kpi2.metric("Potrebna kolicina goriva", f"{fuel_needed:.2f} l/kg")
        kpi3.metric("Ukupni trosak", f"{total_cost} RSD")
        kpi4.metric("Procenjeno vreme", f"{travel_hours:.2f} h")

        if has_toll:
            st.info("Ruta ukljucuje deonice sa putarinom.")

        route_coordinates = extract_route_coordinates(route_feature)

        if route_coordinates:
            st.subheader("Putanja na mapi")
            render_route_map(route_coordinates, start_coords, end_coords)
        else:
            st.warning("Geoapify nije vratio podrzanu geometriju rute (LineString/MultiLineString).")

    except Exception as exc:
        st.error(f"Doslo je do greske. Proverite unose i pokusajte ponovo: {exc}")
