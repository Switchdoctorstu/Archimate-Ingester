# ArchiMate ingestor with relationships & diagrams
VERSIONTEXT=" Version: 8.1 3d"
# - Load .archimate XML
# - Quick-add elements (type/name/description) -> appends to Paste Area
# - Paste Area (text list) including relationships -> staged elements & relationships
# - Insert commits staged lines into the model, placing elements in the correct folder
# - Relationships are placed in Relations folder and diagram objects + connections are created in an "Auto Diagram"
# - Tree view shows the model; selecting a node shows details
# - Save writes a valid .archimate file with proper namespaces
# - Live XML output panel always shows current model

# TODO:
# - [ ] Improve error handling and user notifications
# - [ ] Optimize XML handling and improve performance for large models
# - [ ] Enhance 3D view: better visuals, interaction, and support for more element types
# - [ ] Add support for custom element attributes and more relationship types
# - [ ] Allow editing of existing elements and relationships
# - [ ] Implement import and export of views/diagrams
# - [ ] Offer multiple file save formats and settings for export customization
# - [ ] Improve documentation and user guidance within the app

# ---- Imports ----
import tkinter as tk
from tkinter import simpledialog
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
import uuid
import copy
import os
from xml.dom import minidom
import datetime

from ThreeDViewer import ThreeDViewer
import google.generativeai as genai # You may need to run: pip install google-generativeai
from config import FOLDER_MAP, COMMON_TYPES, RELATIONSHIP_TYPES, RELATIONSHIP_RULES, AUTOCOMPLETE_RULES


def list_gemini_models():
    """Fetch list of available Gemini models for dropdown."""
    try:
        client = genai.Client()
        models = client.models.list()
        return [m.name for m in models if "gemini" in m.name]
    except Exception as e:
        print(f"⚠️ Could not fetch model list: {e}")
        # Fallback: common known models
        return ["models/gemini-2.5-pro", "models/gemini-2.5-flash", "models/gemini-2.0-flash"]

# ---- Gemini API Key ----
# IMPORTANT: Replace "YOUR_API_KEY" with your actual Google AI Studio API key.
# Keep this key secure and do not commit it to public repositories.
GEMINI_API_KEY = "xxxxxxxxx"

# ---- Namespaces ----
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ARCHIMATE = "http://www.archimatetool.com/archimate"
ET.register_namespace("xsi", XSI)
ET.register_namespace("archimate", ARCHIMATE)

# ---- Utility ----
def generate_id(prefix="id"):
    return f"{prefix}-{uuid.uuid4().hex}"

def get_build_version():
    try:
        # Use the file's last modification time as the build date
        build_time = os.path.getmtime(__file__)
        build_dt = datetime.datetime.fromtimestamp(build_time)
        return build_dt.strftime("Build %Y-%m-%d %H:%M:%S")
    except Exception:
        return "Build date unknown"

# Map ArchiMate element short types to Folder name
# --- All large configuration dictionaries have been moved to config.py ---


class ArchiIngestorApp:
    def __init__(self, root):
        self.root = root
        version_str = get_build_version()
        self.root.title(f"ArchiMate Ingestor ({VERSIONTEXT }) ({version_str})")
        self.root.geometry("1400x900")

        self.tree = None
        self.model = None
        self.dirty = False # Track if model has unsaved changes
        self.history = []
        self.filepath = None
        self.element_db = {}
        self.relationship_counts = {}
        self.relationship_map = {} # Cache for fast relationship lookups
        self.depth_var = tk.IntVar(value=1)
        self.viewer = ThreeDViewer(self) # Create an instance of the 3D viewer

        self.build_gui()
        self.default_bg = self.open_button.cget("background") # Get default button background
        self.update_button_states() # Initial state update

    def build_gui(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill="x", pady=4)
        self.open_button = tk.Button(toolbar, text="Open .archimate", command=self.open_file)
        self.open_button.pack(side="left", padx=4)
        self.insert_button = tk.Button(toolbar, text="Insert (commit staged)", command=self.insert_from_paste)
        self.insert_button.pack(side="left", padx=4)
        self.undo_button = tk.Button(toolbar, text="Undo", command=self.undo)
        self.undo_button.pack(side="left", padx=4)
        self.save_button = tk.Button(toolbar, text="Save As...", command=self.save_as)
        self.save_button.pack(side="left", padx=4)
        self.refresh_button = tk.Button(toolbar, text="Refresh Tree", command=self.refresh_tree)
        self.refresh_button.pack(side="left", padx=4)
        self.view3d_button = tk.Button(toolbar, text="Show 3D View", command=self.viewer.show_3d_view)
        self.view3d_button.pack(side="left", padx=4)

        tk.Label(toolbar, text="3D Depth:").pack(side="left", padx=(10, 2))
        depth_slider = tk.Scale(toolbar, from_=0, to=5, orient=tk.HORIZONTAL, variable=self.depth_var, length=80)
        depth_slider.pack(side="left", padx=2)
        
        self.clean_button = tk.Button(toolbar, text="Clean & Validate", command=self.validate_and_clean_relationships)
        self.clean_button.pack(side="left", padx=4)
        # Add the conservative autocomplete button
        self.autocomplete_button = tk.Button(toolbar, text="Autocomplete", command=self.autocomplete_model_conservative)
        self.autocomplete_button.pack(side="left", padx=4)
        self.catalog_button = tk.Button(toolbar, text="Catalog", command=self.show_catalog_window)
        self.catalog_button.pack(side="left", padx=4)
        # Add conservative validation button
        #tk.Button(toolbar, text="Validate", command=self.validate_relationships_conservative).pack(side="left", padx=4)

        main = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill="both", expand=True, padx=6, pady=6)

        # Left: Tree, details, XML
        left_frame = tk.Frame(main)
        main.add(left_frame, stretch="always", minsize=400)

        # --- Search and Tree Frame ---
        tree_container = tk.Frame(left_frame)
        tree_container.pack(fill="x", pady=(0, 5))

        tk.Label(tree_container, text="Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(tree_container, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_var.trace_add("write", self.search_tree)

        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill="both", expand=True)
        self.treeview = ttk.Treeview(tree_frame)
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

        # XML Output Panel
        xml_frame = tk.LabelFrame(left_frame, text="Current Output XML")
        xml_frame.pack(fill="both", expand=True, padx=2, pady=2)
        self.xml_output_text = tk.Text(xml_frame, height=18, state="disabled", font=("Consolas", 9))
        self.xml_output_text.pack(fill="both", expand=True)

        # Right: Quick add, paste, preview
        right_frame = tk.Frame(main)
        main.add(right_frame, stretch="never", minsize=400)

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
        # Gemini Frame
        gemini_frame = tk.LabelFrame(right_frame, text="Ask Gemini")
        gemini_frame.pack(fill="x", padx=4, pady=4)
        # --- Gemini Model Selection ---
        tk.Label(gemini_frame, text="Select Gemini Model:").pack(anchor="w")
        self.model_var = tk.StringVar()
        available_models = list_gemini_models()
        self.model_combo = ttk.Combobox(gemini_frame, textvariable=self.model_var, values=available_models, width=40)
        self.model_combo.pack(anchor="w", pady=2)
        if available_models:
            self.model_combo.current(0)  # select first by default

        self.gemini_prompt_text = tk.Text(gemini_frame, height=4, wrap="word")
        self.gemini_prompt_text.pack(fill="x", expand=True, padx=4, pady=(4,0))
        self.gemini_prompt_text.insert("1.0", "As a Planning Officer, what are the key technologies that will affect my role over the next 5 years and how can i best take advantage of them?")
        gemini_button_frame = tk.Frame(gemini_frame)
        gemini_button_frame.pack(fill="x")
        tk.Button(gemini_button_frame, text="Resend inventory", command=self.resend_inventory).pack(side="left", padx=4)
        tk.Checkbutton(gemini_button_frame, text="Delta mode", variable=tk.BooleanVar(value=False),
               command=lambda: setattr(self, "gemini_delta_mode", not getattr(self, "gemini_delta_mode", False))).pack(side="left", padx=4)

        self.gemini_generate_button = tk.Button(gemini_button_frame, text="Generate!", command=self.handle_ask_gemini)
        self.gemini_generate_button.pack(side="right", padx=4, pady=4)

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
        tk.Button(paste_buttons, text="3D Preview", command=self.viewer.show_staged_3d_preview).pack(side="left", padx=4, pady=4)

        preview_frame = tk.LabelFrame(right_frame, text="Staged Preview (XML snippets from paste area)")
        preview_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.preview_text = tk.Text(preview_frame, height=12, state="disabled")
        self.preview_text.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="No file loaded.")
        status = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        status.pack(fill="x")
    

        self.update_staged_preview()

    def update_button_states(self):
        """Updates the state and visual cues of toolbar buttons based on app state."""
        is_model_loaded = self.model is not None
        has_paste_text = self.paste_text.get("1.0", "end-1c").strip() != ""
        highlight_color = "gray80"  # Light gray for highlighting

        # Open button: Highlight if no model is loaded
        self.open_button.config(background=highlight_color if not is_model_loaded else self.default_bg)

        # Save button: Enable if model is loaded, highlight if dirty
        self.save_button.config(state=tk.NORMAL if is_model_loaded else tk.DISABLED)
        self.save_button.config(background=highlight_color if self.dirty else self.default_bg)

        # Insert button: Enable if model is loaded, highlight if there's text to insert
        self.insert_button.config(state=tk.NORMAL if is_model_loaded else tk.DISABLED)
        self.insert_button.config(background=highlight_color if has_paste_text and is_model_loaded else self.default_bg)

        # Undo button: Enable if there's history
        self.undo_button.config(state=tk.NORMAL if self.history else tk.DISABLED)

        # Other model-dependent buttons
        for btn in [self.refresh_button, self.view3d_button, self.clean_button, self.autocomplete_button, self.gemini_generate_button, self.catalog_button]:
            btn.config(state=tk.NORMAL if is_model_loaded else tk.DISABLED)

    def show_catalog_window(self):
        """Creates a non-modal window to generate lists of entities by type."""
        if self.model is None:
            messagebox.showwarning("No Model", "Please open a model file first.")
            return

        # Prevent multiple catalog windows
        if hasattr(self, 'catalog_win') and self.catalog_win.winfo_exists():
            self.catalog_win.lift()
            return

        self.catalog_win = tk.Toplevel(self.root)
        self.catalog_win.title("Entity Catalog")
        self.catalog_win.geometry("400x500")

        # --- Get entity types from the current model ---
        entity_types = set()
        for el in self.model.findall(".//element"):
            el_type_full = el.get(f"{{{XSI}}}type", "")
            # Exclude relationships from the list of types
            if el_type_full and "Relationship" not in el_type_full:
                entity_types.add(el_type_full.replace("archimate:", ""))
        
        sorted_types = sorted(list(entity_types))

        # --- Widgets ---
        top_frame = tk.Frame(self.catalog_win)
        top_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(top_frame, text="Entity Type:").pack(side="left")
        
        type_var = tk.StringVar()
        type_combo = ttk.Combobox(top_frame, textvariable=type_var, values=sorted_types, state="readonly")
        type_combo.pack(side="left", fill="x", expand=True, padx=5)

        text_frame = tk.Frame(self.catalog_win)
        text_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        entity_list_text = tk.Text(text_frame, wrap="none")
        entity_list_text.pack(side="left", fill="both", expand=True)
        
        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=entity_list_text.yview)
        text_scroll.pack(side="right", fill="y")
        entity_list_text.config(yscrollcommand=text_scroll.set)

        bottom_frame = tk.Frame(self.catalog_win)
        bottom_frame.pack(fill="x", padx=10, pady=5)

        def copy_to_clipboard():
            content = entity_list_text.get("1.0", "end-1c")
            if content:
                self.root.clipboard_clear()
                self.root.clipboard_append(content)
                
        copy_button = tk.Button(bottom_frame, text="Copy List to Clipboard", command=copy_to_clipboard)
        copy_button.pack(side="right")

        # --- Logic to update the list when a type is selected ---
        def on_type_selected(*args):
            selected_type = type_var.get()
            if not selected_type:
                return
            
            entity_list_text.config(state="normal")
            entity_list_text.delete("1.0", "end")

            names = []
            for el in self.model.findall(".//element"):
                el_type_full = el.get(f"{{{XSI}}}type", "")
                if el_type_full.replace("archimate:", "") == selected_type:
                    name = el.get("name")
                    if name:
                        names.append(name)
            
            entity_list_text.insert("1.0", "\n".join(sorted(names)))
            entity_list_text.config(state="disabled")

        type_var.trace_add('write', on_type_selected)

    # --- Gemini Context Management ---

    def extract_model_inventory(self):
        """Builds a compact entity inventory."""
        if self.model is None:
            return []
        inventory = []
        for el in self.model.findall(".//element"):
            etype = el.get(f"{{{XSI}}}type", "").replace("archimate:", "")
            name = el.get("name", "")
            if name:
                inventory.append(f"{etype} | {name}")
        return inventory

    def extract_model_triples(self):
        """Builds compact triples of relationships."""
        if self.model is None:
            return []
        triples = []
        for rel in self.find_all_relationships():
            rel_type = rel.get(f"{{{XSI}}}type", "").replace("archimate:", "")
            src = self.element_db_by_id.get(rel.get("source"), {}).get("name", "")
            tgt = self.element_db_by_id.get(rel.get("target"), {}).get("name", "")
            if src and tgt:
                triples.append(f"{src} -> {rel_type} -> {tgt}")
        return triples

    def handle_ask_gemini(self):
        """Handles the Ask Gemini button press from the main GUI panel."""
        prompt = self.gemini_prompt_text.get("1.0", "end").strip()
        if not prompt or "e.g.," in prompt:
            messagebox.showwarning("Gemini", "Please enter a valid prompt.")
            return
        
        self._send_to_gemini(prompt)

    def build_gemini_context(self, delta_only=False):
        """Builds the context payload (inventory + triples, or delta)."""
        if delta_only and hasattr(self, "_last_snapshot"):
            # Compute delta
            current_inv = set(self.extract_model_inventory())
            current_triples = set(self.extract_model_triples())
            old_inv, old_triples = self._last_snapshot
            new_inv = current_inv - old_inv
            new_triples = current_triples - old_triples
            context = ["# Delta Model Update"]
            if new_inv:
                context.append("Entities:\n" + "\n".join(sorted(new_inv)))
            if new_triples:
                context.append("Relationships:\n" + "\n".join(sorted(new_triples)))
        else:
            # Full snapshot
            inv = self.extract_model_inventory()
            triples = self.extract_model_triples()
            context = ["# Full Model Inventory"]
            context.append("Entities:\n" + "\n".join(sorted(inv)))
            context.append("Relationships:\n" + "\n".join(sorted(triples)))
            # Store snapshot
            self._last_snapshot = (set(inv), set(triples))
        return "\n\n".join(context)

    def resend_inventory(self):
        """Forces resending full inventory on next Gemini call."""
        self.gemini_context_sent = False
        messagebox.showinfo("Gemini", "Inventory will be resent on the next request.")


    def _send_to_gemini(self, prompt):
        """Sends a prompt to the Gemini API and adds the response to the paste area."""
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY":
            messagebox.showerror("Gemini API Error", "Please set your GEMINI_API_KEY at the top of the script.")
            return

        self.gemini_generate_button.config(text="Thinking...", state="disabled")
        self.status_var.set("Asking Gemini...")
        self.root.update_idletasks()  # Force UI update

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            selected_model = self.model_var.get().strip() or "models/gemini-2.5-pro"

            model = genai.GenerativeModel(selected_model)
            # Prepare context
            if not hasattr(self, "gemini_context_sent"):
                self.gemini_context_sent = False
            if not hasattr(self, "gemini_delta_mode"):
                self.gemini_delta_mode = False

            context = ""
            if not self.gemini_context_sent:
                context = self.build_gemini_context(delta_only=False)
                self.gemini_context_sent = True
            elif self.gemini_delta_mode:
                context = self.build_gemini_context(delta_only=True)
            # Construct a detailed prompt for the model
            system_prompt = f"""
You are an expert in Enterprise Architecture and the ArchiMate modeling language.
Your task is to represent the results of a user's request as TOGAF architecture elements in a specific text format that can be parsed by a tool.
The output format is a list of elements and relationships, one per line.

The format for elements is:
ElementType | ElementName | attribute1=value1 | attribute2=value2

The format for relationships is:
RelationshipType | SourceElementName | target=TargetElementName | attribute1=value1

Here are some valid element types you should use:
{', '.join(COMMON_TYPES)}

Here are the valid relationship types you should use:
{', '.join(RELATIONSHIP_TYPES)}

RULES:
1.  ONLY output text in the specified format.
2.  No commentary or explanations.
3.  Do NOT use markdown code blocks (```) in your response.
4.  If the user's request is ambiguous, make a reasonable assumption based on common architectural patterns.
5.  Ensure the relationship's source and target names exactly match the names of the elements you define.
6.  If an element is mentioned multiple times, ensure it is only defined once.
7.  Use 'description' as an attribute to provide additional details about elements or relationships.
8.  If the user requests multiple elements or relationships, list each on a new line.
9.  If the user requests an element type or relationship type not in the provided lists, substitute with the closest valid type.
10.  If the user requests a relationship between two elements that is not valid according to ArchiMate rules, choose the closest valid relationship type or omit the relationship if no valid type exists.
11.  If the user requests an element or relationship that already exists in the model (based on the names), do not create a duplicate; instead, reference the existing element by name.

Here is any current model or context:
{context}

User's request: "{prompt}"
"""

            response = model.generate_content(system_prompt)
            response_text = response.text.strip()

            if not response_text:
                messagebox.showinfo("Gemini", "Received an empty response.")
                return

            current_paste_content = self.paste_text.get("1.0", "end").strip()
            if current_paste_content:
                self.paste_text.insert("end", f"\n# --- Gemini Response for: \"{prompt}\" ---\n" + response_text)
            else:
                self.paste_text.insert("end", response_text)
            
            self.update_staged_preview()
            messagebox.showinfo("Gemini", "Response added to Paste Area.")

        except Exception as e:
            messagebox.showerror("Gemini API Error", f"An error occurred: {e}")
        finally:
            self.gemini_generate_button.config(text="Generate!", state="normal")
            self.status_var.set("Ready.")

    # --- Autocomplete Feature ---

    def _create_progress_window(self, title, max_value):
        """Creates and displays a standardized progress bar window."""
        progress_win = tk.Toplevel(self.root)
        progress_win.title(title)
        progress_win.geometry("450x120")
        progress_win.transient(self.root)
        progress_win.grab_set()
        progress_win.resizable(False, False)

        tk.Label(progress_win, text=f"Processing: {title}...", font=("Segoe UI", 10)).pack(pady=(10, 5))
        
        progress_bar = ttk.Progressbar(progress_win, orient="horizontal", length=400, mode="determinate", maximum=max_value)
        progress_bar.pack(pady=5)
        
        status_label = tk.Label(progress_win, text="Initializing...")
        status_label.pack(pady=5)

        return progress_win, progress_bar, status_label

    def autocomplete_model_conservative(self):
        """
        Scans the model and adds missing ArchiMate entities and relationships based on a configurable set of conservative rules.
        """
        if self.model is None:
            messagebox.showwarning("No model", "Open an .archimate file first.")
            return

        self.save_history()
        added_elements_log = []
        added_relationships_log = []

        # Build a comprehensive list of all elements
        elements_by_type = {}
        all_elements_by_id = {}
        for folder in self.model.findall("folder"):
            for el in folder.findall("element"):
                el_id = el.get("id")
                el_name = el.get("name", "")
                el_type_full = el.get(f"{{{XSI}}}type", "")
                el_type = el_type_full.replace("archimate:", "")
                if el_id and el_name and el_type:
                    if el_type not in elements_by_type:
                        elements_by_type[el_type] = []
                    element_data = {'id': el_id, 'type': el_type, 'name': el_name, 'el': el}
                    elements_by_type[el_type].append(element_data)
                    all_elements_by_id[el_id] = element_data

        # --- Progress Bar Setup ---
        total_iterations = 0
        for rule in AUTOCOMPLETE_RULES:
            source_elements = []
            for el_type in rule['source_types']:
                source_elements.extend(elements_by_type.get(el_type, []))
            target_elements = []
            for el_type in rule['target_types']:
                target_elements.extend(elements_by_type.get(el_type, []))
            total_iterations += len(source_elements) * len(target_elements)

        if total_iterations == 0:
            messagebox.showinfo("Autocomplete", "No element pairs to check.")
            return

        progress_win, progress_bar, status_label = self._create_progress_window("Autocomplete", total_iterations)
        current_iteration = 0

        try:
            # --- Rule Processing Engine ---
            for rule in AUTOCOMPLETE_RULES:
                source_elements = []
                for el_type in rule['source_types']:
                    source_elements.extend(elements_by_type.get(el_type, []))

                target_elements = []
                for el_type in rule['target_types']:
                    target_elements.extend(elements_by_type.get(el_type, []))

                for source_data in source_elements:
                    for target_data in target_elements:
                        current_iteration += 1
                        if current_iteration % 100 == 0:  # Update UI periodically to avoid slowdown
                            progress_bar['value'] = current_iteration
                            status_label.config(text=f"Rule: {rule['name'][:40]}...")
                            self.root.update_idletasks()

                        if self._evaluate_autocomplete_conditions(rule['conditions'], source_data, target_data):
                            new_els, new_rels = self._execute_autocomplete_action(rule, source_data, target_data, all_elements_by_id)
                            added_elements_log.extend(new_els)
                            added_relationships_log.extend(new_rels)
        finally:
            progress_win.destroy()

        # Update the element database and refresh
        self.build_element_database()
        self.build_relationship_map()
        self.calculate_relationship_counts()
        self.refresh_tree()
        self.update_xml_output_panel()

        if added_elements_log or added_relationships_log:
            self.dirty = True
        self.update_button_states()

        # Show results
        result_msg = "Autocomplete completed based on configurable rules.\n"
        if added_elements_log:
            result_msg += f"Added {len(added_elements_log)} elements:\n- " + "\n- ".join(added_elements_log) + "\n\n"
        if added_relationships_log:
            result_msg += f"Added {len(added_relationships_log)} relationships:\n- " + "\n- ".join(added_relationships_log)

        if not added_elements_log and not added_relationships_log:
            result_msg = "No missing elements or relationships found based on the current rules."

        self._show_report_window("Autocomplete Report", result_msg)
    # Add a more conservative validation function
    def validate_relationships_conservative(self):
        """
        Conservative validation that focuses on the most problematic relationship types.
        """
        if self.model is None:
            messagebox.showwarning("No model", "Open an .archimate file first.")
            return
    
        # Focus on the most common illegal relationships
        common_illegal_patterns = [
            # Requirement -> BusinessService: Realization is illegal
            ("Requirement", "BusinessService", "RealizationRelationship"),
            # BusinessService -> ApplicationComponent: Realization is questionable
            ("BusinessService", "ApplicationComponent", "RealizationRelationship"),
            # ApplicationComponent -> BusinessActor: Serving is questionable
            ("ApplicationComponent", "BusinessActor", "ServingRelationship"),
        ]
    
        illegal_relationships = []
    
        for folder in self.model.findall("folder"):
            for rel in folder.findall("element"):
                rel_type = rel.get(f"{{{XSI}}}type", "")
                if not rel_type.endswith("Relationship"):
                    continue
                 
                source_id = rel.get("source")
                target_id = rel.get("target")
            
                source_el = self.find_element_by_id(source_id)
                target_el = self.find_element_by_id(target_id)
            
                if source_el is None or target_el is None:
                    continue
                 
                source_type = source_el.get(f"{{{XSI}}}type", "").replace("archimate:", "")
                target_type = target_el.get(f"{{{XSI}}}type", "").replace("archimate:", "")
            
                # Check against common illegal patterns
                for illegal_pattern in common_illegal_patterns:
                    if (source_type == illegal_pattern[0] and 
                        target_type == illegal_pattern[1] and 
                        rel_type.endswith(illegal_pattern[2])):
                    
                        source_name = source_el.get("name", "Unnamed")
                        target_name = target_el.get("name", "Unnamed")
                        illegal_relationships.append({
                            "relationship": rel_type,
                            "source": f"{source_type}: {source_name}",
                            "target": f"{target_type}: {target_name}",
                            "pattern": f"{illegal_pattern[0]} -> {illegal_pattern[1]} with {illegal_pattern[2]}"
                        })
                        break
    
        if not illegal_relationships:
            messagebox.showinfo("Validation", "No problematic relationships found!")
            return
    
        # Build the report string
        report_content = f"Found {len(illegal_relationships)} potentially problematic relationships:\n\n"
        for i, rel in enumerate(illegal_relationships, 1):
            report_content += f"{i}. {rel['pattern']}\n"
            report_content += f"   Source: {rel['source']}\n"
            report_content += f"   Target: {rel['target']}\n\n"
            
        self._show_report_window("Problematic Relationships Report", report_content)
    
     
    
    def is_relationship_allowed(self, source_type, target_type, relationship_type):
        """
        Check if a relationship is allowed between two element types according to ArchiMate spec.
        """
        # Remove namespace prefix if present
        if ":" in source_type:
            source_type = source_type.split(":")[-1]
        if ":" in target_type:
            target_type = target_type.split(":")[-1]
        if ":" in relationship_type:
            relationship_type = relationship_type.split(":")[-1]
    
        # Get rules for source type, fall to back to default rules
        rules = RELATIONSHIP_RULES.get(source_type, RELATIONSHIP_RULES["*"])
    
        # Check if this relationship type is allowed for the source
        if relationship_type not in rules["allowed_targets"]:
            return False
    
        # Check if the target type is allowed for this relationship
        allowed_targets = rules["allowed_targets"][relationship_type]
        if "*" in allowed_targets:
            return True
        return target_type in allowed_targets

    def validate_all_relationships(self):
        """
        Scan all relationships in the model and identify illegal ones.
        """
        illegal_relationships = []
    
        for folder in self.model.findall("folder"):
            for rel in folder.findall("element"):
                rel_type = rel.get(f"{{{XSI}}}type", "")
                if not rel_type.endswith("Relationship"):
                    continue
                 
                source_id = rel.get("source")
                target_id = rel.get("target")
            
                source_el = self.find_element_by_id(source_id)
                target_el = self.find_element_by_id(target_id)
            
                if source_el is None or target_el is None:
                    continue
                 
                source_type = source_el.get(f"{{{XSI}}}type", "")
                target_type = target_el.get(f"{{{XSI}}}type", "")
            
                if not self.is_relationship_allowed(source_type, target_type, rel_type):
                    source_name = source_el.get("name", "Unnamed")
                    target_name = target_el.get("name", "Unnamed")
                    illegal_relationships.append({
                        "relationship": rel_type,
                        "source": f"{source_type}: {source_name}",
                        "target": f"{target_type}: {target_name}"
                    })
    
        return illegal_relationships
    def fix_and_refresh(self, window):
        """
        Fix illegal relationships and refresh the report window.
        """
        fixed_count, illegal_count = self.fix_illegal_relationships()
        self.refresh_tree()
        self.update_xml_output_panel()
    
        messagebox.showinfo("Fix Complete", 
                           f"Fixed {fixed_count} of {illegal_count} illegal relationships.")
        window.destroy()
    def fix_illegal_relationships(self):
        """
        Attempt to fix illegal relationships by replacing them with legal alternatives.
        """
        illegal_relationships = self.validate_all_relationships()
        fixed_count = 0
    
        for illegal_rel in illegal_relationships:
            rel_type = illegal_rel["relationship"]
            source_type = illegal_rel["source"].split(":")[0].strip()
            target_type = illegal_rel["target"].split(":")[0].strip()
        
            # Find the relationship element to fix
            for folder in self.model.findall("folder"):
                for rel in folder.findall("element"):
                    if rel.get(f"{{{XSI}}}type", "") == rel_type:
                        source_id = rel.get("source")
                        target_id = rel.get("target")
                    
                        source_el = self.find_element_by_id(source_id)
                        target_el = self.find_element_by_id(target_id)
                    
                        if (source_el and source_el.get("name", "") in illegal_rel["source"] and
                            target_el and target_el.get("name", "") in illegal_rel["target"]):
                        
                            # Try to find a legal alternative relationship type
                            alternative_rel = self.find_legal_alternative(source_type, target_type, rel_type)
                        
                            if alternative_rel:
                                # Replace the relationship type
                                rel.set(f"{{{XSI}}}type", f"archimate:{alternative_rel}")
                                fixed_count += 1
                            else:
                                # No legal alternative found, remove the relationship
                                folder.remove(rel)
                                fixed_count += 1
    
        return fixed_count, len(illegal_relationships)

    def find_legal_alternative(self, source_type, target_type, original_rel_type):
        """
        Find a legal alternative relationship type for the given source and target types.
        """
        # Common illegal relationship fixes
        relationship_fixes = {
            # Requirement -> BusinessService: RealizationRelationship is illegal
            ("Requirement", "BusinessService", "RealizationRelationship"): "InfluenceRelationship",
            # BusinessService -> ApplicationService: RealizationRelationship is legal, but sometimes mistaken
            ("BusinessService", "ApplicationService", "RealizationRelationship"): "ServingRelationship",
            # ApplicationService -> TechnologyService: RealizationRelationship is legal, but sometimes mistaken
            ("ApplicationService", "TechnologyService", "RealizationRelationship"): "ServingRelationship",
        }
    
        # Check for specific fixes
        key = (source_type, target_type, original_rel_type)
        if key in relationship_fixes:
            return relationship_fixes[key]
    
        # Generic fallback: try to find any legal relationship
        rules = RELATIONSHIP_RULES.get(source_type, RELATIONSHIP_RULES["*"])
        for rel_type, allowed_targets in rules["allowed_targets"].items():
            if "*" in allowed_targets or target_type in allowed_targets:
                return rel_type
    
        return None    
    RELATIONSHIP_FIX_PRIORITY = [
        "AssociationRelationship", "InfluenceRelationship", "ServingRelationship", 
        "UsedByRelationship", "AccessRelationship", "FlowRelationship", 
        "TriggeringRelationship", "RealizationRelationship", "AssignmentRelationship", 
        "SpecializationRelationship", "CompositionRelationship", "AggregationRelationship"
    ]

    def _find_alternative_relationship(self, source_type, target_type):
        """Finds all valid relationship types from a source type to a target type."""
        valid_rels = []
        source_type_short = source_type.split(":")[-1]
        target_type_short = target_type.split(":")[-1]

        source_rules = RELATIONSHIP_RULES.get(source_type_short, {})
        for rel_type, allowed_targets in source_rules.get("allowed_targets", {}).items():
            if "*" in allowed_targets or target_type_short in allowed_targets:
                valid_rels.append(rel_type)

        default_rules = RELATIONSHIP_RULES.get("*", {})
        for rel_type, allowed_targets in default_rules.get("allowed_targets", {}).items():
            if rel_type not in valid_rels and ("*" in allowed_targets or target_type_short in allowed_targets):
                valid_rels.append(rel_type)
        
        return valid_rels

    def _attempt_to_fix_relationship(self, rel):
        """Tries to fix an illegal relationship by changing its type or direction."""
        source_el = self.find_element_by_id(rel.get("source"))
        target_el = self.find_element_by_id(rel.get("target"))
        
        if source_el is None or target_el is None:
            return None

        source_type = source_el.get(f"{{{XSI}}}type")
        target_type = target_el.get(f"{{{XSI}}}type")
        original_rel_type = rel.get(f"{{{XSI}}}type")
        
        source_name = source_el.get("name", "Unnamed")
        target_name = target_el.get("name", "Unnamed")
        original_rel_type_short = original_rel_type.split(':')[-1]

        # Attempt 1: Change direction (if current type is valid in reverse)
        if self.is_relationship_allowed(target_type, source_type, original_rel_type):
            rel.set("source", target_el.get("id"))
            rel.set("target", source_el.get("id"))
            return f"Reversed direction of {original_rel_type_short} between '{target_name}' and '{source_name}'."

        # Attempt 2: Find alternative relationship type (same direction)
        valid_rels_same_dir = self._find_alternative_relationship(source_type, target_type)
        if valid_rels_same_dir:
            for best_rel in self.RELATIONSHIP_FIX_PRIORITY:
                if best_rel in valid_rels_same_dir:
                    rel.set(f"{{{XSI}}}type", f"archimate:{best_rel}")
                    
                    return f"Changed type from {original_rel_type_short} to {best_rel} for '{source_name}' -> '{target_name}'."


        # Attempt 3: Find alternative relationship type (reversed direction)
        valid_rels_rev_dir = self._find_alternative_relationship(target_type, source_type)
        if valid_rels_rev_dir:
            for best_rel in self.RELATIONSHIP_FIX_PRIORITY:
                if best_rel in valid_rels_rev_dir:
                    rel.set("source", target_el.get("id"))
                    rel.set("target", source_el.get("id"))
                    rel.set(f"{{{XSI}}}type", f"archimate:{best_rel}")
                    return f"Reversed and changed type from {original_rel_type_short} to {best_rel} for '{target_name}' -> '{source_name}'."

        return None # No fix found

    def find_all_relationships(self):
        """
        Finds and returns a list of all relationship elements in the model.
        """
        if self.model is None:
            return []
        relationships = []
        for folder in self.model.findall("folder"):
            for element in folder.findall("element"):
                if element.get(f"{{{XSI}}}type", "").endswith("Relationship"):
                    relationships.append(element)
        return relationships

    def validate_and_clean_relationships(self):
        """
        Performs a full validation and cleaning of relationships in the model.
        1. Removes orphaned relationships (invalid source/target).
        2. Removes duplicate relationships.
        3. Attempts to fix illegal relationships by changing type or direction.
        4. Removes relationships that cannot be fixed.
        5. Provides a detailed report of all actions taken.
        """
        if self.model is None:
            messagebox.showwarning("No model", "Open an .archimate file first.")
            return

        self.save_history()
        other_folder_log = []
        orphans_removed_log = []
        duplicates_removed_log = []
        fixed_rels_log = []
        unfixable_rels_log = []

        # --- Progress Bar Setup ---
        all_relationships = self.find_all_relationships()
        other_folder_elements = self.model.findall("./folder[@type='other']/element")
        total_steps = len(other_folder_elements) + len(all_relationships) * 3 # Add new step to total
        
        progress_win, progress_bar, status_label = self._create_progress_window("Clean & Validate", total_steps)
        current_step = 0

        try:
            # --- Step 0: Tidy 'Other' Folder ---
            status_label.config(text="Tidying 'Other' folder...")
            self.root.update_idletasks()
            
            other_folder = self.model.find("./folder[@type='other']")
            if other_folder is not None:
                elements_to_process = list(other_folder) # Create a copy to iterate over
                for el in elements_to_process:
                    current_step += 1
                    progress_bar['value'] = current_step

                    el_type_full = el.get(f"{{{XSI}}}type", "")
                    el_type_short = el_type_full.split(":")[-1]
                    el_name = el.get("name", "[Unnamed]")
                    moved = False

                    # Is it a relationship? Move to Relations folder.
                    if el_type_short.endswith("Relationship") or el_type_short in RELATIONSHIP_TYPES:
                        relations_folder = self.get_or_create_relations_folder()
                        if relations_folder is not other_folder:
                            relations_folder.append(el)
                            other_folder.remove(el)
                            other_folder_log.append(f"Moved relationship '{el_name}' to 'Relations' folder.")
                            moved = True
                    
                    # Is it a standard element? Move to its correct folder.
                    elif el_type_short in FOLDER_MAP:
                        correct_folder = self.get_folder_for_type(el_type_short)
                        if correct_folder is not None and correct_folder is not other_folder:
                            correct_folder.append(el)
                            other_folder.remove(el)
                            other_folder_log.append(f"Moved element '{el_name}' to '{correct_folder.get('name')}' folder.")
                            moved = True

                    # If it couldn't be moved, it might be unclassifiable and should be deleted.
                    if not moved:
                        folder_name_for_type = FOLDER_MAP.get(el_type_short, None)
                        if folder_name_for_type is None and el_type_full:
                            other_folder.remove(el)
                            other_folder_log.append(f"Deleted unclassifiable element '{el_name}' (type: {el_type_short}) from 'Other' folder.")

            # --- Step 1: Remove Orphans ---
            status_label.config(text="Checking for orphaned relationships...")
            self.root.update_idletasks()
            valid_ids = {element.get("id") for element in self.model.findall(".//element")}
            
            all_relationships = self.find_all_relationships() # Re-fetch after potential moves
            rels_to_process = []
            for rel in all_relationships:
                current_step += 1
                progress_bar['value'] = current_step
                source_id = rel.get("source")
                target_id = rel.get("target")
                if source_id not in valid_ids or target_id not in valid_ids:
                    source_name = self.element_db_by_id.get(source_id, {}).get('name', f'ID: {source_id}')
                    target_name = self.element_db_by_id.get(target_id, {}).get('name', f'ID: {target_id}')
                    rel_type_short = rel.get(f"{{{XSI}}}type", "Rel").split(':')[-1]
                    orphans_removed_log.append(f"Removed orphaned '{rel_type_short}' from '{source_name}' to '{target_name}'")
                    self._find_and_remove_element(rel)
                else:
                    rels_to_process.append(rel)

            # --- Step 2: Remove Duplicates ---
            status_label.config(text="Checking for duplicate relationships...")
            self.root.update_idletasks()
            unique_relationships = set()
            for rel in list(rels_to_process): # Iterate over a copy
                current_step += 1
                progress_bar['value'] = current_step
                source_id = rel.get("source")
                target_id = rel.get("target")
                rel_type_full = rel.get(f"{{{XSI}}}type", "")
                rel_tuple = (source_id, target_id, rel_type_full)

                if rel_tuple in unique_relationships:
                    source_name = self.find_element_by_id(rel.get("source")).get('name', 'Unnamed')
                    target_name = self.find_element_by_id(rel.get("target")).get('name', 'Unnamed')
                    rel_type_short = rel.get(f"{{{XSI}}}type").split(':')[-1]
                    duplicates_removed_log.append(f"Removed duplicate '{rel_type_short}' from '{source_name}' to '{target_name}'")
                    self._find_and_remove_element(rel)
                    rels_to_process.remove(rel)
                else:
                    unique_relationships.add(rel_tuple)

            # --- Step 3: Fix Illegal Relationships ---
            status_label.config(text="Fixing illegal relationships...")
            self.root.update_idletasks()
            for rel in list(rels_to_process): # Iterate over a copy
                current_step += 1
                progress_bar['value'] = current_step
                source_el = self.find_element_by_id(rel.get("source"))
                target_el = self.find_element_by_id(rel.get("target"))
                
                if not self.is_relationship_allowed(source_el.get(f"{{{XSI}}}type"), target_el.get(f"{{{XSI}}}type"), rel.get(f"{{{XSI}}}type")):
                    fix_desc = self._attempt_to_fix_relationship(rel)
                    if fix_desc:
                        fixed_rels_log.append(fix_desc)
                    else:
                        # Unfixable, remove it
                        source_name = source_el.get("name", "Unnamed")
                        target_name = target_el.get("name", "Unnamed")
                        rel_type_short = rel.get(f"{{{XSI}}}type").split(':')[-1]
                        unfixable_rels_log.append(f"Removed unfixable '{rel_type_short}' from '{source_name}' to '{target_name}'")
                        self._find_and_remove_element(rel)
        finally:
            progress_win.destroy()

        # --- Step 4: Update UI and Report ---
        self.build_element_database()
        self.build_relationship_map()
        self.calculate_relationship_counts()
        self.refresh_tree()
        self.update_xml_output_panel()

        # Build and show report
        report_content = "Validation and Cleaning Report:\n\n"
        report_content += f"--- Summary ---\n"
        report_content += f"Actions in 'Other' folder: {len(other_folder_log)}\n"
        report_content += f"Orphaned relationships removed: {len(orphans_removed_log)}\n"
        report_content += f"Duplicate relationships removed: {len(duplicates_removed_log)}\n"
        report_content += f"Illegal relationships fixed: {len(fixed_rels_log)}\n"
        report_content += f"Unfixable relationships removed: {len(unfixable_rels_log)}\n\n"

        if other_folder_log:
            report_content += "--- 'Other' Folder Cleanup ---\n"
            report_content += "\n".join([f"- {log}" for log in other_folder_log]) + "\n\n"

        if fixed_rels_log:
            report_content += "--- Fixes Applied ---\n"
            report_content += "\n".join([f"- {log}" for log in fixed_rels_log]) + "\n\n"
        
        if unfixable_rels_log:
            report_content += "--- Unfixable Relationships (Removed) ---\n"
            report_content += "\n".join([f"- {log}" for log in unfixable_rels_log]) + "\n\n"

        if orphans_removed_log:
            report_content += "--- Orphaned Relationships (Removed) ---\n"
            report_content += "\n".join([f"- {log}" for log in orphans_removed_log]) + "\n\n"

        if duplicates_removed_log:
            report_content += "--- Duplicate Relationships (Removed) ---\n"
            report_content += "\n".join([f"- {log}" for log in duplicates_removed_log]) + "\n\n"

        if not any([other_folder_log, orphans_removed_log, duplicates_removed_log, fixed_rels_log, unfixable_rels_log]):
            report_content = "Validation Complete: No issues found."

        self._show_report_window("Validation Report", report_content)

    # --- File I/O ---
    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("ArchiMate files", "*.archimate;*.xml"), ("All files","*.*")])
        if not path:
            return
        try:
            self.tree = ET.parse(path)
            self.model = self.tree.getroot()
            self.filepath = path
            self.dirty = False # Freshly loaded file is not dirty
            self.history.clear()
            self.element_db.clear()
            self.build_element_database()
            self.build_relationship_map()
            self.calculate_relationship_counts()
            self.save_history()
            self.status_var.set(f"Loaded: {os.path.basename(path)}")
            self.refresh_tree()
            self.update_staged_preview()
            self.update_xml_output_panel()
            self.update_button_states()
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
            xml_str = ET.tostring(self.model, encoding='utf-8').decode()
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ")
            lines = pretty_xml.split('\n')
            if lines[0].startswith('<?xml'):
                lines = lines[1:]
            pretty_xml = '\n'.join(lines).strip()
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<?xml version=\'1.0\' encoding=\'utf-8\'?>\n')
                f.write(pretty_xml)
            self.dirty = False # Saved, so no longer dirty
            messagebox.showinfo("Saved", f"Saved to {path}")
            self.status_var.set(f"Saved: {os.path.basename(path)}")
            self.update_button_states()
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save file:\n{e}")

    def build_element_database(self):
        if self.model is None:
            return
        self.element_db.clear()
        self.element_db_by_id = {}
        for element in self.model.findall(".//element"):
            name = element.get("name")
            element_id = element.get("id")
            element_type = element.get(f"{{{XSI}}}type", "")
            if name and element_id:
                self.element_db[name] = (element_id, element_type)
                self.element_db[name.lower()] = (element_id, element_type)
            if element_id:
                self.element_db_by_id[element_id] = {'name': name, 'type': element_type}

    def build_relationship_map(self):
        """Builds a cache for quick lookup of relationships for each element."""
        self.relationship_map = {}
        if self.model is None:
            return
        
        # Initialize map for all non-relationship elements
        for el in self.model.findall(".//element"):
            el_id = el.get("id")
            etype = el.get(f"{{{XSI}}}type", "")
            if el_id and "Relationship" not in etype:
                self.relationship_map[el_id] = []

        # Populate map with relationships
        for rel in self.find_all_relationships():
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get(f"{{{XSI}}}type", "").split(":")[-1]

            if source_id and source_id in self.relationship_map and target_id:
                self.relationship_map[source_id].append({'id': target_id, 'type': rel_type, 'direction': 'out'})
            
            if target_id and target_id in self.relationship_map and source_id:
                self.relationship_map[target_id].append({'id': source_id, 'type': rel_type, 'direction': 'in'})

    def calculate_relationship_counts(self):
        """Calculates incoming and outgoing relationship counts for each element."""
        if self.model is None:
            self.relationship_counts = {}
            return

        counts = {}
        # Initialize all elements with zero counts
        for el in self.model.findall(".//element"):
            el_id = el.get("id")
            if el_id:
                counts[el_id] = {'in': 0, 'out': 0}

        # Iterate through relationships and increment counts
        for rel in self.model.findall(".//element"):
            rel_type = rel.get(f"{{{XSI}}}type", "")
            if rel_type and rel_type.split(":")[-1] in RELATIONSHIP_TYPES:
                source_id = rel.get("source")
                target_id = rel.get("target")
                if source_id and source_id in counts:
                    counts[source_id]['out'] += 1
                if target_id and target_id in counts:
                    counts[target_id]['in'] += 1
        
        self.relationship_counts = counts
    # --- TreeView ---
    def refresh_tree(self, filter_text=""):
        self.treeview.delete(*self.treeview.get_children())
        if self.model is None:
            return
        
        filter_text = filter_text.lower()

        root_label = f"archimate:model | {self.model.get('name','')}"
        root_id = self.treeview.insert("", "end", text=root_label, open=True, values=("model",))
        for folder in self.model.findall("folder"):
            fname = folder.get("name", "Folder")
            ftype = folder.get("type", "")
            folder_id = self.treeview.insert(root_id, "end", text=f"{fname} ({ftype})", values=("folder", folder.get("id","")), open=bool(filter_text))
            for el in folder.findall("element"):
                etype_full = el.get(f"{{{XSI}}}type", "")
                etype = etype_full.split(":")[-1] if ":" in etype_full else etype_full
                name = el.get("name","")
                el_id = el.get("id","")
                if filter_text and filter_text not in name.lower():
                    continue

                counts = self.relationship_counts.get(el_id, {'in': 0, 'out': 0})
                el_label = f"[{counts['in']}] > {name} < [{counts['out']}]" if name else f"{etype}"
                el_node = self.treeview.insert(folder_id, "end", text=el_label, values=("element", el_id))
                # The following block is commented out as it was from a previous version
                # for child in list(el):
                #     ctag = child.tag
                #     ctext = (child.text or "").strip()
                #     if ctext:
                #         child_label = f"{ctag}: {ctext}"
                #         self.treeview.insert(el_node, "end", text=child_label)
        self.update_xml_output_panel()

    def search_tree(self, *args):
        # Filters the treeview based on the search entry."""
        self.refresh_tree(self.search_var.get())

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
                    ctag = child.tag
                    ctext = (child.text or "").strip()
                    self.details_text.insert("end", f"{ctag}: {ctext}\n")
        self.details_text.config(state="disabled")

    # --- Paste Area handling ---
    def clear_paste(self):
        self.paste_text.delete("1.0", "end")
        self.update_staged_preview()
        self.update_button_states()

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
            self.update_button_states()
            self.paste_text.edit_modified(False)

    def update_staged_preview(self):
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        text = self.paste_text.get("1.0", "end").strip()
        if not text:
            self.preview_text.insert("end", "(no staged entries)\n")
            self.preview_text.config(state="disabled")
            return

        # Build a temp element_db for preview so relationships can resolve IDs
        temp_db = dict(self.element_db)
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
        snippets = []
        temp_ids = {}

        # First pass: assign IDs to new elements
        for ln in lines:
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2:
                continue
            raw_type = parts[0]
            short = raw_type.split(":")[-1]
            if short.endswith("Relationship") or short in RELATIONSHIP_TYPES:
                continue
            name = parts[1]
            if name not in temp_db:
                new_id = generate_id()
                temp_db[name] = (new_id, f"archimate:{raw_type}")
                temp_db[name.lower()] = (new_id, f"archimate:{raw_type}")
                temp_ids[name] = new_id

        # Second pass: generate XML snippets
        for ln in lines:
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2:
                snippets.append(f"<!-- Could not parse: {ln} -->")
                continue
            raw_type = parts[0]
            short = raw_type.split(":")[-1]
            if short.endswith("Relationship") or short in RELATIONSHIP_TYPES:
                src_name = parts[1]
                extras = {}
                for extra in parts[2:]:
                    if "=" in extra:
                        k,v = extra.split("=",1)
                        extras[k.strip()] = v.strip()
                tgt_name = extras.get("target")
                descr = extras.get("description")
                src_id = temp_db.get(src_name, (None,))[0]
                tgt_id = temp_db.get(tgt_name, (None,))[0]
                snippet = f'<element xsi:type="archimate:{short}"'
                snippet += f' source="{src_id or "[source_id]"}" target="{tgt_id or "[target_id]"}"'
                if descr:
                    snippet += f' description="{descr}"'
                snippet += ' />'
                snippets.append(snippet)
            else:
                name = parts[1]
                extras = {}
                for extra in parts[2:]:
                    if "=" in extra:
                        k,v = extra.split("=",1)
                        extras[k.strip()] = v.strip()
                doc = extras.get("description")
                el_id = temp_db.get(name, (None,))[0] or "[new_id]"
                snippet = f'<element xsi:type="archimate:{raw_type}" name="{name}" id="{el_id}"'
                if doc:
                    snippet += f'>\n  <documentation>{doc}</documentation>\n</element>'
                else:
                    snippet += ' />'
                snippets.append(snippet)
        for s in snippets:
            self.preview_text.insert("end", s + "\n")
        self.preview_text.config(state="disabled")

    # --- Insert / Commit ---
    def insert_from_paste(self):
        if self.model is None:
            messagebox.showwarning("No model", "Open an .archimate file first.")
            return
        paste = self.paste_text.get("1.0", "end").strip()
        if not paste:
            messagebox.showinfo("Nothing to insert", "Paste Area is empty.")
            return
        lines = [l.strip() for l in paste.splitlines() if l.strip() and not l.startswith("#")]
        if not lines:
            messagebox.showinfo("Nothing to insert", "Paste Area is empty.")
            return

        self.save_history()
        created_elements = []
        relationships_to_create = []
        self.create_default_folders()

        # First pass: create elements and assign IDs
        for ln in lines:
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2:
                continue
            raw_type = parts[0]
            short = raw_type.split(":")[-1]
            if short.endswith("Relationship") or short in RELATIONSHIP_TYPES:
                src_name = parts[1]
                extras = {}
                for extra in parts[2:]:
                    if "=" in extra:
                        k,v = extra.split("=",1)
                        extras[k.strip()] = v.strip()
                tgt_name = extras.get("target")
                descr = extras.get("description")
                relationships_to_create.append({
                    "type": short,
                    "source_name": src_name,
                    "target_name": tgt_name,
                    "description": descr
                })
                continue
            name = parts[1]
            extras = {}
            for extra in parts[2:]:
                if "=" in extra:
                    k,v = extra.split("=",1)
                    extras[k.strip()] = v.strip()
            if name in self.element_db:
                continue
            etype_full = f"archimate:{raw_type}"
            new_el_id = generate_id()
            folder = self.get_folder_for_type(raw_type)
            if folder is None:
                continue
            attribs = {f"{{{XSI}}}type": etype_full, "name": name, "id": new_el_id}
            new_el = ET.SubElement(folder, "element", attribs)
            doc_text = extras.get("description")
            if doc_text:
                doc_el = ET.SubElement(new_el, "documentation")
                doc_el.text = doc_text
            self.element_db[name] = (new_el_id, etype_full)
            self.element_db[name.lower()] = (new_el_id, etype_full)
            created_elements.append((name, new_el_id))

        # Second pass: create relationships
        rel_folder = self.get_or_create_relations_folder()
        for rel in relationships_to_create:
            rtype = rel["type"]
            src_name = rel["source_name"]
            tgt_name = rel["target_name"]
            descr = rel.get("description")
            src_info = self.element_db.get(src_name) or self.element_db.get(src_name.lower())
            tgt_info = None
            if tgt_name:
                tgt_info = self.element_db.get(tgt_name) or self.element_db.get(tgt_name.lower())

            if not src_info or not tgt_info:
                print(f"Warning: Could not find source '{src_name}' or target '{tgt_name}'")
                continue
            src_id, _ = src_info
            tgt_id, _ = tgt_info
            rel_id = generate_id()
            rel_attribs = {
                f"{{{XSI}}}type": f"archimate:{rtype}",
                "id": rel_id,
                "source": src_id,
                "target": tgt_id
            }
            rel_el = ET.SubElement(rel_folder, "element", rel_attribs)
            if descr:
                doc_el = ET.SubElement(rel_el, "documentation")
                doc_el.text = descr

        if created_elements or relationships_to_create:
            self.dirty = True

        self.remove_relationships_from_other()
        self.build_element_database() # Rebuild after adding elements
        self.build_relationship_map()
        self.calculate_relationship_counts()
        self.refresh_tree()
        
        # Clear the paste area now that the content has been committed
        if created_elements or relationships_to_create:
            self.paste_text.delete("1.0", "end")

        self.update_staged_preview()
        self.update_xml_output_panel()
        self.update_button_states()
        messagebox.showinfo("Inserted", f"Inserted {len(created_elements)} elements and {len(relationships_to_create)} relationships.")

    # --- Helper methods ---
    def find_element_by_id(self, el_id):
        if self.model is None:
            return None
        return self.model.find(f".//*[@id='{el_id}']")

    def _find_and_remove_element(self, element_to_remove):
        """Helper to find the parent folder of an element and remove it."""
        if self.model is None or element_to_remove is None:
            return False
        # An element's parent is a folder.
        for folder in self.model.findall("folder"):
            try:
                folder.remove(element_to_remove)
                return True # Successfully found and removed
            except ValueError:
                pass # Not in this folder, continue searching
        return False # Element not found in any folder

    def _show_report_window(self, title, content):
        """
        Displays a resizable window with selectable, scrollable text content for reports.
        """
        report_window = tk.Toplevel(self.root)
        report_window.title(title)
        report_window.geometry("800x600")

        # Configure grid layout for the window
        report_window.rowconfigure(0, weight=1)
        report_window.columnconfigure(0, weight=1)

        # Main frame with padding
        main_frame = tk.Frame(report_window, padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Text widget
        report_text = tk.Text(main_frame, wrap="none", font=("Consolas", 10))
        report_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        y_scroll = tk.Scrollbar(main_frame, orient="vertical", command=report_text.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = tk.Scrollbar(main_frame, orient="horizontal", command=report_text.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")

        report_text.config(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # Insert content and make read-only
        report_text.insert("1.0", content)
        report_text.config(state="disabled")

        # Make modal
        report_window.transient(self.root)
        report_window.grab_set()
        self.root.wait_window(report_window)

    def get_folder_for_type(self, element_type):
        short = element_type.split(":")[-1]
        if short.endswith("Relationship") or short in RELATIONSHIP_TYPES:
            return None
        folder_name = FOLDER_MAP.get(element_type, "Other")
        for folder in self.model.findall("folder"):
            if folder.get("name") == folder_name:
                return folder
        return self.create_folder(folder_name, folder_name.lower())

    def get_or_create_relations_folder(self):
        for folder in self.model.findall("folder"):
            if folder.get("type") == "relations":
                return folder
        return self.create_folder("Relations", "relations")

    def create_folder(self, name, folder_type):
        folder_id = generate_id()
        attribs = {"name": name, "id": folder_id, "type": folder_type}
        return ET.SubElement(self.model, "folder", attribs)

    def create_default_folders(self):
        folders = [
            ("Strategy", "strategy"),
            ("Business", "business"),
            ("Application", "application"),
            ("Technology & Physical", "technology"),
            ("Motivation", "motivation"),
            ("Implementation & Migration", "implementation_migration"),
            ("Other", "other"),
            ("Relations", "relations"),
            ("Views", "diagrams")
        ]
        for name, ftype in folders:
            found = False
            for folder in self.model.findall("folder"):
                if folder.get("type") == ftype:
                    found = True
                    break
            if not found:
                self.create_folder(name, ftype)

    def remove_relationships_from_other(self):
        for folder in self.model.findall("folder"):
            if folder.get("type") == "other":
                to_remove = []
                for el in folder.findall("element"):
                    etype_full = el.get(f"{{{XSI}}}type", "")
                    short = etype_full.split(":")[-1]
                    if short.endswith("Relationship") or short in RELATIONSHIP_TYPES:
                        to_remove.append(el)
                for el in to_remove:
                    folder.remove(el)

    def update_xml_output_panel(self):
        if not hasattr(self, "xml_output_text"):
            return
        if self.model is None:
            self.xml_output_text.config(state="normal")
            self.xml_output_text.delete("1.0", "end")
            self.xml_output_text.insert("end", "(no model loaded)")
            self.xml_output_text.config(state="disabled")
            return
        xml_str = ET.tostring(self.model, encoding='utf-8')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        lines = pretty_xml.split('\n')
        if lines and lines[0].startswith('<?xml'):
            lines = lines[1:]
        pretty_xml = '\n'.join(lines).strip()
        self.xml_output_text.config(state="normal")
        self.xml_output_text.delete("1.0", "end")
        self.xml_output_text.insert("end", pretty_xml)
        self.xml_output_text.config(state="disabled")

    # --- History / Undo ---
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
        self.dirty = True # Undoing is a change
        self.build_element_database()
        self.build_relationship_map()
        self.calculate_relationship_counts()
        self.refresh_tree()
        self.update_xml_output_panel()
        self.update_button_states()
        messagebox.showinfo("Undo", "Reverted one step.")

    # --- 3D Visualization methods have been moved to the ThreeDViewer class ---

    def get_element_relationships(self, el_id):
        """
        Returns a list of relationships for a given element ID using the pre-built map.
        """
        return self.relationship_map.get(el_id, [])
if __name__ == "__main__":
    root = tk.Tk()
    app = ArchiIngestorApp(root)

    root.mainloop()
