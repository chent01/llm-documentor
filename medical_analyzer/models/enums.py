"""
Enumerations for the Medical Software Analysis Tool data models.
"""

from enum import Enum, auto


class ChunkType(Enum):
    """Types of code chunks for analysis."""
    FUNCTION = auto()
    CLASS = auto()
    MODULE = auto()
    GLOBAL = auto()
    INTERFACE = auto()


class FeatureCategory(Enum):
    """Categories for identified software features."""
    DATA_PROCESSING = auto()
    USER_INTERFACE = auto()
    COMMUNICATION = auto()
    SAFETY = auto()
    DEVICE_CONTROL = auto()
    ALGORITHM = auto()
    STORAGE = auto()
    VALIDATION = auto()
    MONITORING = auto()
    CONFIGURATION = auto()


class RequirementType(Enum):
    """Types of requirements in the analysis."""
    USER = auto()
    SOFTWARE = auto()
    SYSTEM = auto()


class Severity(Enum):
    """Risk severity levels per ISO 14971."""
    CATASTROPHIC = "Catastrophic"
    SERIOUS = "Serious" 
    MINOR = "Minor"
    NEGLIGIBLE = "Negligible"


class Probability(Enum):
    """Risk probability levels per ISO 14971."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    REMOTE = "Remote"


class RiskLevel(Enum):
    """Overall risk levels calculated from severity and probability."""
    UNACCEPTABLE = "Unacceptable"
    UNDESIRABLE = "Undesirable"
    ACCEPTABLE = "Acceptable"
    NEGLIGIBLE = "Negligible"