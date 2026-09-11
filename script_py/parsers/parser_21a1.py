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


def parse_descrittore_21a1(
    dat,
    descrittore="2.1.a.1"
):
    """
    Cerca in dat tutti i record con:

        record["descrittore"] == "2.1.a.1"

    Per tutte le tabelle presenti in record["html"] estrae:

        - dati scuola/plesso
        - dati provincia
        - dati regione
        - dati Italia

    Restituisce quattro DataFrame.
    """

    school_rows = []
    province_rows = []
    region_rows = []
    national_rows = []

    found = 0

    # ==========================================================
    # CERCA IL RECORD DEL DESCRITTORE
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

        # ======================================================
        # PARSING HTML
        # ======================================================

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # tutte le tabelle del descrittore
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
            
                class_labels = [
                    x for x in texts
                    if x.lower().startswith("classe ")
                ]
            
                if class_labels:
            
                    classi = class_labels
                    header_idx = i
                    break
            
            
            # tabella non riconosciuta
            if header_idx is None:
                continue
            
            
            # ==================================================
            # INDIVIDUA GRADO / INDIRIZZO
            #
            # Prende la prima riga non vuota precedente
            # alla riga delle classi.
            #
            # Funziona sia con:
            #   Scuola primaria
            #   Scuola secondaria di I grado
            # sia con:
            #   Scientifico
            #   Scientifico - Scienze Applicate
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
            
                if texts:
                    grado = " ".join(texts).strip()
                    break
            
            
            if grado is None:
                continue

            if classi is None:
                continue

            # ==================================================
            # LETTURA DELLE RIGHE
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

                # ----------------------------------------------
                # inizio blocco riferimenti
                # ----------------------------------------------

                if label.casefold() == "riferimenti":
                    in_riferimenti = True
                    continue

                # deve esserci una colonna descrittiva +
                # una colonna per ogni classe
                if len(texts) != len(classi) + 1:
                    continue

                valori = texts[1:]

                dati = dict(
                    zip(
                        classi,
                        valori
                    )
                )

                # ==============================================
                # SCUOLA / PLESSO
                #
                # "Situazione della scuola AP1E005007"
                # ==============================================

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

                # le righe geografiche devono stare
                # dopo "Riferimenti"
                if not in_riferimenti:
                    continue

                # ==============================================
                # PROVINCIA
                # ==============================================

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

                # ==============================================
                # ITALIA
                # ==============================================

                elif label.casefold() == "italia":

                    national_rows.append({
                        "NAZIONE":
                            label,

                        "GRADO":
                            grado,

                        **dati
                    })

                # ==============================================
                # REGIONE
                #
                # nel formato attuale è la riga rimanente
                # all'interno dei riferimenti
                # ==============================================

                else:

                    region_rows.append({
                        "REGIONE":
                            label,

                        "GRADO":
                            grado,

                        **dati
                    })

    # ==========================================================
    # CONTROLLO
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
        
