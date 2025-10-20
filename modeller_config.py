"""
CONFIGURATION FILE - ArchiMate Digital Twin Simulator

This file contains all configuration parameters, neural node types, 
propagation rules, and simulation settings.

The system models each ArchiMate element as a computational neuron
with YAML-defined behavior that processes and propagates metric signals
through the enterprise architecture graph.
"""
MODELS_DIR="./"
# =============================================================================
# SIMULATION ENGINE CONFIGURATION
# =============================================================================

SIMULATION = {
    "time_step_ms": 100,           # Simulation clock granularity
    "max_propagation_depth": 50,   # Prevent infinite propagation loops
    "signal_decay_factor": 0.8,    # How signals weaken over hops
    "default_activation_threshold": 0.1,  # Minimum signal strength to propagate
    "enable_parallel_processing": True,
    "max_workers": 4,              # For parallel neuron processing
}

# =============================================================================
# NEURAL NODE TYPE DEFINITIONS
# =============================================================================

NEURON_TYPES = {
    "motivation": {
        "Stakeholder": {
            "input_metrics": ["sentiment", "influence", "satisfaction"],
            "output_metrics": ["requirement_pressure", "priority_signal"],
            "default_activation": 0.2,
            "propagation_delay_ms": 50,
        },
        "Goal": {
            "input_metrics": ["achievement_level", "priority"],
            "output_metrics": ["target_state", "performance_gap"],
            "default_activation": 0.3,
            "propagation_delay_ms": 100,
        },
        "Requirement": {
            "input_metrics": ["priority", "urgency"],
            "output_metrics": ["implementation_demand", "compliance_pressure"],
            "default_activation": 0.15,
            "propagation_delay_ms": 75,
        }
    },
    
    "business": {
        "BusinessProcess": {
            "input_metrics": ["workload", "efficiency", "automation_level"],
            "output_metrics": ["throughput", "cost", "service_level"],
            "default_activation": 0.25,
            "propagation_delay_ms": 150,
        },
        "BusinessService": {
            "input_metrics": ["demand", "availability", "performance"],
            "output_metrics": ["value_output", "customer_satisfaction"],
            "default_activation": 0.2,
            "propagation_delay_ms": 120,
        }
    },
    
    "application": {
        "ApplicationComponent": {
            "input_metrics": ["transaction_volume", "data_load", "config_change"],
            "output_metrics": ["response_time", "throughput", "error_rate"],
            "default_activation": 0.3,
            "propagation_delay_ms": 80,
        },
        "ApplicationService": {
            "input_metrics": ["request_rate", "complexity"],
            "output_metrics": ["availability", "latency", "capacity_utilization"],
            "default_activation": 0.25,
            "propagation_delay_ms": 60,
        }
    },
    
    "technology": {
        "Node": {
            "input_metrics": ["workload", "config_change", "maintenance_signal"],
            "output_metrics": ["performance", "availability", "resource_usage"],
            "default_activation": 0.4,
            "propagation_delay_ms": 200,
        },
        "TechnologyService": {
            "input_metrics": ["demand", "scaling_factor"],
            "output_metrics": ["capacity", "reliability", "cost"],
            "default_activation": 0.35,
            "propagation_delay_ms": 180,
        }
    }
}

# =============================================================================
# PROPAGATION RULES BY RELATIONSHIP TYPE
# =============================================================================

PROPAGATION_RULES = {
    "influences": {
        "signal_transform": "amplify",
        "weight": 0.8,
        "allowed_layers": ["motivation->motivation", "motivation->business"],
        "metric_mapping": {"sentiment": "priority", "urgency": "workload"}
    },
    
    "realizes": {
        "signal_transform": "direct_pass",
        "weight": 1.0,
        "allowed_layers": ["application->business", "technology->application"],
        "metric_mapping": {"throughput": "throughput", "availability": "availability"}
    },
    
    "serves": {
        "signal_transform": "demand_response",
        "weight": 0.9,
        "allowed_layers": ["application->business", "technology->application"],
        "metric_mapping": {"demand": "workload", "capacity": "throughput"}
    },
    
    "triggers": {
        "signal_transform": "event_chain",
        "weight": 0.95,
        "allowed_layers": ["business->business", "application->application"],
        "metric_mapping": {"completion_signal": "activation_signal"}
    }
}

# =============================================================================
# METRIC DEFINITIONS AND RANGES
# =============================================================================

METRICS = {
    "performance": {"min": 0, "max": 1, "default": 0.7, "decay_rate": 0.1},
    "cost": {"min": 0, "max": 1000000, "default": 1000, "decay_rate": 0.05},
    "availability": {"min": 0, "max": 1, "default": 0.99, "decay_rate": 0.02},
    "sentiment": {"min": -1, "max": 1, "default": 0.5, "decay_rate": 0.15},
    "throughput": {"min": 0, "max": 10000, "default": 100, "decay_rate": 0.08},
    "workload": {"min": 0, "max": 1, "default": 0.3, "decay_rate": 0.12},
}

# =============================================================================
# WORKLOAD SIMULATOR PROFILES
# =============================================================================

WORKLOAD_PROFILES = {
    "customer_channel_shift": {
        "description": "Simulates migration from physical to digital channels",
        "target_neurons": ["BusinessProcess", "BusinessService"],
        "metric_changes": {
            "workload": {"from": 0.3, "to": 0.7, "duration_ms": 5000},
            "automation_level": {"from": 0.2, "to": 0.8, "duration_ms": 8000}
        }
    },
    
    "database_optimization": {
        "description": "Simulates performance improvement in data layer",
        "target_neurons": ["Node", "TechnologyService"],
        "metric_changes": {
            "performance": {"from": 0.5, "to": 0.9, "duration_ms": 3000},
            "response_time": {"from": 200, "to": 50, "duration_ms": 4000}
        }
    },
    
    "sentiment_shock": {
        "description": "Simulates sudden change in stakeholder sentiment",
        "target_neurons": ["Stakeholder", "Driver"],
        "metric_changes": {
            "sentiment": {"from": 0.7, "to": -0.3, "duration_ms": 1000},
            "urgency": {"from": 0.3, "to": 0.9, "duration_ms": 2000}
        }
    }
}

# =============================================================================
# MONITORING AND OUTPUT CONFIGURATION
# =============================================================================

MONITORING = {
    "output_neurons": [
        "BusinessService:customer_satisfaction",
        "Goal:achievement_level", 
        "Node:performance",
        "BusinessProcess:cost"
    ],
    
    "sampling_interval_ms": 1000,
    "data_retention_count": 1000,
    
    "alert_thresholds": {
        "availability": {"warning": 0.95, "critical": 0.9},
        "performance": {"warning": 0.8, "critical": 0.6},
        "sentiment": {"warning": 0.3, "critical": 0.0},
        "cost": {"warning": 50000, "critical": 100000}
    }
}

# =============================================================================
# DEFAULT METRICS FOR ELEMENT TYPES
# =============================================================================

DEFAULT_METRICS = {
    "Stakeholder": {"satisfaction": 0.7, "influence": 0.8},
    "Driver": {"urgency": 0.9, "impact": 0.8},
    "Goal": {"achievement": 0.0, "priority": 0.9},
    "Requirement": {"compliance": 0.0, "importance": 0.8},
    "BusinessProcess": {"efficiency": 0.7, "cost": 300.0, "throughput": 50.0},
    "BusinessService": {"availability": 0.95, "satisfaction": 0.8, "cost": 500.0},
    "ApplicationService": {"response_time": 1.0, "throughput": 100.0, "availability": 0.99},
    "TechnologyService": {"availability": 0.999, "performance": 0.9},
    "BusinessActor": {"satisfaction": 0.7, "influence": 0.6},
    "BusinessRole": {"efficiency": 0.8, "workload": 0.5},
    "Capability": {"maturity": 0.5, "performance": 0.7},
    "Resource": {"utilization": 0.6, "cost": 200.0},
    "ApplicationComponent": {"performance": 0.8, "availability": 0.98},
    "DataObject": {"integrity": 0.95, "accessibility": 0.9},
    "Device": {"uptime": 0.99, "performance": 0.85},
    "SystemSoftware": {"stability": 0.95, "performance": 0.8},
    "WorkPackage": {"progress": 0.0, "budget_utilization": 0.3},
    "Deliverable": {"completeness": 0.0, "quality": 0.8},
    "Plateau": {"maturity": 0.5, "stability": 0.7}
}
