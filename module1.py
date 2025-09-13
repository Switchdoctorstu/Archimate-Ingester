#!/usr/bin/env python3
"""
ArchiMate ingestor GUI (single-file)
- Load .archimate XML
- Quick-add elements (type/name/description) -> appends to Paste Area
- Paste Area (text list) -> staged elements
- Staged Preview shows the XML snippets that will be created
- Insert commits staged lines into the model, placing elements in the correct folder
- Tree view shows the model; selecting a node shows details
- Save writes a valid .archimate file with proper namespaces
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import uuid
import copy
import os

# ---- Namespaces ----
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ARCHIMATE = "http://www.archimatetool.com/archimate"
ET.register_namespace("xsi", XSI)
ET.register_namespace("archimate", ARCHIMATE)

# ---- Utility ----
def generate_id():
    return "id-" + uuid.uuid4().hex

# Map ArchiMate element types to folder names
FOLDER_MAP = {
    "BusinessActor": "Business",
    "BusinessRole": "Business",
    "BusinessProcess": "Business",
    "BusinessService": "Business",
    "BusinessEvent": "Business",
    "BusinessFunction": "Business",
    "BusinessObject": "Business",
    "ApplicationComponent": "Application",
    "ApplicationService": "Application",
    "ApplicationInterface": "Application",
    "Node": "Technology & Physical",
    "Device": "Technology & Physical",
    "SystemSoftware": "Technology & Physical",
    "Artifact": "Technology & Physical",
    "Goal": "Motivation",
    "Driver": "Motivation",
    "Requirement": "Motivation",
    "Constraint": "Motivation",
    "Capability": "Strategy",
    "CourseOfAction": "Strategy",
    "WorkPackage": "Implementation & Migration",
    "Deliverable": "Implementation & Migration",
}

# Set of commonly-used ArchiMate short types to populate the quick-add combobox
COMMON_TYPES = [
    "BusinessActor", "BusinessRole", "BusinessProcess", "BusinessService",
    "ApplicationComponent", "ApplicationService",
    "Node", "Device", "SystemSoftware",
    "Goal", "Driver", "WorkPackage", "Deliverable"
]

class ArchiIngestorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ArchiMate Ingestor")
        self.root.geometry("1100x700")

        # XML model state
        self.tree = None          # ElementTree
        self.model = None         # root element
        self.history = []         # undo stack (deep copies of tree)
        self.filepath = None

        # Define all attributes that will be used in build_gui first
        self.status_var = tk.StringVar()
        self.status_var.set("No file loaded.")
        
        self.type_var = tk.StringVar()
        
        # Now build the GUI
        self.build_gui()

    def build_gui(self):
        # Top toolbar
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill="x", pady=4)
        tk.Button(toolbar, text="Open .archimate", command=self.open_file).pack(side="left", padx=4)
        tk.Button(toolbar, text="Insert (commit staged)", command=self.insert_from_paste).pack(side="left", padx=4)
        tk.Button(toolbar, text="Undo", command=self.undo).pack(side="left", padx=4)
        tk.Button(toolbar, text="Save As...", command=self.save_as).pack(side="left", padx=4)
        tk.Button(toolbar, text="Refresh Tree", command=self.refresh_tree).pack(side="left", padx=4)

        # Main panes
        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill="both", expand=True, padx=6, pady=6)

        # Left: Treeview + Details
        left_frame = tk.Frame(main)
        main.add(left_frame, stretch="always")

        tree_label = tk.Label(left_frame, text="Model Tree (folders -> elements)")
        tree_label.pack(anchor="w")
        self.treeview = ttk.Treeview(left_frame)
        self.treeview.pack(fill="both", expand=True, side="left")
        self.treeview.bind("<<TreeviewSelect>>", self.on_tree_select)

        tree_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.treeview.yview)
        tree_scroll.pack(side="left", fill="y")
        self.treeview.configure(yscrollcommand=tree_scroll.set)

        details_frame = tk.Frame(left_frame)
        details_frame.pack(fill="x")
        tk.Label(details_frame, text="Selected Node Details:").pack(anchor="w")
        self.details_text = tk.Text(details_frame, height=6, state="disabled")
        self.details_text.pack(fill="both", expand=True)

        # Right: Inputs / Paste / Staged preview
        right_frame = tk.Frame(main)
        main.add(right_frame, stretch="always")

        # Quick Add
        quick_frame = tk.LabelFrame(right_frame, text="Quick Add (appends to Paste Area)")
        quick_frame.pack(fill="x", padx=4, pady=4)

        tk.Label(quick_frame, text="Type:").grid(row=0, column=0, sticky="w")
        self.type_combo = ttk.Combobox(quick_frame, textvariable=self.type_var, values=COMMON_TYPES, width=30)
        self.type_combo.grid(row=0, column=1, sticky="we", padx=4, pady=2)
        self.type_combo.current(0)

        tk.Label(quick_frame, text="Name:").grid(row=1, column=0, sticky="w")
        self.name_entry = tk.Entry(quick_frame, width=50)
        self.name_entry.grid(row=1, column=1, sticky="we", padx=4, pady=2)

        tk.Label(quick_frame, text="Description:").grid(row=2, column=0, sticky="w")
        self.desc_entry = tk.Entry(quick_frame, width=50)
        self.desc_entry.grid(row=2, column=1, sticky="we", padx=4, pady=2)

        tk.Button(quick_frame, text="Add → Paste Area", command=self.quick_add_to_paste).grid(row=3, column=1, sticky="e", padx=4, pady=6)

        quick_frame.grid_columnconfigure(1, weight=1)

        # Paste area (staging text)
        paste_frame = tk.LabelFrame(right_frame, text="Paste Area (text-based staging)")
        paste_frame.pack(fill="both", expand=True, padx=4, pady=4)

        tk.Label(paste_frame, text="One entry per line. Format (simple):\nType | Name | key=value | description=...").pack(anchor="w")
        self.paste_text = tk.Text(paste_frame, height=10)
        self.paste_text.pack(fill="both", expand=True)
        self.paste_text.bind("<<Modified>>", self.on_paste_modified)

        paste_buttons = tk.Frame(paste_frame)
        paste_buttons.pack(fill="x")
        tk.Button(paste_buttons, text="Clear Paste Area", command=self.clear_paste).pack(side="left", padx=4, pady=4)
        tk.Button(paste_buttons, text="Parse Preview", command=self.update_staged_preview).pack(side="left", padx=4, pady=4)

        # Staged preview (shows the XML snippets that will be created from paste area)
        preview_frame = tk.LabelFrame(right_frame, text="Staged Preview (XML snippets from paste area)")
        preview_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.preview_text = tk.Text(preview_frame, height=12, state="disabled")
        self.preview_text.pack(fill="both", expand=True)

        # bottom status
        status = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        status.pack(fill="x")

    # ---------------- File I/O ----------------
    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("ArchiMate files", "*.archimate;*.xml"), ("All files","*.*")])
        if not path:
            return
        try:
            self.tree = ET.parse(path)
            self.model = self.tree.getroot()
            self.filepath = path
            self.history.clear()
            self.save_history()  # initial snapshot
            self.status_var.set(f"Loaded: {os.path.basename(path)}")
            self.refresh_tree()
            self.update_staged_preview()
        except Exception as e:
            messagebox.showerror("Open error", f"Failed to open file:\n{e}")

    def save_as(self):
        if self.tree is None:
            messagebox.showwarning("No file", "No model loaded.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".archimate", filetypes=[("ArchiMate files", "*.archimate;*.xml")])
        if not path:
            return
        try:
            self.tree.write(path, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Saved", f"Saved to {path}")
            self.status_var.set(f"Saved: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save file:\n{e}")

    # ---------------- TreeView / Preview ----------------
    def refresh_tree(self):
        self.treeview.delete(*self.treeview.get_children())
        if self.model is None:
            return

        # Create root node
        root_label = f"Model: {self.model.get('name', 'Unnamed')}"
        root_id = self.treeview.insert("", "end", text=root_label, open=True)
    
        # Add all folders - use correct namespace
        folders = self.model.findall(".//{http://www.archimatetool.com/archimate}folder")
        if not folders:
            # Try without namespace as fallback
            folders = self.model.findall(".//folder")
    
        for folder in folders:
            folder_name = folder.get("name", "Unnamed Folder")
            folder_type = folder.get("type", "")
            folder_id = self.treeview.insert(root_id, "end", text=f"{folder_name} ({folder_type})", open=True)
        
            # Add elements in this folder - use correct namespace
            elements = folder.findall(".//{http://www.archimatetool.com/archimate}element")
            if not elements:
                # Try without namespace as fallback
                elements = folder.findall(".//element")
        
            for element in elements:
                element_type = element.get(f"{{{XSI}}}type", "").split(":")[-1] if ":" in element.get(f"{{{XSI}}}type", "") else element.get(f"{{{XSI}}}type", "")
                element_name = element.get("name", "Unnamed")
                element_id = element.get("id", "")
            
                element_label = f"{element_type}: {element_name}"
                element_node = self.treeview.insert(folder_id, "end", text=element_label)
            
                # Add documentation if exists - use correct namespace
                documentation = element.find(".//{http://www.archimatetool.com/archimate}documentation")
                if documentation is None:
                    # Try without namespace as fallback
                    documentation = element.find(".//documentation")
            
                if documentation is not None and documentation.text:
                    self.treeview.insert(element_node, "end", text=f"Documentation: {documentation.text}")
    def on_tree_select(self, event):
        sel = self.treeview.selection()
        if not sel:
            return
        node = sel[0]
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("end", self.treeview.item(node, "text") + "\n")
        self.details_text.config(state="disabled")

    # ---------------- Paste Area handling ----------------
    def clear_paste(self):
        self.paste_text.delete("1.0", "end")
        self.update_staged_preview()

    def quick_add_to_paste(self):
        t = self.type_var.get().strip()
        name = self.name_entry.get().strip()
        desc = self.desc_entry.get().strip()
        if not t or not name:
            messagebox.showwarning("Missing", "Please provide both Type and Name for Quick Add.")
            return
        # create a paste-line consistent with expected format
        line = f"{t} | {name}"
        if desc:
            # ensure description uses key 'description' (we will convert to documentation element)
            line += f" | description={desc}"
        # append to paste area (newline)
        cur = self.paste_text.get("1.0", "end").rstrip()
        if cur:
            self.paste_text.insert("end", "\n" + line)
        else:
            self.paste_text.insert("end", line)
        # update preview
        self.update_staged_preview()
        # clear name/desc for convenience
        self.name_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")

    def on_paste_modified(self, event=None):
        # update staged preview when paste area changes
        if self.paste_text.edit_modified():
            self.update_staged_preview()
            self.paste_text.edit_modified(False)

    def update_staged_preview(self):
    
        """Parse paste area lines and render XML snippets into preview_text (read-only)."""
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        text = self.paste_text.get("1.0", "end").strip()
        if not text:
            self.preview_text.insert("end", "(no staged entries)\n")
            self.preview_text.config(state="disabled")
            return
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        snippets = []
        for ln in lines:
            # Accept formats: Type | Name | k=v | description=...
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2:
                snippets.append(f"<!-- Could not parse: {ln} -->")
                continue
            raw_type = parts[0]
            short = raw_type if ":" in raw_type else f"archimate:{raw_type}"
            name = parts[1]
            attrs = {f"{{{XSI}}}type": short, "name": name, "id": generate_id()}
            extras = {}
            for extra in parts[2:]:
                if "=" in extra:
                    k, v = extra.split("=", 1)
                    extras[k.strip()] = v.strip()
            # If description present, show as documentation child in snippet
            doc = extras.get("description") or extras.get("documentation")
            # render snippet WITHOUT namespace prefixes
            if doc:
                snippet = f'<element xsi:type="{short}" name="{name}" id="{attrs["id"]}"><documentation>{doc}</documentation></element>'
            else:
                snippet = f'<element xsi:type="{short}" name="{name}" id="{attrs["id"]}" />'
            snippets.append(snippet)
        # show all snippets
        for s in snippets:
            self.preview_text.insert("end", s + "\n")
        self.preview_text.config(state="disabled")
    # ---------------- Insert / Commit ----------------
 
    def insert_from_paste(self):
        """Parse each paste line and append correct element(s) into proper folder in loaded model."""
        if self.model is None:
            messagebox.showwarning("No model", "Open an .archimate file first.")
            return

        paste = self.paste_text.get("1.0", "end").strip()
        if not paste:
            messagebox.showinfo("Nothing to insert", "Paste Area is empty.")
            return

        lines = [l.strip() for l in paste.splitlines() if l.strip()]
        if not lines:
            messagebox.showinfo("Nothing to insert", "Paste Area is empty.")
            return

        # push undo snapshot
        self.save_history()

        # Get all folders once - use the correct namespace
        folders = self.model.findall(".//{http://www.archimatetool.com/archimate}folder")
        if not folders:
            # Try without namespace as fallback
            folders = self.model.findall(".//folder")
            if not folders:
                messagebox.showerror("Error", "No folders found in the model!")
                return

        inserted = 0
        for ln in lines:
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2:
                continue
            raw_type = parts[0]
            short_name = raw_type.split(":")[-1]  # e.g. BusinessActor
            xsi_type = raw_type if ":" in raw_type else f"archimate:{raw_type}"
            name = parts[1]

            # build element attribs - use the correct namespace URI without prefix
            attribs = {f"{{{XSI}}}type": xsi_type, "name": name, "id": generate_id()}

            extras = {}
            for extra in parts[2:]:
                if "=" in extra:
                    k, v = extra.split("=", 1)
                    extras[k.strip()] = v.strip()

            # create element WITHOUT namespace prefix - use the full URI
            new_el = ET.Element("{http://www.archimatetool.com/archimate}element", attribs)

            # handle documentation as child element if provided - also without prefix
            doc_text = extras.get("description") or extras.get("documentation")
            if doc_text:
                doc_el = ET.SubElement(new_el, "{http://www.archimatetool.com/archimate}documentation")
                doc_el.text = doc_text

            # Find the appropriate folder for this element type
            target_folder_name = FOLDER_MAP.get(short_name, "Other")
        
            # Find the folder with the matching name
            folder_node = None
            for f in folders:
                if f.get("name") == target_folder_name:
                    folder_node = f
                    break
        
            # If not found, use the "Other" folder as fallback
            if folder_node is None:
                for f in folders:
                    if f.get("name") == "Other":
                        folder_node = f
                        break
        
            # If still not found, use the first available folder
            if folder_node is None:
                folder_node = folders[0]

            # append the new element to the existing folder
            folder_node.append(new_el)
            inserted += 1

        # after insertion refresh tree and clear paste if desired
        self.refresh_tree()
        self.update_staged_preview()
        messagebox.showinfo("Inserted", f"Inserted {inserted} element(s).")
    # ---------------- Undo / History ----------------
    def save_history(self):
        if self.tree is None:
            return
        # deep copy of tree to keep snapshot
        self.history.append(copy.deepcopy(self.tree))
        if len(self.history) > 30:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            messagebox.showinfo("Undo", "No undo history.")
            return
        snapshot = self.history.pop()
        self.tree = snapshot
        self.model = self.tree.getroot()
        self.refresh_tree()
        messagebox.showinfo("Undo", "Reverted one step.")

# ---- Run ----
if __name__ == "__main__":
    root = tk.Tk()
    app = ArchiIngestorApp(root)
    root.mainloop()
