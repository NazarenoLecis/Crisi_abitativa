import argparse
from api import scarica_tutto
from grafici import crea_grafici
from grafici_europei import crea_grafici_europei
from grafici_oecd import crea_grafici_oecd
from grafici_oecd_affordable import crea_grafici_oecd_affordable


parser = argparse.ArgumentParser(description="Genera grafici usando direttamente le API Eurostat e OECD.")
parser.add_argument("--output", default="outputs/charts", help="Cartella dove salvare i PNG.")
args = parser.parse_args()

print("Avvio generazione grafici crisi abitativa.", flush=True)
print("Scarico i dati dalle API: questa fase puo' richiedere qualche minuto.", flush=True)
dati = scarica_tutto(mostra_progresso=True)

print("Dati pronti. Inizio a creare e salvare i grafici.", flush=True)
percorsi = crea_grafici(dati, args.output, mostra_progresso=True)

print("Creo i confronti Italia-UE sui principali indicatori abitativi.", flush=True)
percorsi.extend(crea_grafici_europei(args.output, mostra_progresso=True))

print("Creo i confronti OECD sui prezzi delle case.", flush=True)
percorsi.extend(crea_grafici_oecd(args.output, mostra_progresso=True))

print("Creo i grafici dalla OECD Affordable Housing Database.", flush=True)
percorsi.extend(crea_grafici_oecd_affordable(args.output, mostra_progresso=True))

print("Grafici creati:")
for percorso in percorsi:
    print(f"- {percorso}")
