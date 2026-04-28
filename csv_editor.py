#!/usr/bin/env python3
"""Enkel CSV-editor: åpne, redigere og lagre CSV-filer med komma som skilletegn."""

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class CSVEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSV Editor")
        self.geometry("900x600")

        self.current_path: str | None = None
        self.headers: list[str] = []
        self.rows: list[list[str]] = []

        self._build_menu()
        self._build_table()
        self._build_statusbar()

    def _build_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Åpne...", command=self.open_file, accelerator="Ctrl+O")
        filemenu.add_command(label="Lagre", command=self.save_file, accelerator="Ctrl+S")
        filemenu.add_command(label="Lagre som...", command=self.save_file_as)
        filemenu.add_separator()
        filemenu.add_command(label="Legg til rad", command=self.add_row)
        filemenu.add_command(label="Slett valgt rad", command=self.delete_row)
        filemenu.add_separator()
        filemenu.add_command(label="Avslutt", command=self.quit)
        menubar.add_cascade(label="Fil", menu=filemenu)
        self.config(menu=menubar)

        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())

    def _build_table(self):
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(frame, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_double_click)

    def _build_statusbar(self):
        self.status = tk.StringVar(value="Ingen fil åpnet")
        bar = ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken")
        bar.pack(side="bottom", fill="x")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Åpne CSV-fil",
            filetypes=[("CSV-filer", "*.csv"), ("Alle filer", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=",")
                data = list(reader)
        except UnicodeDecodeError:
            with open(path, newline="", encoding="latin-1") as f:
                reader = csv.reader(f, delimiter=",")
                data = list(reader)
        except Exception as exc:
            messagebox.showerror("Feil ved åpning", str(exc))
            return

        if not data:
            messagebox.showwarning("Tom fil", "CSV-filen er tom.")
            return

        self.current_path = path
        self.headers = data[0]
        self.rows = [list(r) for r in data[1:]]
        self._refresh_table()
        self.title(f"CSV Editor - {path}")
        self.status.set(f"Åpnet: {path}  ({len(self.rows)} rader, {len(self.headers)} kolonner)")

    def _refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        cols = [f"c{i}" for i in range(len(self.headers))]
        self.tree["columns"] = cols
        for i, name in enumerate(self.headers):
            self.tree.heading(cols[i], text=name)
            self.tree.column(cols[i], width=120, anchor="w", stretch=True)

        for row in self.rows:
            padded = row + [""] * (len(self.headers) - len(row))
            self.tree.insert("", "end", values=padded[: len(self.headers)])

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return

        col_index = int(col_id.replace("#", "")) - 1
        x, y, width, height = self.tree.bbox(row_id, col_id)
        current = self.tree.set(row_id, self.tree["columns"][col_index])

        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current)
        entry.focus_set()
        entry.select_range(0, "end")

        def commit(_event=None):
            new_value = entry.get()
            self.tree.set(row_id, self.tree["columns"][col_index], new_value)
            row_index = self.tree.index(row_id)
            while len(self.rows[row_index]) < len(self.headers):
                self.rows[row_index].append("")
            self.rows[row_index][col_index] = new_value
            entry.destroy()
            self.status.set(f"Endret rad {row_index + 1}, kolonne '{self.headers[col_index]}'")

        def cancel(_event=None):
            entry.destroy()

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", cancel)

    def add_row(self):
        if not self.headers:
            messagebox.showinfo("Ingen fil", "Åpne en CSV-fil først.")
            return
        new_row = [""] * len(self.headers)
        self.rows.append(new_row)
        self.tree.insert("", "end", values=new_row)
        self.status.set(f"La til rad ({len(self.rows)} rader totalt)")

    def delete_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Ingen valgt", "Velg en rad som skal slettes.")
            return
        for item in selected:
            idx = self.tree.index(item)
            self.tree.delete(item)
            del self.rows[idx]
        self.status.set(f"Slettet rad(er). {len(self.rows)} rader igjen.")

    def save_file(self):
        if not self.current_path:
            self.save_file_as()
            return
        self._write_csv(self.current_path)

    def save_file_as(self):
        if not self.headers:
            messagebox.showinfo("Ingenting å lagre", "Åpne en CSV-fil først.")
            return
        path = filedialog.asksaveasfilename(
            title="Lagre CSV som",
            defaultextension=".csv",
            filetypes=[("CSV-filer", "*.csv"), ("Alle filer", "*.*")],
        )
        if not path:
            return
        self.current_path = path
        self.title(f"CSV Editor - {path}")
        self._write_csv(path)

    def _write_csv(self, path: str):
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow(self.headers)
                writer.writerows(self.rows)
        except Exception as exc:
            messagebox.showerror("Feil ved lagring", str(exc))
            return
        self.status.set(f"Lagret: {path}")


if __name__ == "__main__":
    CSVEditor().mainloop()
