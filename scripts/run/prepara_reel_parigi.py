from pathlib import Path
from shutil import copy2
import csv
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


RADICE_REEL = Path("outputs/reel_parigi_9mq")
CARTELLA_GRAFICI = RADICE_REEL / "grafici"
CARTELLA_CARD = RADICE_REEL / "card"

WATERMARK = "Elaborazione di Nazareno Lecis"

COLORE_TESTO = "#111111"
COLORE_MUTED = "#4A4A4A"
COLORE_BLU = "#0D3B66"
COLORE_ROSSO = "#C1121F"
COLORE_VERDE = "#2A9D8F"
COLORE_ARANCIO = "#E76F51"
COLORE_GRIGIO = "#6F6F6F"
COLORE_SFONDO = "#FFFFFF"
COLORE_TRACCIA = "#E7E7E7"


GRAFICI_ESISTENTI = [
    {
        "destinazione": "01_parigi_milano_affitti_prezzi_redditi.png",
        "sorgente": Path("outputs/francia/charts/focus/parigi_milano_confronto_affitti_vendita_reddito.png"),
        "uso": "Confronto diretto Parigi-Milano su affitti, prezzi e rapporto con redditi.",
    },
    {
        "destinazione": "02_prezzi_affitti_redditi_inflazione.png",
        "sorgente": Path("outputs/francia/charts/confronti/francia_ue_prezzi_affitti_redditi_inflazione.png"),
        "uso": "Prezzi, affitti, redditi e inflazione: Francia, Italia e UE27.",
    },
    {
        "destinazione": "03_rapporto_prezzi_reddito_ocse.png",
        "sorgente": Path("outputs/francia/charts/confronti/oecd_rapporto_prezzi_reddito.png"),
        "uso": "Contesto OCSE sul rapporto prezzi/redditi, con Italia.",
    },
    {
        "destinazione": "04_rapporto_prezzi_affitti_ocse.png",
        "sorgente": Path("outputs/francia/charts/confronti/oecd_rapporto_prezzi_affitti.png"),
        "uso": "Contesto OCSE sul rapporto prezzi/affitti, con Italia.",
    },
    {
        "destinazione": "05_permessi_costruzione_abitazioni.png",
        "sorgente": Path("outputs/francia/charts/confronti/francia_ue_permessi_costruzione_abitazioni.png"),
        "uso": "Offerta: indice dei permessi di costruzione abitazioni.",
    },
    {
        "destinazione": "06_investimenti_abitazioni_pil.png",
        "sorgente": Path("outputs/francia/charts/confronti/francia_ue_investimenti_abitazioni_pil.png"),
        "uso": "Offerta: investimenti in abitazioni in percentuale del PIL.",
    },
    {
        "destinazione": "07_case_non_occupate_eurostat.png",
        "sorgente": Path("outputs/francia/charts/confronti/eurostat_abitazioni_non_occupate_stock_2021.png"),
        "uso": "Stock abitativo non occupato: confronto europeo con Francia e Italia.",
    },
    {
        "destinazione": "08_abitazioni_vuote_stagionali_ocse.png",
        "sorgente": Path("outputs/francia/charts/confronti/oecd_ahd_abitazioni_vuote_stagionali.png"),
        "uso": "Contesto OCSE su abitazioni vuote o stagionali, con Italia.",
    },
    {
        "destinazione": "09_stock_abitazioni_italia.png",
        "sorgente": Path("outputs/italia/charts/confronti/eurostat_stock_abitazioni_totali_2021.png"),
        "uso": "Contesto Italia: stock abitativo totale.",
    },
    {
        "destinazione": "10_sovraccarico_costi_inquilini.png",
        "sorgente": Path("outputs/francia/charts/confronti/francia_ue_sovraccarico_costi_inquilini.png"),
        "uso": "Effetto sociale: peso dei costi abitativi per gli inquilini.",
    },
]


CARD = [
    {
        "file": "01_minimo_legale_9mq_parigi.png",
        "tipo": "numero",
        "etichetta": "Soglia minima legale",
        "titolo": "Tu vivresti in 9 metri quadri?",
        "valore": "9 m²",
        "testo": "In Francia, per affittare un alloggio come abitazione principale serve almeno una stanza principale di 9 m² e 2,20 m di altezza, oppure 20 m³.",
        "fonte": "Service Public France, fiche F34905, verificata 21 marzo 2025",
        "url": "https://www.service-public.gouv.fr/particuliers/vosdroits/F34905",
        "colore": COLORE_BLU,
    },
    {
        "file": "02_controllo_affitti_apur.png",
        "tipo": "numero",
        "etichetta": "Controllo degli affitti",
        "titolo": "A Parigi ha frenato i canoni",
        "valore": "-5,2%",
        "testo": "Effetto moderatore stimato sui canoni tra luglio 2019 e giugno 2024 rispetto allo scenario senza regolazione. Utile, ma non aumenta lo stock di case.",
        "fonte": "APUR, The impact of rent control in Paris in 2024, giugno 2025",
        "url": "https://www.apur.org/en/housing-dwelling/housing-stock-evolution/impact-rent-control-paris",
        "colore": COLORE_ROSSO,
    },
    {
        "file": "03_plu_riabilitazione_verde.png",
        "tipo": "numero",
        "etichetta": "Vincoli urbanistici",
        "titolo": "Aggiungere offerta è difficile",
        "valore": "65%",
        "testo": "Nel PLU bioclimatico la riabilitazione è privilegiata rispetto alla demolizione e, sulle parcelle oltre 150 m², gli spazi liberi e vegetali possono arrivare fino al 65% del terreno.",
        "fonte": "Ville de Paris, Plan local d'urbanisme bioclimatique, aggiornato 16 aprile 2026",
        "url": "https://www.paris.fr/pages/plan-local-d-urbanisme-bioclimatique-vers-un-paris-plus-vert-et-plus-solidaire-23805",
        "colore": COLORE_VERDE,
    },
    {
        "file": "04_plu_plafonds_hauteurs.png",
        "tipo": "numero",
        "etichetta": "Altezze degli edifici",
        "titolo": "Il PLU mappa i plafonds des hauteurs",
        "valore": "PLU",
        "testo": "Il dataset ufficiale sui plafonds des hauteurs del PLU bioclimatico è stato votato dal Consiglio di Parigi il 20 novembre 2024. È utile per mostrare che i limiti di altezza sono parte della regolazione urbanistica.",
        "fonte": "Paris Open Data, PLU bioclimatique - Plafonds des hauteurs",
        "url": "https://opendata.paris.fr/explore/dataset/plub_hauteur/",
        "colore": COLORE_GRIGIO,
    },
    {
        "file": "05_case_non_occupate_parigi.png",
        "tipo": "stack",
        "etichetta": "Case non usate come abitazione principale",
        "titolo": "A Parigi quasi una casa su cinque è non occupata",
        "valore": "262 mila",
        "testo": "Secondo APUR, nel censimento 2020 il 19% dello stock è non occupato: 9% vuoto e 10% seconde case o usi occasionali.",
        "fonte": "APUR, Unoccupied housing in Paris, dicembre 2023",
        "url": "https://www.apur.org/en/housing-dwelling/private-housing-stock/unoccupied-housing-paris",
        "colore": COLORE_ARANCIO,
        "segmenti": [
            ("Abitazioni occupate", 81, "#DADADA"),
            ("Vuote", 9, COLORE_ROSSO),
            ("Seconde case/occasionali", 10, COLORE_BLU),
        ],
    },
    {
        "file": "06_case_non_occupate_arrondissement.png",
        "tipo": "barre",
        "etichetta": "Dove il problema pesa di più",
        "titolo": "In alcuni arrondissement si arriva intorno a un terzo dello stock",
        "valore": "36%",
        "testo": "APUR indica il 28% a Paris Centre, 30% nel 6e, 34% nel 7e e 36% nell'8e arrondissement.",
        "fonte": "APUR, Unoccupied housing in Paris, dicembre 2023",
        "url": "https://www.apur.org/en/housing-dwelling/private-housing-stock/unoccupied-housing-paris",
        "colore": COLORE_ARANCIO,
        "barre": [
            ("Paris Centre", 28),
            ("6e", 30),
            ("7e", 34),
            ("8e", 36),
        ],
    },
    {
        "file": "07_italia_stock_abitazioni_istat.png",
        "tipo": "metriche",
        "etichetta": "Il contesto italiano",
        "titolo": "In Italia le case esistono. Il punto è dove e come rientrano nel mercato.",
        "valore": "35,6 mln",
        "testo": "Nel 2021-2023 ISTAT stima oltre 35,6 milioni di abitazioni: più di 26 milioni occupate da residenti e 9,5 milioni non occupate o occupate da non residenti.",
        "fonte": "ISTAT, Abitazioni occupate, pubblicato 11 febbraio 2026",
        "url": "https://www.istat.it/comunicato-stampa/abitazioni-occupate/",
        "colore": COLORE_BLU,
        "metriche": [
            ("Totale abitazioni", "35,6 mln", COLORE_BLU),
            ("Occupate da residenti", ">26 mln", COLORE_VERDE),
            ("Non occupate/non residenti", "9,5 mln", COLORE_ROSSO),
        ],
    },
    {
        "file": "08_studentati_mur.png",
        "tipo": "metriche",
        "etichetta": "Una risposta lato offerta",
        "titolo": "Più studentati dove c'è domanda universitaria",
        "valore": "60 mila",
        "testo": "Il pacchetto housing universitario finanzia nuovi posti letto entro il 30 giugno 2026 e richiede immobili vicini alle sedi universitarie o ben collegati dal trasporto pubblico.",
        "fonte": "MUR, pacchetto housing universitario, 26 febbraio 2024",
        "url": "https://www.mur.gov.it/it/news/lunedi-26022024/universita-ecco-il-pacchetto-housing-procedure-semplificate-e-bando-da-12-mld",
        "colore": COLORE_VERDE,
        "metriche": [
            ("Nuovi posti letto", "60 mila", COLORE_VERDE),
            ("Stanziamento", "1,2 mld €", COLORE_BLU),
            ("Scadenza PNRR", "30/06/2026", COLORE_ROSSO),
        ],
    },
]


def prepara_cartelle():
    CARTELLA_GRAFICI.mkdir(parents=True, exist_ok=True)
    CARTELLA_CARD.mkdir(parents=True, exist_ok=True)


def testo_su_piu_righe(testo, larghezza):
    return "\n".join(textwrap.wrap(testo, width=larghezza, break_long_words=False))


def aggiungi_testo_wrappato(figura, x, y, testo, larghezza, dimensione, peso="normal", colore=COLORE_TESTO, altezza_riga=0.032):
    righe = textwrap.wrap(testo, width=larghezza, break_long_words=False)
    for indice, riga in enumerate(righe):
        figura.text(
            x,
            y - indice * altezza_riga,
            riga,
            ha="left",
            va="top",
            fontsize=dimensione,
            fontweight=peso,
            color=colore,
        )
    return y - len(righe) * altezza_riga


def crea_figura(colore):
    figura = plt.figure(figsize=(6.75, 12), dpi=160)
    figura.patch.set_facecolor(COLORE_SFONDO)
    figura.patches.extend(
        [
            Rectangle((0, 0.955), 1, 0.045, transform=figura.transFigure, color=colore, zorder=-1),
            Rectangle((0.065, 0.07), 0.87, 0.0025, transform=figura.transFigure, color=colore, alpha=0.9),
        ]
    )
    return figura


def aggiungi_intestazione(figura, card):
    figura.text(0.065, 0.925, card["etichetta"].upper(), ha="left", va="top", fontsize=10, fontweight="bold", color=card["colore"])
    return aggiungi_testo_wrappato(figura, 0.065, 0.885, card["titolo"], 28, 22, "bold", COLORE_TESTO, 0.04)


def aggiungi_footer(figura, card):
    testo = f"Fonte: {card['fonte']} | {WATERMARK}"
    figura.text(0.065, 0.035, testo_su_piu_righe(testo, 82), ha="left", va="bottom", fontsize=7.6, color=COLORE_MUTED)


def salva_card(figura, percorso):
    figura.savefig(percorso, dpi=160, facecolor=figura.get_facecolor())
    plt.close(figura)


def disegna_card_numero(card, percorso):
    figura = crea_figura(card["colore"])
    posizione_y = aggiungi_intestazione(figura, card)
    figura.text(0.065, posizione_y - 0.03, card["valore"], ha="left", va="top", fontsize=66, fontweight="bold", color=card["colore"])
    aggiungi_testo_wrappato(figura, 0.065, posizione_y - 0.2, card["testo"], 42, 14.5, "normal", COLORE_MUTED, 0.033)
    aggiungi_footer(figura, card)
    salva_card(figura, percorso)


def disegna_card_stack(card, percorso):
    figura = crea_figura(card["colore"])
    posizione_y = aggiungi_intestazione(figura, card)
    figura.text(0.065, posizione_y - 0.025, card["valore"], ha="left", va="top", fontsize=54, fontweight="bold", color=card["colore"])
    aggiungi_testo_wrappato(figura, 0.065, posizione_y - 0.165, card["testo"], 42, 14.5, "normal", COLORE_MUTED, 0.033)

    asse = figura.add_axes([0.065, 0.28, 0.87, 0.2])
    asse.set_xlim(0, 100)
    asse.set_ylim(0, 1)
    asse.axis("off")
    inizio = 0
    for etichetta, valore, colore in card["segmenti"]:
        asse.barh(0.56, valore, left=inizio, height=0.3, color=colore)
        asse.text(inizio + valore / 2, 0.56, f"{valore:.0f}%", ha="center", va="center", fontsize=12, fontweight="bold", color="#FFFFFF" if colore != "#DADADA" else COLORE_TESTO)
        inizio += valore

    posizioni_legenda = [0.065, 0.42, 0.6]
    for posizione_x, elemento in zip(posizioni_legenda, card["segmenti"]):
        etichetta, valore, colore = elemento
        figura.patches.append(Rectangle((posizione_x, 0.255), 0.018, 0.018, transform=figura.transFigure, color=colore))
        figura.text(posizione_x + 0.025, 0.264, f"{etichetta} ({valore:.0f}%)", ha="left", va="center", fontsize=9.3, color=COLORE_MUTED)

    aggiungi_footer(figura, card)
    salva_card(figura, percorso)


def disegna_card_barre(card, percorso):
    figura = crea_figura(card["colore"])
    posizione_y = aggiungi_intestazione(figura, card)
    figura.text(0.065, posizione_y - 0.025, card["valore"], ha="left", va="top", fontsize=54, fontweight="bold", color=card["colore"])
    aggiungi_testo_wrappato(figura, 0.065, posizione_y - 0.165, card["testo"], 42, 14.5, "normal", COLORE_MUTED, 0.033)

    asse = figura.add_axes([0.15, 0.25, 0.72, 0.27])
    etichette = [elemento[0] for elemento in card["barre"]]
    valori = [elemento[1] for elemento in card["barre"]]
    colori = [COLORE_GRIGIO, COLORE_ARANCIO, COLORE_ARANCIO, COLORE_ROSSO]
    barre = asse.bar(etichette, valori, color=colori, width=0.62)
    asse.set_ylim(0, 42)
    asse.set_yticks([0, 10, 20, 30, 40])
    asse.set_yticklabels([f"{valore}%" for valore in [0, 10, 20, 30, 40]], fontsize=9)
    asse.tick_params(axis="x", labelsize=10)
    asse.grid(axis="y", alpha=0.22)
    asse.spines[["top", "right", "left"]].set_visible(False)
    for barra, valore in zip(barre, valori):
        asse.text(barra.get_x() + barra.get_width() / 2, valore + 1, f"{valore}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    aggiungi_footer(figura, card)
    salva_card(figura, percorso)


def disegna_card_metriche(card, percorso):
    figura = crea_figura(card["colore"])
    posizione_y = aggiungi_intestazione(figura, card)
    figura.text(0.065, posizione_y - 0.025, card["valore"], ha="left", va="top", fontsize=54, fontweight="bold", color=card["colore"])
    posizione_testo = aggiungi_testo_wrappato(figura, 0.065, posizione_y - 0.16, card["testo"], 42, 14.2, "normal", COLORE_MUTED, 0.032)

    y = min(posizione_testo - 0.06, 0.47)
    for etichetta, valore, colore in card["metriche"]:
        figura.patches.append(Rectangle((0.065, y - 0.011), 0.018, 0.018, transform=figura.transFigure, color=colore))
        figura.text(0.1, y, etichetta, ha="left", va="center", fontsize=12, color=COLORE_MUTED)
        figura.text(0.935, y, valore, ha="right", va="center", fontsize=19, fontweight="bold", color=colore)
        y -= 0.075

    aggiungi_footer(figura, card)
    salva_card(figura, percorso)


def disegna_card(card):
    percorso = CARTELLA_CARD / card["file"]
    if card["tipo"] == "numero":
        disegna_card_numero(card, percorso)
    elif card["tipo"] == "stack":
        disegna_card_stack(card, percorso)
    elif card["tipo"] == "barre":
        disegna_card_barre(card, percorso)
    elif card["tipo"] == "metriche":
        disegna_card_metriche(card, percorso)
    else:
        raise ValueError(f"Tipo card non gestito: {card['tipo']}")
    return percorso


def copia_grafici_esistenti():
    righe = []
    mancanti = []
    for grafico in GRAFICI_ESISTENTI:
        sorgente = grafico["sorgente"]
        destinazione = CARTELLA_GRAFICI / grafico["destinazione"]
        if sorgente.exists():
            copy2(sorgente, destinazione)
            stato = "copiato"
        else:
            stato = "mancante"
            mancanti.append(str(sorgente))
        righe.append(
            {
                "tipo": "grafico_esistente",
                "file": str(destinazione),
                "uso": grafico["uso"],
                "fonte": "Fonte indicata nel footer del grafico",
                "url": "",
                "stato": stato,
            }
        )
    return righe, mancanti


def crea_card_mancanti():
    righe = []
    for card in CARD:
        percorso = disegna_card(card)
        righe.append(
            {
                "tipo": "card_mancante",
                "file": str(percorso),
                "uso": card["titolo"],
                "fonte": card["fonte"],
                "url": card["url"],
                "stato": "creata",
            }
        )
    return righe


def scrivi_manifest(righe):
    percorso = RADICE_REEL / "manifest_reel_parigi_9mq.csv"
    with percorso.open("w", newline="", encoding="utf-8") as file:
        campi = ["tipo", "file", "uso", "fonte", "url", "stato"]
        writer = csv.DictWriter(file, fieldnames=campi)
        writer.writeheader()
        writer.writerows(righe)
    return percorso


def scrivi_scaletta(righe):
    percorso = RADICE_REEL / "README.md"
    card = [riga for riga in righe if riga["tipo"] == "card_mancante"]
    grafici = [riga for riga in righe if riga["tipo"] == "grafico_esistente"]
    testo = [
        "# Reel Parigi 9 mq",
        "",
        "Cartella pronta per montaggio reel: card verticali per i passaggi che mancavano e grafici già prodotti copiati in ordine narrativo.",
        "",
        "## Card create",
        "",
    ]
    for riga in card:
        testo.append(f"- `{Path(riga['file']).name}` — {riga['uso']}")
    testo.extend(["", "## Grafici copiati", ""])
    for riga in grafici:
        testo.append(f"- `{Path(riga['file']).name}` — {riga['uso']}")
    testo.extend(
        [
            "",
            "## Nota",
            "",
            f"Tutte le card includono fonte e {WATERMARK}. I grafici mantengono il footer originale.",
            "Il file `manifest_reel_parigi_9mq.csv` contiene percorso, fonte e URL per ogni asset.",
            "",
        ]
    )
    percorso.write_text("\n".join(testo), encoding="utf-8")
    return percorso


def run():
    prepara_cartelle()
    righe_grafici, mancanti = copia_grafici_esistenti()
    righe_card = crea_card_mancanti()
    righe = righe_card + righe_grafici
    manifest = scrivi_manifest(righe)
    readme = scrivi_scaletta(righe)
    print(f"Cartella reel: {RADICE_REEL}")
    print(f"Card create: {len(righe_card)}")
    print(f"Grafici copiati: {sum(1 for riga in righe_grafici if riga['stato'] == 'copiato')}")
    if mancanti:
        print("Grafici mancanti:")
        for percorso in mancanti:
            print(f"- {percorso}")
    print(f"Manifest: {manifest}")
    print(f"README: {readme}")


run()
