# Crisi Abitativa

Script per studiare la crisi abitativa usando API pubbliche.

Il progetto e' organizzato in modo semplice: i comandi stanno in `scripts/run/`, mentre il codice
riusabile sta in `scripts/helpers/`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Script principali

Estrarre le serie disponibili per tutti i paesi OCSE:

```bash
python3 -m scripts.run.estrai_ocse
```

Confrontare paesi OCSE scelti:

```bash
python3 -m scripts.run.analisi_paesi --paesi ITA DEU FRA ESP
```

Approfondire l'Italia:

```bash
python3 -m scripts.run.analisi_italia
```

Generare grafici:

```bash
python3 -m scripts.run.genera_grafici
```

Generare solo il focus locale sui capoluoghi italiani:

```bash
python3 -m scripts.run.focus_locale_italia
```

Generare una sola versione del focus locale:

```bash
python3 -m scripts.run.focus_locale_italia --versione capoluoghi-regione
python3 -m scripts.run.focus_locale_italia --versione regioni
python3 -m scripts.run.focus_locale_italia --versione province
```

Consultare il glossario metodologico degli indicatori:

```text
docs/definizioni.md
```

I grafici vengono salvati in sottocartelle di `outputs/charts/`:

- `outputs/charts/eurostat/confronti/`
- `outputs/charts/eurostat/italia/`
- `outputs/charts/italia_locale/`
- `outputs/charts/oecd/confronti/`

I grafici con banda min-max salvano anche un CSV in `outputs/summary/` con paese minimo,
paese massimo, valore Italia ed eventuale valore EU27 per ogni periodo.

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
- stock abitativo, abitazioni occupate/non occupate e periodo di costruzione dal censimento Eurostat 2021;
- abitazioni per 1.000 abitanti e abitazioni per famiglia privata;
- quote di stock costruito prima del 1981 e dal 2001 in poi.

## Focus Locale Italia

Il focus locale sui capoluoghi italiani usa:

- lista dei comuni da ISTAT, con default sui capoluoghi di provincia, citta' metropolitane e liberi consorzi;
- quotazioni OMI Agenzia Entrate per prezzi di vendita e canoni di locazione;
- redditi dichiarati comunali MEF/Dipartimento Finanze;
- mediana semplice delle zone OMI del comune, senza pesi per transazioni, stock o superficie.

Il comando produce tre versioni: capoluoghi di regione, regioni e province. Le versioni regionali
e provinciali sono aggregazioni dei capoluoghi di provincia scaricati da OMI, quindi vanno lette
come proxy territoriali basate sui capoluoghi e non come quotazioni ufficiali aggregate da OMI.

Tutti i comuni inclusi sono trattati allo stesso modo: non ci sono categorie o colori basati su
ipotesi preliminari.

Output:

- `outputs/charts/italia_locale/capoluoghi_regione/`
- `outputs/charts/italia_locale/regioni/`
- `outputs/charts/italia_locale/province/`
- `outputs/summary/italia_locale/`

## File

- `docs/definizioni.md`: glossario metodologico degli indicatori usati nel progetto.
- `scripts/helpers/config.py`: lista degli indicatori e dei filtri API.
- `scripts/helpers/api.py`: funzioni per scaricare dati Eurostat e OECD.
- `scripts/helpers/utils.py`: funzioni generiche riusabili.
- `scripts/helpers/grafici.py`: funzioni di plotting Eurostat e grafici base.
- `scripts/helpers/grafici_europei.py`: confronti Italia-UE sui principali indicatori abitativi.
- `scripts/helpers/grafici_locali_italia.py`: focus locale sui capoluoghi italiani con ISTAT, OMI e redditi MEF.
- `scripts/helpers/grafici_oecd.py`: confronti OECD sui prezzi delle case.
- `scripts/helpers/grafici_oecd_affordable.py`: grafici da OECD Affordable Housing Database.
- `scripts/run/estrai_ocse.py`: panoramica OCSE.
- `scripts/run/analisi_paesi.py`: confronto tra paesi scelti.
- `scripts/run/analisi_italia.py`: approfondimento Italia.
- `scripts/run/genera_grafici.py`: produzione dei grafici.
- `scripts/run/focus_locale_italia.py`: produzione del solo focus locale Italia.

## Fonti

- Eurostat API statistics: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-detailed-guidelines/api-statistics
- Eurostat housing statistics: https://ec.europa.eu/eurostat/web/housing
- Eurostat affordable housing indicators: https://ec.europa.eu/eurostat/web/housing/affordable-housing
- OECD SDMX API: https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html
- OECD average annual wages: https://www.oecd.org/en/data/indicators/average-annual-wages.html
- OECD housing prices: https://www.oecd.org/en/data/indicators/housing-prices.html
- OECD Affordable Housing Database: https://www.oecd.org/content/oecd/en/data/datasets/oecd-affordable-housing-database.html
- DG ECFIN AMECO database: https://economy-finance.ec.europa.eu/economic-research-and-databases/economic-databases/ameco-database_en
- Agenzia Entrate, consultazione quotazioni OMI: https://www1.agenziaentrate.gov.it/servizi/geopoi_omi/
- MEF Dipartimento Finanze, open data dichiarazioni redditi comunali: https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?opendata=yes

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

I tempi medi di rilascio permessi e di costruzione non risultano disponibili come serie armonizzata unica nei dataset Eurostat/OECD usati qui. Per ora vengono usati proxy osservabili: permessi edilizi, produzione nelle costruzioni, investimenti e stock abitativo per periodo di costruzione. Se troviamo una fonte amministrativa comparabile sui tempi effettivi, si puo' aggiungere in `scripts/helpers/config.py`.

Il focus locale Italia usa le quotazioni OMI come misura del livello territoriale dei prezzi e dei
canoni. Gli indicatori di affordability locale sono proxy: il prezzo di 80 mq e gli esempi di
affitto per 40, 50 e 60 mq vengono rapportati al reddito medio dichiarato comunale MEF. Il reddito
dichiarato e' per contribuente, non per nucleo familiare, e la mediana OMI comunale non e' pesata
per numero di abitazioni, transazioni o popolazione residente nelle zone. I canoni OMI non sono
canoni di offerta degli annunci immobiliari.
