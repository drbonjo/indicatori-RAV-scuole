# -*- coding: utf-8 -*-
"""
Created on Fri Sep 11 14:42:24 2026

@author: imore
"""

from bs4 import BeautifulSoup
import re 
import pandas as pd 


def _clean_html_text(node):
    """
    Estrae il testo da un nodo HTML eliminando spazi,
    newline e tabulazioni ridondanti.
    """
    return re.sub(
        r"\s+",
        " ",
        node.get_text(" ", strip=True)
    ).strip()


def _strip_province_prefix(label):
    """
    'Provincia di ASCOLI PICENO'
        -> 'ASCOLI PICENO'
    """
    return re.sub(
        r"(?i)^Provincia\s+(?:autonoma\s+)?di\s+",
        "",
        label
    ).strip()


def _df_from_rows(rows, id_cols):
    """
    Costruisce il DataFrame mettendo prima le colonne identificative.
    """
    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=id_cols)

    other_cols = [
        col for col in df.columns
        if col not in id_cols
    ]

    return df[id_cols + other_cols]

def parse_descrittore_21a2(
    dat,
    descrittore="2.1.a.2"
):
    """
    Estrae dal record con descrittore 2.1.a.2
    i dati relativi a:

        - scuole
        - province
        - regioni
        - Italia

    Restituisce un dizionario contenente quattro DataFrame.
    """

    school_rows = []
    province_rows = []
    region_rows = []
    national_rows = []

    found = 0

    # ==========================================================
    # CICLO SUI RECORD DEL JSONL
    # ==========================================================

    for item in dat:

        record = item.get("record")

        if not isinstance(record, dict):
            continue

        if record.get("descrittore") != descrittore:
            continue

        found += 1

        html = record.get("html")
        codice_istituto = record.get("scuola")

        if not isinstance(html, str):
            continue

        if not html.strip():
            continue

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # ======================================================
        # CICLO SULLE TABELLE
        # ======================================================

        for table in soup.find_all("table"):

            trs = table.find_all("tr")

            if not trs:
                continue

            grado = None
            classi = None
            header_idx = None

            # ==================================================
            # INDIVIDUA LA RIGA DELLE CLASSI
            # ==================================================

            for i, tr in enumerate(trs):

                cells = tr.find_all(
                    ["th", "td"],
                    recursive=False
                )

                texts = [
                    _clean_html_text(cell)
                    for cell in cells
                ]

                if not texts:
                    continue

                # la prima cella normalmente è vuota,
                # le successive sono Classe I, Classe II, ...
                class_labels = [
                    x for x in texts
                    if x.lower().startswith("classe ")
                ]

                if class_labels:

                    classi = class_labels
                    header_idx = i
                    break

            # se non troviamo le classi,
            # la tabella non è del formato atteso
            if header_idx is None:
                continue

            # ==================================================
            # INDIVIDUA IL TITOLO / GRADO
            #
            # Cerchiamo nelle righe precedenti alla riga
            # delle classi, partendo dalla più vicina.
            #
            # Esempi:
            #   Scientifico
            #   Scientifico - Scienze Applicate
            #   Scientifico - Sportivo
            #   Tecnico Tecnologico
            # ==================================================

            for tr in reversed(trs[:header_idx]):

                cells = tr.find_all(
                    ["th", "td"],
                    recursive=False
                )

                texts = [
                    _clean_html_text(cell)
                    for cell in cells
                ]

                texts = [
                    x for x in texts
                    if x
                ]

                if not texts:
                    continue

                # prendiamo la prima riga precedente
                # che contiene testo effettivo
                grado = " ".join(texts).strip()
                break

            if grado is None:
                continue

            # ==================================================
            # LETTURA DELLE RIGHE DATI
            # ==================================================

            in_riferimenti = False

            for tr in trs[header_idx + 1:]:

                cells = tr.find_all(
                    ["th", "td"],
                    recursive=False
                )

                texts = [
                    _clean_html_text(cell)
                    for cell in cells
                ]

                if not texts:
                    continue

                label = texts[0].strip()

                # ------------------------------------------------
                # INIZIO SEZIONE RIFERIMENTI
                # ------------------------------------------------

                if label.casefold() == "riferimenti":
                    in_riferimenti = True
                    continue

                # ------------------------------------------------
                # Devono esserci:
                #
                # 1 colonna identificativa
                # +
                # N colonne corrispondenti alle classi
                # ------------------------------------------------

                if len(texts) != len(classi) + 1:
                    continue

                valori = texts[1:]

                dati = dict(
                    zip(
                        classi,
                        valori
                    )
                )

                # ==================================================
                # SCUOLA
                #
                # Situazione della scuola VCIS02100Q
                # ==================================================

                match_scuola = re.match(
                    r"(?i)^Situazione della scuola\s+(.+?)\s*$",
                    label
                )

                if match_scuola:

                    codice_meccanografico = (
                        match_scuola
                        .group(1)
                        .strip()
                    )

                    school_rows.append({
                        "CODICEISTITUTO":
                            codice_istituto,

                        "CODICEMECCANOGRAFICO":
                            codice_meccanografico,

                        "GRADO":
                            grado,

                        **dati
                    })

                    continue

                # ------------------------------------------------
                # Provincia, regione e Italia devono comparire
                # dopo la riga "Riferimenti"
                # ------------------------------------------------

                if not in_riferimenti:
                    continue

                # ==================================================
                # PROVINCIA
                # ==================================================

                if re.match(
                    r"(?i)^Provincia\b",
                    label
                ):

                    provincia = (
                        _strip_province_prefix(
                            label
                        )
                    )

                    province_rows.append({
                        "PROVINCIA":
                            provincia,

                        "GRADO":
                            grado,

                        **dati
                    })

                    continue

                # ==================================================
                # NAZIONALE
                # ==================================================

                if label.casefold() == "italia":

                    national_rows.append({
                        "NAZIONE":
                            "Italia",

                        "GRADO":
                            grado,

                        **dati
                    })

                    continue

                # ==================================================
                # REGIONE
                #
                # Nel formato HTML attuale, dopo la provincia
                # e prima di Italia, la riga residua è la regione.
                # ==================================================

                region_rows.append({
                    "REGIONE":
                        label,

                    "GRADO":
                        grado,

                    **dati
                })

    # ==========================================================
    # CONTROLLO DESCRITTORE
    # ==========================================================

    if found == 0:

        print(f"descrittore {descrittore} non trovato")

    # ==========================================================
    # OUTPUT
    # ==========================================================

    return {

        "scuole":
            _df_from_rows(
                school_rows,
                [
                    "CODICEISTITUTO",
                    "CODICEMECCANOGRAFICO",
                    "GRADO"
                ]
            ),

        "province":
            _df_from_rows(
                province_rows,
                [
                    "PROVINCIA",
                    "GRADO"
                ]
            ),

        "regioni":
            _df_from_rows(
                region_rows,
                [
                    "REGIONE",
                    "GRADO"
                ]
            ),

        "nazionale":
            _df_from_rows(
                national_rows,
                [
                    "NAZIONE",
                    "GRADO"
                ]
            )
    }
        
# datasets = parse_descrittore_21a2(dat)

# df_scuole = datasets["scuole"]
# df_province = datasets["province"]
# df_regioni = datasets["regioni"]
# df_nazionale = datasets["nazionale"]