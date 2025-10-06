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
RELATIONSHIP_RULES = {
    # Strategy elements
    "Capability": {
        "allowed_targets": {
            "RealizationRelationship": ["Goal", "Requirement", "Outcome"],
            "ServingRelationship": ["BusinessActor", "BusinessRole"],
            "AggregationRelationship": ["Capability"],
            "AssociationRelationship": ["*"]
        }
    },
    # Motivation elements
    "Requirement": {
        "allowed_targets": {
            "RealizationRelationship": ["ApplicationService", "TechnologyService", "BusinessService", "Capability", "CourseOfAction"],
            "InfluenceRelationship": ["Goal", "Principle", "Requirement"],
            "AggregationRelationship": ["Requirement"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["Requirement"]
        }
    },
    "Goal": {
        "allowed_targets": {
            "RealizationRelationship": ["Outcome"], # Corrected from InfluenceRelationship
            "InfluenceRelationship": ["Goal", "Principle", "Requirement"],
            "AggregationRelationship": ["Goal"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["Goal"]
        }
    },
    # Business elements
    "BusinessService": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessActor", "BusinessRole", "BusinessProcess"],
            "RealizationRelationship": ["ApplicationService"],
            "AccessRelationship": ["BusinessObject"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["BusinessService"]
        }
    },
    "BusinessProcess": {
        "allowed_targets": {
            "UsedByRelationship": ["BusinessActor", "BusinessRole"],
            "AccessRelationship": ["BusinessObject"],
            "FlowRelationship": ["BusinessProcess", "BusinessFunction"],
            "TriggeringRelationship": ["BusinessProcess", "BusinessFunction", "BusinessEvent"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["BusinessProcess"]
        }
    },
    # Application elements
    "ApplicationComponent": {
        "allowed_targets": {
            "RealizationRelationship": ["ApplicationService", "ApplicationFunction"], # Added for completeness
            "UsedByRelationship": ["ApplicationComponent"],
            "AccessRelationship": ["DataObject"],
            "FlowRelationship": ["ApplicationComponent"],
            "CompositionRelationship": ["ApplicationComponent", "ApplicationInterface"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["ApplicationComponent"]
        }
    },
    "ApplicationService": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessProcess", "BusinessFunction", "BusinessService", "ApplicationComponent"],
            "RealizationRelationship": ["ApplicationComponent"],
            "AccessRelationship": ["DataObject"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["ApplicationService"]
        }
    },
    "ApplicationInterface": {
        "allowed_targets": {
            "ServingRelationship": ["BusinessActor", "BusinessRole", "BusinessProcess", "ApplicationComponent"],
            "CompositionRelationship": ["ApplicationComponent"],
            "AssignmentRelationship": ["ApplicationService"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["ApplicationInterface"]
        }
    },
    # Technology elements
    "Node": {
        "allowed_targets": {
            "RealizationRelationship": ["TechnologyService"],
            "AssignmentRelationship": ["SystemSoftware", "Artifact"],
            "AssociationRelationship": ["*"]
        }
    },
    "TechnologyService": {
        "allowed_targets": {
            "ServingRelationship": ["ApplicationComponent", "ApplicationService", "Node", "Device"],
            "RealizationRelationship": ["Node", "Device", "SystemSoftware"],
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["TechnologyService"]
        }
    },
    # Default rule for any element type
    "*": {
        "allowed_targets": {
            "AssociationRelationship": ["*"],
            "SpecializationRelationship": ["*"]  # Can specialize to same type
        }
    }
}

AUTOCOMPLETE_RULES = [
    {
        'name': 'Add Application Interface between Business Consumer and external-facing Application Service',
        'rule_type': 'insert_intermediary',
        'source_types': ['BusinessActor', 'BusinessRole'],
        'target_types': ['ApplicationService'],
        'conditions': {
            'not_directly_related_by': ['UsedByRelationship', 'ServingRelationship'],
            'target_name_contains': ['api', 'interface', 'portal', 'gateway', 'endpoint', 'service', 'consumer', 'client', 'user', 'customer', 'public']
        },
        'intermediary': {
            'type': 'ApplicationInterface',
            'name_template': '{target_name} Interface'
        },
        'new_relationships': [
            {'from': 'intermediary', 'to': 'target', 'type': 'AssignmentRelationship'},
            {'from': 'intermediary', 'to': 'source', 'type': 'ServingRelationship'}
        ]
    },
    {
        'name': 'Add Access Relationship from Application Component to related Data Object',
        'rule_type': 'direct_relationship',
        'source_types': ['ApplicationComponent'],
        'target_types': ['DataObject'],
        'conditions': {
            'not_directly_related_by': ['AccessRelationship'],
            'strong_name_match': True
        },
        'new_relationships': [
            {'from': 'source', 'to': 'target', 'type': 'AccessRelationship', 'attributes': {'accessType': 'readWrite'}}
        ]
    },
    {
        'name': 'Connect Business Process to supporting Application Service',
        'rule_type': 'direct_relationship',
        'source_types': ['ApplicationService'],
        'target_types': ['BusinessProcess'],
        'conditions': {
            'not_directly_related_by': ['ServingRelationship', 'RealizationRelationship'],
            'strong_name_match': True
        },
        'new_relationships': [
            {'from': 'source', 'to': 'target', 'type': 'ServingRelationship'}
        ]
    },
    {
        'name': 'Compose Application Component from sub-components',
        'rule_type': 'direct_relationship',
        'source_types': ['ApplicationComponent'], # The container
        'target_types': ['ApplicationComponent'], # The part
        'conditions': {
            'not_directly_related_by': ['CompositionRelationship', 'AggregationRelationship'],
            'target_name_is_part_of_source': True
        },
        'new_relationships': [
            {'from': 'source', 'to': 'target', 'type': 'CompositionRelationship'}
        ]
    },
    {
        'name': 'Assign System Software to a hosting Node',
        'rule_type': 'direct_relationship',
        'source_types': ['Node'],
        'target_types': ['SystemSoftware'],
        'conditions': {
            'not_directly_related_by': ['AssignmentRelationship'],
            'strong_name_match': True
        },
        'new_relationships': [
            {'from': 'source', 'to': 'target', 'type': 'AssignmentRelationship'}
        ]
    }
]
