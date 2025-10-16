# ArchiMate ingester By Stuart Oldfield
VERSIONTEXT=" Version: 3.x JSON 3d"
# - Load .archimate XML
# - Quick-add elements (type/name/description) -> appends to Paste Area
# - Paste Area (JSON format) including relationships -> staged elements & relationships
# - Insert commits staged JSON into the model, placing elements in the correct folder
# - Relationships are placed in Relations folder and diagram objects + connections are created in an "Auto Diagram"
# - Tree view shows the model; selecting a node shows details
# - Save writes a valid .archimate file with proper namespaces
# - Live XML output panel always shows current model

# TODO:
# - [ ] Improve error handling and user notifications
# - [ ] Optimize XML handling and improve performance for large models
# - [ ] VR ?
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
import csv
import json

from DBDriver import ArchiMateDB, generate_id
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
GEMINI_API_KEY = "YOUR_API_KEY"


# ---- Namespaces ----
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ARCHIMATE = "http://www.archimatetool.com/archimate"
ET.register_namespace("xsi", XSI)
ET.register_namespace("archimate", ARCHIMATE)



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

        # --- DB Integration ---
        self.db_manager = None
        self.db_filepath = None
        self.current_mode = 'file' # 'file' or 'db'

        self.build_gui()
        self.default_bg = self.open_button.cget("background") # Get default button background
        self.update_button_states() # Initial state update

    def insert_from_paste(self):
        if self.model is None:
            messagebox.showwarning("No model", "Open an .archimate file first.")
            return
        
        # Get the entire paste content as a single string
        paste_content = self.paste_text.get("1.0", "end").strip()
        if not paste_content:
            messagebox.showinfo("Nothing to insert", "Paste Area is empty.")
            return
        
        # Parse JSON content
        try:
            json_data = json.loads(paste_content)
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON format:\n{e}")
            return
        
        # Convert the JSON to the expected format
        converted_data = self._convert_json_format(json_data)
        if not converted_data:
            return

        self.save_history()
        created_elements = []
        relationships_to_create = []
        self.create_default_folders()

        # Process elements from JSON
        for element in converted_data.get("elements", []):
            if not self._validate_element(element):
                continue
                
            name = element["name"]
            raw_type = element["type"]
            
            # Corrected duplicate check: An element is only a duplicate if both its name AND type match.
            is_duplicate = False
            potential_matches = self.element_db.get(name.lower(), [])
            for _, existing_type_full in potential_matches:
                if existing_type_full.split(":")[-1] == raw_type.split(":")[-1]:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue # Skip true duplicates (same name, same type)

            etype_full = f"archimate:{raw_type}"
            new_el_id = generate_id()
            folder = self.get_folder_for_type(raw_type)

            if folder is None:
                print(f"Warning: Could not find or create a folder for type '{raw_type}'. Skipping element '{name}'.")
                continue

            attribs = {f"{{{XSI}}}type": etype_full, "name": name, "id": new_el_id}
            new_el = ET.SubElement(folder, "element", attribs)
            doc_text = element.get("description")
            if doc_text:
                doc_el = ET.SubElement(new_el, "documentation")
                doc_el.text = doc_text
            
            # Update the local name->ID cache immediately for subsequent relationship lookups
            name_lower = name.lower()
            if name_lower not in self.element_db:
                self.element_db[name_lower] = []
            self.element_db[name_lower].append((new_el_id, etype_full))
            created_elements.append((name, new_el_id))

        # Process relationships from JSON
        rel_folder = self.get_or_create_relations_folder()
        for relationship in converted_data.get("relationships", []):
            if not self._validate_relationship(relationship):
                continue
                
            rtype = relationship["type"]
            src_name = relationship["source"]
            tgt_name = relationship["target"]
            descr = relationship.get("description")

            # --- Robust Element Lookup Helper ---
            def find_element_info(name, element_type_hint=None):
                potential_matches = self.element_db.get(name.lower(), [])
                if not potential_matches: 
                    print(f"Warning: Could not find any element named '{name}'.")
                    return None
                
                if len(potential_matches) == 1: 
                    return potential_matches[0]
                
                # Ambiguity exists, try to resolve with type hint
                if element_type_hint:
                    hint_full = f"archimate:{element_type_hint}"
                    for match in potential_matches:
                        if match[1] == hint_full:
                            return match
                    print(f"Warning: Found elements named '{name}', but none of type '{element_type_hint}'.")
                    return None
                
                print(f"Warning: Ambiguous element name '{name}' and no type hint provided. Skipping relationship.")
                return None

            src_info = find_element_info(src_name)
            tgt_info = find_element_info(tgt_name)

            if not src_info or not tgt_info:
                continue # Warnings are printed inside the helper
            
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
            relationships_to_create.append(f"{src_name} -> {rtype} -> {tgt_name}")

        if created_elements or relationships_to_create:
            self.dirty = True

        self.build_element_database() # Rebuild after adding all elements
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


    def clean_and_validate_model(self):
        messagebox.showwarning("Clean and validate requested")
        """
        Comprehensive validation and cleaning of the model:
        1. Ensure entities are in correct folders for their type
        2. Check relationships against configuration rules
        3. Fix invalid relationships by trying alternatives or reversing direction
        4. Remove duplicate relationships
        """
        if self.model is None:
            messagebox.showwarning("No model", "Open an .archimate file first.")
            return

        self.save_history()
        
        # Track all actions for reporting
        actions = {
            'relocated_elements': [],
            'fixed_relationships': [],
            'removed_relationships': [],
            'duplicates_removed': []
        }

        # Step 1: Ensure entities are in correct folders
        folder_elements_moved = self._relocate_elements_to_correct_folders()
        actions['relocated_elements'] = folder_elements_moved

        # Step 2 & 3: Validate and fix relationships
        relationship_results = self._validate_and_fix_relationships()
        actions['fixed_relationships'] = relationship_results['fixed']
        actions['removed_relationships'] = relationship_results['removed']

        # Step 4: Remove duplicate relationships
        duplicates_removed = self._remove_duplicate_relationships()
        actions['duplicates_removed'] = duplicates_removed

        # Update UI and databases
        self.build_element_database()
        self.build_relationship_map()
        self.calculate_relationship_counts()
        self.refresh_tree()
        self.update_xml_output_panel()

        # Build and show report
        report_content = self._build_validation_report(actions)
        
        if any(len(items) > 0 for items in actions.values()):
            self.dirty = True
            self.update_button_states()

        self._show_report_window("Validation and Cleaning Report", report_content)
    def is_relationship_allowed(self, source_type, target_type, relationship_type):
        """
        Check if a relationship is allowed between two element types according to ArchiMate spec.
        Uses the RELATIONSHIP_RULES configuration.
        """
        # Remove namespace prefix if present
        if ":" in source_type:
            source_type = source_type.split(":")[-1]
        if ":" in target_type:
            target_type = target_type.split(":")[-1]
        if ":" in relationship_type:
            relationship_type = relationship_type.split(":")[-1]

        # Get rules for source type, fall back to default rules
        source_rules = RELATIONSHIP_RULES.get(source_type, {})
        
        # Check if this relationship type is allowed for the source
        if "allowed_targets" in source_rules:
            if relationship_type in source_rules["allowed_targets"]:
                allowed_targets = source_rules["allowed_targets"][relationship_type]
                if "*" in allowed_targets or target_type in allowed_targets:
                    return True

        # Check default rules
        default_rules = RELATIONSHIP_RULES.get("*", {})
        if "allowed_targets" in default_rules:
            if relationship_type in default_rules["allowed_targets"]:
                allowed_targets = default_rules["allowed_targets"][relationship_type]
                if "*" in allowed_targets or target_type in allowed_targets:
                    return True

        return False

    def _relocate_elements_to_correct_folders(self):
        """Ensure all elements are in the correct folders based on their type."""
        moved_elements = []
        
        if self.model is None:
            return moved_elements

        # Get all folders by name for quick lookup
        folders_by_name = {}
        for folder in self.model.findall("folder"):
            folders_by_name[folder.get("name")] = folder

        # Process all elements
        for folder in self.model.findall("folder"):
            for element in folder.findall("element"):
                element_type_full = element.get(f"{{{XSI}}}type", "")
                if not element_type_full:
                    continue
                    
                # Skip relationships (they go in Relations folder)
                element_type = element_type_full.replace("archimate:", "")
                if element_type.endswith("Relationship") or element_type in RELATIONSHIP_TYPES:
                    correct_folder_name = "Relations"
                else:
                    correct_folder_name = FOLDER_MAP.get(element_type, "Other")

                current_folder_name = folder.get("name", "")
                
                if current_folder_name != correct_folder_name:
                    # Find or create the correct folder
                    if correct_folder_name not in folders_by_name:
                        # Create missing folder
                        folder_type = correct_folder_name.lower().replace(" & ", "_").replace(" ", "_")
                        new_folder = ET.SubElement(self.model, "folder", {
                            "name": correct_folder_name, 
                            "id": generate_id(), 
                            "type": folder_type
                        })
                        folders_by_name[correct_folder_name] = new_folder
                    
                    # Move element to correct folder
                    target_folder = folders_by_name[correct_folder_name]
                    folder.remove(element)
                    target_folder.append(element)
                    
                    element_name = element.get("name", "Unnamed")
                    moved_elements.append(f"'{element_name}' ({element_type}) from '{current_folder_name}' to '{correct_folder_name}'")

        return moved_elements

    def _validate_and_fix_relationships(self):
        """Validate relationships against rules and attempt to fix invalid ones."""
        fixed_relationships = []
        removed_relationships = []
        
        if self.model is None:
            return {'fixed': fixed_relationships, 'removed': removed_relationships}

        # Priority order for relationship types (most meaningful first)
        RELATIONSHIP_PRIORITY = [
            "RealizationRelationship", "AssignmentRelationship", "ServingRelationship",
            "AccessRelationship", "InfluenceRelationship", "AssociationRelationship",
            "UsedByRelationship", "FlowRelationship", "TriggeringRelationship",
            "SpecializationRelationship", "CompositionRelationship", "AggregationRelationship"
        ]

        # Get all relationships
        all_relationships = self.find_all_relationships()
        
        for rel in all_relationships:
            rel_type_full = rel.get(f"{{{XSI}}}type", "")
            rel_type = rel_type_full.replace("archimate:", "")
            source_id = rel.get("source")
            target_id = rel.get("target")

            source_el = self.find_element_by_id(source_id)
            target_el = self.find_element_by_id(target_id)

            if not source_el or not target_el:
                # Remove relationships with missing elements
                self._find_and_remove_element(rel)
                removed_relationships.append(f"Removed '{rel_type}' with missing source/target elements")
                continue

            source_type_full = source_el.get(f"{{{XSI}}}type", "")
            target_type_full = target_el.get(f"{{{XSI}}}type", "")
            source_type = source_type_full.replace("archimate:", "")
            target_type = target_type_full.replace("archimate:", "")

            source_name = source_el.get("name", "Unnamed")
            target_name = target_el.get("name", "Unnamed")

            # Check if relationship is allowed
            if not self.is_relationship_allowed(source_type, target_type, rel_type):
                # Try to fix the relationship
                fix_result = self._attempt_relationship_fix(rel, source_el, target_el, RELATIONSHIP_PRIORITY)
                
                if fix_result:
                    fixed_relationships.append(fix_result)
                else:
                    # Remove unfixable relationships
                    self._find_and_remove_element(rel)
                    removed_relationships.append(f"Removed illegal '{rel_type}' from '{source_name}' to '{target_name}'")

        return {'fixed': fixed_relationships, 'removed': removed_relationships}

    def _attempt_relationship_fix(self, rel, source_el, target_el, priority_list):
        """Attempt to fix an illegal relationship by trying alternatives or reversing direction."""
        source_type = source_el.get(f"{{{XSI}}}type", "").replace("archimate:", "")
        target_type = target_el.get(f"{{{XSI}}}type", "").replace("archimate:", "")
        original_rel_type = rel.get(f"{{{XSI}}}type", "").replace("archimate:", "")
        
        source_name = source_el.get("name", "Unnamed")
        target_name = target_el.get("name", "Unnamed")

        # Strategy 1: Try alternative relationship types (same direction)
        valid_same_dir = self._find_valid_relationships(source_type, target_type)
        if valid_same_dir:
            # Try relationships in priority order
            for rel_type in priority_list:
                if rel_type in valid_same_dir:
                    rel.set(f"{{{XSI}}}type", f"archimate:{rel_type}")
                    return f"Fixed: Changed '{original_rel_type}' to '{rel_type}' for '{source_name}' → '{target_name}'"

        # Strategy 2: Try reverse direction with alternative types
        valid_reverse_dir = self._find_valid_relationships(target_type, source_type)
        if valid_reverse_dir:
            # Try relationships in priority order
            for rel_type in priority_list:
                if rel_type in valid_reverse_dir:
                    # Swap source and target
                    rel.set("source", target_el.get("id"))
                    rel.set("target", source_el.get("id"))
                    rel.set(f"{{{XSI}}}type", f"archimate:{rel_type}")
                    return f"Fixed: Reversed and changed '{original_rel_type}' to '{rel_type}' for '{target_name}' → '{source_name}'"

        return None

    def _find_valid_relationships(self, source_type, target_type):
        """Find all valid relationship types between source and target types."""
        valid_rels = []
        
        # Check specific rules for source type
        source_rules = RELATIONSHIP_RULES.get(source_type, {})
        for rel_type, allowed_targets in source_rules.get("allowed_targets", {}).items():
            if "*" in allowed_targets or target_type in allowed_targets:
                valid_rels.append(rel_type)
        
        # Check default rules
        default_rules = RELATIONSHIP_RULES.get("*", {})
        for rel_type, allowed_targets in default_rules.get("allowed_targets", {}).items():
            if rel_type not in valid_rels and ("*" in allowed_targets or target_type in allowed_targets):
                valid_rels.append(rel_type)
        
        return valid_rels

    def _remove_duplicate_relationships(self):
        """Remove duplicate relationships (same source, target, and type)."""
        duplicates_removed = []
        
        if self.model is None:
            return duplicates_removed

        seen_relationships = set()
        relationships_to_remove = []

        for rel in self.find_all_relationships():
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get(f"{{{XSI}}}type", "")
            
            # Create a unique key for this relationship
            rel_key = (source_id, target_id, rel_type)
            
            if rel_key in seen_relationships:
                relationships_to_remove.append(rel)
            else:
                seen_relationships.add(rel_key)

        # Remove duplicates
        for rel in relationships_to_remove:
            source_el = self.find_element_by_id(rel.get("source"))
            target_el = self.find_element_by_id(rel.get("target"))
            rel_type = rel.get(f"{{{XSI}}}type", "").replace("archimate:", "")
            
            source_name = source_el.get("name", "Unnamed") if source_el else "Unknown"
            target_name = target_el.get("name", "Unnamed") if target_el else "Unknown"
            
            self._find_and_remove_element(rel)
            duplicates_removed.append(f"Removed duplicate '{rel_type}' from '{source_name}' to '{target_name}'")

        return duplicates_removed

    def _build_validation_report(self, actions):
        """Build a comprehensive validation report."""
        total_actions = sum(len(items) for items in actions.values())
        
        if total_actions == 0:
            return "Validation Complete: No issues found. Model is clean and valid."
        
        report_lines = ["Validation and Cleaning Complete", "=" * 40, f"Total actions performed: {total_actions}\n"]
        
        # Relocated elements
        if actions['relocated_elements']:
            report_lines.append(f"RELOCATED ELEMENTS ({len(actions['relocated_elements'])}):")
            for action in actions['relocated_elements']:
                report_lines.append(f"  • {action}")
            report_lines.append("")
        
        # Fixed relationships
        if actions['fixed_relationships']:
            report_lines.append(f"FIXED RELATIONSHIPS ({len(actions['fixed_relationships'])}):")
            for action in actions['fixed_relationships']:
                report_lines.append(f"  • {action}")
            report_lines.append("")
        
        # Removed relationships
        if actions['removed_relationships']:
            report_lines.append(f"REMOVED RELATIONSHIPS ({len(actions['removed_relationships'])}):")
            for action in actions['removed_relationships']:
                report_lines.append(f"  • {action}")
            report_lines.append("")
        
        # Duplicates removed
        if actions['duplicates_removed']:
            report_lines.append(f"DUPLICATES REMOVED ({len(actions['duplicates_removed'])}):")
            for action in actions['duplicates_removed']:
                report_lines.append(f"  • {action}")
        
        return "\n".join(report_lines)

    def _find_and_remove_element(self, element_to_remove):
        """Helper to find and remove an element from its parent folder."""
        if self.model is None or element_to_remove is None:
            return False
        
        for folder in self.model.findall("folder"):
            try:
                folder.remove(element_to_remove)
                return True
            except ValueError:
                pass
        
        return False


    def _convert_json_format(self, json_data):
        """Convert various JSON formats to the standard format expected by the application."""
        converted = {"elements": [], "relationships": []}
        
        # Handle array format (your current format)
        if isinstance(json_data, list):
            for item in json_data:
                if not isinstance(item, dict):
                    continue
                    
                # Check if it's a relationship (has source_name and target_name)
                if "source_name" in item and "target_name" in item:
                    # It's a relationship
                    relationship = {
                        "type": item.get("element_type", ""),
                        "source": item.get("source_name", ""),
                        "target": item.get("target_name", ""),
                        "description": item.get("description", "")
                    }
                    if self._validate_relationship(relationship):
                        converted["relationships"].append(relationship)
                # Check if it's an element (has element_type and name, but no source_name/target_name)
                elif "element_type" in item and "name" in item and "source_name" not in item:
                    # It's a regular element
                    element = {
                        "type": item["element_type"],
                        "name": item["name"],
                        "description": item.get("description", "")
                    }
                    if self._validate_element(element):
                        converted["elements"].append(element)
        
        # Handle standard format with elements/relationships keys
        elif isinstance(json_data, dict):
            if "elements" in json_data:
                for element in json_data["elements"]:
                    if self._validate_element(element):
                        converted["elements"].append(element)
            
            if "relationships" in json_data:
                for relationship in json_data["relationships"]:
                    if self._validate_relationship(relationship):
                        converted["relationships"].append(relationship)
        
        return converted

    def _validate_relationship(self, relationship):
        """Validate an individual relationship object."""
        if not isinstance(relationship, dict):
            return False
            
        if "type" not in relationship or "source" not in relationship or "target" not in relationship:
            print(f"Missing required fields in relationship: {relationship}")
            return False
            
        if not isinstance(relationship["type"], str) or not isinstance(relationship["source"], str) or not isinstance(relationship["target"], str):
            print(f"Invalid field types in relationship: {relationship}")
            return False
            
        if not relationship["type"] or not relationship["source"] or not relationship["target"]:
            print(f"Empty required fields in relationship: {relationship}")
            return False
            
        if "description" in relationship and not isinstance(relationship["description"], str):
            print(f"Invalid description type in relationship: {relationship}")
            return False
            
        return True

    def _validate_json_structure(self, json_data):
        """Validate the basic structure of the JSON data - now more flexible."""
        if not isinstance(json_data, (dict, list)):
            messagebox.showerror("JSON Error", "JSON must be an object or array.")
            return False
        
        # For array format, check that it contains valid objects
        if isinstance(json_data, list):
            if not json_data:
                messagebox.showerror("JSON Error", "JSON array is empty.")
                return False
            
            valid_items = 0
            for item in json_data:
                if isinstance(item, dict) and ("element_type" in item or "type" in item):
                    valid_items += 1
            
            if valid_items == 0:
                messagebox.showerror("JSON Error", "No valid elements or relationships found in JSON array.")
                return False
        
        # For object format, check for expected structure
        elif isinstance(json_data, dict):
            if "elements" not in json_data and "relationships" not in json_data:
                messagebox.showerror("JSON Error", "JSON object must contain 'elements' and/or 'relationships' arrays.")
                return False
            
            if "elements" in json_data and not isinstance(json_data["elements"], list):
                messagebox.showerror("JSON Error", "'elements' must be an array.")
                return False
                
            if "relationships" in json_data and not isinstance(json_data["relationships"], list):
                messagebox.showerror("JSON Error", "'relationships' must be an array.")
                return False
                
        return True

    def update_staged_preview(self):
        """Updates the preview text based on the JSON content in the paste area."""
        content = self.paste_text.get("1.0", "end").strip()
        if not content:
            self.preview_text.config(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "No staged content.")
            self.preview_text.config(state="disabled")
            return
        
        try:
            json_data = json.loads(content)
            converted_data = self._convert_json_format(json_data)
            preview_lines = []
            
            # Process elements
            elements = converted_data.get("elements", [])
            if elements:
                preview_lines.append("Elements to add:")
                for element in elements:
                    preview_lines.append(f"  - {element['type']}: {element['name']}")
                    if element.get("description"):
                        preview_lines.append(f"    Description: {element['description']}")
            
            # Process relationships
            relationships = converted_data.get("relationships", [])
            if relationships:
                if elements:
                    preview_lines.append("")  # Add spacing
                preview_lines.append("Relationships to add:")
                for rel in relationships:
                    preview_lines.append(f"  - {rel['source']} -> {rel['type']} -> {rel['target']}")
                    if rel.get("description"):
                        preview_lines.append(f"    Description: {rel['description']}")
            
            if not preview_lines:
                preview_lines.append("No valid elements or relationships found.")
            
            self.preview_text.config(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "\n".join(preview_lines))
            self.preview_text.config(state="disabled")
            
        except json.JSONDecodeError:
            self.preview_text.config(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "Invalid JSON format")
            self.preview_text.config(state="disabled")

    def _validate_json_structure(self, json_data):
        """Validate the basic structure of the JSON data."""
        if not isinstance(json_data, dict):
            messagebox.showerror("JSON Error", "JSON must be an object with 'elements' and/or 'relationships' arrays.")
            return False
        
        if "elements" not in json_data and "relationships" not in json_data:
            messagebox.showerror("JSON Error", "JSON must contain 'elements' and/or 'relationships' arrays.")
            return False
        
        if "elements" in json_data and not isinstance(json_data["elements"], list):
            messagebox.showerror("JSON Error", "'elements' must be an array.")
            return False
            
        if "relationships" in json_data and not isinstance(json_data["relationships"], list):
            messagebox.showerror("JSON Error", "'relationships' must be an array.")
            return False
            
        return True

    def _validate_element(self, element):
        """Validate an individual element object."""
        if not isinstance(element, dict):
            return False
            
        if "type" not in element or "name" not in element:
            messagebox.showerror("JSON Error", "Each element must have 'type' and 'name' fields.")
            return False
            
        if not isinstance(element["type"], str) or not isinstance(element["name"], str):
            messagebox.showerror("JSON Error", "Element 'type' and 'name' must be strings.")
            return False
            
        if "description" in element and not isinstance(element["description"], str):
            messagebox.showerror("JSON Error", "Element 'description' must be a string.")
            return False
            
        return True

    def show_staged_3d_preview(self):
        """Show 3D preview of staged JSON content."""
        content = self.paste_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("No Content", "Paste area is empty.")
            return
        
        try:
            # Parse JSON content using the same method as insert_from_paste
            json_data = json.loads(content)
            
            # Call the new JSON-aware 3D preview method
            self.viewer.show_staged_3d_preview_from_json(json_data)
            
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON format in paste area:\n{e}")
        except Exception as e:
            messagebox.showerror("3D Preview Error", f"Failed to create 3D preview:\n{e}")
    def get_folder_for_type_in_model(self, element_type, strategy_folder, business_folder, relations_folder):
        """Helper to determine which folder to use for an element type in the temporary model."""
        if "Relationship" in element_type:
            return relations_folder
        elif element_type in ["Goal", "Principle", "Requirement"]:
            return strategy_folder
        elif element_type in ["BusinessActor", "BusinessRole", "BusinessProcess"]:
            return business_folder
        else:
            return strategy_folder  # Default fallback

    def build_gui(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(fill="x", pady=4)
        self.open_button = tk.Button(toolbar, text="Open .archimate", command=self.open_file)
        self.open_button.pack(side="left", padx=4)
        self.save_button = tk.Button(toolbar, text="Save As XML...", command=self.save_as)
        self.save_button.pack(side="left", padx=4)

        # --- DB Buttons ---
        self.open_db_button = tk.Button(toolbar, text="Open DB", command=self.open_database)
        self.open_db_button.pack(side="left", padx=4)
        self.save_db_button = tk.Button(toolbar, text="Save to DB", command=self.save_to_database)
        self.save_db_button.pack(side="left", padx=4)

        self.export_csv_button = tk.Button(toolbar, text="Export to CSV", command=self.export_pivot_csv)
        self.export_csv_button.pack(side="left", padx=4)

        self.insert_button = tk.Button(toolbar, text="Insert (commit staged)", command=self.insert_from_paste)
        self.insert_button.pack(side="left", padx=4)
        self.undo_button = tk.Button(toolbar, text="Undo", command=self.undo)
        self.undo_button.pack(side="left", padx=4)
        self.refresh_button = tk.Button(toolbar, text="Refresh Tree", command=self.refresh_tree)
        self.refresh_button.pack(side="left", padx=4)
        self.view3d_button = tk.Button(toolbar, text="Show 3D View", command=lambda: self.viewer.show_3d_view(self.depth_var.get()))
        self.view3d_button.pack(side="left", padx=4)

        tk.Label(toolbar, text="3D Depth:").pack(side="left", padx=(10, 2))
        depth_slider = tk.Scale(toolbar, from_=0, to=5, orient=tk.HORIZONTAL, variable=self.depth_var, length=80)
        depth_slider.pack(side="left", padx=2)
        
        self.clean_button = tk.Button(toolbar, text="Clean & Validate", command=self.clean_and_validate_model)
        self.clean_button.pack(side="left", padx=4)
        # Add the catalog button
        self.catalog_button = tk.Button(toolbar, text="Catalog", command=self.show_catalog_window)
        self.catalog_button.pack(side="left", padx=4)

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

        quick_frame = tk.LabelFrame(right_frame, text="Quick Add (appends to Paste Area as JSON)")
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
        gemini_button_frame.pack(fill="x", pady=4)

        tk.Label(gemini_button_frame, text="Context Strategy:").pack(side="left", padx=(4, 2))
        self.gemini_context_strategy_var = tk.StringVar(value="None (Stateless)")
        context_options = ["None (Stateless)", "Auto-Detect", "Full Model"]
        context_combo = ttk.Combobox(gemini_button_frame, textvariable=self.gemini_context_strategy_var, values=context_options, state="readonly", width=15)
        context_combo.pack(side="left", padx=2)

        self.gemini_generate_button = tk.Button(gemini_button_frame, text="Generate!", command=self.handle_ask_gemini)
        self.gemini_generate_button.pack(side="right", padx=4, pady=0)

        paste_frame = tk.LabelFrame(right_frame, text="Paste Area (JSON staging)")
        paste_frame.pack(fill="both", expand=True, padx=4, pady=4)
        tk.Label(paste_frame, text="Paste JSON format:\n{\"elements\": [{\"type\": \"...\", \"name\": \"...\", \"description\": \"...\"}], \"relationships\": [{\"type\": \"...\", \"source\": \"...\", \"target\": \"...\", \"description\": \"...\"}]}").pack(anchor="w")
        self.paste_text = tk.Text(paste_frame, height=14)
        self.paste_text.pack(fill="both", expand=True)
        self.paste_text.bind("<<Modified>>", self.on_paste_modified)
        paste_buttons = tk.Frame(paste_frame)
        paste_buttons.pack(fill="x")
        tk.Button(paste_buttons, text="Clear Paste Area", command=self.clear_paste).pack(side="left", padx=4, pady=4)
        tk.Button(paste_buttons, text="Validate JSON", command=self.validate_json).pack(side="left", padx=4, pady=4)
        tk.Button(paste_buttons, text="3D Preview", command=self.show_staged_3d_preview).pack(side="left", padx=4, pady=4)
        tk.Button(paste_buttons, text="Format JSON", command=self.format_json).pack(side="left", padx=4, pady=4)

        preview_frame = tk.LabelFrame(right_frame, text="Staged Preview (from JSON paste area)")
        preview_frame.pack(fill="both", expand=True, padx=4, pady=4)
        self.preview_text = tk.Text(preview_frame, height=12, state="disabled")
        self.preview_text.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="No file loaded.")
        status = tk.Label(self.root, textvariable=self.status_var, anchor="w")
        status.pack(fill="x")
    
        self.update_staged_preview()

    def validate_json(self):
        """Validate the JSON in the paste area."""
        content = self.paste_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("JSON Validation", "Paste area is empty.")
            return
        
        try:
            json_data = json.loads(content)
            if self._validate_json_structure(json_data):
                # Validate individual elements and relationships
                valid = True
                for element in json_data.get("elements", []):
                    if not self._validate_element(element):
                        valid = False
                        break
                
                if valid:
                    for relationship in json_data.get("relationships", []):
                        if not self._validate_relationship(relationship):
                            valid = False
                            break
                
                if valid:
                    messagebox.showinfo("JSON Validation", "JSON is valid and properly formatted!")
                else:
                    messagebox.showwarning("JSON Validation", "JSON structure is valid but some elements/relationships have issues.")
            else:
                messagebox.showerror("JSON Validation", "JSON structure is invalid.")
                
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Validation", f"Invalid JSON format:\n{e}")

    def format_json(self):
        """Format the JSON in the paste area for better readability."""
        content = self.paste_text.get("1.0", "end").strip()
        if not content:
            return
        
        try:
            json_data = json.loads(content)
            formatted_json = json.dumps(json_data, indent=2)
            self.paste_text.delete("1.0", "end")
            self.paste_text.insert("1.0", formatted_json)
            self.update_staged_preview()
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Format Error", f"Invalid JSON format:\n{e}")

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
        for btn in [self.refresh_button, self.view3d_button, self.clean_button, self.gemini_generate_button, self.catalog_button, self.save_db_button, self.export_csv_button]:
            btn.config(state=tk.NORMAL if is_model_loaded else tk.DISABLED)

    def show_catalog_window(self):
        """Creates a non-modal window to view and edit entities by type."""
        if self.model is None:
            messagebox.showwarning("No Model", "Please open a model file first.")
            return

        # Prevent multiple catalog windows
        if hasattr(self, 'catalog_win') and self.catalog_win.winfo_exists():
            self.catalog_win.lift()
            return

        self.catalog_win = tk.Toplevel(self.root)
        self.catalog_win.title("Entity Catalog Editor")
        self.catalog_win.geometry("800x600")

        # --- Get entity types from the current model ---
        entity_types = set()
        for el in self.model.findall(".//element"):
            el_type_full = el.get(f"{{{XSI}}}type", "")
            if el_type_full and "Relationship" not in el_type_full:
                entity_types.add(el_type_full.replace("archimate:", ""))
        
        sorted_types = sorted(list(entity_types))

        # --- Widgets ---
        top_frame = tk.Frame(self.catalog_win, padx=10, pady=10)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="Entity Type:").pack(side="left")
        
        type_var = tk.StringVar()
        type_combo = ttk.Combobox(top_frame, textvariable=type_var, values=sorted_types, state="readonly")
        type_combo.pack(side="left", fill="x", expand=True, padx=5)

        # --- Treeview for displaying entities ---
        tree_frame = tk.Frame(self.catalog_win)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        catalog_tree = ttk.Treeview(tree_frame, columns=("name", "description"), show="headings")
        catalog_tree.heading("name", text="Name")
        catalog_tree.heading("description", text="Description")
        catalog_tree.column("name", width=250)
        catalog_tree.column("description", width=450)
        
        catalog_tree.pack(side="left", fill="both", expand=True)
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=catalog_tree.yview)
        tree_scroll.pack(side="right", fill="y")
        catalog_tree.config(yscrollcommand=tree_scroll.set)

        # --- Editing Frame ---
        edit_frame = tk.LabelFrame(self.catalog_win, text="Edit Selected Entity", padx=10, pady=10)
        edit_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(edit_frame, text="Name:").grid(row=0, column=0, sticky="w", pady=2)
        name_edit_var = tk.StringVar()
        name_edit_entry = tk.Entry(edit_frame, textvariable=name_edit_var)
        name_edit_entry.grid(row=0, column=1, sticky="ew", padx=5)

        tk.Label(edit_frame, text="Description:").grid(row=1, column=0, sticky="nw", pady=2)
        desc_edit_text = tk.Text(edit_frame, height=4, wrap="word")
        desc_edit_text.grid(row=1, column=1, sticky="ew", padx=5)
        edit_frame.grid_columnconfigure(1, weight=1)

        # --- Button Frame within Edit Frame ---
        button_frame = tk.Frame(edit_frame)
        button_frame.grid(row=2, column=1, sticky="e", pady=5)

        copy_button = tk.Button(button_frame, text="Copy Selected", state="disabled")
        copy_button.pack(side="left", padx=(0, 10))

        update_button = tk.Button(button_frame, text="Update Entity", state="disabled")
        update_button.pack(side="left")
        
        default_button_bg = update_button.cget("background") # Store default color

        # --- Logic ---
        def copy_selection_to_clipboard(*args):
            """Copies the selected rows from the catalog tree to the clipboard."""
            selection = catalog_tree.selection()
            if not selection:
                return

            data_to_copy = []
            for item_id in selection:
                values = catalog_tree.item(item_id, "values")
                # Join columns with a tab for easy pasting into spreadsheets/text editors
                row_string = "\t".join(str(v) for v in values)
                data_to_copy.append(row_string)

            final_string = "\n".join(data_to_copy)

            if final_string:
                self.catalog_win.clipboard_clear()
                self.catalog_win.clipboard_append(final_string)
                copy_button.config(background=default_button_bg) # Reset glow

        def on_type_selected(*args):
            selected_type = type_var.get()
            catalog_tree.delete(*catalog_tree.get_children()) # Clear previous entries
            if not selected_type:
                return

            for el in self.model.findall(".//element"):
                el_type_full = el.get(f"{{{XSI}}}type", "")
                if el_type_full.replace("archimate:", "") == selected_type:
                    el_id = el.get("id")
                    name = el.get("name", "")
                    doc_el = el.find("documentation")
                    description = doc_el.text if doc_el is not None else ""
                    catalog_tree.insert("", "end", iid=el_id, values=(name, description))

        def on_catalog_item_select(*args):
            selection = catalog_tree.selection()
            if not selection:
                name_edit_var.set("")
                desc_edit_text.delete("1.0", "end")
                update_button.config(state="disabled")
                copy_button.config(state="disabled", background=default_button_bg) # Disable and reset glow
                return
            
            item_id = selection[0]
            values = catalog_tree.item(item_id, "values")
            name_edit_var.set(values[0])
            desc_edit_text.delete("1.0", "end")
            desc_edit_text.insert("1.0", values[1])
            update_button.config(state="normal")
            copy_button.config(state="normal", background="yellow") # Enable and set glow

        def update_entity():
            selection = catalog_tree.selection()
            if not selection:
                return
            
            item_id = selection[0]
            element_to_update = self.find_element_by_id(item_id)
            if element_to_update is None:
                messagebox.showerror("Error", "Could not find the selected element in the model.")
                return

            new_name = name_edit_var.get().strip()
            new_desc = desc_edit_text.get("1.0", "end-1c").strip()

            if not new_name:
                messagebox.showwarning("Validation", "Element name cannot be empty.")
                return

            # Update the XML model
            element_to_update.set("name", new_name)
            
            doc_el = element_to_update.find("documentation")
            if new_desc:
                if doc_el is None:
                    doc_el = ET.SubElement(element_to_update, "documentation")
                doc_el.text = new_desc
            elif doc_el is not None:
                # Remove documentation element if description is cleared
                element_to_update.remove(doc_el)

            # Update the catalog tree view
            catalog_tree.item(item_id, values=(new_name, new_desc))

            # Mark model as dirty and refresh main UI
            self.dirty = True
            self.save_history()
            self.build_element_database()
            self.build_relationship_map()
            self.calculate_relationship_counts()
            self.refresh_tree()
            self.update_xml_output_panel()
            self.update_button_states()
            messagebox.showinfo("Success", f"Updated '{new_name}'.")

        type_var.trace_add('write', on_type_selected)
        catalog_tree.bind("<<TreeviewSelect>>", on_catalog_item_select)
        update_button.config(command=update_entity)
        copy_button.config(command=copy_selection_to_clipboard)

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
                context.append("## New Entities:")
                context.extend(new_inv)
            if new_triples:
                context.append("## New Relationships:")
                context.extend(new_triples)
            return "\n".join(context) if context else "No changes since last snapshot."
        else:
            # Full model
            inventory = self.extract_model_inventory()
            triples = self.extract_model_triples()
            context = ["# Full Model Snapshot"]
            if inventory:
                context.append("## Entities:")
                context.extend(inventory)
            if triples:
                context.append("## Relationships:")
                context.extend(triples)
            return "\n".join(context)

    def _send_to_gemini(self, prompt):
        """Sends the prompt to Gemini with the selected context strategy."""
        strategy = self.gemini_context_strategy_var.get()
        context = None
        if strategy == "Auto-Detect":
            context = self.build_gemini_context(delta_only=True)
        elif strategy == "Full Model":
            context = self.build_gemini_context(delta_only=False)
        # else: strategy == "None (Stateless)" -> context remains None

        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n---\n\n{prompt}"

        try:
            client = genai.Client()
            response = client.models.generate_content(
                model=self.model_var.get(),
                contents=full_prompt
            )
            self._handle_gemini_response(response.text)
        except Exception as e:
            messagebox.showerror("Gemini Error", f"Failed to call Gemini API:\n{e}")

    def _handle_gemini_response(self, response_text):
        """Processes the response from Gemini and updates the paste area."""
        # Try to parse JSON from the response
        try:
            # Look for JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                json_data = json.loads(json_str)
                
                # Validate the JSON structure
                if self._validate_json_structure(json_data):
                    # Format and insert into paste area
                    formatted_json = json.dumps(json_data, indent=2)
                    self.paste_text.delete("1.0", "end")
                    self.paste_text.insert("1.0", formatted_json)
                    self.update_staged_preview()
                    messagebox.showinfo("Gemini Response", "Successfully parsed JSON from response and loaded into paste area.")
                else:
                    messagebox.showwarning("Gemini Response", "Response contained JSON but structure was invalid.")
            else:
                # No JSON found, show the raw response
                messagebox.showinfo("Gemini Response", f"No JSON found in response. Raw response:\n\n{response_text}")
        except json.JSONDecodeError:
            # JSON parsing failed, show the raw response
            messagebox.showinfo("Gemini Response", f"Could not parse JSON from response. Raw response:\n\n{response_text}")

    def on_paste_modified(self, event=None):
        """Called when the paste text area is modified."""
        if self.paste_text.edit_modified():
            self.update_staged_preview()
            self.update_button_states()
            self.paste_text.edit_modified(False)


    def quick_add_to_paste(self):
        """Adds a single element from the quick-add form to the paste area as JSON."""
        etype = self.type_var.get()
        name = self.name_entry.get().strip()
        description = self.desc_entry.get().strip()
        
        if not name:
            messagebox.showwarning("Missing Name", "Please enter a name for the element.")
            return
        
        # Get current paste content
        current_content = self.paste_text.get("1.0", "end").strip()
        json_data = {"elements": [], "relationships": []}
        
        # Parse existing JSON if present
        if current_content:
            try:
                existing_data = json.loads(current_content)
                if "elements" in existing_data:
                    json_data["elements"] = existing_data["elements"]
                if "relationships" in existing_data:
                    json_data["relationships"] = existing_data["relationships"]
            except json.JSONDecodeError:
                # If existing content is invalid JSON, start fresh
                json_data = {"elements": [], "relationships": []}
        
        # Add the new element
        new_element = {"type": etype, "name": name}
        if description:
            new_element["description"] = description
            
        json_data["elements"].append(new_element)
        
        # Update the paste area with formatted JSON
        formatted_json = json.dumps(json_data, indent=2)
        self.paste_text.delete("1.0", "end")
        self.paste_text.insert("1.0", formatted_json)
        
        # Clear the quick-add form
        self.name_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")
        
        self.update_staged_preview()

    def clear_paste(self):
        """Clears the paste area."""
        self.paste_text.delete("1.0", "end")
        self.update_staged_preview()

    # --- File I/O Methods ---
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

            # --- Set mode to file ---
            self.current_mode = 'file'
            self.db_manager = None
            self.db_filepath = None

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
            self.status_var.set(f"Saved XML: {os.path.basename(path)}")
            self.update_button_states()
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save file:\n{e}")

    # --- DB Integration Methods ---
    def open_database(self):
        path = filedialog.askopenfilename(
            title="Open ArchiMate Database",
            filetypes=[("SQLite Database", "*.db;*.sqlite;*.sqlite3"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            self.db_manager = ArchiMateDB(path)
            self.db_filepath = path
            self.load_model_from_db()
            self.status_var.set(f"Loaded DB: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to open database:\n{e}")
            self.db_manager = None
            self.db_filepath = None

    def save_to_database(self):
        if self.model is None:
            messagebox.showwarning("No Model", "No model is currently loaded to save.")
            return

        db_path = self.db_filepath
        if self.current_mode == 'file' or not db_path:
            db_path = filedialog.asksaveasfilename(
                title="Save Model to Database",
                defaultextension=".db",
                filetypes=[("SQLite Database", "*.db"), ("All files", "*.*")]
            )
            if not db_path:
                return

        try:
            if self.db_manager is None or self.db_filepath != db_path:
                self.db_manager = ArchiMateDB(db_path)

            conflicts = self.db_manager.import_from_xml(self.model)

            if conflicts:
                conflict_msg = "Could not save due to version conflicts (model was updated by another user):\n"
                conflict_msg += "\n".join([f"- {c['type']} '{c['name']}" for c in conflicts[:5]])
                if len(conflicts) > 5:
                    conflict_msg += f"\n... and {len(conflicts) - 5} more."
                messagebox.showwarning("Save Conflict", conflict_msg)
            else:
                self.db_filepath = db_path
                self.current_mode = 'db'
                self.dirty = False
                self.update_button_states()
                self.status_var.set(f"Saved to DB: {os.path.basename(db_path)}")
                messagebox.showinfo("Success", f"Model successfully saved to database:\n{db_path}")

        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save to database:\n{e}")

    def load_model_from_db(self):
        if not self.db_manager:
            return
        
        self.model = self.db_manager.export_to_xml()
        if self.model is None:
            messagebox.showerror("DB Error", "Failed to construct model from database.")
            return

        self.tree = ET.ElementTree(self.model)
        self.filepath = None # Not a file-based model
        self.current_mode = 'db'
        self.dirty = False
        self.history.clear()
        self.element_db.clear()

        self.build_element_database()
        self.build_relationship_map()
        self.calculate_relationship_counts()
        self.save_history()
        self.refresh_tree()
        self.update_staged_preview()
        self.update_xml_output_panel()
        self.update_button_states()

    # --- Element Database Management ---
    def build_element_database(self):
        if self.model is None:
            return
        self.element_db.clear()
        self.element_db_by_id = {}
        name_type_combinations = {}
        warnings = []

        for element in self.model.findall(".//element"):
            name = element.get("name")
            element_id = element.get("id")
            element_type = element.get(f"{{{XSI}}}type", "")
            
            if name and element_id:
                name_lower = name.lower()
                # Handle name collisions by storing a list of elements for each name
                if name_lower not in self.element_db:
                    self.element_db[name_lower] = []
                self.element_db[name_lower].append((element_id, element_type))

                # Check for duplicates of different types to warn the user
                if name_lower in name_type_combinations and name_type_combinations[name_lower] != element_type:
                    warnings.append(f"Warning: Name '{name}' is used by multiple element types. Lookups by name may be unpredictable without a type specifier.")
                name_type_combinations[name_lower] = element_type

            if element_id:
                self.element_db_by_id[element_id] = {'name': name, 'type': element_type}
        
        if warnings:
            # Use a set to show unique warnings only
            unique_warnings = "\n".join(sorted(list(set(warnings))))
            print("--- Build Element Database Warnings --- \n" + unique_warnings)

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

    # --- TreeView Methods ---
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
        self.update_xml_output_panel()

    def search_tree(self, *args):
        """Filters the treeview based on the search entry."""
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

    # --- Folder Management ---
    def get_folder_for_type(self, element_type):
        short = element_type.split(":")[-1]
        folder_name = FOLDER_MAP.get(short, "Other")
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

    # --- XML Output ---
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

    # --- Element Lookup ---
    def find_element_by_id(self, el_id):
        if self.model is None:
            return None
        return self.model.find(f".//*[@id='{el_id}']")

    def find_all_relationships(self):
        """Finds and returns a list of all relationship elements in the model."""
        if self.model is None:
            return []
        relationships = []
        for folder in self.model.findall("folder"):
            for element in folder.findall("element"):
                if element.get(f"{{{XSI}}}type", "").endswith("Relationship"):
                    relationships.append(element)
        return relationships

    def get_element_relationships(self, el_id):
        """Returns a list of relationships for a given element ID using the pre-built map."""
        return self.relationship_map.get(el_id, [])

    # --- Export Methods ---
    def export_pivot_csv(self):
        """Exports the entire model to a single denormalized CSV file for pivot tables."""
        if self.model is None:
            messagebox.showwarning("No Model", "Please load a model before exporting.")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"architecture_export_{timestamp}.csv"

        path = filedialog.asksaveasfilename(
            title="Export Architecture to CSV",
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        header = [
            "ElementID", "ElementName", "ElementType", "ElementFolder", "ElementDescription",
            "RelatedTo", "RelatedType", "RelatedFolder", "RelationshipType", "RelationshipDescription"
        ]
        
        rows = []
        element_count = 0

        try:
            if self.current_mode == 'db' and self.db_manager:
                # --- Database Mode ---
                db_rows = self.db_manager.get_pivot_data()
                # Clean up element types for readability
                for row in db_rows:
                    row_list = list(row)
                    if row_list[2]: row_list[2] = row_list[2].replace("archimate:", "")
                    if row_list[6]: row_list[6] = row_list[6].replace("archimate:", "")
                    if row_list[8]: row_list[8] = row_list[8].replace("archimate:", "")
                    rows.append(row_list)
                
                # A simple count of unique elements from the first column
                element_count = len(set(r[0] for r in rows))

            else:
                # --- XML File Mode ---
                element_details = {}
                for folder in self.model.findall("folder"):
                    folder_name = folder.get("name", "Unknown")
                    for el in folder.findall(".//element"):
                        el_id = el.get("id")
                        doc_el = el.find("documentation")
                        element_details[el_id] = {
                            "id": el_id,
                            "name": el.get("name", ""),
                            "type": el.get(f"{{{XSI}}}type", "").replace("archimate:", ""),
                            "folder": folder_name,
                            "desc": doc_el.text if doc_el is not None else ""
                        }
                
                element_count = len(element_details)
                related_element_ids = set()

                for rel in self.find_all_relationships():
                    source_id = rel.get("source")
                    target_id = rel.get("target")
                    related_element_ids.add(source_id)
                    related_element_ids.add(target_id)

                    source = element_details.get(source_id)
                    target = element_details.get(target_id)
                    if not source or not target:
                        continue

                    rel_doc = rel.find("documentation")
                    rel_desc = rel_doc.text if rel_doc is not None else ""
                    rel_type = rel.get(f"{{{XSI}}}type", "").replace("archimate:", "")

                    # Row for the source element
                    rows.append([
                        source["id"], source["name"], source["type"], source["folder"], source["desc"],
                        target["name"], target["type"], target["folder"], rel_type, rel_desc
                    ])
                    # Row for the target element
                    rows.append([
                        target["id"], target["name"], target["type"], target["folder"], target["desc"],
                        source["name"], source["type"], source["folder"], rel_type, rel_desc
                    ])

                # Add orphaned elements
                for el_id, details in element_details.items():
                    if el_id not in related_element_ids:
                        rows.append([
                            details["id"], details["name"], details["type"], details["folder"], details["desc"],
                            "", "", "", "", ""
                        ])

            # --- Write to CSV File ---
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)

            messagebox.showinfo("Export Successful", f"Successfully exported {element_count} elements to:\n{path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred during CSV export:\n{e}")

    # --- Validation and Cleaning Methods ---
    def validate_and_clean_relationships(self):
        """Placeholder for validation and cleaning functionality."""
        messagebox.showinfo("Info", "Validation and cleaning functionality to be implemented.")

    def autocomplete_model_conservative(self):
        """Placeholder for autocomplete functionality."""
        messagebox.showinfo("Info", "Autocomplete functionality to be implemented.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ArchiIngestorApp(root)
    root.mainloop()
