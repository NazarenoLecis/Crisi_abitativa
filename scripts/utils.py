import time
import pandas as pd
import pycountry
import requests


EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
OECD_BASE_URL = "https://sdmx.oecd.org/public/rest/data"
WATERMARK = "Elaborazione di Nazareno Lecis"


def scarica_json(url, params, tentativi=4):
    ultimo_errore = None
    for tentativo in range(1, tentativi + 1):
        try:
            risposta = requests.get(url, params=params, timeout=90)
            risposta.raise_for_status()
            return risposta.json()
        except Exception as errore:
            ultimo_errore = errore
            time.sleep(min(8, tentativo * 1.5))
    raise RuntimeError(f"Richiesta fallita per {url}: {ultimo_errore}") from ultimo_errore


def scarica_testo(url, params, tentativi=4):
    ultimo_errore = None
    intestazioni = {"User-Agent": "crisi-abitativa/0.1"}
    for tentativo in range(1, tentativi + 1):
        try:
            risposta = requests.get(url, params=params, timeout=120, headers=intestazioni)
            if risposta.status_code == 429:
                ultimo_errore = RuntimeError("rate limit OECD/API 429")
                time.sleep(min(30, tentativo * 5))
                continue
            risposta.raise_for_status()
            return risposta.text
        except Exception as errore:
            ultimo_errore = errore
            time.sleep(min(12, tentativo * 2))
    raise RuntimeError(f"Richiesta fallita per {url}: {ultimo_errore}") from ultimo_errore


def scarica_bytes(url, params=None, tentativi=4):
    ultimo_errore = None
    intestazioni = {"User-Agent": "crisi-abitativa/0.1"}
    parametri = params or {}
    for tentativo in range(1, tentativi + 1):
        try:
            risposta = requests.get(url, params=parametri, timeout=120, headers=intestazioni)
            if risposta.status_code == 429:
                ultimo_errore = RuntimeError("rate limit API 429")
                time.sleep(min(30, tentativo * 5))
                continue
            risposta.raise_for_status()
            return risposta.content
        except Exception as errore:
            ultimo_errore = errore
            time.sleep(min(12, tentativo * 2))
    raise RuntimeError(f"Richiesta fallita per {url}: {ultimo_errore}") from ultimo_errore


def jsonstat_to_dataframe(payload):
    dimensioni = payload["id"]
    dimensioni_size = payload["size"]
    metadati = payload["dimension"]
    codici_dimensioni = {}

    for dimensione in dimensioni:
        mappa_indici = metadati[dimensione]["category"]["index"]
        mappa_codici = {posizione: codice for codice, posizione in mappa_indici.items()}
        codici_dimensioni[dimensione] = [mappa_codici[posizione] for posizione in range(len(mappa_codici))]

    righe = []
    for indice_testo, valore in payload.get("value", {}).items():
        indice = int(indice_testo)
        coordinate = []
        resto = indice
        for dimensione_size in reversed(dimensioni_size):
            coordinate.append(resto % dimensione_size)
            resto //= dimensione_size
        coordinate.reverse()
        riga = {dimensione: codici_dimensioni[dimensione][coordinate[posizione]] for posizione, dimensione in enumerate(dimensioni)}
        riga["value"] = valore
        righe.append(riga)

    return pd.DataFrame(righe)


def codice_paese_iso3(codice):
    if codice in {"EU27_2020", "EA20", "EA19", "EU"}:
        return codice
    if len(codice) == 2:
        paese = pycountry.countries.get(alpha_2=codice.upper())
        if paese:
            return paese.alpha_3
    return codice


def nome_paese(codice):
    if codice == "EU27_2020":
        return "Unione europea (27)"
    if codice in {"EA20", "EA19"}:
        return "Area euro"
    if len(codice) == 2:
        paese = pycountry.countries.get(alpha_2=codice.upper())
        if paese:
            return paese.name
    if len(codice) == 3:
        paese = pycountry.countries.get(alpha_3=codice.upper())
        if paese:
            return paese.name
    return codice


def filtra_colonne(frame, filtri):
    risultato = frame.copy()
    for colonna, valore in filtri.items():
        if colonna not in risultato.columns:
            continue
        if isinstance(valore, list):
            risultato = risultato.loc[risultato[colonna].isin(valore)]
        else:
            risultato = risultato.loc[risultato[colonna] == valore]
    return risultato


def latest_by_country(frame, indicatore):
    dati = frame.loc[frame["indicator_id"] == indicatore].copy()
    if dati.empty:
        return dati
    indici = dati.sort_values("time_period").groupby("country_code").tail(1).index
    return dati.loc[indici]


def latest_value(frame, indicatore, paese="ITA"):
    dati = frame.loc[(frame["indicator_id"] == indicatore) & (frame["country_code"] == paese)].copy()
    if dati.empty:
        return None
    riga = dati.sort_values("time_period").iloc[-1]
    return str(riga["time_period"]), float(riga["value"])


def testo_fonte(frame):
    fonti = sorted(frame["source"].dropna().unique())
    return "Fonte: " + ", ".join(fonti)


def stampa_ultimi_valori(frame):
    ultimi = frame.sort_values("time_period").groupby(["indicator_id", "country_code"]).tail(1)
    colonne = ["indicator_name", "country_code", "time_period", "value", "unit", "source"]
    return ultimi[colonne].sort_values(["indicator_name", "country_code"])
