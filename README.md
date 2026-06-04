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

## Come si esegue

Per utenti non esperti il modo piu' semplice e' usare VS Code:

1. apri uno script dentro `scripts/run/`;
2. modifica la chiamata finale `run(...)` in fondo al file, oppure le variabili in alto;
3. premi **Run Python File**.

Ogni script `run` ha una funzione con argomenti chiari. Per esempio, il file principale
`scripts/run/genera_grafici.py` finisce cosi':

```python
run(
    paesi=PAESI,
    output=OUTPUT,
    includi_borsino=INCLUDI_BORSINO,
    includi_affitti_brevi=INCLUDI_AFFITTI_BREVI,
    salta_mappe_focus_estero=SALTA_MAPPE_FOCUS_ESTERO,
)
```

Puoi anche lanciare gli script da terminale, senza argomenti:

```bash
python3 -m scripts.run.genera_grafici
```

## Quale Script Usare

| Cosa vuoi ottenere | Script da aprire | Cosa genera |
| --- | --- | --- |
| Tutto il progetto, scelta consigliata | `scripts/run/genera_grafici.py` | Confronti Eurostat/OECD, focus Italia, mappe/focus Francia e Germania quando richiesti |
| Solo focus locale Italia OMI/MEF | `scripts/run/focus_locale_italia.py` | Grafici per capoluoghi, regioni, province |
| Solo mappe comunali Italia | `scripts/run/mappe_comunali_italia.py` | Mappe regionali a livello comunale |
| Solo mappe e focus Francia/Germania | `scripts/run/mappe_focus_europa.py` | Mappe locali e focus Parigi/Berlino |
| Solo affitti brevi Italia | `scripts/run/affitti_brevi_italia.py` | CSV, classifiche e mappe dal registro CIN |
| Solo Borsino | `scripts/run/focus_borsino_italia.py` | Focus opzionale con API Borsino |
| Vedere dati OECD disponibili | `scripts/run/estrai_ocse.py` | Tabelle a terminale, non grafici |
| Confrontare valori OECD a terminale | `scripts/run/analisi_paesi.py` | Tabelle a terminale, non grafici |
| Snapshot Italia a terminale | `scripts/run/analisi_italia.py` | Riepilogo testuale, non grafici |

## Runner Principale

Il file da usare piu' spesso e' `scripts/run/genera_grafici.py`.

Argomento principale:

```python
paesi="ITA"
paesi=["ITA", "FRA", "DEU"]
paesi="tutti"
paesi="eurostat"
paesi="oecd"
```

Valori utili:

- `paesi="tutti"`: tutti i paesi disponibili in almeno una fonte;
- `paesi="eurostat"`: solo paesi Eurostat;
- `paesi="oecd"`: solo paesi OECD;
- `paesi=["ITA", "FRA", "DEU"]`: solo i paesi indicati.

Gli argomenti Borsino **non sono obbligatori**. Nel runner principale puoi non
scrivere proprio `versione_borsino`, `tipo_immobile_borsino`, `api_key_borsino`
e `pausa_borsino`: hanno gia' valori di default e vengono ignorati se
`includi_borsino=False`. Vengono usati solo se imposti:

```python
includi_borsino=True
```

In quel caso serve una chiave API Borsino, passata con `api_key_borsino="..."`
oppure con la variabile ambiente `BORSINO_API_KEY`.

Esempi di chiamata finale:

```python
run(paesi=["ITA", "FRA", "DEU"])
run(paesi="tutti", salta_mappe_focus_estero=True)
run(paesi="ITA", includi_affitti_brevi=True, regione_affitti_brevi="Sardegna")
run(paesi="ITA", includi_borsino=True, api_key_borsino="...")
```

## Valori Accettati

Per vedere tutti i codici paese accettati, apri `scripts/run/genera_grafici.py` e usa:

```python
run(mostra_lista_paesi=True)
```

Versioni accettate per focus locale e Borsino:

- `"tutte"`;
- `"capoluoghi-regione"`;
- `"regioni"`;
- `"province"`.

Profili accettati per affitti brevi:

- `"residenziale"`;
- `"privati"`;
- `"c2"`;
- `"totale"`.

Consultare il glossario metodologico degli indicatori:

```text
docs/definizioni.md
```

I risultati vengono salvati in cartelle per paese:

- `outputs/italia/charts/confronti/`
- `outputs/italia/charts/eurostat/`
- `outputs/italia/charts/locale/`
- `outputs/italia/charts/affitti_brevi/`
- `outputs/italia/summary/`
- `outputs/francia/charts/confronti/`
- `outputs/francia/charts/mappe/`
- `outputs/francia/charts/focus/`
- `outputs/francia/summary/`
- `outputs/germania/charts/confronti/`
- `outputs/germania/charts/mappe/`
- `outputs/germania/charts/focus/`
- `outputs/germania/summary/`

I grafici con banda min-max salvano anche un CSV nella `summary` del paese con paese minimo,
paese massimo, valore del paese evidenziato ed eventuale valore EU27 per ogni periodo.

I grafici riportano sempre fonte e dicitura in basso a sinistra:

```text
Fonte: ... | Elaborazione di Nazareno Lecis
```

## Indicatori OCSE

- salario medio annuo;
- indici nominali e reali dei prezzi delle case, dal 2000 in poi e ribasati a 2000=100;
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
Il dettaglio provinciale viene salvato in CSV; per evitare grafici illeggibili con troppe barre,
i PNG territoriali della versione provinciale sono mappe regionali calcolate come mediana delle
province disponibili in ogni regione e mappe nazionali con confini provinciali per gli stessi
indicatori.

Il progetto include anche mappe regionali a livello di singolo comune. Il comando genera di
default tutte le regioni, scaricando OMI per ogni comune e unendo i redditi MEF. Per fare test
rapidi imposta `regione="Sardegna"` nella funzione `run(...)` o nella variabile `REGIONE`.
Per evitare mismatch
dovuti ai riassetti provinciali, l'aggancio con i confini comunali openpolis usa il codice
catastale del comune.

Tutti i comuni inclusi sono trattati allo stesso modo: non ci sono categorie o colori basati su
ipotesi preliminari.

Output:

- `outputs/italia/charts/locale/capoluoghi_regione/`
- `outputs/italia/charts/locale/regioni/`
- `outputs/italia/charts/locale/mappe_regioni/`
- `outputs/italia/charts/locale/mappe_province/`
- `outputs/italia/charts/locale/mappe_comunali/`
- `outputs/italia/summary/locale/`

### Sezione aggiuntiva Borsino

Il focus Borsino e' opzionale e non sostituisce OMI. Usa l'API BorsinoPro/Borsino
Immobiliare `getConsoData`, con autenticazione via `BORSINO_API_KEY`, per estrarre
quotazioni comunali consolidate di vendita e affitto. Il default usa il tipo immobile
Borsino `20`, cioe' abitazioni in stabili civili: in questo modo la sezione non mescola
box auto, autorimesse, negozi o altre destinazioni non residenziali.

Nel runner principale questa sezione non parte da sola: bisogna attivarla con
`includi_borsino=True`. Tutti gli altri argomenti Borsino sono opzionali e possono
restare sui default, tranne la chiave API quando decidi di generare davvero questa sezione.

Per limitare chiamate API non necessarie, il comando Borsino genera di default i soli
capoluoghi di regione. Con `versione="province"` scarica i capoluoghi di provincia,
citta' metropolitane e liberi consorzi, salva il CSV e produce mappe regionali e
provinciali per gli stessi indicatori locali: prezzi, canoni, anni di reddito per
80 mq ed esempi di affitto per 40 e 60 mq.

Output:

- `outputs/italia/charts/locale/borsino/capoluoghi_regione/`
- `outputs/italia/charts/locale/borsino/regioni/`
- `outputs/italia/charts/locale/borsino/mappe_regioni/`
- `outputs/italia/charts/locale/borsino/mappe_province/`
- `outputs/italia/summary/locale/borsino/`

### Sezione aggiuntiva affitti brevi

La sezione affitti brevi usa il CSV nazionale del registro CIN del Ministero del Turismo.
Il nome tecnico della fonte e' BDSR, cioe' Banca Dati delle Strutture Ricettive e degli
Immobili destinati a Locazione Breve o per finalita' turistiche. Nei grafici viene evitato
l'acronimo e si usa "registro CIN".

Per misurare la pressione sugli affitti totali il codice aggiunge le famiglie in affitto
dal censimento permanente ISTAT 2021. Per gli indicatori su B&B e hotel aggiunge anche il
numero di abitazioni comunali. Se un denominatore ufficiale non e' disponibile per un comune,
l'indicatore resta vuoto e nelle mappe il comune resta grigio.

Il comando produce:

- CSV comunale con conteggi e quote del registro CIN;
- quota stimata di locazioni brevi private sul totale affitti:
  `locazioni brevi private CIN / (locazioni brevi private CIN + famiglie in affitto ISTAT 2021)`;
- quota di B&B sullo stock abitativo comunale;
- quota di hotel sullo stock abitativo comunale.

Output:

- `outputs/italia/charts/affitti_brevi/classifiche/`
- `outputs/italia/charts/affitti_brevi/mappe_comunali/`
- `outputs/italia/summary/affitti_brevi/`

## Mappe e Focus Francia/Germania

Le mappe estere producono affitti, valori di vendita o proxy di vendita e rapporti al reddito.

Francia:

- livello comunale;
- affitti da "Carte des loyers" 2025;
- prezzi di vendita da DVF stats whole period;
- reddito da livello di vita mediano comunale;
- focus dedicato a Parigi, aggregando gli arrondissement al codice comunale `75056`.

Germania:

- livello Kreise e citta-distretto, non singoli comuni, perche' gli indicatori INKAR usati non sono disponibili in modo completo a livello Gemeinde;
- affitti da INKAR Angebotsmieten 2024;
- valori di acquisto del suolo edificabile da INKAR Bauland 2022, quindi non una quotazione residenziale pura;
- reddito disponibile medio mensile per abitante da INKAR Haushaltseinkommen 2022, annualizzato;
- focus dedicato a Berlino (`11000`).

Output:

- `outputs/francia/charts/mappe/`
- `outputs/francia/charts/focus/`
- `outputs/francia/summary/`
- `outputs/germania/charts/mappe/`
- `outputs/germania/charts/focus/`
- `outputs/germania/summary/`

## File

- `docs/definizioni.md`: glossario metodologico degli indicatori usati nel progetto.
- `scripts/helpers/config.py`: lista degli indicatori e dei filtri API.
- `scripts/helpers/api.py`: funzioni per scaricare dati Eurostat e OECD.
- `scripts/helpers/utils.py`: funzioni generiche riusabili.
- `scripts/helpers/paesi.py`: configurazione dei paesi evidenziati nei confronti.
- `scripts/helpers/grafici.py`: funzioni di plotting Eurostat e grafici base.
- `scripts/helpers/grafici_europei.py`: confronti paese-UE sui principali indicatori abitativi.
- `scripts/helpers/mappe_focus_europa.py`: mappe e focus locali per Francia e Germania.
- `scripts/helpers/grafici_locali_italia.py`: focus locale sui capoluoghi italiani con ISTAT, OMI e redditi MEF.
- `scripts/helpers/mappe_comunali_italia.py`: mappe regionali a livello di singolo comune.
- `scripts/helpers/borsino.py`: focus locale aggiuntivo con API BorsinoPro/Borsino Immobiliare.
- `scripts/helpers/affitti_brevi.py`: sezione aggiuntiva su affitti brevi dal registro CIN.
- `scripts/helpers/grafici_oecd.py`: confronti OECD sui prezzi delle case.
- `scripts/helpers/grafici_oecd_affordable.py`: grafici da OECD Affordable Housing Database.
- `scripts/run/estrai_ocse.py`: panoramica OCSE.
- `scripts/run/analisi_paesi.py`: confronto tra paesi scelti.
- `scripts/run/analisi_italia.py`: approfondimento Italia.
- `scripts/run/genera_grafici.py`: produzione dei grafici.
- `scripts/run/focus_locale_italia.py`: produzione del solo focus locale Italia.
- `scripts/run/mappe_comunali_italia.py`: produzione delle mappe comunali regionali, default tutte le regioni.
- `scripts/run/mappe_focus_europa.py`: produzione delle mappe e dei focus locali esteri.
- `scripts/run/focus_borsino_italia.py`: produzione del focus locale aggiuntivo Borsino.
- `scripts/run/affitti_brevi_italia.py`: produzione della sezione affitti brevi dal registro CIN.

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
- BorsinoPro/Borsino Immobiliare API quotazioni: https://api.borsinopro.it/api-quotazioni.html
- Ministero del Turismo, registro CIN/BDSR: https://bdsr.ministeroturismo.gov.it/mappa-italia
- ISTAT, famiglie per titolo di godimento - comuni: http://dati-censimentipermanenti.istat.it/Index.aspx?DataSetCode=DCSS_HUDW
- ISTAT, dati per sezioni di censimento: https://www.istat.it/notizia/dati-per-sezioni-di-censimento/
- data.gouv.fr, DVF stats: https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/
- data.gouv.fr, Carte des loyers: https://www.data.gouv.fr/fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025/
- data.gouv.fr, niveau de vie median: https://www.data.gouv.fr/fr/datasets/niveau-de-vie-median/
- BBSR INKAR: https://www.inkar.de/
- MEF Dipartimento Finanze, open data dichiarazioni redditi comunali: https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?opendata=yes
- openpolis GeoJSON confini regionali: https://github.com/openpolis/geojson-italy

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
