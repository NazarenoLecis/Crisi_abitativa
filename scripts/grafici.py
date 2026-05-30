from pathlib import Path
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import pandas as pd
from utils import WATERMARK, latest_by_country, testo_fonte


COLORE_PRINCIPALE = "#0D3B66"
COLORE_ITALIA = "#C1121F"
COLORE_EU27 = "#6F6F6F"
COLORE_BANDA = "#D9D9D9"
COLORE_STOCK = "#8A5A44"

GRAFICI_CONFRONTO_EUROSTAT = [
    ("estat_hpi_total_i15_q", "confronto_prezzi_case.png"),
    ("estat_net_earnings_aw100_eur_a", "confronto_retribuzione_netta.png"),
    ("estat_housing_cost_burden_median_a", "confronto_peso_mediano_costi_abitativi.png"),
    ("estat_housing_overburden_total_pc_a", "confronto_housing_overburden.png"),
    ("estat_housing_overburden_tenants_pc_a", "confronto_housing_overburden_inquilini.png"),
    ("estat_arrears_housing_bills_total_a", "confronto_arretrati_casa_bollette.png"),
    ("estat_arop_after_housing_costs_a", "confronto_rischio_poverta_dopo_costi_abitativi.png"),
    ("estat_arop_standard_a", "confronto_rischio_poverta_standard.png"),
    ("estat_overcrowding_total_pc_a", "confronto_sovraffollamento.png"),
    ("estat_severe_housing_deprivation_total_a", "confronto_severe_housing_deprivation.png"),
    ("estat_damp_leaking_dwelling_total_a", "confronto_abitazioni_umidita_perdite.png"),
    ("estat_inability_keep_home_warm_total_a", "confronto_casa_non_riscaldata.png"),
    ("estat_young_living_with_parents_25_34_a", "confronto_giovani_con_genitori.png"),
    ("estat_age_leaving_parental_home_a", "confronto_eta_uscita_casa_genitori.png"),
    ("estat_residential_permits_floor_area_a", "confronto_permessi_residenziali_m2_abitanti.png"),
    ("estat_building_permits_dwellings_index_q", "confronto_permessi_costruzione_indice.png"),
    ("estat_construction_production_index_a", "confronto_produzione_costruzioni.png"),
    ("estat_new_residential_construction_cost_i21_q", "confronto_costi_costruzione_residenziale.png"),
    ("estat_gfcf_dwellings_pct_gdp_a", "confronto_investimenti_abitazioni_pil.png"),
]

GRAFICI_NON_CONFRONTABILI_LINEA = [
    ("estat_population_total_a", "italia_popolazione_totale.png"),
    ("estat_private_households_total_a", "italia_famiglie_private.png"),
    ("estat_residential_permits_dwellings_ths_a", "italia_permessi_nuove_abitazioni.png"),
]

ITALIA_STOCK_ABITAZIONI = [
    "estat_dwellings_built_before_1919_2021",
    "estat_dwellings_built_1919_1945_2021",
    "estat_dwellings_built_1946_1960_2021",
    "estat_dwellings_built_1961_1980_2021",
]

CODICI_AGGREGATI = {"EU27_2020", "EU", "EA20", "EA19"}


def cartella_fonte(cartella_output, fonte, sezione=None):
    parti = [Path(cartella_output), fonte]
    if sezione:
        parti.append(sezione)

    output = Path(*parti)
    output.mkdir(parents=True, exist_ok=True)
    return output


def aggiungi_footer(figura, frame):
    figura.text(
        0.01,
        0.01,
        f"{testo_fonte(frame)} | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=9,
        alpha=0.82,
    )


def formatta_asse_y(asse, percentuale=False):
    if percentuale:
        asse.yaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.0f}%"))
        return

    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    asse.yaxis.set_major_formatter(formatter)
    asse.ticklabel_format(axis="y", style="plain", useOffset=False)


def periodo_to_datetime(periodo):
    testo = str(periodo)
    if "-Q" in testo:
        return pd.Period(testo, freq="Q").to_timestamp(how="end")
    if testo.isdigit() and len(testo) == 4:
        return pd.Timestamp(year=int(testo), month=1, day=1)
    return pd.to_datetime(testo, errors="coerce")


def prepara_serie_temporale(serie):
    risultato = serie.copy()
    risultato["data_plot"] = risultato["time_period"].map(periodo_to_datetime)
    return risultato.dropna(subset=["data_plot"]).sort_values("data_plot")


def formatta_asse_date(asse, serie, massimo_etichette=8):
    serie_date = serie.dropna(subset=["data_plot"]).drop_duplicates("data_plot").sort_values("data_plot")
    if serie_date.empty:
        return

    numero_osservazioni = len(serie_date)
    passo = max(1, round(numero_osservazioni / massimo_etichette))
    posizioni = list(range(0, numero_osservazioni, passo))
    ultima_posizione = numero_osservazioni - 1

    if posizioni[-1] != ultima_posizione:
        distanza_da_ultima = ultima_posizione - posizioni[-1]
        distanza_minima = max(1, round(passo * 0.7))
        if distanza_da_ultima < distanza_minima and len(posizioni) > 1:
            posizioni[-1] = ultima_posizione
        else:
            posizioni.append(ultima_posizione)

    ticks = serie_date.iloc[posizioni]["data_plot"]
    labels = serie_date.iloc[posizioni]["time_period"].astype(str)
    asse.set_xticks(ticks)
    asse.set_xticklabels(labels)

    inizio = serie_date["data_plot"].min()
    fine = serie_date["data_plot"].max()
    margine = max((fine - inizio) * 0.015, pd.Timedelta(days=20))
    asse.set_xlim(inizio - margine, fine + margine)

    contiene_trimestri = labels.str.contains("-Q").any()
    asse.tick_params(axis="x", labelrotation=35 if contiene_trimestri else 0)


def unisci_serie_per_asse(serie_principali):
    serie_non_vuote = [serie for serie in serie_principali if not serie.empty]
    if not serie_non_vuote:
        return pd.DataFrame(columns=["data_plot", "time_period"])
    return pd.concat(serie_non_vuote, ignore_index=True)


def periodo_comune(serie_a, serie_b):
    if serie_a.empty or serie_b.empty:
        return None

    inizio = max(serie_a["data_plot"].min(), serie_b["data_plot"].min())
    fine = min(serie_a["data_plot"].max(), serie_b["data_plot"].max())
    if inizio > fine:
        return None
    return inizio, fine


def limita_periodo(serie, inizio, fine):
    return serie.loc[(serie["data_plot"] >= inizio) & (serie["data_plot"] <= fine)].copy()


def salva_figura(figura, percorso):
    plt.tight_layout(rect=[0, 0.07, 1, 1])
    figura.savefig(percorso, dpi=160)
    plt.close(figura)


def anni_disponibili_snapshot(frame):
    anni = frame["time_period"].dropna().astype(str).unique().tolist()
    return sorted(anni)


def titolo_snapshot(titolo, frame):
    anni = anni_disponibili_snapshot(frame)
    if len(anni) == 1:
        return f"{titolo}, {anni[0]}"
    if len(anni) > 1:
        return f"{titolo}, ultimo anno disponibile ({anni[0]}-{anni[-1]})"
    return titolo


def etichette_paesi_snapshot(frame):
    anni = anni_disponibili_snapshot(frame)
    if len(anni) <= 1:
        return frame["country_code"].astype(str)

    etichette = []
    for riga in frame.itertuples(index=False):
        etichette.append(f"{riga.country_code}\n{riga.time_period}")
    return etichette


def grafico_linea_indicatore(frame, indicatore, nome_file, cartella_output="outputs/charts"):
    serie = frame.loc[(frame["country_code"] == "ITA") & (frame["indicator_id"] == indicatore)]
    if serie.empty:
        return None

    serie = prepara_serie_temporale(serie)
    figura, asse = plt.subplots(figsize=(11, 6))
    asse.plot(serie["data_plot"], serie["value"], color=COLORE_ITALIA, linewidth=2.3)
    asse.set_title(serie["indicator_name"].iloc[0], fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel(serie["unit"].iloc[0])
    asse.grid(alpha=0.22)
    formatta_asse_y(asse)
    formatta_asse_date(asse, serie)
    aggiungi_footer(figura, serie)

    percorso = cartella_fonte(cartella_output, "eurostat", "non_confrontabili") / nome_file
    salva_figura(figura, percorso)
    return percorso


def grafico_stock_abitazioni_italia(frame, cartella_output="outputs/charts"):
    dati = frame.loc[(frame["country_code"] == "ITA") & (frame["indicator_id"].isin(ITALIA_STOCK_ABITAZIONI))].copy()
    if dati.empty:
        return None

    ordine = {indicatore: posizione for posizione, indicatore in enumerate(ITALIA_STOCK_ABITAZIONI)}
    dati["ordine"] = dati["indicator_id"].map(ordine)
    dati = dati.sort_values("ordine")
    etichette = ["Prima del 1919", "1919-1945", "1946-1960", "1961-1980"]
    figura, asse = plt.subplots(figsize=(11, 6))
    asse.bar(etichette, dati["value"], color=COLORE_STOCK)
    asse.set_title("Italia - stock abitativo per periodo di costruzione, 2021", fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel("abitazioni")
    asse.grid(axis="y", alpha=0.22)
    formatta_asse_y(asse)
    aggiungi_footer(figura, dati)

    percorso = cartella_fonte(cartella_output, "eurostat", "non_confrontabili") / "italia_stock_abitazioni_periodo_costruzione.png"
    salva_figura(figura, percorso)
    return percorso


def grafici_non_confrontabili(frame, cartella_output="outputs/charts", mostra_progresso=False):
    percorsi = []
    totale = len(GRAFICI_NON_CONFRONTABILI_LINEA)
    for posizione, (indicatore, nome_file) in enumerate(GRAFICI_NON_CONFRONTABILI_LINEA, start=1):
        if mostra_progresso:
            print(f"[Non confrontabili {posizione}/{totale}] Creo {nome_file}", flush=True)

        percorso = grafico_linea_indicatore(frame, indicatore, nome_file, cartella_output)
        if percorso:
            percorsi.append(percorso)

    if mostra_progresso:
        print("[Non confrontabili] Creo italia_stock_abitazioni_periodo_costruzione.png", flush=True)

    stock = grafico_stock_abitazioni_italia(frame, cartella_output)
    if stock:
        percorsi.append(stock)
    return percorsi


def grafico_ue_banda(frame, indicatore, nome_file, cartella_output="outputs/charts"):
    serie = frame.loc[frame["indicator_id"] == indicatore].copy()
    if serie.empty:
        return None

    serie = prepara_serie_temporale(serie)
    paesi = serie.loc[~serie["country_code"].isin(CODICI_AGGREGATI)]
    italia = serie.loc[serie["country_code"] == "ITA"]
    eu27 = serie.loc[serie["country_code"] == "EU27_2020"]
    if paesi.empty or italia.empty:
        return None

    periodo = periodo_comune(italia, eu27)
    if periodo is not None:
        inizio, fine = periodo
        paesi = limita_periodo(paesi, inizio, fine)
        italia = limita_periodo(italia, inizio, fine)
        eu27 = limita_periodo(eu27, inizio, fine)

    banda = paesi.groupby("data_plot")["value"].agg(["min", "max"]).reset_index()
    banda["data_num"] = mdates.date2num(banda["data_plot"].to_numpy(dtype="datetime64[ms]"))

    figura, asse = plt.subplots(figsize=(11, 6))
    asse.fill_between(
        banda["data_num"],
        banda["min"],
        banda["max"],
        color=COLORE_BANDA,
        alpha=0.75,
        label="Min-max paesi UE",
    )
    if not eu27.empty:
        asse.plot(eu27["data_plot"], eu27["value"], color=COLORE_EU27, linewidth=2.0, label="EU27")
    asse.plot(italia["data_plot"], italia["value"], color=COLORE_ITALIA, linewidth=2.4, label="Italia")
    asse.set_title(serie["indicator_name"].iloc[0], fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel(serie["unit"].iloc[0])
    asse.grid(alpha=0.2)
    formatta_asse_y(asse)
    asse.legend(loc="best", frameon=False)
    serie_asse = unisci_serie_per_asse([italia, eu27])
    formatta_asse_date(asse, serie_asse)
    aggiungi_footer(figura, serie)

    percorso = cartella_fonte(cartella_output, "eurostat", "confronti") / nome_file
    salva_figura(figura, percorso)
    return percorso


def grafici_confronto_eurostat(frame, cartella_output="outputs/charts", mostra_progresso=False):
    percorsi = []
    totale = len(GRAFICI_CONFRONTO_EUROSTAT)
    for posizione, (indicatore, nome_file) in enumerate(GRAFICI_CONFRONTO_EUROSTAT, start=1):
        if mostra_progresso:
            print(f"[Confronti Eurostat {posizione}/{totale}] Creo {nome_file}", flush=True)

        percorso = grafico_ue_banda(frame, indicatore, nome_file, cartella_output)
        if percorso:
            percorsi.append(percorso)
    return percorsi


def grafico_ue_affordability(frame, cartella_output="outputs/charts"):
    ultimi = latest_by_country(frame, "estat_housing_overburden_total_pc_a")
    ultimi = ultimi.loc[~ultimi["country_code"].isin(CODICI_AGGREGATI)]
    if ultimi.empty:
        return None

    ultimi = ultimi.sort_values("value", ascending=False)
    figura, asse = plt.subplots(figsize=(12, 6))
    colori = [COLORE_ITALIA if codice == "ITA" else COLORE_PRINCIPALE for codice in ultimi["country_code"]]
    asse.bar(etichette_paesi_snapshot(ultimi), ultimi["value"], color=colori)
    asse.set_title(titolo_snapshot("UE - tasso di sovraccarico dei costi abitativi", ultimi), fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel("percentuale popolazione")
    asse.grid(axis="y", alpha=0.22)
    formatta_asse_y(asse)
    aggiungi_footer(figura, ultimi)

    percorso = cartella_fonte(cartella_output, "eurostat", "confronti") / "eurostat_housing_overburden_latest.png"
    salva_figura(figura, percorso)
    return percorso


def grafico_ue_shortage_proxy(frame, cartella_output="outputs/charts"):
    ultimi = latest_by_country(frame, "estat_young_living_with_parents_25_34_a")
    ultimi = ultimi.loc[~ultimi["country_code"].isin(CODICI_AGGREGATI)]
    if ultimi.empty:
        return None

    ultimi = ultimi.sort_values("value", ascending=False)
    figura, asse = plt.subplots(figsize=(12, 6))
    colori = [COLORE_ITALIA if codice == "ITA" else COLORE_PRINCIPALE for codice in ultimi["country_code"]]
    asse.bar(etichette_paesi_snapshot(ultimi), ultimi["value"], color=colori)
    asse.set_title(titolo_snapshot("UE - 25-34enni che vivono con i genitori", ultimi), fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel("percentuale popolazione 25-34")
    asse.grid(axis="y", alpha=0.22)
    formatta_asse_y(asse)
    aggiungi_footer(figura, ultimi)

    percorso = cartella_fonte(cartella_output, "eurostat", "confronti") / "eurostat_giovani_con_genitori_latest.png"
    salva_figura(figura, percorso)
    return percorso


def crea_grafici(frame, cartella_output="outputs/charts", mostra_progresso=False):
    percorsi = []
    if mostra_progresso:
        print("Inizio generazione confronti Eurostat.", flush=True)
    percorsi.extend(grafici_confronto_eurostat(frame, cartella_output, mostra_progresso=mostra_progresso))

    if mostra_progresso:
        print("Inizio generazione grafici Eurostat non confrontabili.", flush=True)
    percorsi.extend(grafici_non_confrontabili(frame, cartella_output, mostra_progresso=mostra_progresso))

    grafici_finali = [
        ("eurostat_housing_overburden_latest.png", grafico_ue_affordability),
        ("eurostat_giovani_con_genitori_latest.png", grafico_ue_shortage_proxy),
    ]
    for nome_file, funzione in grafici_finali:
        if mostra_progresso:
            print(f"[Grafici confronto] Creo {nome_file}", flush=True)

        percorso = funzione(frame, cartella_output)
        if percorso:
            percorsi.append(percorso)

    if mostra_progresso:
        print(f"Generazione grafici completata: {len(percorsi)} file creati.", flush=True)
    return percorsi
