"""
VISUALIZATION ENGINE - Powerful graph visualizations using NetworkX and Matplotlib
"""
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from typing import Dict, List, Any, Optional
import numpy as np
from collections import defaultdict

class GraphVisualizer:
    def __init__(self, graph_model):
        self.graph = graph_model.graph
        self.model = graph_model
        self.colors = {
            'Motivation': '#e74c3c',
            'Strategy': '#9b59b6', 
            'Business': '#3498db',
            'Application': '#2ecc71',
            'Technology': '#f39c12',
            'Implementation': '#1abc9c',
            'Other': '#95a5a6'
        }
    
    def create_layered_layout(self, impact_scores: Dict[str, float] = None):
        """Create a layered layout based on architecture layers"""
        pos = {}
        layer_nodes = defaultdict(list)
        
        # Group nodes by layer
        for node in self.graph.nodes():
            layer = self.graph.nodes[node].get('layer', 'Other')
            layer_nodes[layer].append(node)
        
        # Position nodes in layers
        layers_order = ['Motivation', 'Strategy', 'Business', 'Application', 'Technology', 'Implementation', 'Other']
        layer_height = 1.0 / len(layers_order)
        
        for i, layer in enumerate(layers_order):
            if layer in layer_nodes:
                nodes = layer_nodes[layer]
                y_pos = 1.0 - (i * layer_height) - layer_height/2
                
                # Sort nodes by importance for better layout
                if impact_scores:
                    nodes.sort(key=lambda x: impact_scores.get(x, 0), reverse=True)
                
                for j, node in enumerate(nodes):
                    x_pos = (j + 1) / (len(nodes) + 1)
                    pos[node] = (x_pos, y_pos)
        
        return pos
    
    def plot_impact_analysis(self, impact_scores: Dict[str, float], title: str = "Impact Analysis"):
        """Create a visualization of impact analysis results - FIXED for dashboard"""
        # Use current figure instead of creating new one
        fig = plt.gcf()
        fig.clf()
        ax1 = fig.add_subplot(121)  # Left subplot
        ax2 = fig.add_subplot(122)  # Right subplot
        
        # Plot 1: Network visualization
        pos = self.create_layered_layout(impact_scores)
        
        # Draw nodes with size based on impact
        node_sizes = [impact_scores.get(node, 0) * 2000 + 100 for node in self.graph.nodes()]
        node_colors = [self.colors.get(self.graph.nodes[node].get('layer', 'Other'), '#95a5a6') 
                      for node in self.graph.nodes()]
        
        nx.draw_networkx_nodes(self.graph, pos, node_size=node_sizes, 
                              node_color=node_colors, alpha=0.8, ax=ax1)
        
        # Draw edges with transparency based on weight
        edge_weights = [self.graph[u][v].get('weight', 0.5) * 2 for u, v in self.graph.edges()]
        nx.draw_networkx_edges(self.graph, pos, alpha=0.3, width=edge_weights, ax=ax1)
        
        # Draw labels for important nodes only
        important_nodes = [node for node, score in impact_scores.items() if score > 0.1]
        labels = {node: self.graph.nodes[node].get('name', node)[:15] 
                 for node in important_nodes}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=8, ax=ax1)
        
        ax1.set_title(f"{title}\nNetwork View")
        ax1.axis('off')
        
        # Plot 2: Impact distribution by layer
        layer_impacts = defaultdict(list)
        for node, score in impact_scores.items():
            if score > 0:
                layer = self.graph.nodes[node].get('layer', 'Other')
                layer_impacts[layer].append(score)
        
        layers = []
        avg_impacts = []
        for layer, impacts in layer_impacts.items():
            layers.append(layer)
            avg_impacts.append(np.mean(impacts) if impacts else 0)
        
        colors = [self.colors.get(layer, '#95a5a6') for layer in layers]
        bars = ax2.bar(layers, avg_impacts, color=colors, alpha=0.8)
        ax2.set_title('Average Impact by Layer')
        ax2.set_ylabel('Impact Score')
        ax2.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        return fig
    
    def plot_centrality_analysis(self, centrality_scores: Dict[str, Dict]):
        """Visualize different centrality measures - FIXED for dashboard"""
        fig = plt.gcf()
        fig.clf()
        
        measures = list(centrality_scores.keys())[:4]
        rows = 2
        cols = 2
        
        for i, measure in enumerate(measures):
            ax = fig.add_subplot(rows, cols, i+1)
            
            if measure in centrality_scores:
                scores = centrality_scores[measure]
                
                # Get top 20 nodes by centrality
                top_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
                nodes, values = zip(*top_nodes)
                
                # Get node names and layers for coloring
                node_names = [self.graph.nodes[node].get('name', node)[:20] for node in nodes]
                node_layers = [self.graph.nodes[node].get('layer', 'Other') for node in nodes]
                colors = [self.colors.get(layer, '#95a5a6') for layer in node_layers]
                
                bars = ax.barh(node_names, values, color=colors, alpha=0.8)
                ax.set_title(f'Top 20 Nodes by {measure.title()} Centrality')
                ax.set_xlabel('Centrality Score')
                
                # Add value labels
                for bar in bars:
                    width = bar.get_width()
                    ax.text(width, bar.get_y() + bar.get_height()/2.,
                            f'{width:.3f}', ha='left', va='center', fontsize=8)
        
        plt.tight_layout()
        return fig
    
    def plot_community_structure(self, communities: Dict[int, List[str]]):
        """Visualize detected communities in the architecture - FIXED for dashboard"""
        fig = plt.gcf()
        fig.clf()
        ax = fig.add_subplot(111)
        
        # Create a colormap for communities
        cmap = cm.get_cmap('tab20', len(communities))
        
        # Create spring layout
        pos = nx.spring_layout(self.graph, weight='weight', k=1, iterations=50)
        
        # Draw nodes colored by community
        for comm_id, nodes in communities.items():
            nx.draw_networkx_nodes(self.graph, pos, nodelist=nodes,
                                 node_color=[cmap(comm_id)], node_size=100,
                                 alpha=0.8, ax=ax)
        
        # Draw edges
        nx.draw_networkx_edges(self.graph, pos, alpha=0.2, ax=ax)
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=cmap(i), label=f'Community {i+1} ({len(nodes)} nodes)')
                          for i, nodes in communities.items()]
        ax.legend(handles=legend_elements, loc='upper right')
        
        ax.set_title('Architecture Community Structure')
        ax.axis('off')
        
        plt.tight_layout()
        return fig
    
    def plot_force_directed_layout(self, impact_scores: Dict[str, float] = None, title: str = "Force-Directed Layout"):
        """Create a force-directed layout visualization - FIXED for dashboard"""
        fig = plt.gcf()
        fig.clf()
        ax = fig.add_subplot(111)
        
        # Use spring layout for force-directed effect
        pos = nx.spring_layout(self.graph, weight='weight', k=1, iterations=50)
        
        # Node sizes based on impact or importance
        if impact_scores:
            node_sizes = [impact_scores.get(node, 0) * 3000 + 100 for node in self.graph.nodes()]
        else:
            node_sizes = [self.graph.nodes[node].get('importance_score', 0.5) * 2000 + 100 
                         for node in self.graph.nodes()]
        
        # Node colors by layer
        node_colors = [self.colors.get(self.graph.nodes[node].get('layer', 'Other'), '#95a5a6') 
                      for node in self.graph.nodes()]
        
        # Draw the graph
        nx.draw_networkx_nodes(self.graph, pos, node_size=node_sizes, 
                              node_color=node_colors, alpha=0.8, ax=ax)
        
        # Draw edges with weights
        edge_weights = [self.graph[u][v].get('weight', 0.5) * 2 for u, v in self.graph.edges()]
        nx.draw_networkx_edges(self.graph, pos, alpha=0.3, width=edge_weights, ax=ax)
        
        # Draw labels for important nodes only
        if impact_scores:
            important_nodes = [node for node, score in impact_scores.items() if score > 0.1]
        else:
            important_nodes = [node for node in self.graph.nodes() 
                              if self.graph.nodes[node].get('importance_score', 0) > 0.7]
        
        labels = {node: self.graph.nodes[node].get('name', node)[:15] 
                 for node in important_nodes}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=8, ax=ax)
        
        ax.set_title(title)
        ax.axis('off')
        
        # Add legend for layers
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=color, label=layer) 
                          for layer, color in self.colors.items()]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        return fig
    
    def plot_layered_layout(self, impact_scores: Dict[str, float] = None, title: str = "Layered Architecture Layout"):
        """Create a traditional layered architecture visualization - FIXED for dashboard"""
        fig = plt.gcf()
        fig.clf()
        ax = fig.add_subplot(111)
        
        # Use the existing layered layout method
        pos = self.create_layered_layout(impact_scores)
        
        # Node sizes based on impact or importance
        if impact_scores:
            node_sizes = [impact_scores.get(node, 0) * 3000 + 100 for node in self.graph.nodes()]
        else:
            node_sizes = [self.graph.nodes[node].get('importance_score', 0.5) * 2000 + 100 
                         for node in self.graph.nodes()]
        
        # Node colors by layer
        node_colors = [self.colors.get(self.graph.nodes[node].get('layer', 'Other'), '#95a5a6') 
                      for node in self.graph.nodes()]
        
        # Draw the graph
        nx.draw_networkx_nodes(self.graph, pos, node_size=node_sizes, 
                              node_color=node_colors, alpha=0.8, ax=ax)
        
        # Draw edges
        edge_weights = [self.graph[u][v].get('weight', 0.5) * 2 for u, v in self.graph.edges()]
        nx.draw_networkx_edges(self.graph, pos, alpha=0.3, width=edge_weights, ax=ax)
        
        # Draw labels for all nodes in layered layout (more space)
        labels = {node: self.graph.nodes[node].get('name', node)[:20] 
                 for node in self.graph.nodes()}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=7, ax=ax)
        
        ax.set_title(title)
        ax.axis('off')
        
        plt.tight_layout()
        return fig
    
    def plot_impact_heatmap(self, impact_scores: Dict[str, float], title: str = "Impact Heatmap"):
        """Create a heatmap visualization of impacts across layers and node types - FIXED for dashboard"""
        fig = plt.gcf()
        fig.clf()
        ax1 = fig.add_subplot(121)  # Left subplot
        ax2 = fig.add_subplot(122)  # Right subplot
        
        # Plot 1: Impact distribution by layer
        layer_impacts = defaultdict(list)
        for node, score in impact_scores.items():
            if score > 0:
                layer = self.graph.nodes[node].get('layer', 'Other')
                layer_impacts[layer].append(score)
        
        layers = list(layer_impacts.keys())
        avg_impacts = [np.mean(impacts) if impacts else 0 for impacts in layer_impacts.values()]
        
        # Create bar chart
        colors = [self.colors.get(layer, '#95a5a6') for layer in layers]
        bars = ax1.bar(layers, avg_impacts, color=colors, alpha=0.8)
        ax1.set_title('Average Impact by Layer')
        ax1.set_ylabel('Impact Score')
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}', ha='center', va='bottom')
        
        # Plot 2: Impact distribution by node type
        type_impacts = defaultdict(list)
        for node, score in impact_scores.items():
            if score > 0:
                node_type = self.graph.nodes[node].get('type', 'Unknown')
                type_impacts[node_type].append(score)
        
        # Get top 10 node types by average impact
        top_types = sorted(type_impacts.items(), 
                          key=lambda x: np.mean(x[1]) if x[1] else 0, 
                          reverse=True)[:10]
        
        types, type_scores = zip(*top_types)
        avg_type_impacts = [np.mean(scores) if scores else 0 for scores in type_scores]
        
        # Create horizontal bar chart
        y_pos = np.arange(len(types))
        ax2.barh(y_pos, avg_type_impacts, alpha=0.8, color='skyblue')
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(types, fontsize=9)
        ax2.set_xlabel('Average Impact Score')
        ax2.set_title('Top 10 Node Types by Impact')
        
        # Add value labels
        for i, v in enumerate(avg_type_impacts):
            ax2.text(v, i, f' {v:.3f}', va='center', fontsize=8)
        
        plt.suptitle(title, fontsize=16)
        plt.tight_layout()
        return fig
    
    def export_interactive_html(self, impact_scores: Dict[str, float], output_path: str):
        """Export an interactive HTML visualization using pyvis"""
        try:
            from pyvis.network import Network
            
            # Create pyvis network
            net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="black")
            
            # Add nodes
            for node in self.graph.nodes():
                node_data = self.graph.nodes[node]
                layer = node_data.get('layer', 'Other')
                impact = impact_scores.get(node, 0)
                
                net.add_node(
                    node,
                    label=node_data.get('name', node),
                    title=f"{node_data.get('name', 'Unknown')}\n"
                          f"Type: {node_data.get('type', 'Unknown')}\n"
                          f"Layer: {layer}\n"
                          f"Impact: {impact:.3f}\n"
                          f"Centrality: {node_data.get('centrality', 0):.3f}",
                    color=self.colors.get(layer, '#95a5a6'),
                    size=impact * 30 + 10,
                    borderWidth=2
                )
            
            # Add edges
            for u, v, data in self.graph.edges(data=True):
                net.add_edge(
                    u, v,
                    title=f"Type: {data.get('relationship_type', 'Unknown')}\n"
                          f"Weight: {data.get('weight', 0.5):.2f}",
                    width=data.get('weight', 0.5) * 3,
                    color='rgba(100,100,100,0.5)'
                )
            
            # Configure physics for better layout
            net.set_options("""
            var options = {
              "physics": {
                "enabled": true,
                "stabilization": {"iterations": 100},
                "barnesHut": {
                  "gravitationalConstant": -8000,
                  "springLength": 95,
                  "springConstant": 0.04,
                  "damping": 0.09
                }
              }
            }
            """)
            
            net.save_graph(output_path)
            print(f"✅ Interactive HTML exported to: {output_path}")
            
        except ImportError:
            print("⚠️ Pyvis not installed. Install with: pip install pyvis")
