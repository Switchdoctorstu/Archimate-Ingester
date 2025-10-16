import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

from Builder_Config import (DEFAULT_ORGANISATION, DEFAULT_FOCUS, ARCHITECTURE_DOMAINS,
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
        
        ttk.Label(input_frame, text="Focus Area:").grid(row=1, column=0, sticky="w")
        self.focus_var = tk.StringVar(value=DEFAULT_FOCUS)
        self.focus_entry = ttk.Entry(input_frame, textvariable=self.focus_var, width=40)
        self.org_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.focus_entry.grid(row=1, column=1, sticky="ew", padx=5)
        
        # Source requirement checkbox
        self.sources_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="Include source citations", 
                       variable=self.sources_var).grid(row=2, column=1, sticky="w", pady=5)
        
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
        focus = self.focus_var.get().strip()
        
        if not organisation:
            messagebox.showwarning("Input Error", "Organisation cannot be empty")
            return False
        if not focus:
            messagebox.showwarning("Input Error", "Focus area cannot be empty")
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
    
    def setup_sources_tab(self, parent):
        """Tab showing approved sources"""
        ttk.Label(parent, text="Approved Sources for Lincolnshire Council:", 
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=10)
        
        sources_text = scrolledtext.ScrolledText(parent, height=20, width=80)
        sources_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Populate sources
        for key, source in APPROVED_SOURCES.items():
            sources_text.insert(tk.END, 
                               f"• {source['name']}\n"
                               f"  URL: {source['url']}\n"
                               f"  Purpose: {source['description']}\n\n")
        
        sources_text.config(state="disabled")
    
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
    
    def generate_prompts(self):
        """Generate clean, focused prompts based on selected domains"""
        if not self.validate_inputs():
            return
        
        organisation = self.org_var.get()
        focus = self.focus_var.get()
        include_sources = self.sources_var.get()
        
        self.update_status("Generating domain-specific prompts...")
        
        # Generate clean prompts for each selected domain
        self.prompts = []
        for domain_id in self.selected_domains:
            domain_info = ARCHITECTURE_DOMAINS[domain_id]
            
            for template in domain_info["prompt_templates"]:
                # Clean prompt without duplicated headers
                prompt_text = template.format(organisation=organisation, focus=focus)
                
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
                    f.write(f"Focus Area: {self.focus_var.get()}\n")
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
