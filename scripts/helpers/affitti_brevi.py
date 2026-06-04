from io import BytesIO
from pathlib import Path
import base64
from html import unescape
import re
import sys
import unicodedata
import zipfile

RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import matplotlib.pyplot as plt
import pandas as pd
import requests

from scripts.helpers.grafici import COLORE_PRINCIPALE
from scripts.helpers.grafici_locali_italia import (
    formatta_colorbar_mappa,
    limiti_geojson_regioni,
    normalizza_spazi,
    titolo_su_piu_righe,
)
from scripts.helpers.mappe_comunali_italia import (
    disegna_comune,
    nomi_regioni_da_generare,
    regione_indica_tutte,
    risolvi_regione,
    scarica_geojson_comuni_regione,
    slug_testo,
    tabella_comuni_istat_pulita,
    valore_feature_comunale,
)
from scripts.helpers.paesi import radice_output
from scripts.helpers.utils import WATERMARK, cartella_summary


BDSR_DASHBOARD_CSV_URL = "https://api-bdsr.ministeroturismo.gov.it/ui/user/downloadCsvDashboard"
ISTAT_ABITAZIONI_COMUNI_SDMX_URL = (
    "https://esploradati.istat.it/SDMXWS/rest/data/IT1,DF_DCSS_ABITAZIONI_TV_1/"
    "A..NUM_DW_AV......?startPeriod=2021&endPeriod=2021&"
    "dimensionAtObservation=AllDimensions&format=csvfilewithlabels"
)
ISTAT_ABITAZIONI_SEZIONI_2021_URLS = [
    (
        "https://esploradati.istat.it/databrowser/DWL/PERMPOP/SUBCOM/"
        "Dati_regionali_2021.zip"
    ),
    (
        "https://esploradati.censimentopopolazione.istat.it/databrowser/DWL/PERMPOP/"
        "SUBCOM/Dati_regionali_2021.zip"
    ),
]
ISTAT_FAMIGLIE_TITOLO_GODIMENTO_URL = (
    "http://dati-censimentipermanenti.istat.it/Index.aspx?DataSetCode=DCSS_HUDW"
)
FONTE_AFFITTI_BREVI_BDSR = "Ministero del Turismo - registro CIN"
FONTE_ABITAZIONI_ISTAT = "ISTAT censimento permanente 2021"
FONTE_AFFITTI_TOTALI_ISTAT = "ISTAT titolo di godimento abitazione 2021"
PROFILI_AFFITTI_BREVI = {
    "residenziale": "alloggi turistici in affitto registrati",
    "privati": "locazioni brevi/private non imprenditoriali registrate",
    "c2": "altri alloggi privati registrati",
    "totale": "tutte le strutture registrate",
}
COLONNE_NUMERICHE_BDSR = [
    "Totale strutture con CIN verificato",
    "Totale strutture con CIN non verificato",
    "Totale strutture senza CIN",
    "Totale strutture",
]
MAPPE_AFFITTI_BREVI = [
    (
        "quota_locazioni_brevi_su_affitti_totali_pct",
        "Quota locazioni brevi private sul totale affitti (stima)",
        "% totale affitti",
        "quota_locazioni_brevi_su_affitti_totali.png",
        True,
        1,
    ),
    (
        "quota_bed_breakfast_su_abitazioni_pct",
        "Quota B&B sullo stock abitativo",
        "% abitazioni",
        "quota_bed_breakfast_su_abitazioni.png",
        True,
        2,
    ),
    (
        "quota_hotel_su_abitazioni_pct",
        "Quota hotel sullo stock abitativo",
        "% abitazioni",
        "quota_hotel_su_abitazioni.png",
        True,
        2,
    ),
]
def normalizza_testo_affitti_brevi(testo):
    testo_unicode = unicodedata.normalize("NFKD", str(testo))
    testo_ascii = "".join(carattere for carattere in testo_unicode if not unicodedata.combining(carattere))
    testo_ascii = testo_ascii.lower()
    testo_ascii = re.sub(r"[^a-z0-9]+", " ", testo_ascii)
    return testo_ascii.strip()


def intestazioni_bdsr():
    intestazioni = {
        "Accept": "application/json",
        "Authorization": "Bearer undefined",
        "Lang": "it",
        "User-Agent": "crisi-abitativa/0.1",
    }
    return intestazioni


def scarica_bdsr_dashboard_csv():
    risposta = requests.get(BDSR_DASHBOARD_CSV_URL, timeout=120, headers=intestazioni_bdsr())
    risposta.raise_for_status()
    dati = risposta.json()
    contenuto = base64.b64decode(dati["csv"])
    frame = pd.read_csv(BytesIO(contenuto), dtype=str, keep_default_na=False)
    nome_file = dati.get("nomeFile", "bdsr_dashboard.csv")
    return frame, nome_file


def scarica_abitazioni_comunali_sdmx():
    risposta = requests.get(
        ISTAT_ABITAZIONI_COMUNI_SDMX_URL,
        timeout=(15, 120),
        headers={"User-Agent": "crisi-abitativa/0.1"},
    )
    risposta.raise_for_status()
    frame = pd.read_csv(BytesIO(risposta.content), dtype=str)
    if frame.empty:
        return pd.DataFrame(columns=["codice_istat", "abitazioni_istat_2021"])

    colonne_normalizzate = {normalizza_testo_affitti_brevi(colonna): colonna for colonna in frame.columns}
    colonna_area = colonne_normalizzate.get("ref area") or colonne_normalizzate.get("territorio")
    colonna_valore = colonne_normalizzate.get("obs value") or colonne_normalizzate.get("valore")
    if not colonna_area or not colonna_valore:
        return pd.DataFrame(columns=["codice_istat", "abitazioni_istat_2021"])

    dati = frame[[colonna_area, colonna_valore]].copy()
    dati["codice_istat"] = dati[colonna_area].astype(str).str.extract(r"(\d{6})", expand=False)
    dati["abitazioni_istat_2021"] = pd.to_numeric(dati[colonna_valore], errors="coerce")
    dati = dati.dropna(subset=["codice_istat", "abitazioni_istat_2021"])
    dati = dati.groupby("codice_istat", as_index=False)["abitazioni_istat_2021"].sum()
    return dati


def separatore_csv_istat(testo):
    righe = testo.splitlines()
    prima_riga = righe[0] if righe else ""
    if prima_riga.count(";") >= prima_riga.count(","):
        return ";"

    return ","


def leggi_csv_zip_istat(archivio, nome_file):
    with archivio.open(nome_file) as file_zip:
        campione = file_zip.read(4096)

    testo_campione = campione.decode("latin1", errors="ignore")
    separatore = separatore_csv_istat(testo_campione)
    with archivio.open(nome_file) as file_zip:
        frame = pd.read_csv(file_zip, sep=separatore, dtype=str, encoding="latin1", low_memory=False)

    return frame


def colonne_abitazioni_sezioni_istat(frame):
    colonne = {normalizza_testo_affitti_brevi(colonna): colonna for colonna in frame.columns}
    possibili_codici = [
        "procom",
        "codice comune",
        "cod comune",
        "codcom",
        "codice comune formato numerico",
        "codice istat comune",
    ]
    possibili_abitazioni = [
        "a8",
        "abitazioni totali",
        "abitazioni al 31 dicembre",
    ]
    colonna_codice = next((colonne[nome] for nome in possibili_codici if nome in colonne), None)
    colonna_abitazioni = next((colonne[nome] for nome in possibili_abitazioni if nome in colonne), None)
    return colonna_codice, colonna_abitazioni


def scarica_abitazioni_comunali_zip_istat(mostra_progresso=False):
    for url in ISTAT_ABITAZIONI_SEZIONI_2021_URLS:
        try:
            risposta = requests.get(url, timeout=(15, 180), headers={"User-Agent": "crisi-abitativa/0.1"})
            risposta.raise_for_status()
            archivio = zipfile.ZipFile(BytesIO(risposta.content))
        except (requests.RequestException, zipfile.BadZipFile) as errore:
            if mostra_progresso:
                print(f"[Affitti brevi] Fonte ISTAT non raggiunta: {errore}", flush=True)
            continue

        pezzi = []
        for nome_file in archivio.namelist():
            if not nome_file.lower().endswith((".csv", ".txt")):
                continue

            try:
                frame = leggi_csv_zip_istat(archivio, nome_file)
            except (UnicodeDecodeError, ValueError) as errore:
                if mostra_progresso:
                    print(f"[Affitti brevi] Salto {nome_file}: {errore}", flush=True)
                continue

            colonna_codice, colonna_abitazioni = colonne_abitazioni_sezioni_istat(frame)
            if not colonna_codice or not colonna_abitazioni:
                continue

            dati = frame[[colonna_codice, colonna_abitazioni]].copy()
            dati["codice_istat"] = dati[colonna_codice].astype(str).str.extract(r"(\d{6})", expand=False)
            dati["abitazioni_istat_2021"] = pd.to_numeric(
                dati[colonna_abitazioni].astype(str).str.replace(",", ".", regex=False),
                errors="coerce",
            )
            dati = dati.dropna(subset=["codice_istat", "abitazioni_istat_2021"])
            if not dati.empty:
                pezzi.append(dati[["codice_istat", "abitazioni_istat_2021"]])

        if pezzi:
            risultato = pd.concat(pezzi, ignore_index=True)
            risultato = risultato.groupby("codice_istat", as_index=False)["abitazioni_istat_2021"].sum()
            return risultato

    return pd.DataFrame(columns=["codice_istat", "abitazioni_istat_2021"])


def scarica_abitazioni_comunali_istat(mostra_progresso=False):
    try:
        dati = scarica_abitazioni_comunali_sdmx()
    except requests.RequestException as errore:
        if mostra_progresso:
            print(f"[Affitti brevi] API ISTAT abitazioni non raggiunta: {errore}", flush=True)
        dati = pd.DataFrame(columns=["codice_istat", "abitazioni_istat_2021"])

    if not dati.empty:
        return dati

    return scarica_abitazioni_comunali_zip_istat(mostra_progresso=mostra_progresso)


def testo_html_pulito(testo):
    testo_senza_tag = re.sub(r"<[^>]+>", " ", str(testo), flags=re.S)
    testo_decodificato = unescape(testo_senza_tag).replace("\xa0", " ")
    testo_decodificato = re.sub(r"\s+", " ", testo_decodificato)
    return testo_decodificato.strip()


def numero_da_tabella_istat(testo):
    testo_pulito = testo_html_pulito(testo)
    testo_pulito = testo_pulito.replace(".", "")
    testo_pulito = testo_pulito.replace(" ", "")
    testo_pulito = testo_pulito.replace(",", ".")
    return pd.to_numeric(testo_pulito, errors="coerce")


def attributi_input_html(frammento):
    attributi = {}
    for nome, valore in re.findall(r"""([A-Za-z0-9_:]+)=["']([^"']*)["']""", frammento):
        attributi[nome.lower()] = unescape(valore)

    return attributi


def campi_form_callback_istat(testo_html):
    campi = {}
    for input_html in re.findall(r"<input\b[^>]*>", testo_html, flags=re.I | re.S):
        attributi = attributi_input_html(input_html)
        tipo = attributi.get("type", "").lower()
        nome = attributi.get("name")
        identifiant = attributi.get("id", "")
        if not nome:
            continue

        tipi_testuali = {
            "hidden",
            "text",
            "password",
            "search",
            "tel",
            "url",
            "email",
            "number",
            "range",
            "color",
            "datetime",
            "date",
            "month",
            "week",
            "time",
            "datetime-local",
        }
        if tipo in tipi_testuali and identifiant != "__EVENTVALIDATION":
            campi[nome] = attributi.get("value", "")

    return campi


def valore_input_html(testo_html, modello_id):
    modello = re.compile(
        r"<input\b[^>]*id=[\"'][^\"']*" + modello_id + r"[^\"']*[\"'][^>]*>",
        flags=re.I | re.S,
    )
    corrispondenza = modello.search(testo_html)
    if not corrispondenza:
        return ""

    attributi = attributi_input_html(corrispondenza.group(0))
    return attributi.get("value", "")


def risposta_callback_istat(testo):
    separatore = testo.find("|")
    if separatore != -1 and testo[:separatore].isdigit():
        lunghezza = int(testo[:separatore])
        inizio = separatore + 1
        evento_validazione = testo[inizio : inizio + lunghezza]
        frammento = testo[inizio + lunghezza :]
        return evento_validazione, frammento

    if testo.startswith("s"):
        return "", testo[1:]

    return "", testo


def prossima_pagina_istat(testo_html):
    corrispondenza = re.search(
        r"title=[\"']Next page[\"'][^>]*ChgPageNumberSel\((\d+),",
        testo_html,
        flags=re.I | re.S,
    )
    if not corrispondenza:
        return None

    return int(corrispondenza.group(1))


def righe_tenure_istat_da_html(testo_html, contesto):
    righe = []
    for riga_html in re.findall(r"<tr\b[^>]*>(.*?)</tr>", testo_html, flags=re.I | re.S):
        celle = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", riga_html, flags=re.I | re.S)
        if len(celle) < 6:
            continue

        margine = re.search(r"margin-left\s*:\s*(\d+)px", celle[0], flags=re.I)
        if not margine:
            continue

        livello = int(margine.group(1))
        territorio = testo_html_pulito(celle[0])
        if livello == 16:
            contesto["regione"] = territorio
            contesto["provincia"] = ""
            continue

        if livello == 24:
            contesto["provincia"] = territorio
            continue

        if livello != 33 or not contesto.get("regione") or not contesto.get("provincia"):
            continue

        righe.append(
            {
                "regione_istat": contesto["regione"],
                "provincia_istat": contesto["provincia"],
                "comune_istat": territorio,
                "famiglie_proprieta_istat_2021": numero_da_tabella_istat(celle[2]),
                "famiglie_affitto_istat_2021": numero_da_tabella_istat(celle[3]),
                "famiglie_altro_titolo_istat_2021": numero_da_tabella_istat(celle[4]),
                "famiglie_totali_istat_2021": numero_da_tabella_istat(celle[5]),
            }
        )

    return righe


def scarica_pagina_tenure_istat(sessione, url, campi_form, evento_validazione, subsessione, pagina):
    campi = dict(campi_form)
    campi["__CALLBACKID"] = "__Page"
    campi["__CALLBACKPARAM"] = f"CallBack2&NOSORT&{pagina}&false&&&&{subsessione}&false&"
    if evento_validazione:
        campi["__EVENTVALIDATION"] = evento_validazione

    risposta = sessione.post(
        url,
        data=campi,
        timeout=(15, 90),
        headers={"Referer": url},
    )
    risposta.raise_for_status()
    nuovo_evento_validazione, frammento = risposta_callback_istat(risposta.text)
    return nuovo_evento_validazione, frammento


def mappa_tenure_comuni_istat(frame):
    comuni = tabella_comuni_istat_pulita()
    comuni = comuni[
        [
            "codice_istat",
            "regione",
            "unita_sovracomunale",
            "comune",
        ]
    ].drop_duplicates("codice_istat")
    comuni["chiave_completa"] = [
        chiave_comune_regione(regione + "|" + provincia, comune)
        for regione, provincia, comune in zip(comuni["regione"], comuni["unita_sovracomunale"], comuni["comune"])
    ]
    comuni["chiave_regione_comune"] = [
        chiave_comune_regione(regione, comune)
        for regione, comune in zip(comuni["regione"], comuni["comune"])
    ]

    mappa_completa = comuni.drop_duplicates("chiave_completa").set_index("chiave_completa")["codice_istat"]
    chiavi_univoche = comuni.loc[~comuni["chiave_regione_comune"].duplicated(keep=False)].copy()
    mappa_regione_comune = chiavi_univoche.set_index("chiave_regione_comune")["codice_istat"]

    dati = frame.copy()
    dati["chiave_completa"] = [
        chiave_comune_regione(regione + "|" + provincia, comune)
        for regione, provincia, comune in zip(dati["regione_istat"], dati["provincia_istat"], dati["comune_istat"])
    ]
    dati["chiave_regione_comune"] = [
        chiave_comune_regione(regione, comune)
        for regione, comune in zip(dati["regione_istat"], dati["comune_istat"])
    ]
    dati["codice_istat"] = dati["chiave_completa"].map(mappa_completa)
    codice_da_nome = dati["chiave_regione_comune"].map(mappa_regione_comune)
    dati.loc[dati["codice_istat"].isna() & codice_da_nome.notna(), "codice_istat"] = codice_da_nome
    dati = dati.dropna(subset=["codice_istat"]).copy()
    dati["codice_istat"] = dati["codice_istat"].astype(str).str.zfill(6)
    return dati


def scarica_famiglie_affitto_comunali_istat(mostra_progresso=False):
    sessione = requests.Session()
    sessione.headers.update({"User-Agent": "crisi-abitativa/0.1"})
    risposta = sessione.get(ISTAT_FAMIGLIE_TITOLO_GODIMENTO_URL, timeout=(15, 90))
    risposta.raise_for_status()

    campi_form = campi_form_callback_istat(risposta.text)
    evento_validazione = valore_input_html(risposta.text, "__EVENTVALIDATION")
    subsessione = valore_input_html(risposta.text, "TBSubSessionId")
    contesto = {"regione": "", "provincia": ""}
    tutte_le_righe = []
    frammento = risposta.text
    pagina = 1
    limite_pagine = 40

    while pagina <= limite_pagine:
        righe = righe_tenure_istat_da_html(frammento, contesto)
        tutte_le_righe.extend(righe)
        prossima = prossima_pagina_istat(frammento)
        if mostra_progresso:
            totale = formatta_numero_intero(len(tutte_le_righe))
            print(f"[Affitti brevi] ISTAT titolo godimento pagina {pagina}: {totale} comuni letti.", flush=True)

        if not prossima or prossima <= pagina:
            break

        pagina = prossima
        nuovo_evento_validazione, frammento = scarica_pagina_tenure_istat(
            sessione,
            ISTAT_FAMIGLIE_TITOLO_GODIMENTO_URL,
            campi_form,
            evento_validazione,
            subsessione,
            pagina,
        )
        if nuovo_evento_validazione:
            evento_validazione = nuovo_evento_validazione

        campi_form.update(campi_form_callback_istat(frammento))

    if not tutte_le_righe:
        return pd.DataFrame(columns=["codice_istat", "famiglie_affitto_istat_2021"])

    dati = pd.DataFrame(tutte_le_righe)
    dati = mappa_tenure_comuni_istat(dati)
    colonne = [
        "codice_istat",
        "famiglie_proprieta_istat_2021",
        "famiglie_affitto_istat_2021",
        "famiglie_altro_titolo_istat_2021",
        "famiglie_totali_istat_2021",
    ]
    dati = dati[colonne].copy()
    dati = dati.groupby("codice_istat", as_index=False).sum(numeric_only=True)
    return dati


def valori_numerici(serie):
    testo = serie.astype(str).str.strip()
    testo = testo.str.replace(".", "", regex=False)
    testo = testo.str.replace(",", ".", regex=False)
    return pd.to_numeric(testo, errors="coerce").fillna(0)


def prepara_colonne_numeriche_bdsr(frame):
    dati = frame.copy()
    for colonna in COLONNE_NUMERICHE_BDSR:
        if colonna in dati.columns:
            dati[colonna] = valori_numerici(dati[colonna])
        else:
            dati[colonna] = 0

    return dati


def filtra_profilo_bdsr(frame, profilo):
    if profilo == "totale":
        return frame.copy()

    macrocategoria = frame["Codice Macrocategoria ISTAT"].astype(str).str.upper()
    categoria = frame["Codice Categoria ISTAT"].astype(str).str.upper()
    if profilo == "privati":
        maschera = macrocategoria == "C"
    elif profilo == "c2":
        maschera = categoria == "C2"
    else:
        maschera = (macrocategoria == "C") | categoria.isin(["B4", "C1", "C2"])

    return frame.loc[maschera].copy()


def maschera_alloggi_turistici_affitto(frame):
    macrocategoria = frame["Codice Macrocategoria ISTAT"].astype(str).str.upper()
    categoria = frame["Codice Categoria ISTAT"].astype(str).str.upper()
    maschera = (macrocategoria == "C") | categoria.eq("B4")
    return maschera


def maschera_locazioni_brevi_private(frame):
    macrocategoria = frame["Codice Macrocategoria ISTAT"].astype(str).str.upper()
    categoria = frame["Codice Categoria ISTAT"].astype(str).str.upper()
    maschera = (macrocategoria == "C") & categoria.eq("C2")
    return maschera


def aggrega_bdsr_per_comune(frame):
    dati = frame.copy()
    if "codice_istat" not in dati.columns:
        dati["codice_istat"] = codice_istat_bdsr(dati)

    raggruppamento = (
        dati.groupby("codice_istat", as_index=False)[COLONNE_NUMERICHE_BDSR]
        .sum()
        .rename(
            columns={
                "Totale strutture con CIN verificato": "cin_verificati",
                "Totale strutture con CIN non verificato": "cin_non_verificati",
                "Totale strutture senza CIN": "senza_cin",
                "Totale strutture": "totale_strutture",
            }
        )
    )
    return raggruppamento


def codice_istat_bdsr(frame):
    codice = (
        frame["Codice ISTAT Provincia"].astype(str).str.zfill(3)
        + frame["Codice ISTAT Comune"].astype(str).str.zfill(3)
    )
    return codice


def chiave_comune_regione(regione, comune):
    chiave = normalizza_testo_affitti_brevi(regione) + "|" + normalizza_testo_affitti_brevi(comune)
    return chiave


def mappa_codici_comuni_per_nome(comuni):
    dati = comuni[["regione", "comune", "codice_istat"]].drop_duplicates().copy()
    dati["chiave_comune_regione"] = [
        chiave_comune_regione(regione, comune)
        for regione, comune in zip(dati["regione"], dati["comune"])
    ]
    duplicati = dati["chiave_comune_regione"].duplicated(keep=False)
    dati = dati.loc[~duplicati].copy()
    mappa = dati.set_index("chiave_comune_regione")["codice_istat"].to_dict()
    return mappa


def aggiungi_codice_istat_corrente_bdsr(frame, comuni):
    dati = frame.copy()
    dati["codice_istat_bdsr"] = codice_istat_bdsr(dati)
    dati["codice_istat"] = dati["codice_istat_bdsr"]

    codici_attuali = set(comuni["codice_istat"].astype(str).str.zfill(6))
    dati["codice_istat"] = dati["codice_istat"].astype(str).str.zfill(6)
    maschera_non_corrente = ~dati["codice_istat"].isin(codici_attuali)
    if not maschera_non_corrente.any():
        return dati

    mappa_nome = mappa_codici_comuni_per_nome(comuni)
    chiavi = [
        chiave_comune_regione(regione, comune)
        for regione, comune in zip(dati["Regione"], dati["Comune"])
    ]
    dati["chiave_comune_regione"] = chiavi
    codici_da_nome = dati["chiave_comune_regione"].map(mappa_nome)
    dati.loc[maschera_non_corrente & codici_da_nome.notna(), "codice_istat"] = codici_da_nome
    dati = dati.drop(columns=["chiave_comune_regione"])
    return dati


def aggrega_bdsr_per_comune_filtrato(frame, maschera, nome_colonna):
    filtrati = frame.loc[maschera].copy()
    if filtrati.empty:
        return pd.DataFrame(columns=["codice_istat", nome_colonna])

    aggregato = aggrega_bdsr_per_comune(filtrati)
    aggregato = aggregato[["codice_istat", "totale_strutture"]].rename(columns={"totale_strutture": nome_colonna})
    return aggregato


def maschera_hotel_bdsr(frame):
    macrocategoria = frame["Codice Macrocategoria ISTAT"].astype(str).str.upper()
    categoria = frame["Codice Categoria ISTAT"].astype(str).str.upper()
    maschera = (macrocategoria == "A") | (categoria == "A1")
    return maschera


def maschera_bed_breakfast_bdsr(frame):
    macrocategoria = frame["Codice Macrocategoria ISTAT"].astype(str).str.upper()
    categoria = frame["Codice Categoria ISTAT"].astype(str).str.upper()
    sottocategoria = frame["Codice Sottocategoria ISTAT"].astype(str).str.upper()
    descrizione = frame["Sottocategoria ISTAT"].astype(str).map(normalizza_testo_affitti_brevi)
    categoria_non_alberghiera = (macrocategoria != "A") & (categoria != "A1")
    maschera = categoria.eq("C1") | sottocategoria.eq("B407")
    maschera = maschera | (categoria_non_alberghiera & descrizione.str.contains("prima colazione", na=False))
    return maschera


def riepilogo_categorie_bdsr(frame):
    dati = prepara_colonne_numeriche_bdsr(frame)
    colonne_categoria = [
        "Codice Macrocategoria ISTAT",
        "Macrocategoria ISTAT",
        "Codice Categoria ISTAT",
        "Categoria ISTAT",
        "Codice Sottocategoria ISTAT",
        "Sottocategoria ISTAT",
    ]
    riepilogo = (
        dati.groupby(colonne_categoria, dropna=False, as_index=False)[COLONNE_NUMERICHE_BDSR]
        .sum()
        .sort_values("Totale strutture", ascending=False)
    )
    return riepilogo


def prepara_affitti_brevi_bdsr(frame, profilo="residenziale"):
    dati = prepara_colonne_numeriche_bdsr(frame)
    comuni = tabella_comuni_istat_pulita()
    comuni = comuni[
        [
            "codice_istat",
            "codice_catastale",
            "comune",
            "provincia",
            "regione",
            "codice_regione_istat",
            "unita_sovracomunale",
        ]
    ].drop_duplicates("codice_istat")
    dati = aggiungi_codice_istat_corrente_bdsr(dati, comuni)
    profilo_filtrato = filtra_profilo_bdsr(dati, profilo)

    totale_comuni = aggrega_bdsr_per_comune(dati).rename(
        columns={
            "totale_strutture": "strutture_bdsr_totali",
            "cin_verificati": "cin_verificati_bdsr_totali",
            "cin_non_verificati": "cin_non_verificati_bdsr_totali",
            "senza_cin": "senza_cin_bdsr_totali",
        }
    )
    profilo_comuni = aggrega_bdsr_per_comune(profilo_filtrato).rename(
        columns={
            "totale_strutture": "unita_affitti_brevi",
            "cin_verificati": "cin_verificati_affitti_brevi",
            "cin_non_verificati": "cin_non_verificati_affitti_brevi",
            "senza_cin": "senza_cin_affitti_brevi",
        }
    )
    alloggi_turistici_affitto = aggrega_bdsr_per_comune_filtrato(
        dati,
        maschera_alloggi_turistici_affitto(dati),
        "alloggi_turistici_affitto_registrati",
    )
    locazioni_brevi_private = aggrega_bdsr_per_comune_filtrato(
        dati,
        maschera_locazioni_brevi_private(dati),
        "locazioni_brevi_private_registrate",
    )
    hotel_comuni = aggrega_bdsr_per_comune_filtrato(dati, maschera_hotel_bdsr(dati), "hotel_bdsr")
    bed_breakfast_comuni = aggrega_bdsr_per_comune_filtrato(
        dati,
        maschera_bed_breakfast_bdsr(dati),
        "bed_breakfast_bdsr",
    )

    risultato = comuni.merge(totale_comuni, on="codice_istat", how="left")
    risultato = risultato.merge(profilo_comuni, on="codice_istat", how="left")
    risultato = risultato.merge(alloggi_turistici_affitto, on="codice_istat", how="left")
    risultato = risultato.merge(locazioni_brevi_private, on="codice_istat", how="left")
    risultato = risultato.merge(hotel_comuni, on="codice_istat", how="left")
    risultato = risultato.merge(bed_breakfast_comuni, on="codice_istat", how="left")
    colonne_da_azzerare = [
        "strutture_bdsr_totali",
        "cin_verificati_bdsr_totali",
        "cin_non_verificati_bdsr_totali",
        "senza_cin_bdsr_totali",
        "unita_affitti_brevi",
        "cin_verificati_affitti_brevi",
        "cin_non_verificati_affitti_brevi",
        "senza_cin_affitti_brevi",
        "alloggi_turistici_affitto_registrati",
        "locazioni_brevi_private_registrate",
        "hotel_bdsr",
        "bed_breakfast_bdsr",
    ]
    for colonna in colonne_da_azzerare:
        risultato[colonna] = risultato[colonna].fillna(0)

    risultato["profilo_affitti_brevi"] = profilo
    risultato["descrizione_profilo_affitti_brevi"] = PROFILI_AFFITTI_BREVI.get(profilo, profilo)
    risultato = aggiungi_indicatori_affitti_brevi(risultato)
    return risultato


def aggiungi_indicatori_affitti_brevi(frame):
    dati = frame.copy()
    colonne_base = [
        "hotel_bdsr",
        "bed_breakfast_bdsr",
        "locazioni_brevi_private_registrate",
    ]
    for colonna in colonne_base:
        if colonna not in dati.columns:
            dati[colonna] = 0

    dati["unita_affitti_brevi"] = pd.to_numeric(dati["unita_affitti_brevi"], errors="coerce").fillna(0)
    dati["strutture_bdsr_totali"] = pd.to_numeric(dati["strutture_bdsr_totali"], errors="coerce")
    dati["hotel_bdsr"] = pd.to_numeric(dati["hotel_bdsr"], errors="coerce").fillna(0)
    dati["bed_breakfast_bdsr"] = pd.to_numeric(dati["bed_breakfast_bdsr"], errors="coerce").fillna(0)
    dati["locazioni_brevi_private_registrate"] = pd.to_numeric(
        dati["locazioni_brevi_private_registrate"],
        errors="coerce",
    ).fillna(0)
    return dati


def aggiungi_affitti_totali_comunali_istat(riepilogo, mostra_progresso=False):
    try:
        affitti_totali = scarica_famiglie_affitto_comunali_istat(mostra_progresso=mostra_progresso)
    except requests.RequestException as errore:
        if mostra_progresso:
            print(f"[Affitti brevi] ISTAT titolo godimento non raggiunto: {errore}", flush=True)
        affitti_totali = pd.DataFrame(columns=["codice_istat", "famiglie_affitto_istat_2021"])

    dati = riepilogo.copy()
    if affitti_totali.empty:
        dati["famiglie_affitto_istat_2021"] = pd.NA
        dati["famiglie_proprieta_istat_2021"] = pd.NA
        dati["famiglie_altro_titolo_istat_2021"] = pd.NA
        dati["famiglie_totali_istat_2021"] = pd.NA
    else:
        affitti_totali["codice_istat"] = affitti_totali["codice_istat"].astype(str).str.zfill(6)
        dati = dati.merge(affitti_totali, on="codice_istat", how="left")

    dati["famiglie_affitto_istat_2021"] = pd.to_numeric(
        dati["famiglie_affitto_istat_2021"],
        errors="coerce",
    )
    dati["affitti_totali_stimati_istat_cin"] = (
        dati["locazioni_brevi_private_registrate"] + dati["famiglie_affitto_istat_2021"]
    )
    denominatore = dati["affitti_totali_stimati_istat_cin"].where(
        dati["affitti_totali_stimati_istat_cin"] > 0
    )
    dati["quota_locazioni_brevi_su_affitti_totali_pct"] = (
        dati["locazioni_brevi_private_registrate"] / denominatore * 100
    )
    return dati


def aggiungi_abitazioni_comunali_istat(riepilogo, mostra_progresso=False):
    abitazioni = scarica_abitazioni_comunali_istat(mostra_progresso=mostra_progresso)
    dati = riepilogo.copy()
    if abitazioni.empty:
        dati["abitazioni_istat_2021"] = pd.NA
    else:
        abitazioni["codice_istat"] = abitazioni["codice_istat"].astype(str).str.zfill(6)
        dati = dati.merge(abitazioni, on="codice_istat", how="left")

    dati["abitazioni_istat_2021"] = pd.to_numeric(dati["abitazioni_istat_2021"], errors="coerce")
    denominatore = dati["abitazioni_istat_2021"].where(dati["abitazioni_istat_2021"] > 0)
    dati["rapporto_affitti_brevi_abitazioni"] = dati["unita_affitti_brevi"] / denominatore
    dati["rapporto_hotel_abitazioni"] = dati["hotel_bdsr"] / denominatore
    dati["rapporto_bed_breakfast_abitazioni"] = dati["bed_breakfast_bdsr"] / denominatore
    dati["quota_hotel_su_abitazioni_pct"] = dati["rapporto_hotel_abitazioni"] * 100
    dati["quota_bed_breakfast_su_abitazioni_pct"] = dati["rapporto_bed_breakfast_abitazioni"] * 100
    return dati


def carica_affitti_brevi(profilo="residenziale"):
    frame, nome_file = scarica_bdsr_dashboard_csv()
    riepilogo = prepara_affitti_brevi_bdsr(frame, profilo=profilo)
    categorie = riepilogo_categorie_bdsr(frame)
    fonte = f"{FONTE_AFFITTI_BREVI_BDSR} ({nome_file})"
    return riepilogo, categorie, fonte


def percorso_grafici_affitti_brevi(cartella_output, sezione=None):
    parti = [radice_output(cartella_output), "italia", "charts", "affitti_brevi"]
    if sezione:
        parti.append(sezione)

    return Path(*parti)


def cartella_grafici_affitti_brevi(cartella_output, sezione=None):
    cartella = percorso_grafici_affitti_brevi(cartella_output, sezione)
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def cartella_summary_affitti_brevi(cartella_output):
    cartella = cartella_summary(cartella_output, "italia_affitti_brevi")
    return cartella


def rimuovi_grafici_affitti_brevi_obsoleti(cartella_output):
    cartella = percorso_grafici_affitti_brevi(cartella_output)
    if not cartella.exists():
        return

    modelli_obsoleti = [
        "*quota" + "_cin_verificati*",
        "*strutture_affitti_brevi*",
        "*strutture_alberghiere*",
        "*bed_breakfast.png",
        "*rapporto_bed_breakfast_hotel*",
        "*quota_bed_breakfast_su_hotel_bed_breakfast*",
        "*per_1000_abitazioni*",
        "*quota_locazioni_brevi_su_affitti_turistici*",
        "*quota_affitti_brevi_su_affitti_turistici*",
    ]
    for modello in modelli_obsoleti:
        for percorso in cartella.rglob(modello):
            if percorso.is_file():
                percorso.unlink()

    cartella_classifiche = cartella / "classifiche"
    if cartella_classifiche.exists():
        for percorso in cartella_classifiche.glob("*.png"):
            if percorso.is_file():
                percorso.unlink()


def rimuovi_mappe_affitti_brevi_regione(cartella_output, regione):
    cartella = percorso_grafici_affitti_brevi(cartella_output, "mappe_comunali") / slug_testo(regione)
    if not cartella.exists():
        return

    for percorso in cartella.glob("*.png"):
        if percorso.is_file():
            percorso.unlink()


def salva_summary_affitti_brevi(riepilogo, categorie, cartella_output):
    cartella = cartella_summary_affitti_brevi(cartella_output)
    percorso_riepilogo = cartella / "affitti_brevi_comuni.csv"
    riepilogo.sort_values(["unita_affitti_brevi", "regione", "comune"], ascending=[False, True, True]).to_csv(
        percorso_riepilogo,
        index=False,
    )

    percorsi = [percorso_riepilogo]
    if categorie is not None and not categorie.empty:
        percorso_categorie = cartella / "affitti_brevi_categorie_bdsr.csv"
        categorie.to_csv(percorso_categorie, index=False)
        percorsi.append(percorso_categorie)

    return percorsi


def formatta_numero_intero(valore):
    try:
        return f"{float(valore):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return ""


def formatta_asse_x_affitti_brevi(asse, percentuale=False):
    if percentuale:
        asse.xaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.0f}%"))
        return

    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    asse.xaxis.set_major_formatter(formatter)
    asse.ticklabel_format(axis="x", style="plain", useOffset=False)


def aggiungi_footer_affitti_brevi(figura, fonte):
    testo = titolo_su_piu_righe(f"Fonte: {fonte} | {WATERMARK}", larghezza=135)
    figura.text(
        0.01,
        0.01,
        testo,
        ha="left",
        va="bottom",
        fontsize=8.5,
        alpha=0.82,
    )


def grafico_barre_affitti_brevi(
    dati,
    colonna,
    titolo,
    etichetta_x,
    nome_file,
    fonte,
    cartella_output,
    percentuale=False,
    top=30,
):
    disponibili = dati.dropna(subset=[colonna]).copy()
    disponibili[colonna] = pd.to_numeric(disponibili[colonna], errors="coerce")
    disponibili = disponibili.dropna(subset=[colonna])
    disponibili = disponibili.loc[disponibili[colonna] > 0].copy()
    if disponibili.empty:
        return None

    disponibili["etichetta"] = disponibili["comune"] + " (" + disponibili["provincia"] + ")"
    disponibili = disponibili.nlargest(top, colonna).sort_values(colonna)
    altezza = max(6.2, 0.31 * len(disponibili) + 2.0)
    figura, asse = plt.subplots(figsize=(11.5, altezza))
    asse.barh(disponibili["etichetta"], disponibili[colonna], color=COLORE_PRINCIPALE)
    asse.set_title(titolo_su_piu_righe(titolo, larghezza=56), loc="left", fontsize=17, fontweight="bold")
    asse.set_xlabel(etichetta_x)
    asse.grid(axis="x", alpha=0.25)
    asse.grid(axis="y", visible=False)
    formatta_asse_x_affitti_brevi(asse, percentuale=percentuale)
    for bordo in ["top", "right"]:
        asse.spines[bordo].set_visible(False)

    figura.subplots_adjust(left=0.29, right=0.96, top=0.88, bottom=0.15)
    aggiungi_footer_affitti_brevi(figura, fonte)
    cartella = cartella_grafici_affitti_brevi(cartella_output, "classifiche")
    percorso = cartella / nome_file
    figura.savefig(percorso, dpi=170)
    plt.close(figura)
    return percorso


def dati_mappa_affitti_brevi(focus, colonna):
    dati = focus.dropna(subset=[colonna, "codice_catastale"]).copy()
    if dati.empty:
        return pd.DataFrame()

    dati[colonna] = pd.to_numeric(dati[colonna], errors="coerce")
    dati = dati.dropna(subset=[colonna])
    if dati.empty:
        return pd.DataFrame()

    dati["codice_catastale_mappa"] = dati["codice_catastale"].map(normalizza_spazi).str.upper()
    dati["codice_istat_mappa"] = dati["codice_istat"].astype(str).str.zfill(6)
    dati["nome_mappa"] = dati["comune"].map(normalizza_testo_affitti_brevi)
    colonne = ["codice_catastale_mappa", "codice_istat_mappa", "nome_mappa", colonna, "comune", "provincia"]
    return dati[colonne].copy()


def fonte_mappa_affitti_brevi(colonna, fonte_bdsr):
    fonte_registro = FONTE_AFFITTI_BREVI_BDSR
    if "abitazioni" in colonna:
        return f"{fonte_registro}, {FONTE_ABITAZIONI_ISTAT}, openpolis GeoJSON comuni"

    if "affitti_totali" in colonna:
        return f"{fonte_registro}, {FONTE_AFFITTI_TOTALI_ISTAT}, openpolis GeoJSON comuni"

    return f"{fonte_registro}, openpolis GeoJSON comuni"


def nota_mappa_affitti_brevi(colonna):
    if "abitazioni" in colonna:
        return (
            "Colore comunale = strutture registrate per 100 abitazioni ISTAT 2021. "
            "Comuni grigi = dato abitazioni mancante."
        )

    if "affitti_totali" in colonna:
        return (
            "Quota stimata: locazioni brevi private registro CIN / "
            "(locazioni brevi private registro CIN + famiglie in affitto ISTAT 2021). "
            "Comuni grigi = dato ISTAT famiglie in affitto mancante."
        )

    return (
        "Indicatore costruito dal registro CIN. "
        "Il registro non misura canoni, notti o contratti di affitto lungo."
    )


def layout_mappa_affitti_brevi(longitudine_min, longitudine_max, latitudine_min, latitudine_max):
    larghezza_geo = max(longitudine_max - longitudine_min, 0.1)
    altezza_geo = max(latitudine_max - latitudine_min, 0.1)
    rapporto_geo = larghezza_geo / altezza_geo

    if rapporto_geo > 1.35:
        figura_larghezza, figura_altezza = 10.8, 6.3
        area_x, area_y, area_larghezza, area_altezza = 0.04, 0.23, 0.76, 0.53
        colorbar = [0.84, 0.24, 0.026, 0.48]
        titolo_y, nota_y = 0.94, 0.79
    elif rapporto_geo < 0.75:
        figura_larghezza, figura_altezza = 8.6, 9.2
        area_x, area_y, area_larghezza, area_altezza = 0.03, 0.10, 0.74, 0.72
        colorbar = [0.82, 0.22, 0.03, 0.54]
        titolo_y, nota_y = 0.94, 0.84
    else:
        figura_larghezza, figura_altezza = 8.9, 8.0
        area_x, area_y, area_larghezza, area_altezza = 0.04, 0.14, 0.74, 0.64
        colorbar = [0.82, 0.22, 0.03, 0.52]
        titolo_y, nota_y = 0.94, 0.83

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


def grafico_mappa_affitti_brevi_regione(
    focus,
    geojson,
    regione,
    colonna,
    titolo,
    legenda,
    nome_file,
    cartella_output,
    fonte,
    nota,
    percentuale=False,
    decimali=0,
):
    dati = dati_mappa_affitti_brevi(focus, colonna)
    if dati.empty:
        return None

    features = geojson["features"]
    valori_catastali = dati.set_index("codice_catastale_mappa")[colonna].to_dict()
    valori_istat = dati.set_index("codice_istat_mappa")[colonna].to_dict()
    valori_nome = dati.set_index("nome_mappa")[colonna].to_dict()
    minimo = float(dati[colonna].min())
    massimo = float(dati[colonna].max())
    if minimo == massimo:
        minimo -= 1
        massimo += 1

    longitudine_min, longitudine_max, latitudine_min, latitudine_max = limiti_geojson_regioni(features)
    dimensione_figura, posizione_asse, posizione_colorbar, titolo_y, nota_y = layout_mappa_affitti_brevi(
        longitudine_min,
        longitudine_max,
        latitudine_min,
        latitudine_max,
    )
    normalizzazione = Normalize(vmin=minimo, vmax=massimo)
    scala_colori = plt.get_cmap("YlOrRd")
    figura = plt.figure(figsize=dimensione_figura)
    asse = figura.add_axes(posizione_asse)
    for feature in features:
        valore = valore_feature_comunale(feature, valori_catastali, valori_istat, valori_nome)
        colore = scala_colori(normalizzazione(valore)) if valore is not None else "#E6E6E6"
        disegna_comune(asse, feature, colore)

    asse.set_xlim(longitudine_min - 0.25, longitudine_max + 0.25)
    asse.set_ylim(latitudine_min - 0.25, latitudine_max + 0.25)
    asse.set_aspect("equal")
    asse.axis("off")
    figura.text(
        0.03,
        titolo_y,
        titolo_su_piu_righe(titolo, larghezza=58),
        ha="left",
        va="top",
        fontsize=14,
        fontweight="bold",
    )
    figura.text(
        0.03,
        nota_y,
        titolo_su_piu_righe(nota, larghezza=82),
        ha="left",
        va="top",
        fontsize=8.5,
        color="#333333",
    )
    mappabile = ScalarMappable(norm=normalizzazione, cmap=scala_colori)
    mappabile.set_array([])
    asse_colorbar = figura.add_axes(posizione_colorbar)
    colorbar = figura.colorbar(mappabile, cax=asse_colorbar)
    colorbar.set_label(legenda, fontsize=9.2)
    formatta_colorbar_mappa(colorbar, percentuale=percentuale, decimali=decimali)
    aggiungi_footer_affitti_brevi(figura, fonte)

    sezione = f"mappe_comunali/{slug_testo(regione)}"
    percorso = cartella_grafici_affitti_brevi(cartella_output, sezione) / nome_file
    figura.savefig(percorso, dpi=170)
    plt.close(figura)
    return percorso


def crea_classifiche_affitti_brevi(riepilogo, cartella_output, fonte):
    percorsi = []
    classifiche = [
        (
            "quota_locazioni_brevi_su_affitti_totali_pct",
            "Comuni con quota piu' alta di locazioni brevi sul totale affitti (stima)",
            "% totale affitti (stima)",
            "top_comuni_quota_locazioni_brevi_su_affitti_totali.png",
            True,
        ),
        (
            "quota_bed_breakfast_su_abitazioni_pct",
            "Comuni con quota piu' alta di B&B sullo stock abitativo",
            "% abitazioni",
            "top_comuni_quota_bed_breakfast_su_abitazioni.png",
            True,
        ),
        (
            "quota_hotel_su_abitazioni_pct",
            "Comuni con quota piu' alta di hotel sullo stock abitativo",
            "% abitazioni",
            "top_comuni_quota_hotel_su_abitazioni.png",
            True,
        ),
    ]
    for colonna, titolo, etichetta_x, nome_file, percentuale in classifiche:
        percorso = grafico_barre_affitti_brevi(
            riepilogo,
            colonna,
            titolo,
            etichetta_x,
            nome_file,
            fonte_mappa_affitti_brevi(colonna, fonte),
            cartella_output,
            percentuale=percentuale,
        )
        if percorso:
            percorsi.append(percorso)

    return percorsi


def crea_mappe_affitti_brevi_regione(riepilogo, regione, cartella_output, fonte, mostra_progresso=False):
    nome_regione, codice_regione = risolvi_regione(riepilogo, regione)
    focus = riepilogo.loc[riepilogo["codice_regione_istat"] == codice_regione].copy()
    if focus.empty:
        return []

    geojson = scarica_geojson_comuni_regione(codice_regione)
    rimuovi_mappe_affitti_brevi_regione(cartella_output, nome_regione)
    percorsi = []
    for colonna, titolo_base, legenda, nome_file, percentuale, decimali in MAPPE_AFFITTI_BREVI:
        valori = pd.to_numeric(focus[colonna], errors="coerce").dropna()
        if valori.empty or not (valori > 0).any():
            if mostra_progresso:
                print(f"[Affitti brevi {nome_regione}] Salto {nome_file}: nessun valore positivo.", flush=True)
            continue

        nome_output = f"{slug_testo(nome_regione)}_comuni_{nome_file}"
        titolo = f"{titolo_base}: comuni della regione {nome_regione}"
        if mostra_progresso:
            print(f"[Affitti brevi {nome_regione}] Creo {nome_output}", flush=True)

        percorso = grafico_mappa_affitti_brevi_regione(
            focus,
            geojson,
            nome_regione,
            colonna,
            titolo,
            legenda,
            nome_output,
            cartella_output,
            fonte_mappa_affitti_brevi(colonna, fonte),
            nota_mappa_affitti_brevi(colonna),
            percentuale=percentuale,
            decimali=decimali,
        )
        if percorso:
            percorsi.append(percorso)

    return percorsi


def regioni_affitti_brevi_da_generare(riepilogo, regione):
    if regione_indica_tutte(regione):
        return nomi_regioni_da_generare("tutte", dati_comuni=riepilogo)

    nome_regione, codice_regione = risolvi_regione(riepilogo, regione)
    return [nome_regione]


def crea_affitti_brevi_italia(
    cartella_output="outputs/charts",
    regione="tutte",
    profilo="residenziale",
    mostra_progresso=False,
):
    if profilo not in PROFILI_AFFITTI_BREVI:
        profili = ", ".join(PROFILI_AFFITTI_BREVI)
        raise ValueError(f"Profilo affitti brevi non valido: {profilo}. Profili disponibili: {profili}")

    if mostra_progresso:
        print("[Affitti brevi] Scarico dati dal registro CIN del Ministero del Turismo.", flush=True)

    rimuovi_grafici_affitti_brevi_obsoleti(cartella_output)
    riepilogo, categorie, fonte = carica_affitti_brevi(profilo=profilo)
    if mostra_progresso:
        totale = formatta_numero_intero(riepilogo["unita_affitti_brevi"].sum())
        print(f"[Affitti brevi] Strutture nel profilo '{profilo}': {totale}", flush=True)
        print("[Affitti brevi] Scarico famiglie in affitto ISTAT per la quota su affitti totali.", flush=True)

    riepilogo = aggiungi_affitti_totali_comunali_istat(riepilogo, mostra_progresso=mostra_progresso)
    if mostra_progresso:
        copertura_affitti = riepilogo["famiglie_affitto_istat_2021"].notna().mean() * 100
        print(f"[Affitti brevi] Copertura famiglie in affitto ISTAT nei comuni: {copertura_affitti:.1f}%.", flush=True)
        print("[Affitti brevi] Scarico abitazioni comunali ISTAT per gli indicatori per stock.", flush=True)

    riepilogo = aggiungi_abitazioni_comunali_istat(riepilogo, mostra_progresso=mostra_progresso)
    if mostra_progresso:
        copertura = riepilogo["abitazioni_istat_2021"].notna().mean() * 100
        print(f"[Affitti brevi] Copertura abitazioni ISTAT nei comuni: {copertura:.1f}%.", flush=True)

    percorsi = []
    percorsi.extend(salva_summary_affitti_brevi(riepilogo, categorie, cartella_output))
    percorsi.extend(crea_classifiche_affitti_brevi(riepilogo, cartella_output, fonte))

    regioni = regioni_affitti_brevi_da_generare(riepilogo, regione)
    if mostra_progresso:
        print(f"[Affitti brevi] Regioni da mappare: {len(regioni)}", flush=True)

    for posizione, nome_regione in enumerate(regioni, start=1):
        if mostra_progresso:
            print(f"[Affitti brevi {posizione}/{len(regioni)}] Avvio {nome_regione}", flush=True)

        percorsi.extend(
            crea_mappe_affitti_brevi_regione(
                riepilogo,
                nome_regione,
                cartella_output,
                fonte,
                mostra_progresso=mostra_progresso,
            )
        )

    if mostra_progresso:
        print(f"[Affitti brevi] Completato: {len(percorsi)} file creati.", flush=True)

    return percorsi
