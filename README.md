# -- Archimate Toolset 

Prompt builder - Builds LLM prompts to explore an organisation and output archimate entities in JSON format
JSON Ingester - Adds new JSON elements to Archimate files
Viewer - Explore the model
Modeller - Look for insights.


launcher should run the code 

Use Builder to generate LLM Prompts
Use ingester to get them into your model
Use Viewer to look at them


* Opens .archimate files.
* Allows entities to be explored
* Allows entities and relationships to be added via LLM queries.
* Cleans files
* Saves new Versions.

 ---- Imports ----
 
import tkinter as tk
import numpy
import xml.etree.ElementTree as ET

import uuid

import copy

import os
