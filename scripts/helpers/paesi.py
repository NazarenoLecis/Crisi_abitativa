from pathlib import Path
import re
import unicodedata
import pycountry
from scripts.helpers.config import EU27_CODES


PAESI_DEFAULT_CONFRONTO = ["ITA", "FRA", "DEU"]

PAESI_OECD_PREZZI_CASE = [
    "AUS",
    "AUT",
    "BEL",
    "CAN",
    "CHE",
    "CHL",
    "COL",
    "CZE",
    "DEU",
    "DNK",
    "ESP",
    "EST",
    "FIN",
    "FRA",
    "GBR",
    "GRC",
    "HUN",
    "IRL",
    "ISL",
    "ISR",
    "ITA",
    "JPN",
    "KOR",
    "LTU",
    "LUX",
    "LVA",
    "MEX",
    "NLD",
    "NOR",
    "NZL",
    "POL",
    "PRT",
    "SVK",
    "SVN",
    "SWE",
    "TUR",
    "USA",
    "ZAF",
]

NOMI_PAESI = {
    "AUS": "Australia",
    "AUT": "Austria",
    "BEL": "Belgio",
    "BGR": "Bulgaria",
    "CAN": "Canada",
    "CHE": "Svizzera",
    "CHL": "Cile",
    "COL": "Colombia",
    "CRI": "Costa Rica",
    "HRV": "Croazia",
    "CYP": "Cipro",
    "CZE": "Cechia",
    "DEU": "Germania",
    "DNK": "Danimarca",
    "ESP": "Spagna",
    "EST": "Estonia",
    "FIN": "Finlandia",
    "FRA": "Francia",
    "GBR": "Regno Unito",
    "GRC": "Grecia",
    "HUN": "Ungheria",
    "IRL": "Irlanda",
    "ISL": "Islanda",
    "ISR": "Israele",
    "ITA": "Italia",
    "JPN": "Giappone",
    "KOR": "Corea",
    "LTU": "Lituania",
    "LUX": "Lussemburgo",
    "LVA": "Lettonia",
    "MEX": "Messico",
    "MLT": "Malta",
    "NLD": "Paesi Bassi",
    "NOR": "Norvegia",
    "NZL": "Nuova Zelanda",
    "POL": "Polonia",
    "PRT": "Portogallo",
    "ROU": "Romania",
    "SVK": "Slovacchia",
    "SVN": "Slovenia",
    "SWE": "Svezia",
    "TUR": "Turchia",
    "USA": "Stati Uniti",
    "ZAF": "Sudafrica",
}

NOMI_OECD_AHD = {
    "CZE": "Czech Republic",
    "KOR": "Korea",
    "SVK": "Slovak Republic",
    "TUR": "Türkiye",
    "USA": "United States",
}

COLORI_PAESI = {
    "ITA": "#C1121F",
    "FRA": "#2F6BFF",
    "DEU": "#C48A00",
}

COLORI_PALETTE = [
    "#0D3B66",
    "#2A9D8F",
    "#E76F51",
    "#6A4C93",
    "#457B9D",
    "#7A9E35",
    "#BC6C25",
    "#3A5A40",
    "#8E5572",
    "#1D3557",
]


def codice_iso3_da_iso2(codice_iso2):
    paese = pycountry.countries.get(alpha_2=str(codice_iso2).upper())
    if paese:
        return paese.alpha_3
    return str(codice_iso2).upper()


PAESI_EUROSTAT = sorted(codice_iso3_da_iso2(codice) for codice in EU27_CODES)
PAESI_OECD = sorted(PAESI_OECD_PREZZI_CASE)
PAESI_ACCETTATI = sorted(set(PAESI_EUROSTAT) | set(PAESI_OECD))
SCORCIATOIE_PAESI = {
    "tutti": PAESI_ACCETTATI,
    "eurostat": PAESI_EUROSTAT,
    "oecd": PAESI_OECD,
}
VALORI_PAESI_RUN = sorted(PAESI_ACCETTATI + list(SCORCIATOIE_PAESI))


def slug_testo(testo):
    normalizzato = unicodedata.normalize("NFKD", str(testo))
    ascii_testo = normalizzato.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_testo.lower()).strip("_")
    return slug or "paese"


def paese_pycountry(codice):
    return pycountry.countries.get(alpha_3=str(codice).upper())


def nome_inglese_paese(codice):
    paese = paese_pycountry(codice)
    if paese:
        return getattr(paese, "common_name", paese.name)
    return str(codice).upper()


def codice_iso2_paese(codice):
    paese = paese_pycountry(codice)
    if paese:
        return paese.alpha_2
    return str(codice).upper()[:2]


def colore_paese(codice):
    codice_normale = str(codice).upper()
    if codice_normale in COLORI_PAESI:
        return COLORI_PAESI[codice_normale]

    posizione = PAESI_ACCETTATI.index(codice_normale) if codice_normale in PAESI_ACCETTATI else 0
    return COLORI_PALETTE[posizione % len(COLORI_PALETTE)]


def crea_profilo_paese(codice):
    codice_normale = str(codice).upper()
    nome = NOMI_PAESI.get(codice_normale, nome_inglese_paese(codice_normale))
    return {
        "iso2": codice_iso2_paese(codice_normale),
        "iso3": codice_normale,
        "slug": slug_testo(nome),
        "nome": nome,
        "nome_file": slug_testo(nome),
        "label": nome,
        "colore": colore_paese(codice_normale),
        "nome_oecd_ahd": NOMI_OECD_AHD.get(codice_normale, nome_inglese_paese(codice_normale)),
        "ha_eurostat": codice_normale in PAESI_EUROSTAT,
        "ha_oecd": codice_normale in PAESI_OECD,
    }


PAESI_CONFRONTO = {codice: crea_profilo_paese(codice) for codice in PAESI_ACCETTATI}
SLUG_PAESI_CONFRONTO = {profilo["slug"] for profilo in PAESI_CONFRONTO.values()}


def profilo_paese(codice):
    codice_normale = str(codice).upper()
    if codice_normale not in PAESI_CONFRONTO:
        valori = ", ".join(VALORI_PAESI_RUN)
        raise ValueError(f"Paese non configurato: {codice}. Valori ammessi: {valori}")
    return PAESI_CONFRONTO[codice_normale]


def profili_paesi(codici):
    return [profilo_paese(codice) for codice in codici]


def radice_output(cartella_output):
    percorso = Path(cartella_output)
    if percorso.name in {"charts", "summary"}:
        return percorso.parent
    return percorso


def cartella_paese(cartella_output, paese, sezione=None):
    profilo = paese if isinstance(paese, dict) else profilo_paese(paese)
    parti = [radice_output(cartella_output), profilo["slug"], "charts"]
    if sezione:
        parti.append(sezione)

    cartella = Path(*parti)
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella


def aggiungi_codici_unici(codici):
    risultato = []
    visti = set()
    for codice in codici:
        codice_normale = str(codice).upper()
        if codice_normale not in visti:
            risultato.append(codice_normale)
            visti.add(codice_normale)
    return risultato


def risolvi_codici_paesi(codici, default=None):
    if codici is None:
        return list(default or PAESI_DEFAULT_CONFRONTO)

    codici_risolti = []
    for codice in codici:
        valore = str(codice).strip()
        valore_minuscolo = valore.lower()
        if valore_minuscolo in SCORCIATOIE_PAESI:
            codici_risolti.extend(SCORCIATOIE_PAESI[valore_minuscolo])
        else:
            codici_risolti.append(valore.upper())

    codici_unici = aggiungi_codici_unici(codici_risolti)
    non_validi = [codice for codice in codici_unici if codice not in PAESI_CONFRONTO]
    if non_validi:
        valori = ", ".join(VALORI_PAESI_RUN)
        raise ValueError(f"Paesi non validi: {', '.join(non_validi)}. Valori ammessi: {valori}")

    return codici_unici


def normalizza_codici_paesi(codici):
    return risolvi_codici_paesi(codici, default=PAESI_DEFAULT_CONFRONTO)


def filtra_paesi_eurostat(codici):
    return [codice for codice in codici if codice in PAESI_EUROSTAT]


def filtra_paesi_oecd(codici):
    return [codice for codice in codici if codice in PAESI_OECD]
