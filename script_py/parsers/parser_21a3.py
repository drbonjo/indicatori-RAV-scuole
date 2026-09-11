# -*- coding: utf-8 -*-
"""
Created on Fri Sep 11 15:17:02 2026

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


def _is_vote_label(value):
    """
    Verifica se una stringa rappresenta una categoria
    di votazione prevista dal descrittore 2.1.a.3.

    Esempi:
        6
        7
        60
        61-70
        91-100
        Lode
        100 e Lode
    """

    value = value.strip().casefold()

    if not value:
        return False

    if value == "lode":
        return True

    if value == "100 e lode":
        return True

    if re.fullmatch(r"\d+", value):
        return True

    if re.fullmatch(r"\d+\s*-\s*\d+", value):
        return True

    return False


def parse_descrittore_21a3(
    dat,
    descrittore="2.1.a.3"
):
    """
    Parser del descrittore 2.1.a.3.

    Gestisce entrambi i formati:

    FORMATO 1
    ----------
    Scientifico
    Votazione | 60 | 61-70 | ... | 100 e Lode

    FORMATO 2
    ----------
    Votazione
              | 6 | 7 | 8 | 9 | 10 | Lode

    Produce quattro DataFrame:

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

            votazioni = None
            header_idx = None
            grado = None

            # ==================================================
            # INDIVIDUA LA RIGA DELLE VOTAZIONI
            #
            # Funziona sia con:
            #
            # Votazione | 60 | 61-70 | ...
            #
            # sia con:
            #
            #           | 6 | 7 | 8 | ...
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

                if len(texts) < 2:
                    continue

                vote_labels = texts[1:]

                if (
                    vote_labels
                    and all(
                        _is_vote_label(x)
                        for x in vote_labels
                    )
                ):
                    votazioni = vote_labels
                    header_idx = i
                    break

            # tabella non riconosciuta
            if header_idx is None:
                continue

            # ==================================================
            # DETERMINA IL TIPO DI TABELLA / GRADO
            # ==================================================

            previous_text = None

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
                    previous_text = " ".join(texts).strip()
                    break

            # --------------------------------------------------
            # FORMATO SECONDARIA I GRADO
            #
            # La riga precedente contiene soltanto:
            #     Votazione
            #
            # e le categorie sono 6-10 + Lode.
            # --------------------------------------------------

            if (
                previous_text is not None
                and previous_text.casefold() == "votazione"
            ):

                grado = "Scuola secondaria di I grado"

            # --------------------------------------------------
            # FORMATO SECONDARIA II GRADO
            #
            # La riga precedente contiene:
            #
            # Scientifico
            # Scientifico - Opz. Scienze Applicate
            # Tecnico Tecnologico
            # ecc.
            # --------------------------------------------------

            else:

                grado = previous_text

            if grado is None:
                continue

            # ==================================================
            # LETTURA RIGHE DATI
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
                # RIFERIMENTI
                # ------------------------------------------------

                if label.casefold() == "riferimenti":

                    in_riferimenti = True
                    continue

                # deve esserci:
                #
                # 1 identificativo
                # +
                # N votazioni

                if len(texts) != len(votazioni) + 1:
                    continue

                valori = texts[1:]

                dati = dict(
                    zip(
                        votazioni,
                        valori
                    )
                )

                # ==================================================
                # SCUOLA
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

                # Provincia, regione e Italia
                # devono essere nel blocco Riferimenti

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
                # ==================================================

                region_rows.append({
                    "REGIONE":
                        label,

                    "GRADO":
                        grado,

                    **dati
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