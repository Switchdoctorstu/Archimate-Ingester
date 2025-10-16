# togaf_launcher.py
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
from pathlib import Path

class TOGAFLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("TOGAF Modeling Pipeline Launcher")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # Store references to running processes
        self.running_processes = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text="TOGAF Modeling Pipeline Launcher", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(main_frame, 
                              text="Launch all three modeling tools simultaneously for your TOGAF architecture workflow",
                              font=("Arial", 10),
                              wraplength=500,
                              justify=tk.CENTER)
        desc_label.pack(pady=(0, 30))
        
        # Tools frame
        tools_frame = ttk.LabelFrame(main_frame, text="Modeling Tools", padding="15")
        tools_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Tool 1: Prompt Builder
        builder_frame = ttk.Frame(tools_frame)
        builder_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(builder_frame, text="1. Prompt Builder", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(builder_frame, text="Generate structured prompts for ArchiMate model creation", 
                 font=("Arial", 9)).pack(anchor=tk.W)
        
        builder_btn_frame = ttk.Frame(builder_frame)
        builder_btn_frame.pack(fill=tk.X, pady=5)
        
        self.builder_btn = ttk.Button(builder_btn_frame, 
                                     text="Launch Builder.py", 
                                     command=self.launch_builder,
                                     state="normal")
        self.builder_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.builder_status = ttk.Label(builder_btn_frame, text="Ready", foreground="green")
        self.builder_status.pack(side=tk.LEFT)
        
        # Tool 2: Data Ingester
        ingester_frame = ttk.Frame(tools_frame)
        ingester_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(ingester_frame, text="2. Data Ingester", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(ingester_frame, text="Import, validate and manage ArchiMate models", 
                 font=("Arial", 9)).pack(anchor=tk.W)
        
        ingester_btn_frame = ttk.Frame(ingester_frame)
        ingester_btn_frame.pack(fill=tk.X, pady=5)
        
        self.ingester_btn = ttk.Button(ingester_btn_frame, 
                                      text="Launch Ingester.py", 
                                      command=self.launch_ingester,
                                      state="normal")
        self.ingester_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.ingester_status = ttk.Label(ingester_btn_frame, text="Ready", foreground="green")
        self.ingester_status.pack(side=tk.LEFT)
        
        # Tool 3: Visualizer
        viewer_frame = ttk.Frame(tools_frame)
        viewer_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(viewer_frame, text="3. 3D Viewer", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(viewer_frame, text="Visualize ArchiMate models in 3D with advanced analysis", 
                 font=("Arial", 9)).pack(anchor=tk.W)
        
        viewer_btn_frame = ttk.Frame(viewer_frame)
        viewer_btn_frame.pack(fill=tk.X, pady=5)
        
        self.viewer_btn = ttk.Button(viewer_btn_frame, 
                                    text="Launch Viewer.py", 
                                    command=self.launch_viewer,
                                    state="normal")
        self.viewer_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.viewer_status = ttk.Label(viewer_btn_frame, text="Ready", foreground="green")
        self.viewer_status.pack(side=tk.LEFT)
        
        # Batch launch button
        batch_frame = ttk.Frame(main_frame)
        batch_frame.pack(fill=tk.X, pady=10)
        
        self.launch_all_btn = ttk.Button(batch_frame, 
                                        text="Launch All Tools", 
                                        command=self.launch_all_tools,
                                        style="Accent.TButton")
        self.launch_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_all = ttk.Label(batch_frame, text="All tools ready", foreground="blue")
        self.status_all.pack(side=tk.LEFT)
        
        # Instructions
        instructions = ttk.Label(main_frame, 
                                text="Tip: Launch all tools at once for seamless workflow. Each tool runs independently.",
                                font=("Arial", 8),
                                foreground="gray")
        instructions.pack(side=tk.BOTTOM, pady=(10, 0))
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("Accent.TButton", font=("Arial", 10, "bold"))
        
    def launch_process(self, script_name, status_label, button):
        """Launch a Python script as a separate process"""
        try:
            # Check if file exists
            if not os.path.exists(script_name):
                messagebox.showerror("File Not Found", 
                                   f"Could not find {script_name}\n\n"
                                   f"Please ensure all three script files are in the same directory:\n"
                                   f"- Builder.py\n"
                                   f"- Ingester.py\n" 
                                   f"- Viewer.py")
                return
            
            # Launch the script
            process = subprocess.Popen([sys.executable, script_name])
            self.running_processes[script_name] = process
            
            # Update UI
            status_label.config(text="Running", foreground="orange")
            button.config(state="disabled")
            
            # Monitor process (non-blocking)
            self.root.after(1000, lambda: self.check_process(script_name, process, status_label, button))
            
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch {script_name}:\n{str(e)}")
            status_label.config(text="Error", foreground="red")
    
    def check_process(self, script_name, process, status_label, button):
        """Check if a process is still running"""
        if process.poll() is None:  # Still running
            self.root.after(1000, lambda: self.check_process(script_name, process, status_label, button))
        else:  # Process ended
            status_label.config(text="Closed", foreground="red")
            button.config(state="normal")
            if script_name in self.running_processes:
                del self.running_processes[script_name]
    
    def launch_builder(self):
        self.launch_process("Builder.py", self.builder_status, self.builder_btn)
    
    def launch_ingester(self):
        self.launch_process("Ingester.py", self.ingester_status, self.ingester_btn)
    
    def launch_viewer(self):
        self.launch_process("Viewer.py", self.viewer_status, self.viewer_btn)
    
    def launch_all_tools(self):
        """Launch all three tools simultaneously"""
        self.launch_all_btn.config(state="disabled")
        self.status_all.config(text="Launching...", foreground="orange")
        
        # Launch each tool with a small delay to avoid resource contention
        self.root.after(100, self.launch_builder)
        self.root.after(500, self.launch_ingester) 
        self.root.after(900, self.launch_viewer)
        
        # Reset batch button after all are launched
        self.root.after(2000, lambda: self.launch_all_btn.config(state="normal"))
        self.root.after(2000, lambda: self.status_all.config(text="All launched", foreground="green"))
    
    def on_closing(self):
        """Handle application closing"""
        # Terminate any running processes
        for script_name, process in self.running_processes.items():
            try:
                process.terminate()
            except:
                pass
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = TOGAFLauncher(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) // 2
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()
