from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class Domain:
    id: str
    name: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> "Domain":
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"]
        )
