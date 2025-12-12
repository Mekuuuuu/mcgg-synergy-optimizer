from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional

@dataclass(frozen=True)
class Trait:
    id: int
    name: str
    thresholds: Tuple[int, ...] = (2,)    # e.g., (2,4,6,10)

@dataclass
class Hero:
    id: int
    name: str
    quality: int
    trait_ids: List[int]                  # indices into trait_index
    # trait_mask is optional but useful for bitwise ops / fast unions
    trait_mask: int = field(default=0)

    def build_mask(self):
        mask = 0
        for t in self.trait_ids:
            mask |= (1 << t)
        self.trait_mask = mask
        return self.trait_mask
