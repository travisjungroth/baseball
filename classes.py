from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, order=True)
class Team:
    id_: int
    mlb_id: int
    abb: str
    teams: ClassVar = []

    def __post_init__(self):
        self.teams.append(self)

    def __str__(self):
        return self.abb

    def __repr__(self):
        return str(self)
