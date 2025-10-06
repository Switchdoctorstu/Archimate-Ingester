import xml.etree.ElementTree as ET
import uuid
import copy
import os
from xml.dom import minidom
import datetime


import sqlite3
import json

from config import FOLDER_MAP

# ---- Namespaces ----
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ARCHIMATE = "http://www.archimatetool.com/archimate"
ET.register_namespace("xsi", XSI)
ET.register_namespace("archimate", ARCHIMATE)

# ---- Utility ----
def generate_id(prefix="id"):
    return f"{prefix}-{uuid.uuid4().hex}"


class ArchiMateDB:
    """Manages all SQLite database operations for an ArchiMate model."""
    def __init__(self, db_path):
        self.db_path = db_path
        self.create_tables()

    def _get_connection(self):
        """Returns a new database connection and cursor."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn, conn.cursor()

    def create_tables(self):
        """Creates the necessary database tables if they don't exist."""
        conn, c = self._get_connection()
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS elements (
                    guid TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT,
                    description TEXT,
                    folder_type TEXT,
                    version INTEGER DEFAULT 1,
                    properties TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS relationships (
                    guid TEXT PRIMARY KEY,
                    source_guid TEXT NOT NULL,
                    target_guid TEXT NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT,
                    description TEXT,
                    version INTEGER DEFAULT 1,
                    FOREIGN KEY (source_guid) REFERENCES elements(guid) ON DELETE CASCADE,
                    FOREIGN KEY (target_guid) REFERENCES elements(guid) ON DELETE CASCADE
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS model_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def get_pivot_data(self):
        """
        Exports a denormalized list of all elements and their relationships for CSV export.
        This query ensures all elements are included, even orphans.
        """
        conn, c = self._get_connection()
        try:
            query = """
                -- Outgoing Relationships from a source element
                SELECT
                    e1.guid AS ElementID, e1.name AS ElementName, e1.type AS ElementType, e1.folder_type AS ElementFolder, e1.description AS ElementDescription,
                    e2.name AS RelatedTo, e2.type AS RelatedType, e2.folder_type AS RelatedFolder,
                    r.type AS RelationshipType, r.description AS RelationshipDescription
                FROM relationships r
                JOIN elements e1 ON r.source_guid = e1.guid
                JOIN elements e2 ON r.target_guid = e2.guid

                UNION ALL

                -- Incoming Relationships to a target element
                SELECT
                    e1.guid AS ElementID, e1.name AS ElementName, e1.type AS ElementType, e1.folder_type AS ElementFolder, e1.description AS ElementDescription,
                    e2.name AS RelatedTo, e2.type AS RelatedType, e2.folder_type AS RelatedFolder,
                    r.type AS RelationshipType, r.description AS RelationshipDescription
                FROM relationships r
                JOIN elements e1 ON r.target_guid = e1.guid -- e1 is the element of focus
                JOIN elements e2 ON r.source_guid = e2.guid -- e2 is the related element

                UNION ALL

                -- Orphaned elements (not in any relationship)
                SELECT
                    e.guid, e.name, e.type, e.folder_type, e.description,
                    NULL, NULL, NULL, NULL, NULL
                FROM elements e
                WHERE e.guid NOT IN (SELECT source_guid FROM relationships UNION SELECT target_guid FROM relationships);
            """
            c.execute(query)
            return c.fetchall()
        finally:
            conn.close()

    def import_from_xml(self, model_root):
        """
        Imports an entire XML model into the database, overwriting existing data.
        Implements optimistic locking by checking version numbers.
        Returns a list of conflicts if any are found.
        """
        conn, c = self._get_connection()
        conflicts = []
        try:
            with conn: # Use transaction
                # --- Get current versions from DB for optimistic locking ---
                db_versions = {}
                c.execute("SELECT guid, version FROM elements")
                for row in c.fetchall():
                    db_versions[row['guid']] = row['version']
                c.execute("SELECT guid, version FROM relationships")
                for row in c.fetchall():
                    db_versions[row['guid']] = row['version']

                # --- Store folder and view structure for round-trip compatibility ---
                views_folder = model_root.find("./folder[@type='diagrams']")
                views_xml = ET.tostring(views_folder, encoding='unicode') if views_folder is not None else ''
                c.execute("INSERT OR REPLACE INTO model_metadata (key, value) VALUES (?, ?)",
                          ('original_views_xml', views_xml))

                # --- Clear existing data ---
                c.execute("DELETE FROM elements")
                c.execute("DELETE FROM relationships")

                # --- Import Elements ---
                for folder in model_root.findall("folder"):
                    folder_type = folder.get("type", "other")

                    # Skip processing elements in the diagrams folder, as it's stored as a whole
                    if folder_type == 'diagrams':
                        continue

                    for el in folder.findall("element"):
                        el_type = el.get(f"{{{XSI}}}type", "")
                        if "Relationship" in el_type:
                            continue # Process relationships in the next pass

                        guid = el.get("id")
                        doc_el = el.find("documentation")
                        description = doc_el.text if doc_el is not None else ""
                        
                        # Optimistic lock check
                        xml_version = int(el.get('version', '1'))
                        if guid in db_versions and db_versions[guid] > xml_version:
                            conflicts.append({'guid': guid, 'name': el.get('name'), 'type': 'element'})
                            continue

                        c.execute("""
                            INSERT INTO elements (guid, type, name, description, folder_type, version, properties)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (guid, el_type, el.get("name"), description, folder_type, xml_version + 1, json.dumps({})))

                # --- Import Relationships ---
                for rel in model_root.findall(f".//element"):
                    rel_type = rel.get(f"{{{XSI}}}type", "")
                    if "Relationship" not in rel_type:
                        continue
                    
                    guid = rel.get("id")
                    doc_el = rel.find("documentation")
                    description = doc_el.text if doc_el is not None else ""

                    xml_version = int(rel.get('version', '1'))
                    if guid in db_versions and db_versions[guid] > xml_version:
                        conflicts.append({'guid': guid, 'name': rel.get('name'), 'type': 'relationship'})
                        continue

                    c.execute("""
                        INSERT INTO relationships (guid, source_guid, target_guid, type, name, description, version)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (guid, rel.get("source"), rel.get("target"), rel_type, rel.get("name"), description, xml_version + 1))

                if conflicts:
                    conn.rollback() # Abort transaction if conflicts found
                    return conflicts

            return [] # No conflicts
        finally:
            conn.close()

    def export_to_xml(self):
        """Exports the database content to an in-memory XML model."""
        conn, c = self._get_connection()
        try:
            # --- Create base model structure using the correct namespace format ---
            model_root = ET.Element(f"{{{ARCHIMATE}}}model", {
                f"{{{XSI}}}schemaLocation": "http://www.archimatetool.com/archimate archimate.xsd",
                "name": "Exported from DB", "id": generate_id()
            })

            # --- Recreate folder structure ---
            folders = {}
            c.execute("SELECT DISTINCT folder_type FROM elements")
            for row in c.fetchall():
                ftype = row['folder_type']
                fname = next((k for k, v in FOLDER_MAP.items() if v.lower() == ftype), ftype.capitalize())
                folder_el = ET.SubElement(model_root, "folder", {"name": fname, "id": generate_id(), "type": ftype})
                folders[ftype] = folder_el
            
            relations_folder = ET.SubElement(model_root, "folder", {"name": "Relations", "id": generate_id(), "type": "relations"})

            # --- Restore original views ---
            c.execute("SELECT value FROM model_metadata WHERE key = 'original_views_xml'")
            row = c.fetchone()
            if row and row['value']:
                try:
                    # Wrap the XML fragment with a root that defines the necessary namespaces
                    # to provide context for the parser.
                    xml_fragment = row['value']
                    wrapped_xml = f'<root xmlns:archimate="{ARCHIMATE}" xmlns:xsi="{XSI}">{xml_fragment}</root>'
                    
                    # Parse the wrapped XML
                    temp_root = ET.fromstring(wrapped_xml)
                    
                    # Find the original folder element within the wrapper
                    views_el = temp_root.find("./folder")
                    if views_el is not None:
                        model_root.append(views_el)
                except ET.ParseError as e:
                    print(f"Warning: Could not parse stored views XML. Error: {e}")

            # --- Export Elements ---
            c.execute("SELECT * FROM elements")
            for row in c.fetchall():
                folder_el = folders.get(row['folder_type'])
                if folder_el is None:
                    folder_el = folders.setdefault('other', ET.SubElement(model_root, "folder", {"name": "Other", "id": generate_id(), "type": "other"}))
                
                attribs = {
                    f"{{{XSI}}}type": row['type'],
                    "id": row['guid'],
                    "name": row['name'],
                    "version": str(row['version'])
                }
                el = ET.SubElement(folder_el, "element", attribs)
                if row['description']:
                    doc = ET.SubElement(el, "documentation")
                    doc.text = row['description']

            # --- Export Relationships ---
            c.execute("SELECT * FROM relationships")
            for row in c.fetchall():
                attribs = {
                    f"{{{XSI}}}type": row['type'],
                    "id": row['guid'],
                    "source": row['source_guid'],
                    "target": row['target_guid'],
                    "version": str(row['version'])
                }
                if row['name']:
                    attribs['name'] = row['name']
                
                rel = ET.SubElement(relations_folder, "element", attribs)
                if row['description']:
                    doc = ET.SubElement(rel, "documentation")
                    doc.text = row['description']
            
            return model_root
        finally:
            conn.close()

