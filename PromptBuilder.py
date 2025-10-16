import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import os
import tempfile
import shutil

from Builder_Config import (DEFAULT_ORGANISATION, ARCHITECTURE_DOMAINS,
                   APPROVED_SOURCES, HEADER_PROMPT, VALIDATION_RULES)

class PromptGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Archimate Prompt Generator - Domain Selection")
        self.root.geometry("1000x800")
        
        self.current_prompt_index = 0
        self.prompts = []
        self.selected_domains = set()
        
        self.create_widgets()
        self.bind_shortcuts()
        
    def create_widgets(self):
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Main Prompt Tab (now includes domain selection)
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Prompt Generation")
        
        # Sources Tab
        sources_frame = ttk.Frame(notebook)
        notebook.add(sources_frame, text="Approved Sources")
        
        # Header Prompt Tab
        header_frame = ttk.Frame(notebook)
        notebook.add(header_frame, text="Header Prompt")
        
        self.setup_main_tab(main_frame)
        self.setup_sources_tab(sources_frame)
        self.setup_header_tab(header_frame)
        
        # Add status bar at the bottom
        self.status_var = tk.StringVar(value="Select architecture domains to begin")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
    
    def setup_main_tab(self, parent):
        # Main container with two panes
        paned_window = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned_window.grid(row=0, column=0, sticky="nsew")
        
        # Left pane - Domain selection and inputs
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # Right pane - Prompt display
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        
        self.setup_domain_selection(left_frame)
        self.setup_prompt_display(right_frame)
        
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
    
    def setup_domain_selection(self, parent):
        # Input Frame
        input_frame = ttk.LabelFrame(parent, text="Project Setup", padding="10")
        input_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(input_frame, text="Organisation:").grid(row=0, column=0, sticky="w")
        self.org_var = tk.StringVar(value=DEFAULT_ORGANISATION)
        self.org_entry = ttk.Entry(input_frame, textvariable=self.org_var, width=40)
        self.org_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Source requirement checkbox
        self.sources_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="Include source citations", 
                       variable=self.sources_var).grid(row=1, column=1, sticky="w", pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Domain Selection Frame
        domain_frame = ttk.LabelFrame(parent, text="Architecture Domains", padding="10")
        domain_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Domain selection with scrollbar
        domain_container = ttk.Frame(domain_frame)
        domain_container.pack(fill="both", expand=True)
        
        # Create a canvas and scrollbar
        canvas = tk.Canvas(domain_container, height=300)
        scrollbar = ttk.Scrollbar(domain_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Domain checkboxes
        self.domain_vars = {}
        row = 0
        
        for domain_id, domain_info in ARCHITECTURE_DOMAINS.items():
            var = tk.BooleanVar()
            self.domain_vars[domain_id] = var
            
            cb = ttk.Checkbutton(scrollable_frame, text=domain_info["name"], variable=var,
                               command=self.update_domain_selection)
            cb.grid(row=row, column=0, sticky="w", pady=2)
            
            # Description label
            desc_label = ttk.Label(scrollable_frame, text=domain_info["description"], 
                                 font=("Arial", 8), foreground="gray")
            desc_label.grid(row=row, column=1, sticky="w", padx=(10,0), pady=2)
            
            row += 1
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        button_frame = ttk.Frame(domain_frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Select All", 
                  command=self.select_all_domains).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Clear All", 
                  command=self.clear_domains).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Generate Prompts", 
                  command=self.generate_prompts).pack(side="right", padx=2)
    
    def setup_prompt_display(self, parent):
        # Current Prompt Display
        current_frame = ttk.LabelFrame(parent, text="Current Prompt", padding="10")
        current_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.current_prompt_text = scrolledtext.ScrolledText(current_frame, height=12, width=80)
        self.current_prompt_text.pack(fill="both", expand=True)
        
        # Control Buttons
        button_frame = ttk.Frame(current_frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="← Previous", 
                  command=self.previous_prompt).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Copy Prompt", 
                  command=self.copy_current_prompt).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Next →", 
                  command=self.next_prompt).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Copy Header", 
                  command=self.copy_header_prompt).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Export All", 
                  command=self.export_prompts).pack(side="right", padx=2)
        
        # Progress indicator
        self.progress_var = tk.StringVar(value="No prompts generated")
        ttk.Label(button_frame, textvariable=self.progress_var).pack(side="left", padx=20)
        
        # All Prompts List (cleaner display)
        all_frame = ttk.LabelFrame(parent, text="Generated Prompts", padding="10")
        all_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.all_prompts_text = scrolledtext.ScrolledText(all_frame, height=10, width=80)
        self.all_prompts_text.pack(fill="both", expand=True)
    
    def setup_sources_tab(self, parent):
        """Tab showing approved sources with editing capabilities"""
        # Title
        ttk.Label(parent, text="Approved Sources for Lincolnshire Council:", 
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Instructions
        ttk.Label(parent, 
                 text="Paste URLs into the URL field (Ctrl+V or right-click). Click 'Add Source' to add to active list. Double-click to edit.",
                 font=("Arial", 8), 
                 foreground="gray").pack(anchor="w", padx=10, pady=(0, 10))
        
        # Main container with two columns
        main_container = ttk.Frame(parent)
        main_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left column - Current sources list
        left_frame = ttk.LabelFrame(main_container, text="Current Approved Sources")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Treeview for sources
        columns = ("name", "url", "description")
        self.sources_tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=12)
        
        # Configure columns
        self.sources_tree.heading("name", text="Name")
        self.sources_tree.heading("url", text="URL")
        self.sources_tree.heading("description", text="Description")
        
        self.sources_tree.column("name", width=150)
        self.sources_tree.column("url", width=200)
        self.sources_tree.column("description", width=250)
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.sources_tree.yview)
        self.sources_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.sources_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # Right column - Add/Edit sources
        right_frame = ttk.LabelFrame(main_container, text="Add New Source")
        right_frame.pack(side="right", fill="both", padx=(5, 0), ipadx=5)
        
        # URL entry with paste support
        ttk.Label(right_frame, text="URL (paste here with Ctrl+V or right-click):").pack(anchor="w", pady=(5, 2))
        
        url_frame = ttk.Frame(right_frame)
        url_frame.pack(fill="x", padx=5, pady=2)
        
        self.source_url_var = tk.StringVar()
        self.source_url_entry = ttk.Entry(url_frame, textvariable=self.source_url_var)
        self.source_url_entry.pack(side="left", fill="x", expand=True)
        
        # Paste button for URL field
        paste_btn = ttk.Button(url_frame, text="Paste", width=6, command=self.paste_to_url_field)
        paste_btn.pack(side="right", padx=(5, 0))
        
        # Name entry
        name_frame = ttk.Frame(right_frame)
        name_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(name_frame, text="Name:").pack(side="left")
        self.source_name_var = tk.StringVar()
        self.source_name_entry = ttk.Entry(name_frame, textvariable=self.source_name_var)
        self.source_name_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Description entry
        desc_frame = ttk.Frame(right_frame)
        desc_frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(desc_frame, text="Description:").pack(side="left")
        self.source_desc_var = tk.StringVar()
        self.source_desc_entry = ttk.Entry(desc_frame, textvariable=self.source_desc_var)
        self.source_desc_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Auto-fill name from URL when URL changes
        self.source_url_var.trace_add('write', self.auto_fill_name_from_url)
        
        # Buttons frame
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill="x", padx=5, pady=10)
        
        ttk.Button(button_frame, text="Add Source", 
                  command=self.add_source_manual).pack(side="left", padx=(0, 5))
        ttk.Button(button_frame, text="Delete Selected", 
                  command=self.delete_selected_source, style="Danger.TButton").pack(side="right", padx=(5, 0))
        
        # Edit button
        edit_button_frame = ttk.Frame(right_frame)
        edit_button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(edit_button_frame, text="Edit Selected", 
                  command=self.edit_selected_source).pack(side="left", padx=(0, 5))
        
        # Config management buttons
        config_frame = ttk.Frame(right_frame)
        config_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(config_frame, text="Load from Config", 
                  command=self.load_sources_from_config).pack(side="left", padx=(0, 5))
        ttk.Button(config_frame, text="Save to Config", 
                  command=self.save_sources_to_config, 
                  style="Accent.TButton").pack(side="right")
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("Danger.TButton", foreground="red")
        self.style.configure("Accent.TButton", font=("Arial", 9, "bold"))
        
        # Set up paste functionality
        self.setup_paste_support()
        
        # Load current sources
        self.load_sources_to_tree()
        
        # Bind double-click to edit
        self.sources_tree.bind("<Double-1>", self.edit_selected_source)

    def setup_paste_support(self):
        """Set up paste functionality for the URL field"""
        # Bind Ctrl+V
        self.source_url_entry.bind('<Control-v>', lambda e: self.paste_to_url_field())
        
        # Bind right-click paste
        def show_context_menu(event):
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Paste", command=self.paste_to_url_field)
            menu.tk_popup(event.x_root, event.y_root)
        
        self.source_url_entry.bind('<Button-3>', show_context_menu)  # Button-3 is right-click

    def paste_to_url_field(self):
        """Paste clipboard content to URL field"""
        try:
            clipboard_content = self.root.clipboard_get()
            if clipboard_content:
                self.source_url_var.set(clipboard_content.strip())
        except:
            pass

    def auto_fill_name_from_url(self, *args):
        """Auto-fill the name field when URL is entered"""
        url = self.source_url_var.get().strip()
        if url and not self.source_name_var.get().strip():
            name = self.extract_name_from_url(url)
            self.source_name_var.set(name)

    def load_sources_from_config(self):
        """Reload sources from the JSON config file"""
        try:
            from Builder_Config import load_approved_sources
            global APPROVED_SOURCES
            APPROVED_SOURCES = load_approved_sources()
            self.load_sources_to_tree()
            messagebox.showinfo("Success", "Sources reloaded from configuration file.")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load sources:\n{str(e)}")

    def save_sources_to_config(self):
        """Save the current sources back to JSON config file"""
        try:
            from Builder_Config import save_approved_sources
            if save_approved_sources(APPROVED_SOURCES):
                messagebox.showinfo("Success", "Sources saved to configuration file.")
            else:
                messagebox.showerror("Save Error", "Failed to save sources to configuration file.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save sources:\n{str(e)}")

    def load_sources_to_tree(self):
        """Load current sources from config into the treeview"""
        self.sources_tree.delete(*self.sources_tree.get_children())
        for key, source in APPROVED_SOURCES.items():
            self.sources_tree.insert("", "end", values=(
                source["name"], source["url"], source["description"]
            ), tags=(key,))

    def extract_name_from_url(self, url):
        """Extract a readable name from a URL"""
        # Remove protocol and www
        clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
        
        # Extract domain and path for naming
        parts = clean_url.split('/')
        if parts[0]:
            domain = parts[0].split('.')[0]
            if len(parts) > 1 and parts[1]:
                # Use first path segment as part of name
                return f"{domain}_{parts[1]}".title()
            return domain.title()
        
        return "New Source"

    def add_source_manual(self):
        """Add a source manually from the entry fields"""
        name = self.source_name_var.get().strip()
        url = self.source_url_var.get().strip()
        description = self.source_desc_var.get().strip()
        
        if not name or not url:
            messagebox.showwarning("Missing Fields", "Name and URL are required.")
            return
        
        # Generate a unique key
        key = f"custom_source_{len(APPROVED_SOURCES) + 1}"
        APPROVED_SOURCES[key] = {
            "name": name,
            "url": url,
            "description": description
        }
        
        self.load_sources_to_tree()
        
        # Clear entry fields
        self.source_name_var.set("")
        self.source_url_var.set("")
        self.source_desc_var.set("")
        
        messagebox.showinfo("Success", f"Added source: {name}")

    def edit_selected_source(self, event=None):
        """Edit the selected source (called by double-click or Edit button)"""
        selection = self.sources_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source to edit.")
            return
        
        item = selection[0]
        values = self.sources_tree.item(item, "values")
        tags = self.sources_tree.item(item, "tags")
        
        if not values or not tags:
            return
        
        # Create edit dialog
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Source")
        edit_window.geometry("500x250")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # Make the window modal
        edit_window.focus_set()
        
        # Entry fields with labels
        ttk.Label(edit_window, text="Name:", font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(15, 2))
        name_var = tk.StringVar(value=values[0])
        name_entry = ttk.Entry(edit_window, textvariable=name_var, width=60)
        name_entry.pack(fill="x", padx=15, pady=(0, 10))
        
        ttk.Label(edit_window, text="URL:", font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(5, 2))
        url_var = tk.StringVar(value=values[1])
        url_entry = ttk.Entry(edit_window, textvariable=url_var, width=60)
        url_entry.pack(fill="x", padx=15, pady=(0, 10))
        
        ttk.Label(edit_window, text="Description:", font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(5, 2))
        desc_var = tk.StringVar(value=values[2])
        desc_entry = ttk.Entry(edit_window, textvariable=desc_var, width=60)
        desc_entry.pack(fill="x", padx=15, pady=(0, 15))
        
        def save_edit():
            new_name = name_var.get().strip()
            new_url = url_var.get().strip()
            new_desc = desc_var.get().strip()
            
            if not new_name or not new_url:
                messagebox.showwarning("Missing Fields", "Name and URL are required.")
                return
            
            key = tags[0]
            APPROVED_SOURCES[key] = {
                "name": new_name,
                "url": new_url,
                "description": new_desc
            }
            self.load_sources_to_tree()
            edit_window.destroy()
            messagebox.showinfo("Success", f"Source updated: {new_name}")
        
        def cancel_edit():
            edit_window.destroy()
        
        # Buttons frame
        button_frame = ttk.Frame(edit_window)
        button_frame.pack(fill="x", padx=15, pady=10)
        
        ttk.Button(button_frame, text="Cancel", 
                  command=cancel_edit).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Save Changes", 
                  command=save_edit, style="Accent.TButton").pack(side="right")
        
        # Select all text in name field for easy editing
        name_entry.select_range(0, tk.END)
        name_entry.focus_set()

    def delete_selected_source(self):
        """Delete the selected source"""
        selection = self.sources_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a source to delete.")
            return
        
        item = selection[0]
        values = self.sources_tree.item(item, "values")
        tags = self.sources_tree.item(item, "tags")
        
        if not values or not tags:
            return
        
        key = tags[0]
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Delete source: {values[0]}?"):
            if key in APPROVED_SOURCES:
                del APPROVED_SOURCES[key]
                self.load_sources_to_tree()
                messagebox.showinfo("Deleted", "Source deleted.")
    
    def setup_header_tab(self, parent):
        """Tab showing the header prompt"""
        ttk.Label(parent, text="Header Prompt (Use to reset LLM context):", 
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=10)
        
        self.header_text = scrolledtext.ScrolledText(parent, height=25, width=80)
        self.header_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.header_text.insert(1.0, HEADER_PROMPT)
        self.header_text.config(state="disabled")
        
        ttk.Button(parent, text="Copy Header Prompt", 
                  command=self.copy_header_prompt).pack(pady=10)
    
    def update_domain_selection(self):
        """Update the selected domains set"""
        self.selected_domains.clear()
        for domain_id, var in self.domain_vars.items():
            if var.get():
                self.selected_domains.add(domain_id)
        
        domain_count = len(self.selected_domains)
        self.status_var.set(f"Selected {domain_count} domain(s) - ready to generate prompts")
    
    def select_all_domains(self):
        """Select all architecture domains"""
        for var in self.domain_vars.values():
            var.set(True)
        self.update_domain_selection()
    
    def clear_domains(self):
        """Clear all domain selections"""
        for var in self.domain_vars.values():
            var.set(False)
        self.update_domain_selection()
    
    def validate_inputs(self):
        """Validate user inputs before generating prompts"""
        if not self.selected_domains:
            messagebox.showwarning("Input Error", "Please select at least one architecture domain")
            return False
            
        organisation = self.org_var.get().strip()
        
        if not organisation:
            messagebox.showwarning("Input Error", "Organisation cannot be empty")
            return False
        return True
    
    def copy_to_clipboard(self, text):
        """Universal clipboard function with better error handling"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.update_status("Copied to clipboard!")
            return True
        except Exception:
            # Fallback: show the text for manual copy
            print(f"Please manually copy this text:\n{text}")
            self.update_status("Please manually copy from console")
            return False
    
    def generate_prompts(self):
        """Generate clean, focused prompts based on selected domains"""
        if not self.validate_inputs():
            return
        
        organisation = self.org_var.get()
        include_sources = self.sources_var.get()
        
        self.update_status("Generating domain-specific prompts...")
        
        # Generate clean prompts for each selected domain
        self.prompts = []
        for domain_id in self.selected_domains:
            domain_info = ARCHITECTURE_DOMAINS[domain_id]
            
            for template in domain_info["prompt_templates"]:
                # Clean prompt without duplicated headers
                prompt_text = template.format(organisation=organisation)
                
                # Add source citations if requested
                if include_sources:
                    sources_section = self.build_sources_section()
                    prompt_text += f"\n\n{sources_section}"
                
                self.prompts.append(prompt_text)
        
        self.current_prompt_index = 0
        self.update_display()
        self.update_status(f"Generated {len(self.prompts)} clean prompts across {len(self.selected_domains)} domains")
    
    def build_sources_section(self):
        """Build the approved sources section for prompts"""
        sources_text = "## Required Sources\n"
        sources_text += "Use these verified sources when relevant:\n"
        
        for key, source in APPROVED_SOURCES.items():
            sources_text += f"- {source['name']}: {source['url']}\n"
        
        sources_text += "\nInclude specific source references in descriptions where appropriate."
        return sources_text
    
    def update_display(self):
        """Update the display with clean prompt presentation"""
        # Clear and update current prompt
        self.current_prompt_text.delete(1.0, tk.END)
        if self.prompts and self.current_prompt_index < len(self.prompts):
            self.current_prompt_text.insert(1.0, self.prompts[self.current_prompt_index])
        
        # Update progress indicator
        if self.prompts:
            self.progress_var.set(f"Prompt {self.current_prompt_index + 1} of {len(self.prompts)}")
        else:
            self.progress_var.set("No prompts generated")
        
        # Clean all prompts list - just show simple preview
        self.all_prompts_text.delete(1.0, tk.END)
        for i, prompt in enumerate(self.prompts):
            status = "▶ " if i == self.current_prompt_index else "  "
            # Clean preview - first line only
            first_line = prompt.split('\n')[0]
            preview = first_line[:80] + "..." if len(first_line) > 80 else first_line
            self.all_prompts_text.insert(tk.END, f"{status}Prompt {i+1}: {preview}\n")
    
    def copy_current_prompt(self):
        """Copy current prompt to clipboard"""
        if self.prompts and self.current_prompt_index < len(self.prompts):
            success = self.copy_to_clipboard(self.prompts[self.current_prompt_index])
            if not success:
                messagebox.showwarning("Copy Failed", "Could not copy to clipboard. Check console for manual copy option.")
    
    def copy_header_prompt(self):
        """Copy header prompt to clipboard"""
        success = self.copy_to_clipboard(HEADER_PROMPT)
        if not success:
            messagebox.showwarning("Copy Failed", "Could not copy header to clipboard. Check console for manual copy option.")
    
    def next_prompt(self):
        """Move to next prompt"""
        if self.current_prompt_index < len(self.prompts) - 1:
            self.current_prompt_index += 1
            self.update_display()
            self.update_status(f"Prompt {self.current_prompt_index + 1} of {len(self.prompts)}")
    
    def previous_prompt(self):
        """Move to previous prompt"""
        if self.current_prompt_index > 0:
            self.current_prompt_index -= 1
            self.update_display()
            self.update_status(f"Prompt {self.current_prompt_index + 1} of {len(self.prompts)}")
    
    def export_prompts(self):
        """Export all prompts to a text file"""
        if not self.prompts:
            messagebox.showwarning("No Prompts", "No prompts to export. Please generate prompts first.")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Prompts"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Generated ArchiMate Domain Prompts\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"Organisation: {self.org_var.get()}\n")
                    f.write(f"Domains: {', '.join([ARCHITECTURE_DOMAINS[d]['name'] for d in self.selected_domains])}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for i, prompt in enumerate(self.prompts, 1):
                        f.write(f"PROMPT {i}:\n")
                        f.write(prompt)
                        f.write(f"\n\n")
                
                self.update_status(f"Prompts exported to {filename}")
                messagebox.showinfo("Success", f"Prompts exported to {filename}")
        except Exception as e:
            self.update_status("Export failed")
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def bind_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.root.bind('<Control-c>', lambda e: self.copy_current_prompt())
        self.root.bind('<Control-n>', lambda e: self.next_prompt())
        self.root.bind('<Control-p>', lambda e: self.previous_prompt())
        self.root.bind('<Control-g>', lambda e: self.generate_prompts())
        self.root.bind('<Control-e>', lambda e: self.export_prompts())
        self.root.bind('<Control-h>', lambda e: self.copy_header_prompt())

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = PromptGenerator(root)
    root.mainloop()
