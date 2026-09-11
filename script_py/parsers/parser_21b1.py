# -*- coding: utf-8 -*-
"""
Created on Fri Sep 11 15:26:09 2026

@author: imore
"""

# -*- coding: utf-8 -*-

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
    Costruisce il DataFrame mettendo prima
    le colonne identificative.
    """
    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=id_cols)

    other_cols = [
        col for col in df.columns
        if col not in id_cols
    ]

    return df[id_cols + other_cols]


def _make_measure_data(classi, valori, misura):
    """
    Associa ciascun valore alla combinazione:

        Classe | Misura

    Esempi:
        Classe I | N
        Classe I | Percentuale
    """
    return {
        f"{classe} | {misura}": valore
        for classe, valore in zip(classi, valori)
    }


def parse_descrittore_21b1(
    dat,
    descrittore="2.1.b.1"
):
    """
    Parser del descrittore 2.1.b.1.

    Gestisce tabelle del tipo:

        Scuola primaria
        Situazione della scuola CODICE | Classe I | ... | Classe V
        N                            | ...
        Percentuale                  | ...
        Riferimenti
        Provincia                    | percentuali
        Regione                      | percentuali
        Italia                       | percentuali

    e analogamente tabelle relative agli indirizzi
    della secondaria di II grado.

    Restituisce quattro DataFrame:

        scuole
        province
        regioni
        nazionale
    """

    school_rows = []
    province_rows = []
    region_rows = []
    national_rows = []

    found = 0

    # ==========================================================
    # CICLO SUI RECORD
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
            codice_meccanografico = None
            header_idx = None

            # ==================================================
            # TROVA LA RIGA:
            #
            # Situazione della scuola CODICE
            # Classe I
            # Classe II
            # ...
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

                match_scuola = re.match(
                    r"(?i)^Situazione della scuola\s+(.+?)\s*$",
                    texts[0]
                )

                if not match_scuola:
                    continue

                codice_meccanografico = (
                    match_scuola
                    .group(1)
                    .strip()
                )

                classi = [
                    x.strip()
                    for x in texts[1:]
                    if x.strip()
                ]

                header_idx = i
                break

            if header_idx is None:
                continue

            if not classi:
                continue

            # ==================================================
            # TROVA GRADO / INDIRIZZO
            #
            # Prima riga non vuota precedente alla riga
            # "Situazione della scuola ..."
            #
            # Esempi:
            #   Scuola primaria
            #   Scuola secondaria di I grado
            #   SCIENTIFICO
            #   TECNICO TECNOLOGICO
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

                if texts:
                    grado = " ".join(texts).strip()
                    break

            if grado is None:
                continue

            # ==================================================
            # DATI DELLA SCUOLA
            #
            # Una singola unità scuola deve contenere sia
            # gli N sia le percentuali.
            # ==================================================

            school_data = {}

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
                # RIFERIMENTI
                # ------------------------------------------------

                if label.casefold() == "riferimenti":

                    in_riferimenti = True
                    continue

                # ------------------------------------------------
                # PRIMA DEI RIFERIMENTI:
                #
                # N
                # Percentuale
                # ------------------------------------------------

                if not in_riferimenti:

                    if len(texts) != len(classi) + 1:
                        continue

                    valori = texts[1:]

                    if label.casefold() == "n":

                        school_data.update(
                            _make_measure_data(
                                classi,
                                valori,
                                "N"
                            )
                        )

                        continue

                    if label.casefold() == "percentuale":

                        school_data.update(
                            _make_measure_data(
                                classi,
                                valori,
                                "Percentuale"
                            )
                        )

                        continue

                    continue

                # ------------------------------------------------
                # DOPO "RIFERIMENTI":
                #
                # Provincia
                # Regione
                # Italia
                #
                # sono tutte percentuali
                # ------------------------------------------------

                if len(texts) != len(classi) + 1:
                    continue

                valori = texts[1:]

                dati_percentuali = (
                    _make_measure_data(
                        classi,
                        valori,
                        "Percentuale"
                    )
                )

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

                        **dati_percentuali
                    })

                    continue

                # ==================================================
                # ITALIA
                # ==================================================

                if label.casefold() == "italia":

                    national_rows.append({
                        "NAZIONE":
                            "Italia",

                        "GRADO":
                            grado,

                        **dati_percentuali
                    })

                    continue

                # ==================================================
                # REGIONE
                # ==================================================

                region_rows.append({
                    "REGIONE":
                        label,

                    "GRADO":
                        grado,

                    **dati_percentuali
                })

            # ==================================================
            # SALVA LA RIGA DELLA SCUOLA
            # ==================================================

            if school_data:

                school_rows.append({
                    "CODICEISTITUTO":
                        codice_istituto,

                    "CODICEMECCANOGRAFICO":
                        codice_meccanografico,

                    "GRADO":
                        grado,

                    **school_data
                })

    # ==========================================================
    # DESCRITTORE ASSENTE
    # ==========================================================

    if found == 0:
        print(
            f"descrittore {descrittore} non trovato"
        )

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