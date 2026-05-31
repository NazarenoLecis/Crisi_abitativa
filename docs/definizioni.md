# Definizioni e metodologia degli indicatori

Questo documento serve come glossario metodologico del progetto. Non e' un report: spiega cosa misurano gli indicatori, come interpretarli e quali limiti hanno.

## Regole generali di lettura

- Molti indicatori sociali Eurostat derivano da EU-SILC, l'indagine europea su reddito e condizioni di vita.
- Gli indicatori in percentuale di popolazione non misurano il numero assoluto di persone, ma la quota della popolazione che ricade in una certa condizione.
- Gli indicatori basati su reddito disponibile equivalente correggono il reddito del nucleo familiare per dimensione e composizione del nucleo.
- Gli indicatori di poverta' relativa dipendono dalla distribuzione del reddito di ciascun paese: non misurano una soglia assoluta uguale per tutti i paesi.
- Gli indicatori di qualita' abitativa EU-SILC sono spesso dichiarativi: misurano cio' che le famiglie riportano nell'indagine.

## Affordability e poverta'

### Housing cost burden

Il peso dei costi abitativi misura il rapporto tra costi abitativi e reddito disponibile della famiglia. Nei dataset Eurostat usati qui e' espresso come percentuale del reddito disponibile.

I costi abitativi includono spese legate al diritto di vivere nell'abitazione: affitto o interessi del mutuo, utenze, manutenzione ordinaria, tasse e servizi obbligatori collegati all'abitazione. La misura Eurostat considera i costi abitativi e il reddito al netto dei sussidi abitativi quando l'indicatore richiede questa correzione.

Nel progetto:

- `estat_housing_cost_burden_median_a`
- dataset Eurostat `ilc_lvho08a`
- interpreta il valore come mediana della distribuzione del peso dei costi abitativi.

Limite: la mediana non dice quante persone superano una soglia critica; per quello si usa l'overburden rate.

### Housing cost overburden rate

L'housing cost overburden rate e' la quota di popolazione che vive in famiglie in cui i costi abitativi totali superano il 40% del reddito disponibile. Eurostat usa questa soglia per identificare situazioni di sovraccarico dei costi abitativi.

Nel progetto:

- `estat_housing_overburden_total_pc_a`
- `estat_housing_overburden_tenants_pc_a`
- dataset Eurostat `ilc_lvho07a` e `ilc_lvho07c`

Limite: la soglia del 40% e' convenzionale. Due famiglie con lo stesso rapporto costi/reddito possono avere condizioni materiali molto diverse se hanno redditi molto diversi.

### Rischio poverta' standard

Il rischio di poverta' standard misura la quota di persone con reddito disponibile equivalente, dopo i trasferimenti sociali, sotto il 60% della mediana nazionale del reddito disponibile equivalente.

Nel progetto:

- `estat_arop_standard_a`
- dataset Eurostat `tespm010`

Limite: e' una misura relativa. Se tutti i redditi di un paese scendono insieme, la poverta' relativa puo' non aumentare anche se il benessere materiale peggiora.

### Rischio poverta' dopo i costi abitativi

Il rischio di poverta' dopo i costi abitativi misura la quota di persone che risultano sotto la soglia di poverta' dopo aver sottratto i costi abitativi dal reddito disponibile equivalente. Serve a mostrare quanto l'abitare riduca il reddito effettivamente disponibile.

Nel progetto:

- `estat_arop_after_housing_costs_a`
- dataset Eurostat `ilc_li45`

Limite: va letto insieme al rischio poverta' standard. La differenza tra le due misure segnala il peso dei costi abitativi, ma non identifica da sola le cause: affitti, mutui, bollette, struttura familiare e redditi possono contribuire in modo diverso.

### Arretrati su mutuo, affitto o bollette

L'indicatore misura la quota di popolazione in famiglie che dichiarano arretrati nei pagamenti collegati a mutuo, affitto, bollette o acquisti rateali. E' un indicatore di stress finanziario immediato.

Nel progetto:

- `estat_arrears_housing_bills_total_a`
- dataset Eurostat `ilc_mdes05`

Limite: e' dichiarativo e cattura una difficolta' gia' materializzata nei pagamenti, non il rischio futuro.

## Qualita' abitativa e shortage

### Tasso di sovraffollamento abitativo

Eurostat considera una persona in sovraffollamento se vive in una famiglia che non dispone di un numero minimo di stanze. La regola richiede almeno:

- una stanza per la famiglia;
- una stanza per ogni coppia;
- una stanza per ogni single di almeno 18 anni;
- una stanza per ogni coppia di persone dello stesso sesso tra 12 e 17 anni;
- una stanza per ogni persona tra 12 e 17 anni non inclusa nella regola precedente;
- una stanza per ogni coppia di bambini sotto 12 anni.

Nel progetto:

- `estat_overcrowding_total_pc_a`
- dataset Eurostat `ilc_lvho05a`

Limite: misura densita' abitativa rispetto alla composizione familiare, ma non misura direttamente la disponibilita' di case sul mercato.

### Severe housing deprivation rate

La severe housing deprivation combina sovraffollamento e almeno un problema abitativo grave. In termini Eurostat, una persona e' in grave deprivazione abitativa se vive in un'abitazione sovraffollata e presenta almeno una tra queste condizioni: tetto che perde, umidita' o marciume; assenza di bagno/doccia e toilette interna; abitazione considerata troppo buia.

Nel progetto:

- `estat_severe_housing_deprivation_total_a`
- dataset Eurostat `ilc_mdho06a`

Limite: e' un indicatore severo per costruzione, quindi puo' sottostimare problemi abitativi non associati a sovraffollamento.

### Abitazioni con perdite, umidita' o marciume

L'indicatore misura la quota di popolazione che vive in abitazioni con almeno uno tra questi problemi: tetto che perde, pareti/pavimenti/fondazioni umide, marciume in infissi o pavimenti.

Nel progetto:

- `estat_damp_leaking_dwelling_total_a`
- dataset Eurostat `ilc_mdho01`

Limite: e' basato su autovalutazione della famiglia e non misura intensita', durata o gravita' tecnica del problema.

### Incapacita' di riscaldare adeguatamente la casa

L'indicatore misura la quota di popolazione che dichiara di non potersi permettere di mantenere la casa adeguatamente calda. E' spesso usato come proxy di poverta' energetica.

Nel progetto:

- `estat_inability_keep_home_warm_total_a`
- dataset Eurostat `ilc_mdes01`

Limite: la percezione di "adeguatamente calda" puo' variare per paese, clima, standard abitativi e aspettative sociali.

## Domanda latente e demografia

### Giovani 25-34 anni che vivono con i genitori

L'indicatore misura la quota di persone di 25-34 anni che vivono nello stesso nucleo dei genitori. Nel progetto viene usato come proxy di domanda abitativa compressa o ritardata.

Nel progetto:

- `estat_young_living_with_parents_25_34_a`
- dataset Eurostat `ilc_lvps08`

Limite: non e' solo un indicatore economico. Cultura familiare, mercato del lavoro, sistema universitario, welfare, matrimonio e disponibilita' di affitti influenzano il valore.

### Eta' media di uscita dalla casa dei genitori

L'indicatore stima l'eta' media a cui i giovani lasciano la casa dei genitori.

Nel progetto:

- `estat_age_leaving_parental_home_a`
- dataset Eurostat `yth_demo_030`

Limite: e' utile per confronti generali, ma non identifica da solo il peso relativo di salari, affitti, credito e norme sociali.

## Prezzi, redditi e investimenti

### House Price Index Eurostat

L'indice dei prezzi delle case Eurostat misura la variazione dei prezzi delle abitazioni residenziali acquistate dalle famiglie, nuove ed esistenti, incluse diverse tipologie di abitazione.

Nel progetto:

- `estat_hpi_total_i15_q`
- dataset Eurostat `prc_hpi_q`

Limite: misura prezzi di transazione, non accessibilita'. Per affordability va confrontato con redditi, affitti, tassi e condizioni creditizie.

### Indici OECD dei prezzi delle case

Gli indicatori OECD includono prezzi nominali, prezzi reali, rapporti prezzo/reddito e prezzo/affitto. Il prezzo reale e' ottenuto rapportando l'indice nominale al deflatore dei consumi; il rapporto prezzo/reddito confronta prezzi nominali delle case e reddito disponibile nominale pro capite.

Nel progetto:

- `oecd_real_house_price_index_q`
- `oecd_house_price_to_income_q`
- OECD `DF_HOUSE_PRICES`

Limite: molte serie sono indici, non livelli monetari. Un valore piu' alto indica crescita rispetto alla base, non necessariamente case piu' care in euro assoluti rispetto a un altro paese.

### Salario medio annuo OECD

Il salario medio annuo OECD misura le retribuzioni lorde medie dei lavoratori, spesso espresse in dollari USA a parita' di potere d'acquisto per favorire i confronti internazionali.

Nel progetto:

- `oecd_avg_annual_wage_usdppp_a`

Limite: il salario medio non e' il reddito disponibile familiare. Non include pienamente tasse, trasferimenti, composizione familiare e redditi non da lavoro.

### Investimenti in abitazioni

Gli investimenti in abitazioni sono una componente della formazione lorda di capitale fisso. Misurano il valore dell'investimento in abitazioni, non il numero di case costruite.

Nel progetto:

- `estat_gfcf_dwellings_pct_gdp_a`
- `oecd_gfcf_dwellings_current_prices_a`

Limite: possono aumentare per prezzi piu' alti dei lavori, non solo per maggiore quantita' costruita.

## Offerta abitativa

### Permessi edilizi

I permessi edilizi misurano autorizzazioni rilasciate per nuove abitazioni o superfici residenziali. Sono un indicatore anticipatore dell'offerta potenziale.

Nel progetto:

- `estat_residential_permits_dwellings_ths_a`
- `estat_residential_permits_floor_area_a`
- `estat_building_permits_dwellings_index_q`

Limite: un permesso non equivale a un'abitazione completata. Tempi di cantiere, rinunce, fallimenti, vincoli amministrativi e condizioni finanziarie possono impedire la trasformazione del permesso in stock abitativo.

### Produzione nelle costruzioni

Misura l'andamento dell'attivita' produttiva nel settore costruzioni.

Nel progetto:

- `estat_construction_production_index_a`

Limite: include attivita' piu' ampia della sola edilizia residenziale se il filtro usato e' il settore costruzioni complessivo.

### Stock abitativo da censimento

Lo stock abitativo del censimento misura il numero di abitazioni convenzionali e, quando disponibile, la distribuzione per periodo di costruzione.

Nel progetto:

- `estat_dwellings_total_2021`
- `estat_dwellings_occupied_2021`
- `estat_dwellings_unoccupied_2021`
- `estat_dwellings_built_before_1919_2021`
- `estat_dwellings_built_1919_1945_2021`
- `estat_dwellings_built_1946_1960_2021`
- `estat_dwellings_built_1961_1980_2021`
- `estat_dwellings_built_1981_2000_2021`
- `estat_dwellings_built_2001_2010_2021`
- `estat_dwellings_built_2011_2015_2021`
- `estat_dwellings_built_after_2016_2021`
- `estat_dwellings_built_unknown_2021`

Nel grafico sullo stock italiano le abitazioni sono raggruppate per periodo di costruzione. Nei confronti tra paesi vengono usate anche quote sintetiche, come la quota di stock costruita prima del 1981 e quella costruita dal 2001 in poi.

Limite: il censimento fotografa lo stock in un anno specifico; non misura direttamente qualita', efficienza energetica, localizzazione rispetto ai posti di lavoro o disponibilita' sul mercato.

### Abitazioni non occupate

Le abitazioni non occupate sono abitazioni convenzionali che al censimento non risultano occupate come residenza abituale. Nel progetto vengono rapportate allo stock totale per ottenere la quota di abitazioni non occupate.

Nel progetto:

- `estat_dwellings_unoccupied_2021 / estat_dwellings_total_2021`
- dataset Eurostat `cens_21dwop_r3`

Limite: non tutte le abitazioni non occupate sono immediatamente disponibili per ridurre uno shortage. Possono includere seconde case, immobili in ristrutturazione, abitazioni in aree con bassa domanda, unita' non agibili o stock trattenuto fuori dal mercato.

### Abitazioni per 1.000 abitanti

L'indicatore rapporta lo stock di abitazioni convenzionali alla popolazione residente. Serve a normalizzare il numero di case rispetto alla dimensione demografica del paese.

Nel progetto:

- `estat_dwellings_total_2021 / estat_population_total_a`
- dataset Eurostat `cens_21dwop_r3` e `demo_pjan`

Limite: non dice se le abitazioni sono localizzate dove c'e' domanda, se sono accessibili economicamente o se sono effettivamente disponibili sul mercato.

### Abitazioni per famiglia privata

L'indicatore rapporta lo stock di abitazioni convenzionali al numero di famiglie private. E' un proxy semplice della relazione tra stock e nuclei familiari.

Nel progetto:

- `estat_dwellings_total_2021 / estat_private_households_total_a`
- dataset Eurostat `cens_21dwop_r3` e `lfst_hhnhtych`

Limite: una famiglia privata non coincide perfettamente con domanda abitativa effettiva. Convivenze forzate, famiglie che vorrebbero formarsi ma restano insieme, seconde case e stock non disponibile possono alterare la lettura.

## Focus locale Italia

### Selezione dei comuni

Il focus locale usa il file ISTAT dei comuni italiani per selezionare i comuni da analizzare. Il progetto produce tre versioni:

- capoluoghi di regione;
- regioni;
- province, citta' metropolitane e liberi consorzi.

Le versioni regionali e provinciali sono costruite aggregando i capoluoghi di provincia scaricati da OMI. Sono quindi proxy territoriali basate sui capoluoghi e non quotazioni ufficiali OMI gia' aggregate per regione o provincia.

Nel progetto tutti i comuni selezionati sono trattati allo stesso modo: non vengono usate categorie preliminari per distinguere citta' "in pressione" e citta' di confronto.

### Quotazioni OMI

OMI significa Osservatorio del Mercato Immobiliare. E' una banca dati dell'Agenzia delle Entrate che pubblica quotazioni immobiliari per zone territoriali omogenee, dette zone OMI. Per ciascuna zona riporta intervalli di valori, non prezzi puntuali, distinti per destinazione d'uso, tipologia immobiliare e stato conservativo.

Le quotazioni OMI dell'Agenzia Entrate riportano quindi valori indicativi territoriali. Per il focus locale vengono usate le destinazioni residenziali e, quando disponibile, lo stato conservativo normale.

Nel progetto:

- prezzi di vendita in euro/mq;
- canoni di locazione in euro/mq per mese;
- mediana semplice delle zone OMI del comune;
- range tra zona meno cara e zona piu' cara del comune.

Limite: le quotazioni OMI sono intervalli territoriali, non prezzi effettivi di transazione o canoni contrattuali. La mediana usata nel progetto non e' pesata per numero di abitazioni, transazioni, superficie, popolazione o disponibilita' effettiva sul mercato.

### Reddito medio dichiarato comunale MEF

Il reddito medio dichiarato comunale viene calcolato dagli open data MEF/Dipartimento Finanze come rapporto tra reddito complessivo dichiarato e frequenza del reddito complessivo.

Nel progetto:

- reddito medio dichiarato;
- prezzo di 80 mq espresso in anni di reddito medio dichiarato;
- esempi di affitto per 40, 50 e 60 mq, espressi in euro mensili e come quota del reddito medio dichiarato.

Limite: il reddito dichiarato e' riferito ai contribuenti, non ai nuclei familiari. Non misura reddito disponibile equivalente, patrimonio, aiuti familiari, trasferimenti, evasione, composizione del nucleo o accesso al credito. Va quindi letto come proxy territoriale grezzo di pressione, non come misura definitiva di affordability. I canoni OMI sono quotazioni territoriali per zona e non coincidono con i canoni richiesti negli annunci immobiliari.

## Fonti metodologiche principali

- Eurostat, Housing cost overburden rate: https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/2138.pdf
- Eurostat, Overcrowding rate: https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/2137.pdf
- Eurostat, At-risk-of-poverty glossary: https://ec.europa.eu/eurostat/statistics-explained/SEPDF/cache/22724.pdf
- Eurostat, House price index metadata: https://ec.europa.eu/eurostat/cache/metadata/en/tipsho20_esms.htm
- Eurostat, EU-SILC metadata: https://ec.europa.eu/eurostat/cache/metadata/en/ilc_sieusilc.htm
- OECD, Housing prices indicator: https://www.oecd.org/en/data/indicators/housing-prices.html
- OECD, Residential Property Price Indices FAQ: https://www.oecd.org/en/data/insights/data-explainers/2024/07/Residential-Property-Price-Indices-and-related-housing-indicators-Frequently-Asked-Questions.html
- OECD, Average annual wages: https://www.oecd.org/en/data/indicators/average-annual-wages.html
