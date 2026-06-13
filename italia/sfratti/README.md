# Sfratti Italia

Questa cartella contiene i dati 2024 sugli sfratti a livello nazionale, regionale e provinciale, piu' la serie storica nazionale 2004-2024.

## File

- `sfratti_italia_2024.csv`: totale Italia 2024.
- `sfratti_regioni_2024.csv`: dettaglio regionale 2024.
- `sfratti_province_2024.csv`: dettaglio provinciale 2024.
- `sfratti_italia_serie_storica_2004_2024.csv`: serie storica nazionale.

## Fonte

La fonte originaria e' il Ministero dell'Interno, "Procedure di rilascio di immobili ad uso abitativo". Lo script `scripts/run/aggiorna_sfratti_italia.py` usa il mirror SICET del file Excel ministeriale quando il sito ministeriale non consente il download automatico.

## Nota

Le richieste di esecuzione non sono una misura diretta dei tempi medi di sfratto: dipendono dalle prassi degli uffici giudiziari locali e dall'iter concreto delle procedure.
