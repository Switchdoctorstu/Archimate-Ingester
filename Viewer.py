# Viewer_V6.py
# Augmented TOGAF ArchiMate 3D Viewer with:
# - Value Stream Visualisation
# - Impact/Driver Analysis (heatmap propagation)
# - Auto-map Process from Trigger (path extraction + layout)
#
# Based on user's Viewer_V5.py with added UI controls and rendering logic
# Requires: pygame, PyOpenGL, tkinter, numpy

import pygame
import math
import numpy as np
from tkinter import Tk, filedialog, messagebox, Frame, Label, Button, StringVar, OptionMenu, Scale, HORIZONTAL, Checkbutton, BooleanVar, Entry
from tkinter import ttk
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import xml.etree.ElementTree as ET
import traceback
import os
import sys
import time

# Import configuration from config.py if available
try:
    from config import FOLDER_MAP, RELATIONSHIP_TYPES, ARCHITECTURE_LAYERS, TOGAF_VIEWPOINTS
except Exception:
    FOLDER_MAP = {}
    RELATIONSHIP_TYPES = set()
    TOGAF_VIEWPOINTS = {
        "All": [],
        "Business Architecture": ["BusinessActor", "BusinessRole", "BusinessCollaboration", "BusinessInterface",
                                   "BusinessProcess", "BusinessFunction", "BusinessInteraction", "BusinessEvent",
                                   "BusinessService", "BusinessObject", "Contract", "Product"],
        "Application Architecture": ["ApplicationComponent", "ApplicationCollaboration", "ApplicationInterface",
                                     "ApplicationFunction", "ApplicationInteraction", "ApplicationProcess",
                                     "ApplicationEvent", "ApplicationService", "DataObject"],
        "Technology Architecture": ["Node", "Device", "SystemSoftware", "TechnologyCollaboration",
                                    "TechnologyInterface", "Path", "CommunicationNetwork", "TechnologyFunction",
                                    "TechnologyProcess", "TechnologyInteraction", "TechnologyEvent", "TechnologyService",
                                    "Artifact"],
        "Motivation": ["Stakeholder", "Driver", "Assessment", "Goal", "Outcome", "Principle",
                       "Requirement", "Constraint", "Meaning", "Value"],
        "Strategy": ["Resource", "Capability", "CourseOfAction", "ValueStream"],
        "Implementation & Migration": ["WorkPackage", "Deliverable", "ImplementationEvent", "Plateau"],
        "Physical": ["Equipment", "Facility", "Material", "DistributionNetwork"]
    }

    ARCHITECTURE_LAYERS = {
        "Motivation": {"order": 0, "color": (0.8, 0.2, 0.8), "flow_position": "left"},
        "Strategy": {"order": 1, "color": (1.0, 0.4, 0.4), "flow_position": "left"},
        "Business": {"order": 2, "color": (0.2, 0.6, 1.0), "flow_position": "center"},
        "Application": {"order": 3, "color": (0.2, 1.0, 0.6), "flow_position": "center"},
        "Technology": {"order": 4, "color": (1.0, 0.7, 0.2), "flow_position": "center"},
        "Implementation": {"order": 5, "color": (0.6, 0.6, 0.6), "flow_position": "right"},
        "Physical": {"order": 6, "color": (0.9, 0.5, 0.1), "flow_position": "right"}
    }

# --- Scene and rendering primitives (mostly unchanged) ---
class SceneNode:
    OBLONG_VERTICES = [
        [-1.0, -0.5, -0.5], [1.0, -0.5, -0.5], [1.0, 0.5, -0.5], [-1.0, 0.5, -0.5],
        [-1.0, -0.5, 0.5], [1.0, -0.5, 0.5], [1.0, 0.5, 0.5], [-1.0, 0.5, 0.5],
    ]
    OBLONG_FACES = [
        [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4],
        [2, 3, 7, 6], [1, 2, 6, 5], [0, 3, 7, 4],
    ]
    OBLONG_EDGES = [
        (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
        (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)
    ]

    def __init__(self, viewer, node_id, pos, size, color, label, element_type, layer):
        self.viewer = viewer
        self.id = node_id
        self.pos = np.array(pos, dtype=float)
        self.size = size
        self.color = color
        self.label = self._strip_archimate_prefix(str(label)) if label else ""
        self.element_type = self._strip_archimate_prefix(str(element_type)) if element_type else ""
        self.layer = layer
        self.original_color = color
        self.is_dimmed = False
        self.impact_score = 0.0  # for heatmap
        self.path_index = None  # for ordered path layout
        self.name_textures = {}
        self.type_textures = {}
        self.textures_created = False
        self.vertices = None
        self.update_vertices()

    def _strip_archimate_prefix(self, text):
        if text.startswith('archimate:'):
            return text[10:]
        return text

    def update_vertices(self):
        x, y, z = self.pos
        self.vertices = [
            [x + vx * self.size, y + vy * self.size, z + vz * self.size]
            for vx, vy, vz in self.OBLONG_VERTICES
        ]

    def create_textures(self):
        if self.textures_created:
            return
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            # Name texture - for all faces
            if self.label:
                font = pygame.font.SysFont('arial', 16)
                text_surface = font.render(self.label, True, (255, 255, 255))
                text_surface_rgba = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
                text_surface_rgba.blit(text_surface, (0, 0))
                text_data = pygame.image.tostring(text_surface_rgba, "RGBA", True)
                width, height = text_surface_rgba.get_width(), text_surface_rgba.get_height()
                # Create name textures for all faces
                faces = ['front', 'back', 'top', 'bottom', 'left', 'right']
                for face in faces:
                    tex_id = glGenTextures(1)
                    glBindTexture(GL_TEXTURE_2D, tex_id)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
                    self.name_textures[face] = {'id': tex_id, 'width': width, 'height': height}
            # Type texture - for all faces
            if self.element_type:
                font = pygame.font.SysFont('arial', 12)
                type_text = f"<{self.element_type}>"
                text_surface = font.render(type_text, True, (200, 200, 200))
                text_surface_rgba = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
                text_surface_rgba.blit(text_surface, (0, 0))
                text_data = pygame.image.tostring(text_surface_rgba, "RGBA", True)
                width, height = text_surface_rgba.get_width(), text_surface_rgba.get_height()
                # Create type textures for all faces
                faces = ['front', 'back', 'top', 'bottom', 'left', 'right']
                for face in faces:
                    tex_id = glGenTextures(1)
                    glBindTexture(GL_TEXTURE_2D, tex_id)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
                    self.type_textures[face] = {'id': tex_id, 'width': width, 'height': height}
            self.textures_created = True
        except Exception as e:
            print(f"Error creating textures for node {self.id}: {e}")

    def cleanup(self):
        for face_data in self.name_textures.values():
            glDeleteTextures([face_data['id']])
        self.name_textures.clear()
        for face_data in self.type_textures.values():
            glDeleteTextures([face_data['id']])
        self.type_textures.clear()

    def set_dimmed(self, dimmed):
        self.is_dimmed = dimmed

    def get_display_color(self):
        if self.is_dimmed:
            return tuple(c * 0.2 for c in self.original_color)
        # If impact heatmap active, blend color
        if self.impact_score and self.viewer.show_heatmap:
            # impact_score normalized 0..1 -> color from cool (blue-ish) to hot (red)
            s = max(0.0, min(1.0, self.impact_score))
            # interpolate from base color to red
            r = 0.2 + 0.8 * s
            g = max(0.2, (1.0 - s) * self.original_color[1])
            b = max(0.2, (1.0 - s) * self.original_color[2])
            return (r, g, b)
        return self.original_color

    def render(self):
        # Disable lighting for consistent colors
        glDisable(GL_LIGHTING)
        display_color = self.get_display_color()
        glColor3f(*display_color)
        glBegin(GL_QUADS)
        for face in self.OBLONG_FACES:
            for vertex_index in face:
                glVertex3fv(self.vertices[vertex_index])
        glEnd()

        # edges
        glColor3f(1.0, 1.0, 0.0)
        glLineWidth(1.2)
        glBegin(GL_LINES)
        for edge in self.OBLONG_EDGES:
            for vertex_index in edge:
                glVertex3fv(self.vertices[vertex_index])
        glEnd()

        if not self.is_dimmed:
            self._render_all_labels()
        
        # Re-enable lighting for other objects if needed
        #glEnable(GL_LIGHTING)

    def _render_all_labels(self):
        x, y, z = self.pos
        # Render name on front and back
        self._render_name_label(x, y, z + self.size * 0.5 + 0.01, 'front', self.size * 0.8, 0, 0, 1)
        self._render_name_label(x, y, z - self.size * 0.5 - 0.01, 'back', self.size * 0.8, 0, 0, -1)
        # Render type on top and bottom
        self._render_type_label(x, y + self.size * 0.5 + 0.01, z, 'top', self.size * 0.8, 0, 1, 0)
        self._render_type_label(x, y - self.size * 0.5 - 0.01, z, 'bottom', self.size * 0.8, 0, -1, 0)

    def _render_name_label(self, x, y, z, face, quad_size, normal_x, normal_y, normal_z):
        if face not in self.name_textures:
            return
        tex_data = self.name_textures[face]
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_data['id'])
        glColor3f(1, 1, 1)
        
        left = x - quad_size
        right = x + quad_size
        bottom = y - quad_size * 0.3
        top = y + quad_size * 0.3
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(left, bottom, z)
        glTexCoord2f(1, 0); glVertex3f(right, bottom, z)
        glTexCoord2f(1, 1); glVertex3f(right, top, z)
        glTexCoord2f(0, 1); glVertex3f(left, top, z)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def _render_type_label(self, x, y, z, face, quad_size, normal_x, normal_y, normal_z):
        if face not in self.type_textures:
            return
        tex_data = self.type_textures[face]
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_data['id'])
        glColor3f(1, 1, 1)
        
        left = x - quad_size
        right = x + quad_size
        front = z - quad_size * 0.3
        back = z + quad_size * 0.3
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(left, y, front)
        glTexCoord2f(1, 0); glVertex3f(right, y, front)
        glTexCoord2f(1, 1); glVertex3f(right, y, back)
        glTexCoord2f(0, 1); glVertex3f(left, y, back)
        glEnd()
        glDisable(GL_TEXTURE_2D)


class RelationshipTube:
    def __init__(self, viewer, start_pos, end_pos, color, rel_type, radius=0.03, sides=8, strength=1.0):
        self.viewer = viewer
        self.start_pos = np.array(start_pos, dtype=float)
        self.end_pos = np.array(end_pos, dtype=float)
        self.color = color
        self.rel_type = self._strip_archimate_prefix(str(rel_type))
        self.radius = radius
        self.sides = sides
        self.quadric = gluNewQuadric()
        self.is_dimmed = False
        self.type_tex_id = None
        self.type_tex_width = 0
        self.type_tex_height = 0
        self.create_texture()
        self.direction = self.end_pos - self.start_pos
        self.length = np.linalg.norm(self.direction)
        if self.length > 1e-6:
            self.direction = self.direction / self.length
        else:
            self.direction = np.array([0.0, 0.0, 1.0])
            self.length = 0
        self.strength = strength  # used to vary width in impact visualisation

    def _strip_archimate_prefix(self, text):
        if text.startswith('archimate:'):
            return text[10:]
        return text

    def create_texture(self):
        try:
            if not pygame.font.get_init():
                pygame.font.init()
            if self.rel_type:
                # Use larger font for better visibility
                font = pygame.font.SysFont('arial', 18)
                display_text = self.rel_type.replace('Relationship', '')
                text_surface = font.render(display_text, True, (255, 255, 255))
                text_surface_rgba = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
                bg_color = (0, 0, 0, 180)
                text_surface_rgba.fill(bg_color)
                text_surface_rgba.blit(text_surface, (0, 0))
                text_data = pygame.image.tostring(text_surface_rgba, "RGBA", True)
                width, height = text_surface_rgba.get_width(), text_surface_rgba.get_height()
                self.type_tex_id = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, self.type_tex_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
                self.type_tex_width, self.type_tex_height = width, height
        except Exception as e:
            print(f"Error creating relationship texture: {e}")

    def set_dimmed(self, dimmed):
        self.is_dimmed = dimmed

    def get_display_color(self):
        if self.is_dimmed:
            return tuple(c * 0.2 for c in self.color)
        return self.color

    def cleanup(self):
        if self.quadric:
            gluDeleteQuadric(self.quadric)
        if self.type_tex_id:
            glDeleteTextures([self.type_tex_id])

    def render(self):
        if self.length < 1e-6:
            return
        
        # Disable lighting for consistent colors
        glDisable(GL_LIGHTING)
        display_color = self.get_display_color()
        glColor3f(*display_color)
        
        z_axis = np.array([0.0, 0.0, 1.0])
        axis = np.cross(z_axis, self.direction)
        axis_norm = np.linalg.norm(axis)
        if axis_norm < 1e-6:
            axis = np.array([0.0, 1.0, 0.0])
        else:
            axis = axis / axis_norm
        angle = np.degrees(np.arccos(np.clip(np.dot(z_axis, self.direction), -1.0, 1.0)))
        glPushMatrix()
        glTranslatef(self.start_pos[0], self.start_pos[1], self.start_pos[2])
        if abs(angle) > 1e-6:
            glRotatef(angle, axis[0], axis[1], axis[2])
        # vary radius by strength (used by impact visualization)
        cylinder_radius = max(0.01, self.radius * (0.5 + 0.8 * self.strength))
        gluCylinder(self.quadric, cylinder_radius, cylinder_radius, self.length, self.sides, 1)
        # render label
        if not self.is_dimmed and self.type_tex_id:
            self._render_relationship_label(cylinder_radius)
        glPopMatrix()
        
        # Re-enable lighting for other objects
        # glEnable(GL_LIGHTING)

    def _render_relationship_label(self, cylinder_radius):
        """
        IMPORTANT: This renders the relationship label following the tube direction.
        DO NOT change to billboard style as architects need to see the flow direction.
        The label is positioned along the tube and oriented with the tube's rotation.
        """
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.type_tex_id)
        glColor3f(1, 1, 1)
        
        # Position label at 1/3 of the way along the tube for better visibility
        label_pos = self.length * 0.5 # Adjusted to center along tube
        # Increased quad size for larger text
        quad_width = self.type_tex_width * 0.006
        quad_height = self.type_tex_height * 0.006
        
        glPushMatrix()
        glTranslatef(0, 0, label_pos)
        
        # FIX: Rotate 90 degrees around X-axis to make text align with tube direction
        glRotatef(90, 1, 0, 1)
        
        # Position label slightly away from tube surface
        offset = cylinder_radius + 0.1
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(-quad_width, offset, -quad_height)
        glTexCoord2f(1, 0); glVertex3f(quad_width, offset, -quad_height)
        glTexCoord2f(1, 1); glVertex3f(quad_width, offset, quad_height)
        glTexCoord2f(0, 1); glVertex3f(-quad_width, offset, quad_height)
        glEnd()
        
        glPopMatrix()
        glDisable(GL_TEXTURE_2D)


# --- Small UI helper control (checkbox treeview) ---
class CheckboxTreeview(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.checked_items = set()
        self.bind('<Button-1>', self.on_click)

    def on_click(self, event):
        item = self.identify_row(event.y)
        if item:
            if item in self.checked_items:
                self.checked_items.remove(item)
            else:
                self.checked_items.add(item)
            self.update_display()

    def update_display(self):
        for item in self.get_children():
            tags = ('checked',) if item in self.checked_items else ()
            self.item(item, tags=tags)

    def get_checked_items(self):
        return [self.item(item, "values")[0] for item in self.checked_items]


# --- Main viewer class with new features ---
class Archimate3DViewer:
    def __init__(self):
        # Basic app state
        self.root = Tk()
        self.root.title("TOGAF ArchiMate 3D Viewer (V6)")
        self.root.geometry("1500x950")

        self.elements = {}
        self.relationships = []
        self.current_file = None
        self.selected_viewpoints = set(["All"])
        self.max_depth = 3
        self.max_objects = 1000

        self.scene_nodes = []
        self.scene_relationships = []
        self.hovered_node_id = None
        self.selected_node_ids = set()
        self.focused_node_id = None

        # New flags for features
        self.show_heatmap = False
        self.impact_scores = {}  # id -> score
        self.value_streams = {}  # id -> list of element ids
        self.active_value_stream_id = None
        self.impact_decay = 0.6  # default decay factor
        self.impact_min_display = 0.01

        # Relationship colors
        self.RELATIONSHIP_COLORS = {
            "AssignmentRelationship": (1.0, 0.6, 0.0),
            "RealizationRelationship": (0.0, 0.8, 0.8),
            "AssociationRelationship": (0.7, 0.7, 0.7),
            "CompositionRelationship": (0.5, 0.2, 0.8),
            "AggregationRelationship": (0.2, 0.8, 0.2),
            "ServingRelationship": (0.2, 0.2, 1.0),
            "AccessRelationship": (1.0, 0.2, 0.2),
            "FlowRelationship": (1.0, 1.0, 0.0),
            "TriggeringRelationship": (1.0, 0.0, 1.0),
            "SpecializationRelationship": (0.5, 0.5, 0.0),
            "UsedByRelationship": (0.0, 0.5, 0.5),
            "InfluenceRelationship": (0.8, 0.4, 0.0),
        }
        self.DEFAULT_LINK_COLOR = (1.0, 1.0, 1.0)

        self.setup_ui()

    def setup_ui(self):
        main_frame = Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = Frame(main_frame)
        left_frame.pack(side="left", fill="y", padx=(0, 10))

        middle_frame = Frame(main_frame)
        middle_frame.pack(side="left", fill="y", padx=(0, 10))

        right_frame = Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # --- File loader ---
        file_frame = Frame(left_frame)
        file_frame.pack(fill="x", pady=(0, 8))
        Button(file_frame, text="Load ArchiMate File", command=self.load_file).pack(fill="x")
        self.file_label = Label(file_frame, text="No file loaded", wraplength=260)
        self.file_label.pack(fill="x", pady=(5, 0))

        # --- Viewpoint selection ---
        viewpoint_frame = Frame(left_frame)
        viewpoint_frame.pack(fill="both", expand=True, pady=(0, 10))
        Label(viewpoint_frame, text="TOGAF Viewpoints:", font=('Arial', 10, 'bold')).pack(anchor="w")
        tree_container = Frame(viewpoint_frame)
        tree_container.pack(fill="both", expand=True, pady=(5, 0))
        self.viewpoint_tree = CheckboxTreeview(tree_container, height=10, show="tree", selectmode="none")
        self.viewpoint_tree.pack(side="left", fill="both", expand=True)
        self.viewpoint_tree.tag_configure('checked', background='lightblue')
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.viewpoint_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.viewpoint_tree.configure(yscrollcommand=scrollbar.set)
        self.populate_viewpoint_tree()
       
        # --- Control buttons ---
        control_frame = Frame(left_frame)
        control_frame.pack(fill="x", pady=(6, 10))
        Button(control_frame, text="3D Immersive View", command=self.start_immersive_view, height=2, font=('Arial', 10, 'bold')).pack(fill="x", pady=(0, 5))
        Button(control_frame, text="Reset View", command=self.reset_view, height=1).pack(fill="x", pady=(0, 5))
        Button(control_frame, text="Clear Focus", command=self.clear_focus, height=1).pack(fill="x")

        # --- Feature: Value Stream Visualisation ---
        vs_frame = Frame(left_frame)
        vs_frame.pack(fill="x", pady=(10, 6))
        Label(vs_frame, text="Value Streams:", font=('Arial', 10, 'bold')).pack(anchor="w")
        Button(vs_frame, text="Discover Value Streams", command=self.discover_value_streams).pack(fill="x", pady=(4, 2))
        self.vs_options_var = StringVar(value="None")
        vs_options_menu = OptionMenu(vs_frame, self.vs_options_var, "None")
        vs_options_menu.config(width=28)
        vs_options_menu.pack(fill="x")
        Button(vs_frame, text="Visualize Selected Value Stream", command=self.visualize_selected_value_stream).pack(fill="x", pady=(4, 0))

        # --- Feature: Impact Analysis ---
        impact_frame = Frame(left_frame)
        impact_frame.pack(fill="x", pady=(10, 6))
        Label(impact_frame, text="Impact / Driver Analysis:", font=('Arial', 10, 'bold')).pack(anchor="w")
        Label(impact_frame, text="Decay factor (0.1 - 0.95):").pack(anchor="w")
        self.decay_var = StringVar(value=str(self.impact_decay))
        self.decay_entry = Entry(impact_frame, textvariable=self.decay_var)
        self.decay_entry.pack(fill="x")
        Button(impact_frame, text="Run Impact Analysis (from focus/selected drivers)", command=self.run_impact_analysis).pack(fill="x", pady=(4, 2))
        self.heatmap_toggle_var = BooleanVar(value=False)
        Checkbutton(impact_frame, text="Show Heatmap", variable=self.heatmap_toggle_var, command=self.toggle_heatmap).pack(anchor="w", pady=(2,0))

        # --- Feature: Auto-map Process from Trigger ---
        auto_frame = Frame(left_frame)
        auto_frame.pack(fill="x", pady=(10, 6))
        Label(auto_frame, text="Auto-map from Trigger:", font=('Arial', 10, 'bold')).pack(anchor="w")
        Button(auto_frame, text="Auto-map from Focus Entity", command=self.auto_map_from_focus).pack(fill="x", pady=(4, 2))
        Button(auto_frame, text="Auto-map from Selected Entity (entity tree selection)", command=self.auto_map_from_selected_entity).pack(fill="x")

        # --- Depth and object sliders ---
        slider_frame = Frame(left_frame)
        slider_frame.pack(fill="x", pady=(10, 0))
        Label(slider_frame, text="Focus Depth:").pack(anchor="w")
        self.depth_var = StringVar(value="3")
        self.depth_scale = Scale(slider_frame, from_=1, to=10, orient=HORIZONTAL, variable=self.depth_var, command=self.on_depth_change, length=250)
        self.depth_scale.set(3)
        self.depth_scale.pack(fill="x")
        Label(slider_frame, text="Max Objects:").pack(anchor="w")
        self.objects_var = StringVar(value="1000")
        self.objects_scale = Scale(slider_frame, from_=100, to=2000, orient=HORIZONTAL, variable=self.objects_var, command=self.on_objects_change, length=250)
        self.objects_scale.set(1000)
        self.objects_scale.pack(fill="x")

        # --- Entity tree in middle frame ---
        entity_tree_frame = Frame(middle_frame)
        entity_tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        Label(entity_tree_frame, text="Archimate Entities:", font=('Arial', 10, 'bold')).pack(anchor="w")
        search_frame = Frame(entity_tree_frame)
        search_frame.pack(fill="x", pady=(5, 0))
        Label(search_frame, text="Search:").pack(side="left")
        self.search_var = StringVar()
        self.search_var.trace('w', self.on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        entity_tree_container = Frame(entity_tree_frame)
        entity_tree_container.pack(fill="both", expand=True, pady=(5, 0))
        self.entity_tree = ttk.Treeview(entity_tree_container, columns=("type", "id"), show="tree headings", height=20)
        self.entity_tree.heading("#0", text="Name")
        self.entity_tree.heading("type", text="Type")
        self.entity_tree.column("#0", width=260)
        self.entity_tree.column("type", width=120)
        entity_scrollbar = ttk.Scrollbar(entity_tree_container, orient="vertical", command=self.entity_tree.yview)
        entity_scrollbar.pack(side="right", fill="y")
        self.entity_tree.configure(yscrollcommand=entity_scrollbar.set)
        self.entity_tree.pack(side="left", fill="both", expand=True)
        self.entity_tree.bind("<Double-1>", self.on_entity_double_click)
        Button(entity_tree_frame, text="Set as Focus Entity", command=self.set_selected_entity_as_focus, height=1).pack(fill="x", pady=(5, 0))
        self.focus_label = Label(entity_tree_frame, text="No focus entity set", wraplength=320, relief="sunken", bg="lightyellow", padx=5, pady=5)
        self.focus_label.pack(fill="x", pady=(5, 0))

        # --- Info and status in right frame ---
        info_frame = Frame(right_frame)
        info_frame.pack(fill="x", pady=(0, 10))
        self.info_label = Label(info_frame, text="Select a file to begin", wraplength=860, justify="left")
        self.info_label.pack(fill="x")
        self.status_label = Label(right_frame, text="Ready", relief="sunken", anchor="w")
        self.status_label.pack(fill="x", side="bottom")
         # select all by default
        self.select_all_viewpoints()

    # --- UI helpers and tree population ---
    def populate_viewpoint_tree(self):
        for item in self.viewpoint_tree.get_children():
            self.viewpoint_tree.delete(item)
        all_item = self.viewpoint_tree.insert("", "end", text="✓ All Viewpoints", values=("All",))
        self.viewpoint_tree.checked_items.add(all_item)
        for viewpoint in TOGAF_VIEWPOINTS.keys():
            if viewpoint != "All":
                self.viewpoint_tree.insert("", "end", text=viewpoint, values=(viewpoint,))
        self.viewpoint_tree.update_display()

    def select_all_viewpoints(self):
        self.viewpoint_tree.checked_items = set(self.viewpoint_tree.get_children())
        self.viewpoint_tree.update_display()
        self.update_selected_viewpoints()

    def clear_all_viewpoints(self):
        self.viewpoint_tree.checked_items.clear()
        self.viewpoint_tree.update_display()
        self.update_selected_viewpoints()

    def update_selected_viewpoints(self):
        self.selected_viewpoints = set(self.viewpoint_tree.get_checked_items())
        if self.selected_viewpoints:
            status_text = f"Active viewpoints: {', '.join(sorted(self.selected_viewpoints))}"
        else:
            status_text = "No viewpoints selected"
        self.status_label.config(text=status_text)
        if self.elements:
            filtered_count = len(self.get_filtered_elements())
            self.info_label.config(text=f"Active viewpoints: {', '.join(sorted(self.selected_viewpoints))}. Showing {filtered_count} of {len(self.elements)} elements.")
            self.populate_entity_tree()
            self.clear_focus()

    def populate_entity_tree(self):
        for item in self.entity_tree.get_children():
            self.entity_tree.delete(item)
        if not self.elements:
            return
        filtered_elements = self.get_filtered_elements()
        elements_by_type = {}
        for elem_id, elem in filtered_elements.items():
            elem_type = self._strip_archimate_prefix(elem['type'])
            if elem_type.endswith('Relationship'):
                continue
            elements_by_type.setdefault(elem_type, []).append(elem)
        sorted_types = sorted(elements_by_type.keys())
        for elem_type in sorted_types:
            type_node = self.entity_tree.insert("", "end", text=f"{elem_type} ({len(elements_by_type[elem_type])})", values=("", ""))
            for elem in sorted(elements_by_type[elem_type], key=lambda x: x['name']):
                display_name = self._strip_archimate_prefix(elem['name'])
                self.entity_tree.insert(type_node, "end", text=display_name, values=(elem_type, elem['id']))
        for child in self.entity_tree.get_children():
            self.entity_tree.item(child, open=True)

    def _strip_archimate_prefix(self, text):
        if text.startswith('archimate:'):
            return text[10:]
        return text

    def on_search_changed(self, *args):
        search_term = self.search_var.get().lower()
        if not search_term:
            for child in self.entity_tree.get_children():
                self.entity_tree.item(child, open=True)
                for grandchild in self.entity_tree.get_children(child):
                    self.entity_tree.item(grandchild, open=True)
            return
        for child in self.entity_tree.get_children():
            self.entity_tree.item(child, open=False)
            for grandchild in self.entity_tree.get_children(child):
                self.entity_tree.item(grandchild, open=False)
        for child in self.entity_tree.get_children():
            child_text = self.entity_tree.item(child, "text").lower()
            if search_term in child_text:
                self.entity_tree.item(child, open=True)
                continue
            has_matching_children = False
            for grandchild in self.entity_tree.get_children(child):
                grandchild_text = self.entity_tree.item(grandchild, "text").lower()
                if search_term in grandchild_text:
                    has_matching_children = True
                    self.entity_tree.item(grandchild, open=True)
            if has_matching_children:
                self.entity_tree.item(child, open=True)

    def on_entity_double_click(self, event):
        item = self.entity_tree.selection()[0] if self.entity_tree.selection() else None
        if item:
            values = self.entity_tree.item(item, "values")
            if len(values) >= 2 and values[1]:
                self.set_focus_entity(values[1])

    def set_selected_entity_as_focus(self):
        item = self.entity_tree.selection()[0] if self.entity_tree.selection() else None
        if item:
            values = self.entity_tree.item(item, "values")
            if len(values) >= 2 and values[1]:
                self.set_focus_entity(values[1])
            else:
                messagebox.showinfo("Info", "Please select a specific entity (not a category)")
        else:
            messagebox.showinfo("Info", "Please select an entity from the tree")

    def set_focus_entity(self, element_id):
        if element_id in self.elements:
            self.focused_node_id = element_id
            elem = self.elements[element_id]
            display_name = self._strip_archimate_prefix(elem['name'])
            display_type = self._strip_archimate_prefix(elem['type'])
            self.focus_label.config(text=f"Focus: {display_name} ({display_type})")
            self.status_label.config(text=f"Focus set to: {display_name}")
            print(f"Focus set to: {display_name} ({display_type})")
        else:
            messagebox.showerror("Error", "Selected entity not found in current viewpoint")

    def on_depth_change(self, value):
        self.max_depth = int(value)
        self.status_label.config(text=f"Focus depth: {self.max_depth}")
        if self.scene_nodes:
            self.update_focus_dimming()

    def on_objects_change(self, value):
        self.max_objects = int(value)
        self.status_label.config(text=f"Max objects: {self.max_objects}")

    # --- File parsing / model building (robust) ---
    def load_file(self):
        file_path = filedialog.askopenfilename(title="Select ArchiMate File", filetypes=[("XML files", "*.xml"), ("ArchiMate files", "*.archimate"), ("All files", "*.*")])
        if file_path:
            try:
                self.parse_archimate_file(file_path)
                self.current_file = file_path
                filename = os.path.basename(file_path)
                self.file_label.config(text=filename)
                filtered_count = len(self.get_filtered_elements())
                viewpoint_status = ', '.join(sorted(self.selected_viewpoints))
                self.info_label.config(text=f"Loaded {len(self.elements)} elements and {len(self.relationships)} relationships from {filename}. Active viewpoints: {viewpoint_status}. Showing {filtered_count} elements.")
                self.status_label.config(text="File loaded successfully")
                self.calculate_relationship_counts()
                self.populate_entity_tree()
            except Exception as e:
                error_msg = f"Failed to load file: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                messagebox.showerror("Error", error_msg)

    def parse_archimate_file(self, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        self.elements = {}
        self.relationships = []
        # Remove namespace prefixes
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
            for attr in list(elem.attrib.keys()):
                if '}' in attr:
                    new_attr = attr.split('}', 1)[1]
                    elem.attrib[new_attr] = elem.attrib[attr]
                    del elem.attrib[attr]
        elements_parsed = 0
        for elem in root.findall('.//element'):
            element_data = self._parse_element(elem)
            if element_data:
                self.elements[element_data['id']] = element_data
                elements_parsed += 1
        relationships_parsed = 0
        for rel in root.findall('.//relationship'):
            relationship_data = self._parse_relationship(rel)
            if relationship_data:
                self.relationships.append(relationship_data)
                relationships_parsed += 1
        relations_folder = root.find('.//folder[@type="relations"]')
        if relations_folder is not None:
            for rel_elem in relations_folder.findall('element'):
                relationship_data = self._parse_relationship(rel_elem)
                if relationship_data and not self._relationship_exists(relationship_data):
                    self.relationships.append(relationship_data)
                    relationships_parsed += 1
        self._build_relationship_networks()
        print(f"Parsed {elements_parsed} elements and {relationships_parsed} relationships")
        if not self.elements:
            raise Exception("No elements found in the file.")

    def _parse_element(self, elem):
        elem_id = elem.get('id')
        if not elem_id:
            return None
        elem_type = elem.get('type')
        if not elem_type:
            return None
        elem_name = elem.get('name', 'Unnamed')
        documentation_elem = elem.find('documentation')
        documentation = documentation_elem.text if documentation_elem is not None else ""
        return {'id': elem_id, 'name': elem_name, 'type': elem_type, 'documentation': documentation, 'relationships': {'in': [], 'out': []}}

    def _parse_relationship(self, rel):
        rel_id = rel.get('id')
        rel_type = rel.get('type')
        source = rel.get('source')
        target = rel.get('target')
        if not all([rel_id, rel_type, source, target]):
            return None
        documentation_elem = rel.find('documentation')
        documentation = documentation_elem.text if documentation_elem is not None else ""
        return {'id': rel_id, 'type': rel_type, 'source': source, 'target': target, 'documentation': documentation}

    def _relationship_exists(self, relationship_data):
        for rel in self.relationships:
            if (rel['source'] == relationship_data['source'] and rel['target'] == relationship_data['target'] and rel['type'] == relationship_data['type']):
                return True
        return False

    def _build_relationship_networks(self):
        for rel in self.relationships:
            source_id = rel['source']
            target_id = rel['target']
            if source_id in self.elements:
                self.elements[source_id]['relationships']['out'].append(rel)
            else:
                print(f"Warning: Relationship source element not found: {source_id}")
            if target_id in self.elements:
                self.elements[target_id]['relationships']['in'].append(rel)
            else:
                print(f"Warning: Relationship target element not found: {target_id}")

    def calculate_relationship_counts(self):
        for elem_id, elem in self.elements.items():
            elem['relationship_count'] = len(elem['relationships']['in']) + len(elem['relationships']['out'])

    def get_filtered_elements(self):
        if "All" in self.selected_viewpoints:
            return self.elements
        allowed_types = set()
        for viewpoint in self.selected_viewpoints:
            if viewpoint in TOGAF_VIEWPOINTS:
                allowed_types.update(TOGAF_VIEWPOINTS[viewpoint])
        filtered_elements = {}
        for elem_id, elem in self.elements.items():
            if elem['type'] in allowed_types:
                filtered_elements[elem_id] = elem
        return filtered_elements

    def get_layer_for_element(self, element_type):
        folder = FOLDER_MAP.get(element_type, "")
        folder_to_layer = {
            "Business": "Business",
            "Application": "Application",
            "Technology & Physical": "Technology",
            "Motivation": "Motivation",
            "Strategy": "Strategy",
            "Implementation & Migration": "Implementation",
            "Views": "Business",
            "Other": "Business"
        }
        layer = folder_to_layer.get(folder, "Business")
        if not folder:
            element_type_lower = element_type.lower()
            if any(x in element_type_lower for x in ["business"]):
                return "Business"
            elif any(x in element_type_lower for x in ["application"]):
                return "Application"
            elif any(x in element_type_lower for x in ["technology", "node", "device", "systemsoftware", "artifact"]):
                return "Technology"
            elif any(x in element_type_lower for x in ["stakeholder", "driver", "goal", "requirement", "principle", "assessment"]):
                return "Motivation"
            elif any(x in element_type_lower for x in ["resource", "capability", "value", "courseofaction"]):
                return "Strategy"
            elif any(x in element_type_lower for x in ["workpackage", "deliverable", "implementation", "plateau"]):
                return "Implementation"
            elif any(x in element_type_lower for x in ["equipment", "facility", "material", "distribution"]):
                return "Physical"
        return layer

    def get_color_for_layer(self, layer):
        return ARCHITECTURE_LAYERS.get(layer, {}).get("color", (0.8, 0.8, 0.8))

    # --- Hierarchical layout (extended to support path and value stream layouts) ---
    def build_hierarchical_layout(self, layout_mode="hierarchical", path_nodes=None, vs_nodes=None):
        """
        layout_mode: "hierarchical" (default), "path", "value_stream"
        path_nodes: ordered list of element ids for path layout (auto-map)
        vs_nodes: set/list of element ids to highlight for value stream
        """
        filtered_elements = self.get_filtered_elements()
        if not filtered_elements:
            self.scene_nodes = []
            self.scene_relationships = []
            return [], []

        self.scene_nodes = []
        self.scene_relationships = []

        # pick focus if absent
        if not self.focused_node_id:
            for elem_id, elem in filtered_elements.items():
                if elem.get('relationship_count', 0) > 0:
                    self.focused_node_id = elem_id
                    break
            if not self.focused_node_id and filtered_elements:
                self.focused_node_id = list(filtered_elements.keys())[0]
        if not self.focused_node_id:
            return [], []

        # default: place focus center
        focus_elem = filtered_elements[self.focused_node_id]
        focus_layer = self.get_layer_for_element(focus_elem['type'])
        focus_color = self.get_color_for_layer(focus_layer)
        focus_node = SceneNode(self, self.focused_node_id, np.array([0, 0, 0]), 1.0, focus_color, focus_elem['name'], focus_elem['type'], focus_layer)
        self.scene_nodes.append(focus_node)
        plotted_elements = {self.focused_node_id}

        # For path layout (auto-map) if provided: place nodes along an arc in order
        if layout_mode == "path" and path_nodes:
            total = len(path_nodes)
            radius = max(6.0, total * 2.0)
            for idx, eid in enumerate(path_nodes):
                if eid not in filtered_elements:
                    continue
                angle = (idx / max(1, total - 1)) * math.pi - math.pi/2  # -90..+90
                x = radius * math.cos(angle)
                y = - (idx - total/2) * 0.8
                z = radius * 0.2 * math.sin(angle)
                elem = filtered_elements[eid]
                layer = self.get_layer_for_element(elem['type'])
                color = self.get_color_for_layer(layer)
                size = 0.9 if eid != self.focused_node_id else 1.1
                node = SceneNode(self, eid, np.array([x, y, z]), size, color, elem['name'], elem['type'], layer)
                node.path_index = idx
                self.scene_nodes.append(node)
                plotted_elements.add(eid)
            # create tubes for consecutive nodes in path
            for i in range(len(self.scene_nodes) - 1):
                a = self.scene_nodes[i]
                b = self.scene_nodes[i + 1]
                rel_color = (0.9, 0.9, 0.4)
                tube = RelationshipTube(self, a.pos, b.pos, rel_color, "PathStepRelationship", radius=0.03, strength=1.0)
                self.scene_relationships.append(tube)
            # Create normal relationships that exist between path nodes as well
            self.create_relationship_tubes()
            for node in self.scene_nodes:
                node.create_textures()
            return self.scene_nodes, self.scene_relationships

        # Value stream layout: if vs_nodes provided, place them along a left->right flow
        if layout_mode == "value_stream" and vs_nodes:
            vs_list = list(vs_nodes)
            total = len(vs_list)
            left_x = -18
            right_x = 18
            for idx, eid in enumerate(vs_list):
                if eid not in filtered_elements:
                    continue
                t = idx / max(1, total - 1) if total > 1 else 0.5
                x = left_x + (right_x - left_x) * t
                y = math.sin(t * math.pi) * 6
                z = (t - 0.5) * 8 * 0.4
                elem = filtered_elements[eid]
                layer = self.get_layer_for_element(elem['type'])
                color = self.get_color_for_layer(layer)
                node = SceneNode(self, eid, np.array([x, y, z]), 0.9, color, elem['name'], elem['type'], layer)
                self.scene_nodes.append(node)
                plotted_elements.add(eid)
            # connect sequentially left->right
            for i in range(len(self.scene_nodes) - 1):
                a = self.scene_nodes[i]
                b = self.scene_nodes[i + 1]
                rel_color = (0.9, 0.6, 0.1)
                tube = RelationshipTube(self, a.pos, b.pos, rel_color, "ValueStreamStep", radius=0.04)
                self.scene_relationships.append(tube)
            # add surrounding related elements (inputs to the first, outputs from last) sparsely
            self.create_relationship_tubes()
            for node in self.scene_nodes:
                node.create_textures()
            return self.scene_nodes, self.scene_relationships

        # Default hierarchical placement (inputs left, outputs right) - similar to v5
        input_relationships = focus_elem['relationships']['in']
        output_relationships = focus_elem['relationships']['out']
        self.place_related_elements(input_relationships, 'source', -1, plotted_elements, filtered_elements, 1)
        self.place_related_elements(output_relationships, 'target', 1, plotted_elements, filtered_elements, 1)
        self.create_relationship_tubes()
        for node in self.scene_nodes:
            node.create_textures()
        return self.scene_nodes, self.scene_relationships

    def place_related_elements(self, relationships, direction_key, x_direction, plotted_elements, filtered_elements, depth):
        if depth > self.max_depth or not relationships:
            return
        elements_to_place = []
        for rel in relationships:
            elem_id = rel[direction_key]
            if elem_id in filtered_elements and elem_id not in plotted_elements:
                elements_to_place.append(elem_id)
                plotted_elements.add(elem_id)
        if not elements_to_place:
            return
        radius = depth * 8.0 * 0.6
        angle_step = math.pi / (len(elements_to_place) + 1)
        for i, elem_id in enumerate(elements_to_place):
            elem = filtered_elements[elem_id]
            layer = self.get_layer_for_element(elem['type'])
            color = self.get_color_for_layer(layer)
            angle = (i + 1) * angle_step - math.pi/2
            x = x_direction * radius
            y = math.sin(angle) * radius * 0.7
            z = math.cos(angle) * radius * 0.5
            node = SceneNode(self, elem_id, np.array([x, y, z]), 0.8, color, elem['name'], elem['type'], layer)
            self.scene_nodes.append(node)
            # recursively place next level
            if depth < 2:
                next_relationships = elem['relationships']['in'] if direction_key == 'source' else elem['relationships']['out']
                self.place_related_elements(next_relationships, direction_key, x_direction, plotted_elements, filtered_elements, depth + 1)

    def create_relationship_tubes(self):
        relationship_count = 0
        node_map = {node.id: node for node in self.scene_nodes}
        for rel in self.relationships:
            if RELATIONSHIP_TYPES and rel['type'] not in RELATIONSHIP_TYPES:
                continue
            source_node = node_map.get(rel['source'])
            target_node = node_map.get(rel['target'])
            if source_node and target_node:
                # USE THE SAME TRIMMED TYPE FOR COLOR LOOKUP
                trimmed_type = self._strip_archimate_prefix(rel['type'])
                rel_color = self.RELATIONSHIP_COLORS.get(trimmed_type, self.DEFAULT_LINK_COLOR)
                # determine strength (used by impact visualization) default 1.0
                strength = 1.0
                tube = RelationshipTube(self, source_node.pos, target_node.pos, rel_color, rel['type'], radius=0.04, strength=strength)
                self.scene_relationships.append(tube)
                relationship_count += 1
                if relationship_count >= self.max_objects:
                    print(f"Limited relationships to {self.max_objects}")
                    break

    # --- Related elements exploration utilities ---
    def find_related_elements(self, start_element_id, max_depth):
        if start_element_id not in self.elements:
            return set()
        visited = set()
        to_visit = [(start_element_id, 0)]
        related_elements = set()
        while to_visit:
            current_id, depth = to_visit.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            related_elements.add(current_id)
            if depth < max_depth:
                for rel in self.elements[current_id]['relationships']['out']:
                    to_visit.append((rel['target'], depth + 1))
                for rel in self.elements[current_id]['relationships']['in']:
                    to_visit.append((rel['source'], depth + 1))
        return related_elements

    def update_focus_dimming(self):
        if not self.focused_node_id:
            for node in self.scene_nodes:
                node.set_dimmed(False)
            for rel in self.scene_relationships:
                rel.set_dimmed(False)
            return
        focused_elements = self.find_related_elements(self.focused_node_id, self.max_depth)
        for node in self.scene_nodes:
            node.set_dimmed(node.id not in focused_elements)
        # for relationships dim if either end dimmed (simple check)
        for rel in self.scene_relationships:
            # map start_pos/end_pos to node ids by position - approximate
            start_dimmed = True
            target_dimmed = True
            for n in self.scene_nodes:
                if np.allclose(n.pos, rel.start_pos, atol=1e-4):
                    start_dimmed = n.is_dimmed
                if np.allclose(n.pos, rel.end_pos, atol=1e-4):
                    target_dimmed = n.is_dimmed
            rel.set_dimmed(start_dimmed or target_dimmed)

    def clear_focus(self):
        self.focused_node_id = None
        self.selected_node_ids.clear()
        self.focus_label.config(text="No focus entity set")
        if self.scene_nodes:
            self.update_focus_dimming()
        self.status_label.config(text="Focus cleared")
        # reset impact/heatmap state
        self.show_heatmap = False
        self.impact_scores = {}
        self.value_streams = {}
        self.active_value_stream_id = None

    def reset_view(self):
        self.clear_focus()
        if self.elements:
            self.build_hierarchical_layout()
            self.status_label.config(text="View reset to hierarchical layout")

    # --- Immersive 3D view and main render loop (extended HUD + heatmap legend) ---
    def start_immersive_view(self):
        if not self.elements:
            messagebox.showwarning("Warning", "Please load an ArchiMate file first.")
            return
        try:
            print("Starting pre-rendering phase...")
            # build default layout
            self.build_hierarchical_layout()
            if not self.scene_nodes:
                messagebox.showwarning("Warning", f"No elements to display for viewpoints: {self.selected_viewpoints}")
                return
            pygame.init()
            display = (1280, 860)
            screen = pygame.display.set_mode(display, DOUBLEBUF | OPENGL | RESIZABLE)
            pygame.display.set_caption(f"TOGAF 3D Viewer V6 - {', '.join(sorted(self.selected_viewpoints))}")
            # recreate textures now that pygame is initialized
            for node in self.scene_nodes:
                node.textures_created = False
                node.create_textures()
            for rel in self.scene_relationships:
                rel.create_texture()
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glClearColor(0.05, 0.05, 0.1, 1.0)
            # Don't enable lighting at all for consistent colors
            glDisable(GL_LIGHTING)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45, display[0] / display[1], 0.1, 500.0)
            glMatrixMode(GL_MODELVIEW)
            cam_dist = 40.0
            yaw = math.radians(0)
            pitch = math.radians(10)
            orbit_center = np.array([0.0, 0.0, 0.0])
            clock = pygame.time.Clock()
            running = True
            last_mouse_pos = None
            is_rotating = False
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_r:
                            cam_dist = 40.0
                            yaw = math.radians(0)
                            pitch = math.radians(10)
                        elif event.key == pygame.K_c:
                            self.clear_focus()
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            mouse_pos = pygame.mouse.get_pos()
                            selected_id = self.raycast_select(mouse_pos, display)
                            if selected_id:
                                self.focused_node_id = selected_id
                                self.build_hierarchical_layout()
                                print(f"Focused on: {self.elements[selected_id]['name']}")
                        elif event.button == 3:
                            is_rotating = True
                            last_mouse_pos = event.pos
                        elif event.button == 4:
                            cam_dist = max(5.0, cam_dist * 0.9)
                        elif event.button == 5:
                            cam_dist = min(200.0, cam_dist * 1.1)
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 3:
                            is_rotating = False
                            last_mouse_pos = None
                    elif event.type == pygame.MOUSEMOTION:
                        if is_rotating and last_mouse_pos:
                            dx, dy = event.pos[0] - last_mouse_pos[0], event.pos[1] - last_mouse_pos[1]
                            yaw += dx * 0.005
                            pitch = max(-math.pi/2 + 0.01, min(math.pi/2 - 0.01, pitch - dy * 0.005))
                            last_mouse_pos = event.pos
                
                # Clear the screen
                glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
                glLoadIdentity()
                
                # Set up camera
                cam_x = orbit_center[0] + cam_dist * math.cos(yaw) * math.cos(pitch)
                cam_y = orbit_center[1] + cam_dist * math.sin(pitch)
                cam_z = orbit_center[2] + cam_dist * math.sin(yaw) * math.cos(pitch)
                gluLookAt(cam_x, cam_y, cam_z, orbit_center[0], orbit_center[1], orbit_center[2], 0, 1, 0)
                
                # Render all objects (lighting is disabled for consistent colors)
                for rel in self.scene_relationships:
                    rel.render()
                
                for node in self.scene_nodes:
                    node.update_vertices()
                    node.render()
                
                # Render HUD using pygame (2D overlay)
                self._render_hud(screen, display)
                
                pygame.display.flip()
                clock.tick(60)
            
            pygame.quit()
            print("3D viewer closed")
            
        except Exception as e:
            print(f"Error in 3D viewer: {e}")
            traceback.print_exc()
            try:
                pygame.quit()
            except:
                pass

    def _render_hud(self, screen, display):
        """Render HUD overlay using pygame"""
        # Create HUD surface
        hud = pygame.Surface(display, pygame.SRCALPHA)
        
        # Create fonts
        font = pygame.font.SysFont('Arial', 14)
        small_font = pygame.font.SysFont('Arial', 12)
        
        # Legend
        focus_name = self._strip_archimate_prefix(self.elements[self.focused_node_id]['name']) if self.focused_node_id else 'None'
        legend_text = f"Nodes: {len(self.scene_nodes)}  Relationships: {len(self.scene_relationships)}  Focus: {focus_name}"
        t_surf = font.render(legend_text, True, (255,255,255))
        hud.blit(t_surf, (8, 8))
        
        # Heatmap legend
        if self.show_heatmap:
            hud.blit(small_font.render("Heatmap (low → high):", True, (255,255,255)), (8, 34))
            for i in range(11):
                s = i/10.0
                r = int((0.2 + 0.8*s)*255)
                g = int(max(0.2, (1.0-s)*0.9)*255)
                b = int(max(0.2, (1.0-s)*0.9)*255)
                pygame.draw.rect(hud, (r,g,b), (160 + i*14, 34, 12, 12))
        
        # Instructions
        hud.blit(small_font.render("Left click: focus. Right drag: rotate. Mouse wheel: zoom. R: reset camera. C: clear focus", True, (200,200,200)), (8, 60))
        
        # Blit HUD to screen
        screen.blit(hud, (0,0))

    def raycast_select(self, mouse_pos, display):
        if not self.scene_nodes:
            return None
        try:
            viewport = glGetIntegerv(GL_VIEWPORT)
            modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
            projection = glGetDoublev(GL_PROJECTION_MATRIX)
            win_x, win_y = mouse_pos
            win_y = viewport[3] - win_y
            closest_node = None
            closest_dist = float('inf')
            for node in self.scene_nodes:
                obj_x, obj_y, obj_z = node.pos
                win_pos = gluProject(obj_x, obj_y, obj_z, modelview, projection, viewport)
                if win_pos:
                    dist = math.sqrt((win_x - win_pos[0])**2 + (win_y - win_pos[1])**2)
                    if dist < 30 and dist < closest_dist:
                        closest_dist = dist
                        closest_node = node
            return closest_node.id if closest_node else None
        except Exception as e:
            print(f"Error in raycast: {e}")
            return None

    # --- New: Value stream discovery and visualisation ---
    def discover_value_streams(self):
        """Collect ValueStream elements and related elements (simple territory expansion)"""
        self.value_streams = {}
        for eid, elem in self.elements.items():
            typ = self._strip_archimate_prefix(elem['type'])
            if typ.lower() == "valuestream" or "ValueStream" in elem['type']:
                # find connected elements (two hops)
                connected = self.find_related_elements(eid, 2)
                self.value_streams[eid] = connected
        if not self.value_streams:
            messagebox.showinfo("Value Streams", "No ValueStream elements found in the model.")
            return
        # populate option menu
        menu = None
        for child in self.root.children.values():
            pass
        # update OptionMenu widget (we have vs_options_var and an OptionMenu in setup_ui)
        # We need to find the OptionMenu widget to update choices - but simpler: rebuild menu by searching widgets
        for widget in self.root.winfo_children():
            pass
        # Replace the OptionMenu by setting its menu
        # find option menu in left frame by traversing
        def update_menu():
            for w in self.root.winfo_children():
                for child in w.winfo_children():
                    for g in child.winfo_children():
                        if isinstance(g, OptionMenu) and g.cget("textvariable") == str(self.vs_options_var):
                            menu = g["menu"]
                            menu.delete(0, "end")
                            menu.add_command(label="None", command=lambda v="None": self.vs_options_var.set(v))
                            for vsid in self.value_streams.keys():
                                name = self._strip_archimate_prefix(self.elements[vsid]['name'])
                                label = f"{name} ({vsid})"
                                menu.add_command(label=label, command=lambda v=vsid: self.vs_options_var.set(v))
                            return
        update_menu()
        self.status_label.config(text=f"Discovered {len(self.value_streams)} value streams")

    def visualize_selected_value_stream(self):
        selected = self.vs_options_var.get()
        if not selected or selected == "None":
            messagebox.showinfo("Value Stream", "Please choose a discovered ValueStream first (Discover Value Streams).")
            return
        if selected not in self.value_streams:
            messagebox.showerror("Value Stream", "Selected value stream not available.")
            return
        vs_nodes = self.value_streams[selected]
        # Build a layout that places value stream nodes left->right
        self.active_value_stream_id = selected
        self.build_hierarchical_layout(layout_mode="value_stream", vs_nodes=vs_nodes)
        self.status_label.config(text=f"Visualised ValueStream: {self._strip_archimate_prefix(self.elements[selected]['name'])}")

    # --- New: Impact / Driver Analysis ---
    def run_impact_analysis(self):
        """
        Run propagation from driver(s) or focus:
        - If focus element is a Driver or user selected Driver elements -> start from them
        - Otherwise start from focus element as a trigger
        Propagate through relationships with decay.
        """
        # parse decay factor
        try:
            decay = float(self.decay_var.get())
            if not (0.05 <= decay < 1.0):
                raise ValueError()
            self.impact_decay = decay
        except Exception:
            messagebox.showerror("Input error", "Decay factor must be a number between 0.05 and 0.95")
            return
        # determine seed nodes: drivers if selected in tree, else focused element
        seed_nodes = set()
        # check entity tree selection for drivers
        sel = self.entity_tree.selection()
        for item in sel:
            vals = self.entity_tree.item(item, "values")
            if len(vals) >= 2 and vals[1]:
                eid = vals[1]
                if self._strip_archimate_prefix(self.elements[eid]['type']).lower() == "driver":
                    seed_nodes.add(eid)
        # if none found, use focused element
        if not seed_nodes and self.focused_node_id:
            seed_nodes.add(self.focused_node_id)
        if not seed_nodes:
            messagebox.showinfo("Impact Analysis", "No driver or focused element to start from. Set focus or select Driver(s) in the entities list.")
            return
        # BFS/propagation with decay and relationship weighting
        weights = {
            'InfluenceRelationship': 1.0,
            'TriggeringRelationship': 0.9,
            'FlowRelationship': 0.8,
            'ServingRelationship': 0.6,
            'AccessRelationship': 0.5,
            'UsedByRelationship': 0.5,
            'AssignmentRelationship': 0.3,
            'CompositionRelationship': 0.4,
            'AssociationRelationship': 0.2,
            'RealizationRelationship': 0.4,
        }
        # initialize scores
        scores = {eid: 0.0 for eid in self.elements.keys()}
        # queue of (node, strength)
        from collections import deque
        q = deque()
        for s in seed_nodes:
            scores[s] = 1.0
            q.append((s, 1.0))
        visited_depth = {s: 0 for s in seed_nodes}
        max_steps = 6  # avoid runaway
        while q:
            node_id, strength = q.popleft()
            depth = visited_depth.get(node_id, 0)
            if depth >= max_steps:
                continue
            # propagate along outgoing relationships first (driver influences)
            for rel in self.elements[node_id]['relationships']['out']:
                tgt = rel['target']
                if tgt not in scores:
                    continue
                rtype = rel['type'].split('}')[-1] if '}' in rel['type'] else rel['type']
                weight = weights.get(rtype, 0.25)
                propagated = strength * weight * self.impact_decay
                if propagated < self.impact_min_display:
                    continue
                # accumulate (max of previous and propagated to avoid overcounting many weak paths)
                new_score = scores[tgt] + propagated
                if new_score > scores[tgt] + 1e-9:
                    scores[tgt] = new_score
                # push forward
                if propagated > 0.01:
                    # set depth
                    nd = depth + 1
                    if visited_depth.get(tgt, 999) > nd:
                        visited_depth[tgt] = nd
                        q.append((tgt, propagated))
            # propagate inbound too (influence may be bidirectional)
            for rel in self.elements[node_id]['relationships']['in']:
                src = rel['source']
                if src not in scores:
                    continue
                rtype = rel['type'].split('}')[-1] if '}' in rel['type'] else rel['type']
                weight = weights.get(rtype, 0.25)
                propagated = strength * weight * self.impact_decay * 0.5
                if propagated < self.impact_min_display:
                    continue
                new_score = scores[src] + propagated
                if new_score > scores[src] + 1e-9:
                    scores[src] = new_score
                if propagated > 0.01:
                    nd = depth + 1
                    if visited_depth.get(src, 999) > nd:
                        visited_depth[src] = nd
                        q.append((src, propagated))
        # normalise scores 0..1
        max_score = max(scores.values()) if scores else 1.0
        if max_score <= 0:
            # nothing to show
            self.impact_scores = {}
            messagebox.showinfo("Impact Analysis", "No propagating impact found with current decay/settings.")
            return
        for k in scores:
            scores[k] = scores[k] / max_score
        self.impact_scores = scores
        # mark results into scene nodes (rebuild layout to show current focus surrounding)
        self.show_heatmap = True if self.heatmap_toggle_var.get() else False
        # apply scores to node objects if they exist in scene_nodes; else rebuild scene and map
        for node in self.scene_nodes:
            node.impact_score = self.impact_scores.get(node.id, 0.0)
        # also increase relationship thickness where both ends have high scores
        for rel in self.scene_relationships:
            # find start and end ids by matching positions (be tolerant)
            start_id = None
            end_id = None
            for n in self.scene_nodes:
                if np.allclose(n.pos, rel.start_pos, atol=1e-4):
                    start_id = n.id
                if np.allclose(n.pos, rel.end_pos, atol=1e-4):
                    end_id = n.id
            if start_id and end_id:
                rel_strength = (self.impact_scores.get(start_id, 0.0) + self.impact_scores.get(end_id, 0.0)) / 2.0
                rel.strength = rel_strength
        self.status_label.config(text=f"Impact analysis complete (seeds: {len(seed_nodes)}, decay={self.impact_decay})")
        # refresh textures if running viewer
        for node in self.scene_nodes:
            node.create_textures()

    def toggle_heatmap(self):
        self.show_heatmap = bool(self.heatmap_toggle_var.get())
        # update node display
        for node in self.scene_nodes:
            node.create_textures()

    # --- New: Auto-map process from trigger ---
    def auto_map_from_focus(self):
        if not self.focused_node_id:
            messagebox.showinfo("Auto-map", "Set a focus entity first (double click an entity or choose from tree and 'Set as Focus Entity').")
            return
        path = self.extract_process_path_from_trigger(self.focused_node_id, max_steps=20)
        if not path:
            messagebox.showinfo("Auto-map", "No process path found from the focused element.")
            return
        self.build_hierarchical_layout(layout_mode="path", path_nodes=path)
        self.status_label.config(text=f"Auto-mapped process path from focus ({len(path)} steps)")

    def auto_map_from_selected_entity(self):
        item = self.entity_tree.selection()[0] if self.entity_tree.selection() else None
        if not item:
            messagebox.showinfo("Auto-map", "Please select an entity in the entity tree first.")
            return
        values = self.entity_tree.item(item, "values")
        if len(values) >= 2 and values[1]:
            eid = values[1]
            path = self.extract_process_path_from_trigger(eid, max_steps=20)
            if not path:
                messagebox.showinfo("Auto-map", "No process path found from the selected entity.")
                return
            self.build_hierarchical_layout(layout_mode="path", path_nodes=path)
            self.status_label.config(text=f"Auto-mapped process path from selected entity ({len(path)} steps)")
        else:
            messagebox.showinfo("Auto-map", "Please select a concrete entity (not a category).")

    def extract_process_path_from_trigger(self, start_eid, max_steps=50):
        """
        Heuristic to extract a process chain starting from a 'trigger' element:
        - prefer outgoing TriggeringRelationship and FlowRelationship
        - follow the chain greedily (choose next node with highest outgoing trigger/flow degree)
        - stop when no further steps or cycle detected
        """
        if start_eid not in self.elements:
            return []
        path = [start_eid]
        visited = set(path)
        current = start_eid
        steps = 0
        while steps < max_steps:
            steps += 1
            candidates = []
            # prefer explicit TriggeringRelationship and FlowRelationship
            for rel in self.elements[current]['relationships']['out']:
                rtype = rel['type'].split('}')[-1] if '}' in rel['type'] else rel['type']
                if 'Trigger' in rtype or 'Flow' in rtype or 'UsedBy' in rtype or 'Serving' in rtype:
                    tgt = rel['target']
                    if tgt not in visited:
                        candidates.append((rtype, tgt))
            # fallback to any outgoing if none found
            if not candidates:
                for rel in self.elements[current]['relationships']['out']:
                    tgt = rel['target']
                    if tgt not in visited:
                        candidates.append((rel['type'], tgt))
            if not candidates:
                break
            # choose candidate with highest connectivity (naive heuristic)
            best = None
            best_score = -1
            for rtype, tgt in candidates:
                outdeg = len(self.elements.get(tgt, {}).get('relationships', {}).get('out', []))
                indeg = len(self.elements.get(tgt, {}).get('relationships', {}).get('in', []))
                score = outdeg + indeg
                if score > best_score:
                    best_score = score
                    best = tgt
            if not best or best in visited:
                break
            path.append(best)
            visited.add(best)
            current = best
        return path

    # --- Run the Tk mainloop ---
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    viewer = Archimate3DViewer()
    viewer.run()
