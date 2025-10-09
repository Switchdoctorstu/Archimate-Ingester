# ---- Configuration Data for ArchiMate Ingestor ----

XSI = "http://www.w3.org/2001/XMLSchema-instance"
ARCHIMATE = "http://www.archimatetool.com/archimate"


# Map ArchiMate element short types to Folder name
FOLDER_MAP = {
    # Business
    "BusinessActor": "Business",
    "BusinessRole": "Business",
    "BusinessCollaboration": "Business",
    "BusinessEvent": "Business",
    "BusinessProcess": "Business",
    "BusinessFunction": "Business",
    "BusinessInteraction": "Business",
    "BusinessService": "Business",
    "BusinessObject": "Business",
    "BusinessInterface": "Business",
    "BusinessContract": "Business",
    "BusinessRepresentation": "Business",
    # Application
    "ApplicationComponent": "Application",
    "ApplicationCollaboration": "Application",
    "ApplicationInterface": "Application",
    "ApplicationService": "Application",
    "ApplicationFunction": "Application",
    "ApplicationProcess": "Application",
    "ApplicationInteraction": "Application",
    "ApplicationEvent": "Application",
    "DataObject": "Application",
    # Technology & Physical
    "Node": "Technology & Physical",
    "Device": "Technology & Physical",
    "SystemSoftware": "Technology & Physical",
    "TechnologyInterface": "Technology & Physical",
    "TechnologyService": "Technology & Physical",
    "Artifact": "Technology & Physical",
    # Motivation
    "Stakeholder": "Motivation",
    "Driver": "Motivation",
    "Goal": "Motivation",
    "Outcome": "Motivation",
    "Assessment": "Motivation",
    "Principle": "Motivation",
    "Requirement": "Motivation",
    "Constraint": "Motivation",
    # Strategy
    "Capability": "Strategy",
    "CourseOfAction": "Strategy",
    "ValueStream": "Strategy",
    "Resource": "Strategy",
    # Implementation & Migration
    "WorkPackage": "Implementation & Migration",
    "Deliverable": "Implementation & Migration",
    "Plateau": "Implementation & Migration"
}

COMMON_TYPES = [
    "Stakeholder", "Requirement", "Goal", "Driver", "Outcome",
    "BusinessActor", "BusinessRole", "BusinessCollaboration", "BusinessInterface", "BusinessProcess", "BusinessFunction", "BusinessService",
    "ApplicationComponent", "ApplicationService", "ApplicationInterface", "DataObject",
    "Node", "Device", "SystemSoftware", "TechnologyService",
    "Capability", "ValueStream",
    "WorkPackage", "Deliverable"
]

RELATIONSHIP_TYPES = set([
    "AssignmentRelationship","RealizationRelationship","AssociationRelationship",
    "CompositionRelationship","AggregationRelationship","ServingRelationship",
    "AccessRelationship","FlowRelationship","TriggeringRelationship",
    "SpecializationRelationship","UsedByRelationship","InfluenceRelationship"
])

# Add relationship validation rules
# Add relationship validation rules
RELATIONSHIP_RULES = {
    # Strategy elements
    "Capability": {
        "allowed_targets": {
            "RealizationRelationship": ["Goal", "Requirement", "Outcome", "CourseOfAction"],
            "ServingRelationship": ["BusinessActor", "BusinessRole"],
            "CompositionRelationship": ["Capability"],
            "AggregationRelationship": ["Capability"],
            "InfluenceRelationship": ["Goal", "Principle", "Requirement"],
            "AssociationRelationship": ["*"]
        }
    },
    "CourseOfAction": {
        "allowed_targets": {
            "RealizationRelationship": ["Capability", "Goal"],
            "ServingRelationship": ["BusinessActor", "BusinessRole"],
            "CompositionRelationship": ["CourseOfAction"],
            "AggregationRelationship": ["CourseOfAction"],
            "AssociationRelationship": ["*"]
        }
    },
    "ValueStream": {
        "allowed_targets": {
            "CompositionRelationship": ["ValueStream"],
            "AggregationRelationship": ["ValueStream"],
            "RealizationRelationship": ["BusinessProcess", "BusinessFunction"],
            "AssociationRelationship": ["*"]
        }
    },
    "Resource": {
        "allowed_targets": {
            "RealizationRelationship": ["BusinessObject", "DataObject", "Artifact"],
            "CompositionRelationship": ["Resource"],
            "AggregationRelationship": ["Resource"],
            "AssociationRelationship": ["*"]
        }
    },
    # Motivation elements
    "Stakeholder": {
        "allowed_targets": {
            "InfluenceRelationship": ["Goal", "Driver", "Requirement"],
            "AssignmentRelationship": ["BusinessActor", "BusinessRole"],
            "AssociationRelationship": ["*"]
        }
    },
    "Driver": {
        "allowed_targets": {
            "InfluenceRelationship": ["Goal", "Assessment", "Requirement"],
            "AssociationRelationship": ["*"]
        }
    },
    "Assessment": {
        "allowed_targets": {
            "InfluenceRelationship": ["Driver", "Goal"],
            "AssociationRelationship": ["*"]
        }
    },
    "Goal": {
        "allowed_targets": {
            "RealizationRelationship": ["Outcome", "Capability"],
            "InfluenceRelationship": ["Goal", "Principle", "Requirement"],
            "CompositionRelationship": ["Goal"],
            "AggregationRelationship": ["Goal"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["Goal"]
        }
    },
    "Outcome": {
        "allowed_targets": {
            "RealizationRelationship": ["Capability"],
            "InfluenceRelationship": ["Goal"],
            "AssociationRelationship": ["*"]
        }
    },
    "Principle": {
        "allowed_targets": {
            "InfluenceRelationship": ["Goal", "Requirement", "Constraint"],
            "AssociationRelationship": ["*"]
        }
    },
    "Requirement": {
        "allowed_targets": {
            "RealizationRelationship": ["ApplicationService", "TechnologyService", "BusinessService", "Capability", "CourseOfAction"],
            "InfluenceRelationship": ["Goal", "Principle", "Requirement"],
            "CompositionRelationship": ["Requirement"],
            "AggregationRelationship": ["Requirement"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["Requirement"]
        }
    },
    "Constraint": {
        "allowed_targets": {
            "InfluenceRelationship": ["Goal", "Requirement", "Principle"],
            "AssociationRelationship": ["*"]
        }
    },
    # Business elements
    "BusinessActor": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessActor", "BusinessRole", "BusinessProcess", "BusinessFunction"],
            "UsedByRelationship": ["BusinessProcess", "BusinessFunction"],
            "CompositionRelationship": ["BusinessActor", "BusinessRole"],
            "AggregationRelationship": ["BusinessActor", "BusinessRole"],
            "AssignmentRelationship": ["BusinessRole"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["BusinessActor"]
        }
    },
    "BusinessRole": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessActor", "BusinessRole", "BusinessProcess", "BusinessFunction"],
            "UsedByRelationship": ["BusinessProcess", "BusinessFunction"],
            "CompositionRelationship": ["BusinessRole"],
            "AggregationRelationship": ["BusinessRole"],
            "AssignmentRelationship": ["BusinessActor"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["BusinessRole"]
        }
    },
    "BusinessCollaboration": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessProcess", "BusinessFunction"],
            "CompositionRelationship": ["BusinessActor", "BusinessRole"],
            "AggregationRelationship": ["BusinessActor", "BusinessRole"],
            "AssociationRelationship": ["*"]
        }
    },
    "BusinessInterface": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessActor", "BusinessRole", "BusinessProcess"],
            "AssignmentRelationship": ["BusinessService"],
            "CompositionRelationship": ["BusinessActor", "BusinessRole"],
            "AssociationRelationship": ["*"]
        }
    },
    "BusinessProcess": {
        "allowed_targets": {
            "UsedByRelationship": ["BusinessActor", "BusinessRole"],
            "ServingRelationship": ["BusinessActor", "BusinessRole"],
            "AccessRelationship": ["BusinessObject"],
            "FlowRelationship": ["BusinessProcess", "BusinessFunction"],
            "TriggeringRelationship": ["BusinessProcess", "BusinessFunction", "BusinessEvent"],
            "CompositionRelationship": ["BusinessProcess", "BusinessFunction"],
            "AggregationRelationship": ["BusinessProcess", "BusinessFunction"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["BusinessProcess"]
        }
    },
    "BusinessFunction": {
        "allowed_targets": {
            "UsedByRelationship": ["BusinessActor", "BusinessRole"],
            "ServingRelationship": ["BusinessActor", "BusinessRole"],
            "AccessRelationship": ["BusinessObject"],
            "FlowRelationship": ["BusinessProcess", "BusinessFunction"],
            "TriggeringRelationship": ["BusinessProcess", "BusinessFunction", "BusinessEvent"],
            "CompositionRelationship": ["BusinessFunction"],
            "AggregationRelationship": ["BusinessFunction"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["BusinessFunction"]
        }
    },
    "BusinessInteraction": {
        "allowed_targets": {
            "FlowRelationship": ["BusinessProcess", "BusinessFunction", "BusinessInteraction"],
            "TriggeringRelationship": ["BusinessProcess", "BusinessFunction", "BusinessEvent"],
            "AssociationRelationship": ["*"]
        }
    },
    "BusinessEvent": {
        "allowed_targets": {
            "TriggeringRelationship": ["BusinessProcess", "BusinessFunction"],
            "AssociationRelationship": ["*"]
        }
    },
    "BusinessService": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessActor", "BusinessRole", "BusinessProcess"],
            "RealizationRelationship": ["ApplicationService", "BusinessProcess", "BusinessFunction"],
            "AccessRelationship": ["BusinessObject"],
            "CompositionRelationship": ["BusinessService"],
            "AggregationRelationship": ["BusinessService"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["BusinessService"]
        }
    },
    "BusinessObject": {
        "allowed_targets": {
            "AccessRelationship": ["BusinessProcess", "BusinessFunction", "BusinessService"],
            "RealizationRelationship": ["DataObject"],
            "CompositionRelationship": ["BusinessObject"],
            "AggregationRelationship": ["BusinessObject"],
            "AssociationRelationship": ["*"]
        }
    },
    "BusinessContract": {
        "allowed_targets": {
            "AccessRelationship": ["BusinessProcess", "BusinessFunction"],
            "AssociationRelationship": ["*"]
        }
    },
    "BusinessRepresentation": {
        "allowed_targets": {
            "AccessRelationship": ["BusinessObject"],
            "AssociationRelationship": ["*"]
        }
    },
    # Application elements
    "ApplicationComponent": {
        "allowed_targets": {
            "RealizationRelationship": ["ApplicationService", "ApplicationFunction"],
            "UsedByRelationship": ["ApplicationComponent"],
            "ServingRelationship": ["ApplicationComponent"],
            "AccessRelationship": ["DataObject"],
            "FlowRelationship": ["ApplicationComponent"],
            "CompositionRelationship": ["ApplicationComponent", "ApplicationInterface", "ApplicationFunction"],
            "AggregationRelationship": ["ApplicationComponent", "ApplicationInterface", "ApplicationFunction"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["ApplicationComponent"]
        }
    },
    "ApplicationCollaboration": {
        "allowed_targets": {
            "CompositionRelationship": ["ApplicationComponent"],
            "AggregationRelationship": ["ApplicationComponent"],
            "AssociationRelationship": ["*"]
        }
    },
    "ApplicationInterface": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessActor", "BusinessRole", "BusinessProcess", "ApplicationComponent"],
            "AssignmentRelationship": ["ApplicationService"],
            "CompositionRelationship": ["ApplicationComponent"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["ApplicationInterface"]
        }
    },
    "ApplicationService": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessProcess", "BusinessFunction", "BusinessService", "ApplicationComponent"],
            "RealizationRelationship": ["ApplicationComponent", "ApplicationFunction"],
            "AccessRelationship": ["DataObject"],
            "CompositionRelationship": ["ApplicationService"],
            "AggregationRelationship": ["ApplicationService"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["ApplicationService"]
        }
    },
    "ApplicationFunction": {
        "allowed_targets": {
            "UsedByRelationship": ["ApplicationComponent"],
            "AccessRelationship": ["DataObject"],
            "FlowRelationship": ["ApplicationFunction"],
            "TriggeringRelationship": ["ApplicationFunction", "ApplicationEvent"],
            "CompositionRelationship": ["ApplicationFunction"],
            "AggregationRelationship": ["ApplicationFunction"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["ApplicationFunction"]
        }
    },
    "ApplicationProcess": {
        "allowed_targets": {
            "AccessRelationship": ["DataObject"],
            "FlowRelationship": ["ApplicationProcess"],
            "TriggeringRelationship": ["ApplicationProcess", "ApplicationEvent"],
            "CompositionRelationship": ["ApplicationProcess"],
            "AggregationRelationship": ["ApplicationProcess"],
            "AssociationRelationship": ["*"]
        }
    },
    "ApplicationInteraction": {
        "allowed_targets": {
            "FlowRelationship": ["ApplicationProcess", "ApplicationFunction", "ApplicationInteraction"],
            "TriggeringRelationship": ["ApplicationProcess", "ApplicationFunction", "ApplicationEvent"],
            "AssociationRelationship": ["*"]
        }
    },
    "ApplicationEvent": {
        "allowed_targets": {
            "TriggeringRelationship": ["ApplicationProcess", "ApplicationFunction"],
            "AssociationRelationship": ["*"]
        }
    },
    "DataObject": {
        "allowed_targets": {
            "AccessRelationship": ["ApplicationComponent", "ApplicationFunction", "ApplicationProcess", "ApplicationService"],
            "RealizationRelationship": ["Artifact"],
            "CompositionRelationship": ["DataObject"],
            "AggregationRelationship": ["DataObject"],
            "AssociationRelationship": ["*"]
        }
    },
    # Technology & Physical elements
    "Node": {
        "allowed_targets": {
            "RealizationRelationship": ["TechnologyService"],
            "AssignmentRelationship": ["SystemSoftware", "Artifact", "Device"],
            "CompositionRelationship": ["Node", "Device", "SystemSoftware"],
            "AggregationRelationship": ["Node", "Device", "SystemSoftware"],
            "AssociationRelationship": ["*"]
        }
    },
    "Device": {
        "allowed_targets": {
            "RealizationRelationship": ["TechnologyService"],
            "AssignmentRelationship": ["SystemSoftware", "Artifact"],
            "CompositionRelationship": ["Device"],
            "AggregationRelationship": ["Device"],
            "AssociationRelationship": ["*"]
        }
    },
    "SystemSoftware": {
        "allowed_targets": {
            "RealizationRelationship": ["TechnologyService"],
            "AssignmentRelationship": ["Node", "Device"],
            "CompositionRelationship": ["SystemSoftware"],
            "AggregationRelationship": ["SystemSoftware"],
            "AssociationRelationship": ["*"]
        }
    },
    "TechnologyInterface": {
        "allowed_targets": {
            "ServingRelationship": ["ApplicationComponent", "Node", "Device"],
            "AssignmentRelationship": ["TechnologyService"],
            "CompositionRelationship": ["Node", "Device"],
            "AssociationRelationship": ["*"]
        }
    },
    "TechnologyService": {
        "allowed_targets": {
            "ServingRelationship": ["ApplicationComponent", "ApplicationService", "Node", "Device"],
            "RealizationRelationship": ["Node", "Device", "SystemSoftware"],
            "CompositionRelationship": ["TechnologyService"],
            "AggregationRelationship": ["TechnologyService"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["TechnologyService"]
        }
    },
    "Artifact": {
        "allowed_targets": {
            "AssignmentRelationship": ["Node", "Device"],
            "RealizationRelationship": ["DataObject"],
            "AssociationRelationship": ["*"]
        }
    },
    # Implementation & Migration elements
    "WorkPackage": {
        "allowed_targets": {
            "RealizationRelationship": ["Deliverable"],
            "CompositionRelationship": ["WorkPackage"],
            "AggregationRelationship": ["WorkPackage"],
            "AssociationRelationship": ["*"]
        }
    },
    "Deliverable": {
        "allowed_targets": {
            "RealizationRelationship": ["Artifact", "BusinessObject", "DataObject"],
            "CompositionRelationship": ["Deliverable"],
            "AggregationRelationship": ["Deliverable"],
            "AssociationRelationship": ["*"]
        }
    },
    "Plateau": {
        "allowed_targets": {
            "CompositionRelationship": ["Plateau"],
            "AggregationRelationship": ["Plateau"],
            "AssociationRelationship": ["*"]
        }
    },
    # Default rule for any element type (more restrictive)
    "*": {
        "allowed_targets": {
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["*"]  # Can specialize to same type only
        }
    }
}

AUTOCOMPLETE_RULES = [
    # --- MOTIVATION to BUSINESS LAYER ---
    {
        'name': 'Connect Goals to Business Capabilities that realize them',
        'rule_type': 'direct_relationship',
        'source_types': ['Capability'],
        'target_types': ['Goal'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['RealizationRelationship', 'InfluenceRelationship']}
        ],
        'action': {
            'create_relationships': [
                {'type': 'RealizationRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Connect Requirements to Business Services that fulfill them',
        'rule_type': 'direct_relationship',
        'source_types': ['BusinessService'],
        'target_types': ['Requirement'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['RealizationRelationship']}
        ],
        'action': {
            'create_relationships': [
                {'type': 'RealizationRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Connect Drivers to Business Processes they influence',
        'rule_type': 'direct_relationship',
        'source_types': ['Driver'],
        'target_types': ['BusinessProcess'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['InfluenceRelationship']}
        ],
        'action': {
            'create_relationships': [
                {'type': 'InfluenceRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },

    # --- BUSINESS to APPLICATION LAYER ---
    {
        'name': 'Connect Business Services to Application Services that realize them',
        'rule_type': 'direct_relationship',
        'source_types': ['ApplicationService'],
        'target_types': ['BusinessService'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['RealizationRelationship']},
            {'type': 'name_similarity', 'threshold': 0.6}
        ],
        'action': {
            'create_relationships': [
                {'type': 'RealizationRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Connect Business Processes to Application Services that support them',
        'rule_type': 'direct_relationship',
        'source_types': ['ApplicationService'],
        'target_types': ['BusinessProcess'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['ServingRelationship']},
            {'type': 'name_similarity', 'threshold': 0.5}
        ],
        'action': {
            'create_relationships': [
                {'type': 'ServingRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Connect Business Objects to Data Objects that implement them',
        'rule_type': 'direct_relationship',
        'source_types': ['DataObject'],
        'target_types': ['BusinessObject'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['RealizationRelationship']},
            {'type': 'name_similarity', 'threshold': 0.7}
        ],
        'action': {
            'create_relationships': [
                {'type': 'RealizationRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },

    # --- APPLICATION to TECHNOLOGY LAYER ---
    {
        'name': 'Connect Application Components to Nodes that host them',
        'rule_type': 'direct_relationship',
        'source_types': ['Node'],
        'target_types': ['ApplicationComponent'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['AssignmentRelationship']},
            {'type': 'name_similarity', 'threshold': 0.4}
        ],
        'action': {
            'create_relationships': [
                {'type': 'AssignmentRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Connect Application Services to Technology Services that enable them',
        'rule_type': 'direct_relationship',
        'source_types': ['TechnologyService'],
        'target_types': ['ApplicationService'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['ServingRelationship']},
            {'type': 'name_similarity', 'threshold': 0.5}
        ],
        'action': {
            'create_relationships': [
                {'type': 'ServingRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Connect Data Objects to Artifacts that store them',
        'rule_type': 'direct_relationship',
        'source_types': ['Artifact'],
        'target_types': ['DataObject'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['RealizationRelationship']},
            {'type': 'name_similarity', 'threshold': 0.6}
        ],
        'action': {
            'create_relationships': [
                {'type': 'RealizationRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },

    # --- CROSS-LAYER INTERFACE CONNECTIONS ---
    {
        'name': 'Add Application Interface between Business Actors and Application Services',
        'rule_type': 'insert_intermediary',
        'source_types': ['BusinessActor', 'BusinessRole'],
        'target_types': ['ApplicationService'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['ServingRelationship', 'UsedByRelationship']},
            {'type': 'target_name_contains', 'keywords': ['api', 'portal', 'gateway', 'service', 'interface']}
        ],
        'action': {
            'create_element': {
                'type': 'ApplicationInterface',
                'name': '{target_name} Interface'
            },
            'create_relationships': [
                {'type': 'AssignmentRelationship', 'source': 'intermediary', 'target': 'target'},
                {'type': 'ServingRelationship', 'source': 'intermediary', 'target': 'source'}
            ]
        }
    },
    {
        'name': 'Add Technology Interface between Application Components and Technology Services',
        'rule_type': 'insert_intermediary',
        'source_types': ['ApplicationComponent'],
        'target_types': ['TechnologyService'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['ServingRelationship']},
            {'type': 'target_name_contains', 'keywords': ['api', 'service', 'interface', 'gateway']}
        ],
        'action': {
            'create_element': {
                'type': 'TechnologyInterface',
                'name': '{target_name} Interface'
            },
            'create_relationships': [
                {'type': 'AssignmentRelationship', 'source': 'intermediary', 'target': 'target'},
                {'type': 'ServingRelationship', 'source': 'intermediary', 'target': 'source'}
            ]
        }
    },

    # --- VALUE STREAM & CAPABILITY CONNECTIONS ---
    {
        'name': 'Connect Capabilities to Value Streams they enable',
        'rule_type': 'direct_relationship',
        'source_types': ['Capability'],
        'target_types': ['ValueStream'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['RealizationRelationship']}
        ],
        'action': {
            'create_relationships': [
                {'type': 'RealizationRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Connect Value Streams to Business Processes that implement them',
        'rule_type': 'direct_relationship',
        'source_types': ['BusinessProcess'],
        'target_types': ['ValueStream'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['RealizationRelationship']},
            {'type': 'name_similarity', 'threshold': 0.6}
        ],
        'action': {
            'create_relationships': [
                {'type': 'RealizationRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },

    # --- COMPOSITION RELATIONSHIPS ---
    {
        'name': 'Compose Business Processes from sub-processes',
        'rule_type': 'direct_relationship',
        'source_types': ['BusinessProcess'],
        'target_types': ['BusinessProcess'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['CompositionRelationship', 'AggregationRelationship']},
            {'type': 'target_name_is_part_of_source', 'threshold': 0.8}
        ],
        'action': {
            'create_relationships': [
                {'type': 'CompositionRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    },
    {
        'name': 'Compose Application Components from sub-components',
        'rule_type': 'direct_relationship',
        'source_types': ['ApplicationComponent'],
        'target_types': ['ApplicationComponent'],
        'conditions': [
            {'type': 'no_relationship_of_type', 'rel_types': ['CompositionRelationship', 'AggregationRelationship']},
            {'type': 'target_name_is_part_of_source', 'threshold': 0.8}
        ],
        'action': {
            'create_relationships': [
                {'type': 'CompositionRelationship', 'source': 'source', 'target': 'target'}
            ]
        }
    }
]
