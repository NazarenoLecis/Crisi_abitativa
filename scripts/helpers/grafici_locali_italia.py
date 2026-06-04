from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
import html
import re
import textwrap
import time
from urllib.parse import urljoin
from zipfile import ZipFile
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import pandas as pd
import requests
from scripts.helpers.grafici import COLORE_PRINCIPALE, COLORE_EU27
from scripts.helpers.paesi import radice_output
from scripts.helpers.utils import WATERMARK, cartella_summary


OMI_BASE_URL = "https://www1.agenziaentrate.gov.it/servizi/geopoi_omi/"
ISTAT_COMUNI_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx"
MEF_REDDITI_COMUNI_URL = (
    "https://www1.finanze.gov.it/finanze/analisi_stat/public/"
    "v_4_0_0/contenuti/Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.zip"
)
REGIONI_GEOJSON_URL = "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson"
PROVINCE_GEOJSON_URL = "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_provinces.geojson"

CAPOLUOGHI_REGIONE = {
    "Ancona",
    "Aosta",
    "Bari",
    "Bologna",
    "Cagliari",
    "Campobasso",
    "Catanzaro",
    "Firenze",
    "Genova",
    "L'Aquila",
    "Milano",
    "Napoli",
    "Palermo",
    "Perugia",
    "Potenza",
    "Roma",
    "Torino",
    "Trento",
    "Trieste",
    "Venezia",
}

AMBITI_FOCUS_LOCALE = {
    "capoluoghi-provincia": "capoluoghi di provincia, citta' metropolitane e liberi consorzi",
    "capoluoghi-regione": "capoluoghi di regione",
}

VERSIONI_FOCUS_LOCALE = {
    "capoluoghi-regione": "capoluoghi di regione",
    "regioni": "regioni, mediana dei capoluoghi di provincia",
    "province": "province, citta' metropolitane e liberi consorzi",
}

ESEMPI_METRATURE_AFFITTO = [40, 50, 60]
SIGLE_PROVINCE_STORICHE = {
    "CI": "SU",
    "OG": "NU",
    "OT": "SS",
    "VS": "SU",
}

MAPPE_REGIONALI_DA_PROVINCE = [
    (
        "prezzo_mq_mediano",
        "Prezzi di vendita OMI: sintesi regionale delle province",
        "euro/mq",
        "mappa_regioni_da_province_prezzi_vendita_omi.png",
        False,
        0,
    ),
    (
        "affitto_mq_mese_mediano",
        "Canoni di locazione OMI: sintesi regionale delle province",
        "euro/mq/mese",
        "mappa_regioni_da_province_canoni_locazione_omi.png",
        False,
        1,
    ),
    (
        "affitto_40mq_mese",
        "Canone mensile stimato per 40 mq: sintesi regionale delle province",
        "euro al mese",
        "mappa_regioni_da_province_affitto_40mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Affitto stimato per 40 mq sul reddito medio dichiarato: sintesi regionale delle province",
        "% del reddito",
        "mappa_regioni_da_province_affitto_40mq_reddito.png",
        True,
        0,
    ),
    (
        "affitto_60mq_mese",
        "Canone mensile stimato per 60 mq: sintesi regionale delle province",
        "euro al mese",
        "mappa_regioni_da_province_affitto_60mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_60mq_su_reddito_pct",
        "Affitto stimato per 60 mq sul reddito medio dichiarato: sintesi regionale delle province",
        "% del reddito",
        "mappa_regioni_da_province_affitto_60mq_reddito.png",
        True,
        0,
    ),
]

MAPPE_PROVINCIALI = [
    (
        "prezzo_mq_mediano",
        "Prezzi di vendita OMI: province",
        "euro/mq",
        "mappa_province_prezzi_vendita_omi.png",
        False,
        0,
    ),
    (
        "affitto_mq_mese_mediano",
        "Canoni di locazione OMI: province",
        "euro/mq/mese",
        "mappa_province_canoni_locazione_omi.png",
        False,
        1,
    ),
    (
        "anni_reddito_per_80mq",
        "Prezzo di 80 mq in anni di reddito medio dichiarato: province",
        "anni di reddito",
        "mappa_province_anni_reddito_per_80mq.png",
        False,
        1,
    ),
    (
        "affitto_40mq_mese",
        "Canone mensile stimato per 40 mq: province",
        "euro al mese",
        "mappa_province_affitto_40mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Affitto stimato per 40 mq sul reddito medio dichiarato: province",
        "% del reddito",
        "mappa_province_affitto_40mq_reddito.png",
        True,
        0,
    ),
    (
        "affitto_60mq_mese",
        "Canone mensile stimato per 60 mq: province",
        "euro al mese",
        "mappa_province_affitto_60mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_60mq_su_reddito_pct",
        "Affitto stimato per 60 mq sul reddito medio dichiarato: province",
        "% del reddito",
        "mappa_province_affitto_60mq_reddito.png",
        True,
        0,
    ),
]


def intestazioni_omi():
    return {
        "User-Agent": "crisi-abitativa/0.1",
        "Referer": urljoin(OMI_BASE_URL, "index.htm"),
    }


def scarica_json_omi(endpoint, tentativi=4):
    url = urljoin(OMI_BASE_URL, endpoint)
    ultimo_errore = None
    for tentativo in range(1, tentativi + 1):
        try:
            risposta = requests.get(url, timeout=60, headers=intestazioni_omi())
            risposta.raise_for_status()
            return risposta.json()
        except Exception as errore:
            ultimo_errore = errore
            time.sleep(min(8, tentativo * 1.5))

    raise RuntimeError(f"Richiesta OMI fallita per {url}: {ultimo_errore}") from ultimo_errore


def scarica_testo_omi(endpoint, tentativi=4):
    url = urljoin(OMI_BASE_URL, endpoint)
    ultimo_errore = None
    for tentativo in range(1, tentativi + 1):
        try:
            risposta = requests.get(url, timeout=60, headers=intestazioni_omi())
            risposta.raise_for_status()
            return risposta.text
        except Exception as errore:
            ultimo_errore = errore
            time.sleep(min(8, tentativo * 1.5))

    raise RuntimeError(f"Richiesta OMI fallita per {url}: {ultimo_errore}") from ultimo_errore


def normalizza_spazi(testo):
    pulito = str(testo).replace("\n", " ").replace("\xa0", " ")
    pulito = re.sub(r"\s+", " ", pulito)
    return pulito.strip()


def trova_colonna(frame, parole):
    parole_normalizzate = [parola.lower() for parola in parole]
    for colonna in frame.columns:
        testo_colonna = normalizza_spazi(colonna).lower()
        if all(parola in testo_colonna for parola in parole_normalizzate):
            return colonna

    colonne = ", ".join(normalizza_spazi(colonna) for colonna in frame.columns)
    raise KeyError(f"Colonna ISTAT non trovata per {parole}. Colonne disponibili: {colonne}")


def scarica_comuni_istat():
    risposta = requests.get(ISTAT_COMUNI_URL, timeout=120, headers={"User-Agent": "crisi-abitativa/0.1"})
    risposta.raise_for_status()
    return pd.read_excel(BytesIO(risposta.content), dtype=str, keep_default_na=False)


def etichetta_ambito(ambito):
    if ambito in AMBITI_FOCUS_LOCALE:
        return AMBITI_FOCUS_LOCALE[ambito]

    valori = ", ".join(sorted(AMBITI_FOCUS_LOCALE))
    raise ValueError(f"Ambito focus locale non valido: {ambito}. Valori ammessi: {valori}")


def seleziona_comuni_focus(ambito="capoluoghi-provincia"):
    etichetta_ambito(ambito)
    frame = scarica_comuni_istat()
    colonna_comune = trova_colonna(frame, ["denominazione in italiano"])
    colonna_regione = trova_colonna(frame, ["denominazione regione"])
    colonna_provincia = trova_colonna(frame, ["sigla automobilistica"])
    colonna_unita = trova_colonna(frame, ["denominazione dell", "territoriale sovracomunale"])
    colonna_codice = trova_colonna(frame, ["codice catastale"])
    colonna_capoluogo = trova_colonna(frame, ["flag comune capoluogo"])

    dati = frame.copy()
    dati[colonna_comune] = dati[colonna_comune].map(normalizza_spazi)
    dati[colonna_provincia] = dati[colonna_provincia].map(normalizza_spazi)
    dati[colonna_codice] = dati[colonna_codice].map(normalizza_spazi)
    dati[colonna_capoluogo] = dati[colonna_capoluogo].map(normalizza_spazi)

    if ambito == "capoluoghi-regione":
        dati = dati.loc[dati[colonna_comune].isin(CAPOLUOGHI_REGIONE)].copy()
    else:
        dati = dati.loc[dati[colonna_capoluogo] == "1"].copy()

    dati = dati.loc[dati[colonna_codice] != ""].copy()
    dati = dati.sort_values([colonna_regione, colonna_unita, colonna_comune])
    comuni = []
    for riga in dati.itertuples(index=False):
        mappa = dict(zip(dati.columns, riga))
        comuni.append(
            {
                "comune": mappa[colonna_comune],
                "provincia": mappa[colonna_provincia],
                "regione": mappa[colonna_regione],
                "unita_sovracomunale": mappa[colonna_unita],
                "codice_catastale": mappa[colonna_codice],
                "ambito": ambito,
                "ambito_label": etichetta_ambito(ambito),
            }
        )

    return comuni


def scarica_semestre_omi():
    semestri = scarica_json_omi("zoneomi.php?richiesta=5")
    if not semestri:
        raise RuntimeError("Nessun semestre OMI disponibile")
    return str(semestri[0]["SEMESTRE"])


def formatta_semestre(semestre):
    testo = str(semestre)
    if len(testo) == 5:
        return f"{testo[:4]}-S{testo[-1]}"
    return testo


def valore_numerico_italiano(valore):
    testo = html.unescape(str(valore)).replace("\xa0", " ").strip()
    testo = re.sub(r"<[^>]+>", " ", testo)
    testo = re.sub(r"\s+", " ", testo)
    if not testo:
        return None

    testo = testo.replace(".", "").replace(",", ".")
    trovato = re.search(r"-?\d+(?:\.\d+)?", testo)
    if not trovato:
        return None
    return float(trovato.group(0))


def testo_cella_html(contenuto):
    testo = html.unescape(contenuto)
    testo = re.sub(r"<[^>]+>", " ", testo)
    testo = testo.replace("\xa0", " ")
    testo = re.sub(r"\s+", " ", testo)
    return testo.strip()


def righe_tabella_omi(testo_html):
    tabelle = re.findall(r"<table[^>]*>(.*?)</table>", testo_html, flags=re.IGNORECASE | re.DOTALL)
    if not tabelle:
        return []

    righe = []
    tabella = tabelle[0]
    for riga_html in re.findall(r"<tr[^>]*>(.*?)</tr>", tabella, flags=re.IGNORECASE | re.DOTALL):
        celle = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", riga_html, flags=re.IGNORECASE | re.DOTALL)
        celle = [testo_cella_html(cella) for cella in celle]
        if len(celle) == 8 and celle[0].lower() != "tipologia":
            righe.append(celle)

    return righe


def scarica_quotazioni_zona(citta, zona, semestre):
    codice_catastale = citta["codice_catastale"]
    codice_zona = zona["ZONA"]
    tipologie = scarica_json_omi(
        f"zoneomi.php?richiesta=8&codcom={codice_catastale}&semestre={semestre}&zo={codice_zona}"
    )
    residenziale = [tipologia for tipologia in tipologie if tipologia.get("DESCR_TIPOLOGIA") == "Residenziale"]
    if not residenziale:
        return pd.DataFrame()

    link_zona = residenziale[0]["LINK_ZONA"]
    pagina = scarica_testo_omi(
        f"stampaomi.php?{codice_catastale}/{link_zona}/{semestre}/R/{codice_zona}/0/0"
    )
    righe = []
    for celle in righe_tabella_omi(pagina):
        prezzo_minimo = valore_numerico_italiano(celle[2])
        prezzo_massimo = valore_numerico_italiano(celle[3])
        affitto_minimo = valore_numerico_italiano(celle[5])
        affitto_massimo = valore_numerico_italiano(celle[6])
        righe.append(
            {
                "comune": citta["comune"],
                "provincia": citta["provincia"],
                "codice_catastale": codice_catastale,
                "semestre": semestre,
                "zona": codice_zona,
                "descrizione_zona": zona["DIZIONE"],
                "fascia": zona["FASCIA"],
                "tipologia": celle[0],
                "stato_conservativo": celle[1],
                "prezzo_min_eur_m2": prezzo_minimo,
                "prezzo_max_eur_m2": prezzo_massimo,
                "affitto_min_eur_m2_mese": affitto_minimo,
                "affitto_max_eur_m2_mese": affitto_massimo,
            }
        )

    frame = pd.DataFrame(righe)
    colonne_numeriche = [
        "prezzo_min_eur_m2",
        "prezzo_max_eur_m2",
        "affitto_min_eur_m2_mese",
        "affitto_max_eur_m2_mese",
    ]
    for colonna in colonne_numeriche:
        frame[colonna] = pd.to_numeric(frame[colonna], errors="coerce")
    return frame


def scarica_zona_con_gestione(citta, zona, semestre):
    try:
        frame_zona = scarica_quotazioni_zona(citta, zona, semestre)
        return frame_zona, None
    except Exception as errore:
        messaggio = f"Salto zona {zona.get('ZONA', '')}: {errore}"
        return pd.DataFrame(), messaggio


def stampa_progresso_zone(citta, posizione, totale):
    if posizione == 1 or posizione == totale or posizione % 15 == 0:
        print(
            f"  {citta['comune']}: zone completate {posizione}/{totale}",
            flush=True,
        )


def scarica_quotazioni_citta(citta, semestre, mostra_progresso=False, lavoratori=4):
    zone = scarica_json_omi(f"zoneomi.php?richiesta=3&codcom={citta['codice_catastale']}")
    frames = []
    totale = len(zone)
    if totale == 0:
        return pd.DataFrame()

    if lavoratori <= 1 or totale == 1:
        for posizione, zona in enumerate(zone, start=1):
            if mostra_progresso:
                stampa_progresso_zone(citta, posizione, totale)

            frame_zona, messaggio = scarica_zona_con_gestione(citta, zona, semestre)
            if messaggio and mostra_progresso:
                print(f"  {messaggio}", flush=True)
            if not frame_zona.empty:
                frames.append(frame_zona)
    else:
        lavoratori_effettivi = min(lavoratori, totale)
        with ThreadPoolExecutor(max_workers=lavoratori_effettivi) as esecutore:
            richieste = [
                esecutore.submit(scarica_zona_con_gestione, citta, zona, semestre)
                for zona in zone
            ]
            for posizione, richiesta in enumerate(as_completed(richieste), start=1):
                if mostra_progresso:
                    stampa_progresso_zone(citta, posizione, totale)

                frame_zona, messaggio = richiesta.result()
                if messaggio and mostra_progresso:
                    print(f"  {messaggio}", flush=True)
                if not frame_zona.empty:
                    frames.append(frame_zona)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def filtra_abitazioni_normali(frame):
    abitazioni = frame.loc[
        frame["tipologia"].str.contains("Abitazioni", case=False, na=False)
        & ~frame["tipologia"].str.contains("Box|Posti auto|Autorimesse", case=False, na=False)
    ].copy()
    if abitazioni.empty:
        return abitazioni

    normali = abitazioni.loc[
        abitazioni["stato_conservativo"].str.contains("normale", case=False, na=False)
    ].copy()
    if not normali.empty:
        return normali
    return abitazioni


def riepilogo_quotazioni_citta(frame, citta):
    abitazioni = filtra_abitazioni_normali(frame)
    if abitazioni.empty:
        return None

    abitazioni["prezzo_medio_eur_m2"] = (
        abitazioni["prezzo_min_eur_m2"] + abitazioni["prezzo_max_eur_m2"]
    ) / 2
    abitazioni["affitto_medio_eur_m2_mese"] = (
        abitazioni["affitto_min_eur_m2_mese"] + abitazioni["affitto_max_eur_m2_mese"]
    ) / 2

    zone = (
        abitazioni.groupby("zona", as_index=False)
        .agg(
            prezzo_medio_eur_m2=("prezzo_medio_eur_m2", "median"),
            affitto_medio_eur_m2_mese=("affitto_medio_eur_m2_mese", "median"),
        )
        .dropna(subset=["prezzo_medio_eur_m2"])
    )
    if zone.empty:
        return None

    affitti_validi = zone["affitto_medio_eur_m2_mese"].dropna()
    affitto_mediano = float(affitti_validi.median()) if not affitti_validi.empty else None
    return {
        "comune": citta["comune"],
        "provincia": citta["provincia"],
        "regione": citta["regione"],
        "unita_sovracomunale": citta["unita_sovracomunale"],
        "codice_catastale": citta["codice_catastale"],
        "ambito": citta["ambito"],
        "ambito_label": citta["ambito_label"],
        "semestre_omi": frame["semestre"].iloc[0],
        "zone_omi": int(zone["zona"].nunique()),
        "prezzo_mq_mediano": float(zone["prezzo_medio_eur_m2"].median()),
        "prezzo_mq_min_zona": float(zone["prezzo_medio_eur_m2"].min()),
        "prezzo_mq_max_zona": float(zone["prezzo_medio_eur_m2"].max()),
        "affitto_mq_mese_mediano": affitto_mediano,
        "affitto_mq_mese_min_zona": float(affitti_validi.min()) if not affitti_validi.empty else None,
        "affitto_mq_mese_max_zona": float(affitti_validi.max()) if not affitti_validi.empty else None,
    }


def scarica_redditi_comunali(codici_catastali):
    risposta = requests.get(MEF_REDDITI_COMUNI_URL, timeout=120, headers={"User-Agent": "crisi-abitativa/0.1"})
    risposta.raise_for_status()
    with ZipFile(BytesIO(risposta.content)) as archivio:
        nome_file = archivio.namelist()[0]
        frame = pd.read_csv(archivio.open(nome_file), sep=";", encoding="latin1")

    frame = frame.loc[frame["Codice catastale"].isin(codici_catastali)].copy()
    frame["reddito_medio_dichiarato"] = (
        pd.to_numeric(frame["Reddito complessivo - Ammontare in euro"], errors="coerce")
        / pd.to_numeric(frame["Reddito complessivo - Frequenza"], errors="coerce")
    )
    frame["contribuenti"] = pd.to_numeric(frame["Numero contribuenti"], errors="coerce")
    colonne = [
        "Codice catastale",
        "Anno di imposta",
        "reddito_medio_dichiarato",
        "contribuenti",
    ]
    return frame[colonne].rename(
        columns={
            "Codice catastale": "codice_catastale",
            "Anno di imposta": "anno_redditi_mef",
        }
    )


def aggiungi_indicatori_affordability(focus):
    risultato = focus.copy()
    colonne_superate = [colonna for colonna in risultato.columns if colonna.startswith("affitto_70mq")]
    if colonne_superate:
        risultato = risultato.drop(columns=colonne_superate)

    risultato["prezzo_80mq"] = risultato["prezzo_mq_mediano"] * 80
    risultato["anni_reddito_per_80mq"] = risultato["prezzo_80mq"] / risultato["reddito_medio_dichiarato"]
    for metratura in ESEMPI_METRATURE_AFFITTO:
        risultato[f"affitto_{metratura}mq_mese"] = risultato["affitto_mq_mese_mediano"] * metratura
        risultato[f"affitto_{metratura}mq_annuo"] = risultato[f"affitto_{metratura}mq_mese"] * 12
        risultato[f"affitto_{metratura}mq_su_reddito_pct"] = (
            risultato[f"affitto_{metratura}mq_annuo"] / risultato["reddito_medio_dichiarato"] * 100
        )
    return risultato


def costruisci_focus_locale(mostra_progresso=False, ambito="capoluoghi-provincia", lavoratori_omi=4):
    semestre = scarica_semestre_omi()
    citta_focus = seleziona_comuni_focus(ambito)
    if mostra_progresso:
        print(f"[Focus locale Italia] Semestre OMI disponibile: {formatta_semestre(semestre)}", flush=True)
        print(
            f"[Focus locale Italia] Comuni selezionati: {len(citta_focus)} ({etichetta_ambito(ambito)})",
            flush=True,
        )

    riepiloghi = []
    totale = len(citta_focus)
    for posizione, citta in enumerate(citta_focus, start=1):
        if mostra_progresso:
            print(f"[Focus locale Italia {posizione}/{totale}] Scarico OMI {citta['comune']}", flush=True)

        quotazioni = scarica_quotazioni_citta(
            citta,
            semestre,
            mostra_progresso=mostra_progresso,
            lavoratori=lavoratori_omi,
        )
        riepilogo = riepilogo_quotazioni_citta(quotazioni, citta) if not quotazioni.empty else None
        if riepilogo:
            riepiloghi.append(riepilogo)
        elif mostra_progresso:
            print(f"  Nessun dato residenziale OMI utilizzabile per {citta['comune']}", flush=True)

    if not riepiloghi:
        return pd.DataFrame()

    focus = pd.DataFrame(riepiloghi)
    redditi = scarica_redditi_comunali(focus["codice_catastale"].tolist())
    focus = focus.merge(redditi, on="codice_catastale", how="left")
    focus["etichetta"] = etichette_citta(focus)
    return aggiungi_indicatori_affordability(focus)


def percorso_grafici_locali(cartella_output, sezione=None):
    cartella = radice_output(cartella_output) / "italia" / "charts" / "locale"
    if sezione:
        cartella = cartella / sezione
    return cartella


def cartella_grafici_locali(cartella_output, sezione=None):
    cartella = percorso_grafici_locali(cartella_output, sezione)
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def rimuovi_grafici_province(cartella_output):
    cartella = percorso_grafici_locali(cartella_output, "province")
    if not cartella.exists():
        cartella_mappe = percorso_grafici_locali(cartella_output, "mappe_regioni")
        mappa_superata = cartella_mappe / "mappa_regioni_da_province_anni_reddito_per_80mq.png"
        if mappa_superata.exists():
            mappa_superata.unlink()
        return

    for percorso in cartella.glob("*.png"):
        percorso.unlink()

    cartella_mappe = percorso_grafici_locali(cartella_output, "mappe_regioni")
    mappa_superata = cartella_mappe / "mappa_regioni_da_province_anni_reddito_per_80mq.png"
    if mappa_superata.exists():
        mappa_superata.unlink()


def aggiungi_footer_locale(figura, fonte):
    figura.text(
        0.01,
        0.01,
        f"Fonte: {fonte} | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#333333",
    )


def formato_asse_x(asse, percentuale=False):
    if percentuale:
        asse.xaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.0f}%"))
        return

    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    asse.xaxis.set_major_formatter(formatter)
    asse.ticklabel_format(axis="x", style="plain", useOffset=False)


def formatta_valore_mappa(valore, percentuale=False, decimali=0):
    if pd.isna(valore):
        return ""

    if percentuale:
        return f"{valore:.{decimali}f}%"

    return f"{valore:.{decimali}f}"


def formatta_colorbar_mappa(colorbar, percentuale=False, decimali=0):
    colorbar.ax.yaxis.set_major_formatter(
        FuncFormatter(lambda valore, posizione: formatta_valore_mappa(valore, percentuale, decimali))
    )
    colorbar.ax.tick_params(labelsize=8.5)


def salva_grafico(figura, percorso):
    plt.tight_layout(rect=[0, 0.08, 0.99, 0.95])
    figura.savefig(percorso, dpi=170)
    plt.close(figura)


def titolo_su_piu_righe(titolo, larghezza=72):
    return "\n".join(textwrap.wrap(titolo, width=larghezza, break_long_words=False))


def aggiungi_nota_locale(asse, nota):
    if not nota:
        return

    asse.text(
        0.01,
        0.98,
        nota,
        transform=asse.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        color="#333333",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.76, "boxstyle": "round,pad=0.25"},
    )


def dimensioni_grafico_locale(numero_righe):
    altezza = max(7, min(38, 0.27 * numero_righe + 2.4))
    if numero_righe > 80:
        etichetta = 6.5
    elif numero_righe > 45:
        etichetta = 7.5
    else:
        etichetta = 10

    return altezza, etichetta


def etichette_citta(frame):
    return frame["comune"] + " (" + frame["provincia"] + ")"


def media_ponderata(gruppo, colonna, peso):
    dati = gruppo[[colonna, peso]].copy()
    dati[colonna] = pd.to_numeric(dati[colonna], errors="coerce")
    dati[peso] = pd.to_numeric(dati[peso], errors="coerce")
    dati = dati.dropna(subset=[colonna, peso])
    dati = dati.loc[dati[peso] > 0]
    if dati.empty:
        valori = pd.to_numeric(gruppo[colonna], errors="coerce").dropna()
        return float(valori.median()) if not valori.empty else None

    return float((dati[colonna] * dati[peso]).sum() / dati[peso].sum())


def sigle_territorio(gruppo):
    sigle = sorted({normalizza_spazi(sigla) for sigla in gruppo["provincia"] if normalizza_spazi(sigla)})
    return ", ".join(sigle)


def sigla_da_etichetta(etichetta):
    testo = normalizza_spazi(etichetta)
    trovato = re.search(r"\(([A-Z]{2})\)$", testo)
    if trovato:
        return trovato.group(1)

    return ""


def completa_provincia_da_etichetta(focus):
    if "provincia" not in focus.columns or "etichetta" not in focus.columns:
        return focus

    risultato = focus.copy()
    provincia_testo = risultato["provincia"].map(normalizza_spazi)
    province_mancanti = provincia_testo == ""
    if province_mancanti.any():
        risultato.loc[province_mancanti, "provincia"] = risultato.loc[province_mancanti, "etichetta"].map(
            sigla_da_etichetta
        )

    return risultato


def aggrega_focus_locale(focus, livello):
    if livello == "regioni":
        colonne_gruppo = ["regione"]
    elif livello == "province":
        colonne_gruppo = ["regione", "unita_sovracomunale"]
    else:
        raise ValueError(f"Livello aggregazione non valido: {livello}")

    righe = []
    for chiave, gruppo in focus.groupby(colonne_gruppo, dropna=False):
        if livello == "regioni":
            etichetta = chiave if isinstance(chiave, str) else chiave[0]
            provincia = ""
            unita_sovracomunale = ""
            regione = etichetta
        else:
            chiave_tuple = chiave if isinstance(chiave, tuple) else ("", chiave)
            regione = chiave_tuple[0]
            unita_sovracomunale = chiave_tuple[1]
            provincia = sigle_territorio(gruppo)
            etichetta = f"{unita_sovracomunale} ({provincia})" if provincia else unita_sovracomunale

        righe.append(
            {
                "comune": etichetta,
                "provincia": provincia,
                "regione": regione,
                "unita_sovracomunale": unita_sovracomunale,
                "codice_catastale": "",
                "ambito": livello,
                "ambito_label": VERSIONI_FOCUS_LOCALE[livello],
                "etichetta": etichetta,
                "semestre_omi": gruppo["semestre_omi"].iloc[0],
                "zone_omi": int(pd.to_numeric(gruppo["zone_omi"], errors="coerce").fillna(0).sum()),
                "numero_comuni": int(len(gruppo)),
                "prezzo_mq_mediano": float(pd.to_numeric(gruppo["prezzo_mq_mediano"], errors="coerce").median()),
                "prezzo_mq_min_zona": float(pd.to_numeric(gruppo["prezzo_mq_min_zona"], errors="coerce").min()),
                "prezzo_mq_max_zona": float(pd.to_numeric(gruppo["prezzo_mq_max_zona"], errors="coerce").max()),
                "affitto_mq_mese_mediano": float(
                    pd.to_numeric(gruppo["affitto_mq_mese_mediano"], errors="coerce").median()
                ),
                "affitto_mq_mese_min_zona": float(
                    pd.to_numeric(gruppo["affitto_mq_mese_min_zona"], errors="coerce").min()
                ),
                "affitto_mq_mese_max_zona": float(
                    pd.to_numeric(gruppo["affitto_mq_mese_max_zona"], errors="coerce").max()
                ),
                "anno_redditi_mef": gruppo["anno_redditi_mef"].dropna().iloc[0]
                if gruppo["anno_redditi_mef"].notna().any()
                else None,
                "reddito_medio_dichiarato": media_ponderata(gruppo, "reddito_medio_dichiarato", "contribuenti"),
                "contribuenti": float(pd.to_numeric(gruppo["contribuenti"], errors="coerce").sum()),
            }
        )

    aggregato = pd.DataFrame(righe)
    if aggregato.empty:
        return aggregato
    return aggiungi_indicatori_affordability(aggregato)


def prepara_versione_focus(focus, versione):
    if versione == "capoluoghi-regione":
        dati = focus.loc[focus["comune"].isin(CAPOLUOGHI_REGIONE)].copy()
        dati["ambito"] = versione
        dati["ambito_label"] = VERSIONI_FOCUS_LOCALE[versione]
        dati["numero_comuni"] = 1
        dati["etichetta"] = etichette_citta(dati)
        return dati

    if versione in {"regioni", "province"}:
        return aggrega_focus_locale(focus, versione)

    valori = ", ".join(sorted(VERSIONI_FOCUS_LOCALE))
    raise ValueError(f"Versione focus locale non valida: {versione}. Valori ammessi: {valori}")


def scarica_geojson_regioni():
    risposta = requests.get(REGIONI_GEOJSON_URL, timeout=120, headers={"User-Agent": "crisi-abitativa/0.1"})
    risposta.raise_for_status()
    return risposta.json()


def scarica_geojson_province():
    risposta = requests.get(PROVINCE_GEOJSON_URL, timeout=120, headers={"User-Agent": "crisi-abitativa/0.1"})
    risposta.raise_for_status()
    return risposta.json()


def poligoni_feature_regionale(feature):
    geometria = feature.get("geometry", {})
    tipo = geometria.get("type")
    coordinate = geometria.get("coordinates", [])
    if tipo == "Polygon":
        return [coordinate]
    if tipo == "MultiPolygon":
        return coordinate

    return []


def limiti_geojson_regioni(features):
    longitudini = []
    latitudini = []
    for feature in features:
        for poligono in poligoni_feature_regionale(feature):
            if not poligono:
                continue

            esterno = poligono[0]
            longitudini.extend([punto[0] for punto in esterno])
            latitudini.extend([punto[1] for punto in esterno])

    return min(longitudini), max(longitudini), min(latitudini), max(latitudini)


def disegna_regione(asse, feature, colore):
    for poligono in poligoni_feature_regionale(feature):
        if not poligono:
            continue

        esterno = poligono[0]
        patch = Polygon(
            esterno,
            closed=True,
            facecolor=colore,
            edgecolor="white",
            linewidth=0.65,
        )
        asse.add_patch(patch)


def aggrega_mappa_regionale_da_province(focus, colonna):
    dati = focus.dropna(subset=[colonna]).copy()
    if dati.empty:
        return pd.DataFrame()

    aggregato = (
        dati.groupby("regione", as_index=False)
        .agg(
            valore=(colonna, "median"),
            province=("etichetta", "count"),
        )
        .sort_values("valore", ascending=False)
    )
    return aggregato


def sigla_provincia_per_mappa(valore):
    if pd.isna(valore):
        return ""

    sigla = normalizza_spazi(valore).upper()
    if sigla in SIGLE_PROVINCE_STORICHE:
        return SIGLE_PROVINCE_STORICHE[sigla]

    return sigla


def aggrega_mappa_provinciale(focus, colonna):
    dati = completa_provincia_da_etichetta(focus).dropna(subset=[colonna]).copy()
    if dati.empty:
        return pd.DataFrame()

    dati["sigla_mappa"] = dati["provincia"].map(sigla_provincia_per_mappa)
    dati = dati.loc[dati["sigla_mappa"] != ""].copy()
    if dati.empty:
        return pd.DataFrame()

    aggregato = (
        dati.groupby("sigla_mappa", as_index=False)
        .agg(
            valore=(colonna, "median"),
            territori=("etichetta", "count"),
        )
        .sort_values("valore", ascending=False)
    )
    return aggregato


def grafico_mappa_regionale_da_province(
    focus,
    colonna,
    titolo,
    legenda,
    nome_file,
    cartella_output,
    percentuale=False,
    decimali=0,
    fonte="ISTAT, Agenzia Entrate - OMI, MEF Dipartimento Finanze, openpolis GeoJSON regioni",
    nota="Colore regionale = mediana delle province disponibili nella regione.",
    sezione="mappe_regioni",
):
    dati_regionali = aggrega_mappa_regionale_da_province(focus, colonna)
    if dati_regionali.empty:
        return None

    geojson = scarica_geojson_regioni()
    features = geojson["features"]
    valori = dati_regionali.set_index("regione")["valore"].to_dict()
    minimo = float(dati_regionali["valore"].min())
    massimo = float(dati_regionali["valore"].max())
    if minimo == massimo:
        minimo -= 1
        massimo += 1

    normalizzazione = Normalize(vmin=minimo, vmax=massimo)
    scala_colori = plt.get_cmap("YlOrRd")
    figura, asse = plt.subplots(figsize=(8.2, 9.2))
    for feature in features:
        regione = feature["properties"]["reg_name"]
        valore = valori.get(regione)
        colore = scala_colori(normalizzazione(valore)) if valore is not None else "#E6E6E6"
        disegna_regione(asse, feature, colore)

    longitudine_min, longitudine_max, latitudine_min, latitudine_max = limiti_geojson_regioni(features)
    asse.set_xlim(longitudine_min - 0.7, longitudine_max + 0.7)
    asse.set_ylim(latitudine_min - 0.6, latitudine_max + 0.6)
    asse.set_aspect("equal")
    asse.axis("off")
    asse.set_title(titolo_su_piu_righe(titolo, larghezza=58), fontsize=14, fontweight="bold", loc="left", pad=12)
    mappabile = ScalarMappable(norm=normalizzazione, cmap=scala_colori)
    mappabile.set_array([])
    colorbar = figura.colorbar(mappabile, ax=asse, fraction=0.035, pad=0.02)
    colorbar.set_label(legenda, fontsize=9.2)
    formatta_colorbar_mappa(colorbar, percentuale=percentuale, decimali=decimali)
    aggiungi_nota_locale(asse, nota)
    aggiungi_footer_locale(figura, fonte)

    percorso = cartella_grafici_locali(cartella_output, sezione) / nome_file
    salva_grafico(figura, percorso)
    return percorso


def grafico_mappa_provinciale(
    focus,
    colonna,
    titolo,
    legenda,
    nome_file,
    cartella_output,
    percentuale=False,
    decimali=0,
    fonte="ISTAT, Agenzia Entrate - OMI, MEF Dipartimento Finanze, openpolis GeoJSON province",
    nota="Colore provinciale = valore del capoluogo/provincia disponibile. Sigle sarde storiche aggregate ai confini GeoJSON correnti.",
    sezione="mappe_province",
):
    dati_provinciali = aggrega_mappa_provinciale(focus, colonna)
    if dati_provinciali.empty:
        return None

    geojson = scarica_geojson_province()
    features = geojson["features"]
    valori = dati_provinciali.set_index("sigla_mappa")["valore"].to_dict()
    minimo = float(dati_provinciali["valore"].min())
    massimo = float(dati_provinciali["valore"].max())
    if minimo == massimo:
        minimo -= 1
        massimo += 1

    normalizzazione = Normalize(vmin=minimo, vmax=massimo)
    scala_colori = plt.get_cmap("YlOrRd")
    figura, asse = plt.subplots(figsize=(8.2, 9.2))
    for feature in features:
        sigla = feature["properties"]["prov_acr"]
        valore = valori.get(sigla)
        colore = scala_colori(normalizzazione(valore)) if valore is not None else "#E6E6E6"
        disegna_regione(asse, feature, colore)

    longitudine_min, longitudine_max, latitudine_min, latitudine_max = limiti_geojson_regioni(features)
    asse.set_xlim(longitudine_min - 0.7, longitudine_max + 0.7)
    asse.set_ylim(latitudine_min - 0.6, latitudine_max + 0.6)
    asse.set_aspect("equal")
    asse.axis("off")
    asse.set_title(titolo_su_piu_righe(titolo, larghezza=58), fontsize=14, fontweight="bold", loc="left", pad=12)
    mappabile = ScalarMappable(norm=normalizzazione, cmap=scala_colori)
    mappabile.set_array([])
    colorbar = figura.colorbar(mappabile, ax=asse, fraction=0.035, pad=0.02)
    colorbar.set_label(legenda, fontsize=9.2)
    formatta_colorbar_mappa(colorbar, percentuale=percentuale, decimali=decimali)
    aggiungi_nota_locale(asse, nota)
    aggiungi_footer_locale(figura, fonte)

    percorso = cartella_grafici_locali(cartella_output, sezione) / nome_file
    salva_grafico(figura, percorso)
    return percorso


def crea_mappe_regionali_da_province(focus, cartella_output, mostra_progresso=False):
    percorsi = []
    for colonna, titolo, legenda, nome_file, percentuale, decimali in MAPPE_REGIONALI_DA_PROVINCE:
        if mostra_progresso:
            print(f"[Focus locale Italia - province] Creo mappa regionale {nome_file}", flush=True)

        percorso = grafico_mappa_regionale_da_province(
            focus,
            colonna,
            titolo,
            legenda,
            nome_file,
            cartella_output,
            percentuale=percentuale,
            decimali=decimali,
        )
        if percorso:
            percorsi.append(percorso)

    return percorsi


def crea_mappe_provinciali(focus, cartella_output, mostra_progresso=False):
    percorsi = []
    for colonna, titolo, legenda, nome_file, percentuale, decimali in MAPPE_PROVINCIALI:
        if mostra_progresso:
            print(f"[Focus locale Italia - province] Creo mappa provinciale {nome_file}", flush=True)

        percorso = grafico_mappa_provinciale(
            focus,
            colonna,
            titolo,
            legenda,
            nome_file,
            cartella_output,
            percentuale=percentuale,
            decimali=decimali,
        )
        if percorso:
            percorsi.append(percorso)

    return percorsi


def grafico_barre_locali(
    focus,
    colonna,
    titolo,
    asse_x,
    nome_file,
    fonte,
    cartella_output,
    sezione,
    percentuale=False,
    nota=None,
):
    dati = focus.dropna(subset=[colonna]).sort_values(colonna, ascending=False).copy()
    if dati.empty:
        return None

    altezza, etichetta = dimensioni_grafico_locale(len(dati))
    figura, asse = plt.subplots(figsize=(11, altezza))
    asse.barh(dati["etichetta"], dati[colonna], color=COLORE_PRINCIPALE)
    asse.invert_yaxis()
    asse.set_title(titolo_su_piu_righe(titolo), fontsize=14, fontweight="bold", loc="left", pad=12)
    asse.set_xlabel(asse_x)
    asse.grid(axis="x", alpha=0.22)
    asse.tick_params(axis="y", labelsize=etichetta)
    formato_asse_x(asse, percentuale=percentuale)
    aggiungi_nota_locale(asse, nota)
    aggiungi_footer_locale(figura, fonte)

    percorso = cartella_grafici_locali(cartella_output, sezione) / nome_file
    salva_grafico(figura, percorso)
    return percorso


def grafico_range_zone_vendita(focus, cartella_output, sezione, nome_file, titolo):
    dati = focus.dropna(subset=["prezzo_mq_mediano", "prezzo_mq_min_zona", "prezzo_mq_max_zona"]).copy()
    if dati.empty:
        return None

    dati = dati.sort_values("prezzo_mq_mediano", ascending=False)
    altezza, etichetta = dimensioni_grafico_locale(len(dati))
    figura, asse = plt.subplots(figsize=(11, altezza))
    posizioni = range(len(dati))
    for posizione, riga in zip(posizioni, dati.itertuples(index=False)):
        asse.hlines(
            posizione,
            riga.prezzo_mq_min_zona,
            riga.prezzo_mq_max_zona,
            color=COLORE_EU27,
            linewidth=2,
            alpha=0.65,
        )
        asse.scatter(riga.prezzo_mq_mediano, posizione, color=COLORE_PRINCIPALE, s=46, zorder=3)

    asse.set_yticks(list(posizioni))
    asse.set_yticklabels(dati["etichetta"])
    asse.invert_yaxis()
    asse.set_title(titolo_su_piu_righe(titolo), fontsize=14, fontweight="bold", loc="left", pad=12)
    asse.set_xlabel("euro/mq")
    asse.grid(axis="x", alpha=0.22)
    asse.tick_params(axis="y", labelsize=etichetta)
    formato_asse_x(asse)
    aggiungi_footer_locale(figura, "Agenzia Entrate - OMI")

    percorso = cartella_grafici_locali(cartella_output, sezione) / nome_file
    salva_grafico(figura, percorso)
    return percorso


def sezione_versione(versione):
    return versione.replace("-", "_")


def versioni_da_generare(versione):
    if versione == "tutte":
        return ["capoluoghi-regione", "regioni", "province"]
    if versione in VERSIONI_FOCUS_LOCALE:
        return [versione]

    valori = ["tutte"] + sorted(VERSIONI_FOCUS_LOCALE)
    raise ValueError(f"Versione focus locale non valida: {versione}. Valori ammessi: {', '.join(valori)}")


def salva_summary_locale(focus, cartella_output, versione):
    cartella = cartella_summary(cartella_output, "italia_locale")
    percorso = cartella / f"focus_locale_{sezione_versione(versione)}_omi_mef.csv"
    focus_pulito = completa_provincia_da_etichetta(focus)
    focus_pulito.sort_values("anni_reddito_per_80mq", ascending=False).to_csv(percorso, index=False)
    return percorso


def salva_summary_base_locale(focus, cartella_output):
    cartella = cartella_summary(cartella_output, "italia_locale")
    percorso = cartella / "focus_locale_base_capoluoghi_provincia_omi_mef.csv"
    focus_pulito = completa_provincia_da_etichetta(focus)
    focus_pulito.sort_values("anni_reddito_per_80mq", ascending=False).to_csv(percorso, index=False)
    return percorso


def crea_grafici_versione_locale(focus, versione, cartella_output, mostra_progresso=False):
    if focus.empty:
        if mostra_progresso:
            print(f"Focus locale Italia {versione} non creato: nessun dato disponibile.", flush=True)
        return []

    salva_summary_locale(focus, cartella_output, versione)
    if versione == "province":
        rimuovi_grafici_province(cartella_output)
        if mostra_progresso:
            print(
                "[Focus locale Italia - province] Dettaglio provinciale salvato in CSV; "
                "per i PNG creo mappe regionali e provinciali basate sui valori provinciali.",
                flush=True,
            )

        percorsi_mappe = crea_mappe_regionali_da_province(
            focus,
            cartella_output,
            mostra_progresso=mostra_progresso,
        )
        percorsi_mappe.extend(
            crea_mappe_provinciali(
                focus,
                cartella_output,
                mostra_progresso=mostra_progresso,
            )
        )
        return percorsi_mappe

    sezione = sezione_versione(versione)
    semestre = formatta_semestre(focus["semestre_omi"].iloc[0])
    anno_redditi = int(focus["anno_redditi_mef"].dropna().iloc[0]) if focus["anno_redditi_mef"].notna().any() else ""
    ambito_label = focus["ambito_label"].iloc[0]
    prefisso_file = sezione
    fonte_completa = "ISTAT, Agenzia Entrate - OMI, MEF Dipartimento Finanze"
    nota_omi_affitti = "Quotazioni OMI: mediana semplice delle zone, non canoni di offerta degli annunci."
    percorsi = []
    grafici = [
        (
            "prezzo_mq_mediano",
            f"Prezzi di vendita OMI - {ambito_label}, {semestre}",
            "euro/mq, mediana delle zone OMI",
            f"{prefisso_file}_prezzi_vendita_omi.png",
            fonte_completa,
            False,
            None,
        ),
        (
            "affitto_mq_mese_mediano",
            f"Canoni di locazione OMI - {ambito_label}, {semestre}",
            "euro/mq/mese, mediana delle zone OMI",
            f"{prefisso_file}_canoni_locazione_omi.png",
            fonte_completa,
            False,
            nota_omi_affitti,
        ),
        (
            "anni_reddito_per_80mq",
            f"Prezzo di 80 mq in anni di reddito medio dichiarato - {ambito_label}, redditi {anno_redditi}",
            "anni di reddito medio dichiarato",
            f"{prefisso_file}_anni_reddito_per_80mq.png",
            fonte_completa,
            False,
            None,
        ),
    ]
    for metratura in [40, 60]:
        grafici.append(
            (
                f"affitto_{metratura}mq_mese",
                f"Esempio OMI: canone mensile stimato per {metratura} mq - {ambito_label}, {semestre}",
                f"euro al mese per {metratura} mq",
                f"{prefisso_file}_affitto_{metratura}mq_mese.png",
                fonte_completa,
                False,
                nota_omi_affitti,
            )
        )
        grafici.append(
            (
                f"affitto_{metratura}mq_su_reddito_pct",
                f"Esempio OMI: affitto di {metratura} mq sul reddito medio dichiarato - {ambito_label}, redditi {anno_redditi}",
                "% del reddito medio dichiarato",
                f"{prefisso_file}_affitto_{metratura}mq_reddito.png",
                fonte_completa,
                True,
                nota_omi_affitti,
            )
        )

    for colonna, titolo, asse_x, nome_file, fonte, percentuale, nota in grafici:
        if mostra_progresso:
            print(f"[Focus locale Italia - {versione}] Creo {nome_file}", flush=True)

        percorso = grafico_barre_locali(
            focus,
            colonna,
            titolo,
            asse_x,
            nome_file,
            fonte,
            cartella_output,
            sezione,
            percentuale=percentuale,
            nota=nota,
        )
        if percorso:
            percorsi.append(percorso)

    if mostra_progresso:
        print(f"[Focus locale Italia - {versione}] Creo {prefisso_file}_range_zone_vendita_omi.png", flush=True)

    percorso = grafico_range_zone_vendita(
        focus,
        cartella_output,
        sezione,
        f"{prefisso_file}_range_zone_vendita_omi.png",
        f"Prezzi OMI: mediana e range tra zone - {ambito_label}, {semestre}",
    )
    if percorso:
        percorsi.append(percorso)

    return percorsi


def crea_grafici_locali_italia(
    cartella_output="outputs/charts",
    mostra_progresso=False,
    versione="tutte",
    lavoratori_omi=4,
):
    versioni = versioni_da_generare(versione)
    ambito_base = "capoluoghi-regione" if versioni == ["capoluoghi-regione"] else "capoluoghi-provincia"
    focus_base = costruisci_focus_locale(
        mostra_progresso=mostra_progresso,
        ambito=ambito_base,
        lavoratori_omi=lavoratori_omi,
    )
    if focus_base.empty:
        if mostra_progresso:
            print("Focus locale Italia non creato: nessun dato disponibile.", flush=True)
        return []

    if ambito_base == "capoluoghi-provincia":
        salva_summary_base_locale(focus_base, cartella_output)

    percorsi = []
    for versione_corrente in versioni:
        focus_versione = prepara_versione_focus(focus_base, versione_corrente)
        if mostra_progresso:
            print(
                f"[Focus locale Italia] Creo versione {versione_corrente}: {len(focus_versione)} righe",
                flush=True,
            )

        percorsi.extend(
            crea_grafici_versione_locale(
                focus_versione,
                versione_corrente,
                cartella_output,
                mostra_progresso=mostra_progresso,
            )
        )

    if mostra_progresso:
        print(f"Focus locale Italia completato: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
