# -*- coding: utf-8 -*-
"""
Renderer interattivo per i file JSONL prodotti dallo scraper SNV.

Funzioni:
- permette di scegliere una cartella dati tra le sottocartelle di ROOT_DIR;
- legge automaticamente tutti i *.jsonl presenti nella cartella scelta;
- menu a tendina per la scelta del file/scuola;
- menu a tendina per la scelta della riga/descrittore;
- mostra informazioni sintetiche sulla riga selezionata;
- estrae il campo "html";
- crea un file HTML locale nella sottocartella render della cartella dati;
- apre il render nel browser predefinito;
- salva il codice HTML grezzo in ROOT_DIR/templates come CODICESCUOLA_DESCRITTORE.txt.
"""

from pathlib import Path
import html as html_lib
import json
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
import os

# ==============================================================
# CONFIGURAZIONE
# ==============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]
os.chdir(ROOT_DIR)

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


# ==============================================================
# HTML
# ==============================================================

def build_document(html_fragment, record, line_number):
    """
    Inserisce il frammento HTML in una pagina completa e leggibile.
    """

    scuola = str(
        record.get("scuola", "")
    )

    descrittore = str(
        record.get("descrittore", "")
    )

    gruppo = str(
        record.get("gruppo", "")
    )

    status = record.get(
        "status",
        ""
    )

    funzione = str(
        record.get("funzione", "")
    )

    safe_scuola = html_lib.escape(scuola)
    safe_descrittore = html_lib.escape(descrittore)
    safe_gruppo = html_lib.escape(gruppo)
    safe_funzione = html_lib.escape(funzione)
    safe_status = html_lib.escape(str(status))

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">

<title>{safe_scuola} - {safe_descrittore}</title>

<style>
    body {{
        font-family: Arial, sans-serif;
        margin: 30px;
        line-height: 1.35;
    }}

    table {{
        border-collapse: collapse;
        margin-top: 15px;
        margin-bottom: 30px;
        max-width: 100%;
    }}

    th, td {{
        padding: 7px 10px;
        border: 1px solid #777;
    }}

    th {{
        font-weight: bold;
    }}

    .render-info {{
        margin-bottom: 25px;
        padding: 12px;
        border: 1px solid #aaa;
        background: #f5f5f5;
    }}

    .render-info div {{
        margin: 3px 0;
    }}
</style>

</head>

<body>

<div class="render-info">
    <div><strong>Riga JSONL:</strong> {line_number}</div>
    <div><strong>Scuola:</strong> {safe_scuola}</div>
    <div><strong>Gruppo:</strong> {safe_gruppo}</div>
    <div><strong>Descrittore:</strong> {safe_descrittore}</div>
    <div><strong>Funzione:</strong> {safe_funzione}</div>
    <div><strong>Status:</strong> {safe_status}</div>
</div>

{html_fragment}

</body>
</html>
"""


def safe_filename_piece(value):
    value = str(value).strip()

    if not value:
        return "NA"

    for char in '<>:"/\\|?*':
        value = value.replace(char, "_")

    return value.replace(".", "_")


def safe_template_filename_piece(value):
    """
    Rende sicura una parte del nome file mantenendo i punti.

    Esempio:
        2.2.a.1 -> 2.2.a.1
    """
    value = str(value).strip()

    if not value:
        return "NA"

    for char in '<>:"/\\|?*':
        value = value.replace(char, "_")

    # Windows non consente nomi che terminano con spazio o punto
    value = value.rstrip(" .")

    return value or "NA"


def save_html_template(record, templates_dir=None):
    """
    Salva il codice HTML grezzo del record in ROOT_DIR/_templates. (contenuto in .gitignore)

    Il nome file è:
        CODICESCUOLA_DESCRITTORE.txt

    Esempio:
        VCIS02100Q_2.2.a.1.txt

    Se il file esiste già viene sovrascritto.
    """
    if "html" not in record:
        raise KeyError(
            "La riga selezionata non contiene il campo 'html'."
        )

    html_fragment = record["html"]

    if html_fragment is None:
        raise ValueError(
            "Il campo 'html' della riga selezionata è None."
        )

    html_fragment = str(html_fragment)

    if not html_fragment.strip():
        raise ValueError(
            "Il campo 'html' della riga selezionata è vuoto."
        )

    scuola = record.get("scuola", "scuola")
    descrittore = record.get("descrittore", "descrittore")

    if templates_dir is None:
        templates_dir = ROOT_DIR / "_templates"
    else:
        templates_dir = Path(templates_dir)

    templates_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        templates_dir
        / (
            f"{safe_template_filename_piece(scuola)}_"
            f"{safe_template_filename_piece(descrittore)}.txt"
        )
    )

    output_path.write_text(
        html_fragment,
        encoding="utf-8"
    )

    return output_path


def render_record(record, line_number, render_dir):
    """
    Crea il file HTML locale e lo apre nel browser predefinito.
    """
    render_dir = Path(render_dir)

    if "html" not in record:
        raise KeyError(
            "La riga selezionata non contiene il campo 'html'."
        )

    html_fragment = record["html"]

    if html_fragment is None:
        raise ValueError(
            "Il campo 'html' della riga selezionata è None."
        )

    html_fragment = str(html_fragment)

    if not html_fragment.strip():
        raise ValueError(
            "Il campo 'html' della riga selezionata è vuoto."
        )

    scuola = record.get(
        "scuola",
        "scuola"
    )

    descrittore = record.get(
        "descrittore",
        f"riga_{line_number}"
    )

    document = build_document(
        html_fragment,
        record,
        line_number
    )

    render_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        render_dir
        / (
            f"{safe_filename_piece(scuola)}_"
            f"{safe_filename_piece(descrittore)}_"
            f"riga_{line_number}.html"
        )
    )

    output_path.write_text(
        document,
        encoding="utf-8"
    )

    webbrowser.open(
        output_path.resolve().as_uri()
    )

    return output_path


# ==============================================================
# GUI
# ==============================================================

class RendererApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "SNV JSONL Renderer"
        )

        self.root.geometry(
            "900x500"
        )

        self.data_dirs = []
        self.data_dir = None
        self.json_files = []
        self.current_rows = []

        self.data_var = tk.StringVar()
        self.file_var = tk.StringVar()
        self.row_var = tk.StringVar()

        self.info_var = tk.StringVar(
            value="Seleziona una cartella dati."
        )

        self.path_var = tk.StringVar(
            value=f"Root: {ROOT_DIR}"
        )

        self.build_ui()
        self.refresh_data_dirs()


    def build_ui(self):

        main = ttk.Frame(
            self.root,
            padding=18
        )

        main.pack(
            fill="both",
            expand=True
        )

        # ------------------------------------------------------
        # Percorso root
        # ------------------------------------------------------

        ttk.Label(
            main,
            textvariable=self.path_var
        ).pack(
            anchor="w",
            pady=(0, 16)
        )

        # ------------------------------------------------------
        # Cartella dati
        # ------------------------------------------------------

        ttk.Label(
            main,
            text="Cartella dati:"
        ).pack(
            anchor="w"
        )

        data_frame = ttk.Frame(main)

        data_frame.pack(
            fill="x",
            pady=(5, 16)
        )

        self.data_combo = ttk.Combobox(
            data_frame,
            textvariable=self.data_var,
            state="readonly"
        )

        self.data_combo.pack(
            side="left",
            fill="x",
            expand=True
        )

        self.data_combo.bind(
            "<<ComboboxSelected>>",
            self.on_data_dir_selected
        )

        ttk.Button(
            data_frame,
            text="Aggiorna cartelle",
            command=self.refresh_data_dirs
        ).pack(
            side="left",
            padx=(8, 0)
        )

        # ------------------------------------------------------
        # File JSONL
        # ------------------------------------------------------

        ttk.Label(
            main,
            text="File JSONL:"
        ).pack(
            anchor="w"
        )

        file_frame = ttk.Frame(main)

        file_frame.pack(
            fill="x",
            pady=(5, 16)
        )

        self.file_combo = ttk.Combobox(
            file_frame,
            textvariable=self.file_var,
            state="readonly"
        )

        self.file_combo.pack(
            side="left",
            fill="x",
            expand=True
        )

        self.file_combo.bind(
            "<<ComboboxSelected>>",
            self.on_file_selected
        )

        ttk.Button(
            file_frame,
            text="Aggiorna",
            command=self.refresh_files
        ).pack(
            side="left",
            padx=(8, 0)
        )

        # ------------------------------------------------------
        # Riga
        # ------------------------------------------------------

        ttk.Label(
            main,
            text="Riga / descrittore:"
        ).pack(
            anchor="w"
        )

        self.row_combo = ttk.Combobox(
            main,
            textvariable=self.row_var,
            state="readonly"
        )

        self.row_combo.pack(
            fill="x",
            pady=(5, 16)
        )

        self.row_combo.bind(
            "<<ComboboxSelected>>",
            self.on_row_selected
        )

        # ------------------------------------------------------
        # Informazioni
        # ------------------------------------------------------

        info_frame = ttk.LabelFrame(
            main,
            text="Informazioni",
            padding=12
        )

        info_frame.pack(
            fill="both",
            expand=True,
            pady=(0, 16)
        )

        self.info_label = ttk.Label(
            info_frame,
            textvariable=self.info_var,
            justify="left",
            anchor="nw"
        )

        self.info_label.pack(
            fill="both",
            expand=True
        )

        # ------------------------------------------------------
        # Render
        # ------------------------------------------------------

        button_frame = ttk.Frame(main)

        button_frame.pack(
            fill="x"
        )

        self.render_button = ttk.Button(
            button_frame,
            text="Render HTML",
            command=self.render_selected,
            state="disabled"
        )

        self.render_button.pack(
            side="right"
        )

        self.template_button = ttk.Button(
            button_frame,
            text="Salva template TXT",
            command=self.save_selected_template,
            state="disabled"
        )

        self.template_button.pack(
            side="right",
            padx=(0, 8)
        )


    def refresh_data_dirs(self):

        try:
            self.data_dirs = list_data_dirs()

        except Exception as exc:

            messagebox.showerror(
                "Errore",
                str(exc)
            )

            return

        names = [
            path.name
            for path in self.data_dirs
        ]

        self.data_combo["values"] = names
        self.data_var.set("")

        self.data_dir = None
        self.path_var.set(
            f"Root: {ROOT_DIR}"
        )

        self.file_combo["values"] = []
        self.file_var.set("")
        self.row_combo["values"] = []
        self.row_var.set("")

        self.json_files = []
        self.current_rows = []

        self.render_button.configure(
            state="disabled"
        )

        self.template_button.configure(
            state="disabled"
        )

        if not names:
            self.info_var.set(
                "Nessuna sottocartella trovata nella root."
            )
        else:
            self.info_var.set(
                f"Trovate {len(names)} cartelle. Seleziona la cartella dati."
            )


    def on_data_dir_selected(self, event=None):

        index = self.data_combo.current()

        if index < 0:
            return

        self.data_dir = self.data_dirs[index]

        self.path_var.set(
            f"Cartella dati: {self.data_dir}"
        )

        self.refresh_files()


    def refresh_files(self):

        if self.data_dir is None:
            self.info_var.set(
                "Seleziona prima una cartella dati."
            )
            return

        try:
            self.json_files = (
                list_jsonl_files(self.data_dir)
            )

        except Exception as exc:

            messagebox.showerror(
                "Errore",
                str(exc)
            )

            return

        names = [
            path.name
            for path in self.json_files
        ]

        self.file_combo["values"] = names

        self.file_var.set("")
        self.row_var.set("")

        self.row_combo["values"] = []

        self.current_rows = []

        self.render_button.configure(
            state="disabled"
        )

        self.template_button.configure(
            state="disabled"
        )

        if not names:
            self.info_var.set(
                f"Nessun file .jsonl trovato in {self.data_dir.name}."
            )

        else:
            self.info_var.set(
                f"Trovati {len(names)} file JSONL in {self.data_dir.name}."
            )


    def on_file_selected(self, event=None):

        index = self.file_combo.current()

        if index < 0:
            return

        path = self.json_files[index]

        try:
            self.current_rows = (
                read_jsonl(path)
            )

        except Exception as exc:

            messagebox.showerror(
                "Errore lettura JSONL",
                str(exc)
            )

            return

        labels = []

        valid_count = 0
        invalid_count = 0

        for item in self.current_rows:

            line_number = item[
                "line_number"
            ]

            if item["error"]:

                invalid_count += 1

                label = (
                    f"{line_number:03d} | "
                    f"ERRORE JSON | "
                    f"{item['error']}"
                )

            else:

                valid_count += 1

                record = item[
                    "record"
                ]

                descriptor = record.get(
                    "descrittore",
                    "?"
                )

                status = record.get(
                    "status",
                    "?"
                )

                html_field = record.get(
                    "html"
                )

                if html_field is None:
                    html_chars = 0
                else:
                    html_chars = len(
                        str(html_field)
                    )

                label = (
                    f"{line_number:03d} | "
                    f"{descriptor} | "
                    f"status={status} | "
                    f"html={html_chars} chars"
                )

            labels.append(label)

        self.row_combo[
            "values"
        ] = labels

        self.row_var.set("")

        self.render_button.configure(
            state="disabled"
        )

        self.template_button.configure(
            state="disabled"
        )

        self.info_var.set(
            (
                f"File: {path.name}\n"
                f"Righe totali: {len(self.current_rows)}\n"
                f"Righe JSON valide: {valid_count}\n"
                f"Righe non valide: {invalid_count}"
            )
        )


    def on_row_selected(self, event=None):

        index = self.row_combo.current()

        if index < 0:
            return

        item = self.current_rows[
            index
        ]

        if item["error"]:

            self.info_var.set(
                (
                    f"Riga: {item['line_number']}\n"
                    f"Errore: {item['error']}"
                )
            )

            self.render_button.configure(
                state="disabled"
            )

            self.template_button.configure(
                state="disabled"
            )

            return

        record = item[
            "record"
        ]

        html_field = record.get(
            "html"
        )

        html_chars = (
            0
            if html_field is None
            else len(str(html_field))
        )

        self.info_var.set(
            (
                f"Riga: {item['line_number']}\n"
                f"Scuola: {record.get('scuola', '')}\n"
                f"Gruppo: {record.get('gruppo', '')}\n"
                f"Descrittore: {record.get('descrittore', '')}\n"
                f"Funzione: {record.get('funzione', '')}\n"
                f"HTTP status: {record.get('status', '')}\n"
                f"Content-Type: {record.get('content_type', '')}\n"
                f"Caratteri HTML: {html_chars}"
            )
        )

        if (
            html_field is not None
            and str(html_field).strip()
        ):
            self.render_button.configure(
                state="normal"
            )

            self.template_button.configure(
                state="normal"
            )

        else:
            self.render_button.configure(
                state="disabled"
            )

            self.template_button.configure(
                state="disabled"
            )


    def save_selected_template(self):

        index = self.row_combo.current()

        if index < 0:
            messagebox.showwarning(
                "Nessuna riga",
                "Seleziona una riga."
            )
            return

        item = self.current_rows[index]

        if item["error"]:
            messagebox.showerror(
                "Riga non valida",
                item["error"]
            )
            return

        try:
            output_path = save_html_template(
                item["record"],
                ROOT_DIR / "_templates"
            )

            self.info_var.set(
                self.info_var.get()
                + "\n"
                + f"Template TXT: {output_path}"
            )

        except Exception as exc:
            messagebox.showerror(
                "Errore salvataggio template",
                f"{type(exc).__name__}: {exc}"
            )


    def render_selected(self):

        index = self.row_combo.current()

        if index < 0:
            messagebox.showwarning(
                "Nessuna riga",
                "Seleziona una riga."
            )
            return

        item = self.current_rows[
            index
        ]

        if item["error"]:
            messagebox.showerror(
                "Riga non valida",
                item["error"]
            )
            return

        try:

            if self.data_dir is None:
                raise RuntimeError(
                    "Nessuna cartella dati selezionata."
                )

            output_path = render_record(
                item["record"],
                item["line_number"],
                self.data_dir / "render"
            )

            self.info_var.set(
                self.info_var.get()
                + "\n"
                + f"Render: {output_path}"
            )

        except Exception as exc:

            messagebox.showerror(
                "Errore render",
                f"{type(exc).__name__}: {exc}"
            )


def main():

    root = tk.Tk()

    app = RendererApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
