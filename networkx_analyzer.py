"""
NETWORKX ANALYZER - Advanced graph analysis for Archimate models
"""
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Set, Tuple
import numpy as np
from collections import defaultdict, deque

class ArchimateAnalyzer:
    def __init__(self, graph_model):
        self.graph = graph_model.graph
        self.model = graph_model
    
    def analyze_centrality(self) -> Dict[str, Dict]:
        """Compute multiple centrality measures"""
        try:
            measures = {
                'betweenness': nx.betweenness_centrality(self.graph, weight='weight'),
                'pagerank': nx.pagerank(self.graph, weight='weight'),
                'degree': nx.degree_centrality(self.graph),
                'closeness': nx.closeness_centrality(self.graph)
            }
            return measures
        except Exception as e:
            print(f"⚠️ Centrality analysis failed: {e}")
            return {}
    
    def find_critical_paths(self, source: str, target: str) -> List[List[str]]:
        """Find all simple paths between two nodes, ranked by importance"""
        try:
            paths = list(nx.all_simple_paths(self.graph, source, target, cutoff=5))
            # Rank paths by cumulative weight
            ranked_paths = []
            for path in paths:
                path_weight = sum(
                    self.graph[path[i]][path[i+1]].get('weight', 0.5)
                    for i in range(len(path)-1)
                )
                ranked_paths.append((path, path_weight / len(path)))
            
            ranked_paths.sort(key=lambda x: x[1], reverse=True)
            return [path for path, score in ranked_paths[:10]]  # Top 10 paths
        except Exception as e:
            print(f"⚠️ Path finding failed: {e}")
            return []
    
    def detect_communities(self) -> Dict[int, List[str]]:
        """Detect communities in the architecture using Louvain method"""
        try:
            # Convert to undirected graph for community detection
            undirected_graph = self.graph.to_undirected()
            communities = nx.community.louvain_communities(undirected_graph, weight='weight')
            
            community_dict = {}
            for i, community in enumerate(communities):
                community_dict[i] = list(community)
            
            return community_dict
        except Exception as e:
            print(f"⚠️ Community detection failed: {e}")
            return {}
    
    def find_bottlenecks(self) -> List[Tuple[str, str]]:
        """Find critical edges that are bottlenecks"""
        try:
            edge_betweenness = nx.edge_betweenness_centrality(self.graph, weight='weight')
            critical_edges = sorted(edge_betweenness.items(), key=lambda x: x[1], reverse=True)
            return [(u, v) for (u, v), score in critical_edges[:20]]  # Top 20 bottlenecks
        except Exception as e:
            print(f"⚠️ Bottleneck detection failed: {e}")
            return []
    
    def analyze_layer_connectivity(self) -> Dict[str, Dict]:
        """Analyze connectivity between architecture layers"""
        layer_connectivity = defaultdict(lambda: defaultdict(int))
        
        for u, v, data in self.graph.edges(data=True):
            u_layer = self.graph.nodes[u].get('layer', 'Unknown')
            v_layer = self.graph.nodes[v].get('layer', 'Unknown')
            layer_connectivity[u_layer][v_layer] += 1
        
        return dict(layer_connectivity)
    
    def simulate_change_impact(self, changed_nodes: List[str], impact_strength: float = 0.8) -> Dict[str, float]:
        """Simulate the impact of changes to specific nodes"""
        impact_scores = {}
        
        for start_node in changed_nodes:
            if start_node not in self.graph:
                continue
            
            # Use BFS to propagate impact
            visited = set()
            queue = deque([(start_node, impact_strength)])
            
            while queue:
                current_node, current_impact = queue.popleft()
                
                if current_node in visited:
                    continue
                
                visited.add(current_node)
                
                # Update impact score (maximum impact from any source)
                if current_node in impact_scores:
                    impact_scores[current_node] = max(impact_scores[current_node], current_impact)
                else:
                    impact_scores[current_node] = current_impact
                
                # Propagate to neighbors
                for neighbor in self.graph.successors(current_node):
                    if neighbor not in visited:
                        edge_data = self.graph[current_node][neighbor]
                        weight = edge_data.get('weight', 0.5)
                        new_impact = current_impact * weight * 0.7  # Decay
                        
                        if new_impact > 0.05:  # Only track significant impacts
                            queue.append((neighbor, new_impact))
        
        return impact_scores
    
    def get_architecture_health_metrics(self) -> Dict[str, float]:
        """Compute overall architecture health metrics"""
        metrics = {}
        
        try:
            # Density (lower is better for layered architecture)
            metrics['density'] = nx.density(self.graph)
            
            # Average shortest path length
            if nx.is_weakly_connected(self.graph):
                metrics['avg_path_length'] = nx.average_shortest_path_length(self.graph)
            else:
                metrics['avg_path_length'] = float('inf')
            
            # Clustering coefficient
            metrics['clustering'] = nx.average_clustering(self.graph.to_undirected())
            
            # Modularity (measure of community structure)
            communities = self.detect_communities()
            if communities:
                undirected = self.graph.to_undirected()
                partition = {}
                for comm_id, nodes in communities.items():
                    for node in nodes:
                        partition[node] = comm_id
                metrics['modularity'] = nx.algorithms.community.modularity(undirected, [set(nodes) for nodes in communities.values()])
            else:
                metrics['modularity'] = 0.0
            
        except Exception as e:
            print(f"⚠️ Health metrics computation failed: {e}")
        
        return metrics
