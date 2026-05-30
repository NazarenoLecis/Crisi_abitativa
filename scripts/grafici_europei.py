from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import EU27_CODES
from grafici_oecd import scarica_prezzi_case_oecd
from grafici import (
    COLORE_BANDA,
    COLORE_EU27,
    COLORE_ITALIA,
    COLORE_PRINCIPALE,
    formatta_asse_date,
    formatta_asse_y,
    periodo_comune,
    periodo_to_datetime,
)
from utils import EUROSTAT_BASE_URL, WATERMARK, codice_paese_iso3, jsonstat_to_dataframe, scarica_bytes, scarica_json


AMECO_CAPITOLO_URL = "https://ec.europa.eu/economy_finance/db_indicators/ameco/documents/ameco{capitolo}.zip"
COLORE_GRIGLIA = "#D0D0D0"
COLORE_TESTO = "#111111"
COLORE_ACCENTO = "#457B9D"
COLORE_VERDE = "#2A9D8F"
COLORE_ARANCIO = "#E76F51"
PAESI_EUROPEI = EU27_CODES + ["EU27_2020"]


def cartella_grafici_europei(cartella_output):
    cartella = Path(cartella_output) / "eurostat" / "confronti"
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def scarica_eurostat_dettagliato(dataset_code, filtri, paesi):
    parametri = dict(filtri)
    if paesi is not None:
        parametri["geo"] = paesi

    payload = scarica_json(f"{EUROSTAT_BASE_URL}/{dataset_code}", parametri)
    frame = jsonstat_to_dataframe(payload)
    if frame.empty:
        return frame

    frame = frame.rename(columns={"geo": "country_code_raw", "time": "time_period"})
    frame["country_code"] = frame["country_code_raw"].map(codice_paese_iso3)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame["source_dataset"] = dataset_code
    return frame.dropna(subset=["value"])


def scarica_ameco_capitolo(capitolo):
    contenuto_zip = scarica_bytes(AMECO_CAPITOLO_URL.format(capitolo=capitolo))
    with ZipFile(BytesIO(contenuto_zip)) as archivio:
        nome_file = archivio.namelist()[0]
        separatore = ";" if nome_file.lower().endswith(".txt") else ","
        frame = pd.read_csv(BytesIO(archivio.read(nome_file)), sep=separatore, dtype=str, encoding="latin1")

    codici = frame["CODE"].astype(str).str.split(".")
    frame["area_code"] = codici.str[0].str.strip()
    frame["indicator_code"] = codici.str[-1].str.strip()
    return frame


def serie_ameco(frame, codice_indicatore, area_code):
    riga = frame.loc[(frame["indicator_code"] == codice_indicatore) & (frame["area_code"] == area_code)].copy()
    if riga.empty:
        return pd.Series(dtype=float)

    anni = [colonna for colonna in frame.columns if colonna.isdigit()]
    return pd.to_numeric(riga.iloc[0][anni], errors="coerce")


def reddito_disponibile_ameco():
    popolazione = scarica_ameco_capitolo(1)
    famiglie = scarica_ameco_capitolo(15)
    righe = []
    paesi = {"ITA": "ITA", "EU27": "EU27_2020"}

    for area_code, country_code in paesi.items():
        reddito = serie_ameco(famiglie, "UVGH", area_code)
        popolazione_totale = serie_ameco(popolazione, "NPTD", area_code)
        valore_pro_capite = (reddito / popolazione_totale).dropna()
        for anno, valore in valore_pro_capite.items():
            # Nei country fact sheet la serie EU27 del reddito parte dal 2005.
            if country_code == "EU27_2020" and int(anno) < 2005:
                continue
            righe.append(
                {
                    "country_code": country_code,
                    "time_period": str(anno),
                    "value": float(valore),
                    "source_dataset": "AMECO",
                    "metrica": "Reddito",
                }
            )

    return pd.DataFrame(righe)


def prezzi_case_estesi():
    prezzi_italia = scarica_prezzi_case_oecd(paesi=["ITA"], misure=["HPI"], inizio="2000", fine="2024")
    prezzi_italia = prezzi_italia.loc[prezzi_italia["measure_code"] == "HPI"].copy()
    prezzi_italia = prezzi_italia[["country_code", "time_period", "value"]]
    prezzi_italia["source_dataset"] = "OECD DF_HOUSE_PRICES"
    prezzi_italia["metrica"] = "Prezzi case"

    prezzi_eu27 = scarica_eurostat_dettagliato(
        "prc_hpi_a",
        {"freq": "A", "purchase": "TOTAL", "unit": "I15_A_AVG"},
        ["EU27_2020"],
    )
    prezzi_eu27 = prezzi_eu27[["country_code", "time_period", "value", "source_dataset"]]
    prezzi_eu27["metrica"] = "Prezzi case"

    return pd.concat([prezzi_italia, prezzi_eu27], ignore_index=True)


def applica_stile_grafici_europei(asse, percentuale=False):
    asse.grid(axis="y", color=COLORE_GRIGLIA, linewidth=0.8, alpha=0.55)
    asse.grid(axis="x", color=COLORE_GRIGLIA, linewidth=0.6, alpha=0.18)
    asse.spines["top"].set_visible(False)
    asse.spines["right"].set_visible(False)
    asse.tick_params(axis="both", labelsize=10, colors=COLORE_TESTO)
    formatta_asse_y(asse, percentuale=percentuale)


def aggiungi_titolo(asse, titolo):
    asse.set_title(titolo, loc="left", fontsize=16, fontweight="bold", color=COLORE_TESTO, pad=12)


def aggiungi_footer_grafici_europei(figura, fonte):
    figura.text(
        0.01,
        0.015,
        f"Fonte: {fonte} | {WATERMARK}",
        ha="left",
        va="bottom",
        fontsize=9,
        color="#333333",
    )


def salva_grafico_europeo(figura, percorso):
    plt.tight_layout(rect=[0, 0.2, 1, 0.96])
    figura.savefig(percorso, dpi=170)
    plt.close(figura)


def filtra_periodo(frame, inizio=None, fine=None):
    risultato = frame.copy()
    risultato["data_plot"] = risultato["time_period"].map(periodo_to_datetime)
    risultato = risultato.dropna(subset=["data_plot"]).sort_values("data_plot")

    if inizio is not None:
        data_inizio = periodo_to_datetime(inizio)
        risultato = risultato.loc[risultato["data_plot"] >= data_inizio]
    if fine is not None:
        data_fine = periodo_to_datetime(fine)
        risultato = risultato.loc[risultato["data_plot"] <= data_fine]

    return risultato


def formatta_anni_brevi(asse, serie):
    serie_date = serie.dropna(subset=["data_plot"]).drop_duplicates("data_plot").sort_values("data_plot")
    if serie_date.empty:
        return

    ticks = serie_date["data_plot"]
    labels = []
    for periodo in serie_date["time_period"].astype(str):
        if "-Q" in periodo:
            anno, trimestre = periodo.split("-Q")
            labels.append(f"{anno[-2:]}-Q{trimestre}")
        else:
            labels.append(periodo[-2:])

    asse.set_xticks(ticks)
    asse.set_xticklabels(labels)
    asse.tick_params(axis="x", labelrotation=0)
    inizio = serie_date["data_plot"].min()
    fine = serie_date["data_plot"].max()
    margine = max((fine - inizio) * 0.02, pd.Timedelta(days=25))
    asse.set_xlim(inizio - margine, fine + margine)


def formatta_trimestri(asse, serie):
    serie_date = serie.dropna(subset=["data_plot"]).drop_duplicates("data_plot").sort_values("data_plot")
    if serie_date.empty:
        return

    formatta_asse_date(asse, serie_date, massimo_etichette=12)
    asse.tick_params(axis="x", labelrotation=45)


def rebase_serie(frame, colonne_gruppo, anno_base="2019"):
    frames = []
    for valori_gruppo, gruppo in frame.groupby(colonne_gruppo, dropna=False):
        ordinato = gruppo.copy()
        ordinato["time_period"] = ordinato["time_period"].astype(str)
        ordinato = ordinato.sort_values("time_period")
        base = ordinato.loc[ordinato["time_period"] == str(anno_base), "value"]
        if base.empty or base.iloc[0] == 0:
            continue

        ordinato["value"] = ordinato["value"] / base.iloc[0] * 100
        frames.append(ordinato)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def ultima_serie(frame, paese, colonna_valore=None, valore_dimensione=None, anno_preferito=None):
    dati = frame.loc[frame["country_code"] == paese].copy()
    if colonna_valore is not None:
        dati = dati.loc[dati[colonna_valore] == valore_dimensione]
    if dati.empty:
        return None

    if anno_preferito is not None:
        preferito = dati.loc[dati["time_period"] == str(anno_preferito)]
        if not preferito.empty:
            return float(preferito.sort_values("time_period").iloc[-1]["value"])

    return float(dati.sort_values("time_period").iloc[-1]["value"])


def annota_ultimo_valore(asse, serie, suffisso="", decimali=1):
    if serie.empty:
        return

    ultimo = serie.sort_values("data_plot").iloc[-1]
    valore = ultimo["value"]
    testo = f"{valore:.{decimali}f}{suffisso}"
    asse.annotate(
        testo,
        xy=(ultimo["data_plot"], valore),
        xytext=(6, 0),
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#404040",
    )


def prepara_banda(frame, inizio=None, fine=None):
    serie = filtra_periodo(frame, inizio=inizio, fine=fine)
    paesi = serie.loc[~serie["country_code"].isin({"EU27_2020", "EU", "EA20", "EA19"})].copy()
    italia = serie.loc[serie["country_code"] == "ITA"].copy()
    eu27 = serie.loc[serie["country_code"] == "EU27_2020"].copy()
    if italia.empty or eu27.empty:
        return pd.DataFrame(), italia, eu27

    periodo = periodo_comune(italia, eu27)
    if periodo is None:
        return pd.DataFrame(), italia, eu27

    data_inizio, data_fine = periodo
    paesi = paesi.loc[(paesi["data_plot"] >= data_inizio) & (paesi["data_plot"] <= data_fine)]
    italia = italia.loc[(italia["data_plot"] >= data_inizio) & (italia["data_plot"] <= data_fine)]
    eu27 = eu27.loc[(eu27["data_plot"] >= data_inizio) & (eu27["data_plot"] <= data_fine)]
    banda = paesi.groupby("data_plot")["value"].agg(["min", "max", "count"]).reset_index()
    banda = banda.loc[banda["count"] >= 8].copy()
    banda["data_num"] = mdates.date2num(banda["data_plot"].to_numpy(dtype="datetime64[ms]"))
    return banda, italia, eu27


def disegna_banda_linee(asse, banda, italia, eu27, percentuale=False):
    if not banda.empty:
        asse.fill_between(
            banda["data_num"],
            banda["min"],
            banda["max"],
            color=COLORE_BANDA,
            alpha=1,
            linewidth=0,
        )

    if not eu27.empty:
        asse.plot(eu27["data_plot"], eu27["value"], color=COLORE_EU27, linewidth=2.1, label="EU27")
    if not italia.empty:
        asse.plot(italia["data_plot"], italia["value"], color=COLORE_ITALIA, linewidth=2.4, label="Italia")

    applica_stile_grafici_europei(asse, percentuale=percentuale)


def aggiungi_legenda_figura(figura, asse, colonne=2):
    handles, labels = asse.get_legend_handles_labels()
    if not handles:
        return

    figura.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.07),
        ncol=colonne,
        frameon=False,
        fontsize=11,
    )


def grafico_prezzi_affitti_redditi_inflazione(cartella_output):
    paesi = ["IT", "EU27_2020"]
    prezzi_case = prezzi_case_estesi()

    hicp = scarica_eurostat_dettagliato(
        "prc_hicp_aind",
        {"freq": "A", "unit": "INX_A_AVG", "coicop": ["CP00", "CP041"]},
        paesi,
    )
    hicp["metrica"] = hicp["coicop"].map({"CP041": "Affitti", "CP00": "Inflazione"})

    reddito = reddito_disponibile_ameco()

    dati = pd.concat([prezzi_case, hicp, reddito], ignore_index=True)
    dati = dati.loc[dati["time_period"].astype(str).str.isdigit()].copy()
    dati = rebase_serie(dati, ["country_code", "metrica"], anno_base="2019")
    dati = filtra_periodo(dati, inizio="2000", fine="2024")
    if dati.empty:
        return None

    colori = {
        "Prezzi case": COLORE_PRINCIPALE,
        "Affitti": COLORE_VERDE,
        "Reddito": COLORE_ACCENTO,
        "Inflazione": COLORE_ARANCIO,
    }

    figura, asse = plt.subplots(figsize=(9.8, 6.0))
    for metrica in ["Prezzi case", "Affitti", "Reddito", "Inflazione"]:
        for paese in ["ITA", "EU27_2020"]:
            serie = dati.loc[(dati["metrica"] == metrica) & (dati["country_code"] == paese)].sort_values("data_plot")
            if serie.empty:
                continue
            stile = "-" if paese == "ITA" else (0, (4, 4))
            label_paese = "Italia" if paese == "ITA" else "EU27"
            asse.plot(
                serie["data_plot"],
                serie["value"],
                color=colori[metrica],
                linestyle=stile,
                linewidth=1.7,
                label=f"{metrica} {label_paese}",
            )

    aggiungi_titolo(asse, "Prezzi delle case, affitti, redditi e inflazione (2019=100)")
    asse.set_ylabel("indice 2019=100")
    applica_stile_grafici_europei(asse)
    formatta_anni_brevi(asse, dati)
    asse.set_ylim(max(0, dati["value"].min() * 0.94), dati["value"].max() * 1.06)
    aggiungi_legenda_figura(figura, asse, colonne=4)
    aggiungi_footer_grafici_europei(
        figura,
        "Eurostat (prc_hpi_a, prc_hicp_aind), OECD (DF_HOUSE_PRICES), DG ECFIN AMECO (UVGH, NPTD)",
    )

    percorso = cartella_grafici_europei(cartella_output) / "italia_ue_prezzi_affitti_redditi_inflazione.png"
    salva_grafico_europeo(figura, percorso)
    return percorso


def grafico_banda_europeo(dataset_code, filtri, titolo, nome_file, cartella_output, inizio=None, fine=None, percentuale=False):
    dati = scarica_eurostat_dettagliato(dataset_code, filtri, PAESI_EUROPEI)
    if dati.empty:
        return None

    banda, italia, eu27 = prepara_banda(dati, inizio=inizio, fine=fine)
    if italia.empty or eu27.empty:
        return None

    figura, asse = plt.subplots(figsize=(9.2, 5.5))
    disegna_banda_linee(asse, banda, italia, eu27, percentuale=percentuale)
    aggiungi_titolo(asse, titolo)
    serie_asse = pd.concat([italia, eu27], ignore_index=True)
    if "-Q" in "".join(serie_asse["time_period"].astype(str).head(5).tolist()):
        formatta_trimestri(asse, serie_asse)
    else:
        formatta_anni_brevi(asse, serie_asse)
    annota_ultimo_valore(asse, italia, suffisso="%" if percentuale else "", decimali=1)
    annota_ultimo_valore(asse, eu27, suffisso="%" if percentuale else "", decimali=1)
    aggiungi_legenda_figura(figura, asse, colonne=2)
    aggiungi_footer_grafici_europei(figura, f"Eurostat ({dataset_code})")

    percorso = cartella_grafici_europei(cartella_output) / nome_file
    salva_grafico_europeo(figura, percorso)
    return percorso


def grafico_linee_europeo(dataset_code, filtri, titolo, nome_file, cartella_output, inizio=None, fine=None, percentuale=False):
    dati = scarica_eurostat_dettagliato(dataset_code, filtri, ["IT", "EU27_2020"])
    if dati.empty:
        return None

    serie = filtra_periodo(dati, inizio=inizio, fine=fine)
    italia = serie.loc[serie["country_code"] == "ITA"].copy()
    eu27 = serie.loc[serie["country_code"] == "EU27_2020"].copy()
    if italia.empty or eu27.empty:
        return None

    periodo = periodo_comune(italia, eu27)
    if periodo is not None:
        data_inizio, data_fine = periodo
        italia = italia.loc[(italia["data_plot"] >= data_inizio) & (italia["data_plot"] <= data_fine)]
        eu27 = eu27.loc[(eu27["data_plot"] >= data_inizio) & (eu27["data_plot"] <= data_fine)]

    figura, asse = plt.subplots(figsize=(9.2, 5.5))
    asse.plot(eu27["data_plot"], eu27["value"], color=COLORE_EU27, linewidth=2.1, label="EU27")
    asse.plot(italia["data_plot"], italia["value"], color=COLORE_ITALIA, linewidth=2.4, label="Italia")
    aggiungi_titolo(asse, titolo)
    applica_stile_grafici_europei(asse, percentuale=percentuale)
    serie_asse = pd.concat([italia, eu27], ignore_index=True)
    formatta_trimestri(asse, serie_asse)
    annota_ultimo_valore(asse, italia, suffisso="%" if percentuale else "", decimali=0)
    annota_ultimo_valore(asse, eu27, suffisso="%" if percentuale else "", decimali=0)
    aggiungi_legenda_figura(figura, asse, colonne=2)
    aggiungi_footer_grafici_europei(figura, f"Eurostat ({dataset_code})")

    percorso = cartella_grafici_europei(cartella_output) / nome_file
    salva_grafico_europeo(figura, percorso)
    return percorso


def grafico_tenure_status(cartella_output):
    dati = scarica_eurostat_dettagliato(
        "ilc_lvho02",
        {
            "freq": "A",
            "unit": "PC",
            "incgrp": "TOTAL",
            "hhcomp": "TOTAL",
            "tenure": ["OWN_L", "OWN_NL", "RENT_FR", "RENT_MKT"],
        },
        ["IT", "EU27_2020"],
    )
    if dati.empty:
        return None

    anno = "2024" if "2024" in set(dati["time_period"]) else dati["time_period"].max()
    dati = dati.loc[dati["time_period"] == anno].copy()
    ordine = ["OWN_L", "OWN_NL", "RENT_FR", "RENT_MKT"]
    etichette = ["IT", "EU27"]
    colori = ["#ED7D31", "#1F6B86", "#92D050", "#00B050"]
    legenda = [
        "Proprieta' con mutuo",
        "Proprieta' senza mutuo",
        "Affitto ridotto o gratuito",
        "Affitto a prezzo di mercato",
    ]

    figura, asse = plt.subplots(figsize=(9.2, 5.8))
    ascisse = np.arange(len(etichette))
    fondo = np.zeros(len(etichette))
    for posizione, tenure in enumerate(ordine):
        valori = []
        for paese in ["ITA", "EU27_2020"]:
            valore = ultima_serie(dati, paese, "tenure", tenure, anno_preferito=anno)
            valori.append(0 if valore is None else valore)

        barre = asse.bar(ascisse, valori, bottom=fondo, color=colori[posizione], width=0.42, label=legenda[posizione])
        for indice, barra in enumerate(barre):
            altezza = barra.get_height()
            if altezza >= 5:
                asse.text(
                    barra.get_x() + barra.get_width() / 2,
                    fondo[indice] + altezza / 2,
                    f"{altezza:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                )
        fondo = fondo + np.array(valori)

    aggiungi_titolo(asse, f"Popolazione per titolo di godimento dell'abitazione, {anno}")
    applica_stile_grafici_europei(asse, percentuale=True)
    asse.set_xticks(ascisse)
    asse.set_xticklabels(etichette)
    asse.set_ylim(0, 105)
    aggiungi_legenda_figura(figura, asse, colonne=2)
    aggiungi_footer_grafici_europei(figura, "Eurostat (ilc_lvho02)")

    percorso = cartella_grafici_europei(cartella_output) / "italia_ue_titolo_godimento_abitazione.png"
    salva_grafico_europeo(figura, percorso)
    return percorso


def grafico_homeownership_income(cartella_output):
    dati = scarica_eurostat_dettagliato(
        "ilc_lvho02",
        {
            "freq": "A",
            "unit": "PC",
            "hhcomp": "TOTAL",
            "tenure": "OWN",
            "incgrp": ["TOTAL", "B_MD60", "A_MD60"],
        },
        ["IT", "EU27_2020"],
    )
    if dati.empty:
        return None

    anno = "2024" if "2024" in set(dati["time_period"]) else dati["time_period"].max()
    dati = dati.loc[dati["time_period"] == anno].copy()
    ascisse = np.arange(2)
    paesi = ["ITA", "EU27_2020"]
    etichette = ["IT", "EU27"]
    totale = [ultima_serie(dati, paese, "incgrp", "TOTAL", anno_preferito=anno) for paese in paesi]
    sotto_soglia = [ultima_serie(dati, paese, "incgrp", "B_MD60", anno_preferito=anno) for paese in paesi]
    sopra_soglia = [ultima_serie(dati, paese, "incgrp", "A_MD60", anno_preferito=anno) for paese in paesi]

    figura, asse = plt.subplots(figsize=(9.2, 5.5))
    asse.bar(ascisse, totale, color="#D8E8F3", width=0.35, label="Totale")
    asse.scatter(ascisse, sotto_soglia, marker="o", s=95, color=COLORE_ARANCIO, label="A rischio poverta'")
    asse.scatter(ascisse, sopra_soglia, marker="D", s=85, color=COLORE_PRINCIPALE, label="Non a rischio poverta'")
    aggiungi_titolo(asse, f"Proprietari di casa per gruppo di reddito, {anno}")
    applica_stile_grafici_europei(asse, percentuale=True)
    asse.set_xticks(ascisse)
    asse.set_xticklabels(etichette)
    asse.set_ylim(0, 100)
    aggiungi_legenda_figura(figura, asse, colonne=3)
    aggiungi_footer_grafici_europei(figura, "Eurostat (ilc_lvho02)")

    percorso = cartella_grafici_europei(cartella_output) / "italia_ue_proprietari_casa_reddito.png"
    salva_grafico_europeo(figura, percorso)
    return percorso


def combina_overburden_inquilini():
    tassi = scarica_eurostat_dettagliato(
        "ilc_lvho07c",
        {"freq": "A", "unit": "PC", "tenure": ["RENT_MKT", "RENT_FR"]},
        PAESI_EUROPEI,
    )
    quote = scarica_eurostat_dettagliato(
        "ilc_lvho02",
        {
            "freq": "A",
            "unit": "PC",
            "incgrp": "TOTAL",
            "hhcomp": "TOTAL",
            "tenure": ["RENT_MKT", "RENT_FR"],
        },
        PAESI_EUROPEI,
    )
    if tassi.empty or quote.empty:
        return pd.DataFrame()

    colonne = ["country_code", "time_period", "tenure"]
    unito = tassi[colonne + ["value"]].merge(
        quote[colonne + ["value"]],
        on=colonne,
        suffixes=("_tasso", "_quota"),
    )
    unito["quota_ponderata"] = unito["value_tasso"] * unito["value_quota"]
    aggregato = (
        unito.groupby(["country_code", "time_period"], as_index=False)
        .agg(quota_ponderata=("quota_ponderata", "sum"), quota_totale=("value_quota", "sum"))
    )
    aggregato = aggregato.loc[aggregato["quota_totale"] > 0].copy()
    aggregato["value"] = aggregato["quota_ponderata"] / aggregato["quota_totale"]
    aggregato["source_dataset"] = "ilc_lvho07c, ilc_lvho02"
    return aggregato[["country_code", "time_period", "value", "source_dataset"]]


def grafico_overburden_inquilini(cartella_output):
    dati = combina_overburden_inquilini()
    if dati.empty:
        return None

    banda, italia, eu27 = prepara_banda(dati)
    if italia.empty or eu27.empty:
        return None

    figura, asse = plt.subplots(figsize=(9.2, 5.5))
    disegna_banda_linee(asse, banda, italia, eu27, percentuale=True)
    aggiungi_titolo(asse, "Sovraccarico dei costi abitativi per gli inquilini")
    serie_asse = pd.concat([italia, eu27], ignore_index=True)
    formatta_anni_brevi(asse, serie_asse)
    asse.set_ylim(0, max(80, banda["max"].max() * 1.05 if not banda.empty else 80))
    aggiungi_legenda_figura(figura, asse, colonne=2)
    aggiungi_footer_grafici_europei(figura, "Eurostat ad hoc extraction (based on ilc_lvho07c and ilc_lvho02)")

    percorso = cartella_grafici_europei(cartella_output) / "italia_ue_sovraccarico_costi_inquilini.png"
    salva_grafico_europeo(figura, percorso)
    return percorso


def aggiungi_etichette_barre(asse, barre):
    for barra in barre:
        altezza = barra.get_height()
        asse.text(
            barra.get_x() + barra.get_width() / 2,
            altezza + 0.6,
            f"{altezza:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )


def grafico_accesso_adeguato_arop(cartella_output):
    sovraffollamento = scarica_eurostat_dettagliato(
        "ilc_lvho05a",
        {"freq": "A", "unit": "PC", "incgrp": ["B_MD60", "A_MD60"], "age": "TOTAL", "sex": "T"},
        ["IT", "EU27_2020"],
    )
    riscaldamento = scarica_eurostat_dettagliato(
        "ilc_mdes01",
        {"freq": "A", "unit": "PC", "hhtyp": "TOTAL", "incgrp": ["B_MD60", "A_MD60"]},
        ["IT", "EU27_2020"],
    )
    deprivazione = scarica_eurostat_dettagliato(
        "ilc_mdho06a",
        {"freq": "A", "unit": "PC", "rskpovth": ["B_60", "A_60"], "age": "TOTAL", "sex": "T"},
        ["IT", "EU27_2020"],
    )
    if sovraffollamento.empty or riscaldamento.empty or deprivazione.empty:
        return None

    categorie = [
        ("Sovraffollamento", sovraffollamento, "incgrp", "B_MD60", "A_MD60", "2024"),
        ("Casa non riscaldata\nadeguatamente", riscaldamento, "incgrp", "B_MD60", "A_MD60", "2024"),
        ("Grave deprivazione\nabitativa", deprivazione, "rskpovth", "B_60", "A_60", "2023"),
    ]
    serie_legenda = [
        ("A rischio poverta' EU27", "EU27_2020", True, COLORE_EU27),
        ("A rischio poverta' Italia", "ITA", True, COLORE_ITALIA),
        ("Non a rischio poverta' EU27", "EU27_2020", False, COLORE_ACCENTO),
        ("Non a rischio poverta' Italia", "ITA", False, COLORE_VERDE),
    ]

    figura, asse = plt.subplots(figsize=(9.8, 5.5))
    ascisse = np.arange(len(categorie))
    larghezza = 0.18
    for posizione, (label, paese, usa_arop, colore) in enumerate(serie_legenda):
        valori = []
        for nome_categoria, frame, colonna, codice_arop, codice_non_arop, anno in categorie:
            codice = codice_arop if usa_arop else codice_non_arop
            valore = ultima_serie(frame, paese, colonna, codice, anno_preferito=anno)
            valori.append(0 if valore is None else valore)

        offset = (posizione - 1.5) * larghezza
        barre = asse.bar(ascisse + offset, valori, width=larghezza, color=colore, label=label)
        aggiungi_etichette_barre(asse, barre)

    aggiungi_titolo(
        asse,
        "Accesso a un'abitazione adeguata per rischio poverta', ultimo anno disponibile",
    )
    applica_stile_grafici_europei(asse, percentuale=True)
    asse.set_xticks(ascisse)
    asse.set_xticklabels([f"{categoria[0]}\n{categoria[5]}" for categoria in categorie])
    asse.set_ylim(0, 45)
    aggiungi_legenda_figura(figura, asse, colonne=2)
    aggiungi_footer_grafici_europei(figura, "Eurostat (ilc_lvho05a, ilc_mdes01, ilc_mdho06a)")

    percorso = cartella_grafici_europei(cartella_output) / "italia_ue_accesso_abitazione_adeguata_poverta.png"
    salva_grafico_europeo(figura, percorso)
    return percorso


def grafico_arop_prima_dopo_costi(cartella_output):
    arop = scarica_eurostat_dettagliato(
        "tespm010",
        {"freq": "A", "unit": "PC", "indic_il": "LI_R_MD60", "sex": "T", "age": "TOTAL"},
        ["IT", "EU27_2020"],
    )
    dopo_costi = scarica_eurostat_dettagliato(
        "ilc_li45",
        {"freq": "A", "sex": "T", "age": "TOTAL", "unit": "PC"},
        ["IT", "EU27_2020"],
    )
    if arop.empty or dopo_costi.empty:
        return None

    anno = "2024"
    paesi = ["ITA", "EU27_2020"]
    valori_arop = [ultima_serie(arop, paese, anno_preferito=anno) for paese in paesi]
    valori_dopo = [ultima_serie(dopo_costi, paese, anno_preferito=anno) for paese in paesi]
    valori_arop = [0 if valore is None else valore for valore in valori_arop]
    valori_dopo = [0 if valore is None else valore for valore in valori_dopo]

    figura, asse = plt.subplots(figsize=(9.2, 5.3))
    ascisse = np.arange(2)
    larghezza = 0.26
    barre_arop = asse.bar(ascisse - larghezza / 2, valori_arop, width=larghezza, color=COLORE_ACCENTO, label="Rischio poverta'")
    barre_dopo = asse.bar(
        ascisse + larghezza / 2,
        valori_dopo,
        width=larghezza,
        color=COLORE_ITALIA,
        label="Dopo costi abitativi",
    )
    aggiungi_etichette_barre(asse, barre_arop)
    aggiungi_etichette_barre(asse, barre_dopo)
    aggiungi_titolo(
        asse,
        "Rischio poverta' prima e dopo i costi abitativi, 2024",
    )
    applica_stile_grafici_europei(asse, percentuale=True)
    asse.set_xticks(ascisse)
    asse.set_xticklabels(["IT", "EU27"], fontweight="bold")
    asse.set_ylim(0, 35)
    aggiungi_legenda_figura(figura, asse, colonne=2)
    aggiungi_footer_grafici_europei(figura, "Eurostat (ilc_li45, tespm010)")

    percorso = cartella_grafici_europei(cartella_output) / "italia_ue_rischio_poverta_costi_abitativi.png"
    salva_grafico_europeo(figura, percorso)
    return percorso


def crea_grafici_europei(cartella_output="outputs/charts", mostra_progresso=False):
    grafici = [
        {"nome": "prezzi, affitti, redditi e inflazione", "tipo": "funzione", "funzione": grafico_prezzi_affitti_redditi_inflazione},
        {
            "nome": "investimenti in abitazioni",
            "tipo": "banda",
            "dataset_code": "nama_10_an6",
            "filtri": {"freq": "A", "unit": "PC_GDP", "asset10": "N111G"},
            "titolo": "Investimenti in abitazioni (% del PIL)",
            "nome_file": "italia_ue_investimenti_abitazioni_pil.png",
            "inizio": "2000",
            "percentuale": True,
        },
        {
            "nome": "permessi di costruzione",
            "tipo": "linee",
            "dataset_code": "sts_cobp_q",
            "filtri": {
                "freq": "Q",
                "indic_bt": "BPRM_DW",
                "cpa2_1": "CPA_F41001_X_410014",
                "s_adj": "SCA",
                "unit": "I21",
            },
            "titolo": "Permessi di costruzione abitazioni (2021=100)",
            "nome_file": "italia_ue_permessi_costruzione_abitazioni.png",
            "inizio": "2021-Q1",
            "percentuale": True,
        },
        {
            "nome": "costi di costruzione residenziale",
            "tipo": "banda",
            "dataset_code": "sts_copi_q",
            "filtri": {
                "freq": "Q",
                "indic_bt": "COST",
                "cpa2_1": "CPA_F41001_X_410014",
                "s_adj": "NSA",
                "unit": "I21",
            },
            "titolo": "Costi di costruzione dei nuovi edifici residenziali (2021-Q1=100)",
            "nome_file": "italia_ue_costi_costruzione_residenziale.png",
            "inizio": "2021-Q1",
            "percentuale": True,
        },
        {"nome": "titolo di godimento dell'abitazione", "tipo": "funzione", "funzione": grafico_tenure_status},
        {"nome": "proprietari per gruppo di reddito", "tipo": "funzione", "funzione": grafico_homeownership_income},
        {"nome": "sovraccarico costi per inquilini", "tipo": "funzione", "funzione": grafico_overburden_inquilini},
        {"nome": "abitazione adeguata e rischio poverta'", "tipo": "funzione", "funzione": grafico_accesso_adeguato_arop},
        {"nome": "rischio poverta' dopo costi abitativi", "tipo": "funzione", "funzione": grafico_arop_prima_dopo_costi},
        {
            "nome": "eta' uscita dalla casa dei genitori",
            "tipo": "banda",
            "dataset_code": "yth_demo_030",
            "filtri": {"freq": "A", "unit": "AVG", "sex": "T"},
            "titolo": "Eta' media di uscita dalla casa dei genitori",
            "nome_file": "italia_ue_eta_uscita_casa_genitori.png",
            "inizio": "2000",
            "percentuale": False,
        },
    ]

    percorsi = []
    totale = len(grafici)
    for posizione, grafico in enumerate(grafici, start=1):
        if mostra_progresso:
            print(f"[Confronti Italia-UE {posizione}/{totale}] Creo {grafico['nome']}", flush=True)

        if grafico["tipo"] == "funzione":
            percorso = grafico["funzione"](cartella_output)
        elif grafico["tipo"] == "banda":
            percorso = grafico_banda_europeo(
                grafico["dataset_code"],
                grafico["filtri"],
                grafico["titolo"],
                grafico["nome_file"],
                cartella_output,
                inizio=grafico.get("inizio"),
                fine=grafico.get("fine"),
                percentuale=grafico["percentuale"],
            )
        elif grafico["tipo"] == "linee":
            percorso = grafico_linee_europeo(
                grafico["dataset_code"],
                grafico["filtri"],
                grafico["titolo"],
                grafico["nome_file"],
                cartella_output,
                inizio=grafico.get("inizio"),
                fine=grafico.get("fine"),
                percentuale=grafico["percentuale"],
            )
        else:
            percorso = None

        if percorso:
            percorsi.append(percorso)

    if mostra_progresso:
        print(f"Confronti Italia-UE completati: {len(percorsi)} grafici creati.", flush=True)
    return percorsi
