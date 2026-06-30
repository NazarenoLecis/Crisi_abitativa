from io import BytesIO
import json
import re
import textwrap
import copy
import unicodedata
import urllib3
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import pandas as pd
import requests
from scripts.helpers.grafici import COLORE_EU27, COLORE_PRINCIPALE
from scripts.helpers.paesi import cartella_paese, normalizza_codici_paesi, profilo_paese
from scripts.helpers.utils import WATERMARK, cartella_summary


FRANCIA_DVF_URL = "https://object.files.data.gouv.fr/data-pipeline-open/dvf/stats_whole_period.csv"
FRANCIA_AFFITTI_URL = (
    "https://static.data.gouv.fr/resources/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025/"
    "20251211-145010/pred-app-mef-dhup.csv"
)
FRANCIA_REDDITI_URL = (
    "https://static.data.gouv.fr/resources/niveau-de-vie-median/20260414-112033/mediane-niveau-vie-com.csv"
)
FRANCIA_GEOJSON_URL = "https://france-geojson.gregoiredavid.fr/repo/communes.geojson"
GERMANIA_GEOJSON_URL = "https://raw.githubusercontent.com/m-ad/geofeatures-ags-germany/master/geojson/counties.json"
BERLINO_AFFITTI_WFS_URL = "https://gdi.berlin.de/services/wfs/wa_01_angebotsmieten"
BERLINO_AFFITTI_LAYER = "wa_01_angebotsmieten:wa_01_2022"
BERLINO_ORTSTEILE_GEOJSON_URL = "https://tsb-opendata.s3.eu-central-1.amazonaws.com/ortsteile/lor_ortsteile.geojson"
IMMOBILIENPREISE_BASE_URL = "https://www.immobilienpreise.org"
MIETE_AKTUELL_BASE_URL = "https://www.miete-aktuell.de/immobilienpreise-quadratmeterpreise"
INKAR_BASE_URL = "https://www.inkar.de"
USER_AGENT = "crisi-abitativa/0.1"
BROWSER_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36"
LETTERE_PREZZI_LANDKREISE = list("abcdefghijklmnopqrstuvwxyz") + ["ue", "ae", "oe"]

FONTE_FRANCIA = (
    "data.gouv.fr: DVF stats whole period, Carte des loyers 2025, niveau de vie median; "
    "france-geojson.gregoiredavid.fr"
)
FONTE_GERMANIA = (
    "BBSR INKAR: Angebotsmieten 2024, Haushaltseinkommen 2022; geofeatures-ags-germany"
)
FONTE_GERMANIA_PREZZI = (
    "immobilienpreise.org: Wohnungspreis pro mq 2026; BBSR INKAR Haushaltseinkommen 2022; "
    "geofeatures-ags-germany"
)
FONTE_BERLINO_QUARTIERI = (
    "Wohnatlas Berlin Angebotsmieten 2022; BBSR INKAR Haushaltseinkommen 2022"
)
FONTE_BERLINO_PREZZI = (
    "miete-aktuell.de: prezzi di offerta residenziali 2026 per Ortsteil; ODIS Berlin Ortsteile; "
    "BBSR INKAR Haushaltseinkommen 2022"
)

MAPPE_FRANCIA = [
    (
        "affitto_mq_mese",
        "Affitti annunciati per appartamenti: comuni francesi, 2025",
        "euro/mq/mese",
        "francia_comuni_affitti_mq_mese.png",
        False,
        1,
    ),
    (
        "prezzo_mq",
        "Prezzi di vendita residenziali DVF: comuni francesi",
        "euro/mq",
        "francia_comuni_prezzi_vendita_mq.png",
        False,
        0,
    ),
    (
        "anni_reddito_per_80mq",
        "Prezzo stimato di 80 mq in anni di reddito mediano: comuni francesi",
        "anni di reddito",
        "francia_comuni_anni_reddito_per_80mq.png",
        False,
        1,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Affitto stimato di 40 mq sul reddito mediano: comuni francesi",
        "% del reddito",
        "francia_comuni_affitto_40mq_reddito.png",
        True,
        0,
    ),
]

MAPPE_GERMANIA = [
    (
        "affitto_mq_mese",
        "Affitti annunciati per appartamenti: Kreise e citta-distretto tedesche, 2024",
        "euro/mq/mese",
        "germania_kreise_affitti_mq_mese.png",
        False,
        1,
    ),
    (
        "prezzo_mq",
        "Prezzi di vendita annunciati per appartamenti: Kreise e citta-distretto tedesche, 2026",
        "euro/mq",
        "germania_kreise_prezzi_vendita_mq.png",
        False,
        0,
    ),
    (
        "anni_reddito_per_80mq",
        "Prezzo stimato di 80 mq in anni di reddito disponibile: Kreise e citta-distretto tedesche",
        "anni di reddito",
        "germania_kreise_anni_reddito_per_80mq.png",
        False,
        1,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Affitto stimato di 40 mq sul reddito disponibile: Kreise e citta-distretto tedesche",
        "% del reddito",
        "germania_kreise_affitto_40mq_reddito.png",
        True,
        0,
    ),
]

MAPPE_PARIGI = [
    (
        "affitto_mq_mese",
        "Affitti annunciati per appartamenti: arrondissement di Parigi, 2025",
        "euro/mq/mese",
        "parigi_affitti_mq_mese.png",
        False,
        1,
    ),
    (
        "prezzo_mq",
        "Prezzi di vendita residenziali DVF: arrondissement di Parigi",
        "euro/mq",
        "parigi_prezzi_vendita_mq.png",
        False,
        0,
    ),
    (
        "anni_reddito_per_80mq",
        "Prezzo stimato di 80 mq sul reddito mediano di Parigi: arrondissement",
        "anni di reddito",
        "parigi_anni_reddito_per_80mq.png",
        False,
        1,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Affitto stimato di 40 mq sul reddito mediano di Parigi: arrondissement",
        "% del reddito",
        "parigi_affitto_40mq_reddito.png",
        True,
        0,
    ),
]

MAPPE_BERLINO = [
    (
        "affitto_mq_mese",
        "Affitti annunciati per appartamenti: quartieri statistici di Berlino, 2022",
        "euro/mq/mese",
        "berlino_affitti_mq_mese.png",
        False,
        1,
    ),
    (
        "prezzo_mq",
        "Prezzi di vendita residenziali annunciati: Ortsteile di Berlino, 2026",
        "euro/mq",
        "berlino_prezzi_vendita_mq.png",
        False,
        0,
    ),
    (
        "anni_reddito_per_80mq",
        "Prezzo stimato di 80 mq sul reddito disponibile medio di Berlino: Ortsteile",
        "anni di reddito",
        "berlino_anni_reddito_per_80mq.png",
        False,
        1,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Affitto stimato di 40 mq sul reddito disponibile medio di Berlino: quartieri statistici",
        "% del reddito",
        "berlino_affitto_40mq_reddito.png",
        True,
        0,
    ),
]

FOCUS_CITTA = {
    "FRA": {
        "codice": "75056",
        "nome": "Parigi",
        "prefisso_file": "parigi_",
        "prefisso_nome_file": "francia_comuni_",
    },
    "DEU": {
        "codice": "11000",
        "nome": "Berlino",
        "prefisso_file": "berlino_",
        "prefisso_nome_file": "germania_kreise_",
    },
}

AGGREGAZIONI_COMUNI_FRANCIA = {
    "75056": {"nome": "Paris", "codici": [f"751{numero:02d}" for numero in range(1, 21)]},
    "13055": {"nome": "Marseille", "codici": [f"132{numero:02d}" for numero in range(1, 17)]},
    "69123": {"nome": "Lyon", "codici": [f"6938{numero}" for numero in range(1, 10)]},
}

NOMI_DIPARTIMENTI_FRANCESI = {
    "01": "Ain",
    "02": "Aisne",
    "03": "Allier",
    "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes",
    "06": "Alpes-Maritimes",
    "07": "Ardeche",
    "08": "Ardennes",
    "09": "Ariege",
    "10": "Aube",
    "11": "Aude",
    "12": "Aveyron",
    "13": "Bouches-du-Rhone",
    "14": "Calvados",
    "15": "Cantal",
    "16": "Charente",
    "17": "Charente-Maritime",
    "18": "Cher",
    "19": "Correze",
    "2A": "Corse-du-Sud",
    "2B": "Haute-Corse",
    "21": "Cote-d'Or",
    "22": "Cotes-d'Armor",
    "23": "Creuse",
    "24": "Dordogne",
    "25": "Doubs",
    "26": "Drome",
    "27": "Eure",
    "28": "Eure-et-Loir",
    "29": "Finistere",
    "30": "Gard",
    "31": "Haute-Garonne",
    "32": "Gers",
    "33": "Gironde",
    "34": "Herault",
    "35": "Ille-et-Vilaine",
    "36": "Indre",
    "37": "Indre-et-Loire",
    "38": "Isere",
    "39": "Jura",
    "40": "Landes",
    "41": "Loir-et-Cher",
    "42": "Loire",
    "43": "Haute-Loire",
    "44": "Loire-Atlantique",
    "45": "Loiret",
    "46": "Lot",
    "47": "Lot-et-Garonne",
    "48": "Lozere",
    "49": "Maine-et-Loire",
    "50": "Manche",
    "51": "Marne",
    "52": "Haute-Marne",
    "53": "Mayenne",
    "54": "Meurthe-et-Moselle",
    "55": "Meuse",
    "56": "Morbihan",
    "57": "Moselle",
    "58": "Nievre",
    "59": "Nord",
    "60": "Oise",
    "61": "Orne",
    "62": "Pas-de-Calais",
    "63": "Puy-de-Dome",
    "64": "Pyrenees-Atlantiques",
    "65": "Hautes-Pyrenees",
    "66": "Pyrenees-Orientales",
    "67": "Bas-Rhin",
    "68": "Haut-Rhin",
    "69": "Rhone",
    "70": "Haute-Saone",
    "71": "Saone-et-Loire",
    "72": "Sarthe",
    "73": "Savoie",
    "74": "Haute-Savoie",
    "75": "Paris",
    "76": "Seine-Maritime",
    "77": "Seine-et-Marne",
    "78": "Yvelines",
    "79": "Deux-Sevres",
    "80": "Somme",
    "81": "Tarn",
    "82": "Tarn-et-Garonne",
    "83": "Var",
    "84": "Vaucluse",
    "85": "Vendee",
    "86": "Vienne",
    "87": "Haute-Vienne",
    "88": "Vosges",
    "89": "Yonne",
    "90": "Territoire de Belfort",
    "91": "Essonne",
    "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne",
    "95": "Val-d'Oise",
}


def richiesta_get(url, timeout=120, params=None):
    risposta = requests.get(url, timeout=timeout, params=params, headers={"User-Agent": USER_AGENT})
    risposta.raise_for_status()
    return risposta


def scarica_html(url, timeout=45):
    try:
        risposta = requests.get(url, timeout=timeout, headers={"User-Agent": BROWSER_USER_AGENT})
        risposta.raise_for_status()
    except requests.RequestException:
        return ""
    return risposta.text


def leggi_csv_url(url, **opzioni):
    risposta = richiesta_get(url, timeout=180)
    return pd.read_csv(BytesIO(risposta.content), **opzioni)


def numero_con_virgola(valore):
    testo = str(valore).strip().replace("\xa0", "")
    testo = testo.replace(",", ".")
    return pd.to_numeric(testo, errors="coerce")


def numero_tedesco(valore):
    testo = str(valore).strip().replace("\xa0", " ")
    if testo.lower() in {"", "nan"} or "k.a" in testo.lower():
        return pd.NA
    trovato = re.search(r"([0-9][0-9.]*,?[0-9]*)", testo)
    if not trovato:
        return pd.NA
    numero = trovato.group(1).replace(".", "").replace(",", ".")
    return pd.to_numeric(numero, errors="coerce")


def testo_ascii_tedesco(testo):
    testo = str(testo).strip()
    sostituzioni = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
    for originale, sostituto in sostituzioni.items():
        testo = testo.replace(originale, sostituto)
    return unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode("ascii")


def slug_tedesco(testo):
    testo = testo_ascii_tedesco(testo)
    testo = testo.replace("i.d.OPf.", "in der Oberpfalz").replace("i.d. OPf.", "in der Oberpfalz")
    testo = re.sub(r"\((.*?)\)", r" \1 ", testo)
    testo = re.sub(r"[^A-Za-z0-9]+", "-", testo).strip("-")
    return testo.lower()


def slug_miete_aktuell(testo):
    testo = testo_ascii_tedesco(testo)
    testo = re.sub(r"\((.*?)\)", r" \1 ", testo)
    testo = re.sub(r"[^A-Za-z0-9]+", "-", testo).strip("-")
    return testo


def chiave_area_tedesca(testo):
    testo = testo_ascii_tedesco(testo).lower()
    testo = re.sub(r"\b(stadt|landkreis|kreisfreie|kreis|lkr)\b", " ", testo)
    testo = re.sub(r"[^a-z0-9]+", " ", testo)
    return re.sub(r"\s+", " ", testo).strip()


def chiavi_area_tedesca(testo):
    base = chiave_area_tedesca(testo)
    chiavi = {base}
    parole_da_rimuovere = ["staedteregion", "regionalverband", "region"]
    for parola in parole_da_rimuovere:
        pulita = re.sub(rf"\b{parola}\b", " ", base)
        pulita = re.sub(r"\s+", " ", pulita).strip()
        if pulita:
            chiavi.add(pulita)
    return [chiave for chiave in chiavi if chiave]


def codice_francese(valore):
    testo = str(valore).strip()
    if testo.lower() in {"", "nan"}:
        return ""
    if re.fullmatch(r"\d+", testo):
        return testo.zfill(5)
    return testo.upper()


def carica_affitti_francia():
    frame = leggi_csv_url(FRANCIA_AFFITTI_URL, sep=";", encoding="latin1", dtype={"INSEE_C": str})
    dati = frame[["INSEE_C", "LIBGEO", "loypredm2", "nbobs_com"]].copy()
    dati["codice_area"] = dati["INSEE_C"].map(codice_francese)
    dati["comune"] = dati["LIBGEO"].astype(str).str.strip()
    dati["affitto_mq_mese"] = dati["loypredm2"].map(numero_con_virgola)
    dati["osservazioni_affitto"] = pd.to_numeric(dati["nbobs_com"], errors="coerce")
    dati = dati[["codice_area", "comune", "affitto_mq_mese", "osservazioni_affitto"]]
    return aggiungi_aggregati_francia(dati, "affitto_mq_mese", "osservazioni_affitto")


def carica_vendite_francia():
    colonne = [
        "code_geo",
        "libelle_geo",
        "echelle_geo",
        "nb_ventes_whole_apt_maison",
        "med_prix_m2_whole_apt_maison",
    ]
    frame = leggi_csv_url(FRANCIA_DVF_URL, dtype={"code_geo": str}, usecols=colonne)
    dati = frame.loc[frame["echelle_geo"] == "commune"].copy()
    dati["codice_area"] = dati["code_geo"].map(codice_francese)
    dati["comune"] = dati["libelle_geo"].astype(str).str.strip()
    dati["prezzo_mq"] = pd.to_numeric(dati["med_prix_m2_whole_apt_maison"], errors="coerce")
    dati["vendite_dvf"] = pd.to_numeric(dati["nb_ventes_whole_apt_maison"], errors="coerce")
    dati = dati[["codice_area", "comune", "prezzo_mq", "vendite_dvf"]]
    return aggiungi_aggregati_francia(dati, "prezzo_mq", "vendite_dvf")


def valore_pesato(gruppo, colonna_valore, colonna_peso):
    valori = pd.to_numeric(gruppo[colonna_valore], errors="coerce")
    pesi = pd.to_numeric(gruppo[colonna_peso], errors="coerce")
    validi = valori.notna() & pesi.notna() & (pesi > 0)
    if validi.any():
        return float((valori[validi] * pesi[validi]).sum() / pesi[validi].sum())

    valori_validi = valori.dropna()
    if valori_validi.empty:
        return None
    return float(valori_validi.median())


def aggiungi_aggregati_francia(dati, colonna_valore, colonna_peso):
    righe = []
    risultato = dati.copy()
    for codice, profilo in AGGREGAZIONI_COMUNI_FRANCIA.items():
        gruppo = risultato.loc[risultato["codice_area"].isin(profilo["codici"])].copy()
        if gruppo.empty:
            continue
        righe.append(
            {
                "codice_area": codice,
                "comune": profilo["nome"],
                colonna_valore: valore_pesato(gruppo, colonna_valore, colonna_peso),
                colonna_peso: pd.to_numeric(gruppo[colonna_peso], errors="coerce").sum(),
            }
        )

    if not righe:
        return risultato

    risultato = risultato.loc[~risultato["codice_area"].isin(set(AGGREGAZIONI_COMUNI_FRANCIA))].copy()
    return pd.concat([risultato, pd.DataFrame(righe)], ignore_index=True)


def carica_redditi_francia():
    frame = leggi_csv_url(FRANCIA_REDDITI_URL, dtype={"code_com": str})
    frame["anno"] = pd.to_numeric(frame["annee"], errors="coerce")
    anno = frame["anno"].max()
    dati = frame.loc[frame["anno"] == anno].copy()
    dati["codice_area"] = dati["code_com"].map(codice_francese)
    dati["reddito_annuo"] = pd.to_numeric(dati["valeur"], errors="coerce")
    dati["anno_reddito"] = int(anno) if pd.notna(anno) else pd.NA
    return dati[["codice_area", "reddito_annuo", "anno_reddito"]]


def aggiungi_indicatori_reddito(dati):
    risultato = dati.copy()
    risultato["prezzo_80mq"] = risultato["prezzo_mq"] * 80
    risultato["anni_reddito_per_80mq"] = risultato["prezzo_80mq"] / risultato["reddito_annuo"]
    risultato["affitto_40mq_mese"] = risultato["affitto_mq_mese"] * 40
    risultato["affitto_40mq_annuo"] = risultato["affitto_40mq_mese"] * 12
    risultato["affitto_40mq_su_reddito_pct"] = risultato["affitto_40mq_annuo"] / risultato["reddito_annuo"] * 100
    return risultato


def carica_dati_francia(mostra_progresso=False):
    if mostra_progresso:
        print("[Mappe Francia] Scarico affitti, vendite DVF e redditi comunali.", flush=True)

    affitti = carica_affitti_francia()
    vendite = carica_vendite_francia()
    redditi = carica_redditi_francia()
    dati = vendite.merge(affitti, on="codice_area", how="outer", suffixes=("_vendite", "_affitti"))
    dati["comune"] = dati["comune_vendite"].fillna(dati["comune_affitti"])
    dati = dati.drop(columns=["comune_vendite", "comune_affitti"])
    dati = dati.merge(redditi, on="codice_area", how="left")
    dati["paese"] = "Francia"
    dati["livello_territoriale"] = "comune"
    dati["fonte_prezzo"] = "DVF stats whole period"
    dati["fonte_affitto"] = "Carte des loyers 2025"
    dati["fonte_reddito"] = "Niveau de vie median"
    dati = aggiungi_indicatori_reddito(dati)
    return dati.sort_values(["codice_area", "comune"])


def decodifica_json_inkar(contenuto):
    risultato = contenuto
    while isinstance(risultato, str):
        risultato = json.loads(risultato)
    return risultato


def richiesta_inkar(percorso, corpo=None):
    url = f"{INKAR_BASE_URL}/{percorso}"
    intestazioni = {"User-Agent": USER_AGENT}
    try:
        risposta = requests.post(url, json=corpo, timeout=90, headers=intestazioni)
    except requests.exceptions.SSLError:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        risposta = requests.post(url, json=corpo, timeout=90, headers=intestazioni, verify=False)

    risposta.raise_for_status()
    return decodifica_json_inkar(risposta.json())


def tempi_inkar(indicatore, livello="KRE"):
    corpo = {
        "IndicatorCollection": [{"Gruppe": str(indicatore)}],
        "TimeCollection": "",
        "SpaceCollection": [{"level": livello}],
    }
    risposta = richiesta_inkar("Wizard/GetM%C3%B6glich", corpo)
    return risposta.get("Möglich", [])


def scarica_indicatore_inkar(indicatore, anno=None, livello="KRE"):
    tempi = tempi_inkar(indicatore, livello=livello)
    if not tempi:
        return pd.DataFrame()

    anni = sorted({str(riga.get("Zeit")) for riga in tempi if str(riga.get("Zeit", "")).isdigit()})
    anno_usato = str(anno) if anno is not None else anni[-1]
    tempi_selezionati = [
        {
            "group": riga.get("Gruppe"),
            "indicator": riga.get("IndID"),
            "level": riga.get("RaumID"),
            "time": riga.get("ZeitID"),
        }
        for riga in tempi
        if str(riga.get("Zeit")) == anno_usato
    ]
    corpo = {
        "IndicatorCollection": [{"Gruppe": str(indicatore)}],
        "TimeCollection": tempi_selezionati,
        "SpaceCollection": [{"level": livello}],
        "pageorder": "1",
    }
    risposta = richiesta_inkar("Table/GetDataTable", corpo)
    dati = pd.DataFrame(risposta.get("Daten", []))
    if dati.empty:
        return dati

    dati = dati.rename(columns={"Schlüssel": "codice_area", "Wert": "value", "ZeitID": "anno"})
    dati["codice_area"] = dati["codice_area"].astype(str).str.zfill(5)
    dati["value"] = pd.to_numeric(dati["value"], errors="coerce")
    dati["anno"] = pd.to_numeric(dati["anno"], errors="coerce")
    return dati[["codice_area", "value", "anno"]].dropna(subset=["value"])


def scarica_geojson_germania():
    return richiesta_get(GERMANIA_GEOJSON_URL, timeout=120).json()


def scarica_geojson_berlino_affitti():
    parametri = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typenames": BERLINO_AFFITTI_LAYER,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }
    return richiesta_get(BERLINO_AFFITTI_WFS_URL, timeout=180, params=parametri).json()


def scarica_geojson_berlino_ortsteile():
    return richiesta_get(BERLINO_ORTSTEILE_GEOJSON_URL, timeout=180).json()


def codice_feature_berlino(feature):
    proprieta = feature.get("properties", {})
    return str(proprieta.get("prognoseraum_nummer", feature.get("id", ""))).strip().zfill(4)


def codice_feature_berlino_ortsteil(feature):
    proprieta = feature.get("properties", {})
    return str(proprieta.get("spatial_name", feature.get("id", ""))).strip().zfill(4)


def reddito_annuo_berlino(dati_germania):
    if dati_germania is None or dati_germania.empty:
        return None
    righe = dati_germania.loc[dati_germania["codice_area"] == "11000"].copy()
    if righe.empty:
        return None
    valore = pd.to_numeric(righe["reddito_annuo"], errors="coerce").dropna()
    if valore.empty:
        return None
    return float(valore.iloc[0])


def prezzo_ortsteil_berlino(nome):
    url = f"{MIETE_AKTUELL_BASE_URL}/Berlin/Berlin/{slug_miete_aktuell(nome)}/"
    html = scarica_html(url)
    if not html:
        return pd.NA
    testo = BeautifulSoup(html, "html.parser").get_text(" ")
    modelli = [
        r"liegt bei\s+([0-9.]+,[0-9]+)\s*€\s+je Quadratmeter",
        r"im Jahr 2026 etwa\s+([0-9.]+,[0-9]+)\s*€",
    ]
    for modello in modelli:
        trovato = re.search(modello, testo, flags=re.S)
        if trovato:
            return numero_tedesco(trovato.group(1))
    return pd.NA


def carica_dati_berlino_vendite(dati_germania=None, mostra_progresso=False):
    geojson = scarica_geojson_berlino_ortsteile()
    reddito_annuo = reddito_annuo_berlino(dati_germania)
    righe = []
    features = []
    elementi = geojson.get("features", [])
    totale = len(elementi)
    for posizione, feature in enumerate(elementi, start=1):
        copia = copy.deepcopy(feature)
        proprieta = copia.get("properties", {})
        codice_area = codice_feature_berlino_ortsteil(copia)
        nome = str(proprieta.get("OTEIL", proprieta.get("spatial_alias", codice_area))).strip()
        if mostra_progresso and posizione % 20 == 0:
            print(f"[Mappe DEU] Prezzi Berlino Ortsteile {posizione}/{totale}", flush=True)
        prezzo = prezzo_ortsteil_berlino(nome)
        copia["id"] = codice_area
        proprieta["code"] = codice_area
        proprieta["name"] = nome
        copia["properties"] = proprieta
        features.append(copia)
        righe.append(
            {
                "codice_area": codice_area,
                "comune": nome,
                "bezirk": str(proprieta.get("BEZIRK", "")).strip(),
                "prezzo_mq": prezzo,
                "affitto_mq_mese": pd.NA,
                "reddito_annuo": reddito_annuo,
                "fonte_prezzo": "miete-aktuell.de Immobilienpreise 2026",
                "fonte_reddito": "INKAR Haushaltseinkommen 2022, valore Berlino",
            }
        )

    dati = pd.DataFrame(righe)
    if not dati.empty:
        dati = aggiungi_indicatori_reddito(dati)
    return dati, {"type": "FeatureCollection", "features": features}


def carica_dati_berlino_quartieri(dati_germania=None):
    geojson = scarica_geojson_berlino_affitti()
    reddito_annuo = reddito_annuo_berlino(dati_germania)
    righe = []
    features = []
    for feature in geojson.get("features", []):
        copia = copy.deepcopy(feature)
        proprieta = copia.get("properties", {})
        codice_area = codice_feature_berlino(copia)
        nome = str(proprieta.get("prognoseraum_bezeichnung", codice_area)).strip()
        affitto = pd.to_numeric(pd.Series([proprieta.get("angebotsmieten")]), errors="coerce").iloc[0]
        copia["id"] = codice_area
        proprieta["code"] = codice_area
        proprieta["name"] = nome
        copia["properties"] = proprieta
        features.append(copia)
        righe.append(
            {
                "codice_area": codice_area,
                "comune": nome,
                "bezirk": str(proprieta.get("bezirk", "")).strip(),
                "affitto_mq_mese": affitto,
                "reddito_annuo": reddito_annuo,
                "fonte_affitto": "Wohnatlas Berlin Angebotsmieten 2022",
                "fonte_reddito": "INKAR Haushaltseinkommen 2022, valore Berlino",
            }
        )

    dati = pd.DataFrame(righe)
    if not dati.empty:
        dati["affitto_40mq_mese"] = dati["affitto_mq_mese"] * 40
        dati["affitto_40mq_annuo"] = dati["affitto_40mq_mese"] * 12
        dati["affitto_40mq_su_reddito_pct"] = dati["affitto_40mq_annuo"] / dati["reddito_annuo"] * 100

    return dati, {"type": "FeatureCollection", "features": features}


def completa_reddito_focus_francia(dati_citta, dati, codice_area):
    righe_citta = dati.loc[dati["codice_area"] == codice_area].copy()
    if righe_citta.empty:
        return dati_citta

    reddito = pd.to_numeric(righe_citta["reddito_annuo"], errors="coerce").dropna()
    if reddito.empty:
        return dati_citta

    risultato = dati_citta.copy()
    risultato["reddito_annuo"] = pd.to_numeric(risultato["reddito_annuo"], errors="coerce").fillna(float(reddito.iloc[0]))
    risultato = aggiungi_indicatori_reddito(risultato)
    return risultato


def nomi_kreise_germania(geojson):
    righe = []
    for feature in geojson.get("features", []):
        proprieta = feature.get("properties", {})
        righe.append(
            {
                "codice_area": str(feature.get("id", "")).zfill(5),
                "comune": proprieta.get("name", ""),
                "stato": proprieta.get("state", ""),
                "tipo_area": proprieta.get("districtType", ""),
            }
        )
    return pd.DataFrame(righe)


def prezzo_citta_immobilienpreise(nome):
    url = f"{IMMOBILIENPREISE_BASE_URL}/stadt/{slug_tedesco(nome)}"
    html = scarica_html(url)
    if not html:
        return pd.NA
    testo = BeautifulSoup(html, "html.parser").get_text(" ")
    modelli = [
        r"Derzeit liegen die Wohnungspreise in .*? bei\s+([0-9.]+,?[0-9]*)\s*€/m²",
        r"Die Quadratmeterpreise bei Wohnungen in .*? betragen\s+([0-9.]+,?[0-9]*)\s*€",
        r"Verkaufspreise für Wohnungen .*? bei\s+([0-9.]+,?[0-9]*)\s*€",
    ]
    for modello in modelli:
        trovato = re.search(modello, testo, flags=re.S)
        if trovato and "k.A" not in trovato.group(0):
            return numero_tedesco(trovato.group(1))
    return pd.NA


def prezzo_landkreis_immobilienpreise(nome):
    url = f"{IMMOBILIENPREISE_BASE_URL}/landkreis/{slug_tedesco(nome)}"
    html = scarica_html(url)
    if not html:
        return pd.NA
    testo = BeautifulSoup(html, "html.parser").get_text(" ")
    modelli = [
        r"Derzeit liegen die Wohnungspreise .*? bei\s+([0-9.]+,?[0-9]*)\s*€/m²",
        r"Wohnungspreise im Landkreis .*? Durchschnittlich\s+([0-9.]+,?[0-9]*)\s*€",
    ]
    for modello in modelli:
        trovato = re.search(modello, testo, flags=re.S)
        if trovato and "k.A" not in trovato.group(0):
            return numero_tedesco(trovato.group(1))
    return pd.NA


def prezzi_landkreise_immobilienpreise():
    valori = {}
    for lettera in LETTERE_PREZZI_LANDKREISE:
        url = f"{IMMOBILIENPREISE_BASE_URL}/landkreise-mit-{lettera}"
        html = scarica_html(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for riga in soup.find_all("tr")[1:]:
            celle = [cella.get_text(" ", strip=True) for cella in riga.find_all(["td", "th"])]
            if len(celle) < 5:
                continue
            valore = numero_tedesco(celle[4])
            if pd.isna(valore):
                continue
            for chiave in chiavi_area_tedesca(celle[0]):
                valori[chiave] = float(valore)
    return valori


def valore_prezzo_landkreis(nome, valori_landkreise):
    for chiave in chiavi_area_tedesca(nome):
        if chiave in valori_landkreise:
            return valori_landkreise[chiave]
    return prezzo_landkreis_immobilienpreise(nome)


def carica_prezzi_vendita_germania(geojson, mostra_progresso=False):
    if mostra_progresso:
        print("[Mappe Germania] Scarico prezzi appartamenti da immobilienpreise.org.", flush=True)

    valori_landkreise = prezzi_landkreise_immobilienpreise()
    righe = []
    features = geojson.get("features", [])
    totale = len(features)
    for posizione, feature in enumerate(features, start=1):
        proprieta = feature.get("properties", {})
        codice_area = str(feature.get("id", "")).zfill(5)
        nome = str(proprieta.get("name", "")).strip()
        tipo_area = str(proprieta.get("districtType", "")).strip()
        if tipo_area in {"Landkreis", "Kreis"}:
            valore = valore_prezzo_landkreis(nome, valori_landkreise)
        else:
            if mostra_progresso and posizione % 35 == 0:
                print(f"[Mappe Germania] Prezzi citta {posizione}/{totale}", flush=True)
            valore = prezzo_citta_immobilienpreise(nome)
        righe.append(
            {
                "codice_area": codice_area,
                "prezzo_mq": valore,
                "anno_prezzo": 2026 if pd.notna(valore) else pd.NA,
                "fonte_prezzo": "immobilienpreise.org Wohnungspreis pro mq 2026",
            }
        )

    return pd.DataFrame(righe)


def carica_dati_germania(geojson=None, mostra_progresso=False):
    if mostra_progresso:
        print("[Mappe Germania] Scarico indicatori INKAR a livello Kreise.", flush=True)

    geojson_usato = geojson if geojson is not None else scarica_geojson_germania()
    nomi = nomi_kreise_germania(geojson_usato)
    affitti = scarica_indicatore_inkar("58", anno=2024).rename(
        columns={"value": "affitto_mq_mese", "anno": "anno_affitto"}
    )
    redditi = scarica_indicatore_inkar("244", anno=2022).rename(
        columns={"value": "reddito_mese", "anno": "anno_reddito"}
    )
    prezzi = carica_prezzi_vendita_germania(geojson_usato, mostra_progresso=mostra_progresso)
    dati = nomi.merge(affitti, on="codice_area", how="left")
    dati = dati.merge(redditi, on="codice_area", how="left")
    dati = dati.merge(prezzi, on="codice_area", how="left")
    dati["reddito_annuo"] = dati["reddito_mese"] * 12
    dati["paese"] = "Germania"
    dati["livello_territoriale"] = "Kreise e kreisfreie Staedte"
    dati["fonte_prezzo"] = dati["fonte_prezzo"].fillna("non disponibile")
    dati["fonte_affitto"] = "INKAR Angebotsmieten 2024"
    dati["fonte_reddito"] = "INKAR Haushaltseinkommen 2022"
    dati = aggiungi_indicatori_reddito(dati)
    return dati.sort_values(["codice_area", "comune"])


def scarica_geojson_francia():
    return richiesta_get(FRANCIA_GEOJSON_URL, timeout=180).json()


def geojson_francia_metropolitana(geojson):
    features = []
    for feature in geojson.get("features", []):
        codice = codice_feature_francia(feature)
        if codice.startswith(("97", "98", "99")):
            continue
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def poligoni_feature(feature):
    geometria = feature.get("geometry", {})
    tipo = geometria.get("type")
    coordinate = geometria.get("coordinates", [])
    if tipo == "Polygon":
        return [coordinate]
    if tipo == "MultiPolygon":
        return coordinate
    return []


def limiti_geojson(features):
    longitudini = []
    latitudini = []
    for feature in features:
        for poligono in poligoni_feature(feature):
            if not poligono:
                continue
            esterno = poligono[0]
            longitudini.extend([punto[0] for punto in esterno])
            latitudini.extend([punto[1] for punto in esterno])
    return min(longitudini), max(longitudini), min(latitudini), max(latitudini)


def disegna_area(asse, feature, colore, bordo="#FFFFFF", larghezza_bordo=0.08):
    for poligono in poligoni_feature(feature):
        if not poligono:
            continue
        esterno = poligono[0]
        patch = Polygon(
            esterno,
            closed=True,
            facecolor=colore,
            edgecolor=bordo,
            linewidth=larghezza_bordo,
        )
        asse.add_patch(patch)


def codice_feature_francia(feature):
    proprieta = feature.get("properties", {})
    return codice_francese(proprieta.get("code", ""))


def codice_feature_germania(feature):
    return str(feature.get("id", "")).zfill(5)


def codici_focus_francia(codice_area):
    profilo = AGGREGAZIONI_COMUNI_FRANCIA.get(codice_area)
    if profilo and "codici" in profilo:
        return set(profilo["codici"])
    return {codice_area}


def geojson_focus_citta(paese_focus, geojson, codice_area, nome_citta):
    if paese_focus == "FRA":
        funzione_codice = codice_feature_francia
        codice_mappa = codici_focus_francia(codice_area)
    elif paese_focus == "DEU":
        funzione_codice = codice_feature_germania
        codice_mappa = {codice_area}
    else:
        return {"type": "FeatureCollection", "features": []}

    features = []
    for feature in geojson.get("features", []):
        if funzione_codice(feature) in codice_mappa:
            copia = copy.deepcopy(feature)
            codice_feature = funzione_codice(feature)
            copia["id"] = codice_feature
            proprieta = copia.get("properties", {})
            if isinstance(proprieta, dict):
                proprieta["code"] = codice_feature
                proprieta["name"] = proprieta.get("nom", nome_citta)
                copia["properties"] = proprieta
            features.append(copia)

    if not features and funzione_codice is not None:
        for feature in geojson.get("features", []):
            if funzione_codice(feature) == codice_area:
                copia = copy.deepcopy(feature)
                copia["id"] = codice_area
                proprieta = copia.get("properties", {})
                if isinstance(proprieta, dict):
                    proprieta["code"] = codice_area
                    proprieta["name"] = nome_citta
                    copia["properties"] = proprieta
                features.append(copia)

    return {"type": "FeatureCollection", "features": features}


def file_focus_citta(paese_focus, nome_file):
    parametro = FOCUS_CITTA[paese_focus]
    return nome_file.replace(parametro["prefisso_nome_file"], parametro["prefisso_file"])


def crea_mappe_focus_citta(dati, paese_focus, geojson, cartella_output="outputs/charts", mostra_progresso=False):
    parametro = FOCUS_CITTA.get(paese_focus)
    if parametro is None:
        return []

    codice_area = parametro["codice"]
    nome_citta = parametro["nome"]
    if paese_focus == "DEU":
        dati_affitti, geojson_affitti = carica_dati_berlino_quartieri(dati)
        dati_prezzi, geojson_prezzi = carica_dati_berlino_vendite(dati, mostra_progresso=mostra_progresso)
        mappe_citta = MAPPE_BERLINO
    else:
        codici_citta = codici_focus_francia(codice_area)
        dati_citta = dati.loc[dati["codice_area"].isin(codici_citta)].copy()
        dati_citta = completa_reddito_focus_francia(dati_citta, dati, codice_area)
        mappe_citta = MAPPE_PARIGI
        fonte = FONTE_FRANCIA
        funzione_codice = codice_feature_francia
        geojson_citta = geojson_focus_citta(paese_focus, geojson, codice_area, nome_citta)
        larghezza_bordo = 0.08

    percorsi = []
    for colonna, titolo, legenda, nome_file, percentuale, decimali in mappe_citta:
        if paese_focus == "DEU" and colonna in {"prezzo_mq", "anni_reddito_per_80mq"}:
            dati_citta = dati_prezzi
            geojson_citta = geojson_prezzi
            fonte = FONTE_BERLINO_PREZZI
            funzione_codice = codice_feature_berlino_ortsteil
            larghezza_bordo = 0.08
        elif paese_focus == "DEU":
            dati_citta = dati_affitti
            geojson_citta = geojson_affitti
            fonte = FONTE_BERLINO_QUARTIERI
            funzione_codice = codice_feature_berlino
            larghezza_bordo = 0.04
        if not geojson_citta["features"]:
            continue
        if mostra_progresso:
            print(f"[Mappe {paese_focus}] Creo {file_focus_citta(paese_focus, nome_file)}", flush=True)
        percorso = grafico_mappa_aree_output(
            dati_citta,
            geojson_citta,
            paese_focus,
            colonna,
            titolo,
            legenda,
            file_focus_citta(paese_focus, nome_file),
            cartella_output,
            fonte,
            funzione_codice,
            percentuale=percentuale,
            decimali=decimali,
            larghezza_bordo=larghezza_bordo,
            margine_geo=None,
        )
        if percorso:
            percorsi.append(percorso)
    return percorsi


def layout_mappa(longitudine_min, longitudine_max, latitudine_min, latitudine_max):
    larghezza_geo = max(longitudine_max - longitudine_min, 0.1)
    altezza_geo = max(latitudine_max - latitudine_min, 0.1)
    rapporto_geo = larghezza_geo / altezza_geo

    if rapporto_geo > 1.2:
        figura_larghezza, figura_altezza = 10.8, 7.1
        area_x, area_y, area_larghezza, area_altezza = 0.04, 0.12, 0.77, 0.64
        colorbar = [0.85, 0.20, 0.026, 0.49]
        titolo_y, nota_y = 0.94, 0.82
    else:
        figura_larghezza, figura_altezza = 8.8, 9.4
        area_x, area_y, area_larghezza, area_altezza = 0.04, 0.10, 0.74, 0.73
        colorbar = [0.83, 0.22, 0.03, 0.54]
        titolo_y, nota_y = 0.95, 0.85

    area_rapporto = (figura_larghezza * area_larghezza) / (figura_altezza * area_altezza)
    if area_rapporto > rapporto_geo:
        asse_altezza = area_altezza
        asse_larghezza = (figura_altezza * asse_altezza * rapporto_geo) / figura_larghezza
    else:
        asse_larghezza = area_larghezza
        asse_altezza = (figura_larghezza * asse_larghezza) / (figura_altezza * rapporto_geo)

    asse_x = area_x + (area_larghezza - asse_larghezza) / 2
    asse_y = area_y + (area_altezza - asse_altezza) / 2
    return (figura_larghezza, figura_altezza), [asse_x, asse_y, asse_larghezza, asse_altezza], colorbar, titolo_y, nota_y


def formatta_colorbar(colorbar, percentuale=False, decimali=0):
    if percentuale:
        colorbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.{decimali}f}%"))
    else:
        formatter = ScalarFormatter(useOffset=False)
        formatter.set_scientific(False)
        colorbar.ax.yaxis.set_major_formatter(formatter)
    colorbar.ax.tick_params(labelsize=8.5)


def limiti_colore(dati, colonna):
    valori = pd.to_numeric(dati[colonna], errors="coerce").dropna()
    if valori.empty:
        return None, None
    minimo = float(valori.quantile(0.02))
    massimo = float(valori.quantile(0.98))
    if minimo == massimo:
        minimo = float(valori.min())
        massimo = float(valori.max())
    if minimo == massimo:
        minimo -= 1
        massimo += 1
    return minimo, massimo


def titolo_su_piu_righe(titolo, larghezza=64):
    return "\n".join(textwrap.wrap(titolo, width=larghezza, break_long_words=False))


def fonte_su_piu_righe(fonte, larghezza=130):
    testo = f"Fonte: {fonte} | {WATERMARK}"
    return "\n".join(textwrap.wrap(testo, width=larghezza, break_long_words=False))


def salva_mappa(figura, percorso):
    figura.savefig(percorso, dpi=170)
    plt.close(figura)


def dipartimento_francese(codice_area):
    codice = str(codice_area).strip().upper()
    if codice.startswith(("97", "98")):
        return codice[:3]
    return codice[:2]


def etichetta_dipartimento_francese(codice):
    codice_testo = str(codice).strip().upper()
    nome = NOMI_DIPARTIMENTI_FRANCESI.get(codice_testo)
    if nome:
        return f"{nome} ({codice_testo})"
    return f"Dip. {codice_testo}"


def aggrega_range_locale(dati, gruppo, etichetta, colonna):
    dati_validi = dati.dropna(subset=[gruppo, etichetta, colonna]).copy()
    dati_validi[colonna] = pd.to_numeric(dati_validi[colonna], errors="coerce")
    dati_validi = dati_validi.dropna(subset=[colonna])
    if dati_validi.empty:
        return pd.DataFrame()

    colonne_gruppo = [gruppo] if gruppo == etichetta else [gruppo, etichetta]
    aggregato = (
        dati_validi.groupby(colonne_gruppo, as_index=False)
        .agg(
            valore_mediano=(colonna, "median"),
            valore_minimo=(colonna, "min"),
            valore_massimo=(colonna, "max"),
            aree=(colonna, "count"),
        )
        .sort_values("valore_mediano", ascending=False)
    )
    return aggregato


def grafico_range_locale(
    dati,
    paese_focus,
    gruppo,
    etichetta,
    colonna,
    titolo,
    asse_x,
    nome_file,
    cartella_output,
    fonte,
    limite_righe=None,
):
    range_locale = aggrega_range_locale(dati, gruppo, etichetta, colonna)
    if range_locale.empty:
        return None

    if limite_righe:
        range_locale = range_locale.head(limite_righe).copy()

    altezza = max(6.8, min(18, 0.34 * len(range_locale) + 2.5))
    figura, asse = plt.subplots(figsize=(11, altezza))
    posizioni = range(len(range_locale))
    for posizione, riga in zip(posizioni, range_locale.itertuples(index=False)):
        asse.hlines(
            posizione,
            riga.valore_minimo,
            riga.valore_massimo,
            color=COLORE_EU27,
            linewidth=2,
            alpha=0.65,
        )
        asse.scatter(riga.valore_mediano, posizione, color=COLORE_PRINCIPALE, s=46, zorder=3)

    asse.set_yticks(list(posizioni))
    asse.set_yticklabels(range_locale[etichetta])
    asse.invert_yaxis()
    asse.set_title(titolo_su_piu_righe(titolo), fontsize=14, fontweight="bold", loc="left", pad=12)
    asse.set_xlabel(asse_x)
    asse.grid(axis="x", alpha=0.22)
    asse.tick_params(axis="y", labelsize=9.5)
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    asse.xaxis.set_major_formatter(formatter)
    figura.text(
        0.01,
        0.01,
        fonte_su_piu_righe(fonte),
        ha="left",
        va="bottom",
        fontsize=7.8,
        color="#333333",
    )

    percorso = cartella_paese(cartella_output, paese_focus, "focus") / nome_file
    plt.tight_layout(rect=[0, 0.08, 0.99, 0.95])
    figura.savefig(percorso, dpi=170)
    plt.close(figura)
    return percorso


def crea_range_francia(dati, cartella_output="outputs/charts", mostra_progresso=False):
    dati_range = dati.loc[
        ~dati["codice_area"].isin(list(AGGREGAZIONI_COMUNI_FRANCIA))
        & ~dati["codice_area"].str.startswith(("97", "98", "99"), na=False)
    ].copy()
    dati_range["dipartimento"] = dati_range["codice_area"].map(dipartimento_francese)
    dati_range["etichetta_range"] = dati_range["dipartimento"].map(etichetta_dipartimento_francese)
    if mostra_progresso:
        print("[Focus Francia] Creo francia_range_prezzi_dvf_dipartimenti.png", flush=True)

    percorso = grafico_range_locale(
        dati_range,
        "FRA",
        "dipartimento",
        "etichetta_range",
        "prezzo_mq",
        "Prezzi DVF: mediana e range tra comuni - dipartimenti francesi",
        "euro/mq",
        "francia_range_prezzi_dvf_dipartimenti.png",
        cartella_output,
        FONTE_FRANCIA,
        limite_righe=25,
    )
    return [percorso] if percorso else []


def crea_range_germania(dati, cartella_output="outputs/charts", mostra_progresso=False):
    dati_range, geojson = carica_dati_berlino_quartieri(dati)
    if mostra_progresso:
        print("[Focus Germania] Creo berlino_range_affitti_quartieri.png", flush=True)

    percorso = grafico_range_locale(
        dati_range,
        "DEU",
        "bezirk",
        "bezirk",
        "affitto_mq_mese",
        "Affitti: mediana e range tra quartieri statistici - Bezirke di Berlino",
        "euro/mq/mese",
        "berlino_range_affitti_quartieri.png",
        cartella_output,
        FONTE_BERLINO_QUARTIERI,
    )
    return [percorso] if percorso else []


def grafico_mappa_aree_output(
    dati,
    geojson,
    paese_focus,
    colonna,
    titolo,
    legenda,
    nome_file,
    cartella_output,
    fonte,
    funzione_codice,
    percentuale=False,
    decimali=0,
    larghezza_bordo=0.08,
    margine_geo=0.25,
):
    dati_mappa = dati.dropna(subset=[colonna, "codice_area"]).copy()
    dati_mappa[colonna] = pd.to_numeric(dati_mappa[colonna], errors="coerce")
    dati_mappa = dati_mappa.dropna(subset=[colonna])
    if dati_mappa.empty:
        return None

    valori = dati_mappa.set_index("codice_area")[colonna].to_dict()
    minimo, massimo = limiti_colore(dati_mappa, colonna)
    normalizzazione = Normalize(vmin=minimo, vmax=massimo, clip=True)
    scala_colori = plt.get_cmap("YlOrRd")
    features = geojson.get("features", [])
    longitudine_min, longitudine_max, latitudine_min, latitudine_max = limiti_geojson(features)
    dimensione_figura, posizione_asse, posizione_colorbar, titolo_y, nota_y = layout_mappa(
        longitudine_min,
        longitudine_max,
        latitudine_min,
        latitudine_max,
    )

    figura = plt.figure(figsize=dimensione_figura)
    asse = figura.add_axes(posizione_asse)
    for feature in features:
        codice = funzione_codice(feature)
        valore = valori.get(codice)
        colore = scala_colori(normalizzazione(valore)) if valore is not None else "#E6E6E6"
        disegna_area(asse, feature, colore, larghezza_bordo=larghezza_bordo)

    if margine_geo is None:
        margine_x = max((longitudine_max - longitudine_min) * 0.04, 0.006)
        margine_y = max((latitudine_max - latitudine_min) * 0.04, 0.006)
    else:
        margine_x = margine_geo
        margine_y = margine_geo

    asse.set_xlim(longitudine_min - margine_x, longitudine_max + margine_x)
    asse.set_ylim(latitudine_min - margine_y, latitudine_max + margine_y)
    asse.set_aspect("equal")
    asse.axis("off")
    figura.text(0.03, titolo_y, titolo_su_piu_righe(titolo), ha="left", va="top", fontsize=14, fontweight="bold")
    figura.text(
        0.03,
        nota_y,
        "Scala colore tagliata al 2-98 percentile. Aree grigie = dato non disponibile.",
        ha="left",
        va="top",
        fontsize=8.8,
        color="#333333",
    )
    mappabile = ScalarMappable(norm=normalizzazione, cmap=scala_colori)
    mappabile.set_array([])
    asse_colorbar = figura.add_axes(posizione_colorbar)
    colorbar = figura.colorbar(mappabile, cax=asse_colorbar)
    colorbar.set_label(legenda, fontsize=9.2)
    formatta_colorbar(colorbar, percentuale=percentuale, decimali=decimali)
    figura.text(
        0.01,
        0.012,
        fonte_su_piu_righe(fonte),
        ha="left",
        va="bottom",
        fontsize=7.8,
        color="#333333",
    )

    percorso = cartella_paese(cartella_output, paese_focus, "mappe") / nome_file
    salva_mappa(figura, percorso)
    return percorso


def salva_summary_locale(dati, cartella_output, paese_focus, nome_file):
    profilo = profilo_paese(paese_focus)
    percorso = cartella_summary(cartella_output, profilo["slug"], "mappe") / nome_file
    dati.to_csv(percorso, index=False)
    return percorso


def crea_mappe_francia(dati, cartella_output="outputs/charts", mostra_progresso=False):
    geojson = geojson_francia_metropolitana(scarica_geojson_francia())
    dati_mappa = dati.loc[~dati["codice_area"].str.startswith(("97", "98", "99"), na=False)].copy()
    percorsi = []
    for colonna, titolo, legenda, nome_file, percentuale, decimali in MAPPE_FRANCIA:
        if mostra_progresso:
            print(f"[Mappe Francia] Creo {nome_file}", flush=True)
        percorso = grafico_mappa_aree_output(
            dati_mappa,
            geojson,
            "FRA",
            colonna,
            titolo,
            legenda,
            nome_file,
            cartella_output,
            FONTE_FRANCIA,
            codice_feature_francia,
            percentuale=percentuale,
            decimali=decimali,
            larghezza_bordo=0.025,
        )
        if percorso:
            percorsi.append(percorso)
    return percorsi


def crea_mappe_germania(dati, geojson, cartella_output="outputs/charts", mostra_progresso=False):
    percorsi = []
    for colonna, titolo, legenda, nome_file, percentuale, decimali in MAPPE_GERMANIA:
        if mostra_progresso:
            print(f"[Mappe Germania] Creo {nome_file}", flush=True)
        fonte = FONTE_GERMANIA_PREZZI if colonna in {"prezzo_mq", "anni_reddito_per_80mq"} else FONTE_GERMANIA
        percorso = grafico_mappa_aree_output(
            dati,
            geojson,
            "DEU",
            colonna,
            titolo,
            legenda,
            nome_file,
            cartella_output,
            fonte,
            codice_feature_germania,
            percentuale=percentuale,
            decimali=decimali,
            larghezza_bordo=0.22,
        )
        if percorso:
            percorsi.append(percorso)
    return percorsi


def valore_mediano(dati, colonna):
    valori = pd.to_numeric(dati[colonna], errors="coerce").dropna()
    if valori.empty:
        return None
    return float(valori.median())


def riga_focus(dati, codice_area):
    righe = dati.loc[dati["codice_area"] == codice_area].copy()
    if righe.empty:
        return None
    return righe.iloc[0]


def etichetta_valore(valore, percentuale=False, decimali=1):
    if pd.isna(valore):
        return "n.d."
    if percentuale:
        return f"{valore:.{decimali}f}%"
    return f"{valore:.{decimali}f}"


def metriche_focus(paese_focus):
    profilo = profilo_paese(paese_focus)
    if profilo["iso3"] == "DEU":
        return [
            {
                "colonna": "affitto_mq_mese",
                "titolo": "Affitto mensile\n(euro/mq/mese)",
                "unita": "euro per mq al mese",
                "percentuale": False,
                "decimali": 1,
            },
            {
                "colonna": "affitto_40mq_su_reddito_pct",
                "titolo": "Affitto 40 mq\n(% del reddito annuo)",
                "unita": "% del reddito annuo",
                "percentuale": True,
                "decimali": 0,
            },
        ]
    else:
        titolo_acquisto = "Acquisto: prezzo al mq\n(euro/mq)"
        titolo_reddito_acquisto = "Acquisto 80 mq\n(anni di reddito annuo)"

    return [
        {
            "colonna": "affitto_mq_mese",
            "titolo": "Affitto mensile\n(euro/mq/mese)",
            "unita": "euro per mq al mese",
            "percentuale": False,
            "decimali": 1,
        },
        {
            "colonna": "prezzo_mq",
            "titolo": titolo_acquisto,
            "unita": "euro per mq",
            "percentuale": False,
            "decimali": 0,
        },
        {
            "colonna": "affitto_40mq_su_reddito_pct",
            "titolo": "Affitto 40 mq\n(% del reddito annuo)",
            "unita": "% del reddito annuo",
            "percentuale": True,
            "decimali": 0,
        },
        {
            "colonna": "anni_reddito_per_80mq",
            "titolo": titolo_reddito_acquisto,
            "unita": "anni di reddito annuo",
            "percentuale": False,
            "decimali": 1,
        },
    ]


def grafico_focus_citta(dati, paese_focus, codice_area, nome_citta, nome_file, cartella_output, fonte):
    focus = riga_focus(dati, codice_area)
    if focus is None:
        return None

    profilo = profilo_paese(paese_focus)
    metriche = metriche_focus(paese_focus)
    if len(metriche) == 2:
        figura, assi = plt.subplots(1, 2, figsize=(10.8, 4.8))
        assi_piatte = assi.flatten()
        layout_rect = [0, 0.12, 1, 0.72]
        titolo_y = 0.98
        intestazione_y = 0.82
    else:
        figura, assi = plt.subplots(2, 2, figsize=(10.8, 7.4))
        assi_piatte = assi.flatten()
        layout_rect = [0, 0.06, 1, 0.84]
        titolo_y = 0.98
        intestazione_y = 0.875
    righe_summary = []
    for asse, metrica in zip(assi_piatte, metriche):
        colonna = metrica["colonna"]
        titolo = metrica["titolo"]
        unita = metrica["unita"]
        percentuale = metrica["percentuale"]
        decimali = metrica["decimali"]
        valore_citta = pd.to_numeric(pd.Series([focus.get(colonna)]), errors="coerce").iloc[0]
        valore_paese = valore_mediano(dati, colonna)
        valori = [0 if pd.isna(valore_citta) else valore_citta, 0 if valore_paese is None else valore_paese]
        colori = [profilo["colore"], COLORE_EU27]
        barre = asse.barh([nome_citta, f"Mediana {profilo['label']}"], valori, color=colori, height=0.48)
        asse.set_title(titolo, loc="left", fontsize=11.7, fontweight="bold")
        asse.grid(axis="x", alpha=0.22)
        asse.spines["top"].set_visible(False)
        asse.spines["right"].set_visible(False)
        asse.tick_params(axis="y", labelsize=9.5)
        if percentuale:
            asse.xaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.0f}%"))
        else:
            formatter = ScalarFormatter(useOffset=False)
            formatter.set_scientific(False)
            asse.xaxis.set_major_formatter(formatter)
        limite = max(valori) * 1.25 if max(valori) > 0 else 1
        asse.set_xlim(0, limite)
        for barra, valore in zip(barre, valori):
            asse.text(
                barra.get_width() + limite * 0.02,
                barra.get_y() + barra.get_height() / 2,
                etichetta_valore(valore, percentuale=percentuale, decimali=decimali),
                va="center",
                fontsize=9.2,
            )
        asse.set_xlabel(unita, fontsize=9)
        righe_summary.append(
            {
                "metrica": colonna,
                "citta": nome_citta,
                "valore_citta": valore_citta,
                "mediana_paese": valore_paese,
                "unita": unita,
            }
        )

    titolo_focus = (
        f"Focus {nome_citta}: affitto e rapporto al reddito"
        if profilo["iso3"] == "DEU"
        else f"Focus {nome_citta}: affitto e acquisto rispetto al reddito"
    )
    figura.suptitle(
        titolo_focus,
        x=0.01,
        y=titolo_y,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    intestazione_destra = "RAPPORTO AL REDDITO" if profilo["iso3"] == "DEU" else "ACQUISTO"
    figura.text(0.285, intestazione_y, "AFFITTO", ha="center", va="center", fontsize=12.5, fontweight="bold")
    figura.text(0.745, intestazione_y, intestazione_destra, ha="center", va="center", fontsize=12.5, fontweight="bold")
    figura.text(
        0.01,
        0.01,
        fonte_su_piu_righe(fonte),
        ha="left",
        va="bottom",
        fontsize=7.8,
        color="#333333",
    )
    plt.tight_layout(rect=layout_rect)
    percorso = cartella_paese(cartella_output, paese_focus, "focus") / nome_file
    figura.savefig(percorso, dpi=170)
    plt.close(figura)

    percorso_summary = cartella_summary(cartella_output, profilo["slug"], "focus") / f"{nome_file[:-4]}.csv"
    pd.DataFrame(righe_summary).to_csv(percorso_summary, index=False)
    return percorso


def crea_focus_francia(dati, cartella_output="outputs/charts", mostra_progresso=False):
    if mostra_progresso:
        print("[Focus Francia] Creo focus Parigi.", flush=True)
    percorso = grafico_focus_citta(
        dati,
        "FRA",
        "75056",
        "Parigi",
        "parigi_focus_affitti_vendita_reddito.png",
        cartella_output,
        FONTE_FRANCIA,
    )
    return [percorso] if percorso else []


def leggi_summary_parigi_milano(cartella_output):
    percorso_francia = (
        cartella_summary(cartella_output, "francia", "mappe")
        / "francia_comuni_affitti_vendita_reddito.csv"
    )
    percorso_italia = (
        cartella_summary(cartella_output, "italia_locale")
        / "focus_locale_base_capoluoghi_provincia_omi_mef.csv"
    )
    if not percorso_francia.exists() or not percorso_italia.exists():
        return pd.DataFrame()

    francia = pd.read_csv(percorso_francia, dtype={"codice_area": str})
    italia = pd.read_csv(percorso_italia)
    parigi = francia.loc[francia["codice_area"].astype(str) == "75056"].copy()
    milano = italia.loc[
        (italia["comune"].astype(str).str.lower() == "milano")
        & (italia["provincia"].astype(str).str.upper() == "MI")
    ].copy()
    if parigi.empty or milano.empty:
        return pd.DataFrame()

    riga_parigi = parigi.iloc[0]
    riga_milano = milano.iloc[0]
    metriche = [
        ("affitto_mq_mese", "Affitto mensile", "euro/mq/mese", False, 1),
        ("prezzo_mq", "Prezzo di vendita", "euro/mq", False, 0),
        ("affitto_40mq_su_reddito_pct", "Affitto 40 mq sul reddito", "% del reddito annuo", True, 1),
        ("anni_reddito_per_80mq", "Acquisto 80 mq sul reddito", "anni di reddito annuo", False, 1),
    ]
    colonne_milano = {
        "affitto_mq_mese": "affitto_mq_mese_mediano",
        "prezzo_mq": "prezzo_mq_mediano",
        "affitto_40mq_su_reddito_pct": "affitto_40mq_su_reddito_pct",
        "anni_reddito_per_80mq": "anni_reddito_per_80mq",
    }
    righe = []
    for codice, metrica, unita, percentuale, decimali in metriche:
        valore_parigi = pd.to_numeric(pd.Series([riga_parigi.get(codice)]), errors="coerce").iloc[0]
        valore_milano = pd.to_numeric(pd.Series([riga_milano.get(colonne_milano[codice])]), errors="coerce").iloc[0]
        righe.extend(
            [
                {
                    "citta": "Parigi",
                    "paese": "Francia",
                    "metrica": metrica,
                    "codice_metrica": codice,
                    "value": valore_parigi,
                    "unita": unita,
                    "percentuale": percentuale,
                    "decimali": decimali,
                    "fonte_prezzo": riga_parigi.get("fonte_prezzo", ""),
                    "fonte_affitto": riga_parigi.get("fonte_affitto", ""),
                    "fonte_reddito": riga_parigi.get("fonte_reddito", ""),
                    "periodo": f"affitti 2025, redditi {formatta_anno(riga_parigi.get('anno_reddito', ''))}",
                },
                {
                    "citta": "Milano",
                    "paese": "Italia",
                    "metrica": metrica,
                    "codice_metrica": codice,
                    "value": valore_milano,
                    "unita": unita,
                    "percentuale": percentuale,
                    "decimali": decimali,
                    "fonte_prezzo": "Agenzia Entrate - OMI",
                    "fonte_affitto": "Agenzia Entrate - OMI",
                    "fonte_reddito": "MEF Dipartimento Finanze",
                    "periodo": (
                        f"OMI {formatta_semestre_locale(riga_milano.get('semestre_omi', ''))}, "
                        f"redditi {formatta_anno(riga_milano.get('anno_redditi_mef', ''))}"
                    ),
                },
            ]
        )

    return pd.DataFrame(righe)


def formatta_anno(valore):
    numero = pd.to_numeric(pd.Series([valore]), errors="coerce").iloc[0]
    if pd.isna(numero):
        return ""
    return str(int(numero))


def formatta_semestre_locale(valore):
    testo = str(valore).strip()
    if testo.endswith(".0"):
        testo = testo[:-2]
    if len(testo) == 5 and testo.isdigit():
        return f"{testo[:4]}-S{testo[-1]}"
    return testo


def crea_confronto_parigi_milano(cartella_output="outputs/charts"):
    dati = leggi_summary_parigi_milano(cartella_output)
    if dati.empty:
        return None

    percorso_summary = (
        cartella_summary(cartella_output, "francia", "focus")
        / "parigi_milano_confronto_affitti_vendita_reddito.csv"
    )
    dati.to_csv(percorso_summary, index=False)

    profilo_francia = profilo_paese("FRA")
    profilo_italia = profilo_paese("ITA")
    colori = {"Parigi": profilo_francia["colore"], "Milano": profilo_italia["colore"]}
    ordine_metriche = dati.drop_duplicates("codice_metrica")

    figura, assi = plt.subplots(2, 2, figsize=(10.8, 7.2))
    for asse, metrica in zip(assi.flatten(), ordine_metriche.itertuples(index=False)):
        valori = dati.loc[dati["codice_metrica"] == metrica.codice_metrica].copy()
        valori["value"] = pd.to_numeric(valori["value"], errors="coerce")
        valori = valori.dropna(subset=["value"])
        if valori.empty:
            asse.axis("off")
            continue

        barre = asse.bar(
            valori["citta"],
            valori["value"],
            color=[colori.get(citta, COLORE_PRINCIPALE) for citta in valori["citta"]],
            width=0.55,
        )
        asse.set_title(metrica.metrica, loc="left", fontsize=11.5, fontweight="bold")
        asse.set_ylabel(metrica.unita, fontsize=9.2)
        asse.grid(axis="y", alpha=0.22)
        asse.spines["top"].set_visible(False)
        asse.spines["right"].set_visible(False)
        if metrica.percentuale:
            asse.yaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.0f}%"))
        else:
            formatter = ScalarFormatter(useOffset=False)
            formatter.set_scientific(False)
            asse.yaxis.set_major_formatter(formatter)
        limite = valori["value"].max() * 1.22 if valori["value"].max() > 0 else 1
        asse.set_ylim(0, limite)
        for barra, valore in zip(barre, valori["value"]):
            testo = etichetta_valore(
                valore,
                percentuale=metrica.percentuale,
                decimali=int(metrica.decimali),
            )
            asse.text(
                barra.get_x() + barra.get_width() / 2,
                valore + limite * 0.025,
                testo,
                ha="center",
                va="bottom",
                fontsize=9.4,
            )

    periodi = dati.drop_duplicates("citta")[["citta", "periodo"]]
    nota_periodi = "; ".join(f"{riga.citta}: {riga.periodo}" for riga in periodi.itertuples(index=False))
    figura.suptitle(
        "Parigi e Milano: affitto, acquisto e rapporto al reddito",
        x=0.01,
        y=0.98,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    figura.text(0.01, 0.91, nota_periodi, ha="left", va="top", fontsize=8.7, color="#333333")
    fonte = (
        "data.gouv.fr: DVF stats whole period, Carte des loyers 2025, niveau de vie median; "
        "ISTAT, Agenzia Entrate - OMI, MEF Dipartimento Finanze"
    )
    figura.text(
        0.01,
        0.01,
        fonte_su_piu_righe(fonte),
        ha="left",
        va="bottom",
        fontsize=7.8,
        color="#333333",
    )
    plt.tight_layout(rect=[0, 0.08, 1, 0.86])
    percorso = cartella_paese(cartella_output, "FRA", "focus") / "parigi_milano_confronto_affitti_vendita_reddito.png"
    figura.savefig(percorso, dpi=170)
    plt.close(figura)
    return percorso


def crea_focus_germania(dati, cartella_output="outputs/charts", mostra_progresso=False):
    if mostra_progresso:
        print("[Focus Germania] Creo focus Berlino.", flush=True)
    percorso = grafico_focus_citta(
        dati,
        "DEU",
        "11000",
        "Berlino",
        "berlino_focus_affitti_reddito.png",
        cartella_output,
        FONTE_GERMANIA,
    )
    return [percorso] if percorso else []


def crea_mappe_e_focus_europa(cartella_output="outputs/charts", paesi=None, mostra_progresso=False):
    paesi_focus = normalizza_codici_paesi(paesi)
    percorsi = []

    if "FRA" in paesi_focus:
        dati_francia = carica_dati_francia(mostra_progresso=mostra_progresso)
        geojson_francia = scarica_geojson_francia()
        salva_summary_locale(dati_francia, cartella_output, "FRA", "francia_comuni_affitti_vendita_reddito.csv")
        percorsi.extend(crea_range_francia(dati_francia, cartella_output, mostra_progresso=mostra_progresso))
        percorsi.extend(crea_mappe_francia(dati_francia, cartella_output, mostra_progresso=mostra_progresso))
        percorsi.extend(
            crea_mappe_focus_citta(
                dati_francia,
                "FRA",
                geojson_francia,
                cartella_output,
                mostra_progresso=mostra_progresso,
            )
        )
        percorsi.extend(crea_focus_francia(dati_francia, cartella_output, mostra_progresso=mostra_progresso))

    if "DEU" in paesi_focus:
        geojson_germania = scarica_geojson_germania()
        dati_germania = carica_dati_germania(geojson=geojson_germania, mostra_progresso=mostra_progresso)
        salva_summary_locale(dati_germania, cartella_output, "DEU", "germania_kreise_affitti_reddito.csv")
        percorsi.extend(crea_range_germania(dati_germania, cartella_output, mostra_progresso=mostra_progresso))
        percorsi.extend(
            crea_mappe_focus_citta(
                dati_germania,
                "DEU",
                geojson_germania,
                cartella_output,
                mostra_progresso=mostra_progresso,
            )
        )
        percorsi.extend(
            crea_mappe_germania(dati_germania, geojson_germania, cartella_output, mostra_progresso=mostra_progresso)
        )
        percorsi.extend(crea_focus_germania(dati_germania, cartella_output, mostra_progresso=mostra_progresso))

    if mostra_progresso:
        print(f"Mappe e focus esteri completati: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
