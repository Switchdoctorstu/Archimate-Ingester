# -- Archimate Ingester
8.3 is the current working version.

* Opens .archimate files.
* Allows entities to be explored
* Allows entities and relationships to be added via LLM queries.
* Cleans files
* Saves new Versions.

 ---- Imports ----
 
import tkinter as tk

import xml.etree.ElementTree as ET

import uuid

import copy

import os

from xml.dom import minidom

import datetime

from ThreeDViewer import ThreeDViewer

import google.generativeai as genai 

from config import FOLDER_MAP, COMMON_TYPES, RELATIONSHIP_TYPES, RELATIONSHIP_RULES, AUTOCOMPLETE_RULES
