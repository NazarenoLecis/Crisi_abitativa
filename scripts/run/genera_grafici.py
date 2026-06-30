from pathlib import Path
import sys


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
if str(RADICE_PROGETTO) not in sys.path:
    sys.path.insert(0, str(RADICE_PROGETTO))

from scripts.helpers.api import scarica_unione_europea
from scripts.helpers.grafici import crea_grafici
from scripts.helpers.grafici_europei import crea_grafici_europei
from scripts.helpers.grafici_locali_italia import crea_grafici_locali_italia
from scripts.helpers.grafici_oecd import crea_grafici_oecd
from scripts.helpers.grafici_oecd_affordable import crea_grafici_oecd_affordable
from scripts.helpers.mappe_focus_europa import crea_confronto_parigi_milano, crea_mappe_e_focus_europa
from scripts.helpers.borsino import BORSINO_TIPO_ABITAZIONI_CIVILI, crea_grafici_borsino_italia
from scripts.helpers.affitti_brevi import PROFILI_AFFITTI_BREVI, crea_affitti_brevi_italia
from scripts.helpers.paesi import (
    PAESI_ACCETTATI,
    PAESI_EUROSTAT,
    PAESI_OECD,
    SCORCIATOIE_PAESI,
    profilo_paese,
    risolvi_codici_paesi,
    valori_paesi,
)


VERSIONI_FOCUS = ["tutte", "capoluoghi-regione", "regioni", "province"]
PROFILI_AFFITTI_BREVI_ACCETTATI = sorted(PROFILI_AFFITTI_BREVI)

# Cambia questo valore quando esegui lo script da VS Code senza argomenti.
# Esempi validi:
# PAESI = "ITA"
# PAESI = ["ITA", "FRA", "DEU"]
# PAESI = "tutti"
# PAESI = "eurostat"
# PAESI = "oecd"
PAESI = ["ITA", "FRA", "DEU"]
OUTPUT = "outputs"
INCLUDI_BORSINO = False
# Le opzioni Borsino qui sotto sono opzionali: servono solo se INCLUDI_BORSINO = True.
# Puoi lasciarle sui default o non passarle a run(...): verranno ignorate finche' Borsino e' spento.
VERSIONE_BORSINO = "capoluoghi-regione"
TIPO_IMMOBILE_BORSINO = BORSINO_TIPO_ABITAZIONI_CIVILI
API_KEY_BORSINO = None
PAUSA_BORSINO = 0.2
INCLUDI_AFFITTI_BREVI = False
REGIONE_AFFITTI_BREVI = "tutte"
PROFILO_AFFITTI_BREVI = "residenziale"
SALTA_MAPPE_FOCUS_ESTERO = False


def descrizione_paesi(codici):
    righe = []
    for codice in codici:
        profilo = profilo_paese(codice)
        righe.append(f"{codice}={profilo['nome']}")
    return ", ".join(righe)


def codici_unici(codici):
    risultato = []
    visti = set()
    for codice in codici:
        if codice not in visti:
            risultato.append(codice)
            visti.add(codice)
    return risultato


def aggiungi_italia_contesto(codici):
    if not codici or "ITA" in codici:
        return codici
    return codici_unici(codici + ["ITA"])


def risolvi_paesi_run(codici):
    richiesti = []
    paesi_eurostat = []
    paesi_oecd = []
    paesi_locali = []

    for valore in valori_paesi(codici, PAESI):
        valore_testo = str(valore).strip()
        valore_minuscolo = valore_testo.lower()
        if valore_minuscolo == "tutti":
            richiesti.extend(PAESI_ACCETTATI)
            paesi_eurostat.extend(PAESI_EUROSTAT)
            paesi_oecd.extend(PAESI_OECD)
            paesi_locali.extend(["ITA", "FRA", "DEU"])
            continue
        if valore_minuscolo == "eurostat":
            richiesti.extend(PAESI_EUROSTAT)
            paesi_eurostat.extend(PAESI_EUROSTAT)
            continue
        if valore_minuscolo == "oecd":
            richiesti.extend(PAESI_OECD)
            paesi_oecd.extend(PAESI_OECD)
            continue

        codice = risolvi_codici_paesi([valore_testo])[0]
        richiesti.append(codice)
        if codice in PAESI_EUROSTAT:
            paesi_eurostat.append(codice)
        if codice in PAESI_OECD:
            paesi_oecd.append(codice)
        if codice in {"ITA", "FRA", "DEU"}:
            paesi_locali.append(codice)

    richiesti = codici_unici(richiesti)
    paesi_eurostat = aggiungi_italia_contesto(codici_unici(paesi_eurostat))
    paesi_oecd = aggiungi_italia_contesto(codici_unici(paesi_oecd))
    paesi_locali = codici_unici(paesi_locali)
    if "FRA" in paesi_locali and "ITA" not in paesi_locali:
        paesi_locali.append("ITA")
    if ("ITA" in paesi_eurostat or "ITA" in paesi_oecd or "ITA" in paesi_locali) and "ITA" not in richiesti:
        richiesti.append("ITA")

    return richiesti, paesi_eurostat, paesi_oecd, paesi_locali


def deve_creare_confronto_parigi_milano(paesi_locali, salta_mappe_focus_estero):
    return "FRA" in paesi_locali and "ITA" in paesi_locali and not salta_mappe_focus_estero


def stampa_paesi_accettati():
    print("Valori speciali accettati:")
    for nome, codici in SCORCIATOIE_PAESI.items():
        print(f"- {nome}: {', '.join(codici)}")
    print("")
    print("Codici ISO3 Eurostat accettati:")
    print(descrizione_paesi(PAESI_EUROSTAT))
    print("")
    print("Codici ISO3 OECD accettati:")
    print(descrizione_paesi(PAESI_OECD))
    print("")
    print("Unione dei codici accettati:")
    print(", ".join(PAESI_ACCETTATI))


def run(
    paesi=PAESI,
    output=OUTPUT,
    mostra_lista_paesi=False,
    includi_borsino=INCLUDI_BORSINO,
    versione_borsino=VERSIONE_BORSINO,
    tipo_immobile_borsino=TIPO_IMMOBILE_BORSINO,
    api_key_borsino=API_KEY_BORSINO,
    pausa_borsino=PAUSA_BORSINO,
    includi_affitti_brevi=INCLUDI_AFFITTI_BREVI,
    regione_affitti_brevi=REGIONE_AFFITTI_BREVI,
    profilo_affitti_brevi=PROFILO_AFFITTI_BREVI,
    salta_mappe_focus_estero=SALTA_MAPPE_FOCUS_ESTERO,
):
    """
    Genera i grafici principali.

    Valori utili per `paesi`:
    - "ITA", "FRA", "DEU", "ESP", "USA", ... per singoli paesi;
    - ["ITA", "FRA"] per una lista di paesi;
    - "tutti" per tutti i paesi disponibili in almeno una fonte;
    - "eurostat" per i soli paesi Eurostat;
    - "oecd" per i soli paesi OECD.

    Valori accettati:
    - versione_borsino: "tutte", "capoluoghi-regione", "regioni", "province";
    - profilo_affitti_brevi: "residenziale", "privati", "c2", "totale";
    - regione_affitti_brevi: "tutte" oppure nome regione, es. "Sardegna".

    Gli argomenti Borsino non sono obbligatori:
    - lasciali come sono se `includi_borsino=False`;
    - puoi omettere `versione_borsino`, `tipo_immobile_borsino`,
      `api_key_borsino` e `pausa_borsino` nella chiamata a `run(...)`;
    - vengono usati solo se imposti `includi_borsino=True`;
    - in quel caso serve una chiave API, passata con `api_key_borsino`
      oppure tramite variabile ambiente BORSINO_API_KEY.
    """
    if mostra_lista_paesi:
        stampa_paesi_accettati()
        return []

    paesi_run, paesi_eurostat, paesi_oecd, paesi_locali = risolvi_paesi_run(paesi)

    print("Avvio generazione grafici crisi abitativa.", flush=True)
    print(f"Paesi richiesti: {', '.join(paesi_run)}", flush=True)
    print(f"Paesi Eurostat: {', '.join(paesi_eurostat) if paesi_eurostat else 'nessuno'}", flush=True)
    print(f"Paesi OECD: {', '.join(paesi_oecd) if paesi_oecd else 'nessuno'}", flush=True)
    print(f"Paesi con focus locali: {', '.join(paesi_locali) if paesi_locali else 'nessuno'}", flush=True)

    percorsi = []
    if paesi_eurostat:
        print("Scarico dati Eurostat: questa fase puo' richiedere qualche minuto.", flush=True)
        dati = scarica_unione_europea(mostra_progresso=True)
        print("Dati Eurostat pronti. Inizio a creare e salvare i grafici Eurostat.", flush=True)
        percorsi.extend(crea_grafici(dati, output, mostra_progresso=True, paesi_confronto=paesi_eurostat))
    else:
        print("Nessun paese Eurostat richiesto: salto il download Eurostat.", flush=True)

    if paesi_eurostat:
        print("Creo i confronti paese-UE sui principali indicatori abitativi.", flush=True)
        percorsi.extend(crea_grafici_europei(output, mostra_progresso=True, paesi_confronto=paesi_eurostat))

    if paesi_oecd:
        print("Creo i confronti OECD sui prezzi delle case.", flush=True)
        percorsi.extend(crea_grafici_oecd(output, mostra_progresso=True, paesi_confronto=paesi_oecd))

    if paesi_oecd:
        print("Creo i grafici dalla OECD Affordable Housing Database.", flush=True)
        percorsi.extend(crea_grafici_oecd_affordable(output, mostra_progresso=True, paesi_confronto=paesi_oecd))

    paesi_estero = [paese for paese in paesi_locali if paese in {"FRA", "DEU"}]
    if paesi_estero and not salta_mappe_focus_estero:
        print("Creo mappe e focus locali per Francia e Germania.", flush=True)
        percorsi.extend(crea_mappe_e_focus_europa(output, paesi=paesi_estero, mostra_progresso=True))

    if "ITA" in paesi_locali:
        print("Creo il focus locale sui capoluoghi italiani.", flush=True)
        percorsi.extend(crea_grafici_locali_italia(output, mostra_progresso=True))

    if includi_borsino and "ITA" in paesi_locali:
        print("Creo la sezione aggiuntiva Borsino.", flush=True)
        try:
            percorsi.extend(
                crea_grafici_borsino_italia(
                    output,
                    mostra_progresso=True,
                    versione=versione_borsino,
                    tipo_immobile=tipo_immobile_borsino,
                    api_key=api_key_borsino,
                    pausa=pausa_borsino,
                )
            )
        except RuntimeError as errore:
            print(str(errore), flush=True)
            raise SystemExit(1)
    elif includi_borsino:
        print("Salto Borsino: la sezione e' disponibile solo quando PAESI include ITA.", flush=True)

    if includi_affitti_brevi and "ITA" in paesi_locali:
        print("Creo la sezione aggiuntiva sugli affitti brevi.", flush=True)
        percorsi.extend(
            crea_affitti_brevi_italia(
                cartella_output=output,
                regione=regione_affitti_brevi,
                profilo=profilo_affitti_brevi,
                mostra_progresso=True,
            )
        )
    elif includi_affitti_brevi:
        print("Salto affitti brevi: la sezione e' disponibile solo quando PAESI include ITA.", flush=True)

    if deve_creare_confronto_parigi_milano(paesi_locali, salta_mappe_focus_estero):
        print("Creo il confronto locale Parigi-Milano.", flush=True)
        percorso = crea_confronto_parigi_milano(output)
        if percorso:
            percorsi.append(percorso)
        else:
            print("Confronto Parigi-Milano non creato: dati locali insufficienti.", flush=True)

    print("Grafici creati:")
    for percorso in percorsi:
        print(f"- {percorso}")
    return percorsi


if __name__ == "__main__":
    run(
        paesi=PAESI,
        output=OUTPUT,
        mostra_lista_paesi=False,
        includi_borsino=INCLUDI_BORSINO,
        versione_borsino=VERSIONE_BORSINO,
        tipo_immobile_borsino=TIPO_IMMOBILE_BORSINO,
        api_key_borsino=API_KEY_BORSINO,
        pausa_borsino=PAUSA_BORSINO,
        includi_affitti_brevi=INCLUDI_AFFITTI_BREVI,
        regione_affitti_brevi=REGIONE_AFFITTI_BREVI,
        profilo_affitti_brevi=PROFILO_AFFITTI_BREVI,
        salta_mappe_focus_estero=SALTA_MAPPE_FOCUS_ESTERO,
    )
