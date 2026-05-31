from pathlib import Path
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


def cartella_summary(cartella_output, fonte, sezione=None):
    radice_output = Path(cartella_output)
    if radice_output.name == "charts":
        radice_summary = radice_output.parent / "summary"
    else:
        radice_summary = radice_output / "summary"

    parti = [radice_summary, fonte]
    if sezione:
        parti.append(sezione)

    cartella = Path(*parti)
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def crea_min_max_summary(frame, paesi_esclusi=None, min_paesi=1):
    colonne_vuote = [
        "time_period",
        "data_plot",
        "min_country",
        "min_value",
        "max_country",
        "max_value",
        "countries_count",
        "italy_value",
        "eu27_value",
    ]
    if frame.empty:
        return pd.DataFrame(columns=colonne_vuote)

    paesi_esclusi = set(paesi_esclusi or [])
    dati = frame.dropna(subset=["country_code", "data_plot", "value"]).copy()
    dati["value"] = pd.to_numeric(dati["value"], errors="coerce")
    dati = dati.dropna(subset=["value"])
    paesi = dati.loc[~dati["country_code"].isin(paesi_esclusi)].copy()
    if paesi.empty:
        return pd.DataFrame(columns=colonne_vuote)

    righe = []
    for data_plot, gruppo in paesi.groupby("data_plot"):
        gruppo = gruppo.sort_values(["value", "country_code"]).copy()
        if len(gruppo) < min_paesi:
            continue

        minimo = gruppo.iloc[0]
        massimo = gruppo.iloc[-1]
        righe.append(
            {
                "time_period": minimo["time_period"],
                "data_plot": data_plot,
                "min_country": minimo["country_code"],
                "min_value": float(minimo["value"]),
                "max_country": massimo["country_code"],
                "max_value": float(massimo["value"]),
                "countries_count": int(len(gruppo)),
            }
        )

    summary = pd.DataFrame(righe)
    if summary.empty:
        return pd.DataFrame(columns=colonne_vuote)

    valori_italia = dati.loc[dati["country_code"] == "ITA", ["data_plot", "value"]].rename(columns={"value": "italy_value"})
    valori_eu27 = dati.loc[dati["country_code"] == "EU27_2020", ["data_plot", "value"]].rename(columns={"value": "eu27_value"})
    summary = summary.merge(valori_italia, on="data_plot", how="left")
    summary = summary.merge(valori_eu27, on="data_plot", how="left")
    return summary[colonne_vuote].sort_values("data_plot")


def salva_min_max_summary(frame, cartella_output, fonte, sezione, nome_file, paesi_esclusi=None, min_paesi=1):
    summary = crea_min_max_summary(frame, paesi_esclusi=paesi_esclusi, min_paesi=min_paesi)
    if summary.empty:
        return None, summary

    output = summary.copy()
    output["data_plot"] = pd.to_datetime(output["data_plot"]).dt.strftime("%Y-%m-%d")
    percorso = cartella_summary(cartella_output, fonte, sezione) / f"{Path(nome_file).stem}_min_max.csv"
    output.to_csv(percorso, index=False)
    return percorso, summary


def testo_min_max_ultimo_periodo(summary, suffisso="", decimali=1):
    if summary.empty:
        return ""

    ultimo = summary.sort_values("data_plot").iloc[-1]
    min_value = f"{ultimo['min_value']:.{decimali}f}{suffisso}"
    max_value = f"{ultimo['max_value']:.{decimali}f}{suffisso}"
    return f"Ultimo periodo ({ultimo['time_period']}): min {ultimo['min_country']} {min_value} | max {ultimo['max_country']} {max_value}"
