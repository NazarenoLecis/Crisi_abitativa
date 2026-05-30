from io import BytesIO
from pathlib import Path
import warnings
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import pandas as pd
from grafici import COLORE_EU27, COLORE_ITALIA, COLORE_PRINCIPALE, formatta_asse_y
from utils import WATERMARK, scarica_bytes


OECD_AHD_BASE_URL = "https://webfs.oecd.org/Els-com/Affordable_Housing_Database"

INDICATORI_BARRE = [
    {
        "nome": "Abitazioni per 1.000 abitanti",
        "file": "HM1-1-Housing-stock-and-construction.xlsx",
        "foglio": "HM 1.1.1",
        "colonne": {"paese": 11, "valore": 14, "anno": 15},
        "nome_file": "oecd_ahd_abitazioni_per_1000_abitanti.png",
        "asse_x": "abitazioni per 1.000 abitanti",
        "moltiplicatore": 1,
        "percentuale": False,
        "anno_titolo": "ultimo anno disponibile",
    },
    {
        "nome": "Abitazioni vuote e case stagionali",
        "file": "HM1-1-Housing-stock-and-construction.xlsx",
        "foglio": "HM1.1.2",
        "colonne": {"paese": 12, "valore": 15, "anno": 16},
        "nome_file": "oecd_ahd_abitazioni_vuote_stagionali.png",
        "asse_x": "% dello stock abitativo",
        "moltiplicatore": 1,
        "percentuale": True,
        "anno_titolo": "ultimo anno disponibile",
    },
    {
        "nome": "Peso mediano dei costi abitativi sul reddito",
        "file": "HC1-2-Housing-costs-over-income.xlsx",
        "foglio": "HC12_1",
        "colonne": {"paese": 11, "valore": 14},
        "nome_file": "oecd_ahd_peso_costi_abitativi_reddito.png",
        "asse_x": "% del reddito disponibile",
        "moltiplicatore": 100,
        "percentuale": True,
        "anno_titolo": "2024 o ultimo anno disponibile",
    },
    {
        "nome": "Sovraffollamento abitativo",
        "file": "HC2-1-Living-space.xlsx",
        "foglio": "HC2.1.3",
        "colonne": {"paese": 11, "valore": 15},
        "nome_file": "oecd_ahd_sovraffollamento_abitativo.png",
        "asse_x": "% delle famiglie",
        "moltiplicatore": 1,
        "percentuale": True,
        "anno_titolo": "2024 o ultimo anno disponibile",
    },
    {
        "nome": "Stock di edilizia sociale in affitto",
        "file": "PH4-2-Social-rental-housing-stock.xlsx",
        "foglio": "Figure PH4.2.1",
        "colonne": {"paese": 12, "valore": 13, "anno": 14},
        "nome_file": "oecd_ahd_stock_edilizia_sociale_affitto.png",
        "asse_x": "% dello stock abitativo",
        "moltiplicatore": 1,
        "percentuale": True,
        "anno_titolo": "ultimo anno disponibile",
    },
    {
        "nome": "Spesa pubblica per housing allowances",
        "file": "PH3-1-Public-spending-on-housing-allowances.xlsx",
        "foglio": "Figure_PH 3.1.1",
        "colonne": {"paese": 11, "valore": 12, "anno": 13},
        "nome_file": "oecd_ahd_spesa_housing_allowances.png",
        "asse_x": "% del PIL",
        "moltiplicatore": 100,
        "percentuale": True,
        "anno_titolo": "ultimo anno disponibile",
    },
]


def cartella_oecd_affordable(cartella_output):
    cartella = Path(cartella_output) / "oecd" / "confronti"
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def leggi_foglio_oecd_ahd(nome_file, foglio):
    url = f"{OECD_AHD_BASE_URL}/{nome_file}"
    contenuto = scarica_bytes(url)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        return pd.read_excel(BytesIO(contenuto), sheet_name=foglio, header=None)


def normalizza_paese(valore):
    if pd.isna(valore):
        return ""

    testo = str(valore).strip()
    testo = testo.replace("U.K.", "United Kingdom")
    testo = testo.replace("  ", " ")
    return testo


def estrai_indicatore_barre(indicatore):
    foglio = leggi_foglio_oecd_ahd(indicatore["file"], indicatore["foglio"])
    colonne = indicatore["colonne"]
    tabella = pd.DataFrame(
        {
            "paese": foglio.iloc[:, colonne["paese"]].map(normalizza_paese),
            "value": pd.to_numeric(foglio.iloc[:, colonne["valore"]], errors="coerce"),
        }
    )

    if "anno" in colonne:
        tabella["anno"] = pd.to_numeric(foglio.iloc[:, colonne["anno"]], errors="coerce")
    else:
        tabella["anno"] = pd.NA

    tabella = tabella.loc[(tabella["paese"] != "") & tabella["value"].notna()].copy()
    tabella["value"] = tabella["value"] * indicatore["moltiplicatore"]
    tabella = tabella.drop_duplicates(subset=["paese"], keep="first")
    return tabella.sort_values("value")


def colore_barra(paese):
    if paese == "Italy":
        return COLORE_ITALIA
    if paese in {"EU", "OECD"}:
        return COLORE_EU27
    return COLORE_PRINCIPALE


def formatta_anno(valore):
    if pd.isna(valore):
        return ""

    anno = pd.to_numeric(valore, errors="coerce")
    if pd.notna(anno):
        return str(int(anno))
    return str(valore).strip()


def anni_disponibili_barre(dati):
    if "anno" not in dati.columns:
        return []

    anni = []
    for valore in dati["anno"].dropna():
        anno = formatta_anno(valore)
        if anno:
            anni.append(anno)
    return sorted(set(anni))


def titolo_barre(indicatore, dati):
    anni = anni_disponibili_barre(dati)
    if len(anni) == 1:
        return f"{indicatore['nome']}, {anni[0]}"
    if len(anni) > 1:
        return f"{indicatore['nome']}, {indicatore['anno_titolo']} ({anni[0]}-{anni[-1]})"
    return f"{indicatore['nome']}, {indicatore['anno_titolo']}"


def etichette_paesi_barre(indicatore, dati):
    anni = anni_disponibili_barre(dati)
    if len(anni) <= 1:
        return dati["paese"]

    etichette = []
    for riga in dati.itertuples(index=False):
        anno = formatta_anno(riga.anno)
        etichette.append(f"{riga.paese} ({anno})" if anno else riga.paese)
    return etichette


def aggiungi_footer(figura):
    figura.text(
        0.01,
        0.01,
        f"Fonte: OECD Affordable Housing Database | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#333333",
    )


def salva_grafico(figura, percorso):
    plt.tight_layout(rect=[0, 0.06, 1, 0.96])
    figura.savefig(percorso, dpi=170)
    plt.close(figura)


def grafico_barre_orizzontali(indicatore, dati, cartella_output):
    if dati.empty:
        return None

    altezza = max(6, min(15, 0.28 * len(dati) + 1.8))
    figura, asse = plt.subplots(figsize=(10, altezza))
    colori = [colore_barra(paese) for paese in dati["paese"]]
    asse.barh(etichette_paesi_barre(indicatore, dati), dati["value"], color=colori)
    asse.set_title(titolo_barre(indicatore, dati), fontsize=15, fontweight="bold", loc="left", pad=10)
    asse.set_xlabel(indicatore["asse_x"])
    asse.grid(axis="x", alpha=0.22)
    asse.spines["top"].set_visible(False)
    asse.spines["right"].set_visible(False)

    if indicatore["percentuale"]:
        asse.xaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.0f}%"))
    else:
        formatter = ScalarFormatter(useOffset=False)
        formatter.set_scientific(False)
        asse.xaxis.set_major_formatter(formatter)

    aggiungi_footer(figura)
    percorso = cartella_oecd_affordable(cartella_output) / indicatore["nome_file"]
    salva_grafico(figura, percorso)
    return percorso


def estrai_spesa_abitativa_consumi():
    foglio = leggi_foglio_oecd_ahd(
        "HC1-1-Housing-related-expenditure-of-households.xlsx",
        "Figure HC1.1.2",
    )
    intestazioni = foglio.iloc[2]
    anni = []
    colonne_anni = []
    for posizione, valore in intestazioni.items():
        anno = pd.to_numeric(valore, errors="coerce")
        if pd.notna(anno):
            anni.append(str(int(anno)))
            colonne_anni.append(posizione)

    righe = []
    paesi = {"Italy": "Italia", "EU": "EU", "OECD": "OECD"}
    for posizione_riga in range(3, len(foglio)):
        paese = normalizza_paese(foglio.iat[posizione_riga, 10])
        if paese not in paesi:
            continue
        for anno, posizione_colonna in zip(anni, colonne_anni):
            valore = pd.to_numeric(foglio.iat[posizione_riga, posizione_colonna], errors="coerce")
            if pd.notna(valore):
                righe.append(
                    {
                        "paese": paesi[paese],
                        "time_period": anno,
                        "value": float(valore),
                    }
                )

    dati = pd.DataFrame(righe)
    if dati.empty:
        return dati
    dati["data_plot"] = pd.to_datetime(dati["time_period"], format="%Y")
    return dati.sort_values(["paese", "data_plot"])


def grafico_spesa_abitativa_consumi(cartella_output):
    dati = estrai_spesa_abitativa_consumi()
    if dati.empty:
        return None

    colori = {"Italia": COLORE_ITALIA, "EU": COLORE_EU27, "OECD": COLORE_PRINCIPALE}
    figura, asse = plt.subplots(figsize=(10, 5.8))
    for paese, gruppo in dati.groupby("paese"):
        asse.plot(
            gruppo["data_plot"],
            gruppo["value"],
            color=colori.get(paese, COLORE_PRINCIPALE),
            linewidth=2.3,
            label=paese,
        )

    asse.set_title("Spesa abitativa sui consumi finali delle famiglie", fontsize=15, fontweight="bold", loc="left")
    asse.set_ylabel("% dei consumi finali")
    asse.grid(alpha=0.22)
    asse.spines["top"].set_visible(False)
    asse.spines["right"].set_visible(False)
    formatta_asse_y(asse, percentuale=True)
    asse.legend(frameon=False, loc="best")
    aggiungi_footer(figura)

    percorso = cartella_oecd_affordable(cartella_output) / "oecd_ahd_spesa_abitativa_consumi_famiglie.png"
    salva_grafico(figura, percorso)
    return percorso


def crea_grafici_oecd_affordable(cartella_output="outputs/charts", mostra_progresso=False):
    percorsi = []
    totale = len(INDICATORI_BARRE) + 1
    for posizione, indicatore in enumerate(INDICATORI_BARRE, start=1):
        if mostra_progresso:
            print(f"[OECD AHD {posizione}/{totale}] Creo {indicatore['nome_file']}", flush=True)

        dati = estrai_indicatore_barre(indicatore)
        percorso = grafico_barre_orizzontali(indicatore, dati, cartella_output)
        if percorso:
            percorsi.append(percorso)

    if mostra_progresso:
        print(f"[OECD AHD {totale}/{totale}] Creo oecd_ahd_spesa_abitativa_consumi_famiglie.png", flush=True)

    percorso = grafico_spesa_abitativa_consumi(cartella_output)
    if percorso:
        percorsi.append(percorso)

    if mostra_progresso:
        print(f"OECD Affordable Housing Database completato: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
