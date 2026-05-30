from io import StringIO
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
from grafici import COLORE_ITALIA, COLORE_PRINCIPALE, formatta_asse_y, periodo_to_datetime, salva_figura
from utils import OECD_BASE_URL, WATERMARK, scarica_testo


PAESI_DEFAULT = ["ITA", "FRA", "DEU", "ESP", "NLD", "PRT", "GRC", "USA", "GBR"]
ANNO_BASE_INDICI = "2019"

MISURE_PREZZI_CASE = [
    ("RHP", "Prezzi reali delle case", "oecd_prezzi_reali_case.png"),
    ("HPI", "Prezzi nominali delle case", "oecd_prezzi_nominali_case.png"),
    ("HPI_YDH", "Rapporto prezzi case / reddito", "oecd_rapporto_prezzi_reddito.png"),
    ("HPI_RPI", "Rapporto prezzi case / affitti", "oecd_rapporto_prezzi_affitti.png"),
]


def cartella_oecd(cartella_output):
    output = Path(cartella_output) / "oecd" / "confronti"
    output.mkdir(parents=True, exist_ok=True)
    return output


def scarica_prezzi_case_oecd(paesi=None, misure=None, inizio="2000", fine="2024"):
    lista_paesi = paesi or PAESI_DEFAULT
    lista_misure = misure or [misura for misura, titolo, nome_file in MISURE_PREZZI_CASE]
    chiave = f"{'+'.join(lista_paesi)}.A.{'+'.join(lista_misure)}.?"
    parametri = {
        "startPeriod": inizio,
        "endPeriod": fine,
        "dimensionAtObservation": "AllDimensions",
        "format": "csvfilewithlabels",
    }
    testo_csv = scarica_testo(
        f"{OECD_BASE_URL}/OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES/{chiave}",
        parametri,
    )
    dati = pd.read_csv(StringIO(testo_csv))
    if dati.empty:
        return dati

    dati = dati.rename(
        columns={
            "REF_AREA": "country_code",
            "Reference area": "country_name",
            "MEASURE": "measure_code",
            "Measure": "measure_name",
            "TIME_PERIOD": "time_period",
            "OBS_VALUE": "value",
        }
    )
    dati["value"] = pd.to_numeric(dati["value"], errors="coerce")
    dati["data_plot"] = dati["time_period"].map(periodo_to_datetime)
    return dati.dropna(subset=["value", "data_plot"]).sort_values(["measure_code", "country_code", "data_plot"])


def ribasa_indici_oecd(dati, anno_base=ANNO_BASE_INDICI):
    serie_ribasate = []
    for valori_gruppo, gruppo in dati.groupby(["country_code", "measure_code"], dropna=False):
        base = gruppo.loc[gruppo["time_period"].astype(str) == str(anno_base), "value"]
        if base.empty or base.iloc[0] == 0:
            continue

        ordinato = gruppo.sort_values("data_plot").copy()
        ordinato["value"] = ordinato["value"] / base.iloc[0] * 100
        serie_ribasate.append(ordinato)

    if not serie_ribasate:
        return pd.DataFrame(columns=dati.columns)
    return pd.concat(serie_ribasate, ignore_index=True)


def grafico_linee_oecd(dati, misura, titolo, nome_file, cartella_output, anno_base=ANNO_BASE_INDICI):
    serie = dati.loc[dati["measure_code"] == misura].copy()
    if serie.empty:
        return None

    figura, asse = plt.subplots(figsize=(11, 6))
    for paese, gruppo in serie.groupby("country_code"):
        gruppo = gruppo.sort_values("data_plot")
        colore = COLORE_ITALIA if paese == "ITA" else None
        larghezza = 2.8 if paese == "ITA" else 1.7
        alpha = 1 if paese == "ITA" else 0.72
        asse.plot(gruppo["data_plot"], gruppo["value"], label=paese, color=colore, linewidth=larghezza, alpha=alpha)

    asse.set_title(f"{titolo} ({anno_base}=100)", fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel(f"indice {anno_base}=100")
    asse.grid(alpha=0.22)
    formatta_asse_y(asse)
    asse.legend(loc="best", frameon=False, ncol=2)
    figura.text(
        0.01,
        0.01,
        f"Fonte: OECD (DF_HOUSE_PRICES) | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=9,
        alpha=0.82,
    )

    percorso = cartella_oecd(cartella_output) / nome_file
    salva_figura(figura, percorso)
    return percorso


def crea_grafici_oecd(cartella_output="outputs/charts", paesi=None, mostra_progresso=False):
    if mostra_progresso:
        print("Scarico dati OECD DF_HOUSE_PRICES per confronti multi-paese.", flush=True)

    dati = scarica_prezzi_case_oecd(paesi=paesi)
    dati = ribasa_indici_oecd(dati, ANNO_BASE_INDICI)
    percorsi = []
    totale = len(MISURE_PREZZI_CASE)
    for posizione, (misura, titolo, nome_file) in enumerate(MISURE_PREZZI_CASE, start=1):
        if mostra_progresso:
            print(f"[Confronti OECD {posizione}/{totale}] Creo {nome_file}", flush=True)

        percorso = grafico_linee_oecd(dati, misura, titolo, nome_file, cartella_output, anno_base=ANNO_BASE_INDICI)
        if percorso:
            percorsi.append(percorso)

    if mostra_progresso:
        print(f"Confronti OECD completati: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
