from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

@dataclass
class LearnerProfile:
    vark: Dict[str, float] = field(default_factory=dict)
    motivation: Dict[str, float] = field(default_factory=dict)
    self_regulation: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vark": self.vark,
            "motivation": self.motivation,
            "self_regulation": self.self_regulation
        }

@dataclass
class KnowledgeAreaScore:
    id: str
    name: str
    type: str
    mastery: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class KnowledgeProfile:
    domain_id: str
    overall_mastery: float
    areas: List[KnowledgeAreaScore] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "overall_mastery": self.overall_mastery,
            "areas": [area.to_dict() for area in self.areas]
        }

@dataclass
class StudentSnapshot:
    student_id: str
    student_name: str
    learner_profile: LearnerProfile
    knowledge_profile: KnowledgeProfile

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "student_name": self.student_name,
            "learner_profile": self.learner_profile.to_dict(),
            "knowledge_profile": self.knowledge_profile.to_dict()
        }
