# Builder_V6_tokenaware.py
# Token-aware ArchiMate Prompt Generator (Tkinter)
# - JSON-first outputs
# - Token estimation (tiktoken optional; fallback heuristic)
# - Running token totals, color-coded safety indicator
# - Summarisation scaffold / compressed-summary stub
#
# Drop into same folder as Builder_Config.py

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json, os, math, re
from datetime import datetime

# Try to import the user's config (DEFAULT_ORGANISATION, ARCHITECTURE_DOMAINS, HEADER_PROMPT, APPROVED_SOURCES, VALIDATION_RULES)
try:
    from Builder_Config import (
        DEFAULT_ORGANISATION,
        ARCHITECTURE_DOMAINS,
        APPROVED_SOURCES,
        HEADER_PROMPT,
        VALIDATION_RULES
    )
except Exception as e:
    # Minimal fallbacks if config missing
    DEFAULT_ORGANISATION = "Lincolnshire County Council"
    ARCHITECTURE_DOMAINS = {}
    APPROVED_SOURCES = {}
    HEADER_PROMPT = ""
    VALIDATION_RULES = {}

# Optional tokenizer (tiktoken). If not available we fall back to a heuristic.
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except Exception:
    TIKTOKEN_AVAILABLE = False

# ---------- Configuration: model & thresholds ----------
# Targeting Copilot / GPT-4 Turbo-ish environment
MODEL_NAME_FOR_ESTIMATE = "gpt-4o"  # symbolic. tiktoken will map common models.
# Thresholds for Copilot-like environment (tokens)
SAFE_GREEN = 20000      # comfortable
SAFE_AMBER = 32000      # approaching Copilot limit
SAFE_RED = 64000        # definitely too large (use 1M for enterprise models if available)

# ---------- Token estimator helper ----------
def estimate_tokens(text: str, model_name: str = MODEL_NAME_FOR_ESTIMATE) -> int:
    """
    Estimate tokens for given text. Uses tiktoken if available; fallback to chars/4 heuristic.
    """
    if not text:
        return 0
    if TIKTOKEN_AVAILABLE:
        try:
            enc = tiktoken.encoding_for_model(model_name)
        except Exception:
            # Model name not found: choose a default encoding
            enc = tiktoken.get_encoding("cl100k_base")
        toks = len(enc.encode(text))
        return toks
    else:
        # Heuristic: average 4 characters per token (approx)
        # Also compress long repeated whitespace and typical XML/JSON punctuation cost
        cleaned = re.sub(r"\s+", " ", text)
        return max(1, int(len(cleaned) / 4))

# ---------- Small helpers ----------
def short_summary(text: str, max_chars: int = 200) -> str:
    """
    Produce a cheap local 'summary' of a text block for token-saving.
    - naive: take the first sentence or truncate to max_chars
    """
    if not text:
        return ""
    # Try to grab first sentence (up to punctuation)
    m = re.search(r"(.+?[.!?])\s", text)
    if m:
        s = m.group(1).strip()
        if len(s) <= max_chars:
            return s
    s = text.strip().replace("\n", " ")
    if len(s) > max_chars:
        s = s[:max_chars].rsplit(" ", 1)[0] + "..."
    return s

def compact_text_for_prompt(text: str) -> str:
    """
    Reduce verbosity in prompts: remove visual whitespace, compress repeats.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

# ---------- Main app ----------
class TokenAwarePromptGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("ArchiMate Prompt Builder — Token-aware (V6)")
        self.root.geometry("1100x820")

        # State
        self.selected_domains = set()
        self.prompts = []                    # list of generated prompt texts (string)
        self.prompt_json_cache = {}          # domain_id -> generated JSON objects (list)
        self.current_prompt_index = 0
        self.org_name = DEFAULT_ORGANISATION

        # UI
        self.create_widgets()
        self.bind_shortcuts()

    # ---------- UI ----------
    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Prompt Builder")

        sources_frame = ttk.Frame(notebook)
        notebook.add(sources_frame, text="Approved Sources")

        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="Header & Settings")

        self.setup_main_tab(main_frame)
        self.setup_sources_tab(sources_frame)
        self.setup_config_tab(config_frame)

        # status bar
        self.status_var = tk.StringVar(value="Ready — select domains and generate prompts")
        status = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status.grid(row=1, column=0, sticky="ew", padx=2, pady=2)

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

    def setup_main_tab(self, parent):
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        # Left: Project + Domain selection
        self.setup_project_and_domains(left)

        # Right: Prompt display, controls, generated JSONs
        self.setup_prompt_area(right)

    def setup_project_and_domains(self, parent):
        top = ttk.LabelFrame(parent, text="Project Setup", padding=8)
        top.pack(fill="x", padx=4, pady=4)

        ttk.Label(top, text="Organisation:").grid(row=0, column=0, sticky="w")
        self.org_var = tk.StringVar(value=self.org_name)
        ttk.Entry(top, textvariable=self.org_var, width=40).grid(row=0, column=1, sticky="ew", padx=6)

        self.sources_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Include source citations", variable=self.sources_var).grid(row=1, column=1, sticky="w", pady=6)

        top.columnconfigure(1, weight=1)

        domain_frame = ttk.LabelFrame(parent, text="Architecture Domains", padding=8)
        domain_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # scrollable domain list
        canvas = tk.Canvas(domain_frame, height=360)
        scrollbar = ttk.Scrollbar(domain_frame, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self.domain_vars = {}
        row = 0
        for domain_id, domain_info in ARCHITECTURE_DOMAINS.items():
            var = tk.BooleanVar(value=False)
            self.domain_vars[domain_id] = var
            cb = ttk.Checkbutton(scrollable, text=domain_info.get("name", domain_id), variable=var, command=self.update_domain_selection)
            cb.grid(row=row, column=0, sticky="w", padx=(2,2), pady=2)
            desc = ttk.Label(scrollable, text=domain_info.get("description",""), font=("Arial", 8), foreground="gray")
            desc.grid(row=row, column=1, sticky="w", padx=(8,0), pady=2)
            row += 1
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ctrl = ttk.Frame(domain_frame)
        ctrl.pack(fill="x", pady=6)
        ttk.Button(ctrl, text="Select All", command=self.select_all_domains).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Clear All", command=self.clear_domains).pack(side="left", padx=2)
        ttk.Button(ctrl, text="Generate Prompts", command=self.generate_prompts).pack(side="right", padx=2)

    def setup_prompt_area(self, parent):
        # Current Prompt
        cp_frame = ttk.LabelFrame(parent, text="Current Prompt", padding=8)
        cp_frame.pack(fill="both", expand=False, padx=4, pady=4)

        self.current_prompt_text = scrolledtext.ScrolledText(cp_frame, height=12)
        self.current_prompt_text.pack(fill="both", expand=True)

        # Token info row
        token_row = ttk.Frame(cp_frame)
        token_row.pack(fill="x", pady=6)

        ttk.Label(token_row, text="Current Prompt tokens:").pack(side="left")
        self.current_tokens_var = tk.StringVar(value="0")
        self.current_tokens_label = ttk.Label(token_row, textvariable=self.current_tokens_var, width=12)
        self.current_tokens_label.pack(side="left", padx=6)

        ttk.Label(token_row, text="Total generated tokens:").pack(side="left", padx=(12,4))
        self.total_tokens_var = tk.StringVar(value="0")
        self.total_tokens_label = ttk.Label(token_row, textvariable=self.total_tokens_var, width=14)
        self.total_tokens_label.pack(side="left", padx=6)

        # Safety indicator
        self.safety_canvas = tk.Canvas(token_row, width=20, height=20)
        self.safety_canvas.pack(side="left", padx=8)
        self.update_safety_indicator(0)

        # Buttons under prompt
        btn_row = ttk.Frame(cp_frame)
        btn_row.pack(fill="x", pady=(0,4))
        ttk.Button(btn_row, text="Estimate Tokens", command=self.estimate_current_prompt_tokens).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Copy Prompt", command=self.copy_current_prompt).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Save Prompt JSON (simulate AI output)", command=self.save_current_prompt_json).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Next →", command=self.next_prompt).pack(side="right", padx=3)
        ttk.Button(btn_row, text="← Previous", command=self.previous_prompt).pack(side="right", padx=3)

        # Generated prompts list
        gen_frame = ttk.LabelFrame(parent, text="Generated Prompts & JSON Cache", padding=8)
        gen_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.all_prompts_text = scrolledtext.ScrolledText(gen_frame, height=10)
        self.all_prompts_text.pack(fill="both", expand=True)

        # Export section
        export_frame = ttk.Frame(parent)
        export_frame.pack(fill="x", pady=6)
        ttk.Button(export_frame, text="Export All JSON", command=self.export_all_json).pack(side="left", padx=4)
        ttk.Button(export_frame, text="Produce Compressed Summary (stub)", command=self.produce_compressed_summary).pack(side="left", padx=4)
        ttk.Button(export_frame, text="Clear Generated Cache", command=self.clear_generated_cache).pack(side="right", padx=4)

    def setup_sources_tab(self, parent):
        ttk.Label(parent, text="Approved Sources", font=("Arial",10,"bold")).pack(anchor="w", padx=8, pady=(8,2))
        self.sources_tree = ttk.Treeview(parent, columns=("name","url","description"), show="headings", height=16)
        self.sources_tree.heading("name", text="Name"); self.sources_tree.heading("url", text="URL"); self.sources_tree.heading("description", text="Description")
        self.sources_tree.pack(fill="both", expand=True, padx=8, pady=6)
        self.load_sources()

        # Simple controls to edit (basic)
        sf = ttk.Frame(parent); sf.pack(fill="x", padx=8, pady=4)
        ttk.Button(sf, text="Reload Sources", command=self.load_sources).pack(side="left")
        ttk.Button(sf, text="Edit Selected (basic)", command=self.edit_selected_source).pack(side="left", padx=4)

    def setup_config_tab(self, parent):
        ttk.Label(parent, text="Header Prompt (read-only template)", font=("Arial",10,"bold")).pack(anchor="w", padx=8, pady=(8,2))
        self.header_area = scrolledtext.ScrolledText(parent, height=22)
        self.header_area.pack(fill="both", expand=True, padx=8, pady=6)
        self.header_area.insert(1.0, HEADER_PROMPT if HEADER_PROMPT else "(No HEADER_PROMPT provided in Builder_Config.py)")
        self.header_area.config(state="disabled")

        cfg_frame = ttk.Frame(parent)
        cfg_frame.pack(fill="x", padx=8, pady=6)
        ttk.Label(cfg_frame, text="Token estimator: ").pack(side="left")
        ttk.Label(cfg_frame, text="Using tiktoken: " + ("Yes" if TIKTOKEN_AVAILABLE else "No (heuristic)")).pack(side="left", padx=8)

    # ---------- Domain selection helpers ----------
    def update_domain_selection(self):
        self.selected_domains.clear()
        for k,v in self.domain_vars.items():
            if v.get():
                self.selected_domains.add(k)
        self.status_var.set(f"Selected {len(self.selected_domains)} domain(s).")

    def select_all_domains(self):
        for v in self.domain_vars.values(): v.set(True)
        self.update_domain_selection()

    def clear_domains(self):
        for v in self.domain_vars.values(): v.set(False)
        self.update_domain_selection()

    # ---------- Generating prompts ----------
    def generate_prompts(self):
        if not self.selected_domains:
            messagebox.showwarning("No domains", "Please select at least one domain to generate prompts.")
            return
        org = self.org_var.get().strip() or DEFAULT_ORGANISATION
        include_sources = self.sources_var.get()

        # produce prompts from templates but compacted
        self.prompts = []
        self.prompt_meta = []  # store (domain_id, template_text)
        for domain_id in self.selected_domains:
            domain_info = ARCHITECTURE_DOMAINS.get(domain_id, {})
            templates = domain_info.get("prompt_templates", [])
            for t in templates:
                prompt_text = t.format(organisation=org)
                # make compact
                prompt_text = compact_text_for_prompt(prompt_text)
                if include_sources:
                    # append a small 'sources token' placeholder (we will not inline full list to save tokens)
                    prompt_text += " [USE_APPROVED_SOURCES]"
                self.prompts.append(prompt_text)
                self.prompt_meta.append((domain_id, prompt_text))

        self.current_prompt_index = 0
        self.update_prompt_display()
        self.update_status(f"Generated {len(self.prompts)} prompts across {len(self.selected_domains)} domains. Estimate tokens before use.")

    def update_prompt_display(self):
        self.current_prompt_text.delete(1.0, tk.END)
        if self.prompts:
            self.current_prompt_text.insert(1.0, self.prompts[self.current_prompt_index])
        self.refresh_all_prompts_view()
        self.estimate_current_prompt_tokens()

    def refresh_all_prompts_view(self):
        self.all_prompts_text.delete(1.0, tk.END)
        for i,p in enumerate(self.prompts):
            flag = "▶ " if i == self.current_prompt_index else "   "
            preview = p if len(p) < 120 else p[:116] + "..."
            self.all_prompts_text.insert(tk.END, f"{flag}Prompt {i+1}: {preview}\n")

    def previous_prompt(self):
        if self.current_prompt_index > 0:
            self.current_prompt_index -= 1
            self.update_prompt_display()

    def next_prompt(self):
        if self.current_prompt_index < len(self.prompts) - 1:
            self.current_prompt_index += 1
            self.update_prompt_display()

    # ---------- Token estimation ----------
    def estimate_current_prompt_tokens(self):
        text = self.current_prompt_text.get("1.0", tk.END).strip()
        # include header if you'd typically send it; but show both counts
        header = HEADER_PROMPT or ""
        header_tokens = estimate_tokens(header)
        prompt_tokens = estimate_tokens(text)
        total_if_sent = header_tokens + prompt_tokens
        self.current_tokens_var.set(f"{prompt_tokens} (hdr {header_tokens})")
        # Update totals from cache
        total_cached = self.calculate_cached_tokens()
        total_with_prompt = total_cached + total_if_sent
        self.total_tokens_var.set(str(total_with_prompt))
        self.update_safety_indicator(total_with_prompt)
        return prompt_tokens, header_tokens, total_with_prompt

    def calculate_cached_tokens(self):
        """Estimate tokens for all cached JSON outputs + header if you would re-send them."""
        total = 0
        for domain_id, json_objects in self.prompt_json_cache.items():
            s = json.dumps(json_objects, ensure_ascii=False)
            total += estimate_tokens(s)
        return total

    def update_safety_indicator(self, tokens_total: int):
        self.safety_canvas.delete("all")
        # Choose color
        if tokens_total < SAFE_GREEN:
            color = "green"
        elif tokens_total < SAFE_AMBER:
            color = "orange"
        else:
            color = "red"
        # draw circle
        self.safety_canvas.create_oval(2,2,18,18, fill=color, outline="black")

    # ---------- Copy / Save JSON (simulate AI output) ----------
    def copy_current_prompt(self):
        txt = self.current_prompt_text.get("1.0", tk.END).strip()
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.root.update()
            self.update_status("Prompt copied to clipboard.")
        except Exception:
            self.update_status("Copy failed — please copy manually.")

    def save_current_prompt_json(self):
        """
        This function simulates the step where you have received the JSON array from the AI.
        It will present a small dialog to paste the JSON result (or auto-generate a tiny mock),
        validate it's an array, then cache it under the domain the prompt belongs to.
        """
        if not self.prompts:
            messagebox.showwarning("No prompts", "Generate prompts first.")
            return

        # Determine domain of current prompt
        domain_id, prompt_text = self.prompt_meta[self.current_prompt_index]
        # Ask user to paste AI-generated JSON (they may have run Copilot separately)
        paste_window = tk.Toplevel(self.root)
        paste_window.title("Paste AI JSON output for current prompt")
        paste_window.geometry("700x420")
        paste_window.transient(self.root)
        paste_window.grab_set()

        ttk.Label(paste_window, text=f"Domain: {ARCHITECTURE_DOMAINS.get(domain_id, {}).get('name',domain_id)}", font=("Arial",10,"bold")).pack(anchor="w", padx=8, pady=(8,2))
        info = ("Paste the JSON array output received from Copilot/AI here. Must be a JSON array "
                "of elements and relationships as per your HEADER_PROMPT structure.\n\n"
                "If you don't have AI output yet, click 'Generate Mock' to create a small example.")
        ttk.Label(paste_window, text=info, wraplength=660, foreground="gray").pack(anchor="w", padx=8, pady=4)

        text_area = scrolledtext.ScrolledText(paste_window, height=16)
        text_area.pack(fill="both", expand=True, padx=8, pady=6)

        def use_mock():
            # create a small mock JSON for this domain (use domain name in elements)
            dom_name = ARCHITECTURE_DOMAINS.get(domain_id, {}).get("name", domain_id)
            mock = [
                {"element_type":"BusinessActor","name":f"{dom_name} Example Actor","description":f"Example actor for {dom_name}"},
                {"element_type":"BusinessService","name":f"{dom_name} Example Service","description":f"Example service provided by {dom_name} actor"}
            ]
            text_area.delete("1.0", tk.END)
            text_area.insert(1.0, json.dumps(mock, indent=2, ensure_ascii=False))

        def save_pasted():
            raw = text_area.get("1.0", tk.END).strip()
            if not raw:
                messagebox.showwarning("No input", "Paste AI output or generate a mock.")
                return
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    messagebox.showerror("Invalid JSON", "Top-level JSON must be an array of elements/relationships.")
                    return
                # Save into cache (append if domain exists)
                existing = self.prompt_json_cache.get(domain_id, [])
                # Simple dedupe by element_type+name (merge)
                merged = self._merge_json_lists(existing, parsed)
                self.prompt_json_cache[domain_id] = merged
                paste_window.destroy()
                self.update_status(f"Saved {len(parsed)} objects to cache for domain {domain_id}")
                self.refresh_cache_view()
                self.estimate_current_prompt_tokens()
            except Exception as e:
                messagebox.showerror("JSON Error", f"Failed to parse JSON: {str(e)}")

        btns = ttk.Frame(paste_window)
        btns.pack(fill="x", padx=8, pady=6)
        ttk.Button(btns, text="Generate Mock", command=use_mock).pack(side="left")
        ttk.Button(btns, text="Save Pasted JSON", command=save_pasted).pack(side="right")

    def _merge_json_lists(self, existing: list, incoming: list) -> list:
        """
        Merge incoming JSON list into existing while attempting to avoid duplicates.
        Deduplicate on (element_type, name) for elements, on relationship signature for relationships.
        """
        out = list(existing)  # shallow copy
        # Build index
        elem_index = {}
        rel_index = set()
        for e in out:
            if "element_type" in e and e.get("name"):
                key = (e["element_type"], e["name"])
                elem_index[key] = e
            else:
                # relationship
                s = (e.get("element_type"), e.get("source_name"), e.get("target_name"), e.get("description"))
                rel_index.add(s)
        for item in incoming:
            if "element_type" in item and item.get("name"):
                key = (item["element_type"], item["name"])
                if key in elem_index:
                    # merge descriptions conservatively
                    exist = elem_index[key]
                    if len(item.get("description","")) > len(exist.get("description","")):
                        exist["description"] = item["description"]
                else:
                    out.append(item)
                    elem_index[key] = item
            else:
                s = (item.get("element_type"), item.get("source_name"), item.get("target_name"), item.get("description"))
                if s not in rel_index:
                    out.append(item)
                    rel_index.add(s)
        return out

    def refresh_cache_view(self):
        self.all_prompts_text.delete("1.0", tk.END)
        for domain_id, objs in self.prompt_json_cache.items():
            dom_name = ARCHITECTURE_DOMAINS.get(domain_id, {}).get("name", domain_id)
            preview = f"Domain: {dom_name} — {len(objs)} objects\n"
            preview += json.dumps(objs[:5], indent=2, ensure_ascii=False) + ("\n ...\n\n" if len(objs) > 5 else "\n\n")
            self.all_prompts_text.insert(tk.END, preview)

    def clear_generated_cache(self):
        if messagebox.askyesno("Confirm", "Clear all cached generated JSON?"):
            self.prompt_json_cache.clear()
            self.update_status("Cleared generated cache.")
            self.refresh_cache_view()
            self.estimate_current_prompt_tokens()

    # ---------- Exports & summarisation ----------
    def export_all_json(self):
        """Export cached JSON per domain into a timestamped folder. Also write a combined JSON file."""
        if not self.prompt_json_cache:
            messagebox.showwarning("No data", "No generated JSON to export.")
            return
        folder = filedialog.askdirectory(title="Select directory to export JSON files")
        if not folder:
            return
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        export_root = os.path.join(folder, f"archimate_export_{stamp}")
        os.makedirs(export_root, exist_ok=True)
        combined = []
        for domain_id, objs in self.prompt_json_cache.items():
            dom_name = ARCHITECTURE_DOMAINS.get(domain_id, {}).get("name", domain_id)
            fname = f"{domain_id}.json"
            path = os.path.join(export_root, fname)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(objs, f, indent=2, ensure_ascii=False)
            combined.extend(objs)
        # Write combined
        combined_path = os.path.join(export_root, "combined_model.json")
        with open(combined_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exported", f"Exported {len(self.prompt_json_cache)} domain files + combined ({len(combined)} objects)\nFolder: {export_root}")
        self.update_status(f"Exported JSON to {export_root}")

    def produce_compressed_summary(self):
        """
        Create a compressed summary prompt containing brief summaries for each domain's cached objects.
        This is a stub: it constructs a small prompt you can paste to Copilot to continue work.
        """
        if not self.prompt_json_cache:
            messagebox.showwarning("No cached model", "No generated JSON found. Save some domain outputs before summarising.")
            return
        # Build domain summaries
        domain_summaries = []
        for domain_id, objs in self.prompt_json_cache.items():
            dom_label = ARCHITECTURE_DOMAINS.get(domain_id,{}).get("name", domain_id)
            # Compact each object's description to 1 sentence
            summaries = []
            for o in objs:
                name = o.get("name") or o.get("source_name") or ""
                et = o.get("element_type") or o.get("element_type")
                desc = o.get("description","")
                c = short_summary(desc, max_chars=180)
                summaries.append(f"{et} '{name}': {c}")
            # join a handful (limit tokens): include only top N items to control size
            joined = "\n".join(summaries[:50])  # limit per domain
            domain_summaries.append(f"DOMAIN: {dom_label}\n{joined}\n")
        compressed_body = "\n\n".join(domain_summaries)
        compressed_body = compact_text_for_prompt(compressed_body)

        # Create the prompt for the AI summariser (header + instruction)
        summariser_prompt = (
            "You are an expert Enterprise Architect. "
            "I will give you compressed domain summaries from an enterprise ArchiMate model. "
            "Produce a single JSON array that summarises cross-domain dependencies, "
            "key capability gaps, and a concise recommended next 'what-if' analysis to run. "
            "Output ONLY JSON. Use ArchiMate element and relationship types.\n\n"
            "INPUT_SUMMARY:\n" + compressed_body
        )

        # Estimate tokens and show prompt in a window so user can copy to Copilot
        p_win = tk.Toplevel(self.root)
        p_win.title("Compressed Summary Prompt (stub) — copy into Copilot")
        p_win.geometry("900x700")
        ta = scrolledtext.ScrolledText(p_win)
        ta.pack(fill="both", expand=True)
        ta.insert(1.0, summariser_prompt)
        ta.configure(state="normal")

        # Small info
        info_lbl = ttk.Label(p_win, text=f"Estimated tokens (approx): {estimate_tokens(summariser_prompt)} (use caution with Copilot limits)")
        info_lbl.pack(anchor="w", padx=8, pady=5)

        ttk.Button(p_win, text="Copy Prompt", command=lambda: self.copy_text_to_clipboard(summariser_prompt)).pack(side="left", padx=8, pady=6)
        ttk.Button(p_win, text="Close", command=p_win.destroy).pack(side="right", padx=8, pady=6)

    def copy_text_to_clipboard(self, text: str):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.update_status("Copied prompt to clipboard.")
        except Exception:
            self.update_status("Failed to copy prompt.")

    # ---------- Sources tab helpers ----------
    def load_sources(self):
        self.sources_tree.delete(*self.sources_tree.get_children())
        for key, s in APPROVED_SOURCES.items():
            self.sources_tree.insert("", "end", values=(s.get("name",""), s.get("url",""), s.get("description","")), tags=(key,))

    def edit_selected_source(self):
        sel = self.sources_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a source to edit.")
            return
        item = sel[0]
        vals = self.sources_tree.item(item, "values")
        tags = self.sources_tree.item(item, "tags")
        key = tags[0] if tags else None
        if not key:
            messagebox.showerror("Error", "Cannot determine source key.")
            return
        # Simple modal to edit (name/url/desc)
        ewin = tk.Toplevel(self.root)
        ewin.title("Edit Source")
        ewin.geometry("640x260")
        ewin.transient(self.root)
        ewin.grab_set()

        name_var = tk.StringVar(value=vals[0])
        url_var = tk.StringVar(value=vals[1])
        desc_var = tk.StringVar(value=vals[2])

        ttk.Label(ewin, text="Name:").pack(anchor="w", padx=8, pady=(8,2))
        ttk.Entry(ewin, textvariable=name_var, width=80).pack(fill="x", padx=8)
        ttk.Label(ewin, text="URL:").pack(anchor="w", padx=8, pady=(8,2))
        ttk.Entry(ewin, textvariable=url_var, width=80).pack(fill="x", padx=8)
        ttk.Label(ewin, text="Description:").pack(anchor="w", padx=8, pady=(8,2))
        ttk.Entry(ewin, textvariable=desc_var, width=80).pack(fill="x", padx=8)

        def save_edit():
            APPROVED_SOURCES[key] = {"name": name_var.get(), "url": url_var.get(), "description": desc_var.get()}
            # attempt to save back to config file if present
            try:
                from Builder_Config import save_approved_sources
                save_approved_sources(APPROVED_SOURCES)
            except Exception:
                pass
            self.load_sources()
            ewin.destroy()
            self.update_status("Saved approved source.")

        ttk.Button(ewin, text="Save", command=save_edit).pack(side="right", padx=8, pady=8)

    # ---------- Misc ----------
    def update_status(self, msg: str):
        self.status_var.set(msg)
        self.root.update_idletasks()

# ---------- Run App ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = TokenAwarePromptGenerator(root)
    root.mainloop()
