"""
ENHANCED DIGITAL TWIN DASHBOARD - Enterprise Architecture Analysis
With consistent filtering across all visualization types
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
matplotlib.use('TkAgg')
from pathlib import Path
import json
import time
import math
import numpy as np
from collections import defaultdict, deque

from graphml_core import GraphMLArchimateModel
from networkx_analyzer import ArchimateAnalyzer
from visualization_engine import GraphVisualizer

class EnhancedDigitalTwinDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("GraphML Digital Twin - Enterprise Architecture Analyzer")
        self.root.geometry("1600x1000")
        
        # Initialize core components
        self.model = GraphMLArchimateModel()
        self.analyzer = None
        self.visualizer = None
        self.impact_scores = {}
        self.focused_node = None
        
        # Enhanced color scheme
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#34495e',
            'accent': '#e74c3c',
            'success': '#27ae60',
            'warning': '#f39c12',
            'info': '#9b59b6',
            'background': '#ecf0f1',
            'card_bg': '#ffffff',
            'text_dark': '#2c3e50',
            'text_light': '#7f8c8d',
            'motivation': '#e74c3c',
            'strategy': '#9b59b6',
            'business': '#3498db',
            'application': '#2ecc71',
            'technology': '#f39c12',
            'implementation': '#1abc9c',
            'other': '#95a5a6'
        }
        
        # Filtering state - simplified
        self.current_filters = {
            'layers': ['all'],
            'importance_threshold': 0.0,
            'search_query': '',
            'sort_by': 'importance'
        }
        
        # Dynamic importance ranges
        self.importance_ranges = {
            'all': (0.0, 1.0),
            'medium': (0.0, 1.0),
            'high': (0.0, 1.0),
            'critical': (0.0, 1.0)
        }
        
        self.setup_gui()
    
    def setup_gui(self):
        """Setup enhanced tab-based interface"""
        # Main container with notebook for tabs
        main_container = ttk.Notebook(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.overview_tab = ttk.Frame(main_container)
        self.analysis_tab = ttk.Frame(main_container)
        self.advanced_tab = ttk.Frame(main_container)
        
        main_container.add(self.overview_tab, text="🏢 Overview")
        main_container.add(self.analysis_tab, text="🔍 Analysis")
        main_container.add(self.advanced_tab, text="📊 Advanced")
        
        self.setup_overview_tab()
        self.setup_analysis_tab()
        self.setup_advanced_tab()
    
    def setup_overview_tab(self):
        """Setup overview tab with model statistics and quick actions"""
        # Header
        header_frame = tk.Frame(self.overview_tab, bg=self.colors['primary'], height=80)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="ENTERPRISE ARCHITECTURE ANALYZER", 
                font=('Arial', 20, 'bold'), fg='white', bg=self.colors['primary']).pack(pady=20)
        
        # Quick actions frame
        actions_frame = tk.Frame(self.overview_tab, bg=self.colors['card_bg'], relief=tk.RAISED, bd=2)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Load model section
        load_frame = tk.Frame(actions_frame, bg=self.colors['card_bg'])
        load_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(load_frame, text="Model Management", 
                font=('Arial', 14, 'bold'), bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        self.model_status = tk.Label(load_frame, text="No model loaded", 
                                   font=('Arial', 11), bg=self.colors['card_bg'], fg=self.colors['text_light'])
        self.model_status.pack(anchor=tk.W, pady=5)
        
        load_btn_frame = tk.Frame(load_frame, bg=self.colors['card_bg'])
        load_btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(load_btn_frame, text="📁 Load Archimate XML", command=self.load_model,
                 bg=self.colors['primary'], fg='white', font=('Arial', 11, 'bold'), 
                 padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(load_btn_frame, text="📤 Export GraphML", command=self.export_graphml,
                 bg=self.colors['success'], fg='white', font=('Arial', 11),
                 padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        # Statistics dashboard
        stats_frame = tk.Frame(self.overview_tab, bg=self.colors['background'])
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left - Key metrics
        metrics_frame = tk.Frame(stats_frame, bg=self.colors['card_bg'], relief=tk.RAISED, bd=1)
        metrics_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(metrics_frame, text="ARCHITECTURE METRICS", font=('Arial', 16, 'bold'),
                bg=self.colors['primary'], fg='white').pack(fill=tk.X, pady=10)
        
        # Metric cards
        metric_content = tk.Frame(metrics_frame, bg=self.colors['card_bg'])
        metric_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.total_elements_var = tk.StringVar(value="0")
        self.total_relations_var = tk.StringVar(value="0")
        self.avg_centrality_var = tk.StringVar(value="0.00")
        self.model_complexity_var = tk.StringVar(value="Low")
        
        self.create_metric_card(metric_content, "Total Elements", self.total_elements_var, "🏢", 0)
        self.create_metric_card(metric_content, "Relationships", self.total_relations_var, "🔗", 1)
        self.create_metric_card(metric_content, "Avg Centrality", self.avg_centrality_var, "⭐", 2)
        self.create_metric_card(metric_content, "Complexity", self.model_complexity_var, "📈", 3)
        
        # Right - Layer distribution
        distribution_frame = tk.Frame(stats_frame, bg=self.colors['card_bg'], relief=tk.RAISED, bd=1)
        distribution_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(distribution_frame, text="LAYER DISTRIBUTION", font=('Arial', 16, 'bold'),
                bg=self.colors['primary'], fg='white').pack(fill=tk.X, pady=10)
        
        self.layer_canvas = tk.Canvas(distribution_frame, bg=self.colors['card_bg'], highlightthickness=0)
        self.layer_canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Initial placeholder
        self.show_overview_placeholder()
    
    def setup_analysis_tab(self):
        """Setup enhanced analysis tab with improved workflow and resizable panes"""
        # Create a PanedWindow for resizable panes
        self.main_paned = ttk.PanedWindow(self.analysis_tab, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls and browser (resizable) - Use tk.Frame for borders
        left_panel = tk.Frame(self.main_paned, relief=tk.RAISED, bd=1, bg=self.colors['card_bg'])
        self.main_paned.add(left_panel, weight=1)  # Lower weight for left panel
        
        # Right panel - Visualization (resizable)
        right_panel = tk.Frame(self.main_paned, relief=tk.RAISED, bd=1, bg=self.colors['card_bg'])
        self.main_paned.add(right_panel, weight=3)  # Higher weight for right panel
        
        self.setup_analysis_controls(left_panel)
        self.setup_visualization_panel(right_panel)
    
    def setup_analysis_controls(self, parent):
        """Setup analysis controls with improved filtering"""
        # Search section
        search_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        search_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(search_frame, text="Search Elements", font=('Arial', 12, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        search_input_frame = tk.Frame(search_frame, bg=self.colors['card_bg'])
        search_input_frame.pack(fill=tk.X, pady=8)
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_input_frame, textvariable=self.search_var, 
                               font=('Arial', 11))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.bind('<KeyRelease>', self.on_search)
        
        tk.Button(search_input_frame, text="Clear", command=self.clear_search,
                 bg=self.colors['warning'], fg='white', font=('Arial', 9)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Layer filtering
        filter_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        filter_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(filter_frame, text="Filter by Layer", font=('Arial', 12, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        # Layer checkboxes in a compact grid
        layer_frame = tk.Frame(filter_frame, bg=self.colors['card_bg'])
        layer_frame.pack(fill=tk.X, pady=8)
        
        self.layer_vars = {}
        layers = [
            ("All", "all"),
            ("Motivation", "Motivation"),
            ("Strategy", "Strategy"), 
            ("Business", "Business"),
            ("Application", "Application"),
            ("Technology", "Technology"),
            ("Implementation", "Implementation")
        ]
        
        for i, (display_name, layer_key) in enumerate(layers):
            var = tk.BooleanVar(value=(layer_key == "all"))
            cb = tk.Checkbutton(layer_frame, text=display_name, variable=var,
                              command=self.on_filter_change, bg=self.colors['card_bg'],
                              font=('Arial', 9))
            cb.grid(row=i//4, column=i%4, sticky=tk.W, padx=2, pady=1)
            self.layer_vars[layer_key] = var
        
        # Dynamic importance threshold
        importance_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        importance_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(importance_frame, text="Importance Filter", font=('Arial', 12, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        self.importance_var = tk.StringVar(value="all")
        self.importance_options_frame = tk.Frame(importance_frame, bg=self.colors['card_bg'])
        self.importance_options_frame.pack(fill=tk.X, pady=5)
        
        # Element browser
        browser_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        browser_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)
        
        # Browser header with sort
        browser_header = tk.Frame(browser_frame, bg=self.colors['card_bg'])
        browser_header.pack(fill=tk.X)
        
        tk.Label(browser_header, text="Element Browser", font=('Arial', 12, 'bold'),
                bg=self.colors['card_bg']).pack(side=tk.LEFT)
        
        self.sort_var = tk.StringVar(value="importance")
        sort_menu = ttk.Combobox(browser_header, textvariable=self.sort_var,
                                values=["name", "type", "layer", "importance", "centrality"],
                                state="readonly", width=12)
        sort_menu.pack(side=tk.RIGHT, padx=5)
        sort_menu.bind('<<ComboboxSelected>>', self.on_sort_change)
        
        # Enhanced treeview
        tree_frame = tk.Frame(browser_frame, bg=self.colors['card_bg'])
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        
        columns = ('name', 'type', 'layer', 'importance', 'centrality')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        
        self.tree.heading('name', text='Element Name')
        self.tree.heading('type', text='Type')
        self.tree.heading('layer', text='Layer')
        self.tree.heading('importance', text='Importance')
        self.tree.heading('centrality', text='Centrality')
        
        self.tree.column('name', width=150)
        self.tree.column('type', width=80)
        self.tree.column('layer', width=70)
        self.tree.column('importance', width=70)
        self.tree.column('centrality', width=70)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-1>', self.on_element_double_click)
        
        # Action buttons
        action_frame = tk.Frame(browser_frame, bg=self.colors['card_bg'])
        action_frame.pack(fill=tk.X, pady=8)
        
        tk.Button(action_frame, text="🎯 Set Focus", command=self.set_focus_from_selection,
                 bg=self.colors['accent'], fg='white', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=2)
        
        tk.Button(action_frame, text="🔍 Impact Analysis", command=self.run_impact_analysis,
                 bg=self.colors['primary'], fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(action_frame, text="🗑️ Clear Focus", command=self.clear_focus,
                 bg=self.colors['warning'], fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        # Focus element display
        focus_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        focus_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(focus_frame, text="Current Focus", font=('Arial', 11, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        self.focus_label = tk.Label(focus_frame, text="No focus element selected", 
                                  font=('Arial', 9), bg=self.colors['card_bg'], fg=self.colors['text_light'])
        self.focus_label.pack(anchor=tk.W, pady=3)
        
        # Update importance options when model loads
        self.update_importance_options()
    
    def update_importance_options(self):
        """Update importance options based on current element distribution"""
        if not hasattr(self, 'importance_options_frame') or not self.model.graph.nodes():
            return
        
        # Clear existing options
        for widget in self.importance_options_frame.winfo_children():
            widget.destroy()
        
        # Get current importance scores from filtered elements
        elements = self.get_filtered_elements()
        if not elements:
            return
        
        importance_scores = [data.get('importance_score', 0) for _, data in elements]
        if not importance_scores:
            return
        
        # Calculate dynamic thresholds based on percentiles
        scores_array = np.array(importance_scores)
        low_threshold = np.percentile(scores_array, 33)  # Bottom 33%
        medium_threshold = np.percentile(scores_array, 66)  # Middle 33%
        high_threshold = np.percentile(scores_array, 90)  # Top 10%
        
        # Update ranges
        self.importance_ranges = {
            'all': (0.0, 1.0),
            'medium': (low_threshold, 1.0),
            'high': (medium_threshold, 1.0),
            'critical': (high_threshold, 1.0)
        }
        
        # Create radio buttons with dynamic labels
        importance_options = [
            (f"All Levels ({len(elements)} elements)", "all"),
            (f"⭐ Medium+ (≥{low_threshold:.2f})", "medium"),
            (f"⭐⭐ High+ (≥{medium_threshold:.2f})", "high"), 
            (f"⭐⭐⭐ Critical (≥{high_threshold:.2f})", "critical")
        ]
        
        for text, value in importance_options:
            rb = tk.Radiobutton(self.importance_options_frame, text=text, variable=self.importance_var,
                              value=value, command=self.on_filter_change, 
                              bg=self.colors['card_bg'], font=('Arial', 8))
            rb.pack(anchor=tk.W, pady=1)
    
    def setup_visualization_panel(self, parent):
        """Setup enhanced visualization panel"""
        # Visualization controls
        viz_control_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        viz_control_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(viz_control_frame, text="Visualization", font=('Arial', 12, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        # Visualization type selector
        viz_type_frame = tk.Frame(viz_control_frame, bg=self.colors['card_bg'])
        viz_type_frame.pack(fill=tk.X, pady=8)
        
        self.viz_type = tk.StringVar(value="force")
        
        viz_types = [
            ("Force-Directed", "force"),
            ("Layered Layout", "layered"), 
            ("Impact Heatmap", "heatmap"),
            ("Radial View", "radial")
        ]
        
        for text, value in viz_types:
            rb = tk.Radiobutton(viz_type_frame, text=text, variable=self.viz_type,
                              value=value, command=self.on_viz_type_change,
                              bg=self.colors['card_bg'], font=('Arial', 9))
            rb.pack(side=tk.LEFT, padx=8)
        
        # Quick action buttons
        quick_action_frame = tk.Frame(viz_control_frame, bg=self.colors['card_bg'])
        quick_action_frame.pack(fill=tk.X, pady=8)
        
        tk.Button(quick_action_frame, text="🔄 Refresh View", command=self.update_visualization,
                 bg=self.colors['success'], fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(quick_action_frame, text="💾 Export HTML", command=self.export_interactive,
                 bg=self.colors['info'], fg='white', font=('Arial', 9)).pack(side=tk.LEFT, padx=2)
        
        # Matplotlib canvas
        viz_canvas_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        viz_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        self.fig, self.ax = plt.subplots(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, viz_canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add navigation toolbar
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        self.toolbar = NavigationToolbar2Tk(self.canvas, viz_canvas_frame)
        self.toolbar.update()
        
        # Initial message
        self.show_visualization_placeholder()
    
    def setup_advanced_tab(self):
        """Setup advanced analysis tools tab"""
        # Create PanedWindow for resizable panes in advanced tab too
        advanced_paned = ttk.PanedWindow(self.advanced_tab, orient=tk.HORIZONTAL)
        advanced_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left - Analysis tools - Use tk.Frame for borders
        tools_frame = tk.Frame(advanced_paned, relief=tk.RAISED, bd=1, bg=self.colors['card_bg'])
        advanced_paned.add(tools_frame, weight=1)
        
        # Right - Results display
        results_frame = tk.Frame(advanced_paned, relief=tk.RAISED, bd=1, bg=self.colors['card_bg'])
        advanced_paned.add(results_frame, weight=2)
        
        # Tools content
        tk.Label(tools_frame, text="ADVANCED ANALYSIS TOOLS", font=('Arial', 14, 'bold'),
                bg=self.colors['primary'], fg='white').pack(fill=tk.X, pady=10)
        
        tools_content = tk.Frame(tools_frame, bg=self.colors['card_bg'])
        tools_content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Analysis buttons
        analyses = [
            ("Centrality Analysis", self.run_centrality_analysis, "Find most important nodes"),
            ("Community Detection", self.run_community_detection, "Discover architecture clusters"),
            ("Bottleneck Analysis", self.find_bottlenecks, "Identify critical connections"),
            ("Value Stream View", self.show_value_stream, "Business process focus"),
            ("Health Metrics", self.show_health_metrics, "Architecture quality assessment")
        ]
        
        for i, (text, command, description) in enumerate(analyses):
            btn_frame = tk.Frame(tools_content, bg=self.colors['card_bg'])
            btn_frame.pack(fill=tk.X, pady=6)
            
            tk.Button(btn_frame, text=text, command=command,
                     bg=self.colors['primary'], fg='white', font=('Arial', 10),
                     width=18).pack(side=tk.LEFT)
            
            tk.Label(btn_frame, text=description, font=('Arial', 8),
                    bg=self.colors['card_bg'], fg=self.colors['text_light']).pack(side=tk.LEFT, padx=8)
        
        # Results content
        tk.Label(results_frame, text="ANALYSIS RESULTS", font=('Arial', 14, 'bold'),
                bg=self.colors['primary'], fg='white').pack(fill=tk.X, pady=10)
        
        results_content = tk.Frame(results_frame, bg=self.colors['card_bg'])
        results_content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        self.results_text = scrolledtext.ScrolledText(results_content, height=20, 
                                                     font=('Consolas', 9),
                                                     bg='#f8f9fa', fg=self.colors['text_dark'])
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial message
        self.results_text.insert(tk.END, "Run analyses to see results here...\n\n")
        self.results_text.insert(tk.END, "Available analyses:\n")
        self.results_text.insert(tk.END, "• Centrality Analysis - Find key nodes\n")
        self.results_text.insert(tk.END, "• Community Detection - Discover clusters\n") 
        self.results_text.insert(tk.END, "• Bottleneck Analysis - Identify critical paths\n")
        self.results_text.insert(tk.END, "• Value Stream View - Business process focus\n")
        self.results_text.insert(tk.END, "• Health Metrics - Architecture quality\n")
    
    def create_metric_card(self, parent, title, value_var, icon, row):
        """Create enhanced metric card"""
        card = tk.Frame(parent, bg=self.colors['background'], relief=tk.RAISED, bd=2)
        card.grid(row=row//2, column=row%2, padx=8, pady=8, sticky='nsew')
        
        # Icon and title
        header_frame = tk.Frame(card, bg=self.colors['primary'])
        header_frame.pack(fill=tk.X)
        
        tk.Label(header_frame, text=icon, font=('Arial', 14),
                bg=self.colors['primary'], fg='white').pack(side=tk.LEFT, padx=8, pady=4)
        tk.Label(header_frame, text=title, font=('Arial', 10, 'bold'),
                bg=self.colors['primary'], fg='white').pack(side=tk.LEFT, padx=4, pady=4)
        
        # Value
        value_label = tk.Label(card, textvariable=value_var, font=('Arial', 18, 'bold'),
                              bg=self.colors['background'], fg=self.colors['primary'])
        value_label.pack(pady=15)
        
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
    
    # =========================================================================
    # FILTERING AND BROWSING - IMPROVED WORKFLOW
    # =========================================================================
    
    def on_search(self, event=None):
        """Handle search with live filtering"""
        self.current_filters['search_query'] = self.search_var.get()
        self.update_tree_display()
        self.update_importance_options()  # Update importance options when search changes
    
    def clear_search(self):
        """Clear search box"""
        self.search_var.set("")
        self.current_filters['search_query'] = ""
        self.update_tree_display()
        self.update_importance_options()
    
    def on_filter_change(self):
        """Handle filter changes"""
        # Get selected layers
        selected_layers = []
        for layer_key, var in self.layer_vars.items():
            if var.get():
                if layer_key == "all":
                    selected_layers = ["all"]
                    break
                selected_layers.append(layer_key)
        
        if not selected_layers:
            selected_layers = ["all"]
            self.layer_vars["all"].set(True)
        
        self.current_filters['layers'] = selected_layers
        
        # Get importance threshold from dynamic ranges
        importance_key = self.importance_var.get()
        self.current_filters['importance_threshold'] = self.importance_ranges[importance_key][0]
        
        self.update_tree_display()
    
    def on_sort_change(self, event=None):
        """Handle sort changes"""
        self.current_filters['sort_by'] = self.sort_var.get()
        self.update_tree_display()
    
    def on_tree_select(self, event):
        """Handle tree selection (single click - preview)"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            element_id = self.tree.item(item, 'tags')[0]
            self.preview_element(element_id)
    
    def on_element_double_click(self, event):
        """Handle element double-click (set focus)"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            element_id = self.tree.item(item, 'tags')[0]
            self.set_focus_element(element_id)
    
    def set_focus_from_selection(self):
        """Set focus from current tree selection"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            element_id = self.tree.item(item, 'tags')[0]
            self.set_focus_element(element_id)
        else:
            messagebox.showwarning("Warning", "Please select an element first")
    
    def update_tree_display(self):
        """Update tree display with current filters"""
        if not hasattr(self.model, 'graph') or not self.model.graph.nodes():
            return
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get filtered and sorted elements
        elements = self.get_filtered_elements()
        
        # Populate tree
        for element_id, element_data in elements:
            node_data = self.model.graph.nodes[element_id]
            self.tree.insert('', tk.END, values=(
                node_data.get('name', 'Unnamed'),
                node_data.get('type', 'Unknown'),
                node_data.get('layer', 'Unknown'),
                f"{node_data.get('importance_score', 0):.3f}",
                f"{node_data.get('centrality', 0):.3f}"
            ), tags=(element_id,))
    
    def get_filtered_elements(self):
        """Get elements filtered by current criteria"""
        elements = []
        
        for node_id, data in self.model.graph.nodes(data=True):
            if self.passes_current_filters(node_id):
                elements.append((node_id, data))
        
        # Sort elements
        sort_key = self.current_filters['sort_by']
        if sort_key == "name":
            elements.sort(key=lambda x: x[1].get('name', '').lower())
        elif sort_key == "type":
            elements.sort(key=lambda x: x[1].get('type', ''))
        elif sort_key == "layer":
            elements.sort(key=lambda x: x[1].get('layer', ''))
        elif sort_key == "importance":
            elements.sort(key=lambda x: x[1].get('importance_score', 0), reverse=True)
        elif sort_key == "centrality":
            elements.sort(key=lambda x: x[1].get('centrality', 0), reverse=True)
        
        return elements
    
    def passes_current_filters(self, node_id):
        """Check if a node passes all current filters"""
        if node_id not in self.model.graph:
            return False
        
        node_data = self.model.graph.nodes[node_id]
        
        # Apply layer filter
        layer_filter = self.current_filters['layers']
        if "all" not in layer_filter and node_data.get('layer') not in layer_filter:
            return False
        
        # Apply importance filter
        importance = node_data.get('importance_score', 0)
        if importance < self.current_filters['importance_threshold']:
            return False
        
        # Apply search filter
        search_query = self.current_filters['search_query'].lower()
        if search_query:
            name = node_data.get('name', '').lower()
            elem_type = node_data.get('type', '').lower()
            if search_query not in name and search_query not in elem_type:
                return False
        
        return True
    
    def preview_element(self, element_id):
        """Preview element details without setting focus"""
        if element_id in self.model.graph:
            node_data = self.model.graph.nodes[element_id]
            
            # Update focus label temporarily
            self.focus_label.config(
                text=f"Preview: {node_data.get('name', 'Unknown')}",
                fg=self.colors['info']
            )
            
            # Show details in results
            details = f"🔍 PREVIEW: {node_data.get('name', 'Unknown')}\n"
            details += f"Type: {node_data.get('type', 'Unknown')} | Layer: {node_data.get('layer', 'Unknown')}\n"
            details += f"Importance: {node_data.get('importance_score', 0):.3f} | Centrality: {node_data.get('centrality', 0):.3f}\n"
            details += f"AI Category: {node_data.get('ai_category', 'Unknown')}\n\n"
            
            # Show metrics if available
            metrics = node_data.get('metrics', {})
            if metrics:
                details += "Metrics:\n"
                for metric, value in metrics.items():
                    details += f"  • {metric}: {value}\n"
            
            self.show_results(details)
    
    def set_focus_element(self, element_id):
        """Set focus element for analysis"""
        if element_id in self.model.graph:
            self.focused_node = element_id
            node_data = self.model.graph.nodes[element_id]
            
            # Update focus label
            self.focus_label.config(
                text=f"🎯 {node_data.get('name', 'Unknown')}",
                fg=self.colors['accent']
            )
            
            messagebox.showinfo("Focus Set", 
                              f"Focus element set to:\n{node_data.get('name', 'Unknown')}\n\n"
                              f"Now run Impact Analysis to see propagation effects.")
    
    def clear_focus(self):
        """Clear current focus"""
        self.focused_node = None
        self.impact_scores = {}
        self.focus_label.config(text="No focus element selected", fg=self.colors['text_light'])
        self.update_visualization()
        self.show_results("Focus cleared. Select an element and run impact analysis.")
    
    # =========================================================================
    # VISUALIZATION METHODS - WITH CONSISTENT FILTERING
    # =========================================================================
    
    def on_viz_type_change(self):
        """Handle visualization type change"""
        self.update_visualization()
    
    def update_visualization(self):
        """Update visualization based on current type and focus - WITH CONSISTENT FILTERING"""
        if not self.visualizer:
            self.show_visualization_placeholder()
            return
        
        try:
            self.fig.clf()
            
            viz_type = self.viz_type.get()
            
            # ALWAYS use filtered impact scores for ALL visualization types
            impact_for_viz = self.get_filtered_impact_scores() if self.impact_scores else None
            
            if viz_type == "force":
                # For force-directed layout, we need to create a subgraph with filtered nodes
                self.plot_filtered_force_directed(impact_for_viz)
            elif viz_type == "layered":
                # For layered layout, use filtered impact scores
                self.plot_filtered_layered_layout(impact_for_viz)
            elif viz_type == "heatmap":
                if not impact_for_viz:
                    messagebox.showwarning("Warning", "Run impact analysis first for heatmap")
                    self.show_visualization_placeholder()
                    return
                self.visualizer.plot_impact_heatmap(impact_for_viz)
            elif viz_type == "radial":
                if not impact_for_viz:
                    messagebox.showwarning("Warning", "Run impact analysis first for radial view")
                    self.show_visualization_placeholder()
                    return
                # Radial view already uses filtered scores correctly
                self.plot_radial_impact(impact_for_viz)
            
            self.canvas.draw()
            
        except Exception as e:
            messagebox.showerror("Error", f"Visualization failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.show_visualization_placeholder()
    
    def plot_filtered_force_directed(self, impact_scores):
        """Create force-directed layout with filtered nodes only"""
        if not impact_scores:
            # If no impact scores, show all filtered elements
            filtered_elements = self.get_filtered_elements()
            if not filtered_elements:
                self.show_no_data_message()
                return
            
            # Create a subgraph with only filtered elements
            filtered_nodes = [elem_id for elem_id, _ in filtered_elements]
            subgraph = self.model.graph.subgraph(filtered_nodes)
            
            # Create a temporary visualizer for the subgraph
            temp_model = GraphMLArchimateModel()
            temp_model.graph = subgraph
            temp_visualizer = GraphVisualizer(temp_model)
            temp_visualizer.plot_force_directed_layout()
        else:
            # Use impact scores but ensure we're only showing filtered nodes
            filtered_impact = {}
            for node, score in impact_scores.items():
                if node in self.model.graph and self.passes_current_filters(node):
                    filtered_impact[node] = score
            
            if not filtered_impact:
                self.show_no_data_message()
                return
            
            # Create subgraph with filtered nodes that have impact scores
            filtered_nodes = list(filtered_impact.keys())
            subgraph = self.model.graph.subgraph(filtered_nodes)
            
            temp_model = GraphMLArchimateModel()
            temp_model.graph = subgraph
            temp_visualizer = GraphVisualizer(temp_model)
            temp_visualizer.plot_force_directed_layout(filtered_impact)
    
    def plot_filtered_layered_layout(self, impact_scores):
        """Create layered layout with filtered nodes only"""
        if not impact_scores:
            # If no impact scores, show all filtered elements
            filtered_elements = self.get_filtered_elements()
            if not filtered_elements:
                self.show_no_data_message()
                return
            
            filtered_nodes = [elem_id for elem_id, _ in filtered_elements]
            subgraph = self.model.graph.subgraph(filtered_nodes)
            
            temp_model = GraphMLArchimateModel()
            temp_model.graph = subgraph
            temp_visualizer = GraphVisualizer(temp_model)
            temp_visualizer.plot_layered_layout()
        else:
            # Use impact scores but ensure we're only showing filtered nodes
            filtered_impact = {}
            for node, score in impact_scores.items():
                if node in self.model.graph and self.passes_current_filters(node):
                    filtered_impact[node] = score
            
            if not filtered_impact:
                self.show_no_data_message()
                return
            
            filtered_nodes = list(filtered_impact.keys())
            subgraph = self.model.graph.subgraph(filtered_nodes)
            
            temp_model = GraphMLArchimateModel()
            temp_model.graph = subgraph
            temp_visualizer = GraphVisualizer(temp_model)
            temp_visualizer.plot_layered_layout(filtered_impact)
    
    def plot_radial_impact(self, impact_scores):
        """Create a proper radial impact visualization (from old code)"""
        if not self.focused_node or not impact_scores:
            return
        
        # Clear the figure
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        
        # Get focus element data
        focus_data = self.model.graph.nodes[self.focused_node]
        focus_name = focus_data.get('name', self.focused_node)
        
        # Prepare data for radial plot - ALREADY FILTERED by get_filtered_impact_scores()
        nodes_to_plot = []
        for node_id, score in impact_scores.items():
            if score > 0.01 and node_id != self.focused_node:  # Only significant impacts
                node_data = self.model.graph.nodes[node_id]
                nodes_to_plot.append({
                    'id': node_id,
                    'name': node_data.get('name', 'Unknown'),
                    'layer': node_data.get('layer', 'Other'),
                    'score': score,
                    'importance': node_data.get('importance_score', 0)
                })
        
        if not nodes_to_plot:
            ax.text(0.5, 0.5, "No significant impacts detected", 
                   ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.axis('off')
            return
        
        # Sort by impact score
        nodes_to_plot.sort(key=lambda x: x['score'], reverse=True)
        
        # Create radial positions
        n_nodes = len(nodes_to_plot)
        angles = np.linspace(0, 2 * np.pi, n_nodes, endpoint=False)
        
        # Plot focus element in center
        ax.scatter(0, 0, s=500, c='red', alpha=0.8, label='Focus')
        ax.text(0, 0, '★', ha='center', va='center', fontsize=16, color='white', fontweight='bold')
        
        # Plot impacted elements in circle
        radius = 1.0
        for i, node in enumerate(nodes_to_plot):
            angle = angles[i]
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            
            # Size based on impact score
            size = 100 + (node['score'] * 400)
            
            # Color based on layer
            color = self.colors.get(node['layer'].lower(), self.colors['other'])
            
            # Plot node
            ax.scatter(x, y, s=size, c=color, alpha=0.7, edgecolors='white', linewidth=1)
            
            # Draw connection line
            ax.plot([0, x], [0, y], 'gray', alpha=0.3, linewidth=0.5)
            
            # Add label
            label_radius = 1.2
            label_x = label_radius * np.cos(angle)
            label_y = label_radius * np.sin(angle)
            
            # Truncate name for display
            display_name = node['name'][:15] + '...' if len(node['name']) > 15 else node['name']
            ax.text(label_x, label_y, display_name, 
                   ha='center', va='center', fontsize=8, 
                   rotation=angle*180/np.pi if angle > np.pi/2 and angle < 3*np.pi/2 else angle*180/np.pi + 180,
                   rotation_mode='anchor')
            
            # Add impact score
            score_x = (radius + 0.1) * np.cos(angle)
            score_y = (radius + 0.1) * np.sin(angle)
            ax.text(score_x, score_y, f'{node["score"]:.2f}', 
                   ha='center', va='center', fontsize=7, color='red', fontweight='bold')
        
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(f'Radial Impact View: {focus_name}', fontsize=14, fontweight='bold', pad=20)
        
        # Add legend for layers
        layers_present = set(node['layer'] for node in nodes_to_plot)
        legend_elements = []
        for layer in layers_present:
            color = self.colors.get(layer.lower(), self.colors['other'])
            legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                            markerfacecolor=color, markersize=8, label=layer))
        
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.1, 1.1))
    
    def get_filtered_impact_scores(self):
        """Get impact scores filtered by current thresholds - ENHANCED"""
        if not self.impact_scores:
            return {}
        
        filtered_scores = {}
        
        for node, score in self.impact_scores.items():
            if score >= 0.01:  # Only significant impacts
                # Also check node passes all current filters
                if self.passes_current_filters(node):
                    filtered_scores[node] = score
        
        return filtered_scores
    
    def show_no_data_message(self):
        """Show message when no data matches filters"""
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        ax.text(0.5, 0.5, 
                "No elements match current filters\n\n"
                "Try adjusting:\n"
                "• Layer filters\n"
                "• Importance threshold\n" 
                "• Search query",
                ha='center', va='center', transform=ax.transAxes, 
                fontsize=12, wrap=True)
        ax.axis('off')
    
    def show_visualization_placeholder(self):
        """Show visualization placeholder"""
        self.fig.clf()
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, 
                    "Enterprise Architecture Visualizer\n\n"
                    "1. Load an Archimate model\n"
                    "2. Browse and filter elements\n" 
                    "3. Set focus element\n"
                    "4. Run impact analysis\n"
                    "5. Explore different visualizations",
                    ha='center', va='center', transform=self.ax.transAxes, 
                    fontsize=12, wrap=True)
        self.ax.axis('off')
        self.canvas.draw()
    
    def show_overview_placeholder(self):
        """Show overview placeholder"""
        self.layer_canvas.delete("all")
        width = self.layer_canvas.winfo_width()
        height = self.layer_canvas.winfo_height()
        
        if width > 1 and height > 1:
            self.layer_canvas.create_text(width/2, height/2, 
                                        text="Load a model to see architecture overview\n\n"
                                             "Key metrics and layer distribution\n"
                                             "will be displayed here",
                                        font=('Arial', 12), fill=self.colors['text_light'],
                                        justify=tk.CENTER)
    
    # =========================================================================
    # MODEL MANAGEMENT
    # =========================================================================
    
    def load_model(self):
        """Load Archimate XML model"""
        file_path = filedialog.askopenfilename(
            title="Select Archimate XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.model_status.config(text="Loading model...")
                self.root.update()
                
                success = self.model.load_archimate_xml(Path(file_path))
                if success:
                    self.model_status.config(text=f"Loaded: {self.model.name}")
                    
                    # Initialize analyzer and visualizer
                    self.analyzer = ArchimateAnalyzer(self.model)
                    self.visualizer = GraphVisualizer(self.model)
                    
                    # Update displays
                    self.update_model_display()
                    self.update_tree_display()
                    self.update_importance_options()  # Initialize importance options
                    self.update_visualization()
                    
                    messagebox.showinfo("Success", 
                                      f"Model loaded successfully!\n\n"
                                      f"Elements: {self.model.get_node_count()}\n"
                                      f"Relationships: {self.model.get_edge_count()}\n\n"
                                      f"Use the Analysis tab to explore the architecture.")
                else:
                    messagebox.showerror("Error", "Failed to load model!")
            except Exception as e:
                messagebox.showerror("Error", f"Error loading model: {str(e)}")
    
    def update_model_display(self):
        """Update model statistics and metrics"""
        if not self.model.get_node_count():
            return
        
        # Update metric cards
        self.total_elements_var.set(str(self.model.get_node_count()))
        self.total_relations_var.set(str(self.model.get_edge_count()))
        
        # Calculate average centrality
        centralities = [data.get('centrality', 0) for data in self.model.graph.nodes.values()]
        avg_centrality = sum(centralities) / len(centralities) if centralities else 0
        self.avg_centrality_var.set(f"{avg_centrality:.3f}")
        
        # Calculate complexity
        complexity_ratio = self.model.get_edge_count() / max(1, self.model.get_node_count())
        if complexity_ratio < 1:
            complexity = "Low"
        elif complexity_ratio < 2:
            complexity = "Medium"
        else:
            complexity = "High"
        self.model_complexity_var.set(complexity)
        
        # Update layer distribution
        self.update_layer_distribution()
    
    def update_layer_distribution(self):
        """Update layer distribution chart"""
        self.layer_canvas.delete("all")
        
        if not self.model.get_node_count():
            return
        
        width = self.layer_canvas.winfo_width()
        height = self.layer_canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # Count elements by layer
        layer_counts = defaultdict(int)
        for data in self.model.graph.nodes.values():
            layer = data.get('layer', 'Other')
            layer_counts[layer] += 1
        
        layers = ["Motivation", "Strategy", "Business", "Application", "Technology", "Implementation", "Other"]
        max_count = max(layer_counts.values()) if layer_counts else 1
        
        # Draw bar chart
        bar_width = width / (len(layers) + 1)
        for i, layer in enumerate(layers):
            count = layer_counts.get(layer, 0)
            bar_height = (count / max_count) * (height - 100)
            x1 = i * bar_width + 50
            y1 = height - 50 - bar_height
            x2 = (i + 0.8) * bar_width + 50
            y2 = height - 50
            
            color = self.colors.get(layer.lower(), self.colors['other'])
            self.layer_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='white')
            self.layer_canvas.create_text(x1 + bar_width/2, height - 30, text=layer, 
                                        font=('Arial', 8), angle=45, anchor=tk.NE)
            self.layer_canvas.create_text(x1 + bar_width/2, y1 - 10, text=str(count),
                                        font=('Arial', 9, 'bold'), fill=self.colors['text_dark'])
    
    # =========================================================================
    # ANALYSIS METHODS
    # =========================================================================
    
    def run_impact_analysis(self):
        """Run impact analysis on focused node"""
        if not self.focused_node:
            messagebox.showwarning("Warning", "Please select a focus element first!")
            return
        
        try:
            self.impact_scores = self.model.get_impact_analysis(self.focused_node, max_depth=3)
            
            # Update visualization
            self.update_visualization()
            
            # Show results
            self.show_impact_results()
            
            messagebox.showinfo("Success", 
                              "Impact analysis completed!\n\n"
                              "Use filters to focus on significant impacts.")
        except Exception as e:
            messagebox.showerror("Error", f"Impact analysis failed: {str(e)}")
    
    def show_impact_results(self):
        """Display impact analysis results"""
        if not self.impact_scores:
            return
        
        filtered_scores = self.get_filtered_impact_scores()
        
        # Group by layer
        layer_impacts = {}
        for node, score in filtered_scores.items():
            if score > 0.01:  # Only significant impacts
                layer = self.model.graph.nodes[node].get('layer', 'Other')
                if layer not in layer_impacts:
                    layer_impacts[layer] = []
                layer_impacts[layer].append((node, score))
        
        results = "IMPACT ANALYSIS RESULTS\n"
        results += "=" * 50 + "\n\n"
        
        focus_name = self.model.graph.nodes[self.focused_node].get('name', self.focused_node)
        results += f"Focus Element: {focus_name}\n"
        results += f"Total Affected Elements: {len([s for s in filtered_scores.values() if s > 0.01])}\n"
        results += f"Filtered from: {len([s for s in self.impact_scores.values() if s > 0.01])} total impacts\n\n"
        
        for layer in ['Motivation', 'Strategy', 'Business', 'Application', 'Technology', 'Implementation']:
            if layer in layer_impacts:
                results += f"{layer.upper()} LAYER:\n"
                # Sort by impact score
                layer_impacts[layer].sort(key=lambda x: x[1], reverse=True)
                for node, score in layer_impacts[layer][:8]:  # Top 8 per layer
                    node_name = self.model.graph.nodes[node].get('name', node)
                    results += f"  {score:.3f} - {node_name}\n"
                results += "\n"
        
        self.show_results(results)
    
    def run_centrality_analysis(self):
        """Run centrality analysis"""
        if not self.analyzer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        try:
            centrality_scores = self.analyzer.analyze_centrality()
            
            # Create visualization
            self.fig.clf()
            self.visualizer.plot_centrality_analysis(centrality_scores)
            self.canvas.draw()
            
            # Show results
            results = "CENTRALITY ANALYSIS RESULTS\n"
            results += "=" * 50 + "\n\n"
            
            for measure, scores in centrality_scores.items():
                results += f"{measure.upper()} CENTRALITY:\n"
                top_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
                for node, score in top_nodes:
                    node_name = self.model.graph.nodes[node].get('name', node)
                    results += f"  {node_name}: {score:.4f}\n"
                results += "\n"
            
            self.show_results(results)
        except Exception as e:
            messagebox.showerror("Error", f"Centrality analysis failed: {str(e)}")
    
    def run_community_detection(self):
        """Run community detection"""
        if not self.analyzer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        try:
            communities = self.analyzer.detect_communities()
            
            # Create visualization
            self.fig.clf()
            self.visualizer.plot_community_structure(communities)
            self.canvas.draw()
            
            # Show results
            results = "COMMUNITY DETECTION RESULTS\n"
            results += "=" * 50 + "\n\n"
            
            for comm_id, nodes in communities.items():
                results += f"Community {comm_id + 1}: {len(nodes)} nodes\n"
                # Show top nodes in community
                community_nodes = [(node, self.model.graph.nodes[node].get('importance_score', 0)) 
                                 for node in nodes]
                community_nodes.sort(key=lambda x: x[1], reverse=True)
                
                for node, score in community_nodes[:5]:  # Top 5 nodes
                    node_name = self.model.graph.nodes[node].get('name', node)
                    results += f"  {node_name} (importance: {score:.3f})\n"
                results += "\n"
            
            self.show_results(results)
        except Exception as e:
            messagebox.showerror("Error", f"Community detection failed: {str(e)}")
    
    def find_bottlenecks(self):
        """Find architecture bottlenecks"""
        if not self.analyzer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        try:
            bottlenecks = self.analyzer.find_bottlenecks()
            
            results = "ARCHITECTURE BOTTLENECKS\n"
            results += "=" * 50 + "\n\n"
            
            for i, (u, v) in enumerate(bottlenecks[:10], 1):
                u_name = self.model.graph.nodes[u].get('name', u)
                v_name = self.model.graph.nodes[v].get('name', v)
                rel_data = self.model.graph[u][v]
                rel_type = rel_data.get('relationship_type', 'Unknown')
                
                results += f"{i}. {u_name} → {v_name}\n"
                results += f"   Type: {rel_type}, Weight: {rel_data.get('weight', 0.5):.2f}\n\n"
            
            self.show_results(results)
        except Exception as e:
            messagebox.showerror("Error", f"Bottleneck analysis failed: {str(e)}")
    
    def show_value_stream(self):
        """Show value stream focused view"""
        if not self.visualizer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        try:
            # Apply business-focused filters
            self.layer_vars["Business"].set(True)
            self.layer_vars["all"].set(False)
            self.importance_var.set("medium")
            self.on_filter_change()
            
            self.fig.clf()
            impact_for_viz = self.impact_scores if self.impact_scores else None
            self.visualizer.plot_layered_layout(impact_for_viz, "Value Stream View")
            self.canvas.draw()
            
            self.show_results("Value Stream View activated.\nFocusing on Business layer with medium+ importance.")
        except Exception as e:
            messagebox.showerror("Error", f"Value stream view failed: {str(e)}")
    
    def show_health_metrics(self):
        """Show architecture health metrics"""
        if not self.analyzer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        try:
            health = self.analyzer.get_architecture_health_metrics()
            
            results = "ARCHITECTURE HEALTH METRICS\n"
            results += "=" * 50 + "\n\n"
            
            for metric, value in health.items():
                results += f"{metric.replace('_', ' ').title()}: {value:.3f}\n"
            
            # Add interpretation
            results += "\nINTERPRETATION:\n"
            results += "• Density: Lower is better for layered architectures\n"
            results += "• Modularity: Higher indicates better separation\n" 
            results += "• Clustering: Higher indicates more local connectivity\n"
            
            self.show_results(results)
        except Exception as e:
            messagebox.showerror("Error", f"Health metrics failed: {str(e)}")
    
    def show_results(self, text):
        """Display results in the results text area"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(1.0, text)
    
    # =========================================================================
    # EXPORT METHODS
    # =========================================================================
    
    def export_graphml(self):
        """Export model to GraphML"""
        if not self.model.get_node_count():
            messagebox.showwarning("Warning", "No model to export!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export GraphML",
            defaultextension=".graphml",
            filetypes=[("GraphML files", "*.graphml")]
        )
        
        if file_path:
            success = self.model.export_to_graphml(Path(file_path))
            if success:
                messagebox.showinfo("Success", f"GraphML exported to:\n{file_path}")
            else:
                messagebox.showerror("Error", "Failed to export GraphML!")
    
    def export_interactive(self):
        """Export interactive HTML visualization"""
        if not self.visualizer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Interactive HTML",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html")]
        )
        
        if file_path:
            try:
                impact_for_export = self.get_filtered_impact_scores() if self.impact_scores else None
                self.visualizer.export_interactive_html(impact_for_export or {}, file_path)
                messagebox.showinfo("Success", f"Interactive HTML exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {str(e)}")

def main():
    """Main application entry point"""
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    style.theme_use('clam')
    
    # Create and run dashboard
    app = EnhancedDigitalTwinDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
