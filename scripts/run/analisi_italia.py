from scripts.helpers.api import scarica_italia
from scripts.helpers.utils import latest_value

dati = scarica_italia()

indicatori = {
    "Prezzi case (indice 2015=100)": "estat_hpi_total_i15_q",
    "Retribuzione netta annua (EUR)": "estat_net_earnings_aw100_eur_a",
    "Mediana costi casa su reddito (%)": "estat_housing_cost_burden_median_a",
    "Overburden costi casa (%)": "estat_housing_overburden_total_pc_a",
    "Overburden inquilini a prezzo di mercato (%)": "estat_housing_overburden_tenants_pc_a",
    "Arretrati mutuo/affitto/bollette (%)": "estat_arrears_housing_bills_total_a",
    "Sovraffollamento (%)": "estat_overcrowding_total_pc_a",
    "Severe housing deprivation (%)": "estat_severe_housing_deprivation_total_a",
    "Abitazioni con umidita'/perdite (%)": "estat_damp_leaking_dwelling_total_a",
    "Incapacita' di riscaldare la casa (%)": "estat_inability_keep_home_warm_total_a",
    "25-34enni con i genitori (%)": "estat_young_living_with_parents_25_34_a",
    "Eta' media uscita casa genitori": "estat_age_leaving_parental_home_a",
    "Popolazione totale": "estat_population_total_a",
    "Famiglie private (migliaia)": "estat_private_households_total_a",
    "Permessi nuove abitazioni (migliaia)": "estat_residential_permits_dwellings_ths_a",
    "Permessi residenziali (m2/1000 ab)": "estat_residential_permits_floor_area_a",
    "Produzione costruzioni (indice)": "estat_construction_production_index_a",
    "Costi costruzione nuovi edifici residenziali": "estat_new_residential_construction_cost_i21_q",
    "Investimenti in abitazioni (% PIL)": "estat_gfcf_dwellings_pct_gdp_a",
    "Rischio poverta' dopo costi abitativi (%)": "estat_arop_after_housing_costs_a",
    "Rischio poverta' standard (%)": "estat_arop_standard_a",
    "Abitazioni totali, censimento 2021": "estat_dwellings_total_2021",
    "Abitazioni pre-1919, censimento 2021": "estat_dwellings_built_before_1919_2021",
    "Abitazioni 1919-1945, censimento 2021": "estat_dwellings_built_1919_1945_2021",
    "Abitazioni 1946-1960, censimento 2021": "estat_dwellings_built_1946_1960_2021",
    "Abitazioni 1961-1980, censimento 2021": "estat_dwellings_built_1961_1980_2021",
    "OCSE rapporto prezzi/reddito": "oecd_house_price_to_income_q",
    "OCSE salario medio annuo (USD PPP)": "oecd_avg_annual_wage_usdppp_a",
}

print("Snapshot Italia")
print("Fonti: Eurostat API e OECD SDMX API")
for etichetta, indicatore in indicatori.items():
    ultimo = latest_value(dati, indicatore)
    if ultimo is None:
        print(f"- {etichetta}: dato non disponibile")
        continue
    periodo, valore = ultimo
    print(f"- {etichetta}: {valore:,.2f} ({periodo})")

permessi = latest_value(dati, "estat_residential_permits_dwellings_ths_a")
famiglie = latest_value(dati, "estat_private_households_total_a")
stock_totale = latest_value(dati, "estat_dwellings_total_2021")
stock_vecchio = [
    latest_value(dati, "estat_dwellings_built_before_1919_2021"),
    latest_value(dati, "estat_dwellings_built_1919_1945_2021"),
    latest_value(dati, "estat_dwellings_built_1946_1960_2021"),
    latest_value(dati, "estat_dwellings_built_1961_1980_2021"),
]

print()
print("Indicatori derivati per shortage/offerta")
if permessi and famiglie:
    periodo = f"{permessi[0]} / famiglie {famiglie[0]}"
    valore = permessi[1] / famiglie[1] * 1000
    print(f"- Permessi nuove abitazioni per 1.000 famiglie: {valore:,.2f} ({periodo})")

if stock_totale and all(stock_vecchio):
    abitazioni_pre_1981 = sum(valore for periodo, valore in stock_vecchio)
    quota = abitazioni_pre_1981 / stock_totale[1] * 100
    print(f"- Quota abitazioni costruite prima del 1981: {quota:,.2f}% (censimento 2021)")
