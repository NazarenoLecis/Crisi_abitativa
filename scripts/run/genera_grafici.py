import argparse
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
from scripts.helpers.mappe_focus_europa import crea_mappe_e_focus_europa
from scripts.helpers.borsino import BORSINO_TIPO_ABITAZIONI_CIVILI, crea_grafici_borsino_italia
from scripts.helpers.affitti_brevi import PROFILI_AFFITTI_BREVI, crea_affitti_brevi_italia
from scripts.helpers.paesi import (
    PAESI_ACCETTATI,
    PAESI_EUROSTAT,
    PAESI_OECD,
    SCORCIATOIE_PAESI,
    VALORI_PAESI_RUN,
    profilo_paese,
    risolvi_codici_paesi,
)


PAESI_RUN = ["ITA", "FRA", "DEU"]


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


def risolvi_paesi_run(codici):
    richiesti = []
    paesi_eurostat = []
    paesi_oecd = []
    paesi_locali = []

    for valore in codici or PAESI_RUN:
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

    return (
        codici_unici(richiesti),
        codici_unici(paesi_eurostat),
        codici_unici(paesi_oecd),
        codici_unici(paesi_locali),
    )


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


parser = argparse.ArgumentParser(description="Genera grafici usando direttamente le API Eurostat e OECD.")
parser.add_argument("--output", default="outputs", help="Cartella dove salvare PNG e CSV per paese.")
parser.add_argument(
    "--paesi-confronto",
    nargs="+",
    default=PAESI_RUN,
    choices=VALORI_PAESI_RUN,
    help=(
        "Paesi da evidenziare nei grafici di confronto. Accetta codici ISO3 "
        "o scorciatoie: tutti, eurostat, oecd. Default: valore di PAESI_RUN."
    ),
)
parser.add_argument(
    "--lista-paesi",
    action="store_true",
    help="Mostra codici paese e scorciatoie accettate, poi termina.",
)
parser.add_argument(
    "--includi-borsino",
    action="store_true",
    help="Include la sezione aggiuntiva Borsino. Richiede BORSINO_API_KEY o --api-key-borsino.",
)
parser.add_argument(
    "--versione-borsino",
    default="capoluoghi-regione",
    choices=["tutte", "capoluoghi-regione", "regioni", "province"],
    help="Versione Borsino da generare se --includi-borsino e' attivo.",
)
parser.add_argument(
    "--tipo-immobile-borsino",
    type=int,
    default=BORSINO_TIPO_ABITAZIONI_CIVILI,
    help="Codice tipo immobile Borsino. Default: 20, abitazioni in stabili civili.",
)
parser.add_argument("--api-key-borsino", default=None, help="Chiave API Borsino opzionale.")
parser.add_argument(
    "--pausa-borsino",
    type=float,
    default=0.2,
    help="Pausa in secondi tra le citta' per la sezione Borsino.",
)
parser.add_argument(
    "--includi-affitti-brevi",
    action="store_true",
    help="Include la sezione aggiuntiva sugli affitti brevi dal registro CIN.",
)
parser.add_argument(
    "--regione-affitti-brevi",
    default="tutte",
    help="Regione da mappare per --includi-affitti-brevi. Default: tutte.",
)
parser.add_argument(
    "--profilo-affitti-brevi",
    default="residenziale",
    choices=sorted(PROFILI_AFFITTI_BREVI),
    help="Filtro del registro CIN da usare per --includi-affitti-brevi.",
)
parser.add_argument(
    "--salta-mappe-focus-estero",
    action="store_true",
    help="Non genera mappe e focus locali per Francia e Germania.",
)


def main():
    args = parser.parse_args()

    if args.lista_paesi:
        stampa_paesi_accettati()
        raise SystemExit(0)

    paesi_run, paesi_eurostat, paesi_oecd, paesi_locali = risolvi_paesi_run(args.paesi_confronto)

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
        percorsi.extend(crea_grafici(dati, args.output, mostra_progresso=True, paesi_confronto=paesi_eurostat))
    else:
        print("Nessun paese Eurostat richiesto: salto il download Eurostat.", flush=True)

    if paesi_eurostat:
        print("Creo i confronti paese-UE sui principali indicatori abitativi.", flush=True)
        percorsi.extend(crea_grafici_europei(args.output, mostra_progresso=True, paesi_confronto=paesi_eurostat))

    if paesi_oecd:
        print("Creo i confronti OECD sui prezzi delle case.", flush=True)
        percorsi.extend(crea_grafici_oecd(args.output, mostra_progresso=True, paesi_confronto=paesi_oecd))

    if paesi_oecd:
        print("Creo i grafici dalla OECD Affordable Housing Database.", flush=True)
        percorsi.extend(crea_grafici_oecd_affordable(args.output, mostra_progresso=True, paesi_confronto=paesi_oecd))

    paesi_estero = [paese for paese in paesi_locali if paese in {"FRA", "DEU"}]
    if paesi_estero and not args.salta_mappe_focus_estero:
        print("Creo mappe e focus locali per Francia e Germania.", flush=True)
        percorsi.extend(crea_mappe_e_focus_europa(args.output, paesi=paesi_estero, mostra_progresso=True))

    if "ITA" in paesi_locali:
        print("Creo il focus locale sui capoluoghi italiani.", flush=True)
        percorsi.extend(crea_grafici_locali_italia(args.output, mostra_progresso=True))

    if args.includi_borsino and "ITA" in paesi_locali:
        print("Creo la sezione aggiuntiva Borsino.", flush=True)
        try:
            percorsi.extend(
                crea_grafici_borsino_italia(
                    args.output,
                    mostra_progresso=True,
                    versione=args.versione_borsino,
                    tipo_immobile=args.tipo_immobile_borsino,
                    api_key=args.api_key_borsino,
                    pausa=args.pausa_borsino,
                )
            )
        except RuntimeError as errore:
            print(str(errore), flush=True)
            raise SystemExit(1)
    elif args.includi_borsino:
        print("Salto Borsino: la sezione e' disponibile solo quando PAESI_RUN include ITA.", flush=True)

    if args.includi_affitti_brevi and "ITA" in paesi_locali:
        print("Creo la sezione aggiuntiva sugli affitti brevi.", flush=True)
        percorsi.extend(
            crea_affitti_brevi_italia(
                cartella_output=args.output,
                regione=args.regione_affitti_brevi,
                profilo=args.profilo_affitti_brevi,
                mostra_progresso=True,
            )
        )
    elif args.includi_affitti_brevi:
        print("Salto affitti brevi: la sezione e' disponibile solo quando PAESI_RUN include ITA.", flush=True)

    print("Grafici creati:")
    for percorso in percorsi:
        print(f"- {percorso}")


if __name__ == "__main__":
    main()
