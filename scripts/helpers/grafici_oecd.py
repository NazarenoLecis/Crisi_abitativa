from io import StringIO
import matplotlib.pyplot as plt
import pandas as pd
from scripts.helpers.grafici import formatta_asse_y, periodo_to_datetime, salva_figura
from scripts.helpers.paesi import cartella_paese, normalizza_codici_paesi, profilo_paese
from scripts.helpers.utils import OECD_BASE_URL, WATERMARK, scarica_testo


PAESI_DEFAULT = ["ITA", "FRA", "DEU", "ESP", "NLD", "PRT", "GRC", "USA", "GBR"]
ANNO_BASE_INDICI = "2000"
INIZIO_SERIE_OECD = "2000"

MISURE_PREZZI_CASE = [
    ("RHP", "Prezzi reali delle case", "oecd_prezzi_reali_case.png"),
    ("HPI", "Prezzi nominali delle case", "oecd_prezzi_nominali_case.png"),
    ("HPI_YDH", "Rapporto prezzi case / reddito", "oecd_rapporto_prezzi_reddito.png"),
    ("HPI_RPI", "Rapporto prezzi case / affitti", "oecd_rapporto_prezzi_affitti.png"),
]


def cartella_oecd(cartella_output, paese_focus="ITA"):
    return cartella_paese(cartella_output, paese_focus, "confronti")


def scarica_prezzi_case_oecd(paesi=None, misure=None, inizio=INIZIO_SERIE_OECD, fine="2024"):
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


def anno_base_oecd(gruppo, anno_base=ANNO_BASE_INDICI):
    ordinato = gruppo.sort_values("data_plot").copy()
    base_preferita = ordinato.loc[ordinato["time_period"].astype(str) == str(anno_base)]
    if not base_preferita.empty:
        return base_preferita.iloc[0]

    return ordinato.iloc[0]


def ribasa_indici_oecd(dati, anno_base=ANNO_BASE_INDICI):
    serie_ribasate = []
    for valori_gruppo, gruppo in dati.groupby(["country_code", "measure_code"], dropna=False):
        base = anno_base_oecd(gruppo, anno_base=anno_base)
        if pd.isna(base["value"]) or base["value"] == 0:
            continue

        ordinato = gruppo.sort_values("data_plot").copy()
        ordinato["anno_base"] = str(base["time_period"])
        ordinato["value"] = ordinato["value"] / base["value"] * 100
        serie_ribasate.append(ordinato)

    if not serie_ribasate:
        return pd.DataFrame(columns=dati.columns)
    return pd.concat(serie_ribasate, ignore_index=True)


def etichetta_base_oecd(serie, anno_base=ANNO_BASE_INDICI):
    basi = sorted({str(valore) for valore in serie["anno_base"].dropna()})
    if len(basi) == 1:
        return f"{basi[0]}=100"

    basi_numeriche = pd.to_numeric(pd.Series(basi), errors="coerce").dropna()
    if not basi_numeriche.empty and basi_numeriche.min() < int(anno_base):
        return "primo anno disponibile=100"

    return f"{anno_base}=100 o primo anno disponibile"


def nota_base_oecd(serie, anno_base=ANNO_BASE_INDICI):
    basi = sorted({str(valore) for valore in serie["anno_base"].dropna()})
    if len(basi) <= 1:
        return ""

    return f"Base: {anno_base} quando disponibile; altrimenti primo anno disponibile nella serie."


def grafico_linee_oecd(
    dati,
    misura,
    titolo,
    nome_file,
    cartella_output,
    anno_base=ANNO_BASE_INDICI,
    paese_focus="ITA",
    paesi_linee=None,
):
    profilo = profilo_paese(paese_focus)
    serie = dati.loc[dati["measure_code"] == misura].copy()
    if paesi_linee is not None:
        serie = serie.loc[serie["country_code"].isin(paesi_linee)].copy()
    if serie.empty:
        return None

    figura, asse = plt.subplots(figsize=(11, 6))
    for paese, gruppo in serie.groupby("country_code"):
        gruppo = gruppo.sort_values("data_plot")
        colore = profilo["colore"] if paese == profilo["iso3"] else None
        larghezza = 2.8 if paese == profilo["iso3"] else 1.7
        alpha = 1 if paese == profilo["iso3"] else 0.72
        asse.plot(gruppo["data_plot"], gruppo["value"], label=paese, color=colore, linewidth=larghezza, alpha=alpha)

    etichetta_base = etichetta_base_oecd(serie, anno_base=anno_base)
    asse.set_title(f"{titolo} ({etichetta_base})", fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel("indice, base=100")
    asse.grid(alpha=0.22)
    formatta_asse_y(asse)
    asse.legend(loc="best", frameon=False, ncol=2)
    nota_base = nota_base_oecd(serie, anno_base=anno_base)
    if nota_base:
        asse.text(
            0.01,
            0.98,
            nota_base,
            transform=asse.transAxes,
            ha="left",
            va="top",
            fontsize=8.5,
            color="#333333",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.76, "boxstyle": "round,pad=0.25"},
        )
    figura.text(
        0.01,
        0.01,
        f"Fonte: OECD (DF_HOUSE_PRICES) | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=9,
        alpha=0.82,
    )

    percorso = cartella_oecd(cartella_output, paese_focus) / nome_file
    salva_figura(figura, percorso)
    return percorso


def crea_grafici_oecd(cartella_output="outputs/charts", paesi=None, mostra_progresso=False, paesi_confronto=None):
    if mostra_progresso:
        print("Scarico dati OECD DF_HOUSE_PRICES per confronti multi-paese.", flush=True)

    paesi_focus = normalizza_codici_paesi(paesi_confronto)
    paesi_download = paesi or sorted(set(PAESI_DEFAULT) | set(paesi_focus))
    dati = scarica_prezzi_case_oecd(paesi=paesi_download)
    dati = ribasa_indici_oecd(dati, ANNO_BASE_INDICI)
    percorsi = []
    totale = len(MISURE_PREZZI_CASE) * len(paesi_focus)
    posizione = 0
    for paese_focus in paesi_focus:
        profilo = profilo_paese(paese_focus)
        paesi_linee = sorted(set(PAESI_DEFAULT) | {paese_focus})
        for misura, titolo, nome_file in MISURE_PREZZI_CASE:
            posizione += 1
            if mostra_progresso:
                print(f"[Confronti OECD {profilo['label']} {posizione}/{totale}] Creo {nome_file}", flush=True)

            percorso = grafico_linee_oecd(
                dati,
                misura,
                titolo,
                nome_file,
                cartella_output,
                anno_base=ANNO_BASE_INDICI,
                paese_focus=paese_focus,
                paesi_linee=paesi_linee,
            )
            if percorso:
                percorsi.append(percorso)

    if mostra_progresso:
        print(f"Confronti OECD completati: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
