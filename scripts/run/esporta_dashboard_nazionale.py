from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import base64
import json
import time
import warnings

import pandas as pd
import requests


RADICE_PROGETTO = Path(__file__).resolve().parents[2]
OUTPUT = RADICE_PROGETTO / "outputs" / "dashboard" / "crisi-abitativa" / "dashboard_extra.json"

EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
BDSR_DASHBOARD_CSV_URL = "https://api-bdsr.ministeroturismo.gov.it/ui/user/downloadCsvDashboard"
OECD_AHD_BASE_URL = "https://webfs.oecd.org/Els-com/Affordable_Housing_Database"

SFRATTI_ITALIA = RADICE_PROGETTO / "italia" / "sfratti" / "sfratti_italia_2024.csv"


def richiesta_get(url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", "crisi-abitativa/0.1")
    ultimo_errore = None
    for tentativo in range(1, 5):
        try:
            risposta = requests.get(url, headers=headers, timeout=kwargs.pop("timeout", 120), **kwargs)
            risposta.raise_for_status()
            return risposta
        except Exception as errore:
            ultimo_errore = errore
            time.sleep(min(10, tentativo * 2))
    raise RuntimeError(f"Richiesta fallita per {url}: {ultimo_errore}") from ultimo_errore


def decode_jsonstat(payload):
    dimensioni = payload.get("id") or []
    dimensioni_size = payload.get("size") or []
    metadati = payload.get("dimension") or {}
    codici_dimensioni = []
    labels_dimensioni = []

    for dimensione in dimensioni:
        categoria = metadati.get(dimensione, {}).get("category", {})
        indici = categoria.get("index", {})
        labels = categoria.get("label", {})
        inverso = {posizione: codice for codice, posizione in indici.items()}
        codici = [inverso[posizione] for posizione in range(len(inverso))]
        codici_dimensioni.append(codici)
        labels_dimensioni.append(labels)

    righe = []
    for indice_testo, valore in (payload.get("value") or {}).items():
        indice = int(indice_testo)
        coordinate = [0] * len(dimensioni_size)
        for posizione in range(len(dimensioni_size) - 1, -1, -1):
            coordinate[posizione] = indice % dimensioni_size[posizione]
            indice //= dimensioni_size[posizione]

        riga = {}
        for posizione, dimensione in enumerate(dimensioni):
            codice = codici_dimensioni[posizione][coordinate[posizione]]
            riga[dimensione] = codice
            riga[f"{dimensione}_label"] = labels_dimensioni[posizione].get(codice, codice)
        riga["value"] = float(valore)
        righe.append(riga)

    return righe


def eurostat_records(dataset, params):
    risposta = richiesta_get(f"{EUROSTAT_API}/{dataset}", params=params, timeout=90)
    payload = risposta.json()
    righe = decode_jsonstat(payload)
    for riga in righe:
        riga["source_updated"] = payload.get("updated", "")
        riga["source_dataset"] = dataset
    return righe


def ultimo_anno(righe, campo_periodo="time"):
    periodi = sorted({str(riga.get(campo_periodo, "")) for riga in righe if riga.get(campo_periodo)})
    return periodi[-1] if periodi else ""


def records_tenure():
    params = {
        "freq": "A",
        "unit": "PC",
        "rskpovth": "TOTAL",
        "hhcomp": "TOTAL",
        "tenure": ["OWN_L", "OWN_NL", "RENT_FR", "RENT_MKT"],
        "geo": ["IT", "EU27_2020"],
    }
    righe = eurostat_records("ilc_lvho02", params)
    anno = ultimo_anno([riga for riga in righe if riga.get("geo") == "IT"])
    labels = {
        "OWN_L": "Proprieta' con mutuo",
        "OWN_NL": "Proprieta' senza mutuo",
        "RENT_FR": "Affitto ridotto o gratuito",
        "RENT_MKT": "Affitto a prezzo di mercato",
    }
    ordine = ["OWN_L", "OWN_NL", "RENT_FR", "RENT_MKT"]
    records = []
    for geo in ["IT", "EU27_2020"]:
        for codice in ordine:
            riga = next(
                (
                    item
                    for item in righe
                    if item.get("geo") == geo and item.get("time") == anno and item.get("tenure") == codice
                ),
                None,
            )
            if not riga:
                continue
            records.append(
                {
                    "scope": "Italia" if geo == "IT" else "EU27",
                    "category": labels[codice],
                    "code": codice,
                    "value": riga["value"],
                    "unit": "% popolazione",
                    "period": anno,
                }
            )
    quota_affitto = sum(
        item["value"] for item in records if item["scope"] == "Italia" and item["code"] in {"RENT_FR", "RENT_MKT"}
    )
    quota_proprieta = sum(
        item["value"] for item in records if item["scope"] == "Italia" and item["code"] in {"OWN_L", "OWN_NL"}
    )
    return {
        "id": "tenure",
        "title": "Proprieta' e mercato dell'affitto",
        "subtitle": "Titolo di godimento dell'abitazione, Italia vs EU27",
        "chart_type": "stacked_bar",
        "records": records,
        "kpis": [
            {"label": "Persone in affitto", "value": round(quota_affitto, 1), "unit": "%", "period": anno},
            {"label": "Persone in proprieta'", "value": round(quota_proprieta, 1), "unit": "%", "period": anno},
        ],
        "note": "Mostra perche' il mercato dell'affitto italiano e' piu' stretto della proprieta': la quota in affitto e' minoritaria, quindi shock su pochi segmenti urbani possono diventare molto visibili.",
        "source": "Eurostat ilc_lvho02",
        "source_url": "https://ec.europa.eu/eurostat/databrowser/view/ilc_lvho02/default/table",
    }


def valore_censimento_stock(housing):
    params = {"freq": "A", "housing": housing, "y_const": "TOTAL", "unit": "NR", "geo": "IT"}
    righe = eurostat_records("cens_21dwop_r3", params)
    if not righe:
        return None, ""
    riga = righe[-1]
    return riga["value"], str(riga.get("time", "2021"))


def records_stock_attivabile():
    totale, periodo = valore_censimento_stock("DW")
    occupate, _ = valore_censimento_stock("DW_OC")
    non_occupate, _ = valore_censimento_stock("DW_NOC")
    quota_non_occupate = non_occupate / totale * 100 if totale else None
    return {
        "id": "stock_activation",
        "title": "Stock esistente e abitazioni non occupate",
        "subtitle": "Censimento Eurostat 2021",
        "chart_type": "donut",
        "records": [
            {"category": "Abitazioni occupate", "value": occupate, "unit": "abitazioni", "period": periodo},
            {"category": "Abitazioni non occupate", "value": non_occupate, "unit": "abitazioni", "period": periodo},
        ],
        "kpis": [
            {"label": "Stock totale", "value": totale, "unit": "abitazioni", "period": periodo},
            {
                "label": "Quota non occupata",
                "value": round(quota_non_occupate, 1) if quota_non_occupate is not None else None,
                "unit": "%",
                "period": periodo,
            },
        ],
        "note": "Il dato non dice che tutte le abitazioni non occupate siano immediatamente disponibili: e' una misura del potenziale e del mismatch tra stock fisico e offerta effettiva.",
        "source": "Eurostat census 2021, cens_21dwop_r3",
        "source_url": "https://ec.europa.eu/eurostat/databrowser/view/cens_21dwop_r3/default/table",
    }


def records_sfratti():
    frame = pd.read_csv(SFRATTI_ITALIA)
    riga = frame.iloc[0]
    anno = str(int(riga["anno"]))
    records = [
        {
            "category": "Provvedimenti emessi",
            "value": float(riga["provvedimenti_totali"]),
            "unit": "provvedimenti",
            "period": anno,
        },
        {
            "category": "Per morosita' o altra causa",
            "value": float(riga["morosita_altra_causa_totale"]),
            "unit": "provvedimenti",
            "period": anno,
        },
        {
            "category": "Richieste di esecuzione",
            "value": float(riga["richieste_esecuzione"]),
            "unit": "richieste",
            "period": anno,
        },
        {
            "category": "Sfratti eseguiti",
            "value": float(riga["sfratti_eseguiti"]),
            "unit": "esecuzioni",
            "period": anno,
        },
    ]
    quota_morosita = float(riga["morosita_altra_causa_totale"]) / float(riga["provvedimenti_totali"]) * 100
    return {
        "id": "evictions",
        "title": "Rischio locazione e sfratti",
        "subtitle": "Italia, Ministero dell'Interno",
        "chart_type": "bar",
        "records": records,
        "kpis": [
            {"label": "Provvedimenti", "value": float(riga["provvedimenti_totali"]), "unit": "", "period": anno},
            {"label": "Quota morosita'", "value": round(quota_morosita, 1), "unit": "%", "period": anno},
            {"label": "Sfratti eseguiti", "value": float(riga["sfratti_eseguiti"]), "unit": "", "period": anno},
        ],
        "note": "Serve per discutere il rischio percepito dai proprietari e il nodo sicurezza dell'affitto: la morosita' pesa sulla maggior parte dei provvedimenti.",
        "source": str(riga.get("fonte", "Ministero Interno")),
        "source_url": "https://ucs.interno.gov.it/ucs/contenuti/Provvedimenti_esecutivi_di_sfratto_e_richieste_di_esecuzione_dati_2024-23323050.htm",
    }


def leggi_oecd_ahd(nome_file, foglio):
    risposta = richiesta_get(f"{OECD_AHD_BASE_URL}/{nome_file}", timeout=120)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        return pd.read_excel(BytesIO(risposta.content), sheet_name=foglio, header=None)


def tabella_oecd_barre(nome_file, foglio, col_paese, col_valore, col_anno=None, moltiplicatore=1.0):
    foglio_excel = leggi_oecd_ahd(nome_file, foglio)
    tabella = pd.DataFrame(
        {
            "country": foglio_excel.iloc[:, col_paese].astype(str).str.strip(),
            "value": pd.to_numeric(foglio_excel.iloc[:, col_valore], errors="coerce") * moltiplicatore,
        }
    )
    if col_anno is not None:
        tabella["period"] = foglio_excel.iloc[:, col_anno].astype(str).str.strip()
    else:
        tabella["period"] = ""
    tabella = tabella.loc[(tabella["country"] != "") & tabella["value"].notna()].copy()
    tabella = tabella.drop_duplicates("country", keep="first")
    return tabella


def records_social_housing():
    social = tabella_oecd_barre(
        "PH4-2-Social-rental-housing-stock.xlsx",
        "Figure PH4.2.1",
        col_paese=12,
        col_valore=13,
        col_anno=14,
    )
    social_records = []
    for paese in ["Italy", "EU", "OECD"]:
        riga = social.loc[social["country"] == paese]
        if riga.empty:
            continue
        item = riga.iloc[0]
        social_records.append(
            {
                "category": {"Italy": "Italia", "EU": "EU", "OECD": "OECD"}[paese],
                "value": float(item["value"]),
                "unit": "% stock abitativo",
                "period": str(item["period"]).replace(".0", "") if str(item["period"]) != "nan" else "",
            }
        )

    erp_total = 823734
    erp_vacant = 61300
    erp_abusive = 22700
    erp_old_share = 84.7
    erp_vacant_share = erp_vacant / erp_total * 100
    return {
        "id": "public_social_housing",
        "title": "ERP e social housing",
        "subtitle": "Stock sociale, alloggi ERP e quota non assegnabile",
        "chart_type": "bar",
        "records": social_records,
        "kpis": [
            {"label": "Alloggi ERP gestiti", "value": erp_total, "unit": "alloggi", "period": "2024/25"},
            {"label": "ERP sfitti da ristrutturare", "value": erp_vacant, "unit": "alloggi", "period": "2024/25"},
            {"label": "Quota ERP sfitta", "value": round(erp_vacant_share, 1), "unit": "%", "period": "2024/25"},
            {"label": "ERP pre-1990", "value": erp_old_share, "unit": "%", "period": "2024/25"},
            {"label": "ERP occupati abusivamente", "value": erp_abusive, "unit": "alloggi", "period": "2024/25"},
        ],
        "note": "Il confronto OECD misura il social rental housing sullo stock totale; i KPI Federcasa-Nomisma raccontano invece il patrimonio ERP gestito e il blocco manutentivo.",
        "source": "OECD Affordable Housing Database; Federcasa-Nomisma Osservatorio nazionale ERP 2024/25",
        "source_url": "https://www.oecd.org/en/data/datasets/oecd-affordable-housing-database.html",
        "secondary_source_url": "https://www.federcasa.it/dms/file/open/?919609c0-42b5-4fd5-8d2b-2db540d57e38=",
    }


def records_student_housing():
    studenti_fuori_sede = 446603
    posti_letto = 49251
    target_nuovi_pnrr = 60000
    target_riforma = 105500
    copertura = posti_letto / studenti_fuori_sede * 100
    return {
        "id": "student_housing",
        "title": "Student housing",
        "subtitle": "Domanda fuori sede, offerta strutturata e target PNRR",
        "chart_type": "bar",
        "records": [
            {"category": "Studenti fuori sede", "value": studenti_fuori_sede, "unit": "studenti", "period": "ANVUR 2023"},
            {"category": "Posti letto rilevati", "value": posti_letto, "unit": "posti letto", "period": "ANVUR 2023"},
            {"category": "Nuovi posti target PNRR", "value": target_nuovi_pnrr, "unit": "posti letto", "period": "target 2026"},
            {"category": "Target stock riforma", "value": target_riforma, "unit": "posti letto", "period": "target"},
        ],
        "kpis": [
            {"label": "Copertura posti/fuori sede", "value": round(copertura, 1), "unit": "%", "period": "ANVUR 2023"},
            {"label": "Target nuovi posti", "value": target_nuovi_pnrr, "unit": "posti letto", "period": "PNRR"},
            {"label": "Fondo CDP 2026", "value": 599, "unit": "milioni euro", "period": "2026"},
            {"label": "Canone calmierato minimo", "value": 15, "unit": "% sotto mercato", "period": "bando CDP"},
            {"label": "Posti riservati DSU", "value": 30, "unit": "%", "period": "bando CDP"},
        ],
        "note": "Il blocco serve a mostrare perche' gli studentati non sono un dettaglio settoriale: quando l'offerta strutturata e' bassa, la domanda studentesca ricade sul mercato privato degli affitti.",
        "source": "ANVUR Rapporto 2023; MUR/PNRR; CDP Fondo alloggi studenti",
        "source_url": "https://www.anvur.it/it/dati-e-pubblicazioni/rapporto-anvur/rapporto-biennale-2023",
        "secondary_source_url": "https://www.cdp.it/sitointernet/it/nuovo_bando_studentati_pnrr.page",
    }


def numeri_bdsr(frame, colonna):
    return pd.to_numeric(
        frame[colonna].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0)


def records_short_rentals():
    risposta = richiesta_get(
        BDSR_DASHBOARD_CSV_URL,
        timeout=120,
        headers={"Accept": "application/json", "Authorization": "Bearer undefined", "Lang": "it"},
    )
    dati = risposta.json()
    contenuto = base64.b64decode(dati["csv"])
    frame = pd.read_csv(BytesIO(contenuto), dtype=str, keep_default_na=False, encoding="latin1")
    colonne_valori = [
        "Totale strutture con CIN verificato",
        "Totale strutture con CIN non verificato",
        "Totale strutture senza CIN",
        "Totale strutture",
    ]
    for colonna in colonne_valori:
        frame[colonna] = numeri_bdsr(frame, colonna)

    totale = float(frame["Totale strutture"].sum())
    status_records = [
        {
            "category": "CIN verificato",
            "value": float(frame["Totale strutture con CIN verificato"].sum()),
            "unit": "strutture",
            "period": dati.get("nomeFile", ""),
        },
        {
            "category": "CIN non verificato",
            "value": float(frame["Totale strutture con CIN non verificato"].sum()),
            "unit": "strutture",
            "period": dati.get("nomeFile", ""),
        },
        {
            "category": "Senza CIN",
            "value": float(frame["Totale strutture senza CIN"].sum()),
            "unit": "strutture",
            "period": dati.get("nomeFile", ""),
        },
    ]

    macro = (
        frame.groupby(["Codice Macrocategoria ISTAT", "Macrocategoria ISTAT"], as_index=False)["Totale strutture"]
        .sum()
        .sort_values("Totale strutture", ascending=False)
    )
    macro_records = [
        {
            "category": riga["Macrocategoria ISTAT"],
            "code": riga["Codice Macrocategoria ISTAT"],
            "value": float(riga["Totale strutture"]),
            "unit": "strutture",
            "period": dati.get("nomeFile", ""),
        }
        for _, riga in macro.iterrows()
    ]

    regioni = (
        frame.groupby("Regione", as_index=False)["Totale strutture"]
        .sum()
        .sort_values("Totale strutture", ascending=False)
        .head(10)
    )
    regional_records = [
        {
            "category": riga["Regione"],
            "value": float(riga["Totale strutture"]),
            "unit": "strutture",
            "period": dati.get("nomeFile", ""),
        }
        for _, riga in regioni.iterrows()
    ]

    categoria = (
        frame.groupby(["Codice Categoria ISTAT", "Categoria ISTAT"], as_index=False)["Totale strutture"]
        .sum()
        .sort_values("Totale strutture", ascending=False)
    )
    categoria_records = [
        {
            "category": riga["Categoria ISTAT"],
            "code": riga["Codice Categoria ISTAT"],
            "value": float(riga["Totale strutture"]),
            "unit": "strutture",
            "period": dati.get("nomeFile", ""),
        }
        for _, riga in categoria.head(8).iterrows()
    ]

    quota_verificata = status_records[0]["value"] / totale * 100 if totale else None
    return {
        "id": "short_rentals",
        "title": "Affitti brevi e ricettivo",
        "subtitle": "Registro CIN/BDSR nazionale",
        "chart_type": "bar",
        "records": status_records,
        "macro_records": macro_records,
        "category_records": categoria_records,
        "regional_records": regional_records,
        "kpis": [
            {"label": "Totale strutture BDSR", "value": totale, "unit": "strutture", "period": dati.get("nomeFile", "")},
            {
                "label": "Quota CIN verificato",
                "value": round(quota_verificata, 1) if quota_verificata is not None else None,
                "unit": "%",
                "period": dati.get("nomeFile", ""),
            },
        ],
        "note": "Il registro CIN non misura notti, fatturato o canoni, ma rende visibile la scala territoriale dell'offerta turistica e delle locazioni brevi registrate.",
        "source": "Ministero del Turismo, BDSR/registro CIN",
        "source_url": "https://bdsr.ministeroturismo.gov.it/",
    }


def records_policy_mix():
    return {
        "id": "policy_mix",
        "title": "Policy mix da tenere insieme",
        "subtitle": "Le leve da incrociare nei grafici della dashboard",
        "chart_type": "cards",
        "records": [
            {
                "label": "Aumentare offerta strutturale",
                "metric": "ERP, ERS/social housing, studentati, recupero stock",
                "why": "Se la crisi e' di offerta locale, i soli bonus alla domanda tendono a rincorrere i canoni.",
            },
            {
                "label": "Ridurre rischio percepito",
                "metric": "sfratti, morosita', garanzie, agenzie sociali",
                "why": "Una parte dello stock resta fuori dal mercato quando il proprietario teme tempi lunghi o morosita'.",
            },
            {
                "label": "Evitare vincoli controproducenti",
                "metric": "permessi, costi, produzione edilizia, rigenerazione",
                "why": "Controlli e limiti aiutano solo se non bloccano nuova offerta e riuso dello stock.",
            },
            {
                "label": "Governare affitti brevi",
                "metric": "BDSR/CIN, pressione territoriale, aree ad alta domanda",
                "why": "La regolazione va mirata dove turismo, universita' e mercato lungo competono sullo stesso stock.",
            },
            {
                "label": "Allargare il mercato accessibile",
                "metric": "trasporto pubblico e connessioni casa-lavoro/studio",
                "why": "Migliori collegamenti aumentano le alternative reali senza concentrare tutta la domanda nei centri.",
            },
            {
                "label": "Usare i sussidi come ponte",
                "metric": "housing allowances e contributi affitto",
                "why": "Sono utili contro l'emergenza, ma non sostituiscono ERP, ERS e nuova offerta.",
            },
        ],
        "kpis": [
            {
                "label": "Spesa housing allowances Italia",
                "value": None,
                "unit": "% PIL",
                "period": "OECD AHD",
                "note": "OECD indica che l'Italia ha housing allowances ma non pubblica una spesa comparabile nel file PH3.1.",
            }
        ],
        "note": "Questo pannello non e' una ricetta unica: serve da promemoria operativo per leggere insieme domanda, offerta, regole, rischio e mobilita'.",
        "source": "OECD Affordable Housing Database; fonti dashboard Eurostat/OMI/MEF/BDSR",
        "source_url": "https://www.oecd.org/en/data/datasets/oecd-affordable-housing-database.html",
    }


def build_payload():
    moduli = [
        records_tenure(),
        records_stock_attivabile(),
        records_sfratti(),
        records_social_housing(),
        records_student_housing(),
        records_short_rentals(),
        records_policy_mix(),
    ]
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "title": "Crisi abitativa - moduli nazionali extra per dashboard",
        "description": (
            "Payload compatto per integrare nella dashboard i driver nazionali non gia' coperti "
            "dai grafici Eurostat/OMI/MEF principali."
        ),
        "coverage_tags": [
            "affordability",
            "domanda",
            "offerta",
            "stock",
            "affitto",
            "sfratti",
            "ERP/social housing",
            "student housing",
            "affitti brevi",
            "policy mix",
        ],
        "modules": moduli,
        "sources": [
            {"label": "Eurostat", "url": "https://ec.europa.eu/eurostat/databrowser/"},
            {
                "label": "OECD Affordable Housing Database",
                "url": "https://www.oecd.org/en/data/datasets/oecd-affordable-housing-database.html",
            },
            {"label": "Ministero del Turismo - BDSR/CIN", "url": "https://bdsr.ministeroturismo.gov.it/"},
            {"label": "Ministero dell'Interno - sfratti", "url": "https://ucs.interno.gov.it/"},
            {"label": "ANVUR Rapporto 2023", "url": "https://www.anvur.it/it/dati-e-pubblicazioni/rapporto-anvur/rapporto-biennale-2023"},
            {"label": "CDP/MUR Fondo alloggi studenti", "url": "https://www.cdp.it/sitointernet/it/nuovo_bando_studentati_pnrr.page"},
            {"label": "Federcasa-Nomisma Osservatorio ERP 2024/25", "url": "https://www.federcasa.it/dms/file/open/?919609c0-42b5-4fd5-8d2b-2db540d57e38="},
        ],
    }


def run(output=OUTPUT):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Creato {output}")
    print(f"Moduli dashboard: {len(payload['modules'])}")
    return output


if __name__ == "__main__":
    run()
