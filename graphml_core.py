"""
GRAPHML-CORE ENGINE - Archimate Digital Twin
Uses GraphML as the fundamental data model for powerful graph analysis
"""
import xml.etree.ElementTree as ET
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import time

class GraphMLArchimateModel:
    def __init__(self, name: str = "Unnamed Model"):
        self.name = name
        self.graph = nx.DiGraph()  # Directed graph for Archimate relationships
        self.source_file: Optional[Path] = None
        
    def load_archimate_xml(self, file_path: Path) -> bool:
        """Load Archimate XML and convert directly to NetworkX graph"""
        try:
            if not file_path.exists():
                return False
            
            print(f"📖 Loading Archimate model from: {file_path}")
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            self.graph.clear()
            self.name = root.get('name', 'Unnamed Model')
            self.source_file = file_path
            
            # Parse elements and add as nodes
            elements = self._parse_elements(root)
            for element_id, element_data in elements.items():
                self.graph.add_node(element_id, **element_data)
            
            # Parse relationships and add as edges
            relationships = self._parse_relationships(root, elements)
            for rel_id, rel_data in relationships.items():
                if rel_data['source'] in elements and rel_data['target'] in elements:
                    self.graph.add_edge(
                        rel_data['source'], 
                        rel_data['target'], 
                        **rel_data['attributes']
                    )
            
            # Calculate graph metrics
            self._compute_graph_metrics()
            
            print(f"✅ Successfully loaded {len(elements)} elements and {len(relationships)} relationships as graph")
            return True
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_elements(self, root: ET.Element) -> Dict[str, Dict]:
        """Parse Archimate elements into graph nodes with rich attributes"""
        elements = {}
        
        for folder in root.findall('.//folder'):
            for element in folder.findall('.//element'):
                element_id = element.get('id')
                element_name = element.get('name', 'Unnamed')
                
                if not element_id:
                    continue
                
                # Extract element type
                element_type = element.get('{http://www.w3.org/2001/XMLSchema-instance}type', '')
                if not element_type:
                    element_type = element.get('type', '')
                
                if ':' in element_type:
                    clean_type = element_type.split(':', 1)[1]
                else:
                    clean_type = element_type
                
                if 'Relationship' in clean_type:
                    continue  # Skip relationship elements (handled separately)
                
                layer = self._determine_layer(clean_type)
                
                # Get default metrics
                try:
                    from modeller_config import DEFAULT_METRICS
                    metrics = DEFAULT_METRICS.get(clean_type, {}).copy()
                except ImportError:
                    metrics = {}
                
                # Create node with rich attributes
                elements[element_id] = {
                    'name': element_name,
                    'type': clean_type,
                    'layer': layer,
                    'metrics': metrics,
                    'documentation': self._extract_documentation(element),
                    'properties': self._extract_properties(element),
                    'ai_category': self._determine_ai_category(clean_type, layer),
                    'importance_score': 0.0,  # Will be computed later
                    'centrality': 0.0,  # Will be computed later
                }
        
        return elements
    
    def _parse_relationships(self, root: ET.Element, elements: Dict) -> Dict[str, Dict]:
        """Parse relationships into graph edges with semantic attributes"""
        relationships = {}
        
        # Parse relationship elements
        for folder in root.findall('.//folder'):
            for element in folder.findall('.//element'):
                element_id = element.get('id')
                element_type = element.get('{http://www.w3.org/2001/XMLSchema-instance}type', '')
                
                if not element_type or 'Relationship' not in element_type:
                    continue
                
                if ':' in element_type:
                    clean_type = element_type.split(':', 1)[1]
                else:
                    clean_type = element_type
                
                source_id = element.get('source')
                target_id = element.get('target')
                
                if all([element_id, source_id, target_id]):
                    relationships[element_id] = {
                        'source': source_id,
                        'target': target_id,
                        'attributes': {
                            'relationship_type': clean_type,
                            'relationship_id': element_id,
                            'name': element.get('name', ''),
                            'documentation': self._extract_documentation(element),
                            'semantic_type': self._determine_semantic_type(clean_type),
                            'weight': self._calculate_relationship_weight(clean_type),
                            'ai_importance': self._calculate_ai_importance(clean_type)
                        }
                    }
        
        # Also parse direct relationship elements
        for rel in root.findall('.//relationship'):
            rel_id = rel.get('id')
            source_id = rel.get('source')
            target_id = rel.get('target')
            rel_type = rel.get('{http://www.w3.org/2001/XMLSchema-instance}type', '')
            
            if all([rel_id, source_id, target_id, rel_type]):
                if ':' in rel_type:
                    clean_type = rel_type.split(':', 1)[1]
                else:
                    clean_type = rel_type
                
                relationships[rel_id] = {
                    'source': source_id,
                    'target': target_id,
                    'attributes': {
                        'relationship_type': clean_type,
                        'relationship_id': rel_id,
                        'name': rel.get('name', ''),
                        'documentation': self._extract_documentation(rel),
                        'semantic_type': self._determine_semantic_type(clean_type),
                        'weight': self._calculate_relationship_weight(clean_type),
                        'ai_importance': self._calculate_ai_importance(clean_type)
                    }
                }
        
        return relationships
    
    def _determine_layer(self, element_type: str) -> str:
        """Determine architecture layer for element type"""
        element_type_lower = element_type.lower()
        
        layer_mapping = {
            'Motivation': ["stakeholder", "driver", "goal", "requirement", "assessment", "value"],
            'Strategy': ["capability", "resource", "course", "outcome"],
            'Business': ["business", "process", "service", "function", "event", "contract", "product", "actor", "role"],
            'Application': ["application", "component", "function", "service", "interface", "data"],
            'Technology': ["technology", "device", "system", "software", "network", "node"],
            'Implementation': ["workpackage", "deliverable", "plateau", "gap", "implementation"]
        }
        
        for layer, keywords in layer_mapping.items():
            if any(keyword in element_type_lower for keyword in keywords):
                return layer
        
        return "Other"
    
    def _determine_ai_category(self, element_type: str, layer: str) -> str:
        """Categorize elements for AI understanding"""
        category_mapping = {
            'motivation': ['stakeholder', 'driver', 'goal', 'requirement'],
            'capability': ['capability', 'resource', 'course'],
            'process': ['process', 'function', 'service'],
            'data': ['data', 'object', 'information'],
            'technology': ['technology', 'device', 'system', 'software'],
            'organization': ['actor', 'role', 'interface'],
            'project': ['workpackage', 'deliverable', 'plateau']
        }
        
        element_type_lower = element_type.lower()
        for category, keywords in category_mapping.items():
            if any(keyword in element_type_lower for keyword in keywords):
                return category
        
        return 'other'
    
    def _determine_semantic_type(self, relationship_type: str) -> str:
        """Determine semantic relationship type for AI understanding"""
        semantic_mapping = {
            'composition': 'structural',
            'aggregation': 'structural',
            'realization': 'functional',
            'influence': 'behavioral',
            'triggering': 'temporal',
            'flow': 'data_flow',
            'access': 'permission',
            'serving': 'functional',
            'assignment': 'organizational',
            'association': 'general'
        }
        
        rel_type_lower = relationship_type.lower()
        for rel_key, semantic_type in semantic_mapping.items():
            if rel_key in rel_type_lower:
                return semantic_type
        
        return 'general'
    
    def _calculate_relationship_weight(self, relationship_type: str) -> float:
        """Calculate relationship weight for AI analysis"""
        weight_mapping = {
            'composition': 1.0,
            'aggregation': 0.9,
            'realization': 0.8,
            'influence': 0.7,
            'triggering': 0.6,
            'flow': 0.5,
            'access': 0.4,
            'association': 0.3
        }
        
        rel_type_lower = relationship_type.lower()
        for rel_key, weight in weight_mapping.items():
            if rel_key in rel_type_lower:
                return weight
        
        return 0.5
    
    def _calculate_ai_importance(self, relationship_type: str) -> float:
        """Calculate AI importance for relationship filtering"""
        importance_mapping = {
            'realization': 0.9,
            'composition': 0.8,
            'influence': 0.7,
            'triggering': 0.6,
            'flow': 0.5,
            'access': 0.4
        }
        
        rel_type_lower = relationship_type.lower()
        for rel_key, importance in importance_mapping.items():
            if rel_key in rel_type_lower:
                return importance
        
        return 0.3
    
    def _extract_documentation(self, element: ET.Element) -> str:
        """Extract documentation from element"""
        documentation = ""
        doc_elem = element.find('documentation')
        if doc_elem is not None and doc_elem.text:
            documentation = doc_elem.text.strip()
        return documentation
    
    def _extract_properties(self, element: ET.Element) -> Dict[str, str]:
        """Extract properties from element"""
        properties = {}
        props_elem = element.find('properties')
        if props_elem is not None:
            for prop in props_elem.findall('property'):
                key = prop.get('key', '')
                value = prop.get('value', '')
                if key and value:
                    properties[key] = value
        return properties
        
    def _compute_graph_metrics(self):
        """Compute graph metrics for all nodes"""
        if not self.graph.nodes():
            return
        
        # Method 1: Try advanced centrality calculations
        try:
            betweenness = nx.betweenness_centrality(self.graph, weight='weight')
            pagerank = nx.pagerank(self.graph, weight='weight')
            
            for node_id in self.graph.nodes():
                centrality_score = betweenness.get(node_id, 0.0)
                pagerank_score = pagerank.get(node_id, 0.0)
                
                self.graph.nodes[node_id]['centrality'] = centrality_score
                self.graph.nodes[node_id]['pagerank'] = pagerank_score
                
                # Calculate importance using advanced metrics
                layer_weight = self._get_layer_weight(self.graph.nodes[node_id]['layer'])
                documentation_score = min(1.0, len(self.graph.nodes[node_id].get('documentation', '')) / 100.0)
                
                importance_score = (
                    centrality_score * 0.5 +
                    layer_weight * 0.3 +
                    documentation_score * 0.2
                )
                self.graph.nodes[node_id]['importance_score'] = importance_score
                
        except Exception as e:
            print(f"⚠️ Could not compute advanced graph metrics: {e}")
            # Method 2: Fallback to simple degree-based calculation
            self._compute_fallback_metrics()

    def _compute_fallback_metrics(self):
        """Compute fallback metrics when advanced calculations fail"""
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            
            # Simple degree-based centrality
            in_degree = self.graph.in_degree(node_id)
            out_degree = self.graph.out_degree(node_id)
            total_degree = in_degree + out_degree
            degree_centrality = total_degree / max(1, (self.graph.number_of_nodes() - 1))
            
            self.graph.nodes[node_id]['centrality'] = degree_centrality
            self.graph.nodes[node_id]['pagerank'] = degree_centrality
            
            # Calculate importance using fallback method
            layer_weight = self._get_layer_weight(node_data.get('layer', 'Other'))
            documentation_score = min(1.0, len(node_data.get('documentation', '')) / 100.0)
            
            importance_score = (
                degree_centrality * 0.4 +
                layer_weight * 0.4 +
                documentation_score * 0.2
            )
            self.graph.nodes[node_id]['importance_score'] = importance_score
    def _get_layer_weight(self, layer: str) -> float:
        """Get weight for layer importance"""
        layer_weights = {
            'Motivation': 0.9,
            'Strategy': 0.8,
            'Business': 0.7,
            'Application': 0.6,
            'Technology': 0.5,
            'Implementation': 0.4,
            'Other': 0.3
        }
        return layer_weights.get(layer, 0.5)
    
    def export_to_graphml(self, file_path: Path) -> bool:
        """Export the graph to GraphML format"""
        try:
            nx.write_graphml(self.graph, file_path)
            print(f"✅ GraphML exported to: {file_path}")
            return True
        except Exception as e:
            print(f"❌ Error exporting GraphML: {e}")
            return False
    
    def get_node_count(self) -> int:
        return len(self.graph.nodes())
    
    def get_edge_count(self) -> int:
        return len(self.graph.edges())
    
    def get_nodes_by_layer(self) -> Dict[str, List[str]]:
        """Get nodes grouped by layer"""
        layers = defaultdict(list)
        for node_id, data in self.graph.nodes(data=True):
            layers[data.get('layer', 'Other')].append(node_id)
        return dict(layers)
    
    def get_impact_analysis(self, start_node: str, max_depth: int = 3) -> Dict[str, float]:
        """Perform impact analysis using graph algorithms"""
        impact_scores = {}
        
        if start_node not in self.graph:
            return impact_scores
        
        # Use BFS with relationship weights
        visited = set()
        queue = deque([(start_node, 0, 1.0)])  # (node, depth, current_impact)
        
        while queue:
            current_node, depth, current_impact = queue.popleft()
            
            if current_node in visited or depth > max_depth:
                continue
            
            visited.add(current_node)
            impact_scores[current_node] = current_impact
            
            # Explore neighbors with impact decay
            for neighbor in self.graph.successors(current_node):
                if neighbor not in visited:
                    edge_data = self.graph[current_node][neighbor]
                    weight = edge_data.get('weight', 0.5)
                    new_impact = current_impact * weight * 0.8  # Decay factor
                    
                    if new_impact > 0.01:  # Only track significant impacts
                        queue.append((neighbor, depth + 1, new_impact))
        
        return impact_scores
