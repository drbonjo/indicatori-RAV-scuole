# -*- coding: utf-8 -*-
"""
Created on Fri Sep 11 12:53:49 2026

@author: imore
"""

import json 
from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parents[1]
os.chdir(ROOT_DIR)
DATA_DIR = ROOT_DIR / "data_1"

from script_py.parsers.parser_21a1 import *
from script_py.parsers.parser_21a2 import *
from script_py.parsers.parser_21a3 import *
from script_py.parsers.parser_21b1 import *
from script_py.parsers.parser_21b2 import *
from script_py.parsers.parser_22a1 import *


# ==============================================================
# LETTURA JSONL
# ==============================================================

def list_data_dirs():
    """
    Restituisce le sottocartelle presenti direttamente in ROOT_DIR.
    """
    if not ROOT_DIR.exists():
        raise FileNotFoundError(
            f"Directory root non trovata:\n{ROOT_DIR}"
        )

    return sorted(
        [path for path in ROOT_DIR.iterdir() if path.is_dir()],
        key=lambda p: p.name.lower()
    )


def list_jsonl_files(data_dir):
    """
    Restituisce tutti i file .jsonl presenti direttamente nella cartella dati.
    """
    data_dir = Path(data_dir)

    if not data_dir.exists():
        raise FileNotFoundError(
            f"Cartella dati non trovata:\n{data_dir}"
        )

    return sorted(
        data_dir.glob("*.jsonl"),
        key=lambda p: p.name.lower()
    )


def read_jsonl(path):
    """
    Legge tutte le righe valide di un JSONL.

    Ogni elemento restituito contiene:
        line_number
        record
        error
    """
    rows = []

    with Path(path).open("r", encoding="utf-8") as f:

        for line_number, line in enumerate(f, start=1):

            stripped = line.strip()

            if not stripped:
                rows.append({
                    "line_number": line_number,
                    "record": None,
                    "error": "riga vuota",
                })
                continue

            try:
                record = json.loads(stripped)

                rows.append({
                    "line_number": line_number,
                    "record": record,
                    "error": None,
                })

            except Exception as exc:
                rows.append({
                    "line_number": line_number,
                    "record": None,
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                })

    return rows


json_list = [
    path.name
    for path in list_jsonl_files(DATA_DIR)
]
# Cominiciamo a ciclare ogni parser  
  
# datasets = parse_descrittore_21a1(dat)

# df_scuole = datasets["scuole"]
# df_province = datasets["province"]
# df_regioni = datasets["regioni"]
# df_nazionale = datasets["nazionale"]


def to_long(
    df,
    id_cols,
    descrittore
):
    """
    Converte un dataset prodotto dal parser in formato long.

    La colonna 'categoria' contiene la dimensione specifica
    del descrittore, ad esempio:

        Classe I
        Classe II
        60
        61-70
        Lode
        ecc.
    """

    if df.empty:
        return pd.DataFrame(
            columns=(
                id_cols
                + [
                    "categoria",
                    "valore",
                    "descrittore"
                ]
            )
        )

    return (
        df
        .melt(
            id_vars=id_cols,
            var_name="categoria",
            value_name="valore"
        )
        .dropna(
            subset=["valore"]
        )
        .assign(
            descrittore=descrittore
        )
    )



# ==============================================================
# ACCUMULATORI
# ==============================================================

scuole_all = []
province_all = []
regioni_all = []
nazionale_all = []
invalsi_22a1_all = []

# ==============================================================
# PARSER DA ESEGUIRE
# ==============================================================

parsers = [
    {
        "descrittore": "2.1.a.1",
        "parser": parse_descrittore_21a1
    }
    ,
    {
        "descrittore": "2.1.a.2",
        "parser": parse_descrittore_21a2
    }
    ,
    {
        "descrittore": "2.1.a.3",
        "parser": parse_descrittore_21a3
    }
    ,
    {
        "descrittore": "2.1.b.1",
        "parser": parse_descrittore_21b1
    }
    ,
    {
        "descrittore": "2.1.b.2",
        "parser": parse_descrittore_21b2
    }
]


# ==============================================================
# CICLO SU TUTTI I JSONL
# ==============================================================

for i, filename in enumerate(json_list, start=1):

    path = DATA_DIR / filename

    print(
        f"[{i}/{len(json_list)}] "
        f"{filename}"
    )

    # legge il JSONL
    dat = read_jsonl(path)
    
    # ==========================================================
    # DESCRITTORE 2.2.a.1 - INVALSI
    # dataset separato, NON passa da to_long()
    # ==========================================================
    
    df_22a1 = parse_descrittore_22a1(
        dat,
        descrittore="2.2.a.1"
    )
    
    if not df_22a1.empty:
        invalsi_22a1_all.append(
            df_22a1
        )

    # ==========================================================
    # CICLO SUI PARSER
    # ==========================================================

    for parser_info in parsers:

        descrittore = parser_info["descrittore"]
        parser_func = parser_info["parser"]

        try:

            datasets = parser_func(
                dat,
                descrittore=descrittore
            )

        except ValueError:

            print(
                f"descrittore {descrittore} "
                f"non trovato"
            )

            continue

        # ------------------------------------------------------
        # SCUOLE
        # ------------------------------------------------------

        df = to_long(
            datasets["scuole"],
            id_cols=[
                "CODICEISTITUTO",
                "CODICEMECCANOGRAFICO",
                "GRADO"
            ],
            descrittore=descrittore
        )

        if not df.empty:
            scuole_all.append(df)

        # ------------------------------------------------------
        # PROVINCE
        # ------------------------------------------------------

        df = to_long(
            datasets["province"],
            id_cols=[
                "PROVINCIA",
                "GRADO"
            ],
            descrittore=descrittore
        )

        if not df.empty:
            province_all.append(df)

        # ------------------------------------------------------
        # REGIONI
        # ------------------------------------------------------

        df = to_long(
            datasets["regioni"],
            id_cols=[
                "REGIONE",
                "GRADO"
            ],
            descrittore=descrittore
        )

        if not df.empty:
            regioni_all.append(df)

        # ------------------------------------------------------
        # NAZIONALE
        # ------------------------------------------------------

        df = to_long(
            datasets["nazionale"],
            id_cols=[
                "NAZIONE",
                "GRADO"
            ],
            descrittore=descrittore
        )

        if not df.empty:
            nazionale_all.append(df)


# ==============================================================
# CONCATENAZIONE FINALE
# ==============================================================

df_invalsi_22a1 = (
    pd.concat(
        invalsi_22a1_all,
        ignore_index=True
    )
    if invalsi_22a1_all
    else pd.DataFrame(
        columns=OUTPUT_COLS_22A1
    )
)


df_scuole_long = (
    pd.concat(
        scuole_all,
        ignore_index=True
    )
    if scuole_all
    else pd.DataFrame()
)

df_province_long = (
    pd.concat(
        province_all,
        ignore_index=True
    )
    if province_all
    else pd.DataFrame()
)

df_regioni_long = (
    pd.concat(
        regioni_all,
        ignore_index=True
    )
    if regioni_all
    else pd.DataFrame()
)

df_nazionale_long = (
    pd.concat(
        nazionale_all,
        ignore_index=True
    )
    if nazionale_all
    else pd.DataFrame()
)


# ==============================================================
# RIMOZIONE DUPLICATI TERRITORIALI
# ==============================================================

df_province_long = (
    df_province_long
    .drop_duplicates()
    .reset_index(drop=True)
)

df_regioni_long = (
    df_regioni_long
    .drop_duplicates()
    .reset_index(drop=True)
)

df_nazionale_long = (
    df_nazionale_long
    .drop_duplicates()
    .reset_index(drop=True)
)