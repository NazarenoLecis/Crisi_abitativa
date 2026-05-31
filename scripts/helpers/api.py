import pandas as pd
from io import StringIO
from scripts.helpers.config import EU27_CODES, EUROSTAT_INDICATORS, OECD_INDICATORS
from scripts.helpers.utils import (
    EUROSTAT_BASE_URL,
    OECD_BASE_URL,
    codice_paese_iso3,
    filtra_colonne,
    jsonstat_to_dataframe,
    nome_paese,
    scarica_json,
    scarica_testo,
)


def scarica_eurostat(paesi="IT", indicatori=None, mostra_progresso=False):
    specifiche = indicatori if indicatori is not None else EUROSTAT_INDICATORS
    frames = []
    totale = len(specifiche)
    for posizione, indicatore in enumerate(specifiche, start=1):
        if mostra_progresso:
            nome = indicatore["indicator_name"]
            dataset = indicatore["dataset_code"]
            print(f"[Eurostat {posizione}/{totale}] Scarico {dataset}: {nome}", flush=True)

        parametri = dict(indicatore["filters"])
        parametri["geo"] = paesi
        payload = scarica_json(f"{EUROSTAT_BASE_URL}/{indicatore['dataset_code']}", parametri)
        frame = jsonstat_to_dataframe(payload)
        if frame.empty:
            if mostra_progresso:
                print("  Nessuna osservazione trovata, passo oltre.", flush=True)
            continue

        frame = frame.rename(columns={"geo": "country_code_raw", "time": "time_period"})
        frame["country_code"] = frame["country_code_raw"].map(codice_paese_iso3)
        frame["country_name"] = frame["country_code_raw"].map(nome_paese)
        frame["source"] = indicatore["source"]
        frame["source_dataset"] = indicatore["dataset_code"]
        frame["source_updated"] = payload.get("updated", "")
        frame["indicator_id"] = indicatore["indicator_id"]
        frame["indicator_name"] = indicatore["indicator_name"]
        frame["unit"] = indicatore["unit"]
        frame["frequency"] = indicatore["frequency"]
        frame["theme"] = indicatore["theme"]
        normalizzato = normalizza_colonne(frame)
        frames.append(normalizzato)

        if mostra_progresso:
            print(f"  Fatto: {len(normalizzato):,} osservazioni.", flush=True)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def scarica_ocse(paesi=None, mostra_progresso=False):
    frames = []
    totale = len(OECD_INDICATORS)
    for posizione, indicatore in enumerate(OECD_INDICATORS, start=1):
        if mostra_progresso:
            nome = indicatore["indicator_name"]
            print(f"[OECD {posizione}/{totale}] Scarico: {nome}", flush=True)

        parametri = {"format": "csvfile"}
        parametri.update(indicatore.get("params", {}))
        try:
            testo_csv = scarica_testo(f"{OECD_BASE_URL}/{indicatore['flow']}/{indicatore['key']}", parametri)
        except RuntimeError as errore:
            print(f"Attenzione: salto {indicatore['indicator_id']} per errore API: {errore}")
            continue
        frame = pd.read_csv(StringIO(testo_csv))
        frame = filtra_colonne(frame, indicatore["filters"])
        if frame.empty:
            if mostra_progresso:
                print("  Nessuna osservazione dopo i filtri, passo oltre.", flush=True)
            continue

        frame = frame.rename(columns={"REF_AREA": "country_code", "TIME_PERIOD": "time_period", "OBS_VALUE": "value"})
        if paesi:
            paesi_lista = paesi if isinstance(paesi, list) else [paesi]
            frame = frame.loc[frame["country_code"].isin(paesi_lista)]
        frame["country_name"] = frame["country_code"].map(nome_paese)
        frame["source"] = indicatore["source"]
        frame["source_dataset"] = indicatore["flow"]
        frame["source_updated"] = ""
        frame["indicator_id"] = indicatore["indicator_id"]
        frame["indicator_name"] = indicatore["indicator_name"]
        frame["unit"] = indicatore["unit"]
        frame["frequency"] = indicatore["frequency"]
        frame["theme"] = indicatore["theme"]
        normalizzato = normalizza_colonne(frame)
        frames.append(normalizzato)

        if mostra_progresso:
            print(f"  Fatto: {len(normalizzato):,} osservazioni.", flush=True)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def scarica_italia():
    eurostat = scarica_eurostat("IT")
    ocse = scarica_ocse("ITA")
    return unisci_fonti([eurostat, ocse])


def scarica_unione_europea(mostra_progresso=False):
    paesi_europei = EU27_CODES + ["EU27_2020"]
    dati = scarica_eurostat(paesi_europei, mostra_progresso=mostra_progresso)
    return dati


def scarica_tutto(mostra_progresso=False):
    if mostra_progresso:
        print("Avvio download Eurostat per paesi UE e aggregato EU27.", flush=True)
    europa = scarica_unione_europea(mostra_progresso=mostra_progresso)

    if mostra_progresso:
        print("Avvio download OECD per i paesi disponibili.", flush=True)
    ocse = scarica_ocse(mostra_progresso=mostra_progresso)

    dati = unisci_fonti([europa, ocse])
    if mostra_progresso:
        paesi = dati["country_code"].nunique() if not dati.empty else 0
        indicatori = dati["indicator_id"].nunique() if not dati.empty else 0
        print(f"Download completato: {len(dati):,} osservazioni, {indicatori} indicatori, {paesi} paesi/aggregati.", flush=True)
    return dati


def normalizza_colonne(frame):
    colonne = [
        "source",
        "source_dataset",
        "source_updated",
        "indicator_id",
        "indicator_name",
        "theme",
        "country_code",
        "country_name",
        "time_period",
        "value",
        "unit",
        "frequency",
    ]
    risultato = frame[colonne].copy()
    risultato["time_period"] = risultato["time_period"].astype(str)
    risultato["value"] = pd.to_numeric(risultato["value"], errors="coerce")
    return risultato.dropna(subset=["value"])


def unisci_fonti(frames):
    frames_non_vuoti = [frame for frame in frames if not frame.empty]
    if not frames_non_vuoti:
        return pd.DataFrame()
    risultato = pd.concat(frames_non_vuoti, ignore_index=True)
    return risultato.sort_values(["indicator_id", "country_code", "time_period"])
