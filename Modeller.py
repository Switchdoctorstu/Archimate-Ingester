"""
DIGITAL TWIN SIMULATOR - ENTERPRISE EXECUTIVE DASHBOARD
Enhanced for large models with advanced filtering and visualization
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import time
import json
import logging
import math
import sys
import re
from collections import defaultdict, deque

# =============================================================================
# CONFIGURATION IMPORT
# =============================================================================

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from modeller_config import *
    print("✅ Configuration loaded successfully from modeller_config.py")
except ImportError as e:
    print(f"❌ Failed to import configuration: {e}")
    sys.exit(1)

# =============================================================================
# ENHANCED MODEL CLASSES
# =============================================================================

@dataclass
class ArchimateElement:
    id: str
    name: str
    type: str
    layer: str
    metrics: Dict[str, float] = field(default_factory=dict)
    relationships: Dict[str, List[Dict[str, Any]]] = field(default_factory=lambda: {"in": [], "out": []})
    tags: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        if self.type in DEFAULT_METRICS:
            self.metrics = DEFAULT_METRICS[self.type].copy()
        # Auto-generate tags for better filtering
        self.tags.add(self.layer.lower())
        self.tags.add(self.type.lower())
        self.tags.add("all")

class Relationship:
    def __init__(self, id: str, type: str, source_id: str, target_id: str, name: str = ""):
        self.id = id
        self.type = type
        self.source_id = source_id
        self.target_id = target_id
        self.name = name

class EnhancedArchimateModel:
    def __init__(self, name: str = "Unnamed Model"):
        self.name = name
        self.elements: Dict[str, ArchimateElement] = {}
        self.relationships: List[Relationship] = []
        self.source_file: Optional[Path] = None
        self.element_index: Dict[str, Set[str]] = defaultdict(set)  # tag -> element_ids
        self.search_index: Dict[str, Set[str]] = defaultdict(set)  # keyword -> element_ids
    
    def load(self, file_path: Path) -> bool:
        """Load and index Archimate model"""
        try:
            if not file_path.exists():
                return False
            
            print(f"📖 Loading model from: {file_path}")
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            self.elements.clear()
            self.relationships.clear()
            self.element_index.clear()
            self.search_index.clear()
            
            self.name = root.get('name', 'Unnamed Model')
            self.source_file = file_path
            
            # Parse all elements
            for folder in root.findall('.//folder'):
                folder_name = folder.get('name', 'Unknown')
                for element in folder.findall('.//element'):
                    self._parse_element(element, folder_name)
            
            self._build_relationship_references()
            self._build_indices()
            
            print(f"✅ Successfully loaded {len(self.elements)} elements and {len(self.relationships)} relationships")
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
    
    def _parse_element(self, element: ET.Element, folder_name: str):
        element_id = element.get('id')
        element_name = element.get('name', 'Unnamed')
        
        if not element_id:
            return
        
        element_type = element.get('{http://www.w3.org/2001/XMLSchema-instance}type', '')
        if not element_type:
            element_type = element.get('type', '')
        
        if ':' in element_type:
            clean_type = element_type.split(':', 1)[1]
        else:
            clean_type = element_type
        
        if 'Relationship' in clean_type:
            self._parse_relationship_element(element, clean_type)
            return
        
        layer = self._determine_layer(clean_type)
        self.elements[element_id] = ArchimateElement(
            id=element_id,
            name=element_name,
            type=clean_type,
            layer=layer
        )
    
    def _parse_relationship_element(self, element: ET.Element, rel_type: str):
        rel_id = element.get('id')
        source_id = element.get('source')
        target_id = element.get('target')
        
        if all([rel_id, source_id, target_id]):
            self.relationships.append(Relationship(
                id=rel_id, type=rel_type, source_id=source_id, target_id=target_id
            ))
    
    def _determine_layer(self, element_type: str) -> str:
        element_type_lower = element_type.lower()
        if any(x in element_type_lower for x in ["stakeholder", "driver", "goal", "requirement"]):
            return "Motivation"
        elif any(x in element_type_lower for x in ["capability", "resource"]):
            return "Strategy"
        elif any(x in element_type_lower for x in ["business"]):
            return "Business"
        elif any(x in element_type_lower for x in ["application", "data"]):
            return "Application"
        elif any(x in element_type_lower for x in ["technology", "device", "system"]):
            return "Technology"
        elif any(x in element_type_lower for x in ["workpackage", "deliverable", "plateau"]):
            return "Implementation"
        else:
            return "Other"
    
    def _build_relationship_references(self):
        for rel in self.relationships:
            if rel.source_id in self.elements:
                self.elements[rel.source_id].relationships["out"].append({
                    "id": rel.id, "type": rel.type, "target": rel.target_id
                })
            if rel.target_id in self.elements:
                self.elements[rel.target_id].relationships["in"].append({
                    "id": rel.id, "type": rel.type, "source": rel.source_id
                })
    
    def _build_indices(self):
        """Build search and filter indices for fast lookup"""
        for element_id, element in self.elements.items():
            # Index by tags
            for tag in element.tags:
                self.element_index[tag].add(element_id)
            
            # Index by keywords for search
            keywords = set(re.findall(r'\w+', element.name.lower()))
            for keyword in keywords:
                if len(keyword) > 2:  # Only index meaningful words
                    self.search_index[keyword].add(element_id)
    
    def search_elements(self, query: str) -> List[str]:
        """Search elements by name (returns element IDs)"""
        if not query or len(query) < 2:
            return []
        
        query_words = set(re.findall(r'\w+', query.lower()))
        results = set()
        
        for word in query_words:
            if word in self.search_index:
                results.update(self.search_index[word])
        
        return list(results)
    
    def filter_elements(self, tags: List[str]) -> List[str]:
        """Filter elements by tags (returns element IDs)"""
        if not tags or "all" in tags:
            return list(self.elements.keys())
        
        results = set(self.elements.keys())
        for tag in tags:
            if tag in self.element_index:
                results = results.intersection(self.element_index[tag])
        
        return list(results)
    
    def get_element_centrality(self, element_id: str) -> float:
        """Calculate centrality score for an element (importance metric)"""
        if element_id not in self.elements:
            return 0.0
        
        element = self.elements[element_id]
        total_connections = len(element.relationships["in"]) + len(element.relationships["out"])
        max_possible = len(self.elements) - 1
        
        return total_connections / max_possible if max_possible > 0 else 0.0

# =============================================================================
# ENTERPRISE EXECUTIVE DASHBOARD
# =============================================================================

class EnterpriseExecutiveDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Twin Simulator - Enterprise Executive Dashboard")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#2c3e50')
        
        # Initialize enhanced model
        self.model = EnhancedArchimateModel()
        self.impact_scores = {}
        self.focused_element = None
        self.current_filter_tags = ["all"]
        
        # Enhanced color scheme
        self.colors = {
            'primary': '#3498db',
            'secondary': '#2c3e50',
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
            'implementation': '#1abc9c'
        }
        
        self.default_models_dir = MODELS_DIR
        #self.default_models_dir.mkdir(parents=True, exist_ok=True)
        
        self.setup_gui()
        
    def setup_gui(self):
        """Setup enhanced enterprise dashboard"""
        # Main container with notebook for tabs
        main_container = ttk.Notebook(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.overview_tab = ttk.Frame(main_container)
        self.analysis_tab = ttk.Frame(main_container)
        self.advanced_tab = ttk.Frame(main_container)
        
        main_container.add(self.overview_tab, text="📊 Overview")
        main_container.add(self.analysis_tab, text="🔍 Impact Analysis")
        main_container.add(self.advanced_tab, text="⚙️ Advanced Tools")
        
        self.setup_overview_tab()
        self.setup_analysis_tab()
        self.setup_advanced_tab()
        
    def setup_overview_tab(self):
        """Setup overview tab with model statistics and quick actions"""
        # Header
        header_frame = tk.Frame(self.overview_tab, bg=self.colors['secondary'], height=60)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="ENTERPRISE ARCHITECTURE OVERVIEW", 
                font=('Arial', 20, 'bold'), fg='white', bg=self.colors['secondary']).pack(pady=15)
        
        # Quick actions frame
        actions_frame = tk.Frame(self.overview_tab, bg=self.colors['card_bg'], relief=tk.RAISED, bd=2)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Load model section
        load_frame = tk.Frame(actions_frame, bg=self.colors['card_bg'])
        load_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(load_frame, text="Model Management:", 
                font=('Arial', 14, 'bold'), bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        self.model_var = tk.StringVar(value="No model loaded")
        model_status = tk.Label(load_frame, textvariable=self.model_var, 
                               font=('Arial', 11), bg=self.colors['card_bg'], fg=self.colors['text_light'])
        model_status.pack(anchor=tk.W, pady=5)
        
        load_btn_frame = tk.Frame(load_frame, bg=self.colors['card_bg'])
        load_btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(load_btn_frame, text="📁 Load Model", command=self.load_model_dialog,
                 bg=self.colors['primary'], fg='white', font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Button(load_btn_frame, text="⚡ Quick Load", command=self.quick_load_model,
                 bg=self.colors['success'], fg='white', font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        # Statistics dashboard
        stats_frame = tk.Frame(self.overview_tab, bg=self.colors['background'])
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left - Key metrics
        metrics_frame = tk.Frame(stats_frame, bg=self.colors['card_bg'], relief=tk.RAISED, bd=1)
        metrics_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(metrics_frame, text="KEY METRICS", font=('Arial', 16, 'bold'),
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
        
    def setup_analysis_tab(self):
        """Setup enhanced analysis tab with advanced filtering"""
        main_frame = tk.Frame(self.analysis_tab, bg=self.colors['background'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left panel - Controls and browser
        left_panel = tk.Frame(main_frame, bg=self.colors['card_bg'], relief=tk.RAISED, bd=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Right panel - Visualization
        right_panel = tk.Frame(main_frame, bg=self.colors['card_bg'], relief=tk.RAISED, bd=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self.setup_analysis_controls(left_panel)
        self.setup_advanced_visualization(right_panel)
        
    def setup_analysis_controls(self, parent):
        """Setup analysis controls with advanced filtering"""
        # Search and filter section
        filter_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        filter_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(filter_frame, text="Search & Filter:", font=('Arial', 14, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        # Search box
        search_frame = tk.Frame(filter_frame, bg=self.colors['card_bg'])
        search_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(search_frame, text="Search:", font=('Arial', 11),
                bg=self.colors['card_bg']).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=('Arial', 11), width=30)
        search_entry.pack(side=tk.LEFT, padx=10)
        search_entry.bind('<KeyRelease>', self.on_search)
        
        # Filter tags
        tag_frame = tk.Frame(filter_frame, bg=self.colors['card_bg'])
        tag_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(tag_frame, text="Filter by:", font=('Arial', 11),
                bg=self.colors['card_bg']).pack(side=tk.LEFT)
        
        self.filter_vars = {}
        filter_tags = ["all", "motivation", "strategy", "business", "application", "technology", "implementation"]
        
        for i, tag in enumerate(filter_tags):
            var = tk.BooleanVar(value=(tag == "all"))
            cb = tk.Checkbutton(tag_frame, text=tag.title(), variable=var,
                               command=self.on_filter_change, bg=self.colors['card_bg'])
            cb.pack(side=tk.LEFT, padx=10)
            self.filter_vars[tag] = var
        
        # Element browser with enhanced features
        browser_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        browser_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Browser with sort options
        browser_header = tk.Frame(browser_frame, bg=self.colors['card_bg'])
        browser_header.pack(fill=tk.X)
        
        tk.Label(browser_header, text="Element Browser:", font=('Arial', 12, 'bold'),
                bg=self.colors['card_bg']).pack(side=tk.LEFT)
        
        self.sort_var = tk.StringVar(value="name")
        sort_menu = ttk.Combobox(browser_header, textvariable=self.sort_var,
                                values=["name", "type", "layer", "centrality"],
                                state="readonly", width=12)
        sort_menu.pack(side=tk.RIGHT, padx=5)
        sort_menu.bind('<<ComboboxSelected>>', self.on_sort_change)
        
        tk.Label(browser_header, text="Sort by:", font=('Arial', 10),
                bg=self.colors['card_bg']).pack(side=tk.RIGHT)
        
        # Enhanced treeview
        tree_frame = tk.Frame(browser_frame, bg=self.colors['card_bg'])
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ('name', 'type', 'layer', 'centrality', 'metrics')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=20)
        
        self.tree.heading('name', text='Element Name')
        self.tree.heading('type', text='Type')
        self.tree.heading('layer', text='Layer')
        self.tree.heading('centrality', text='Centrality')
        self.tree.heading('metrics', text='Key Metrics')
        
        self.tree.column('name', width=200)
        self.tree.column('type', width=120)
        self.tree.column('layer', width=100)
        self.tree.column('centrality', width=80)
        self.tree.column('metrics', width=150)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self.on_element_select)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # Action buttons
        action_frame = tk.Frame(browser_frame, bg=self.colors['card_bg'])
        action_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(action_frame, text="🎯 Set Focus", command=self.set_focus_from_selection,
                 bg=self.colors['accent'], fg='white', font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="🔍 Impact Analysis", command=self.run_impact_analysis,
                 bg=self.colors['primary'], fg='white', font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="🗑️ Clear Focus", command=self.clear_focus,
                 bg=self.colors['warning'], fg='white', font=('Arial', 11)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="💾 Export", command=self.export_results,
                 bg=self.colors['success'], fg='white', font=('Arial', 11)).pack(side=tk.RIGHT, padx=5)
    
    def setup_advanced_visualization(self, parent):
        """Setup advanced visualization panel"""
        # Visualization controls
        viz_control_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        viz_control_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(viz_control_frame, text="Visualization:", font=('Arial', 14, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        # Visualization type selector
        viz_type_frame = tk.Frame(viz_control_frame, bg=self.colors['card_bg'])
        viz_type_frame.pack(fill=tk.X, pady=10)
        
        self.viz_type = tk.StringVar(value="radial")
        tk.Radiobutton(viz_type_frame, text="Radial View", variable=self.viz_type,
                      value="radial", command=self.update_visualization,
                      bg=self.colors['card_bg']).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(viz_type_frame, text="Layered View", variable=self.viz_type,
                      value="layered", command=self.update_visualization,
                      bg=self.colors['card_bg']).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(viz_type_frame, text="Network View", variable=self.viz_type,
                      value="network", command=self.update_visualization,
                      bg=self.colors['card_bg']).pack(side=tk.LEFT, padx=10)
        
        # Visualization canvas
        viz_frame = tk.Frame(parent, bg=self.colors['card_bg'])
        viz_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.viz_canvas = tk.Canvas(viz_frame, bg=self.colors['card_bg'], highlightthickness=0)
        self.viz_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Impact details
        details_frame = tk.Frame(parent, bg=self.colors['card_bg'], height=200)
        details_frame.pack(fill=tk.X, padx=20, pady=10)
        details_frame.pack_propagate(False)
        
        tk.Label(details_frame, text="Impact Details:", font=('Arial', 12, 'bold'),
                bg=self.colors['card_bg']).pack(anchor=tk.W)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, height=8,
                                                     font=('Arial', 10),
                                                     bg='#f8f9fa', fg=self.colors['text_dark'])
        self.details_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.details_text.config(state=tk.DISABLED)
    
    def clear_focus(self):
        """Clear current focus element"""
        self.focused_element = None
        self.impact_scores.clear()
        self.update_visualization()
        self.update_details_text("Focus cleared. Select an element and run impact analysis.")
    
    def on_search(self, event=None):
        """Handle search functionality"""
        query = self.search_var.get()
        if len(query) >= 2:
            results = self.model.search_elements(query)
            self.update_tree_with_elements(results)
        elif not query:
            self.update_tree_display()
    
    def on_filter_change(self):
        """Handle filter changes"""
        selected_tags = [tag for tag, var in self.filter_vars.items() if var.get()]
        if not selected_tags:
            # If nothing selected, select "all"
            self.filter_vars["all"].set(True)
            selected_tags = ["all"]
        
        self.current_filter_tags = selected_tags
        filtered_elements = self.model.filter_elements(selected_tags)
        self.update_tree_with_elements(filtered_elements)
    
    def on_sort_change(self, event=None):
        """Handle sort changes"""
        self.update_tree_display()
    
    def on_tree_select(self, event):
        """Handle tree selection (single click)"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            element_id = self.tree.item(item, 'tags')[0]
            self.preview_element(element_id)
    
    def on_element_select(self, event):
        """Handle element double-click selection"""
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
    
    def preview_element(self, element_id):
        """Preview element details without setting focus"""
        if element_id in self.model.elements:
            element = self.model.elements[element_id]
            details = f"🔍 Preview: {element.name}\n"
            details += f"Type: {element.type} | Layer: {element.layer}\n"
            details += f"Centrality: {self.model.get_element_centrality(element_id):.3f}\n"
            details += f"Relationships: {len(element.relationships['in'])} in, {len(element.relationships['out'])} out\n\n"
            details += "Metrics:\n"
            for metric, value in element.metrics.items():
                details += f"  • {metric}: {value}\n"
            
            self.update_details_text(details)
    
    def update_tree_with_elements(self, element_ids):
        """Update tree with specific element IDs"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        elements = [(elem_id, self.model.elements[elem_id]) for elem_id in element_ids]
        
        # Sort elements
        sort_key = self.sort_var.get()
        if sort_key == "name":
            elements.sort(key=lambda x: x[1].name.lower())
        elif sort_key == "type":
            elements.sort(key=lambda x: x[1].type)
        elif sort_key == "layer":
            elements.sort(key=lambda x: x[1].layer)
        elif sort_key == "centrality":
            elements.sort(key=lambda x: self.model.get_element_centrality(x[0]), reverse=True)
        
        for elem_id, element in elements:
            centrality = self.model.get_element_centrality(elem_id)
            primary_metric = self.get_primary_metric_display(element)
            
            self.tree.insert('', tk.END, values=(
                element.name,
                element.type,
                element.layer,
                f"{centrality:.3f}",
                primary_metric
            ), tags=(elem_id,))
    
    def update_tree_display(self):
        """Update tree display with current filters"""
        filtered_elements = self.model.filter_elements(self.current_filter_tags)
        self.update_tree_with_elements(filtered_elements)
    
    def get_primary_metric_display(self, element):
        """Get formatted primary metric for display"""
        if element.metrics:
            metric_key = list(element.metrics.keys())[0]
            metric_value = element.metrics[metric_key]
            if isinstance(metric_value, float):
                return f"{metric_key}: {metric_value:.2f}"
            return f"{metric_key}: {metric_value}"
        return "N/A"
    
    def update_visualization(self):
        """Update visualization based on selected type with proper cleanup"""
        # Stop any running network animation
        if hasattr(self, 'animation_running'):
            self.animation_running = False
        
        if not self.impact_scores:
            self.show_visualization_placeholder()
            return
        
        viz_type = self.viz_type.get()
        if viz_type == "radial":
            self.visualize_radial_impact()
        elif viz_type == "layered":
            self.visualize_layered_impact()
        elif viz_type == "network":
            # Small delay to ensure canvas is ready
            self.root.after(100, self.visualize_network_impact)
    
    def visualize_radial_impact(self):
        """Radial impact visualization with better text rendering"""
        self.viz_canvas.delete("all")
        
        width = self.viz_canvas.winfo_width()
        height = self.viz_canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        center_x, center_y = width/2, height/2
        radius = min(width, height) * 0.35  # Reduced radius for better text spacing
        
        # Draw focus element
        if self.focused_element and self.focused_element in self.model.elements:
            focus_elem = self.model.elements[self.focused_element]
            
            # Focus element circle
            self.viz_canvas.create_oval(center_x-25, center_y-25, center_x+25, center_y+25,
                                      fill=self.colors['accent'], outline='white', width=3)
            self.viz_canvas.create_text(center_x, center_y, text="★", 
                                      fill='white', font=('Arial', 10, 'bold'))
            
            # Focus element name
            focus_name = focus_elem.name[:15] + "..." if len(focus_elem.name) > 15 else focus_elem.name
            self.viz_canvas.create_text(center_x, center_y - 40, 
                                      text=focus_name,
                                      font=('Arial', 9, 'bold'), fill=self.colors['text_dark'])
        
        # Draw impacted elements
        impacted = [(elem_id, score) for elem_id, score in self.impact_scores.items() 
                   if score > 0.01 and elem_id != self.focused_element and elem_id in self.model.elements]
        
        if not impacted:
            # Show message if no impacted elements
            self.viz_canvas.create_text(center_x, center_y, 
                                      text="No significant impacts detected\nTry different element or threshold",
                                      font=('Arial', 11), fill=self.colors['text_light'],
                                      justify=tk.CENTER)
            return
        
        for i, (elem_id, score) in enumerate(impacted):
            angle = 2 * math.pi * i / len(impacted)
            elem_x = center_x + radius * math.cos(angle)
            elem_y = center_y + radius * math.sin(angle)
            
            # Size based on impact score
            size = max(15, 15 + (score * 25))
            elem = self.model.elements[elem_id]
            color = self.get_layer_color(elem.layer)
            
            # Draw element circle
            self.viz_canvas.create_oval(elem_x-size/2, elem_y-size/2, 
                                      elem_x+size/2, elem_y+size/2,
                                      fill=color, outline='white', width=2)
            
            # Draw connection line
            if self.focused_element:
                self.viz_canvas.create_line(center_x, center_y, elem_x, elem_y,
                                          fill=self.colors['text_light'], width=1, dash=(2, 2))
            
            # Position label further out to avoid overlap
            label_radius = radius * 1.3
            label_x = center_x + label_radius * math.cos(angle)
            label_y = center_y + label_radius * math.sin(angle)
            
            # Element name with background for readability
            display_name = elem.name[:12] + "..." if len(elem.name) > 12 else elem.name
            
            # Create text background
            text_bg = self.viz_canvas.create_rectangle(
                label_x - 45, label_y - 25,
                label_x + 45, label_y + 25,
                fill='white', outline=self.colors['text_light'], width=1
            )
            self.viz_canvas.tag_lower(text_bg)
            
            # Element name
            self.viz_canvas.create_text(label_x, label_y - 8, 
                                      text=display_name,
                                      font=('Arial', 8), fill=self.colors['text_dark'],
                                      width=80, justify=tk.CENTER)
            
            # Add impact score below name
            self.viz_canvas.create_text(label_x, label_y + 8,
                                      text=f"Impact: {score:.2f}",
                                      font=('Arial', 7), fill=self.colors['accent'])
        
        # Add title
        self.viz_canvas.create_text(width/2, 20, 
                                  text="RADIAL IMPACT VIEW",
                                  font=('Arial', 12, 'bold'), fill=self.colors['text_dark'])
        
        # Draw legend
        self.draw_legend(width, height)
    
    def draw_legend(self, width, height):
        """Draw color legend for layers"""
        layers = ["Motivation", "Strategy", "Business", "Application", "Technology", "Implementation"]
        legend_x = width - 120
        legend_y = height - 150
        
        # Legend background
        self.viz_canvas.create_rectangle(legend_x - 10, legend_y - 10, 
                                      width - 10, legend_y + len(layers) * 20 + 10,
                                      fill='white', outline=self.colors['text_light'], width=1)
        
        # Legend title
        self.viz_canvas.create_text(legend_x + 50, legend_y, text="LAYERS", 
                                  font=('Arial', 9, 'bold'), fill=self.colors['text_dark'])
        
        # Layer items
        for i, layer in enumerate(layers):
            y = legend_y + 20 + (i * 20)
            color = self.get_layer_color(layer)
            
            # Color box
            self.viz_canvas.create_rectangle(legend_x, y, legend_x + 12, y + 12,
                                          fill=color, outline=self.colors['text_light'])
            
            # Layer name
            self.viz_canvas.create_text(legend_x + 20, y + 6, text=layer,
                                      font=('Arial', 8), fill=self.colors['text_dark'],
                                      anchor=tk.W)
    
    def visualize_layered_impact(self):
        """Layered architecture visualization with column headers"""
        self.viz_canvas.delete("all")
        
        width = self.viz_canvas.winfo_width()
        height = self.viz_canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        layers = ["Motivation", "Strategy", "Business", "Application", "Technology", "Implementation"]
        layer_height = height / len(layers)
        
        # Add column headers
        header_y = 30
        self.viz_canvas.create_text(75, header_y, text="LAYERS", 
                                  font=('Arial', 11, 'bold'), fill=self.colors['text_dark'])
        self.viz_canvas.create_text(width/2, header_y, text="IMPACTED ELEMENTS", 
                                  font=('Arial', 11, 'bold'), fill=self.colors['text_dark'])
        
        for i, layer in enumerate(layers):
            y = i * layer_height + layer_height/2 + 40  # Offset for headers
            
            # Layer label with colored background
            layer_color = self.get_layer_color(layer)
            self.viz_canvas.create_rectangle(10, y - 20, 140, y + 20,
                                          fill=layer_color, outline='white', width=2)
            self.viz_canvas.create_text(75, y, text=layer, font=('Arial', 10, 'bold'),
                                      fill='white')
            
            # Draw elements in this layer
            layer_elements = [elem_id for elem_id in self.impact_scores 
                            if self.impact_scores[elem_id] > 0.01 and 
                            elem_id in self.model.elements and
                            self.model.elements[elem_id].layer == layer]
            
            # Sort by impact score for consistent layout
            layer_elements.sort(key=lambda x: self.impact_scores[x], reverse=True)
            
            max_elements_per_row = 6  # Limit elements per layer for readability
            elements_to_show = layer_elements[:max_elements_per_row]
            
            for j, elem_id in enumerate(elements_to_show):
                # Calculate position with spacing
                x_spacing = (width - 160) / (max_elements_per_row + 1)
                x = 160 + (j + 1) * x_spacing
                
                score = self.impact_scores[elem_id]
                size = 25 + (score * 35)  # Larger size for visibility
                elem = self.model.elements[elem_id]
                
                # Element circle with outline
                self.viz_canvas.create_oval(x-size/2, y-size/2, x+size/2, y+size/2,
                                          fill=layer_color, outline='white', width=2)
                
                # Element type abbreviation inside circle
                type_abbr = self.get_type_abbreviation(elem.type)
                self.viz_canvas.create_text(x, y, text=type_abbr,
                                          font=('Arial', 7, 'bold'), fill='white')
                
                # Element name below circle
                display_name = elem.name[:12] + "..." if len(elem.name) > 12 else elem.name
                self.viz_canvas.create_text(x, y + size/2 + 15, 
                                          text=display_name,
                                          font=('Arial', 8), fill=self.colors['text_dark'],
                                          width=100, justify=tk.CENTER)
                
                # Impact score below name
                self.viz_canvas.create_text(x, y + size/2 + 30,
                                          text=f"Impact: {score:.2f}",
                                          font=('Arial', 7, 'bold'), fill=self.colors['accent'])
        
        # Add overall title
        self.viz_canvas.create_text(width/2, 15, 
                                  text="ARCHITECTURE LAYER IMPACT ANALYSIS",
                                  font=('Arial', 12, 'bold'), fill=self.colors['text_dark'])
    
    def get_type_abbreviation(self, element_type):
        """Get abbreviation for element type for better display"""
        abbreviations = {
            'Stakeholder': 'SH',
            'Driver': 'DR',
            'Goal': 'GL',
            'Requirement': 'RQ',
            'BusinessProcess': 'BP',
            'BusinessService': 'BS',
            'ApplicationService': 'AS',
            'TechnologyService': 'TS',
            'BusinessActor': 'BA',
            'BusinessRole': 'BR',
            'Capability': 'CP',
            'Resource': 'RS',
            'ApplicationComponent': 'AC',
            'DataObject': 'DO',
            'Device': 'DV',
            'SystemSoftware': 'SS',
            'WorkPackage': 'WP',
            'Deliverable': 'DL',
            'Plateau': 'PL'
        }
        return abbreviations.get(element_type, element_type[:3].upper())
    
    def visualize_network_impact(self):
        """Initialize network visualization with proper animation control"""
        # Stop any existing animation
        if hasattr(self, 'animation_running'):
            self.animation_running = False
        
        self.viz_canvas.delete("all")
        
        width = self.viz_canvas.winfo_width()
        height = self.viz_canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        if not self.impact_scores or not self.focused_element:
            self.show_network_placeholder(width, height)
            return
        
        # Initialize network data structures
        self.network_nodes = {}
        self.network_edges = []
        
        # Create nodes from impacted elements
        impacted_elements = [(elem_id, score) for elem_id, score in self.impact_scores.items() 
                            if score > 0.01 and elem_id in self.model.elements]
        
        if len(impacted_elements) < 2:
            self.viz_canvas.create_text(width/2, height/2, 
                                      text="Need at least 2 elements for network view",
                                      font=('Arial', 12), fill=self.colors['text_light'])
            return
        
        # Position nodes in a circle initially
        center_x, center_y = width/2, height/2
        radius = min(width, height) * 0.35
        
        for i, (elem_id, score) in enumerate(impacted_elements):
            angle = 2 * math.pi * i / len(impacted_elements)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            elem = self.model.elements[elem_id]
            self.network_nodes[elem_id] = {
                'x': x, 'y': y, 
                'vx': 0.0, 'vy': 0.0,  # Initialize velocity
                'element': elem,
                'score': score,
                'is_focus': (elem_id == self.focused_element)
            }
        
        # Create edges from relationships
        for elem_id in self.network_nodes:
            elem = self.model.elements[elem_id]
            # Outgoing relationships
            for rel in elem.relationships["out"]:
                if rel["target"] in self.network_nodes:
                    self.network_edges.append({
                        'source': elem_id,
                        'target': rel["target"],
                        'type': rel["type"]
                    })
            # Incoming relationships (for bidirectional visualization)
            for rel in elem.relationships["in"]:
                if rel["source"] in self.network_nodes:
                    self.network_edges.append({
                        'source': rel["source"],
                        'target': elem_id,
                        'type': rel["type"]
                    })
        
        # Start animation
        self.animation_running = True
        self.animate_network()
    
    def show_network_placeholder(self, width, height):
        """Show network visualization placeholder"""
        self.viz_canvas.create_text(width/2, height/2, 
                                  text="Network Visualization\n\nSelect a focus element and run impact analysis\nto see animated network relationships",
                                  font=('Arial', 12), fill=self.colors['text_light'],
                                  justify=tk.CENTER)
    
    def animate_network(self):
        """Animate the network using force-directed algorithm"""
        if not hasattr(self, 'animation_running') or not self.animation_running:
            return
        
        self.viz_canvas.delete("all")
        width = self.viz_canvas.winfo_width()
        height = self.viz_canvas.winfo_height()
        
        # Force-directed layout parameters
        repulsion_strength = 1000
        attraction_strength = 0.1
        damping = 0.8
        max_velocity = 10
        center_attraction = 0.001
        
        # Calculate repulsive forces (all nodes repel each other)
        node_ids = list(self.network_nodes.keys())
        for i, node1_id in enumerate(node_ids):
            node1 = self.network_nodes[node1_id]
            
            for node2_id in node_ids[i+1:]:
                node2 = self.network_nodes[node2_id]
                
                # Calculate distance
                dx = node1['x'] - node2['x']
                dy = node1['y'] - node2['y']
                distance = max(math.sqrt(dx*dx + dy*dy), 0.1)
                
                # Repulsive force (inverse square)
                force = repulsion_strength / (distance * distance)
                
                # Apply force
                node1['vx'] += (dx / distance) * force
                node1['vy'] += (dy / distance) * force
                node2['vx'] -= (dx / distance) * force
                node2['vy'] -= (dy / distance) * force
        
        # Calculate attractive forces (along edges)
        for edge in self.network_edges:
            source = self.network_nodes[edge['source']]
            target = self.network_nodes[edge['target']]
            
            dx = source['x'] - target['x']
            dy = source['y'] - target['y']
            distance = max(math.sqrt(dx*dx + dy*dy), 0.1)
            
            # Attractive force (proportional to distance)
            force = attraction_strength * distance
            
            # Apply force
            source['vx'] -= (dx / distance) * force
            source['vy'] -= (dy / distance) * force
            target['vx'] += (dx / distance) * force
            target['vy'] += (dy / distance) * force
        
        # Apply center attraction and update positions
        for node_id, node in self.network_nodes.items():
            # Attract to center
            dx_center = width/2 - node['x']
            dy_center = height/2 - node['y']
            node['vx'] += dx_center * center_attraction
            node['vy'] += dy_center * center_attraction
            
            # Apply damping and limit velocity
            node['vx'] *= damping
            node['vy'] *= damping
            node['vx'] = max(min(node['vx'], max_velocity), -max_velocity)
            node['vy'] = max(min(node['vy'], max_velocity), -max_velocity)
            
            # Update position
            node['x'] += node['vx']
            node['y'] += node['vy']
            
            # Keep within bounds with soft constraints
            margin = 50
            if node['x'] < margin:
                node['vx'] += (margin - node['x']) * 0.1
            if node['x'] > width - margin:
                node['vx'] += (width - margin - node['x']) * 0.1
            if node['y'] < margin:
                node['vy'] += (margin - node['y']) * 0.1
            if node['y'] > height - margin:
                node['vy'] += (height - margin - node['y']) * 0.1
        
        # Draw the network
        self.draw_network()
        
        # Continue animation
        if self.animation_running:
            self.root.after(30, self.animate_network)  # ~33 FPS
    
    def draw_network(self):
        """Draw the current state of the network"""
        width = self.viz_canvas.winfo_width()
        height = self.viz_canvas.winfo_height()
        
        # Draw edges first (so they appear behind nodes)
        for edge in self.network_edges:
            source = self.network_nodes[edge['source']]
            target = self.network_nodes[edge['target']]
            
            # Determine edge color and style based on relationship type
            edge_color = self.colors['text_light']
            dash_pattern = None
            
            if 'influence' in edge['type'].lower():
                edge_color = self.colors['primary']
                dash_pattern = (4, 2)
            elif 'realization' in edge['type'].lower():
                edge_color = self.colors['success']
            elif 'serving' in edge['type'].lower():
                edge_color = self.colors['warning']
            elif 'triggering' in edge['type'].lower():
                edge_color = self.colors['accent']
                dash_pattern = (2, 2)
            
            # Draw edge line
            self.viz_canvas.create_line(
                source['x'], source['y'], target['x'], target['y'],
                fill=edge_color, width=1.5, dash=dash_pattern, arrow=tk.LAST
            )
        
        # Draw nodes
        for node_id, node in self.network_nodes.items():
            elem = node['element']
            score = node['score']
            
            # Node size based on impact score
            base_size = 25
            size = base_size + (score * 30)
            
            # Node color based on layer
            color = self.get_layer_color(elem.layer)
            
            # Special styling for focus node
            if node['is_focus']:
                # Pulsing effect for focus node
                pulse = (math.sin(time.time() * 5) + 1) * 3  # Pulsing border
                self.viz_canvas.create_oval(
                    node['x'] - size/2 - pulse, node['y'] - size/2 - pulse,
                    node['x'] + size/2 + pulse, node['y'] + size/2 + pulse,
                    fill=color, outline=self.colors['accent'], width=3
                )
                # Focus indicator
                self.viz_canvas.create_text(node['x'], node['y'], text="★", 
                                        fill='white', font=('Arial', 10, 'bold'))
            else:
                # Regular node
                self.viz_canvas.create_oval(
                    node['x'] - size/2, node['y'] - size/2,
                    node['x'] + size/2, node['y'] + size/2,
                    fill=color, outline='white', width=2
                )
            
            # Node label (type abbreviation)
            type_abbr = self.get_type_abbreviation(elem.type)
            self.viz_canvas.create_text(node['x'], node['y'], text=type_abbr,
                                    fill='white', font=('Arial', 8, 'bold'))
            
            # Node name (hover-like label)
            if size > 30:  # Only show names on larger nodes
                display_name = elem.name[:10] + "..." if len(elem.name) > 10 else elem.name
                self.viz_canvas.create_text(node['x'], node['y'] + size/2 + 12,
                                        text=display_name,
                                        font=('Arial', 7), fill=self.colors['text_dark'])
            
            # Impact score
            self.viz_canvas.create_text(node['x'], node['y'] - size/2 - 8,
                                    text=f"{score:.2f}",
                                    font=('Arial', 7, 'bold'), fill=self.colors['accent'])
        
        # Draw legend
        self.draw_network_legend(width, height)
        
        # Draw title with animation indicator
        self.viz_canvas.create_text(width/2, 20, 
                                text="ANIMATED NETWORK GRAPH • FORCE-DIRECTED LAYOUT",
                                font=('Arial', 11, 'bold'), fill=self.colors['text_dark'])
    
    def draw_network_legend(self, width, height):
        """Draw network-specific legend"""
        legend_x = width - 150
        legend_y = 40
        
        # Legend background
        self.viz_canvas.create_rectangle(legend_x - 10, legend_y - 10, 
                                    width - 10, legend_y + 160,
                                    fill='white', outline=self.colors['text_light'], width=1)
        
        # Legend title
        self.viz_canvas.create_text(legend_x + 60, legend_y, text="NETWORK LEGEND", 
                                font=('Arial', 9, 'bold'), fill=self.colors['text_dark'])
        
        # Edge types
        edge_types = [
            ('Realization', self.colors['success'], None),
            ('Influence', self.colors['primary'], (4, 2)),
            ('Serving', self.colors['warning'], None),
            ('Triggering', self.colors['accent'], (2, 2))
        ]
        
        for i, (edge_name, color, dash) in enumerate(edge_types):
            y = legend_y + 25 + (i * 25)
            
            # Edge sample
            self.viz_canvas.create_line(legend_x, y, legend_x + 30, y,
                                    fill=color, width=1.5, dash=dash, arrow=tk.LAST)
            
            # Edge name
            self.viz_canvas.create_text(legend_x + 40, y, text=edge_name,
                                    font=('Arial', 8), fill=self.colors['text_dark'],
                                    anchor=tk.W)
        
        # Node info
        info_y = legend_y + 125
        self.viz_canvas.create_text(legend_x, info_y, text="• Size = Impact", 
                                font=('Arial', 7), fill=self.colors['text_light'], anchor=tk.W)
        self.viz_canvas.create_text(legend_x, info_y + 12, text="• Color = Layer", 
                                font=('Arial', 7), fill=self.colors['text_light'], anchor=tk.W)
        self.viz_canvas.create_text(legend_x, info_y + 24, text="• ★ = Focus Node", 
                                font=('Arial', 7), fill=self.colors['text_light'], anchor=tk.W)
    
    def stop_network_animation(self):
        """Stop the network animation"""
        self.animation_running = False
    
    def get_layer_color(self, layer):
        """Get color for layer"""
        layer_lower = layer.lower()
        return self.colors.get(layer_lower, self.colors['primary'])
    
    def show_visualization_placeholder(self):
        """Show visualization placeholder"""
        self.viz_canvas.delete("all")
        width = self.viz_canvas.winfo_width()
        height = self.viz_canvas.winfo_height()
        
        if width > 1 and height > 1:
            self.viz_canvas.create_text(width/2, height/2, 
                                      text="Run impact analysis to visualize architecture relationships",
                                      font=('Arial', 12), fill=self.colors['text_light'],
                                      justify=tk.CENTER)
    
    def setup_advanced_tab(self):
        """Setup advanced tools tab"""
        # Placeholder for advanced features
        advanced_frame = tk.Frame(self.advanced_tab, bg=self.colors['background'])
        advanced_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(advanced_frame, text="Advanced Analysis Tools", 
                font=('Arial', 24, 'bold'), bg=self.colors['background']).pack(pady=50)
        
        # Coming soon features
        features = [
            "🧠 Neural Network Simulation",
            "📈 Trend Analysis & Forecasting", 
            "🔧 Architecture Optimization",
            "📊 Performance Benchmarking",
            "🔄 Change Impact Simulation",
            "🎯 Risk Assessment Matrix"
        ]
        
        for feature in features:
            feature_frame = tk.Frame(advanced_frame, bg=self.colors['card_bg'], relief=tk.RAISED, bd=1)
            feature_frame.pack(fill=tk.X, pady=5, padx=50)
            
            tk.Label(feature_frame, text=feature, font=('Arial', 12),
                    bg=self.colors['card_bg']).pack(pady=10)
    
    def create_metric_card(self, parent, title, value_var, icon, row):
        """Create enhanced metric card"""
        card = tk.Frame(parent, bg=self.colors['background'], relief=tk.RAISED, bd=2)
        card.grid(row=row//2, column=row%2, padx=10, pady=10, sticky='nsew')
        
        # Icon and title
        header_frame = tk.Frame(card, bg=self.colors['primary'])
        header_frame.pack(fill=tk.X)
        
        tk.Label(header_frame, text=icon, font=('Arial', 16),
                bg=self.colors['primary'], fg='white').pack(side=tk.LEFT, padx=10, pady=5)
        tk.Label(header_frame, text=title, font=('Arial', 12, 'bold'),
                bg=self.colors['primary'], fg='white').pack(side=tk.LEFT, padx=5, pady=5)
        
        # Value
        value_label = tk.Label(card, textvariable=value_var, font=('Arial', 20, 'bold'),
                              bg=self.colors['background'], fg=self.colors['primary'])
        value_label.pack(pady=20)
        
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
    
    def update_model_metrics(self):
        """Update model-wide metrics"""
        if not self.model.elements:
            return
        
        # Calculate average centrality
        centralities = [self.model.get_element_centrality(elem_id) 
                       for elem_id in self.model.elements]
        avg_centrality = sum(centralities) / len(centralities) if centralities else 0
        
        # Determine complexity
        total_relationships = len(self.model.relationships)
        total_elements = len(self.model.elements)
        complexity_ratio = total_relationships / total_elements if total_elements > 0 else 0
        
        if complexity_ratio < 1:
            complexity = "Low"
        elif complexity_ratio < 2:
            complexity = "Medium"
        else:
            complexity = "High"
        
        self.avg_centrality_var.set(f"{avg_centrality:.3f}")
        self.model_complexity_var.set(complexity)
        
        # Update layer distribution visualization
        self.update_layer_distribution()
    
    def update_layer_distribution(self):
        """Update layer distribution chart"""
        self.layer_canvas.delete("all")
        
        if not self.model.elements:
            return
        
        width = self.layer_canvas.winfo_width()
        height = self.layer_canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # Count elements by layer
        layer_counts = defaultdict(int)
        for element in self.model.elements.values():
            layer_counts[element.layer] += 1
        
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
            
            color = self.get_layer_color(layer)
            self.layer_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='white')
            self.layer_canvas.create_text(x1 + bar_width/2, height - 30, text=layer, 
                                        font=('Arial', 8), angle=45, anchor=tk.NE)
            self.layer_canvas.create_text(x1 + bar_width/2, y1 - 10, text=str(count),
                                        font=('Arial', 9, 'bold'), fill=self.colors['text_dark'])
    
    def load_model(self, file_path: Path):
        if self.model.load(file_path):
            self.model_var.set(f"Loaded: {self.model.name} ({len(self.model.elements)} elements)")
            self.update_model_display()
            self.update_model_metrics()
            messagebox.showinfo("Success", f"Model loaded successfully!\n"
                                         f"Elements: {len(self.model.elements)}\n"
                                         f"Relationships: {len(self.model.relationships)}")
        else:
            messagebox.showerror("Error", f"Failed to load model file:\n{file_path}")
    
    def update_model_display(self):
        self.total_elements_var.set(str(len(self.model.elements)))
        self.total_relations_var.set(str(len(self.model.relationships)))
        self.update_tree_display()
    
    def set_focus_element(self, element_id):
        if element_id in self.model.elements:
            self.focused_element = element_id
            element = self.model.elements[element_id]
            self.update_details_text(f"🎯 Focus set to: {element.name}\n"
                                   f"Type: {element.type} | Layer: {element.layer}\n"
                                   f"Centrality: {self.model.get_element_centrality(element_id):.3f}\n\n"
                                   f"Click 'Impact Analysis' to see propagation effects.")
    
    def run_impact_analysis(self):
        if not self.focused_element:
            messagebox.showwarning("Warning", "Please select a focus element first")
            return
        
        self.impact_scores = self.calculate_impact()
        affected = len([score for score in self.impact_scores.values() if score > 0.01])
        
        self.update_visualization()
        self.update_impact_details()
        
        messagebox.showinfo("Analysis Complete", 
                          f"Impact analysis completed!\n"
                          f"Affected elements: {affected}")
    
    def calculate_impact(self) -> Dict[str, float]:
        # Enhanced impact calculation with relationship weights
        if not self.focused_element:
            return {}
        
        scores = {elem_id: 0.0 for elem_id in self.model.elements.keys()}
        scores[self.focused_element] = 1.0
        
        visited = set()
        queue = deque([(self.focused_element, 1.0)])
        
        while queue:
            current_id, strength = queue.popleft()
            if current_id in visited or strength < 0.01:
                continue
                
            visited.add(current_id)
            element = self.model.elements[current_id]
            
            # Enhanced propagation with relationship-specific weights
            for rel in element.relationships["out"] + element.relationships["in"]:
                target_id = rel.get("target") if "target" in rel else rel.get("source")
                if target_id not in self.model.elements:
                    continue
                
                rel_type = rel["type"].lower()
                weight = self.get_relationship_weight(rel_type)
                propagated = strength * weight * 0.7
                
                if propagated > scores[target_id]:
                    scores[target_id] = propagated
                    queue.append((target_id, propagated))
        
        return scores
    
    def get_relationship_weight(self, rel_type: str) -> float:
        """Get weight for relationship type"""
        weights = {
            "influencerelationship": 0.8,
            "realizationrelationship": 0.9,
            "servingrelationship": 0.7,
            "triggeringrelationship": 0.85,
            "assignmentrelationship": 0.75,
            "accessrelationship": 0.6
        }
        
        for key, weight in weights.items():
            if key in rel_type:
                return weight
        
        return 0.5  # Default weight
    
    def update_impact_details(self):
        if not self.impact_scores:
            return
        
        impacted = [(elem_id, score) for elem_id, score in self.impact_scores.items() 
                   if score > 0.01 and elem_id != self.focused_element]
        impacted.sort(key=lambda x: x[1], reverse=True)
        
        details = "TOP IMPACTED ELEMENTS:\n\n"
        for i, (elem_id, score) in enumerate(impacted[:15]):  # Show top 15
            elem = self.model.elements[elem_id]
            centrality = self.model.get_element_centrality(elem_id)
            details += f"{i+1}. {elem.name} ({elem.type})\n"
            details += f"   Layer: {elem.layer} | Impact: {score:.3f} | Centrality: {centrality:.3f}\n"
            details += f"   Metrics: {', '.join([f'{k}: {v:.2f}' for k, v in list(elem.metrics.items())[:2]])}\n\n"
        
        self.update_details_text(details)
    
    def load_model_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Select Archimate Model File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
            initialdir=self.default_models_dir
        )
        if file_path:
            self.load_model(Path(file_path))
    
    def quick_load_model(self):
        xml_files = list(self.default_models_dir.glob("*.xml"))
        if not xml_files:
            messagebox.showwarning("No Models", f"No XML files found in:\n{self.default_models_dir}")
            return
        file_path = xml_files[0]
        self.load_model(file_path)
    
    def export_results(self):
        if not self.model.elements:
            messagebox.showwarning("Warning", "No model loaded to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Analysis Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                export_data = {
                    "export_timestamp": time.time(),
                    "model_name": self.model.name,
                    "focus_element": self.focused_element,
                    "impact_analysis": {
                        "total_affected": len([s for s in self.impact_scores.values() if s > 0.01]),
                        "scores": self.impact_scores
                    },
                    "model_metrics": {
                        "total_elements": len(self.model.elements),
                        "total_relationships": len(self.model.relationships),
                        "average_centrality": float(self.avg_centrality_var.get()),
                        "complexity": self.model_complexity_var.get()
                    },
                    "elements": {}
                }
                
                for elem_id, element in self.model.elements.items():
                    export_data["elements"][elem_id] = {
                        "name": element.name,
                        "type": element.type,
                        "layer": element.layer,
                        "centrality": self.model.get_element_centrality(elem_id),
                        "metrics": element.metrics,
                        "impact_score": self.impact_scores.get(elem_id, 0.0)
                    }
                
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Results exported to:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results:\n{e}")
    
    def update_details_text(self, text):
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, text)
        self.details_text.config(state=tk.DISABLED)

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Launch the enterprise executive dashboard"""
    root = tk.Tk()
    app = EnterpriseExecutiveDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    main()
