# Kalkulator troskova goriva (Streamlit + Geoapify)

Interaktivna Streamlit aplikacija za:
- racunanje potrosnje i ukupnog troska goriva,
- prikaz rute izmedju dva grada na mapi,
- predloge gradova tokom kucanja (autocomplete),
- procenu vremena putovanja i indikaciju putarine.

## Funkcionalnosti

- Unos polazista i odredista sa predlozima gradova
- Racunanje:
  - ukupne razdaljine
  - potrebne kolicine goriva
  - ukupnog troska goriva
  - procenjenog vremena putovanja
- Prikaz rute na Geoapify mapi
- Podrska za vise tipova goriva
- Opcionalno osvezavanje cena goriva sa interneta (eksperimentalno)

## Tehnologije

- Python
- Streamlit
- Geoapify APIs:
  - Geocoding / Autocomplete
  - Routing
  - Map Tiles
- Leaflet

## Pokretanje lokalno

1. Kloniraj repozitorijum i udji u folder projekta.
2. (Preporuceno) kreiraj virtualno okruzenje.
3. Instaliraj zavisnosti:

```bash
pip install -r requirements.txt
```

4. Kopiraj `.env.example` u `.env` i upisi svoj ključ:

```bash
GEOAPIFY_API_KEY=your_geoapify_api_key_here
```

Geoapify API key mozes dobiti ovde: [Geoapify Getting Started](https://www.geoapify.com/get-started-with-maps-api/).

5. Pokreni aplikaciju:

```bash
streamlit run distance.py
```

## Vazno

- `.env` je u `.gitignore` i ne treba ga commit-ovati.
- Za mapu se koriste Geoapify tile URL-ovi po dokumentaciji: [Geoapify Map Tiles](https://apidocs.geoapify.com/docs/maps/map-tiles/).

## Struktura fajlova

- `distance.py` - glavna Streamlit aplikacija
- `requirements.txt` - Python zavisnosti
- `.env.example` - primer environment promenljivih
- `.gitignore` - ignorisani fajlovi (ukljucujuci `.env`)