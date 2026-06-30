from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import json
from pathlib import Path
import sys
import time

import pandas as pd

RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.grafici_locali_italia import (
    aggiungi_indicatori_affordability,
    etichette_citta,
    formatta_semestre,
    normalizza_spazi,
    scarica_redditi_comunali,
    scarica_semestre_omi,
)
from scripts.helpers.mappe_comunali_italia import (
    nomi_regioni_da_generare,
    riepilogo_comune_omi,
    scarica_geojson_comuni_regione,
    seleziona_comuni_regione,
    slug_testo,
    tabella_comuni_istat_pulita,
)


OUTPUT = "../NazarenoLecis.github.io/data/crisi-abitativa"
REGIONE = "tutte"
LAVORATORI_COMUNI = 8
LIMITE_COMUNI = None
PAUSA = 0.0
SOURCE_REPOSITORY = "https://github.com/NazarenoLecis/Crisi_abitativa"
SOURCE = "OMI Agenzia Entrate; MEF Dipartimento Finanze; ISTAT; openpolis GeoJSON"
METHODOLOGY = (
    "Valori medi e mediani calcolati sulle mediane delle zone OMI residenziali disponibili nel comune. "
    "Non sono pesati per transazioni, stock abitativo, superficie o popolazione."
)
INDEX_METHODOLOGY = [
    "Il focus locale usa quotazioni OMI Agenzia Entrate, redditi dichiarati comunali MEF, "
    "anagrafica ISTAT dei comuni e confini comunali openpolis.",
    "Prezzi e affitti medi/mediani sono calcolati sulle zone OMI residenziali disponibili del comune "
    "e non sono pesati per transazioni, stock abitativo, superficie o popolazione.",
    "Gli indicatori locali sono proxy territoriali: non misurano canoni effettivi di contratto, "
    "prezzi effettivi di rogito o reddito disponibile familiare.",
]


def valore_json(valore):
    if pd.isna(valore):
        return None
    if isinstance(valore, float):
        return float(valore)
    if isinstance(valore, int):
        return int(valore)
    return valore


def codice_istat_json(valore):
    if pd.isna(valore):
        return ""
    testo = str(valore).strip()
    if testo.endswith(".0"):
        testo = testo[:-2]
    return testo.zfill(6)


def anno_json(valore):
    if pd.isna(valore):
        return None
    testo = str(valore).strip()
    if testo.endswith(".0"):
        testo = testo[:-2]
    return testo


def record_json(riga):
    return {
        "comune": valore_json(riga["comune"]),
        "provincia": valore_json(riga["provincia"]),
        "regione": valore_json(riga["regione"]),
        "codice_catastale": valore_json(riga["codice_catastale"]),
        "codice_istat": codice_istat_json(riga["codice_istat"]),
        "zone_omi": int(riga["zone_omi"]),
        "rent_mean": valore_json(riga.get("affitto_mq_mese_medio")),
        "rent_median": valore_json(riga.get("affitto_mq_mese_mediano")),
        "sale_mean": valore_json(riga.get("prezzo_mq_medio")),
        "sale_median": valore_json(riga.get("prezzo_mq_mediano")),
        "income_mean": valore_json(riga.get("reddito_medio_dichiarato")),
        "income_year": anno_json(riga.get("anno_redditi_mef")),
        "sale_80sqm_income_years": valore_json(riga.get("anni_reddito_per_80mq")),
        "rent_50sqm_income_pct": valore_json(riga.get("affitto_50mq_su_reddito_pct")),
    }


def errore_json(riga):
    return {
        "comune": valore_json(riga.get("comune")),
        "provincia": valore_json(riga.get("provincia")),
        "codice_catastale": valore_json(riga.get("codice_catastale")),
        "codice_istat": codice_istat_json(riga.get("codice_istat")),
        "errore": valore_json(riga.get("errore")),
    }


def ordina_focus(focus):
    dati = focus.copy()
    dati["codice_istat_ordinamento"] = dati["codice_istat"].map(codice_istat_json)
    return dati.sort_values(["provincia", "comune", "codice_istat_ordinamento"])


def semestre_json(focus):
    if focus.empty or "semestre_omi" not in focus.columns:
        return None
    return formatta_semestre(focus["semestre_omi"].iloc[0])


def errore_comune(citta, messaggio):
    return {
        "comune": citta["comune"],
        "provincia": citta["provincia"],
        "codice_catastale": citta["codice_catastale"],
        "codice_istat": citta["codice_istat"],
        "errore": messaggio,
    }


def scarica_riepilogo_comune(citta, semestre):
    riepilogo = riepilogo_comune_omi(
        citta,
        semestre,
        mostra_progresso=False,
        lavoratori_omi=1,
    )
    if riepilogo:
        return riepilogo, None
    return None, errore_comune(citta, "nessun dato residenziale OMI utilizzabile")


def costruisci_focus_comuni_regione_export(
    regione,
    dati_comuni,
    lavoratori_comuni,
    limite_comuni,
    pausa,
):
    semestre = scarica_semestre_omi()
    comuni, nome_regione, codice_regione = seleziona_comuni_regione(regione, dati_comuni=dati_comuni)
    if limite_comuni:
        comuni = comuni[: int(limite_comuni)]

    print(f"[Mappe comunali Italia] Regione: {nome_regione} ({codice_regione})", flush=True)
    print(f"[Mappe comunali Italia] Semestre OMI disponibile: {formatta_semestre(semestre)}", flush=True)
    print(f"[Mappe comunali Italia] Comuni da scaricare: {len(comuni)}", flush=True)

    riepiloghi = []
    errori = []
    totale = len(comuni)
    lavoratori_effettivi = max(1, min(int(lavoratori_comuni), totale))

    with ThreadPoolExecutor(max_workers=lavoratori_effettivi) as esecutore:
        richieste = {}
        for citta in comuni:
            richiesta = esecutore.submit(scarica_riepilogo_comune, citta, semestre)
            richieste[richiesta] = citta
            if pausa > 0:
                time.sleep(pausa)

        for posizione, richiesta in enumerate(as_completed(richieste), start=1):
            citta = richieste[richiesta]
            try:
                riepilogo, errore = richiesta.result()
            except Exception as eccezione:
                riepilogo = None
                errore = errore_comune(citta, str(eccezione))

            if riepilogo:
                riepiloghi.append(riepilogo)
            elif errore:
                errori.append(errore)

            if posizione == 1 or posizione == totale or posizione % 25 == 0:
                print(
                    f"[Mappe comunali {nome_regione}] Comuni completati {posizione}/{totale}",
                    flush=True,
                )

    if not riepiloghi:
        return pd.DataFrame(), pd.DataFrame(errori), nome_regione, codice_regione

    focus = pd.DataFrame(riepiloghi)
    redditi = scarica_redditi_comunali(focus["codice_catastale"].tolist())
    focus = focus.merge(redditi, on="codice_catastale", how="left")
    focus["etichetta"] = etichette_citta(focus)
    focus = aggiungi_indicatori_affordability(focus)
    return focus, pd.DataFrame(errori), nome_regione, codice_regione


def scrivi_json(percorso, payload):
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def esporta_regione(nome_regione, dati_comuni, cartella_output, lavoratori_comuni, limite_comuni, pausa):
    focus, errori, label, codice_regione = costruisci_focus_comuni_regione_export(
        regione=nome_regione,
        dati_comuni=dati_comuni,
        lavoratori_comuni=lavoratori_comuni,
        limite_comuni=limite_comuni,
        pausa=pausa,
    )
    if focus.empty:
        print(f"[Export JSON regioni] Salto {label}: nessun dato disponibile.", flush=True)
        return None

    focus = ordina_focus(focus)
    slug = slug_testo(label)
    geojson = scarica_geojson_comuni_regione(codice_regione)
    payload = {
        "label": label,
        "slug": slug,
        "updated_at": date.today().isoformat(),
        "semestre_omi": semestre_json(focus),
        "source": SOURCE,
        "methodology": METHODOLOGY,
        "records": [record_json(riga) for riga in focus.to_dict("records")],
        "errors": [] if errori is None or errori.empty else [errore_json(riga) for riga in errori.to_dict("records")],
        "geojson": geojson,
    }
    percorso = cartella_output / "regions" / f"{slug}.json"
    scrivi_json(percorso, payload)
    print(f"[Export JSON regioni] Creato {percorso} ({len(payload['records'])} comuni).", flush=True)
    return {
        "label": label,
        "file": f"{slug}.json",
        "preload": slug == "sardegna",
        "status": "preloaded" if slug == "sardegna" else "generated",
    }


def scrivi_indice(cartella_output, regioni):
    regioni = [regione for regione in regioni if regione is not None]
    regioni.sort(key=lambda regione: normalizza_spazi(regione["label"]))
    payload = {
        "updated_at": date.today().isoformat(),
        "source_repository": SOURCE_REPOSITORY,
        "default_region": "sardegna.json" if any(regione["file"] == "sardegna.json" for regione in regioni) else (
            regioni[0]["file"] if regioni else ""
        ),
        "regions": regioni,
        "methodology": INDEX_METHODOLOGY,
    }
    scrivi_json(cartella_output / "local_index.json", payload)
    print(f"[Export JSON regioni] Indice aggiornato con {len(regioni)} regioni.", flush=True)


def run(
    output=OUTPUT,
    regione=REGIONE,
    lavoratori_comuni=LAVORATORI_COMUNI,
    limite_comuni=LIMITE_COMUNI,
    pausa=PAUSA,
):
    cartella_output = (RADICE_PROGETTO / output).resolve()
    dati_comuni = tabella_comuni_istat_pulita()
    regioni = nomi_regioni_da_generare(regione=regione, dati_comuni=dati_comuni)
    print(f"[Export JSON regioni] Regioni da esportare: {len(regioni)}.", flush=True)
    risultati = []
    for posizione, nome_regione in enumerate(regioni, start=1):
        print(f"[Export JSON regioni {posizione}/{len(regioni)}] Avvio {nome_regione}.", flush=True)
        risultato = esporta_regione(
            nome_regione,
            dati_comuni,
            cartella_output,
            lavoratori_comuni,
            limite_comuni,
            pausa,
        )
        risultati.append(risultato)

    scrivi_indice(cartella_output, risultati)
    return risultati


if __name__ == "__main__":
    run(
        output=OUTPUT,
        regione=REGIONE,
        lavoratori_comuni=LAVORATORI_COMUNI,
        limite_comuni=LIMITE_COMUNI,
        pausa=PAUSA,
    )
