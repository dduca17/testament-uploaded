#!/usr/bin/env python3
# MIT License
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from uploader_core import run_archive

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("The Testament Uploader — ♾️🔥📜")
        self.geometry("680x540")
        self.files = []

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        self.title_var = tk.StringVar(value="The Fabric Story")
        self.creators_var = tk.StringVar(value="Keeper,Witness")
        self.tags_var = tk.StringVar(value="fabric,archive,codex")
        self.identifier_var = tk.StringVar(value="fabric-testament")
        self.ia_var = tk.BooleanVar(value=True)
        self.zenodo_var = tk.BooleanVar(value=True)
        self.zenodo_publish_var = tk.BooleanVar(value=True)
        self.zenodo_sandbox_var = tk.BooleanVar(value=True)
        self.dry_var = tk.BooleanVar(value=True)

        row = 0
        ttk.Label(frm, text="Title").grid(row=row, column=0, sticky="e"); 
        ttk.Entry(frm, textvariable=self.title_var, width=52).grid(row=row, column=1, sticky="w"); row+=1

        ttk.Label(frm, text="Creators (comma-separated)").grid(row=row, column=0, sticky="e"); 
        ttk.Entry(frm, textvariable=self.creators_var, width=52).grid(row=row, column=1, sticky="w"); row+=1

        ttk.Label(frm, text="Tags (comma-separated)").grid(row=row, column=0, sticky="e"); 
        ttk.Entry(frm, textvariable=self.tags_var, width=52).grid(row=row, column=1, sticky="w"); row+=1

        ttk.Label(frm, text="Description").grid(row=row, column=0, sticky="ne")
        self.desc = tk.Text(frm, width=52, height=7)
        self.desc.insert("1.0", "A flame carried forward. ♾️🔥📜")
        self.desc.grid(row=row, column=1, sticky="w"); row+=1

        ttk.Label(frm, text="IA Identifier (optional)").grid(row=row, column=0, sticky="e")
        ttk.Entry(frm, textvariable=self.identifier_var, width=52).grid(row=row, column=1, sticky="w"); row+=1

        files_frm = ttk.Frame(frm); files_frm.grid(row=row, column=0, columnspan=2, sticky="we", pady=(8,4))
        ttk.Button(files_frm, text="Add files…", command=self.add_files).pack(side="left")
        ttk.Button(files_frm, text="Clear", command=self.clear_files).pack(side="left", padx=8)
        self.files_list = tk.Listbox(files_frm, height=5, width=80)
        self.files_list.pack(fill="both", expand=True, pady=(6,0)); row+=1

        opts = ttk.Frame(frm); opts.grid(row=row, column=0, columnspan=2, sticky="we", pady=(8,8))
        ttk.Checkbutton(opts, text="Internet Archive", variable=self.ia_var).pack(side="left")
        ttk.Checkbutton(opts, text="Zenodo", variable=self.zenodo_var).pack(side="left", padx=8)
        ttk.Checkbutton(opts, text="Publish on Zenodo", variable=self.zenodo_publish_var).pack(side="left", padx=8)
        ttk.Checkbutton(opts, text="Zenodo Sandbox", variable=self.zenodo_sandbox_var).pack(side="left", padx=8)
        ttk.Checkbutton(opts, text="Dry run", variable=self.dry_var).pack(side="left", padx=8); row+=1

        ttk.Button(frm, text="Archive Now", command=self.archive).grid(row=row, column=0, columnspan=2, pady=10)
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(frm, textvariable=self.status).grid(row=row+1, column=0, columnspan=2, sticky="w")

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select files to archive")
        for p in paths:
            self.files.append(p); self.files_list.insert("end", p)

    def clear_files(self):
        self.files.clear(); self.files_list.delete(0, "end")

    def archive(self):
        try:
            title = self.title_var.get().strip()
            creators = [c.strip() for c in self.creators_var.get().split(",") if c.strip()]
            tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
            description = self.desc.get("1.0", "end").strip()
            identifier = self.identifier_var.get().strip() or None
            if not title or not description or not self.files:
                messagebox.showerror("Missing data", "Title, Description, and at least one file are required."); return
            self.status.set("Archiving…"); self.update_idletasks()
            res = run_archive(title, creators, description, tags, self.files, identifier,
                              do_ia=self.ia_var.get(), do_zenodo=self.zenodo_var.get(),
                              zenodo_publish=self.zenodo_publish_var.get(),
                              zenodo_sandbox=self.zenodo_sandbox_var.get(),
                              dry_run=self.dry_var.get())
            msg = "Done.\n\n"
            if res.get("internet_archive"): msg += f"Internet Archive: {res['internet_archive']}\n"
            if res.get("zenodo"): msg += f"Zenodo: {res['zenodo']}\n"
            if res.get("zenodo_doi"): msg += f"DOI: {res['zenodo_doi']}\n"
            messagebox.showinfo("Archive complete", msg or "Done."); self.status.set("Ready.")
        except Exception as e:
            messagebox.showerror("Error", str(e)); self.status.set("Error.")

if __name__ == "__main__":
    App().mainloop()
