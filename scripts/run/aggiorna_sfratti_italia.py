from io import BytesIO
from pathlib import Path
import re
import unicodedata

import pandas as pd
import requests


URL_SFRATTI_MINISTERO = (
    "https://ucs.interno.gov.it/ucs/allegati/"
    "Download%3AProvvedimenti_esecutivi_di_sfratto_e_richieste_di_esecuzione_dati_2024-23323050.htm"
)
URL_SFRATTI_MIRROR = "https://www.sicetcaserta.it/wp-content/uploads/2025/09/Sfratti-2024-dati-Ministero-Interno.xlsx"

REGIONI_OUTPUT = {
    "Emilia Romagna": "Emilia-Romagna",
    "Friuli Venezia Giulia": "Friuli-Venezia Giulia",
    "Trentino Alto Adige": "Trentino-Alto Adige/Südtirol",
    "Valle d'Aosta": "Valle d'Aosta/Vallée d'Aoste",
}

PROVINCE_ALIAS = {
    "Aosta": ("AO", "Valle d'Aosta/Vallée d'Aoste"),
    "Bolzano": ("BZ", "Bolzano/Bozen"),
    "Forlì e Cesena": ("FC", "Forlì-Cesena"),
    "Forli e Cesena": ("FC", "Forlì-Cesena"),
    "L'aquila": ("AQ", "L'Aquila"),
    "Massa Carrara": ("MS", "Massa-Carrara"),
    "Pesaro Urbino": ("PU", "Pesaro e Urbino"),
    "Reggio Emilia": ("RE", "Reggio nell'Emilia"),
    "Verbania": ("VB", "Verbano-Cusio-Ossola"),
}


def normalizza_testo(valore):
    testo = str(valore).strip()
    testo = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode("ascii")
    testo = testo.lower().replace("'", "")
    return re.sub(r"[^a-z0-9]+", " ", testo).strip()


def scarica_excel_sfratti():
    intestazioni = {"User-Agent": "crisi-abitativa/0.1"}
    for url in [URL_SFRATTI_MINISTERO, URL_SFRATTI_MIRROR]:
        try:
            risposta = requests.get(url, timeout=90, headers=intestazioni)
            risposta.raise_for_status()
            contenuto = risposta.content
            if contenuto[:2] == b"PK":
                return BytesIO(contenuto), url
        except Exception:
            continue

    raise RuntimeError("Non sono riuscito a scaricare l'Excel degli sfratti 2024.")


def numero(valore):
    if pd.isna(valore):
        return None
    return pd.to_numeric(valore, errors="coerce")


def righe_sfratti(percorso_excel, foglio, scala, nomi_da_escludere=None):
    nomi_esclusi = set(nomi_da_escludere or [])
    tabella = pd.read_excel(percorso_excel, sheet_name=foglio, header=None)
    righe = []
    for indice in range(8, len(tabella)):
        territorio = tabella.iat[indice, 0]
        if pd.isna(territorio):
            continue

        territorio = str(territorio).strip()
        if territorio in nomi_esclusi or territorio.startswith("("):
            continue

        necessita_capoluogo = numero(tabella.iat[indice, 1])
        necessita_resto = numero(tabella.iat[indice, 2])
        finita_capoluogo = numero(tabella.iat[indice, 3])
        finita_resto = numero(tabella.iat[indice, 4])
        morosita_capoluogo = numero(tabella.iat[indice, 5])
        morosita_resto = numero(tabella.iat[indice, 6])
        provvedimenti_totali = numero(tabella.iat[indice, 7])

        righe.append(
            {
                "fonte": "Ministero Interno via SICET",
                "anno": 2024,
                "territorio": territorio,
                "scala": scala,
                "necessita_locatore_capoluogo": necessita_capoluogo,
                "necessita_locatore_resto_provincia": necessita_resto,
                "necessita_locatore_totale": necessita_capoluogo + necessita_resto,
                "finita_locazione_capoluogo": finita_capoluogo,
                "finita_locazione_resto_provincia": finita_resto,
                "finita_locazione_totale": finita_capoluogo + finita_resto,
                "morosita_altra_causa_capoluogo": morosita_capoluogo,
                "morosita_altra_causa_resto_provincia": morosita_resto,
                "morosita_altra_causa_totale": morosita_capoluogo + morosita_resto,
                "provvedimenti_totali": provvedimenti_totali,
                "var_provvedimenti_percentuale": numero(tabella.iat[indice, 8]),
                "richieste_esecuzione": numero(tabella.iat[indice, 9]),
                "var_richieste_percentuale": numero(tabella.iat[indice, 10]),
                "sfratti_eseguiti": numero(tabella.iat[indice, 11]),
                "var_eseguiti_percentuale": numero(tabella.iat[indice, 12]),
            }
        )

    return pd.DataFrame(righe)


def prepara_regioni(percorso_excel):
    regioni = righe_sfratti(percorso_excel, "Dati regionali 2024", "regione")
    regioni = regioni.loc[regioni["territorio"] != "Totale Italia"].copy()
    regioni["regione"] = regioni["territorio"].replace(REGIONI_OUTPUT)
    return regioni


def mappa_province_output(summary_province):
    mappa = {}
    for riga in summary_province.itertuples(index=False):
        nome = getattr(riga, "unita_sovracomunale")
        sigla = getattr(riga, "provincia")
        etichetta = getattr(riga, "etichetta")
        if pd.isna(sigla) or not str(sigla).strip():
            trovato = re.search(r"\(([A-Z]{2})\)$", str(etichetta))
            sigla = trovato.group(1) if trovato else ""
        mappa[normalizza_testo(nome)] = (sigla, nome)
    return mappa


def prepara_province(percorso_excel, regioni, summary_province):
    province = righe_sfratti(
        percorso_excel,
        "Dati provinciali 2024",
        "provincia",
        nomi_da_escludere=set(regioni["territorio"]) | {"Totale Italia"},
    )
    mappa = mappa_province_output(summary_province)
    sigle = []
    nomi_output = []
    for territorio in province["territorio"]:
        alias = PROVINCE_ALIAS.get(territorio)
        if alias:
            sigla, nome_output = alias
        else:
            sigla, nome_output = mappa.get(normalizza_testo(territorio), ("", territorio))
        sigle.append(sigla)
        nomi_output.append(nome_output)

    province["provincia"] = sigle
    province["unita_sovracomunale"] = nomi_output
    return province


def prepara_italia(percorso_excel):
    totale = righe_sfratti(percorso_excel, "Dati regionali 2024", "nazione")
    return totale.loc[totale["territorio"] == "Totale Italia"].copy()


def prepara_serie_storica(percorso_excel):
    tabella = pd.read_excel(percorso_excel, sheet_name="Serie storica 2004-2024", header=None)
    righe = []
    for indice in range(6, len(tabella)):
        anno = tabella.iat[indice, 0]
        anno_numero = pd.to_numeric(anno, errors="coerce")
        if pd.isna(anno_numero):
            continue
        righe.append(
            {
                "fonte": "Ministero Interno via SICET",
                "anno": int(anno_numero),
                "necessita_locatore": numero(tabella.iat[indice, 1]),
                "finita_locazione": numero(tabella.iat[indice, 2]),
                "morosita_altra_causa": numero(tabella.iat[indice, 3]),
                "provvedimenti_totali": numero(tabella.iat[indice, 4]),
                "var_provvedimenti_percentuale": numero(tabella.iat[indice, 5]),
                "richieste_esecuzione": numero(tabella.iat[indice, 6]),
                "var_richieste_percentuale": numero(tabella.iat[indice, 7]),
                "sfratti_eseguiti": numero(tabella.iat[indice, 8]),
                "var_eseguiti_percentuale": numero(tabella.iat[indice, 9]),
            }
        )
    return pd.DataFrame(righe)


def colonne_sfratti_merge():
    return [
        "necessita_locatore_capoluogo",
        "necessita_locatore_resto_provincia",
        "necessita_locatore_totale",
        "finita_locazione_capoluogo",
        "finita_locazione_resto_provincia",
        "finita_locazione_totale",
        "morosita_altra_causa_capoluogo",
        "morosita_altra_causa_resto_provincia",
        "morosita_altra_causa_totale",
        "provvedimenti_totali",
        "var_provvedimenti_percentuale",
        "richieste_esecuzione",
        "var_richieste_percentuale",
        "sfratti_eseguiti",
        "var_eseguiti_percentuale",
    ]


def completa_sigle_province(summary_province):
    risultato = summary_province.copy()
    province_mancanti = risultato["provincia"].isna() | (risultato["provincia"].astype(str).str.strip() == "")
    sigle_da_etichetta = risultato.loc[province_mancanti, "etichetta"].astype(str).str.extract(r"\(([A-Z]{2})\)$")[0]
    risultato.loc[province_mancanti, "provincia"] = sigle_da_etichetta
    return risultato


def arricchisci_province(summary_province, province):
    colonne = ["provincia"] + colonne_sfratti_merge()
    dati = province[colonne].copy()
    dati = dati.rename(columns={colonna: f"sfratti_2024_{colonna}" for colonna in colonne_sfratti_merge()})
    risultato = completa_sigle_province(summary_province)
    risultato = risultato.drop(columns=[colonna for colonna in risultato.columns if colonna.startswith("sfratti_2024_")])
    return risultato.merge(dati, on="provincia", how="left")


def arricchisci_regioni(summary_regioni, regioni):
    colonne = ["regione"] + colonne_sfratti_merge()
    dati = regioni[colonne].copy()
    dati = dati.rename(columns={colonna: f"sfratti_2024_{colonna}" for colonna in colonne_sfratti_merge()})
    risultato = summary_regioni.drop(columns=[colonna for colonna in summary_regioni.columns if colonna.startswith("sfratti_2024_")])
    return risultato.merge(dati, on="regione", how="left")


def salva_output():
    excel, url_usato = scarica_excel_sfratti()
    cartella = Path("outputs/italia/summary/locale")
    cartella.mkdir(parents=True, exist_ok=True)
    cartella_dati = Path("italia/sfratti")
    cartella_dati.mkdir(parents=True, exist_ok=True)
    summary_province = pd.read_csv(cartella / "focus_locale_province_omi_mef.csv")
    summary_regioni = pd.read_csv(cartella / "focus_locale_regioni_omi_mef.csv")

    regioni = prepara_regioni(excel)
    excel.seek(0)
    province = prepara_province(excel, regioni, summary_province)
    excel.seek(0)
    italia = prepara_italia(excel)
    excel.seek(0)
    serie_storica = prepara_serie_storica(excel)

    regioni.to_csv(cartella / "sfratti_regioni_2024.csv", index=False)
    province.to_csv(cartella / "sfratti_province_2024.csv", index=False)
    italia.to_csv(cartella / "sfratti_italia_2024.csv", index=False)
    serie_storica.to_csv(cartella / "sfratti_italia_serie_storica_2004_2024.csv", index=False)
    regioni.to_csv(cartella_dati / "sfratti_regioni_2024.csv", index=False)
    province.to_csv(cartella_dati / "sfratti_province_2024.csv", index=False)
    italia.to_csv(cartella_dati / "sfratti_italia_2024.csv", index=False)
    serie_storica.to_csv(cartella_dati / "sfratti_italia_serie_storica_2004_2024.csv", index=False)
    arricchisci_province(summary_province, province).to_csv(cartella / "focus_locale_province_omi_mef.csv", index=False)
    arricchisci_regioni(summary_regioni, regioni).to_csv(cartella / "focus_locale_regioni_omi_mef.csv", index=False)

    print(f"Dati sfratti aggiornati da: {url_usato}")
    print(f"Regioni: {len(regioni)}")
    print(f"Province: {len(province)}")
    print(f"Serie storica nazionale: {len(serie_storica)} anni")


if __name__ == "__main__":
    salva_output()
