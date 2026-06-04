from io import BytesIO
import json
import re
import textwrap
import urllib3
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import pandas as pd
import requests
from scripts.helpers.grafici import COLORE_EU27
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
INKAR_BASE_URL = "https://www.inkar.de"
USER_AGENT = "crisi-abitativa/0.1"

FONTE_FRANCIA = (
    "data.gouv.fr: DVF stats whole period, Carte des loyers 2025, niveau de vie median; "
    "france-geojson.gregoiredavid.fr"
)
FONTE_GERMANIA = (
    "BBSR INKAR: Angebotsmieten 2024, Kaufwerte Bauland 2022, Haushaltseinkommen 2022; "
    "geofeatures-ags-germany"
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
        "Valori di acquisto del suolo edificabile: Kreise e citta-distretto tedesche, 2022",
        "euro/mq",
        "germania_kreise_valori_bauland_mq.png",
        False,
        0,
    ),
    (
        "anni_reddito_per_80mq",
        "Valore di 80 mq di suolo edificabile in anni di reddito: Kreise e citta-distretto tedesche",
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

AGGREGAZIONI_COMUNI_FRANCIA = {
    "75056": {"nome": "Paris", "codici": [f"751{numero:02d}" for numero in range(1, 21)]},
    "13055": {"nome": "Marseille", "codici": [f"132{numero:02d}" for numero in range(1, 17)]},
    "69123": {"nome": "Lyon", "codici": [f"6938{numero}" for numero in range(1, 10)]},
}


def richiesta_get(url, timeout=120):
    risposta = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    risposta.raise_for_status()
    return risposta


def leggi_csv_url(url, **opzioni):
    risposta = richiesta_get(url, timeout=180)
    return pd.read_csv(BytesIO(risposta.content), **opzioni)


def numero_con_virgola(valore):
    testo = str(valore).strip().replace("\xa0", "")
    testo = testo.replace(",", ".")
    return pd.to_numeric(testo, errors="coerce")


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


def carica_dati_germania(geojson=None, mostra_progresso=False):
    if mostra_progresso:
        print("[Mappe Germania] Scarico indicatori INKAR a livello Kreise.", flush=True)

    geojson_usato = geojson if geojson is not None else scarica_geojson_germania()
    nomi = nomi_kreise_germania(geojson_usato)
    affitti = scarica_indicatore_inkar("58", anno=2024).rename(
        columns={"value": "affitto_mq_mese", "anno": "anno_affitto"}
    )
    vendite = scarica_indicatore_inkar("46", anno=2022).rename(
        columns={"value": "prezzo_mq", "anno": "anno_prezzo"}
    )
    redditi = scarica_indicatore_inkar("244", anno=2022).rename(
        columns={"value": "reddito_mese", "anno": "anno_reddito"}
    )
    dati = nomi.merge(affitti, on="codice_area", how="left")
    dati = dati.merge(vendite, on="codice_area", how="left")
    dati = dati.merge(redditi, on="codice_area", how="left")
    dati["reddito_annuo"] = dati["reddito_mese"] * 12
    dati["paese"] = "Germania"
    dati["livello_territoriale"] = "Kreise e kreisfreie Staedte"
    dati["fonte_prezzo"] = "INKAR Kaufwerte Bauland 2022"
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


def salva_mappa(figura, percorso):
    figura.savefig(percorso, dpi=170)
    plt.close(figura)


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

    asse.set_xlim(longitudine_min - 0.25, longitudine_max + 0.25)
    asse.set_ylim(latitudine_min - 0.25, latitudine_max + 0.25)
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
        f"Fonte: {fonte} | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=8.5,
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
        percorso = grafico_mappa_aree_output(
            dati,
            geojson,
            "DEU",
            colonna,
            titolo,
            legenda,
            nome_file,
            cartella_output,
            FONTE_GERMANIA,
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
        titolo_acquisto = "Acquisto (proxy): suolo edificabile\n(euro/mq)"
        titolo_reddito_acquisto = "Acquisto 80 mq (proxy suolo)\n(anni di reddito annuo)"
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
    figura, assi = plt.subplots(2, 2, figsize=(10.8, 7.4))
    assi_piatte = assi.flatten()
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

    testo_proxy = " (proxy suolo)" if profilo["iso3"] == "DEU" else ""
    figura.suptitle(
        f"Focus {nome_citta}: affitto e acquisto{testo_proxy} rispetto al reddito",
        x=0.01,
        y=0.98,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    figura.text(0.285, 0.875, "AFFITTO", ha="center", va="center", fontsize=12.5, fontweight="bold")
    figura.text(0.745, 0.875, "ACQUISTO", ha="center", va="center", fontsize=12.5, fontweight="bold")
    figura.text(
        0.01,
        0.01,
        f"Fonte: {fonte} | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=8.8,
        color="#333333",
    )
    plt.tight_layout(rect=[0, 0.06, 1, 0.84])
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


def crea_focus_germania(dati, cartella_output="outputs/charts", mostra_progresso=False):
    if mostra_progresso:
        print("[Focus Germania] Creo focus Berlino.", flush=True)
    percorso = grafico_focus_citta(
        dati,
        "DEU",
        "11000",
        "Berlino",
        "berlino_focus_affitti_vendita_reddito.png",
        cartella_output,
        FONTE_GERMANIA,
    )
    return [percorso] if percorso else []


def crea_mappe_e_focus_europa(cartella_output="outputs/charts", paesi=None, mostra_progresso=False):
    paesi_focus = normalizza_codici_paesi(paesi)
    percorsi = []

    if "FRA" in paesi_focus:
        dati_francia = carica_dati_francia(mostra_progresso=mostra_progresso)
        salva_summary_locale(dati_francia, cartella_output, "FRA", "francia_comuni_affitti_vendita_reddito.csv")
        percorsi.extend(crea_mappe_francia(dati_francia, cartella_output, mostra_progresso=mostra_progresso))
        percorsi.extend(crea_focus_francia(dati_francia, cartella_output, mostra_progresso=mostra_progresso))

    if "DEU" in paesi_focus:
        geojson_germania = scarica_geojson_germania()
        dati_germania = carica_dati_germania(geojson=geojson_germania, mostra_progresso=mostra_progresso)
        salva_summary_locale(dati_germania, cartella_output, "DEU", "germania_kreise_affitti_vendita_reddito.csv")
        percorsi.extend(
            crea_mappe_germania(dati_germania, geojson_germania, cartella_output, mostra_progresso=mostra_progresso)
        )
        percorsi.extend(crea_focus_germania(dati_germania, cartella_output, mostra_progresso=mostra_progresso))

    if mostra_progresso:
        print(f"Mappe e focus esteri completati: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
