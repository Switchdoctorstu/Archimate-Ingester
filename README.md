# -- Archimate Ingester
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
