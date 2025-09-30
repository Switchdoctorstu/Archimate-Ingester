8.3 is the current working version.

Opens .archimate files.
Allows entitie sto be explores
Allows entities and relationships to be added via LLM queries.

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

from ThreeDViewer import ThreeDViewer
import google.generativeai as genai # You may need to run: pip install google-generativeai
from config import FOLDER_MAP, COMMON_TYPES, RELATIONSHIP_TYPES, RELATIONSHIP_RULES, AUTOCOMPLETE_RULES
