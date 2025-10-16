# Prompt Generator Configuration

# Default values
DEFAULT_ORGANISATION = "Lincolnshire County Council"
DEFAULT_FOCUS = "Digital Transformation"

# Architecture Domains for hierarchical selection
ARCHITECTURE_DOMAINS = {
    "motivation": {
        "name": "Motivation & Strategy",
        "description": "Drivers, goals, principles, outcomes",
        "elements": ["Stakeholder", "Driver", "Assessment", "Goal", "Principle", "Requirement", "Constraint", "Meaning", "Value", "Outcome"],
        "prompt_templates": [
            "Create stakeholder analysis for {organisation} focusing on {focus}",
            "Define strategic drivers and assessments for {organisation}'s {focus} initiatives",
            "Establish goals and outcomes for {organisation}'s {focus} transformation",
            "Identify principles and requirements guiding {organisation}'s {focus} approach"
        ]
    },
    "value_streams": {
        "name": "Value Streams & Services", 
        "description": "Value creation and service delivery",
        "elements": ["ValueStream", "BusinessService", "Product", "Contract", "BusinessEvent"],
        "prompt_templates": [
            "Model value streams for {organisation}'s service delivery in {focus}",
            "Define business services and products for {organisation}'s {focus} capabilities",
            "Identify service contracts and business events in {organisation}'s {focus} operations"
        ]
    },
    "business_architecture": {
        "name": "Business Architecture",
        "description": "Organisation structure and processes",
        "elements": ["BusinessActor", "BusinessRole", "BusinessProcess", "BusinessFunction", "BusinessObject", "BusinessInteraction"],
        "prompt_templates": [
            "Define business actors and roles for {organisation}'s {focus} initiatives",
            "Model business processes and functions for {organisation}'s {focus} operations", 
            "Identify business objects and interactions in {organisation}'s {focus} workflows"
        ]
    },
    "application_architecture": {
        "name": "Application & Data",
        "description": "Systems, data and interfaces",
        "elements": ["ApplicationComponent", "ApplicationService", "DataObject", "ApplicationInterface", "ApplicationFunction"],
        "prompt_templates": [
            "Define application components supporting {organisation}'s {focus}",
            "Model application services and interfaces for {organisation}'s {focus} systems",
            "Identify data objects and application functions in {organisation}'s {focus} architecture"
        ]
    },
    "technology_architecture": {
        "name": "Technology & Infrastructure", 
        "description": "Infrastructure and platforms",
        "elements": ["Technology", "Device", "SystemSoftware", "TechnologyService", "Node", "Network"],
        "prompt_templates": [
            "Define technology infrastructure supporting {organisation}'s {focus}",
            "Model technology services and platforms for {organisation}'s {focus} capabilities",
            "Identify devices and system software in {organisation}'s {focus} technology landscape"
        ]
    },
    "implementation": {
        "name": "Implementation & Migration",
        "description": "Projects, work packages and transition",
        "elements": ["WorkPackage", "Deliverable", "ImplementationEvent", "Plateau", "Gap"],
        "prompt_templates": [
            "Define work packages and deliverables for {organisation}'s {focus} implementation",
            "Model implementation roadmap and plateaus for {organisation}'s {focus} transition",
            "Identify capability gaps and implementation events in {organisation}'s {focus} journey"
        ]
    }
}

# Approved Bibliography - Only use these sources
APPROVED_SOURCES = {
    "lincolnshire_gov": {
        "name": "Lincolnshire County Council Website",
        "url": "https://www.lincolnshire.gov.uk",
        "description": "Official council website with service directories and strategies"
    },
    "lincolnshire_digital_strategy": {
        "name": "Lincolnshire Digital Strategy 2023-28", 
        "url": "https://www.lincolnshire.gov.uk/digital-strategy",
        "description": "Official digital transformation strategy document"
    },
    "lincolnshire_climate_strategy": {
        "name": "Lincolnshire Climate Strategy",
        "url": "https://www.lincolnshire.gov.uk/climate-strategy",
        "description": "Climate and environment strategy and action plan"
    },
    "lincolnshire_committee_papers": {
        "name": "Lincolnshire Committee Papers",
        "url": "https://www.lincolnshire.gov.uk/committees",
        "description": "Official committee meeting papers and decisions"
    },
    "uk_gov_service_manual": {
        "name": "GOV.UK Service Manual",
        "url": "https://www.gov.uk/service-manual",
        "description": "UK Government Digital Service standards and patterns"
    },
    "local_gov_association": {
        "name": "Local Government Association",
        "url": "https://www.local.gov.uk",
        "description": "UK local government standards and best practices"
    }
}

# Header Prompt Template - PLAIN TEXT VERSION

HEADER_PROMPT = """MANDATORY FORMAT RULE: Output MUST be a valid JSON array of objects. Each object represents one ArchiMate entity.

OUTPUT FORMAT: Return ONLY a JSON array with this structure:

[
  {
    "element_type": "BusinessActor",
    "name": "Planning Officer", 
    "description": "A role responsible for urban and regional planning"
  },
  {
    "element_type": "Goal",
    "name": "Improve Permit Processing Time",
    "description": "Reduce the average time to approve new building permits"
  },
  {
    "element_type": "InfluenceRelationship", 
    "source_name": "Planning Officer",
    "source_type": "BusinessActor",
    "target_name": "Improve Permit Processing Time",
    "target_type": "Goal",
    "description": "The officer's work directly impacts permit efficiency"
  }
]
Persona: You are an expert Enterprise Architect and a master of the ArchiMate modeling language. Your purpose is to act as a creative modeling partner who communicates solutions exclusively in a structured text format that will be used to ingest the output into a modelling tool.

Core Task: Analyze the user's request and the provided model context. Design a concise yet comprehensive and logical architectural model that fulfills the request. Then, represent your entire solution as a list of new elements and relationships using the strict format defined below.

REQUIRED FIELDS:
- For ALL entities: "element_type", "description"
- For ELEMENTS: "name" 
- For RELATIONSHIPS: "source_name", "source_type", "target_name", "target_type"

CRITICAL RULES:
1. Output ONLY the JSON array - no other text, no markdown, no explanations
2. Use standard ArchiMate 3.2 element and relationship types
3. Create specific, descriptive descriptions in UK english
4. Include both source_type and target_type in all relationships
5. Use clear, consistent entity names that can be easily matched and de-duplicated.
6. Build complete relationship networks
7. Generate as many entities as needed for comprehensive coverage
8. Where an entity has been declared before re-use it.

Remember: Your entire response must be parseable by JSON.parse()
"""


# Validation rules
VALIDATION_RULES = {
    "max_prompts_per_batch": 50,
    "required_sources": ["lincolnshire_gov", "lincolnshire_digital_strategy"],
    "source_citation_required": True
}
