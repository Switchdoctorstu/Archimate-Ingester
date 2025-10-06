import pygame
import math
import numpy as np
from tkinter import messagebox
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import xml.etree.ElementTree as ET
import uuid
import copy
import os
from config import FOLDER_MAP, RELATIONSHIP_TYPES, XSI

# --- 3D Scene Object Classes ---

class SceneNode:
    """Represents a single oblong element in the 3D view."""
    # Static geometry definitions to avoid recalculation
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

    def __init__(self, viewer, node_id, pos, size, color, label, element_type):
        self.viewer = viewer
        self.id = node_id
        self.pos = pos
        self.size = size
        self.color = color
        self.label = label
        self.element_type = element_type
        
        # Pre-render the text texture for the element name
        if self.label:
            self.name_tex_id, self.name_tex_width, self.name_tex_height = self.viewer.make_text_texture(
                self.label, font_size=18, color=(255, 255, 255)
            )
        else:
            self.name_tex_id = None

        # Pre-render the text texture for the element type
        if self.element_type:
            self.type_tex_id, self.type_tex_width, self.type_tex_height = self.viewer.make_text_texture(
                f"<{self.element_type}>", font_size=14, color=(200, 200, 200)
            )
        else:
            self.type_tex_id = None

    def cleanup(self):
        """Releases the GPU resources (texture) used by this object."""
        if self.name_tex_id:
            glDeleteTextures(1, [self.name_tex_id])
            self.name_tex_id = None
        if self.type_tex_id:
            glDeleteTextures(1, [self.type_tex_id])
            self.type_tex_id = None

    def render(self, is_hovered=False):
        """Draws the oblong and its label in the scene."""
        x, y, z = self.pos
        
        # --- Draw the oblong shape ---
        vertices = [
            [x + vx * self.size, y + vy * self.size, z + vz * self.size]
            for vx, vy, vz in self.OBLONG_VERTICES
        ]
        glColor3f(*self.color)
        glBegin(GL_QUADS)
        for face in self.OBLONG_FACES:
            for vertex_index in face:
                glVertex3fv(vertices[vertex_index])
        glEnd()

        # --- Draw edges (highlighted if hovered) ---
        if is_hovered:
            glColor3f(1.0, 1.0, 1.0)
            glLineWidth(3.0)
        else:
            glColor3f(1.0, 1.0, 0.0)
            glLineWidth(1.5)
        glBegin(GL_LINES)
        for edge in self.OBLONG_EDGES:
            for vertex_index in edge:
                glVertex3fv(vertices[vertex_index])
        glEnd()

        # --- Draw the pre-rendered labels ---
        if self.name_tex_id:
            self._render_name_label(x, y, z)
        if self.type_tex_id:
            self._render_type_label(x, y, z)

    def _render_name_label(self, x, y, z):
        """Renders the pre-created texture onto the front/back faces."""
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.name_tex_id)
        glColor3f(1, 1, 1)

        # Calculate quad size to fit text inside the oblong face
        oblong_width, oblong_height = 2 * self.size, 1 * self.size
        margin = 0.1 * self.size
        tex_aspect = self.name_tex_width / self.name_tex_height if self.name_tex_height > 0 else 1.0
        max_text_width, max_text_height = oblong_width - 2 * margin, oblong_height - 2 * margin

        if max_text_width / tex_aspect <= max_text_height:
            quad_width, quad_height = max_text_width, max_text_width / tex_aspect
        else:
            quad_height, quad_width = max_text_height, max_text_height * tex_aspect

        left, right = x - quad_width / 2, x + quad_width / 2
        bottom, top = y - quad_height / 2, y + quad_height / 2
        
        # Front Face (CCW winding)
        z_front = z + 0.5 * self.size + 0.01
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(left, bottom, z_front)
        glTexCoord2f(1, 0); glVertex3f(right, bottom, z_front)
        glTexCoord2f(1, 1); glVertex3f(right, top, z_front)
        glTexCoord2f(0, 1); glVertex3f(left, top, z_front)
        glEnd()

        # Back Face (readable from behind, CCW winding)
        z_back = z - 0.5 * self.size - 0.01
        glBegin(GL_QUADS)
        # Flipped the horizontal (U) texture coordinates to prevent mirroring
        glTexCoord2f(1, 0); glVertex3f(left, bottom, z_back)
        glTexCoord2f(0, 0); glVertex3f(right, bottom, z_back)
        glTexCoord2f(0, 1); glVertex3f(right, top, z_back)
        glTexCoord2f(1, 1); glVertex3f(left, top, z_back)
        glEnd()

        glDisable(GL_TEXTURE_2D)

    def _render_type_label(self, x, y, z):
        """Renders the pre-created texture onto the top face."""
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.type_tex_id)
        glColor3f(0.8, 0.8, 0.8) # Dim the type label slightly

        # Calculate quad size to fit text on the top face
        top_face_width, top_face_depth = 2 * self.size, 1 * self.size
        margin = 0.1 * self.size
        tex_aspect = self.type_tex_width / self.type_tex_height if self.type_tex_height > 0 else 1.0
        max_text_width, max_text_height = top_face_width - 2 * margin, top_face_depth - 2 * margin

        if max_text_width / tex_aspect <= max_text_height:
            quad_width, quad_height = max_text_width, max_text_width / tex_aspect
        else:
            quad_height, quad_width = max_text_height, max_text_height * tex_aspect

        left, right = x - quad_width / 2, x + quad_width / 2
        front, back = z + quad_height / 2, z - quad_height / 2
        y_top = y + 0.5 * self.size + 0.01 # Offset to prevent z-fighting

        glBegin(GL_QUADS)
        # Corrected texture coordinates to make text visible and upright
        # Vertices are wound CCW when viewed from above (+Y)
        glTexCoord2f(0, 0); glVertex3f(left, y_top, front)    # Front-left corner gets bottom-left of texture
        glTexCoord2f(1, 0); glVertex3f(right, y_top, front)   # Front-right corner gets bottom-right of texture
        glTexCoord2f(1, 1); glVertex3f(right, y_top, back)    # Back-right corner gets top-right of texture
        glTexCoord2f(0, 1); glVertex3f(left, y_top, back)     # Back-left corner gets top-left of texture
        glEnd()

        glDisable(GL_TEXTURE_2D)

class RelationshipTube:
    """Represents a single relationship as a 3D tube."""
    def __init__(self, viewer, start_pos, end_pos, color, rel_type, radius=0.03, sides=8):
        self.viewer = viewer
        self.start_pos = np.array(start_pos)
        self.end_pos = np.array(end_pos)
        self.color = color
        self.rel_type = rel_type
        self.radius = radius
        self.sides = sides
        self.quadric = gluNewQuadric()

    def cleanup(self):
        """Releases any GPU resources used by this object."""
        gluDeleteQuadric(self.quadric)

    def render(self):
        """Draws the tube and its label in the scene."""
        # --- Draw the Tube ---
        glColor3f(*self.color)
        
        direction = self.end_pos - self.start_pos
        length = np.linalg.norm(direction)
        if length < 1e-6: return # Avoid division by zero

        direction /= length

        # --- Calculate rotation to align the cylinder with the direction vector ---
        # The default cylinder in OpenGL is along the Z-axis.
        # We need to find the rotation from (0,0,1) to our direction vector.
        z_axis = np.array([0.0, 0.0, 1.0])
        axis = np.cross(z_axis, direction)
        angle = np.degrees(np.arccos(np.dot(z_axis, direction)))

        # --- Use OpenGL matrix stack to position and orient the tube ---
        glPushMatrix()
        glTranslatef(self.start_pos[0], self.start_pos[1], self.start_pos[2])
        if np.linalg.norm(axis) > 1e-6:
            glRotatef(angle, axis[0], axis[1], axis[2])
        
        # Draw the cylinder
        gluCylinder(self.quadric, self.radius, self.radius, length, self.sides, 1)
        
        glPopMatrix()

        # --- Draw the Label ---
        self._render_label()

    def _render_label(self):
        """Renders the relationship type aligned with the tube."""
        tex_info = self.viewer.relationship_label_textures.get(self.rel_type)
        if not tex_info:
            return
        
        tex_id, tex_width, tex_height = tex_info
        
        # --- Quad and Position Calculation ---
        line_vec = self.end_pos - self.start_pos
        length = np.linalg.norm(line_vec)
        if length < 1e-6: return
        line_forward = line_vec / length

        # Define quad size based on texture aspect ratio, scaled to be readable
        tex_aspect = tex_width / tex_height if tex_height > 0 else 1.0
        quad_h = 0.2  # Fixed height for the label quad
        quad_w = quad_h * tex_aspect

        # --- Determine text orientation ---
        up_reference = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(line_forward, up_reference)) > 0.99:
            up_reference = np.array([1.0, 0.0, 0.0])

        text_up = up_reference - np.dot(up_reference, line_forward) * line_forward
        norm = np.linalg.norm(text_up)
        if norm < 1e-6: return
        text_up /= norm

        # --- Position and calculate corners ---
        mid_point = (self.start_pos + self.end_pos) / 2.0
        label_center = mid_point + text_up * (self.radius + 0.05)

        half_w_vec = line_forward * (quad_w / 2)
        half_h_vec = text_up * (quad_h / 2)

        p1 = label_center - half_w_vec - half_h_vec
        p2 = label_center + half_w_vec - half_h_vec
        p3 = label_center + half_w_vec + half_h_vec
        p4 = label_center - half_w_vec + half_h_vec

        # --- Render Quad with the pre-rendered text texture ---
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glColor3f(1, 1, 1) # Set color to white to show texture as-is

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3fv(p1)
        glTexCoord2f(1, 0); glVertex3fv(p2)
        glTexCoord2f(1, 1); glVertex3fv(p3)
        glTexCoord2f(0, 1); glVertex3fv(p4)
        glEnd()

        glDisable(GL_TEXTURE_2D)


class ThreeDViewer:
    def __init__(self, controller):
        self.controller = controller # The main ArchiIngestorApp instance
        self.RELATIONSHIP_COLORS = {
            "AssignmentRelationship": (1.0, 0.6, 0.0),      # Orange
            "RealizationRelationship": (0.0, 0.8, 0.8),     # Cyan
            "AssociationRelationship": (0.7, 0.7, 0.7),     # Light gray
            "CompositionRelationship": (0.5, 0.2, 0.8),     # Purple
            "AggregationRelationship": (0.2, 0.8, 0.2),     # Green
            "ServingRelationship": (0.2, 0.2, 1.0),         # Blue
            "AccessRelationship": (1.0, 0.2, 0.2),          # Red
            "FlowRelationship": (1.0, 1.0, 0.0),            # Yellow
            "TriggeringRelationship": (1.0, 0.0, 1.0),      # Magenta
            "SpecializationRelationship": (0.5, 0.5, 0.0),  # Olive
            "UsedByRelationship": (0.0, 0.5, 0.5),          # Teal
            "InfluenceRelationship": (0.8, 0.4, 0.0),       # Brown
        }
        self.DEFAULT_LINK_COLOR = (1.0, 1.0, 1.0)  # White
        self.relationship_label_textures = {} # Cache for pre-rendered labels

    # --- Geometry drawing methods are now part of the SceneNode class ---
    # --- Cube Geometry Definitions (kept for potential future use) ---
    CUBE_VERTICES = [
        [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5], [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5],
        [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5], [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5],
    ]
    CUBE_FACES = [
        [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6],
        [1, 2, 6, 5], [0, 3, 7, 4],
    ]
    CUBE_EDGES = [
        (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6),
        (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)
    ]

    def draw_cube(self, x=0, y=0, z=0, size=1.0, color=(1, 0, 0), label="", is_hovered=False):
        # This method is no longer used by the main 3D view but is kept for now.
        hs = size / 2.0
        vertices = [[x + v[0] * size, y + v[1] * size, z + v[2] * size] for v in self.CUBE_VERTICES]
        glColor3f(*color)
        glBegin(GL_QUADS)
        for face in self.CUBE_FACES:
            for vertex in face:
                glVertex3fv(vertices[vertex])
        glEnd()
        if is_hovered:
            glColor3f(1.0, 1.0, 1.0)
            glLineWidth(3.0)
        else:
            glColor3f(1.0, 1.0, 0.0)
            glLineWidth(1.5)
        glBegin(GL_LINES)
        for edge in self.CUBE_EDGES:
            for vertex in edge:
                glVertex3fv(vertices[vertex])
        glEnd()

    def get_color_for_type(self, element_type):
        """Returns an (R, G, B) color tuple for the given element type string."""
        layer_colors = {
            "Business": (0.2, 0.6, 1.0), "Application": (0.2, 1.0, 0.6),
            "Technology & Physical": (1.0, 0.7, 0.2), "Motivation": (0.8, 0.2, 0.8),
            "Strategy": (1.0, 0.4, 0.4), "Implementation & Migration": (0.6, 0.6, 0.6),
            "Other": (0.8, 0.8, 0.8),
        }
        folder_name = FOLDER_MAP.get(element_type, "Other")
        return layer_colors.get(folder_name, (0.8, 0.8, 0.8))

    def get_layer_color(self, el_id):
        """Returns an (R, G, B) color tuple for the given element ID based on its type/folder."""
        el = self.controller.find_element_by_id(el_id)
        if el is None: return (0.5, 0.5, 0.5)
        etype_full = el.get(f"{{{XSI}}}type", "")
        etype = etype_full.split(":")[-1] if ":" in etype_full else etype_full
        return self.get_color_for_type(etype)
    
    def _build_recursive_layout(self, node_id, position, depth, max_depth, visited_nodes, scene_nodes, scene_relationships):
        """Recursively builds lists of SceneNode and RelationshipTube objects."""
        if depth > max_depth or node_id in visited_nodes:
            return

        visited_nodes[node_id] = position
        el = self.controller.find_element_by_id(node_id)
        if not el: return
        
        name = el.get("name", "Unknown")
        etype_full = el.get(f"{{{XSI}}}type", "")
        etype = etype_full.split(":")[-1] if ":" in etype_full else etype_full
        size = max(0.3, 1.0 - depth * 0.25)
        color = self.get_color_for_type(etype)
        scene_nodes.append(SceneNode(self, node_id, position, size, color, name, etype))

        if depth == max_depth: return

        rels = self.controller.get_element_relationships(node_id)
        
        def layout_children(child_rels, direction):
            total_children = len(child_rels)
            if total_children == 0: return
            golden_ratio = (1 + 5**0.5) / 2
            base_radius = (5.0 / (1.2**depth)) + (total_children // 8) * 0.5

            for i, rel_data in enumerate(child_rels):
                child_id = rel_data['id']
                line_color = self.RELATIONSHIP_COLORS.get(rel_data['type'], self.DEFAULT_LINK_COLOR)

                if child_id in visited_nodes:
                    child_pos = visited_nodes[child_id]
                    start, end = (child_pos, position) if direction == 'in' else (position, child_pos)
                    scene_relationships.append(RelationshipTube(self, start, end, line_color, rel_data['type']))
                    continue

                phi = math.acos(1 - 2 * (i + 0.5) / total_children)
                theta = 2 * math.pi * i / golden_ratio
                child_counts = self.controller.relationship_counts.get(child_id, {'in': 0, 'out': 0})
                radius = base_radius + min(1.5, (child_counts['in'] + child_counts['out']) / 10.0)
                rel_x = radius * abs(math.cos(theta) * math.sin(phi))
                rel_y = radius * math.sin(theta) * math.sin(phi)
                rel_z = radius * math.cos(phi)
                rel_x = -rel_x if direction == 'in' else rel_x
                child_pos = position + np.array([rel_x, rel_y, rel_z])

                start, end = (child_pos, position) if direction == 'in' else (position, child_pos)
                scene_relationships.append(RelationshipTube(self, start, end, line_color, rel_data['type']))
                self._build_recursive_layout(child_id, child_pos, depth + 1, max_depth, visited_nodes, scene_nodes, scene_relationships)

        layout_children([r for r in rels if r['direction'] == 'out'], 'out')
        layout_children([r for r in rels if r['direction'] == 'in'], 'in')

    def _get_ray_from_mouse(self, mouse_pos):
        """Calculates a 3D ray from a 2D mouse position."""
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        winX, winY = float(mouse_pos[0]), float(viewport[3] - mouse_pos[1])
        near_point = gluUnProject(winX, winY, 0.0, modelview, projection, viewport)
        far_point = gluUnProject(winX, winY, 1.0, modelview, projection, viewport)
        ray_origin = np.array(near_point)
        ray_direction = np.array(far_point) - ray_origin
        ray_direction /= np.linalg.norm(ray_direction)
        return ray_origin, ray_direction

    def _ray_intersects_aabb(self, ray_origin, ray_direction, aabb_min, aabb_max):
        """Checks for intersection between a ray and an Axis-Aligned Bounding Box (AABB)."""
        t_min, t_max = 0.0, float('inf')
        for i in range(3):
            if abs(ray_direction[i]) < 1e-6:
                if ray_origin[i] < aabb_min[i] or ray_origin[i] > aabb_max[i]:
                    return False, 0.0
            else:
                t1 = (aabb_min[i] - ray_origin[i]) / ray_direction[i]
                t2 = (aabb_max[i] - ray_origin[i]) / ray_direction[i]
                if t1 > t2: t1, t2 = t2, t1
                t_min, t_max = max(t_min, t1), min(t_max, t2)
                if t_min > t_max: return False, 0.0
        return True, t_min

    def show_staged_3d_preview(self):
        """Shows a simple, interactive 3D preview of the elements and relationships currently defined in the Paste Area."""
        # This function remains largely unchanged as it uses a simpler, non-OO rendering path.
        paste_content = self.controller.paste_text.get("1.0", "end").strip()
        if not paste_content:
            messagebox.showinfo("3D Preview", "Paste Area is empty.")
            return

        lines = [l.strip() for l in paste_content.splitlines() if l.strip() and not l.startswith("#")]
        staged_elements, staged_relationships = {}, []
        for ln in lines:
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) < 2: continue
            raw_type, short_type = parts[0], parts[0].split(":")[-1]
            if short_type.endswith("Relationship") or short_type in RELATIONSHIP_TYPES:
                src_name = parts[1]
                extras = {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in parts[2:] if "=" in p)}
                tgt_name = extras.get("target")
                if src_name and tgt_name:
                    staged_relationships.append({'type': short_type, 'source': src_name, 'target': tgt_name})
            else:
                name = parts[1]
                if name: staged_elements[name] = {'type': short_type}
        if not staged_elements:
            messagebox.showinfo("3D Preview", "No valid elements found in Paste Area to preview.")
            return

        element_positions = {}
        element_list = list(staged_elements.keys())
        n = len(element_list)
        radius = max(2.0, n / 1.5)
        for i, name in enumerate(element_list):
            angle = 2 * math.pi * i / n
            x, y, z = radius * math.cos(angle), 0, radius * math.sin(angle)
            element_positions[name] = np.array([x, y, z])

        pygame.init()
        display = (800, 600)
        pygame.display.set_mode(display, DOUBLEBUF | OPENGL | RESIZABLE)
        pygame.display.set_caption("Staged 3D Preview")
        glEnable(GL_DEPTH_TEST); glEnable(GL_TEXTURE_2D); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.1, 0.1, 0.1, 1)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(45, display[0] / display[1], 0.1, 150.0)
        glMatrixMode(GL_MODELVIEW)

        cam_dist, yaw, pitch = 5.0 + n, math.radians(-90), math.radians(20)
        last_mouse_pos, is_rotating = None, False
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1: is_rotating, last_mouse_pos = True, event.pos
                    elif event.button == 4: cam_dist = max(2.0, cam_dist * 0.9)
                    elif event.button == 5: cam_dist *= 1.1
                elif event.type == MOUSEBUTTONUP:
                    if event.button == 1: is_rotating, last_mouse_pos = False, None
                elif event.type == MOUSEMOTION:
                    if is_rotating and last_mouse_pos:
                        dx, dy = event.pos[0] - last_mouse_pos[0], event.pos[1] - last_mouse_pos[1]
                        yaw += dx * 0.005
                        pitch = max(-math.pi/2 + 0.01, min(math.pi/2 - 0.01, pitch - dy * 0.005))
                        last_mouse_pos = event.pos
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT); glLoadIdentity()
            eye_x = cam_dist * math.cos(pitch) * math.cos(yaw)
            eye_y = cam_dist * math.sin(pitch)
            eye_z = cam_dist * math.cos(pitch) * math.sin(yaw)
            gluLookAt(eye_x, eye_y, eye_z, 0, 0, 0, 0, 1, 0)
            
            # Create temporary SceneNode objects for rendering this preview
            temp_nodes = [SceneNode(self, name, pos, 0.8, self.get_color_for_type(data['type']), name, data['type']) for name, (pos, data) in zip(staged_elements.keys(), zip(element_positions.values(), staged_elements.values()))]
            for node in temp_nodes: node.render(is_hovered=False)
            
            glLineWidth(2.0); glBegin(GL_LINES)
            for rel in staged_relationships:
                if rel['source'] in element_positions and rel['target'] in element_positions:
                    start_pos, end_pos = element_positions[rel['source']], element_positions[rel['target']]
                    glColor3f(*self.RELATIONSHIP_COLORS.get(rel['type'], self.DEFAULT_LINK_COLOR))
                    glVertex3fv(start_pos); glVertex3fv(end_pos)
            glEnd()
            pygame.display.flip(); pygame.time.wait(10)
        
        # Cleanup temporary node textures
        for node in temp_nodes: node.cleanup()
        pygame.quit()

    def show_3d_view(self, max_depth):
        sel = self.controller.treeview.selection()
        if not sel:
            messagebox.showinfo("3D View", "Select a node in the tree first.")
            return
        node = sel[0]
        vals = self.controller.treeview.item(node, "values")
        if not vals or vals[0] != "element":
            messagebox.showinfo("3D View", "Select an element node.")
            return
        el_id = vals[1]

        pygame.init()
        display = (800, 600)
        pygame.display.set_mode(display, DOUBLEBUF | OPENGL | RESIZABLE)
        pygame.display.set_caption("3D View")

        glEnable(GL_DEPTH_TEST); glEnable(GL_TEXTURE_2D); glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.1, 0.1, 0.1, 1)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(45, display[0] / display[1], 0.1, 150.0)
        glMatrixMode(GL_MODELVIEW)

        # --- Scene and Camera State ---
        scene_nodes, scene_relationships = [], []
        cam_dist, yaw, pitch = 15.0, math.radians(-90), math.radians(20)
        orbit_center = np.array([0.0, 0.0, 0.0])
        last_mouse_pos, hovered_node_id = None, None
        last_click_time = 0
        double_click_threshold = 300

        # Pre-render relationship labels for performance
        for rel_type in self.RELATIONSHIP_COLORS.keys():
            label_text = rel_type.replace("Relationship", "")
            tex_id, w, h = self.make_text_texture(label_text, font_size=16, color=(255, 255, 255))
            self.relationship_label_textures[rel_type] = (tex_id, w, h)

        def build_scene(start_node_id):
            """Cleans up old scene and builds a new one."""
            nonlocal scene_nodes, scene_relationships
            for node in scene_nodes: node.cleanup()
            for rel in scene_relationships: rel.cleanup()
            scene_nodes, scene_relationships = [], []
            visited_nodes = {}
            self._build_recursive_layout(start_node_id, np.array([0.0, 0.0, 0.0]), 0, max_depth, visited_nodes, scene_nodes, scene_relationships)

        build_scene(el_id) # Initial scene build

        eye_x = orbit_center[0] + cam_dist * math.cos(pitch) * math.cos(yaw)
        eye_y = orbit_center[1] + cam_dist * math.sin(pitch)
        eye_z = orbit_center[2] + cam_dist * math.cos(pitch) * math.sin(yaw)
        eye_position = np.array([eye_x, eye_y, eye_z])
        
        running = True
        while running:
            left_pressed, _, right_pressed = pygame.mouse.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == MOUSEBUTTONDOWN:
                    if event.button in [1, 3]: last_mouse_pos = event.pos
                    if event.button == 1:
                        current_time = pygame.time.get_ticks()
                        if hovered_node_id and (current_time - last_click_time) < double_click_threshold:
                            build_scene(hovered_node_id)
                            orbit_center = np.array([0.0, 0.0, 0.0])
                            eye_x = orbit_center[0] + cam_dist * math.cos(pitch) * math.cos(yaw)
                            eye_y = orbit_center[1] + cam_dist * math.sin(pitch)
                            eye_z = orbit_center[2] + cam_dist * math.cos(pitch) * math.sin(yaw)
                            eye_position = np.array([eye_x, eye_y, eye_z])
                            last_click_time = 0
                        else:
                            last_click_time = current_time
                    elif event.button == 4 or event.button == 5:
                        zoom_factor = 0.9 if event.button == 4 else 1.1
                        direction_to_eye = eye_position - orbit_center
                        if np.linalg.norm(direction_to_eye) < 0.1 and zoom_factor < 1.0: continue
                        eye_position = orbit_center + direction_to_eye * zoom_factor
                elif event.type == MOUSEBUTTONUP:
                    if not pygame.mouse.get_pressed()[0] and not pygame.mouse.get_pressed()[2]:
                        last_mouse_pos = None
                elif event.type == MOUSEMOTION:
                    if last_mouse_pos:
                        dx, dy = event.pos[0] - last_mouse_pos[0], event.pos[1] - last_mouse_pos[1]
                        if left_pressed and right_pressed:
                            modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
                            cam_right = np.array([modelview[0][0], modelview[1][0], modelview[2][0]])
                            cam_up = np.array([modelview[0][1], modelview[1][1], modelview[2][1]])
                            dist_to_center = max(1.0, np.linalg.norm(eye_position - orbit_center))
                            pan_speed = 0.003 * dist_to_center
                            pan_vector = (cam_right * -dx * pan_speed) + (cam_up * dy * pan_speed)
                            eye_position += pan_vector; orbit_center += pan_vector
                        elif right_pressed:
                            yaw += dx * 0.005
                            pitch = max(-math.pi/2 + 0.01, min(math.pi/2 - 0.01, pitch - dy * 0.005))
                            current_dist = np.linalg.norm(eye_position - orbit_center)
                            eye_x = orbit_center[0] + current_dist * math.cos(pitch) * math.cos(yaw)
                            eye_y = orbit_center[1] + current_dist * math.sin(pitch)
                            eye_z = orbit_center[2] + current_dist * math.cos(pitch) * math.sin(yaw)
                            eye_position = np.array([eye_x, eye_y, eye_z])
                        elif left_pressed:
                            yaw += dx * 0.005
                            pitch = max(-math.pi/2 + 0.01, min(math.pi/2 - 0.01, pitch - dy * 0.005))
                        last_mouse_pos = event.pos

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT); glLoadIdentity()
            cam_forward = np.array([math.cos(pitch) * math.cos(yaw), math.sin(pitch), math.cos(pitch) * math.sin(yaw)])
            look_at_point = eye_position - cam_forward
            gluLookAt(eye_position[0], eye_position[1], eye_position[2], look_at_point[0], look_at_point[1], look_at_point[2], 0, 1, 0)

            if not left_pressed and not right_pressed:
                mouse_pos = pygame.mouse.get_pos()
                ray_origin, ray_direction = self._get_ray_from_mouse(mouse_pos)
                closest_dist = float('inf'); found_node_id = None
                for node in scene_nodes:
                    aabb_min = node.pos - np.array([node.size, 0.5 * node.size, 0.5 * node.size])
                    aabb_max = node.pos + np.array([node.size, 0.5 * node.size, 0.5 * node.size])
                    intersects, dist = self._ray_intersects_aabb(ray_origin, ray_direction, aabb_min, aabb_max)
                    if intersects and dist >= 0 and dist < closest_dist:
                        closest_dist, found_node_id = dist, node.id
                hovered_node_id = found_node_id

            # --- Render the entire scene ---
            for rel in scene_relationships: rel.render()
            for node in scene_nodes: node.render(is_hovered=(node.id == hovered_node_id))
            
            pygame.display.flip(); pygame.time.wait(10)
        
        # --- Final cleanup of all scene objects ---
        for tex_id, _, _ in self.relationship_label_textures.values():
            glDeleteTextures(1, [tex_id])
        self.relationship_label_textures.clear()

        for node in scene_nodes: node.cleanup()
        for rel in scene_relationships: rel.cleanup()
        pygame.quit()

    def make_text_texture(self, text, font_size=24, color=(255, 255, 255)):
        """Creates an OpenGL texture from a string of text with a transparent background."""
        try:
            font = pygame.font.Font(None, font_size)
        except Exception:
            font = pygame.font.Font(pygame.font.get_default_font(), font_size)
        # The render function without a background argument creates a transparent surface
        text_surface = font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        width, height = text_surface.get_width(), text_surface.get_height()
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        return tex_id, width, height
