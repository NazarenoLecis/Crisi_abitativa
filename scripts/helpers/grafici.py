from pathlib import Path
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, ScalarFormatter
import pandas as pd
from scripts.helpers.paesi import cartella_paese, normalizza_codici_paesi, profilo_paese
from scripts.helpers.utils import WATERMARK, latest_by_country, salva_min_max_summary, testo_fonte, testo_min_max_ultimo_periodo


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

GRAFICI_ITALIA_LINEA = [
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

ETA_STOCK_ABITAZIONI = [
    ("estat_dwellings_built_before_1919_2021", "Prima del 1919"),
    ("estat_dwellings_built_1919_1945_2021", "1919-1945"),
    ("estat_dwellings_built_1946_1960_2021", "1946-1960"),
    ("estat_dwellings_built_1961_1980_2021", "1961-1980"),
    ("estat_dwellings_built_1981_2000_2021", "1981-2000"),
    ("estat_dwellings_built_2001_2010_2021", "2001-2010"),
    ("estat_dwellings_built_2011_2015_2021", "2011-2015"),
    ("estat_dwellings_built_after_2016_2021", "2016 e dopo"),
    ("estat_dwellings_built_unknown_2021", "Non indicato"),
]

INDICATORI_ETA_STOCK_ABITAZIONI = [
    "estat_dwellings_built_before_1919_2021",
    "estat_dwellings_built_1919_1945_2021",
    "estat_dwellings_built_1946_1960_2021",
    "estat_dwellings_built_1961_1980_2021",
    "estat_dwellings_built_1981_2000_2021",
    "estat_dwellings_built_2001_2010_2021",
    "estat_dwellings_built_2011_2015_2021",
    "estat_dwellings_built_after_2016_2021",
    "estat_dwellings_built_unknown_2021",
]


INDICATORI_STOCK_PRE_1981 = [
    "estat_dwellings_built_before_1919_2021",
    "estat_dwellings_built_1919_1945_2021",
    "estat_dwellings_built_1946_1960_2021",
    "estat_dwellings_built_1961_1980_2021",
]

INDICATORI_STOCK_DAL_2001 = [
    "estat_dwellings_built_2001_2010_2021",
    "estat_dwellings_built_2011_2015_2021",
    "estat_dwellings_built_after_2016_2021",
]

COLORI_ETA_STOCK = {
    "Prima del 1919": "#5E3023",
    "1919-1945": "#895737",
    "1946-1960": "#B88B4A",
    "1961-1980": "#D9B166",
    "1981-2000": "#8AA29E",
    "2001-2010": "#4F7CAC",
    "2011-2015": "#2D5D7B",
    "2016 e dopo": "#153B50",
    "Non indicato": "#B8B8B8",
}

CODICI_AGGREGATI = {"EU27_2020", "EU", "EA20", "EA19"}


def colore_paese_confronto(codice, profilo):
    if codice == profilo["iso3"]:
        return profilo["colore"]
    if codice == "ITA":
        return COLORE_ITALIA
    return COLORE_PRINCIPALE


def cartella_fonte(cartella_output, fonte, sezione=None):
    if fonte == "eurostat" and sezione == "italia":
        return cartella_paese(cartella_output, "ITA", "eurostat")

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


def formatta_asse_x(asse, percentuale=False):
    if percentuale:
        asse.xaxis.set_major_formatter(FuncFormatter(lambda valore, posizione: f"{valore:.0f}%"))
        return

    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    asse.xaxis.set_major_formatter(formatter)
    asse.ticklabel_format(axis="x", style="plain", useOffset=False)


def aggiungi_nota_min_max(asse, testo):
    if not testo:
        return

    asse.text(
        0.01,
        0.97,
        testo,
        transform=asse.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#333333",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "boxstyle": "round,pad=0.25"},
    )


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

    percorso = cartella_fonte(cartella_output, "eurostat", "italia") / nome_file
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

    percorso = cartella_fonte(cartella_output, "eurostat", "italia") / "italia_stock_abitazioni_periodo_costruzione.png"
    salva_figura(figura, percorso)
    return percorso


def grafico_stock_abitazioni_italia_completo(frame, cartella_output="outputs/charts"):
    dati = frame.loc[(frame["country_code"] == "ITA") & (frame["indicator_id"].isin(INDICATORI_ETA_STOCK_ABITAZIONI))].copy()
    dati = dati.loc[dati["value"] > 0].copy()
    if dati.empty:
        return None

    ordine = {indicatore: posizione for posizione, indicatore in enumerate(INDICATORI_ETA_STOCK_ABITAZIONI)}
    etichette = {indicatore: etichetta for indicatore, etichetta in ETA_STOCK_ABITAZIONI}
    dati["ordine"] = dati["indicator_id"].map(ordine)
    dati = dati.sort_values("ordine")
    dati["value_mln"] = dati["value"] / 1_000_000
    dati["etichetta"] = dati["indicator_id"].map(etichette)

    figura, asse = plt.subplots(figsize=(11, 6))
    asse.barh(dati["etichetta"], dati["value_mln"], color=COLORE_STOCK)
    asse.invert_yaxis()
    asse.set_title(
        "Italia - stock abitativo per periodo di costruzione completo, 2021",
        fontsize=14,
        fontweight="bold",
        loc="left",
    )
    asse.set_xlabel("milioni di abitazioni")
    asse.grid(axis="x", alpha=0.22)
    formatta_asse_x(asse)
    aggiungi_footer(figura, dati)

    percorso = (
        cartella_fonte(cartella_output, "eurostat", "italia")
        / "italia_stock_abitazioni_periodo_costruzione_completo.png"
    )
    salva_figura(figura, percorso)
    return percorso


def valori_indicatore_per_paese(frame, indicatore, anno_preferito=None):
    dati = frame.loc[frame["indicator_id"] == indicatore].copy()
    if dati.empty:
        return dati

    righe = []
    for paese, gruppo in dati.groupby("country_code"):
        gruppo = gruppo.sort_values("time_period")
        if anno_preferito is not None:
            preferito = gruppo.loc[gruppo["time_period"].astype(str) == str(anno_preferito)]
            if not preferito.empty:
                righe.append(preferito.iloc[-1])
                continue

        righe.append(gruppo.iloc[-1])

    return pd.DataFrame(righe).reset_index(drop=True)


def grafico_barre_paesi(
    dati,
    titolo,
    asse_y,
    nome_file,
    cartella_output="outputs/charts",
    percentuale=False,
    paese_focus="ITA",
):
    if dati.empty:
        return None

    dati = dati.loc[~dati["country_code"].isin(CODICI_AGGREGATI)].copy()
    if dati.empty:
        return None

    profilo = profilo_paese(paese_focus)
    dati = dati.sort_values("value", ascending=False)
    figura, asse = plt.subplots(figsize=(12.5, 6))
    colori = [colore_paese_confronto(codice, profilo) for codice in dati["country_code"]]
    asse.bar(etichette_paesi_snapshot(dati), dati["value"], color=colori)
    asse.set_title(titolo_snapshot(titolo, dati), fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel(asse_y)
    asse.grid(axis="y", alpha=0.22)
    formatta_asse_y(asse, percentuale=percentuale)
    aggiungi_footer(figura, dati)

    percorso = cartella_paese(cartella_output, profilo, "confronti") / nome_file
    salva_figura(figura, percorso)
    return percorso


def grafico_stock_totale_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = valori_indicatore_per_paese(frame, "estat_dwellings_total_2021", anno_preferito="2021")
    if dati.empty:
        return None

    dati = dati.copy()
    dati["value"] = dati["value"] / 1_000_000
    dati["unit"] = "milioni di abitazioni"
    return grafico_barre_paesi(
        dati,
        "Abitazioni convenzionali totali",
        "milioni di abitazioni",
        "eurostat_stock_abitazioni_totali_2021.png",
        cartella_output,
        paese_focus=paese_focus,
    )


def prepara_rapporto_stock(frame, numeratore, denominatore, nome, unita, moltiplicatore=1, fattore_denominatore=1):
    dati_numeratore = valori_indicatore_per_paese(frame, numeratore, anno_preferito="2021")
    dati_denominatore = valori_indicatore_per_paese(frame, denominatore, anno_preferito="2021")
    if dati_numeratore.empty or dati_denominatore.empty:
        return pd.DataFrame()

    sinistra = dati_numeratore[
        ["country_code", "country_name", "time_period", "value", "source", "source_dataset"]
    ].rename(
        columns={
            "time_period": "time_period_numeratore",
            "value": "value_numeratore",
            "source": "source_numeratore",
            "source_dataset": "dataset_numeratore",
        }
    )
    destra = dati_denominatore[["country_code", "time_period", "value", "source", "source_dataset"]].rename(
        columns={
            "time_period": "time_period_denominatore",
            "value": "value_denominatore",
            "source": "source_denominatore",
            "source_dataset": "dataset_denominatore",
        }
    )
    dati = sinistra.merge(destra, on="country_code", how="inner")
    dati = dati.loc[(dati["value_denominatore"].notna()) & (dati["value_denominatore"] != 0)].copy()
    if dati.empty:
        return dati

    denominatore_calcolo = dati["value_denominatore"] * fattore_denominatore
    dati["value"] = dati["value_numeratore"] / denominatore_calcolo * moltiplicatore
    dati["source"] = dati[["source_numeratore", "source_denominatore"]].agg(
        lambda valori: ", ".join(sorted(set(valori.dropna()))),
        axis=1,
    )
    dati["source_dataset"] = dati[["dataset_numeratore", "dataset_denominatore"]].agg(
        lambda valori: ", ".join(sorted(set(valori.dropna()))),
        axis=1,
    )
    dati["indicator_id"] = nome
    dati["indicator_name"] = nome
    dati["theme"] = "stock"
    dati["unit"] = unita
    dati["frequency"] = "A"
    dati["time_period"] = dati.apply(periodo_rapporto_stock, axis=1)
    colonne = [
        "source",
        "source_dataset",
        "indicator_id",
        "indicator_name",
        "theme",
        "country_code",
        "country_name",
        "time_period",
        "value",
        "unit",
        "frequency",
    ]
    return dati[colonne]


def periodo_rapporto_stock(riga):
    numeratore = str(riga["time_period_numeratore"])
    denominatore = str(riga["time_period_denominatore"])
    if numeratore == denominatore:
        return numeratore
    return f"{numeratore}/{denominatore}"


def grafico_stock_non_occupato_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_rapporto_stock(
        frame,
        "estat_dwellings_unoccupied_2021",
        "estat_dwellings_total_2021",
        "Quota di abitazioni non occupate sullo stock",
        "% dello stock abitativo",
        moltiplicatore=100,
    )
    return grafico_barre_paesi(
        dati,
        "Abitazioni non occupate sullo stock",
        "% dello stock abitativo",
        "eurostat_abitazioni_non_occupate_stock_2021.png",
        cartella_output,
        percentuale=True,
        paese_focus=paese_focus,
    )


def grafico_abitazioni_per_1000_abitanti_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_rapporto_stock(
        frame,
        "estat_dwellings_total_2021",
        "estat_population_total_a",
        "Abitazioni per 1.000 abitanti",
        "abitazioni per 1.000 abitanti",
        moltiplicatore=1000,
    )
    return grafico_barre_paesi(
        dati,
        "Abitazioni per 1.000 abitanti",
        "abitazioni per 1.000 abitanti",
        "eurostat_abitazioni_per_1000_abitanti_2021.png",
        cartella_output,
        paese_focus=paese_focus,
    )


def grafico_abitazioni_per_famiglia_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_rapporto_stock(
        frame,
        "estat_dwellings_total_2021",
        "estat_private_households_total_a",
        "Abitazioni per famiglia privata",
        "abitazioni per famiglia privata",
        fattore_denominatore=1000,
    )
    return grafico_barre_paesi(
        dati,
        "Abitazioni per famiglia privata",
        "abitazioni per famiglia privata",
        "eurostat_abitazioni_per_famiglia_2021.png",
        cartella_output,
        paese_focus=paese_focus,
    )


def prepara_quota_periodi_stock(frame, indicatori, nome):
    stock_totale = valori_indicatore_per_paese(frame, "estat_dwellings_total_2021", anno_preferito="2021")
    stock_eta = frame.loc[frame["indicator_id"].isin(indicatori)].copy()
    stock_eta = stock_eta.loc[stock_eta["time_period"].astype(str) == "2021"]
    if stock_totale.empty or stock_eta.empty:
        return pd.DataFrame()

    somma_eta = (
        stock_eta.groupby(["country_code", "country_name"], as_index=False)
        .agg({"value": "sum", "source": "first", "source_dataset": "first"})
        .rename(columns={"value": "value_eta"})
    )
    totale = stock_totale[["country_code", "time_period", "value"]].rename(columns={"value": "value_totale"})
    dati = somma_eta.merge(totale, on="country_code", how="inner")
    dati = dati.loc[(dati["value_totale"].notna()) & (dati["value_totale"] != 0)].copy()
    if dati.empty:
        return dati

    dati["value"] = dati["value_eta"] / dati["value_totale"] * 100
    dati["time_period"] = "2021"
    dati["indicator_id"] = nome
    dati["indicator_name"] = nome
    dati["theme"] = "eta_stock"
    dati["unit"] = "% dello stock abitativo"
    dati["frequency"] = "A"
    colonne = [
        "source",
        "source_dataset",
        "indicator_id",
        "indicator_name",
        "theme",
        "country_code",
        "country_name",
        "time_period",
        "value",
        "unit",
        "frequency",
    ]
    return dati[colonne]


def grafico_stock_pre_1981_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_quota_periodi_stock(
        frame,
        INDICATORI_STOCK_PRE_1981,
        "Quota di abitazioni costruite prima del 1981",
    )
    return grafico_barre_paesi(
        dati,
        "Abitazioni costruite prima del 1981",
        "% dello stock abitativo",
        "eurostat_abitazioni_costruite_prima_1981_2021.png",
        cartella_output,
        percentuale=True,
        paese_focus=paese_focus,
    )


def grafico_stock_dal_2001_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_quota_periodi_stock(
        frame,
        INDICATORI_STOCK_DAL_2001,
        "Quota di abitazioni costruite dal 2001",
    )
    return grafico_barre_paesi(
        dati,
        "Abitazioni costruite dal 2001",
        "% dello stock abitativo",
        "eurostat_abitazioni_costruite_dal_2001_2021.png",
        cartella_output,
        percentuale=True,
        paese_focus=paese_focus,
    )


def base_per_indice(gruppo, anno_base):
    preferito = gruppo.loc[gruppo["time_period"].astype(str) == str(anno_base), "value"]
    if not preferito.empty and preferito.iloc[0] != 0:
        return preferito.iloc[0]

    ordinato = gruppo.sort_values("time_period")
    primo_valore = ordinato["value"].dropna()
    if primo_valore.empty or primo_valore.iloc[0] == 0:
        return None
    return primo_valore.iloc[0]


def prepara_indice_paesi(frame, indicatore, nome, anno_base="2015"):
    dati = frame.loc[frame["indicator_id"] == indicatore].copy()
    if dati.empty:
        return dati

    frames = []
    for paese, gruppo in dati.groupby("country_code"):
        gruppo = gruppo.sort_values("time_period").copy()
        base = base_per_indice(gruppo, anno_base)
        if base is None:
            continue

        gruppo["value"] = gruppo["value"] / base * 100
        frames.append(gruppo)

    if not frames:
        return pd.DataFrame()

    risultato = pd.concat(frames, ignore_index=True)
    risultato["indicator_id"] = nome
    risultato["indicator_name"] = nome
    risultato["unit"] = f"indice {anno_base}=100"
    return risultato


def grafico_popolazione_indice_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_indice_paesi(
        frame,
        "estat_population_total_a",
        "Popolazione totale (indice 2015=100)",
        anno_base="2015",
    )
    return grafico_ue_banda(
        dati,
        "Popolazione totale (indice 2015=100)",
        "confronto_popolazione_totale_indice.png",
        cartella_output,
        paese_focus=paese_focus,
    )


def prepara_famiglie_per_1000_abitanti(frame):
    famiglie = frame.loc[frame["indicator_id"] == "estat_private_households_total_a"].copy()
    popolazione = frame.loc[frame["indicator_id"] == "estat_population_total_a"].copy()
    if famiglie.empty or popolazione.empty:
        return pd.DataFrame()

    sinistra = famiglie[
        ["country_code", "country_name", "time_period", "value", "source", "source_dataset"]
    ].rename(
        columns={
            "value": "famiglie_migliaia",
            "source": "source_famiglie",
            "source_dataset": "dataset_famiglie",
        }
    )
    destra = popolazione[["country_code", "time_period", "value", "source", "source_dataset"]].rename(
        columns={
            "value": "popolazione",
            "source": "source_popolazione",
            "source_dataset": "dataset_popolazione",
        }
    )
    dati = sinistra.merge(destra, on=["country_code", "time_period"], how="inner")
    dati = dati.loc[(dati["popolazione"].notna()) & (dati["popolazione"] != 0)].copy()
    if dati.empty:
        return dati

    dati["value"] = dati["famiglie_migliaia"] * 1_000_000 / dati["popolazione"]
    dati["source"] = dati[["source_famiglie", "source_popolazione"]].agg(
        lambda valori: ", ".join(sorted(set(valori.dropna()))),
        axis=1,
    )
    dati["source_dataset"] = dati[["dataset_famiglie", "dataset_popolazione"]].agg(
        lambda valori: ", ".join(sorted(set(valori.dropna()))),
        axis=1,
    )
    dati["indicator_id"] = "estat_private_households_per_1000_inhabitants_a"
    dati["indicator_name"] = "Famiglie private per 1.000 abitanti"
    dati["theme"] = "demografia"
    dati["unit"] = "famiglie per 1.000 abitanti"
    dati["frequency"] = "A"
    colonne = [
        "source",
        "source_dataset",
        "indicator_id",
        "indicator_name",
        "theme",
        "country_code",
        "country_name",
        "time_period",
        "value",
        "unit",
        "frequency",
    ]
    return dati[colonne]


def grafico_famiglie_per_1000_abitanti_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_famiglie_per_1000_abitanti(frame)
    return grafico_ue_banda(
        dati,
        "estat_private_households_per_1000_inhabitants_a",
        "confronto_famiglie_private_per_1000_abitanti.png",
        cartella_output,
        paese_focus=paese_focus,
    )


def prepara_permessi_per_1000_abitanti(frame):
    permessi = frame.loc[frame["indicator_id"] == "estat_residential_permits_dwellings_ths_a"].copy()
    popolazione = frame.loc[frame["indicator_id"] == "estat_population_total_a"].copy()
    if permessi.empty or popolazione.empty:
        return pd.DataFrame()

    sinistra = permessi[
        ["country_code", "country_name", "time_period", "value", "source", "source_dataset"]
    ].rename(
        columns={
            "value": "permessi_migliaia",
            "source": "source_permessi",
            "source_dataset": "dataset_permessi",
        }
    )
    destra = popolazione[["country_code", "time_period", "value", "source", "source_dataset"]].rename(
        columns={
            "value": "popolazione",
            "source": "source_popolazione",
            "source_dataset": "dataset_popolazione",
        }
    )
    dati = sinistra.merge(destra, on=["country_code", "time_period"], how="inner")
    dati = dati.loc[(dati["popolazione"].notna()) & (dati["popolazione"] != 0)].copy()
    if dati.empty:
        return dati

    dati["value"] = dati["permessi_migliaia"] * 1_000_000 / dati["popolazione"]
    dati["source"] = dati[["source_permessi", "source_popolazione"]].agg(
        lambda valori: ", ".join(sorted(set(valori.dropna()))),
        axis=1,
    )
    dati["source_dataset"] = dati[["dataset_permessi", "dataset_popolazione"]].agg(
        lambda valori: ", ".join(sorted(set(valori.dropna()))),
        axis=1,
    )
    dati["indicator_id"] = "Permessi nuove abitazioni per 1.000 abitanti"
    dati["indicator_name"] = "Permessi nuove abitazioni per 1.000 abitanti"
    dati["theme"] = "offerta"
    dati["unit"] = "abitazioni per 1.000 abitanti"
    dati["frequency"] = "A"
    colonne = [
        "source",
        "source_dataset",
        "indicator_id",
        "indicator_name",
        "theme",
        "country_code",
        "country_name",
        "time_period",
        "value",
        "unit",
        "frequency",
    ]
    return dati[colonne]


def grafico_permessi_per_1000_abitanti_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_permessi_per_1000_abitanti(frame)
    return grafico_ue_banda(
        dati,
        "Permessi nuove abitazioni per 1.000 abitanti",
        "confronto_permessi_nuove_abitazioni_per_1000_abitanti.png",
        cartella_output,
        paese_focus=paese_focus,
    )


def prepara_quote_eta_stock(frame):
    dati = frame.loc[frame["indicator_id"].isin(INDICATORI_ETA_STOCK_ABITAZIONI)].copy()
    dati = dati.loc[(dati["time_period"].astype(str) == "2021") & ~dati["country_code"].isin(CODICI_AGGREGATI)]
    dati = dati.loc[dati["value"] > 0].copy()
    if dati.empty:
        return dati

    etichette = {indicatore: etichetta for indicatore, etichetta in ETA_STOCK_ABITAZIONI}
    ordine = {indicatore: posizione for posizione, indicatore in enumerate(INDICATORI_ETA_STOCK_ABITAZIONI)}
    dati["etichetta"] = dati["indicator_id"].map(etichette)
    dati["ordine"] = dati["indicator_id"].map(ordine)
    totali = dati.groupby("country_code")["value"].transform("sum")
    dati["quota"] = dati["value"] / totali * 100
    return dati.dropna(subset=["quota"])


def grafico_stock_eta_quote_paesi(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    dati = prepara_quote_eta_stock(frame)
    if dati.empty:
        return None

    profilo = profilo_paese(paese_focus)
    quote = dati.pivot_table(
        index="country_code",
        columns="etichetta",
        values="quota",
        aggfunc="sum",
        fill_value=0,
    )
    ordine_colonne = [etichetta for indicatore, etichetta in ETA_STOCK_ABITAZIONI if etichetta in quote.columns]
    quote = quote[ordine_colonne]
    colonne_stock_vecchio = [
        colonna
        for colonna in quote.columns
        if colonna in {"Prima del 1919", "1919-1945", "1946-1960", "1961-1980"}
    ]
    quote["ordinamento"] = quote[colonne_stock_vecchio].sum(axis=1)
    quote = quote.sort_values("ordinamento", ascending=False).drop(columns=["ordinamento"])

    altezza = max(7, 0.32 * len(quote) + 2.2)
    figura, asse = plt.subplots(figsize=(12, altezza))
    sinistra = pd.Series(0, index=quote.index, dtype=float)
    for colonna in quote.columns:
        asse.barh(
            quote.index,
            quote[colonna],
            left=sinistra,
            label=colonna,
            color=COLORI_ETA_STOCK.get(colonna, COLORE_BANDA),
        )
        sinistra = sinistra + quote[colonna]

    asse.invert_yaxis()
    asse.set_title("Stock abitativo per periodo di costruzione nei paesi UE, 2021", fontsize=14, fontweight="bold", loc="left")
    asse.set_xlabel("% dello stock abitativo")
    asse.set_xlim(0, 100)
    asse.grid(axis="x", alpha=0.2)
    formatta_asse_x(asse, percentuale=True)
    for etichetta in asse.get_yticklabels():
        if etichetta.get_text() == profilo["iso3"]:
            etichetta.set_color(profilo["colore"])
            etichetta.set_fontweight("bold")
        elif etichetta.get_text() == "ITA":
            etichetta.set_color(COLORE_ITALIA)
            etichetta.set_fontweight("bold")

    asse.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.08), frameon=False)
    aggiungi_footer(figura, dati)

    percorso = cartella_paese(cartella_output, profilo, "confronti") / "eurostat_stock_periodo_costruzione_quote_2021.png"
    salva_figura(figura, percorso)
    return percorso


def grafici_italia(frame, cartella_output="outputs/charts", mostra_progresso=False):
    percorsi = []
    totale = len(GRAFICI_ITALIA_LINEA)
    for posizione, (indicatore, nome_file) in enumerate(GRAFICI_ITALIA_LINEA, start=1):
        if mostra_progresso:
            print(f"[Focus Italia {posizione}/{totale}] Creo {nome_file}", flush=True)

        percorso = grafico_linea_indicatore(frame, indicatore, nome_file, cartella_output)
        if percorso:
            percorsi.append(percorso)

    if mostra_progresso:
        print("[Focus Italia] Creo italia_stock_abitazioni_periodo_costruzione.png", flush=True)

    stock = grafico_stock_abitazioni_italia(frame, cartella_output)
    if stock:
        percorsi.append(stock)

    if mostra_progresso:
        print("[Focus Italia] Creo italia_stock_abitazioni_periodo_costruzione_completo.png", flush=True)

    stock_completo = grafico_stock_abitazioni_italia_completo(frame, cartella_output)
    if stock_completo:
        percorsi.append(stock_completo)
    return percorsi


def grafico_ue_banda(frame, indicatore, nome_file, cartella_output="outputs/charts", paese_focus="ITA"):
    serie = frame.loc[frame["indicator_id"] == indicatore].copy()
    if serie.empty:
        return None

    profilo = profilo_paese(paese_focus)
    serie = prepara_serie_temporale(serie)
    paesi = serie.loc[~serie["country_code"].isin(CODICI_AGGREGATI)]
    focus = serie.loc[serie["country_code"] == profilo["iso3"]]
    italia = serie.loc[serie["country_code"] == "ITA"]
    eu27 = serie.loc[serie["country_code"] == "EU27_2020"]
    if paesi.empty or focus.empty:
        return None

    periodo = periodo_comune(focus, eu27)
    if periodo is not None:
        inizio, fine = periodo
        paesi = limita_periodo(paesi, inizio, fine)
        focus = limita_periodo(focus, inizio, fine)
        italia = limita_periodo(italia, inizio, fine)
        eu27 = limita_periodo(eu27, inizio, fine)

    banda = paesi.groupby("data_plot")["value"].agg(["min", "max"]).reset_index()
    banda["data_num"] = mdates.date2num(banda["data_plot"].to_numpy(dtype="datetime64[ms]"))
    risultato_summary = salva_min_max_summary(
        pd.concat([paesi, eu27], ignore_index=True),
        cartella_output,
        profilo["slug"],
        "confronti",
        nome_file,
        paesi_esclusi=CODICI_AGGREGATI,
        min_paesi=8,
        paese_focus=profilo["iso3"],
        colonna_focus=f"{profilo['slug']}_value",
    )
    summary_min_max = risultato_summary[1]

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
    if profilo["iso3"] != "ITA" and not italia.empty:
        asse.plot(italia["data_plot"], italia["value"], color=COLORE_ITALIA, linewidth=2.1, label="Italia")
    asse.plot(focus["data_plot"], focus["value"], color=profilo["colore"], linewidth=2.4, label=profilo["label"])
    asse.set_title(serie["indicator_name"].iloc[0], fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel(serie["unit"].iloc[0])
    asse.grid(alpha=0.2)
    formatta_asse_y(asse)
    asse.legend(loc="best", frameon=False)
    serie_asse = unisci_serie_per_asse([focus, italia, eu27])
    formatta_asse_date(asse, serie_asse)
    aggiungi_nota_min_max(asse, testo_min_max_ultimo_periodo(summary_min_max))
    aggiungi_footer(figura, serie)

    percorso = cartella_paese(cartella_output, profilo, "confronti") / nome_file
    salva_figura(figura, percorso)
    return percorso


def grafici_confronto_eurostat(frame, cartella_output="outputs/charts", mostra_progresso=False, paese_focus="ITA"):
    profilo = profilo_paese(paese_focus)
    percorsi = []
    totale = len(GRAFICI_CONFRONTO_EUROSTAT)
    for posizione, (indicatore, nome_file) in enumerate(GRAFICI_CONFRONTO_EUROSTAT, start=1):
        if mostra_progresso:
            print(f"[Confronti Eurostat {profilo['nome']} {posizione}/{totale}] Creo {nome_file}", flush=True)

        percorso = grafico_ue_banda(frame, indicatore, nome_file, cartella_output, paese_focus=paese_focus)
        if percorso:
            percorsi.append(percorso)
    return percorsi


def grafico_ue_affordability(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    ultimi = latest_by_country(frame, "estat_housing_overburden_total_pc_a")
    ultimi = ultimi.loc[~ultimi["country_code"].isin(CODICI_AGGREGATI)]
    if ultimi.empty:
        return None

    profilo = profilo_paese(paese_focus)
    ultimi = ultimi.sort_values("value", ascending=False)
    figura, asse = plt.subplots(figsize=(12, 6))
    colori = [colore_paese_confronto(codice, profilo) for codice in ultimi["country_code"]]
    asse.bar(etichette_paesi_snapshot(ultimi), ultimi["value"], color=colori)
    asse.set_title(titolo_snapshot("UE - tasso di sovraccarico dei costi abitativi", ultimi), fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel("percentuale popolazione")
    asse.grid(axis="y", alpha=0.22)
    formatta_asse_y(asse)
    aggiungi_footer(figura, ultimi)

    percorso = cartella_paese(cartella_output, profilo, "confronti") / "eurostat_housing_overburden_latest.png"
    salva_figura(figura, percorso)
    return percorso


def grafico_ue_shortage_proxy(frame, cartella_output="outputs/charts", paese_focus="ITA"):
    ultimi = latest_by_country(frame, "estat_young_living_with_parents_25_34_a")
    ultimi = ultimi.loc[~ultimi["country_code"].isin(CODICI_AGGREGATI)]
    if ultimi.empty:
        return None

    profilo = profilo_paese(paese_focus)
    ultimi = ultimi.sort_values("value", ascending=False)
    figura, asse = plt.subplots(figsize=(12, 6))
    colori = [colore_paese_confronto(codice, profilo) for codice in ultimi["country_code"]]
    asse.bar(etichette_paesi_snapshot(ultimi), ultimi["value"], color=colori)
    asse.set_title(titolo_snapshot("UE - 25-34enni che vivono con i genitori", ultimi), fontsize=14, fontweight="bold", loc="left")
    asse.set_ylabel("percentuale popolazione 25-34")
    asse.grid(axis="y", alpha=0.22)
    formatta_asse_y(asse)
    aggiungi_footer(figura, ultimi)

    percorso = cartella_paese(cartella_output, profilo, "confronti") / "eurostat_giovani_con_genitori_latest.png"
    salva_figura(figura, percorso)
    return percorso


def crea_grafici(frame, cartella_output="outputs/charts", mostra_progresso=False, paesi_confronto=None):
    paesi_focus = normalizza_codici_paesi(paesi_confronto)
    percorsi = []
    for paese_focus in paesi_focus:
        profilo = profilo_paese(paese_focus)
        if mostra_progresso:
            print(f"Inizio generazione confronti Eurostat per {profilo['nome']}.", flush=True)
        percorsi.extend(
            grafici_confronto_eurostat(
                frame,
                cartella_output,
                mostra_progresso=mostra_progresso,
                paese_focus=paese_focus,
            )
        )

    if mostra_progresso:
        print("Inizio generazione focus Italia Eurostat.", flush=True)
    percorsi.extend(grafici_italia(frame, cartella_output, mostra_progresso=mostra_progresso))

    grafici_finali = [
        ("confronto_popolazione_totale_indice.png", grafico_popolazione_indice_paesi),
        ("confronto_famiglie_private_per_1000_abitanti.png", grafico_famiglie_per_1000_abitanti_paesi),
        ("confronto_permessi_nuove_abitazioni_per_1000_abitanti.png", grafico_permessi_per_1000_abitanti_paesi),
        ("eurostat_housing_overburden_latest.png", grafico_ue_affordability),
        ("eurostat_giovani_con_genitori_latest.png", grafico_ue_shortage_proxy),
        ("eurostat_stock_abitazioni_totali_2021.png", grafico_stock_totale_paesi),
        ("eurostat_abitazioni_non_occupate_stock_2021.png", grafico_stock_non_occupato_paesi),
        ("eurostat_abitazioni_per_1000_abitanti_2021.png", grafico_abitazioni_per_1000_abitanti_paesi),
        ("eurostat_abitazioni_per_famiglia_2021.png", grafico_abitazioni_per_famiglia_paesi),
        ("eurostat_abitazioni_costruite_prima_1981_2021.png", grafico_stock_pre_1981_paesi),
        ("eurostat_abitazioni_costruite_dal_2001_2021.png", grafico_stock_dal_2001_paesi),
        ("eurostat_stock_periodo_costruzione_quote_2021.png", grafico_stock_eta_quote_paesi),
    ]
    for paese_focus in paesi_focus:
        profilo = profilo_paese(paese_focus)
        for nome_file, funzione in grafici_finali:
            if mostra_progresso:
                print(f"[Grafici confronto {profilo['nome']}] Creo {nome_file}", flush=True)

            percorso = funzione(frame, cartella_output, paese_focus=paese_focus)
            if percorso:
                percorsi.append(percorso)

    if mostra_progresso:
        print(f"Generazione grafici completata: {len(percorsi)} file creati.", flush=True)
    return percorsi
