import os
import re
import time
import pandas as pd
import requests
from scripts.helpers.grafici_locali_italia import (
    CAPOLUOGHI_REGIONE,
    aggiungi_indicatori_affordability,
    completa_provincia_da_etichetta,
    etichette_citta,
    etichetta_ambito,
    grafico_barre_locali,
    grafico_mappa_provinciale,
    grafico_mappa_regionale_da_province,
    media_ponderata,
    seleziona_comuni_focus,
    sezione_versione,
    sigle_territorio,
    scarica_redditi_comunali,
)
from scripts.helpers.utils import cartella_summary


BORSINO_API_BASE_URL = "https://api.borsinopro.it/rest/standard-v1"
BORSINO_API_KEY_ENV = "BORSINO_API_KEY"
BORSINO_TIPO_ABITAZIONI_CIVILI = 20
BORSINO_TIPO_LABEL = {
    20: "Abitazioni in stabili civili",
    19: "Abitazioni in stabili signorili",
    21: "Abitazioni in stabili economici",
    1: "Ville e Villini",
}
BORSINO_VERSIONI = {
    "capoluoghi-regione": "capoluoghi di regione",
    "regioni": "regioni, mediana dei capoluoghi di provincia",
    "province": "province, citta' metropolitane e liberi consorzi",
}
BORSINO_FONTE_BASE = "BorsinoPro/Borsino Immobiliare API, ISTAT, MEF Dipartimento Finanze"
BORSINO_FONTE_MAPPE_REGIONI = (
    "BorsinoPro/Borsino Immobiliare API, ISTAT, MEF Dipartimento Finanze, openpolis GeoJSON regioni"
)
BORSINO_FONTE_MAPPE_PROVINCE = (
    "BorsinoPro/Borsino Immobiliare API, ISTAT, MEF Dipartimento Finanze, openpolis GeoJSON province"
)

MAPPE_BORSINO = [
    (
        "borsino_vendita_med_mq",
        "Borsino: prezzi di vendita - province",
        "euro/mq",
        "borsino_mappa_province_prezzi_vendita.png",
        False,
        0,
    ),
    (
        "borsino_affitto_med_mq_mese",
        "Borsino: canoni di locazione - province",
        "euro/mq/mese",
        "borsino_mappa_province_canoni_locazione.png",
        False,
        1,
    ),
    (
        "anni_reddito_per_80mq",
        "Borsino: prezzo di 80 mq in anni di reddito - province",
        "anni di reddito",
        "borsino_mappa_province_anni_reddito_per_80mq.png",
        False,
        1,
    ),
    (
        "affitto_40mq_mese",
        "Borsino: canone mensile stimato per 40 mq - province",
        "euro al mese",
        "borsino_mappa_province_affitto_40mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_40mq_su_reddito_pct",
        "Borsino: affitto di 40 mq sul reddito medio dichiarato - province",
        "% del reddito",
        "borsino_mappa_province_affitto_40mq_reddito.png",
        True,
        0,
    ),
    (
        "affitto_60mq_mese",
        "Borsino: canone mensile stimato per 60 mq - province",
        "euro al mese",
        "borsino_mappa_province_affitto_60mq_mese.png",
        False,
        0,
    ),
    (
        "affitto_60mq_su_reddito_pct",
        "Borsino: affitto di 60 mq sul reddito medio dichiarato - province",
        "% del reddito",
        "borsino_mappa_province_affitto_60mq_reddito.png",
        True,
        0,
    ),
]


def leggi_api_key_borsino(api_key=None):
    chiave = api_key or os.getenv(BORSINO_API_KEY_ENV, "")
    chiave = chiave.strip()
    if chiave:
        return chiave

    raise RuntimeError(
        "Chiave API Borsino non impostata. Esporta BORSINO_API_KEY oppure passa --api-key al runner."
    )


def endpoint_borsino(metodo):
    metodo_pulito = str(metodo).strip("/")
    return f"{BORSINO_API_BASE_URL}/{metodo_pulito}/"


def normalizza_numero_borsino(valore):
    if valore is None:
        return None

    testo = str(valore).strip()
    if not testo:
        return None

    if "," in testo:
        testo = testo.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", testo):
        testo = testo.replace(".", "")

    numero = pd.to_numeric(testo, errors="coerce")
    if pd.isna(numero):
        return None
    return float(numero)


def scarica_borsino(metodo, payload, api_key, tentativi=4):
    url = endpoint_borsino(metodo)
    intestazioni = {"User-Agent": "crisi-abitativa/0.1"}
    ultimo_errore = None
    for tentativo in range(1, tentativi + 1):
        try:
            risposta = requests.post(
                url,
                data=payload,
                timeout=90,
                headers=intestazioni,
                auth=(api_key, ""),
            )
            if risposta.status_code == 429:
                ultimo_errore = RuntimeError("rate limit Borsino API 429")
                time.sleep(min(30, tentativo * 5))
                continue

            risposta.raise_for_status()
            return risposta.json()
        except Exception as errore:
            ultimo_errore = errore
            time.sleep(min(12, tentativo * 2))

    raise RuntimeError(f"Richiesta Borsino fallita per {metodo}: {ultimo_errore}") from ultimo_errore


def estrai_stima_borsino(payload):
    stima = payload.get("estimate")
    if isinstance(stima, dict):
        return stima

    risposta = payload.get("response")
    if isinstance(risposta, dict):
        stima = risposta.get("estimate")
        if isinstance(stima, dict):
            return stima

        quotazione = risposta.get("quotazione")
        if isinstance(quotazione, dict):
            return {
                "min_db": quotazione.get("min"),
                "med_db": quotazione.get("med"),
                "max_db": quotazione.get("max"),
                "anno": quotazione.get("anno"),
                "semestre": quotazione.get("semestre"),
            }

    return {}


def quotazione_consolidata_borsino(citta, contratto, tipo_immobile, api_key):
    payload = {
        "codcat": citta["codice_catastale"],
        "citta": citta["comune"],
        "type": int(tipo_immobile),
        "for": contratto,
    }
    risposta = scarica_borsino("getConsoData", payload, api_key)
    stima = estrai_stima_borsino(risposta)
    return {
        "min": normalizza_numero_borsino(stima.get("min_db")),
        "med": normalizza_numero_borsino(stima.get("med_db")),
        "max": normalizza_numero_borsino(stima.get("max_db")),
        "message": risposta.get("message", ""),
        "contract": risposta.get("contract", contratto),
        "raw_method": risposta.get("method", "getConsoData"),
    }


def riga_borsino_citta(citta, tipo_immobile, api_key):
    vendita = quotazione_consolidata_borsino(citta, "sale", tipo_immobile, api_key)
    affitto = quotazione_consolidata_borsino(citta, "rent", tipo_immobile, api_key)
    return {
        "comune": citta["comune"],
        "provincia": citta["provincia"],
        "regione": citta["regione"],
        "unita_sovracomunale": citta["unita_sovracomunale"],
        "codice_catastale": citta["codice_catastale"],
        "ambito": citta["ambito"],
        "ambito_label": citta["ambito_label"],
        "tipo_immobile_borsino": int(tipo_immobile),
        "tipo_immobile_borsino_label": BORSINO_TIPO_LABEL.get(int(tipo_immobile), str(tipo_immobile)),
        "borsino_vendita_min_mq": vendita["min"],
        "borsino_vendita_med_mq": vendita["med"],
        "borsino_vendita_max_mq": vendita["max"],
        "borsino_affitto_min_mq_mese": affitto["min"],
        "borsino_affitto_med_mq_mese": affitto["med"],
        "borsino_affitto_max_mq_mese": affitto["max"],
        "borsino_messaggio_vendita": vendita["message"],
        "borsino_messaggio_affitto": affitto["message"],
        "borsino_data_estrazione": pd.Timestamp.today().date().isoformat(),
    }


def stampa_progresso_borsino(posizione, totale, citta):
    print(
        f"[Borsino Italia {posizione}/{totale}] Scarico vendita e affitto per {citta['comune']}",
        flush=True,
    )


def aggiungi_indicatori_borsino(focus):
    risultato = focus.copy()
    risultato["prezzo_mq_mediano"] = pd.to_numeric(risultato["borsino_vendita_med_mq"], errors="coerce")
    risultato["affitto_mq_mese_mediano"] = pd.to_numeric(
        risultato["borsino_affitto_med_mq_mese"],
        errors="coerce",
    )
    risultato = aggiungi_indicatori_affordability(risultato)
    risultato = risultato.rename(
        columns={
            "prezzo_80mq": "borsino_prezzo_80mq",
        }
    )
    return risultato


def costruisci_focus_borsino(
    mostra_progresso=False,
    ambito="capoluoghi-provincia",
    tipo_immobile=BORSINO_TIPO_ABITAZIONI_CIVILI,
    api_key=None,
    pausa=0.2,
):
    chiave = leggi_api_key_borsino(api_key)
    citta_focus = seleziona_comuni_focus(ambito)
    if mostra_progresso:
        print(
            f"[Borsino Italia] Comuni selezionati: {len(citta_focus)} ({etichetta_ambito(ambito)})",
            flush=True,
        )
        print(
            f"[Borsino Italia] Tipo immobile: {tipo_immobile} - {BORSINO_TIPO_LABEL.get(tipo_immobile, tipo_immobile)}",
            flush=True,
        )

    righe = []
    errori = []
    totale = len(citta_focus)
    for posizione, citta in enumerate(citta_focus, start=1):
        if mostra_progresso:
            stampa_progresso_borsino(posizione, totale, citta)

        try:
            righe.append(riga_borsino_citta(citta, tipo_immobile, chiave))
        except Exception as errore:
            errori.append({"comune": citta["comune"], "provincia": citta["provincia"], "errore": str(errore)})
            if mostra_progresso:
                print(f"  Salto {citta['comune']}: {errore}", flush=True)

        if pausa > 0:
            time.sleep(pausa)

    if not righe:
        return pd.DataFrame(), pd.DataFrame(errori)

    focus = pd.DataFrame(righe)
    redditi = scarica_redditi_comunali(focus["codice_catastale"].tolist())
    focus = focus.merge(redditi, on="codice_catastale", how="left")
    focus["etichetta"] = etichette_citta(focus)
    focus = aggiungi_indicatori_borsino(focus)
    return focus, pd.DataFrame(errori)


def versione_borsino_da_generare(versione):
    if versione == "tutte":
        return ["capoluoghi-regione", "regioni", "province"]
    if versione in BORSINO_VERSIONI:
        return [versione]

    valori = ["tutte"] + sorted(BORSINO_VERSIONI)
    raise ValueError(f"Versione Borsino non valida: {versione}. Valori ammessi: {', '.join(valori)}")


def aggrega_focus_borsino_regioni(focus):
    righe = []
    colonne_valori = [
        "borsino_vendita_min_mq",
        "borsino_vendita_med_mq",
        "borsino_vendita_max_mq",
        "borsino_affitto_min_mq_mese",
        "borsino_affitto_med_mq_mese",
        "borsino_affitto_max_mq_mese",
    ]
    for regione, gruppo in focus.groupby("regione", dropna=False):
        riga = {
            "comune": regione,
            "provincia": sigle_territorio(gruppo),
            "regione": regione,
            "unita_sovracomunale": "",
            "codice_catastale": "",
            "ambito": "regioni",
            "ambito_label": BORSINO_VERSIONI["regioni"],
            "etichetta": regione,
            "tipo_immobile_borsino": gruppo["tipo_immobile_borsino"].iloc[0],
            "tipo_immobile_borsino_label": gruppo["tipo_immobile_borsino_label"].iloc[0],
            "borsino_data_estrazione": gruppo["borsino_data_estrazione"].dropna().iloc[0],
            "numero_comuni": int(len(gruppo)),
            "anno_redditi_mef": gruppo["anno_redditi_mef"].dropna().iloc[0]
            if gruppo["anno_redditi_mef"].notna().any()
            else None,
            "reddito_medio_dichiarato": media_ponderata(gruppo, "reddito_medio_dichiarato", "contribuenti"),
            "contribuenti": float(pd.to_numeric(gruppo["contribuenti"], errors="coerce").sum()),
        }
        for colonna in colonne_valori:
            riga[colonna] = float(pd.to_numeric(gruppo[colonna], errors="coerce").median())

        righe.append(riga)

    aggregato = pd.DataFrame(righe)
    if aggregato.empty:
        return aggregato
    return aggiungi_indicatori_borsino(aggregato)


def prepara_versione_borsino(focus, versione):
    if versione == "capoluoghi-regione":
        dati = focus.loc[focus["comune"].isin(CAPOLUOGHI_REGIONE)].copy()
        dati["ambito"] = versione
        dati["ambito_label"] = BORSINO_VERSIONI[versione]
        dati["numero_comuni"] = 1
        dati["etichetta"] = etichette_citta(dati)
        return dati

    if versione == "regioni":
        return aggrega_focus_borsino_regioni(focus)

    if versione == "province":
        dati = focus.copy()
        dati["ambito"] = versione
        dati["ambito_label"] = BORSINO_VERSIONI[versione]
        dati["numero_comuni"] = 1
        dati["etichetta"] = etichette_citta(dati)
        return dati

    valori = ", ".join(sorted(BORSINO_VERSIONI))
    raise ValueError(f"Versione Borsino non valida: {versione}. Valori ammessi: {valori}")


def salva_summary_borsino(focus, cartella_output, versione, errori=None):
    cartella = cartella_summary(cartella_output, "italia_locale", "borsino")
    percorso = cartella / f"focus_borsino_{sezione_versione(versione)}.csv"
    focus_pulito = completa_provincia_da_etichetta(focus)
    focus_pulito.sort_values("anni_reddito_per_80mq", ascending=False).to_csv(percorso, index=False)

    if errori is not None and not errori.empty:
        percorso_errori = cartella / f"focus_borsino_{sezione_versione(versione)}_errori.csv"
        errori.to_csv(percorso_errori, index=False)

    return percorso


def nota_borsino(tipo_immobile):
    label = BORSINO_TIPO_LABEL.get(int(tipo_immobile), str(tipo_immobile))
    return (
        "Quotazioni Borsino API getConsoData: valori consolidati comunali, "
        f"tipo {int(tipo_immobile)} ({label})."
    )


def crea_barre_borsino(focus, versione, cartella_output, mostra_progresso=False):
    if focus.empty:
        return []

    sezione = f"borsino/{sezione_versione(versione)}"
    ambito_label = focus["ambito_label"].iloc[0]
    tipo_immobile = int(focus["tipo_immobile_borsino"].iloc[0])
    anno_redditi = int(focus["anno_redditi_mef"].dropna().iloc[0]) if focus["anno_redditi_mef"].notna().any() else ""
    data_estrazione = focus["borsino_data_estrazione"].dropna().iloc[0]
    prefisso_file = f"borsino_{sezione_versione(versione)}"
    nota = nota_borsino(tipo_immobile)
    grafici = [
        (
            "borsino_vendita_med_mq",
            f"Borsino: prezzi di vendita - {ambito_label}, estrazione {data_estrazione}",
            "euro/mq",
            f"{prefisso_file}_prezzi_vendita.png",
            False,
        ),
        (
            "borsino_affitto_med_mq_mese",
            f"Borsino: canoni di locazione - {ambito_label}, estrazione {data_estrazione}",
            "euro/mq/mese",
            f"{prefisso_file}_canoni_locazione.png",
            False,
        ),
        (
            "anni_reddito_per_80mq",
            f"Borsino: prezzo di 80 mq in anni di reddito medio dichiarato - {ambito_label}, redditi {anno_redditi}",
            "anni di reddito medio dichiarato",
            f"{prefisso_file}_anni_reddito_per_80mq.png",
            False,
        ),
        (
            "affitto_40mq_mese",
            f"Borsino: canone mensile stimato per 40 mq - {ambito_label}",
            "euro al mese per 40 mq",
            f"{prefisso_file}_affitto_40mq_mese.png",
            False,
        ),
        (
            "affitto_40mq_su_reddito_pct",
            f"Borsino: affitto di 40 mq sul reddito medio dichiarato - {ambito_label}, redditi {anno_redditi}",
            "% del reddito medio dichiarato",
            f"{prefisso_file}_affitto_40mq_reddito.png",
            True,
        ),
        (
            "affitto_60mq_mese",
            f"Borsino: canone mensile stimato per 60 mq - {ambito_label}",
            "euro al mese per 60 mq",
            f"{prefisso_file}_affitto_60mq_mese.png",
            False,
        ),
        (
            "affitto_60mq_su_reddito_pct",
            f"Borsino: affitto di 60 mq sul reddito medio dichiarato - {ambito_label}, redditi {anno_redditi}",
            "% del reddito medio dichiarato",
            f"{prefisso_file}_affitto_60mq_reddito.png",
            True,
        ),
    ]
    percorsi = []
    for colonna, titolo, asse_x, nome_file, percentuale in grafici:
        if mostra_progresso:
            print(f"[Borsino Italia - {versione}] Creo {nome_file}", flush=True)

        percorso = grafico_barre_locali(
            focus,
            colonna,
            titolo,
            asse_x,
            nome_file,
            BORSINO_FONTE_BASE,
            cartella_output,
            sezione,
            percentuale=percentuale,
            nota=nota,
        )
        if percorso:
            percorsi.append(percorso)

    return percorsi


def crea_mappe_borsino(focus, cartella_output, mostra_progresso=False):
    percorsi = []
    if focus.empty:
        return percorsi

    tipo_immobile = int(focus["tipo_immobile_borsino"].iloc[0])
    nota_regioni = (
        "Colore regionale = mediana delle province disponibili. "
        + nota_borsino(tipo_immobile)
    )
    nota_province = (
        "Colore provinciale = valore del capoluogo/provincia disponibile. "
        + nota_borsino(tipo_immobile)
    )

    for colonna, titolo, legenda, nome_file, percentuale, decimali in MAPPE_BORSINO:
        nome_regionale = nome_file.replace("borsino_mappa_province_", "borsino_mappa_regioni_da_province_")
        titolo_regionale = titolo.replace(" - province", ": sintesi regionale delle province")
        if mostra_progresso:
            print(f"[Borsino Italia - province] Creo mappa regionale {nome_regionale}", flush=True)

        percorso_regionale = grafico_mappa_regionale_da_province(
            focus,
            colonna,
            titolo_regionale,
            legenda,
            nome_regionale,
            cartella_output,
            percentuale=percentuale,
            decimali=decimali,
            fonte=BORSINO_FONTE_MAPPE_REGIONI,
            nota=nota_regioni,
            sezione="borsino/mappe_regioni",
        )
        if percorso_regionale:
            percorsi.append(percorso_regionale)

        if mostra_progresso:
            print(f"[Borsino Italia - province] Creo mappa provinciale {nome_file}", flush=True)

        percorso_provinciale = grafico_mappa_provinciale(
            focus,
            colonna,
            titolo,
            legenda,
            nome_file,
            cartella_output,
            percentuale=percentuale,
            decimali=decimali,
            fonte=BORSINO_FONTE_MAPPE_PROVINCE,
            nota=nota_province,
            sezione="borsino/mappe_province",
        )
        if percorso_provinciale:
            percorsi.append(percorso_provinciale)

    return percorsi


def crea_grafici_versione_borsino(focus, versione, cartella_output, mostra_progresso=False, errori=None):
    if focus.empty:
        if mostra_progresso:
            print(f"Borsino Italia {versione} non creato: nessun dato disponibile.", flush=True)
        return []

    salva_summary_borsino(focus, cartella_output, versione, errori=errori)
    if versione == "province":
        if mostra_progresso:
            print(
                "[Borsino Italia - province] Dettaglio provinciale salvato in CSV; "
                "per i PNG creo mappe regionali e provinciali.",
                flush=True,
            )
        return crea_mappe_borsino(focus, cartella_output, mostra_progresso=mostra_progresso)

    return crea_barre_borsino(focus, versione, cartella_output, mostra_progresso=mostra_progresso)


def crea_grafici_borsino_italia(
    cartella_output="outputs/charts",
    mostra_progresso=False,
    versione="capoluoghi-regione",
    tipo_immobile=BORSINO_TIPO_ABITAZIONI_CIVILI,
    api_key=None,
    pausa=0.2,
):
    versioni = versione_borsino_da_generare(versione)
    ambito_base = "capoluoghi-regione" if versioni == ["capoluoghi-regione"] else "capoluoghi-provincia"
    focus_base, errori = costruisci_focus_borsino(
        mostra_progresso=mostra_progresso,
        ambito=ambito_base,
        tipo_immobile=tipo_immobile,
        api_key=api_key,
        pausa=pausa,
    )
    if focus_base.empty:
        if mostra_progresso:
            print("Borsino Italia non creato: nessun dato disponibile.", flush=True)
        return []

    if ambito_base == "capoluoghi-provincia":
        salva_summary_borsino(focus_base, cartella_output, "base_capoluoghi_provincia", errori=errori)

    percorsi = []
    for versione_corrente in versioni:
        focus_versione = prepara_versione_borsino(focus_base, versione_corrente)
        if mostra_progresso:
            print(
                f"[Borsino Italia] Creo versione {versione_corrente}: {len(focus_versione)} righe",
                flush=True,
            )

        percorsi.extend(
            crea_grafici_versione_borsino(
                focus_versione,
                versione_corrente,
                cartella_output,
                mostra_progresso=mostra_progresso,
                errori=errori,
            )
        )

    if mostra_progresso:
        print(f"Borsino Italia completato: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
