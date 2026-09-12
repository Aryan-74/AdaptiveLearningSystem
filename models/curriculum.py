from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

@dataclass
class CurriculumArea:
    id: str
    name: str
    type: str  # e.g., 'topic', 'concept', 'skill'
    description: str
    parent_id: Optional[str] = None
    prerequisites: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Curriculum:
    domain_id: str
    areas: List[CurriculumArea] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "areas": [area.to_dict() for area in self.areas]
        }
