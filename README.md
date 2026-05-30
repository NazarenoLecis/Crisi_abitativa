# Crisi Abitativa

Script per studiare la crisi abitativa usando API pubbliche.

Il progetto e' organizzato in modo semplice: tutto il codice Python sta in `scripts/`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Script principali

Estrarre le serie disponibili per tutti i paesi OCSE:

```bash
python3 scripts/estrai_ocse.py
```

Confrontare paesi OCSE scelti:

```bash
python3 scripts/analisi_paesi.py --paesi ITA DEU FRA ESP
```

Approfondire l'Italia:

```bash
python3 scripts/analisi_italia.py
```

Generare grafici:

```bash
python3 scripts/genera_grafici.py
```

I grafici vengono salvati in sottocartelle di `outputs/charts/`:

- `outputs/charts/eurostat/confronti/`
- `outputs/charts/eurostat/non_confrontabili/`
- `outputs/charts/oecd/confronti/`

I grafici riportano sempre fonte e dicitura in basso a sinistra:

```text
Fonte: ... | Elaborazione di Nazareno Lecis
```

## Indicatori OCSE

- salario medio annuo;
- indici nominali e reali dei prezzi delle case, ribasati a 2019=100 nei grafici;
- rapporto prezzi case / reddito;
- rapporto prezzi case / affitti;
- investimenti in abitazioni, dove disponibili.

## Approfondimento Italia

Eurostat affordable housing:

- housing cost overburden rate;
- mediana del peso dei costi abitativi sul reddito;
- arretrati su mutuo, affitto o bollette;
- sovraffollamento;
- severe housing deprivation;
- abitazioni con perdite, umidita' o marciume;
- giovani 25-34 anni che vivono con i genitori;
- eta' media di uscita dalla casa dei genitori.

Shortage e offerta:

- popolazione totale;
- numero di famiglie private;
- permessi edilizi per nuove abitazioni;
- permessi residenziali in m2 per 1.000 abitanti;
- produzione nelle costruzioni;
- investimenti in abitazioni;
- stock abitativo e periodo di costruzione dal censimento Eurostat 2021.

## File

- `scripts/config.py`: lista degli indicatori e dei filtri API.
- `scripts/api.py`: funzioni per scaricare dati Eurostat e OECD.
- `scripts/utils.py`: funzioni generiche riusabili.
- `scripts/grafici.py`: funzioni di plotting.
- `scripts/grafici_europei.py`: confronti Italia-UE sui principali indicatori abitativi.
- `scripts/grafici_oecd.py`: confronti OECD sui prezzi delle case.
- `scripts/grafici_oecd_affordable.py`: grafici da OECD Affordable Housing Database.
- `scripts/estrai_ocse.py`: panoramica OCSE.
- `scripts/analisi_paesi.py`: confronto tra paesi scelti.
- `scripts/analisi_italia.py`: approfondimento Italia.
- `scripts/genera_grafici.py`: produzione dei grafici.

## Fonti

- Eurostat API statistics: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-detailed-guidelines/api-statistics
- Eurostat housing statistics: https://ec.europa.eu/eurostat/web/housing
- Eurostat affordable housing indicators: https://ec.europa.eu/eurostat/web/housing/affordable-housing
- OECD SDMX API: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html
- OECD average annual wages: https://www.oecd.org/en/data/indicators/average-annual-wages.html
- OECD housing prices: https://www.oecd.org/en/data/indicators/housing-prices.html
- OECD Affordable Housing Database: https://www.oecd.org/content/oecd/en/data/datasets/oecd-affordable-housing-database.html
- DG ECFIN AMECO database: https://economy-finance.ec.europa.eu/economic-research-and-databases/economic-databases/ameco-database_en

I confronti Italia-UE includono anche i nuclei informativi dei country fact sheet della
Commissione europea: prezzi/affitti/redditi/inflazione, investimenti, permessi di costruzione,
costi di costruzione, tenure, proprieta' per gruppo di reddito, overburden degli inquilini,
accesso ad abitazione adeguata per rischio poverta', rischio poverta' dopo i costi abitativi
ed eta' di uscita dalla casa dei genitori.

Il grafico su prezzi delle case, affitti, redditi e inflazione usa indice comune 2019=100
per rendere comparabili tutte le serie. Usa grandezze coerenti con il
country fact sheet della Commissione: affitti e inflazione da Eurostat `prc_hicp_aind`,
prezzi casa EU27 da Eurostat `prc_hpi_a`, prezzi casa Italia estesi da OECD
`DF_HOUSE_PRICES`, reddito disponibile pro capite da DG ECFIN AMECO (`UVGH / NPTD`).

## Nota metodologica

I tempi medi di rilascio permessi e di costruzione non risultano disponibili come serie armonizzata unica nei dataset Eurostat/OECD usati qui. Per ora vengono usati proxy osservabili: permessi edilizi, produzione nelle costruzioni, investimenti e stock abitativo per periodo di costruzione. Se troviamo una fonte amministrativa comparabile sui tempi effettivi, si puo' aggiungere in `scripts/config.py`.
