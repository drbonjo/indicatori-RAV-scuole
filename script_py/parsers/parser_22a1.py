# -*- coding: utf-8 -*-
"""
Created on Fri Sep 11 15:47:08 2026

@author: imore
"""

# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import re
import pandas as pd


OUTPUT_COLS_22A1 = [
    "CODICEISTITUTO",
    "descrittore",

    "GRADO",
    "ANNO_CORSO",
    "PROVA",

    "LIVELLO",
    "TRACK",

    "CODICEMECCANOGRAFICO",
    "SEZIONE",

    "PUNTEGGIO",
    "PERC_PARTECIPAZIONE",

    "DIFF_ESCS",
    "PERC_COPERTURA_BACKGROUND",

    "RIF_REGIONE_NOME",
    "RIF_REGIONE",

    "RIF_MACROAREA_NOME",
    "RIF_MACROAREA",

    "RIF_PAESE_NOME",
    "RIF_PAESE",

    "ETICHETTA",

    "TABELLA_N",
    "RIGA_N"
]


def _clean_html_text(node):
    """
    Estrae il testo eliminando spazi,
    newline e tabulazioni ridondanti.
    """
    return re.sub(
        r"\s+",
        " ",
        node.get_text(" ", strip=True)
    ).strip()


def _to_float(value):
    """
    Converte i valori numerici in float.

    Esempi:
        '83,5'  -> 83.5
        '67.50' -> 67.5
        '100,0' -> 100.0
        'n.d.'  -> None
        'n.a.'  -> None
    """

    if value is None:
        return None

    value = re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()

    if not value:
        return None

    if value.casefold() in {
        "n.d.",
        "n.d",
        "nd",
        "n.a.",
        "n.a",
        "na",
        "-",
        "--"
    }:
        return None

    value = value.replace("%", "").strip()

    # caso tipo 1.234,5
    if "," in value and "." in value:

        value = (
            value
            .replace(".", "")
            .replace(",", ".")
        )

    # caso tipo 83,5
    elif "," in value:

        value = value.replace(",", ".")

    try:
        return float(value)

    except ValueError:
        return None


def _split_grado_anno(label):
    """
    Esempio:

    'Scuola primaria - classi seconde'

    diventa:

        GRADO       = 'Scuola primaria'
        ANNO_CORSO  = 'classi seconde'
    """

    parts = re.split(
        r"\s+-\s+",
        label,
        maxsplit=1
    )

    if (
        len(parts) == 2
        and parts[1].casefold().startswith("class")
    ):
        return (
            parts[0].strip(),
            parts[1].strip()
        )

    return label.strip(), None


def _strip_anno_suffix(label):
    """
    Esempio:

    'Istituti Tecnici - classi seconde'

    diventa:

    'Istituti Tecnici'
    """

    return re.sub(
        r"\s+-\s+classi?\s+.+$",
        "",
        label,
        flags=re.I
    ).strip()


def _metric_key(label):
    """
    Traduce le intestazioni HTML nei nomi
    delle colonne del dataset.
    """

    text = label.casefold()

    if "punteggio medio" in text:
        return "PUNTEGGIO"

    if "percentuale di partecipazione" in text:
        return "PERC_PARTECIPAZIONE"

    if (
        "diff." in text
        and "escs" in text
    ):
        return "DIFF_ESCS"

    if "copertura background" in text:
        return "PERC_COPERTURA_BACKGROUND"

    return None


def parse_descrittore_22a1(
    dat,
    descrittore="2.2.a.1"
):
    """
    Parser del descrittore 2.2.a.1.

    Produce un unico DataFrame con dati:

        grado / track
        plesso
        classe / sezione

    distinti per:

        anno di corso
        prova

    e conserva i riferimenti numerici:

        regione
        macro-area
        Italia

    Gestisce:

        - tabelle con solo dato aggregato;
        - tabelle con plessi;
        - tabelle con sezioni/classi;
        - tabelle con più track;
        - colonne ESCS opzionali;
        - riferimenti diversi per ciascun track.
    """

    rows = []

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

        for table_no, table in enumerate(
            soup.find_all(
                "table",
                class_="tableDsc"
            ),
            start=1
        ):

            trs = table.find_all("tr")

            if not trs:
                continue

            # ==================================================
            # TROVA TUTTE LE INTESTAZIONI DEI BLOCCHI
            #
            # In una stessa tabella possono esserci più track.
            # Per esempio:
            #
            # Licei ...
            # Istituti Tecnici ...
            #
            # ciascuno con propri riferimenti.
            # ==================================================

            header_positions = []

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

                first = texts[0].casefold()

                if first.startswith(
                    "istituto/plesso"
                ):
                    header_positions.append(i)

            if not header_positions:
                continue

            # ==================================================
            # GRADO + ANNO DI CORSO + PROVA
            # ==================================================

            top_labels = []

            for tr in trs[:header_positions[0]]:

                cells = tr.find_all(
                    ["th", "td"],
                    recursive=False
                )

                texts = [
                    _clean_html_text(cell)
                    for cell in cells
                ]

                texts = [
                    x
                    for x in texts
                    if x
                ]

                if len(texts) == 1:
                    top_labels.append(
                        texts[0]
                    )

            if len(top_labels) < 2:
                continue

            grado_anno = top_labels[0]
            prova = top_labels[1]

            grado, anno_corso = (
                _split_grado_anno(
                    grado_anno
                )
            )

            # ==================================================
            # CICLO SUI BLOCCHI INTERNI ALLA TABELLA
            # ==================================================

            for block_no, header_idx in enumerate(
                header_positions
            ):

                if (
                    block_no + 1
                    < len(header_positions)
                ):
                    block_end = (
                        header_positions[
                            block_no + 1
                        ]
                    )

                else:
                    block_end = len(trs)

                # ==============================================
                # COLONNE DEL BLOCCO
                # ==============================================

                header_cells = (
                    trs[header_idx]
                    .find_all(
                        ["th", "td"],
                        recursive=False
                    )
                )

                header_texts = [
                    _clean_html_text(cell)
                    for cell in header_cells
                ]

                metric_labels = []

                for text in header_texts[1:]:

                    if (
                        text.casefold()
                        == "riferimenti"
                    ):
                        break

                    metric_labels.append(
                        text
                    )

                metric_keys = [
                    _metric_key(text)
                    for text in metric_labels
                ]

                # ==============================================
                # RIFERIMENTI
                #
                # Regione
                # Macro-area
                # Italia
                # ==============================================

                ref_labels = None
                ref_values = None
                data_start = None

                for i in range(
                    header_idx + 1,
                    block_end
                ):

                    cells = trs[i].find_all(
                        ["th", "td"],
                        recursive=False
                    )

                    texts = [
                        _clean_html_text(cell)
                        for cell in cells
                    ]

                    if (
                        len(texts) == 3
                        and all(texts)
                        and all(
                            x.casefold().startswith(
                                "punteggio"
                            )
                            for x in texts
                        )
                    ):

                        ref_labels = texts

                        # riga successiva:
                        # valori numerici dei riferimenti

                        for j in range(
                            i + 1,
                            block_end
                        ):

                            cells_values = (
                                trs[j]
                                .find_all(
                                    ["th", "td"],
                                    recursive=False
                                )
                            )

                            texts_values = [
                                _clean_html_text(
                                    cell
                                )
                                for cell
                                in cells_values
                            ]

                            if (
                                len(texts_values) == 3
                                and any(texts_values)
                            ):

                                ref_values = (
                                    texts_values
                                )

                                data_start = j + 1

                                break

                        break

                if (
                    ref_labels is None
                    or ref_values is None
                    or data_start is None
                ):
                    continue

                ref_names = [
                    re.sub(
                        r"(?i)^Punteggio\s+",
                        "",
                        x
                    ).strip()
                    for x in ref_labels
                ]

                riferimenti = {

                    "RIF_REGIONE_NOME":
                        ref_names[0],

                    "RIF_REGIONE":
                        _to_float(
                            ref_values[0]
                        ),

                    "RIF_MACROAREA_NOME":
                        ref_names[1],

                    "RIF_MACROAREA":
                        _to_float(
                            ref_values[1]
                        ),

                    "RIF_PAESE_NOME":
                        "Italia",

                    "RIF_PAESE":
                        _to_float(
                            ref_values[2]
                        )
                }

                # ==============================================
                # LETTURA DELLE RIGHE DATI
                # ==============================================

                current_track = None
                row_no = 0

                for i in range(
                    data_start,
                    block_end
                ):

                    cells = trs[i].find_all(
                        ["th", "td"],
                        recursive=False
                    )

                    texts = [
                        _clean_html_text(cell)
                        for cell in cells
                    ]

                    if not texts:
                        continue

                    if not texts[0]:
                        continue

                    label = texts[0].strip()

                    # righe tecniche / intestazioni
                    if (
                        label.casefold()
                        .startswith(
                            "istituto/plesso"
                        )
                    ):
                        continue

                    if (
                        label.casefold()
                        .startswith(
                            "punteggio "
                        )
                    ):
                        continue

                    # ==========================================
                    # VALORI DELLE METRICHE
                    # ==========================================

                    values = texts[
                        1:
                        1 + len(metric_keys)
                    ]

                    if (
                        len(values)
                        < len(metric_keys)
                    ):
                        continue

                    metrics = {
                        "PUNTEGGIO":
                            None,

                        "PERC_PARTECIPAZIONE":
                            None,

                        "DIFF_ESCS":
                            None,

                        "PERC_COPERTURA_BACKGROUND":
                            None
                    }

                    for key, value in zip(
                        metric_keys,
                        values
                    ):

                        if key is not None:

                            metrics[key] = (
                                _to_float(
                                    value
                                )
                            )

                    # ==========================================
                    # TIPO DI RIGA
                    # ==========================================

                    codice_meccanografico = None
                    sezione = None

                    # ------------------------------------------
                    # PLESSO / CLASSE
                    # ------------------------------------------

                    if re.match(
                        r"(?i)^Plesso\b",
                        label
                    ):

                        match_plesso = re.match(
                            (
                                r"(?i)^Plesso\s+"
                                r"([A-Z0-9]+)"
                                r"(?:\s*-\s*"
                                r"Sezione\s+(.+))?$"
                            ),
                            label
                        )

                        if match_plesso:

                            codice_meccanografico = (
                                match_plesso
                                .group(1)
                                .strip()
                            )

                            if match_plesso.group(2):

                                sezione = (
                                    match_plesso
                                    .group(2)
                                    .strip()
                                )

                        if sezione:
                            livello = "classe"

                        else:
                            livello = "plesso"

                        track = current_track

                    # ------------------------------------------
                    # AGGREGATO DI GRADO
                    # ------------------------------------------

                    elif (
                        label.casefold()
                        == grado_anno.casefold()
                    ):

                        livello = "grado"

                        current_track = None
                        track = None

                    # ------------------------------------------
                    # AGGREGATO DI TRACK
                    # ------------------------------------------

                    else:

                        livello = "track"

                        current_track = (
                            _strip_anno_suffix(
                                label
                            )
                        )

                        track = current_track

                    row_no += 1

                    # ==========================================
                    # OUTPUT
                    # ==========================================

                    rows.append({

                        "CODICEISTITUTO":
                            codice_istituto,

                        "descrittore":
                            descrittore,

                        "GRADO":
                            grado,

                        "ANNO_CORSO":
                            anno_corso,

                        "PROVA":
                            prova,

                        "LIVELLO":
                            livello,

                        "TRACK":
                            track,

                        "CODICEMECCANOGRAFICO":
                            codice_meccanografico,

                        "SEZIONE":
                            sezione,

                        **metrics,

                        **riferimenti,

                        # conserviamo anche il testo originale
                        "ETICHETTA":
                            label,

                        # servono per non perdere
                        # eventuali righe duplicate reali
                        "TABELLA_N":
                            table_no,

                        "RIGA_N":
                            row_no
                    })

    # ==========================================================
    # DESCRITTORE ASSENTE
    # ==========================================================

    if found == 0:

        print(
            f"descrittore "
            f"{descrittore} "
            f"non trovato"
        )

    # ==========================================================
    # OUTPUT
    # ==========================================================

    if not rows:

        return pd.DataFrame(
            columns=OUTPUT_COLS_22A1
        )

    return (
        pd.DataFrame(rows)
        [OUTPUT_COLS_22A1]
    )