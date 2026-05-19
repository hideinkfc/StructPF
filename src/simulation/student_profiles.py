"""Student profile definitions based on Knowledge Components (KCs)."""

from dataclasses import dataclass, field


@dataclass
class StudentProfile:
    """A simulated student defined by KC mastery levels."""
    profile_id: str
    ability_level: str  # "low", "medium", "high"
    knowledge_components: dict[str, float] = field(default_factory=dict)
    misconceptions: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: dict) -> "StudentProfile":
        """Create a profile from a YAML config."""
        return cls(
            profile_id=config["id"],
            ability_level=config["ability_level"],
            knowledge_components=config.get("kcs", {}),
            misconceptions=config.get("misconceptions", []),
        )
