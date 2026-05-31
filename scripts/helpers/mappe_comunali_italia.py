from pathlib import Path
import re
import sys
import time
import unicodedata

RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Polygon
import matplotlib.pyplot as plt
import pandas as pd
import requests
from scripts.helpers.grafici_locali_italia import (
    aggiungi_footer_locale,
    aggiungi_indicatori_affordability,
    cartella_grafici_locali,
    etichette_citta,
    formatta_colorbar_mappa,
    formatta_semestre,
    limiti_geojson_regioni,
    normalizza_spazi,
    poligoni_feature_regionale,
    riepilogo_quotazioni_citta,
    scarica_comuni_istat,
    scarica_quotazioni_citta,
    scarica_redditi_comunali,
    scarica_semestre_omi,
    titolo_su_piu_righe,
    trova_colonna,
)
from scripts.helpers.utils import cartella_summary


COMUNI_GEOJSON_REGIONE_URL = (
    "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/"
    "limits_R_{codice_regione}_municipalities.geojson"
)
FONTE_MAPPE_COMUNALI = "ISTAT, Agenzia Entrate - OMI, MEF Dipartimento Finanze, openpolis GeoJSON comuni"
VALORI_TUTTE_REGIONI = {"tutte", "italia", "all"}
ALIAS_CATASTALI_GEOJSON_COMUNI = {
    "A134": "B567",
    "E608": "B567",
    "H521": "M435",
    "L487": "M435",
    "D902": "M436",
    "I879": "M436",
    "A121": "M437",
    "M332": "M437",
    "B749": "M438",
    "L878": "M438",
    "C056": "M439",
    "F838": "M439",
}

MAPPE_COMUNALI = [
    (
        "prezzo_mq_mediano",
        "Prezzi di vendita OMI",
        "euro/mq",
        "prezzi_vendita_omi.png",
        False,
        0,
    ),
    (
        "affitto_mq_mese_mediano",
        "Canoni di locazione OMI",
        "euro/mq/mese",
        "canoni_locazione_omi.png",
        False,
        1,
    ),
    (
        "anni_reddito_per_80mq",
        "Prezzo di 80 mq in anni di reddito medio dichiarato",
        "anni di reddito",
        "anni_reddito_per_80mq.png",
        False,
        1,
    ),
    (
        "affitto_40mq_mese",
        "Canone mensile stimato per 40 mq",
        "euro al mese",
        "affitto_40mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Affitto stimato per 40 mq sul reddito medio dichiarato",
        "% del reddito",
        "affitto_40mq_reddito.png",
        True,
        0,
    ),
    (
        "affitto_60mq_mese",
        "Canone mensile stimato per 60 mq",
        "euro al mese",
        "affitto_60mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_60mq_su_reddito_pct",
        "Affitto stimato per 60 mq sul reddito medio dichiarato",
        "% del reddito",
        "affitto_60mq_reddito.png",
        True,
        0,
    ),
]


def normalizza_chiave_testo(testo):
    testo_unicode = unicodedata.normalize("NFKD", str(testo))
    testo_ascii = "".join(carattere for carattere in testo_unicode if not unicodedata.combining(carattere))
    testo_ascii = testo_ascii.lower()
    testo_ascii = re.sub(r"[^a-z0-9]+", " ", testo_ascii)
    return testo_ascii.strip()


def slug_testo(testo):
    chiave = normalizza_chiave_testo(testo)
    slug = re.sub(r"\s+", "_", chiave)
    if slug:
        return slug
    return "regione"


def colonne_tabella_comuni(frame):
    colonne = {
        "codice_regione": trova_colonna(frame, ["codice regione"]),
        "comune": trova_colonna(frame, ["denominazione in italiano"]),
        "regione": trova_colonna(frame, ["denominazione regione"]),
        "provincia": trova_colonna(frame, ["sigla automobilistica"]),
        "unita_sovracomunale": trova_colonna(frame, ["denominazione dell", "territoriale sovracomunale"]),
        "codice_catastale": trova_colonna(frame, ["codice catastale"]),
        "codice_istat": trova_colonna(frame, ["codice comune formato numerico"]),
    }
    return colonne


def tabella_comuni_istat_pulita():
    frame = scarica_comuni_istat()
    colonne = colonne_tabella_comuni(frame)
    dati = frame.copy()
    for colonna in colonne.values():
        dati[colonna] = dati[colonna].map(normalizza_spazi)

    dati["codice_regione_istat"] = dati[colonne["codice_regione"]].str.zfill(2)
    dati["codice_istat"] = dati[colonne["codice_istat"]].str.zfill(6)
    dati["codice_catastale"] = dati[colonne["codice_catastale"]]
    dati["comune"] = dati[colonne["comune"]]
    dati["regione"] = dati[colonne["regione"]]
    dati["provincia"] = dati[colonne["provincia"]]
    dati["unita_sovracomunale"] = dati[colonne["unita_sovracomunale"]]
    return dati


def elenco_regioni_istat():
    dati = tabella_comuni_istat_pulita()
    regioni = (
        dati[["codice_regione_istat", "regione"]]
        .drop_duplicates()
        .sort_values(["codice_regione_istat", "regione"])
    )
    return regioni


def risolvi_regione(dati, regione):
    testo_regione = normalizza_spazi(regione)
    codice_input = testo_regione.zfill(2) if testo_regione.isdigit() else ""
    chiave_input = normalizza_chiave_testo(testo_regione)
    regioni = dati[["codice_regione_istat", "regione"]].drop_duplicates().copy()

    if codice_input:
        corrispondenze = regioni.loc[regioni["codice_regione_istat"] == codice_input]
    else:
        regioni["chiave"] = regioni["regione"].map(normalizza_chiave_testo)
        corrispondenze = regioni.loc[regioni["chiave"] == chiave_input]

    if not corrispondenze.empty:
        riga = corrispondenze.iloc[0]
        return riga["regione"], riga["codice_regione_istat"]

    disponibili = ", ".join(regioni["regione"].sort_values().tolist())
    raise ValueError(f"Regione non trovata: {regione}. Regioni disponibili: {disponibili}")


def seleziona_comuni_regione(regione, dati_comuni=None):
    dati = dati_comuni.copy() if dati_comuni is not None else tabella_comuni_istat_pulita()
    nome_regione, codice_regione = risolvi_regione(dati, regione)
    dati = dati.loc[dati["codice_regione_istat"] == codice_regione].copy()
    dati = dati.loc[dati["codice_catastale"] != ""].copy()
    dati = dati.sort_values(["provincia", "comune"])

    comuni = []
    for riga in dati.itertuples(index=False):
        comuni.append(
            {
                "comune": riga.comune,
                "provincia": riga.provincia,
                "regione": nome_regione,
                "codice_regione_istat": codice_regione,
                "unita_sovracomunale": riga.unita_sovracomunale,
                "codice_catastale": riga.codice_catastale,
                "codice_istat": riga.codice_istat,
                "ambito": "comuni-regione",
                "ambito_label": f"tutti i comuni della regione {nome_regione}",
            }
        )

    return comuni, nome_regione, codice_regione


def scarica_geojson_comuni_regione(codice_regione):
    codice_openpolis = str(int(str(codice_regione)))
    url = COMUNI_GEOJSON_REGIONE_URL.format(codice_regione=codice_openpolis)
    risposta = requests.get(url, timeout=120, headers={"User-Agent": "crisi-abitativa/0.1"})
    risposta.raise_for_status()
    return risposta.json()


def disegna_comune(asse, feature, colore):
    for poligono in poligoni_feature_regionale(feature):
        if not poligono:
            continue

        esterno = poligono[0]
        patch = Polygon(
            esterno,
            closed=True,
            facecolor=colore,
            edgecolor="white",
            linewidth=0.16,
        )
        asse.add_patch(patch)


def salva_mappa_comunale(figura, percorso):
    figura.savefig(percorso, dpi=170)
    plt.close(figura)


def codice_catastale_feature(feature):
    proprieta = feature.get("properties", {})
    codice = proprieta.get("com_catasto_code", "")
    return normalizza_spazi(codice).upper()


def codice_istat_feature(feature):
    proprieta = feature.get("properties", {})
    codice = proprieta.get("com_istat_code", "")
    return str(codice).zfill(6)


def nome_feature(feature):
    proprieta = feature.get("properties", {})
    return normalizza_chiave_testo(proprieta.get("name", ""))


def valore_feature_comunale(feature, valori_catastali, valori_istat, valori_nome):
    codice_catastale = codice_catastale_feature(feature)
    if codice_catastale in valori_catastali:
        return valori_catastali[codice_catastale]

    codice_alias = ALIAS_CATASTALI_GEOJSON_COMUNI.get(codice_catastale)
    if codice_alias in valori_catastali:
        return valori_catastali[codice_alias]

    codice_istat = codice_istat_feature(feature)
    if codice_istat in valori_istat:
        return valori_istat[codice_istat]

    nome = nome_feature(feature)
    return valori_nome.get(nome)


def dati_mappa_comunale(focus, colonna):
    dati = focus.dropna(subset=[colonna, "codice_catastale"]).copy()
    if dati.empty:
        return pd.DataFrame()

    dati["codice_catastale_mappa"] = dati["codice_catastale"].map(normalizza_spazi).str.upper()
    dati[colonna] = pd.to_numeric(dati[colonna], errors="coerce")
    dati = dati.dropna(subset=[colonna])
    if dati.empty:
        return pd.DataFrame()

    dati["codice_istat_mappa"] = dati["codice_istat"].astype(str).str.zfill(6)
    dati["nome_mappa"] = dati["comune"].map(normalizza_chiave_testo)
    colonne = ["codice_catastale_mappa", "codice_istat_mappa", "nome_mappa", colonna, "comune", "provincia"]
    return dati[colonne].copy()


def grafico_mappa_comunale_regione(
    focus,
    geojson,
    regione,
    colonna,
    titolo,
    legenda,
    nome_file,
    cartella_output,
    percentuale=False,
    decimali=0,
):
    dati = dati_mappa_comunale(focus, colonna)
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

    normalizzazione = Normalize(vmin=minimo, vmax=massimo)
    scala_colori = plt.get_cmap("YlOrRd")
    figura = plt.figure(figsize=(8.6, 9.2))
    asse = figura.add_axes([0.03, 0.11, 0.74, 0.72])
    for feature in features:
        valore = valore_feature_comunale(feature, valori_catastali, valori_istat, valori_nome)
        colore = scala_colori(normalizzazione(valore)) if valore is not None else "#E6E6E6"
        disegna_comune(asse, feature, colore)

    longitudine_min, longitudine_max, latitudine_min, latitudine_max = limiti_geojson_regioni(features)
    asse.set_xlim(longitudine_min - 0.25, longitudine_max + 0.25)
    asse.set_ylim(latitudine_min - 0.25, latitudine_max + 0.25)
    asse.set_aspect("equal")
    asse.axis("off")
    figura.text(
        0.03,
        0.94,
        titolo_su_piu_righe(titolo, larghezza=58),
        ha="left",
        va="top",
        fontsize=14,
        fontweight="bold",
    )
    figura.text(
        0.03,
        0.86,
        "Colore comunale = valore OMI del comune. Comuni grigi = nessun dato residenziale OMI utilizzabile.",
        ha="left",
        va="top",
        fontsize=8.8,
        color="#333333",
    )
    mappabile = ScalarMappable(norm=normalizzazione, cmap=scala_colori)
    mappabile.set_array([])
    asse_colorbar = figura.add_axes([0.81, 0.22, 0.028, 0.55])
    colorbar = figura.colorbar(mappabile, cax=asse_colorbar)
    colorbar.set_label(legenda, fontsize=9.2)
    formatta_colorbar_mappa(colorbar, percentuale=percentuale, decimali=decimali)
    aggiungi_footer_locale(figura, FONTE_MAPPE_COMUNALI)

    sezione = f"mappe_comunali/{slug_testo(regione)}"
    percorso = cartella_grafici_locali(cartella_output, sezione) / nome_file
    salva_mappa_comunale(figura, percorso)
    return percorso


def riepilogo_comune_omi(citta, semestre, mostra_progresso=False, lavoratori_omi=4):
    quotazioni = scarica_quotazioni_citta(
        citta,
        semestre,
        mostra_progresso=mostra_progresso,
        lavoratori=lavoratori_omi,
    )
    if quotazioni.empty:
        return None

    riepilogo = riepilogo_quotazioni_citta(quotazioni, citta)
    if not riepilogo:
        return None

    riepilogo["codice_istat"] = citta["codice_istat"]
    riepilogo["codice_regione_istat"] = citta["codice_regione_istat"]
    return riepilogo


def costruisci_focus_comuni_regione(
    regione="Sardegna",
    mostra_progresso=False,
    lavoratori_omi=4,
    limite_comuni=None,
    pausa=0.0,
    semestre=None,
    dati_comuni=None,
):
    semestre_usato = semestre or scarica_semestre_omi()
    comuni, nome_regione, codice_regione = seleziona_comuni_regione(regione, dati_comuni=dati_comuni)
    if limite_comuni:
        comuni = comuni[: int(limite_comuni)]

    if mostra_progresso:
        print(f"[Mappe comunali Italia] Regione: {nome_regione} ({codice_regione})", flush=True)
        print(f"[Mappe comunali Italia] Semestre OMI disponibile: {formatta_semestre(semestre_usato)}", flush=True)
        print(f"[Mappe comunali Italia] Comuni da scaricare: {len(comuni)}", flush=True)

    riepiloghi = []
    errori = []
    totale = len(comuni)
    for posizione, citta in enumerate(comuni, start=1):
        if mostra_progresso:
            print(f"[Mappe comunali {nome_regione} {posizione}/{totale}] Scarico OMI {citta['comune']}", flush=True)

        try:
            riepilogo = riepilogo_comune_omi(
                citta,
                semestre_usato,
                mostra_progresso=mostra_progresso,
                lavoratori_omi=lavoratori_omi,
            )
            if riepilogo:
                riepiloghi.append(riepilogo)
            else:
                errori.append(
                    {
                        "comune": citta["comune"],
                        "provincia": citta["provincia"],
                        "codice_catastale": citta["codice_catastale"],
                        "codice_istat": citta["codice_istat"],
                        "errore": "nessun dato residenziale OMI utilizzabile",
                    }
                )
        except Exception as errore:
            errori.append(
                {
                    "comune": citta["comune"],
                    "provincia": citta["provincia"],
                    "codice_catastale": citta["codice_catastale"],
                    "codice_istat": citta["codice_istat"],
                    "errore": str(errore),
                }
            )
            if mostra_progresso:
                print(f"  Salto {citta['comune']}: {errore}", flush=True)

        if pausa > 0:
            time.sleep(pausa)

    if not riepiloghi:
        return pd.DataFrame(), pd.DataFrame(errori), nome_regione, codice_regione

    focus = pd.DataFrame(riepiloghi)
    redditi = scarica_redditi_comunali(focus["codice_catastale"].tolist())
    focus = focus.merge(redditi, on="codice_catastale", how="left")
    focus["etichetta"] = etichette_citta(focus)
    focus = aggiungi_indicatori_affordability(focus)
    return focus, pd.DataFrame(errori), nome_regione, codice_regione


def salva_summary_comuni_regione(focus, errori, cartella_output, regione):
    cartella = cartella_summary(cartella_output, "italia_locale", f"mappe_comunali/{slug_testo(regione)}")
    percorso = cartella / f"{slug_testo(regione)}_comuni_omi_mef.csv"
    focus.sort_values("anni_reddito_per_80mq", ascending=False).to_csv(percorso, index=False)

    if errori is not None and not errori.empty:
        percorso_errori = cartella / f"{slug_testo(regione)}_comuni_errori.csv"
        errori.to_csv(percorso_errori, index=False)

    return percorso


def crea_mappe_comunali_regione(focus, regione, codice_regione, cartella_output, mostra_progresso=False):
    percorsi = []
    if focus.empty:
        return percorsi

    geojson = scarica_geojson_comuni_regione(codice_regione)
    semestre = formatta_semestre(focus["semestre_omi"].iloc[0])
    for colonna, titolo_base, legenda, nome_file, percentuale, decimali in MAPPE_COMUNALI:
        nome_output = f"{slug_testo(regione)}_comuni_{nome_file}"
        titolo = f"{titolo_base}: comuni della regione {regione}, {semestre}"
        if mostra_progresso:
            print(f"[Mappe comunali {regione}] Creo {nome_output}", flush=True)

        percorso = grafico_mappa_comunale_regione(
            focus,
            geojson,
            regione,
            colonna,
            titolo,
            legenda,
            nome_output,
            cartella_output,
            percentuale=percentuale,
            decimali=decimali,
        )
        if percorso:
            percorsi.append(percorso)

    return percorsi


def crea_mappe_comunali_italia(
    cartella_output="outputs/charts",
    regione="tutte",
    mostra_progresso=False,
    lavoratori_omi=4,
    limite_comuni=None,
    pausa=0.0,
    semestre=None,
    dati_comuni=None,
):
    if regione_indica_tutte(regione):
        return crea_mappe_comunali_tutte_regioni(
            cartella_output=cartella_output,
            regione=regione,
            mostra_progresso=mostra_progresso,
            lavoratori_omi=lavoratori_omi,
            limite_comuni=limite_comuni,
            pausa=pausa,
        )

    focus, errori, nome_regione, codice_regione = costruisci_focus_comuni_regione(
        regione=regione,
        mostra_progresso=mostra_progresso,
        lavoratori_omi=lavoratori_omi,
        limite_comuni=limite_comuni,
        pausa=pausa,
        semestre=semestre,
        dati_comuni=dati_comuni,
    )
    if focus.empty:
        if mostra_progresso:
            print(f"Mappe comunali {nome_regione} non create: nessun dato disponibile.", flush=True)
        return []

    salva_summary_comuni_regione(focus, errori, cartella_output, nome_regione)
    percorsi = crea_mappe_comunali_regione(
        focus,
        nome_regione,
        codice_regione,
        cartella_output,
        mostra_progresso=mostra_progresso,
    )
    if mostra_progresso:
        print(f"Mappe comunali {nome_regione} completate: {len(percorsi)} grafici creati.", flush=True)

    return percorsi


def regione_indica_tutte(regione):
    return normalizza_chiave_testo(regione) in VALORI_TUTTE_REGIONI


def nomi_regioni_da_generare(regione="tutte", dati_comuni=None):
    dati = dati_comuni.copy() if dati_comuni is not None else tabella_comuni_istat_pulita()
    if regione_indica_tutte(regione):
        regioni = (
            dati[["codice_regione_istat", "regione"]]
            .drop_duplicates()
            .sort_values(["codice_regione_istat", "regione"])
        )
        return regioni["regione"].tolist()

    nome_regione, codice_regione = risolvi_regione(dati, regione)
    return [nome_regione]


def crea_mappe_comunali_tutte_regioni(
    cartella_output="outputs/charts",
    regione="tutte",
    mostra_progresso=False,
    lavoratori_omi=4,
    limite_comuni=None,
    pausa=0.0,
):
    dati_comuni = tabella_comuni_istat_pulita()
    regioni = nomi_regioni_da_generare(regione=regione, dati_comuni=dati_comuni)
    semestre = scarica_semestre_omi()
    if mostra_progresso:
        print(
            f"[Mappe comunali Italia] Regioni da generare: {len(regioni)}",
            flush=True,
        )
        print(
            f"[Mappe comunali Italia] Semestre OMI riusato per tutte le regioni: {formatta_semestre(semestre)}",
            flush=True,
        )

    percorsi = []
    for posizione, nome_regione in enumerate(regioni, start=1):
        if mostra_progresso:
            print(
                f"[Mappe comunali Italia {posizione}/{len(regioni)}] Avvio regione {nome_regione}",
                flush=True,
            )

        percorsi.extend(
            crea_mappe_comunali_italia(
                cartella_output=cartella_output,
                regione=nome_regione,
                mostra_progresso=mostra_progresso,
                lavoratori_omi=lavoratori_omi,
                limite_comuni=limite_comuni,
                pausa=pausa,
                semestre=semestre,
                dati_comuni=dati_comuni,
            )
        )

    if mostra_progresso:
        print(f"Mappe comunali Italia completate: {len(percorsi)} grafici creati.", flush=True)

    return percorsi
