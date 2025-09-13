#!/usr/bin/env python3
"""
ArchiMate ingestor with relationships & diagrams
- Load .archimate XML
- Quick-add elements (type/name/description) -> appends to Paste Area
- Paste Area (text list) including relationships -> staged elements & relationships
- Insert commits staged lines into the model, placing elements in the correct folder
- Relationships are placed in Relations folder and diagram objects + connections are created in an "Auto Diagram"
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
def generate_id(prefix="id"):
    return f"{prefix}-{uuid.uuid4().hex}"

# Map ArchiMate element short types to Folder name (exact match on folder @name) or fallback
FOLDER_MAP = {
    # Business
    "BusinessActor": "Business",
    "BusinessRole": "Business",
    "BusinessCollaboration": "Business",
    "BusinessEvent": "Business",
    "BusinessProcess": "Business",
    "BusinessFunction": "Business",
    "BusinessInteraction": "Business",
    "BusinessService": "Business",
    "BusinessObject": "Business",
    # Application
    "ApplicationComponent": "Application",
    "ApplicationCollaboration": "Application",
    "ApplicationInterface": "Application",
    "ApplicationService": "Application",
    "DataObject": "Application",
    # Technology & Physical
    "Node": "Technology & Physical",
    "Device": "Technology & Physical",
    "SystemSoftware": "Technology & Physical",
    "TechnologyInterface": "Technology & Physical",
    "TechnologyService": "Technology & Physical",
    "Artifact": "Technology & Physical",
    # Motivation
    "Driver": "Motivation",
    "Goal": "Motivation",
    "Assessment": "Motivation",
    "Principle": "Motivation",
    "Requirement": "Motivation",
    "Constraint": "Motivation",
    # Strategy
    "Capability": "Strategy",
    "CourseOfAction": "Strategy",
    # Implementation & Migration
    "WorkPackage": "Implementation & Migration",
    "Deliverable": "Implementation & Migration",
    "Plateau": "Implementation & Migration",
    # Relations
    # relationship types are placed in Relations folder (special-handled)
}

# Common types for quick-add combobox
COMMON_TYPES = [
    "BusinessActor", "BusinessRole", "BusinessProcess", "BusinessService",
    "ApplicationComponent", "ApplicationService",
    "Node", "Device", "SystemSoftware",
    "Goal", "Driver", "WorkPackage", "Deliverable"
]

# Relationship types recognized
RELATIONSHIP_TYPES = set([
    "AssignmentRelationship","RealizationRelationship","AssociationRelationship",
    "CompositionRelationship","AggregationRelationship","ServingRelationship",
    "AccessRelationship","FlowRelationship","TriggeringRelationship",
    "SpecializationRelationship","UsedByRelationship","InfluenceRelationship"
])

class ArchiIngestorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ArchiMate Ingestor (Relations & Diagrams)")
        self.root.geometry("1200x800")

        self.tree = None        # ElementTree
        self.model = None       # root element
        self.history = []       # undo snapshots
        self.filepath = None

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

        # Paned layout
        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill="both", expand=True, padx=6, pady=6)

        # Left: Tree & details
        left_frame = tk.Frame(main)
        main.add(left_frame, stretch="always")
        tk.Label(left_frame, text="Model Tree (folders -> elements)").pack(anchor="w")
        self.treeview = ttk.Treeview(left_frame)
        self.treeview.pack(fill="both", expand=True, side="left")
        self.treeview.bind("<<TreeviewSelect>>", self.on_tree_select)
        tree_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.treeview.yview)
        tree_scroll.pack(side="left", fill="y")
        self.treeview.configure(yscrollcommand=tree_scroll.set)
        details_frame = tk.Frame(left_frame)
        details_frame.pack(fill="x")
        tk.Label(details_frame, text="Selected Node Details:").pack(anchor="w")
        self.details_text = tk.Text(details_frame, height=7, state="disabled")
        self.details_text.pack(fill="both", expand=True)

        # Right: Quick add + Paste + Preview
        right_frame = tk.Frame(main)
        main.add(right_frame, stretch="always")

        # Quick Add
        quick_frame = tk.LabelFrame(right_frame, text="Quick Add (appends to Paste Area)")
        quick_frame.pack(fill="x", padx=4, pady=4)
        tk.Label(quick_frame, text="Type:").grid(row=0, column=0, sticky="w")
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(quick_frame, textvariable=self.type_var, values=COMMON_TYPES, width=30)
        self.type_combo.grid(row=0, column=1, sticky="we", padx=4, pady=2)
        self.type_combo.current(0)
        tk.Label(quick_frame, text="Name:").grid(row=1, column=0, sticky="w")
        self.name_entry = tk.Entry(quick_frame, width=60)
        self.name_entry.grid(row=1, column=1, sticky="we", padx=4, pady=2)
        tk.Label(quick_frame, text="Description:").grid(row=2, column=0, sticky="w")
        self.desc_entry = tk.Entry(quick_frame, width=60)
        self.desc_entry.grid(row=2, column=1, sticky="we", padx=4, pady=2)
        tk.Button(quick_frame, text="Add → Paste Area", command=self.quick_add_to_paste).grid(row=3, column=1, sticky="e", padx=4, pady=6)
        quick_frame.grid_columnconfigure(1, weight=1)

        # Paste area
        paste_frame = tk.LabelFrame(right_frame, text="Paste Area (text-based staging)")
        paste_frame.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Label(paste_frame, text="One entry per line. Format examples:\nElement: Type | Name | description=...\nRelationship: AssignmentRelationship | SourceName | target=TargetName | description=...").pack(anchor="w")
        self.paste_text = tk.Text(paste_frame, height=14)
        self.paste_text.pack(fill="both", expand=True)
        self.paste_text.bind("<<Modified>>", self.on_paste_modified)
        paste_buttons = tk.Frame(paste_frame)
        paste_buttons.pack(fill="x")
        tk.Button(paste_buttons, text="Clear Paste Area", command=self.clear_paste).pack(side="left", padx=4, pady=4)
        tk.Button(paste_buttons, text="Parse Preview", command=self.update_staged_preview).pack(side="left", padx=4, pady=4)

        # Preview area (XML snippets)
        preview_frame = tk.LabelFrame(right_frame, text="Staged Preview (XML snippets)")
        preview_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.preview_text = tk.Text(preview_frame, height=12, state="disabled")
        self.preview_text.pack(fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="No file loaded.")
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
            self.save_history()
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
            # ensure ElementTree root is current model
            self.tree = ET.ElementTree(self.model)
            self.tree.write(path, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Saved", f"Saved to {path}")
            self.status_var.set(f"Saved: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save file:\n{e}")

    # ---------------- TreeView ----------------
    def refresh_tree(self):
        self.treeview.delete(*self.treeview.get_children())
        if self.model is None:
            return

        root_label = f"archimate:model | {self.model.get('name','')}"
        root_id = self.treeview.insert("", "end", text=root_label, open=True)

        # Folders
        for folder in self.model.findall(f"{{{ARCHIMATE}}}folder"):
            fname = folder.get("name", "Folder")
            ftype = folder.get("type", "")
            folder_id = self.treeview.insert(root_id, "end", text=f"{fname} ({ftype})", values=("folder", folder.get("id","")))
            # elements
            for el in folder.findall(f"{{{ARCHIMATE}}}element"):
                etype_full = el.get(f"{{{XSI}}}type", "")
                etype = etype_full.split(":")[-1] if ":" in etype_full else etype_full
                name = el.get("name","")
                el_id = el.get("id","")
                el_label = f"{etype} | {name}"
                el_node = self.treeview.insert(folder_id, "end", text=el_label, values=("element", el_id))
                # children (like documentation)
                for child in list(el):
                    ctag = child.tag.split("}")[-1]
                    ctext = (child.text or "").strip()
                    child_label = f"{ctag}: {ctext}" if ctext else ctag
                    self.treeview.insert(el_node, "end", text=child_label)
            # relationships in folder
            for rel in folder.findall(f"{{{ARCHIMATE}}}relationship"):
                rtype = rel.get(f"{{{XSI}}}type","")
                if rtype and "Relationship" in rtype:
                    # show separately as relation items
                    rname = rel.get("id","")
                    src = rel.get("source","")
                    tgt = rel.get("target","")
                    rel_label = f"{rtype.split(':')[-1]} | {src} -> {tgt}"
                    self.treeview.insert(folder_id, "end", text=rel_label, values=("relationship", rel.get("id","")))

    def on_tree_select(self, event):
        sel = self.treeview.selection()
        if not sel:
            return
        node = sel[0]
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        item_text = self.treeview.item(node, "text")
        self.details_text.insert("end", item_text + "\n\n")
        vals = self.treeview.item(node, "values")
        if vals and vals[0] == "element":
            el_id = vals[1]
            el = self.find_element_by_id(el_id)
            if el is not None:
                for k,v in el.attrib.items():
                    self.details_text.insert("end", f"{k} = {v}\n")
                for child in list(el):
                    ctag = child.tag.split("}")[-1]
                    ctext = (child.text or "").strip()
                    self.details_text.insert("end", f"{ctag}: {ctext}\n")
        elif vals and vals[0] == "relationship":
            rel_id = vals[1]
            rel = self.find_relationship_by_id(rel_id)
            if rel is not None:
                for k,v in rel.attrib.items():
                    self.details_text.insert("end", f"{k} = {v}\n")
                for child in list(rel):
                    ctag = child.tag.split("}")[-1]
                    ctext = (child.text or "").strip()
                    self.details_text.insert("end", f"{ctag}: {ctext}\n")
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
        line = f"{t} | {name}"
        if desc:
            line += f" | description={desc}"
        cur = self.paste_text.get("1.0", "end").rstrip()
        if cur:
            self.paste_text.insert("end", "\n" + line)
        else:
            self.paste_text.insert("end", line)
        self.update_staged_preview()
        self.name_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")

    def on_paste_modified(self, event=None):
        if self.paste_text.edit_modified():
            self.update_staged_preview()
            self.paste_text.edit_modified(False)

    def update_staged_preview(self):
        """Parse paste lines and generate preview snippets (elements or relationships)"""
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
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2:
                snippets.append(f"<!-- Could not parse: {ln} -->")
                continue
            raw_type = parts[0]
            # Relationship?
            short = raw_type.split(":")[-1]
            if short.endswith("Relationship") or short in RELATIONSHIP_TYPES:
                # Expect: RelationshipType | SourceName | target=TargetName | description=...
                source = parts[1]
                target = None
                extras = {}
                for extra in parts[2:]:
                    if "=" in extra:
                        k,v = extra.split("=",1)
                        extras[k.strip()] = v.strip()
                target = extras.get("target")
                descr = extras.get("description")
                snippet = f'<relationship xsi:type="archimate:{short}" source="{source}" target="{target or ""}"'
                if descr:
                    snippet += f' description="{descr}"'
                snippet += ' />'
                snippets.append(snippet)
            else:
                # Element parse
                etype = raw_type if ":" in raw_type else f"archimate:{raw_type}"
                name = parts[1]
                extras = {}
                for extra in parts[2:]:
                    if "=" in extra:
                        k,v = extra.split("=",1)
                        extras[k.strip()] = v.strip()
                doc = extras.get("description") or extras.get("documentation")
                if doc:
                    snippet = f'<element xsi:type="{etype}" name="{name}" id="{generate_id()}" ><documentation>{doc}</documentation></element>'
                else:
                    snippet = f'<element xsi:type="{etype}" name="{name}" id="{generate_id()}" />'
                snippets.append(snippet)
        for s in snippets:
            self.preview_text.insert("end", s + "\n")
        self.preview_text.config(state="disabled")

    # ---------------- Insert / Commit ----------------
    def insert_from_paste(self):
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

        # Snapshot for undo
        self.save_history()

        # Two-phase: create elements first, then relationships
        created_elements = []
        relationships_to_create = []

        # list of existing element names -> IDs (map for quick lookup)
        name_to_element = self.build_name_index()

        # Ensure folders list
        folders = list(self.model.findall(f"{{{ARCHIMATE}}}folder"))
        if not folders:
            # create default folders if missing
            self.create_default_folders()

        for ln in lines:
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2:
                continue
            raw_type = parts[0]
            short = raw_type.split(":")[-1]
            # Relationship?
            if short.endswith("Relationship") or short in RELATIONSHIP_TYPES:
                # collect for second pass
                # parts[1] should be source name
                src_name = parts[1]
                extras = {}
                for extra in parts[2:]:
                    if "=" in extra:
                        k,v = extra.split("=",1)
                        extras[k.strip()] = v.strip()
                tgt_name = extras.get("target")
                descr = extras.get("description") or extras.get("documentation")
                relationships_to_create.append({
                    "type": short,
                    "raw_type": raw_type,
                    "source_name": src_name,
                    "target_name": tgt_name,
                    "description": descr
                })
            else:
                # Element creation
                etype_short = short
                etype_full = raw_type if ":" in raw_type else f"archimate:{raw_type}"
                name = parts[1]
                extras = {}
                for extra in parts[2:]:
                    if "=" in extra:
                        k,v = extra.split("=",1)
                        extras[k.strip()] = v.strip()
                # If element with same name and same xsi:type exists skip creating duplicate
                existing_id = self.find_element_id_by_name_and_type(name, etype_full)
                if existing_id:
                    # skip, but ensure index has it
                    name_to_element[name.lower()] = existing_id
                    continue
                # create new element
                new_el_id = generate_id()
                attribs = {f"{{{XSI}}}type": etype_full, "name": name, "id": new_el_id}
                # create element in appropriate folder
                target_folder = self.get_folder_for_type(etype_short)
                new_el = ET.SubElement(target_folder, f"{{{ARCHIMATE}}}element", attribs)
                # documentation child if description
                doc_text = extras.get("description") or extras.get("documentation")
                if doc_text:
                    doc_el = ET.SubElement(new_el, "documentation")
                    doc_el.text = doc_text
                created_elements.append((name, new_el_id))
                name_to_element[name.lower()] = new_el_id

        # Second pass: create relationships
        # Ensure relations folder exists
        rel_folder = self.ensure_relations_folder()
        # Ensure there is a Views folder + an Auto Diagram
        views_folder = self.ensure_folder("Views", folder_type="diagrams")
        diagram_element = self.ensure_diagram_model(views_folder, diagram_name="Auto Diagram")

        # For diagram layout: reuse or create a mapping of element id -> diagram child id, and positions
        diagram_children = self.build_existing_diagram_children_map(diagram_element)
        next_x = 80
        next_y = 80
        col_count = 0
        max_cols = 6

        for rel in relationships_to_create:
            rtype = rel["type"]
            raw_type = rel["raw_type"]
            src_name = rel["source_name"]
            tgt_name = rel["target_name"]
            descr = rel.get("description")

            # resolve source and target element IDs (try exact, then case-insensitive)
            src_id = self.find_element_id_by_name(src_name)
            if not src_id:
                # create placeholder BusinessObject in Other folder so relationship can be created
                created = self.create_placeholder(src_name)
                src_id = created
                name_to_element[src_name.lower()] = src_id

            tgt_id = None
            if tgt_name:
                tgt_id = self.find_element_id_by_name(tgt_name)
                if not tgt_id:
                    created = self.create_placeholder(tgt_name)
                    tgt_id = created
                    name_to_element[tgt_name.lower()] = tgt_id
            else:
                # no explicit target provided: skip creating relationship
                # but still create a partial relationship? skip and warn
                messagebox.showwarning("Relationship parse", f"Relationship '{rtype}' missing target for source '{src_name}' - skipping.")
                continue

            # Create relationship (CRITICAL: use "relationship" not "element")
            rel_id = generate_id()
            rel_attribs = {
                f"{{{XSI}}}type": f"archimate:{rtype}",
                "id": rel_id, 
                "source": src_id, 
                "target": tgt_id
            }
            rel_el = ET.SubElement(rel_folder, f"{{{ARCHIMATE}}}relationship", rel_attribs)
            
            if descr:
                d = ET.SubElement(rel_el, "documentation")
                d.text = descr

            # Now create diagram objects for the source and target (if not already on diagram)
            src_child_id = diagram_children.get(src_id)
            if not src_child_id:
                # create a diagram child for source under diagram_element
                src_child_id = generate_id()
                child_el = ET.SubElement(diagram_element, "child", {f"{{{XSI}}}type": "archimate:DiagramObject", "id": src_child_id, "archimateElement": src_id})
                ET.SubElement(child_el, "bounds", {"x": str(next_x), "y": str(next_y), "width": "140", "height": "60"})
                diagram_children[src_id] = src_child_id
                # advance grid
                next_x += 220
                col_count += 1
                if col_count >= max_cols:
                    col_count = 0
                    next_x = 80
                    next_y += 120

            tgt_child_id = diagram_children.get(tgt_id)
            if not tgt_child_id:
                tgt_child_id = generate_id()
                child_el = ET.SubElement(diagram_element, "child", {f"{{{XSI}}}type": "archimate:DiagramObject", "id": tgt_child_id, "archimateElement": tgt_id})
                ET.SubElement(child_el, "bounds", {"x": str(next_x), "y": str(next_y), "width": "140", "height": "60"})
                diagram_children[tgt_id] = tgt_child_id
                next_x += 220
                col_count += 1
                if col_count >= max_cols:
                    col_count = 0
                    next_x = 80
                    next_y += 120

            # create a connection: put under the source child as sourceConnection element (mimic Archi)
            conn_id = generate_id()
            # source child lookup element reference
            source_child_el = self.find_child_in_element(diagram_element, src_child_id)
            target_child_el = self.find_child_in_element(diagram_element, tgt_child_id)
            if source_child_el is not None:
                conn_attribs = {
                    f"{{{XSI}}}type": "archimate:Connection",
                    "id": conn_id,
                    "source": src_child_id,
                    "target": tgt_child_id,
                    "archimateRelationship": rel_id
                }
                ET.SubElement(source_child_el, "sourceConnection", conn_attribs)
            # set target child's 'targetConnections' attribute (as sample)
            if target_child_el is not None:
                existing = target_child_el.get("targetConnections")
                if existing:
                    target_child_el.set("targetConnections", existing + " " + conn_id)
                else:
                    target_child_el.set("targetConnections", conn_id)

        # done, refresh tree and preview
        # update tree and set tree for saving
        self.tree = ET.ElementTree(self.model)
        self.refresh_tree()
        self.update_staged_preview()
        messagebox.showinfo("Inserted", f"Inserted elements & relationships. Diagram updated (Auto Diagram).")

    # ---------------- helper methods ----------------
    def build_name_index(self):
        """Return dict name_lower -> element id for quick lookup."""
        idx = {}
        if self.model is None:
            return idx
        for el in self.model.findall(f".//{{{ARCHIMATE}}}element"):
            name = el.get("name")
            if name:
                idx[name.lower()] = el.get("id")
        return idx

    def find_element_by_id(self, el_id):
        if self.model is None:
            return None
        return self.model.find(f".//*[@id='{el_id}']")

    def find_relationship_by_id(self, rel_id):
        if self.model is None:
            return None
        return self.model.find(f".//{{{ARCHIMATE}}}relationship[@id='{rel_id}']")

    def find_element_id_by_name_and_type(self, name, etype_full):
        """Exact match name + xsi:type string -> id if exists"""
        if self.model is None:
            return None
        for el in self.model.findall(f".//{{{ARCHIMATE}}}element"):
            if el.get("name") == name and el.get(f"{{{XSI}}}type") == etype_full:
                return el.get("id")
        return None

    def find_element_id_by_name(self, name):
        if self.model is None:
            return None
        # exact match first
        for el in self.model.findall(f".//{{{ARCHIMATE}}}element"):
            if el.get("name") == name:
                return el.get("id")
        # case-insensitive fallback
        lname = name.lower()
        for el in self.model.findall(f".//{{{ARCHIMATE}}}element"):
            if el.get("name") and el.get("name").lower() == lname:
                return el.get("id")
        return None

    def get_folder_for_type(self, etype_short):
        """Return folder element where an element of type etype_short should go (create 'Other' fallback)."""
        # Handle relationships differently
        if etype_short.endswith("Relationship") or etype_short in RELATIONSHIP_TYPES:
            return self.ensure_relations_folder()
        
        target_folder_name = FOLDER_MAP.get(etype_short)
        # search by folder type attribute first (e.g. type="business")
        if target_folder_name:
            # try to find a folder whose name matches
            for f in self.model.findall(f"{{{ARCHIMATE}}}folder"):
                if f.get("name") == target_folder_name or (f.get("type") and f.get("type").lower() == target_folder_name.lower()):
                    return f
        # fallback: find folder named 'Other'
        for f in self.model.findall(f"{{{ARCHIMATE}}}folder"):
            if f.get("name") == "Other":
                return f
        # else create Other folder at root
        other = ET.SubElement(self.model, f"{{{ARCHIMATE}}}folder", {"name": "Other", "id": generate_id(), "type": "other"})
        return other

    def ensure_folder(self, folder_name, folder_type=None):
        """Find or create a folder by name AND type."""
        # First try to find by type if specified
        if folder_type:
            for f in self.model.findall(f"{{{ARCHIMATE}}}folder"):
                if f.get("type") == folder_type:
                    return f
        
        # Then try by name
        for f in self.model.findall(f"{{{ARCHIMATE}}}folder"):
            if f.get("name") == folder_name:
                # Update type if needed
                if folder_type and f.get("type") != folder_type:
                    f.set("type", folder_type)
                return f
        
        # Create new folder
        attribs = {"name": folder_name, "id": generate_id()}
        if folder_type:
            attribs["type"] = folder_type
        newf = ET.SubElement(self.model, f"{{{ARCHIMATE}}}folder", attribs)
        return newf

    def ensure_relations_folder(self):
        """Find or create the relations folder with proper type attribute"""
        for f in self.model.findall(f"{{{ARCHIMATE}}}folder"):
            if f.get("type") == "relations":
                return f
        # Create proper relations folder
        rel_folder = ET.SubElement(self.model, f"{{{ARCHIMATE}}}folder", {
            "name": "Relations", 
            "id": generate_id(), 
            "type": "relations"  # This is CRITICAL
        })
        return rel_folder

    def create_default_folders(self):
        # create the common folders if missing
        defaults = [
            ("Strategy","strategy"),
            ("Business","business"),
            ("Application","application"),
            ("Technology & Physical","technology"),
            ("Motivation","motivation"),
            ("Implementation & Migration","implementation_migration"),
            ("Other","other"),
            ("Relations","relations"),  # This MUST be "relations" (not "relations")
            ("Views","diagrams")
        ]
        for name, ftype in defaults:
            found = False
            for f in self.model.findall(f"{{{ARCHIMATE}}}folder"):
                if f.get("type") == ftype:  # Check by type, not name
                    found = True
                    break
            if not found:
                ET.SubElement(self.model, f"{{{ARCHIMATE}}}folder", {
                    "name": name, 
                    "id": generate_id(), 
                    "type": ftype
                })

    def create_placeholder(self, name):
        """Create a small BusinessObject placeholder in Other folder and return its id."""
        other_folder = self.get_or_create_folder_by_name("Other")
        pid = generate_id()
        attribs = {f"{{{XSI}}}type": "archimate:BusinessObject", "name": name, "id": pid}
        p = ET.SubElement(other_folder, f"{{{ARCHIMATE}}}element", attribs)
        doc = ET.SubElement(p, "documentation")
        doc.text = "Auto-created placeholder"
        return pid

    def get_or_create_folder_by_name(self, folder_name):
        for f in self.model.findall(f"{{{ARCHIMATE}}}folder"):
            if f.get("name") == folder_name:
                return f
        newf = ET.SubElement(self.model, f"{{{ARCHIMATE}}}folder", {"name": folder_name, "id": generate_id(), "type": folder_name.lower()})
        return newf

    def ensure_diagram_model(self, views_folder, diagram_name="Auto Diagram"):
        """Find or create an ArchimateDiagramModel element in the Views folder."""
        # find existing diagram element (xsi:type archimate:ArchimateDiagramModel)
        for el in views_folder.findall(f"{{{ARCHIMATE}}}element"):
            if el.get(f"{{{XSI}}}type","").endswith("ArchimateDiagramModel") and el.get("name")==diagram_name:
                return el
        # create new diagram element
        diag_id = generate_id()
        diag_attribs = {f"{{{XSI}}}type": "archimate:ArchimateDiagramModel", "name": diagram_name, "id": diag_id}
        diag_el = ET.SubElement(views_folder, f"{{{ARCHIMATE}}}element", diag_attribs)
        return diag_el

    def build_existing_diagram_children_map(self, diagram_element):
        """Return mapping element_id -> child_id for existing child DiagramObjects of diagram_element."""
        mapping = {}
        if diagram_element is None:
            return mapping
        for child in diagram_element.findall("child"):
            arch_elem = child.get("archimateElement")
            cid = child.get("id")
            if arch_elem and cid:
                mapping[arch_elem] = cid
        return mapping

    def find_child_in_element(self, diagram_element, child_id):
        """Find the child node element with id == child_id under diagram_element."""
        if diagram_element is None:
            return None
        for ch in diagram_element.findall("child"):
            if ch.get("id") == child_id:
                return ch
        return None

    # ---------------- History / Undo ----------------
    def save_history(self):
        if self.model is None:
            return
        self.history.append(copy.deepcopy(self.model))
        if len(self.history) > 40:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            messagebox.showinfo("Undo", "No undo history.")
            return
        snapshot = self.history.pop()
        self.model = snapshot
        self.tree = ET.ElementTree(self.model)
        self.refresh_tree()
        messagebox.showinfo("Undo", "Reverted one step.")

# ---- Run ----
if __name__ == "__main__":
    root = tk.Tk()
    app = ArchiIngestorApp(root)
    root.mainloop()