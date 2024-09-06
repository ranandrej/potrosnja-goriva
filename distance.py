import streamlit as st
import requests
import math

YOUR_API_KEY=''
# Funkcija za geokodiranje (dobijanje koordinata)
def getcoordinates(query):
    url = f'https://api.geoapify.com/v1/geocode/search?text={query}&apiKey={YOUR_API_KEY}'
    response = requests.get(url)
    coordinates = response.json()["features"][0]["geometry"]["coordinates"]
    return coordinates

# Funkcija za izračunavanje potrošnje goriva
def calculate_fuel_consumption(mean_consumption, distance, fuel_price):
    fuel_consumption = (mean_consumption * distance) / 100 * fuel_price
    return math.ceil(fuel_consumption)

# Naslov aplikacije
st.title("Kalkulator troškova goriva")

# Unos polaznog i krajnjeg odredišta
polazno_odrediste = st.text_input("Unesite polazno odredište:",placeholder="format:Belgrade,Serbia")
krajnje_odrediste = st.text_input("Unesite krajnje odredište:",placeholder="format:Novi Sad,Serbia")

# Unos prosečne potrošnje goriva (u litrama na 100 km)
mean_consumption = st.number_input("Unesite prosečnu potrošnju goriva (L/100km):", min_value=0.0, value=5.6)

# Unos cene goriva po litru
fuel_price = st.number_input("Unesite cenu goriva (RSD/l):", min_value=0, value=194)

# Prikaz kalkulacija ako su uneta odredišta
if st.button("Izračunaj"):
    try:
        # Dohvati koordinate za polazno i krajnje odredište
        koordinate_polazne = getcoordinates(polazno_odrediste)
        koordinate_krajnje = getcoordinates(krajnje_odrediste)
        
        # Prikaz koordinata
        st.write(f"Polazne koordinate: {koordinate_polazne}")
        st.write(f"Krajnje koordinate: {koordinate_krajnje}")

        # URL za rutu između dve tačke (API za rutiranje)
        url = f"https://api.geoapify.com/v1/routing?waypoints={koordinate_polazne[1]},{koordinate_polazne[0]}|{koordinate_krajnje[1]},{koordinate_krajnje[0]}&mode=drive&apiKey={YOUR_API_KEY}"
        response = requests.get(url)
        data = response.json()

        # Prikaz razdaljine
        distance = data["features"][0]["properties"]["distance"] / 1000  # Pretvaranje u kilometre
        st.write(f"Ukupna razdaljina: {distance:.2f} km")

        # Izračunavanje troškova goriva
        cost = calculate_fuel_consumption(mean_consumption, math.ceil(distance), fuel_price)
        st.write(f"Potrebna količina goriva: {mean_consumption * distance / 100:.2f} L")
        st.write(f"Ukupni troškovi goriva: {cost} RSD")
    
    except Exception as e:
        st.error(f"Došlo je do greške,unesite validan grad i zemlju: {e}")
