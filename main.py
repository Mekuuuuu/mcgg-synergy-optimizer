from heroes_and_traits import traits, heroes
from models import Trait, Hero

def initialize_traits_and_heroes(traits, heroes):
    # init traits
    trait_index = []
    for tid, t in enumerate(traits):
        trait_index.append(
            Trait(
                id=tid,
                name=t["name"],
                thresholds=tuple(t["thresholds"])
            )
        )

    # init heroes
    hero_index = []
    for hid, h in enumerate(heroes):
        hero = Hero(
            id=hid,
            name=h["name"],
            quality=h["quality"], 
            trait_ids=h["traits"]
        )
        hero.build_mask()          # auto-compute bitmask
        hero_index.append(hero)

    return trait_index, hero_index


traits_index, hero_index = initialize_traits_and_heroes(traits, heroes)

import itertools
from collections import Counter

METRO_ZERO_ID = 9
METRO_ZERO_THRESHOLD = 2 
METRO_ZERO_BONUS = 500

def evaluate_team(hero_ids, hero_index, trait_index):
    """Returns (score, synergy_info) for a team of hero objects."""
    
    # 1. Combine traits using bitmask OR
    combined_mask = 0
    for hid in hero_ids:
        combined_mask |= hero_index[hid].trait_mask

    # 2. Count how many heroes per trait
    trait_counter = Counter()
    for hid in hero_ids:
        for tid in hero_index[hid].trait_ids:
            trait_counter[tid] += 1

    # 3. Check Metro Zero requirement
    metro_zero_active = trait_counter[METRO_ZERO_ID] >= METRO_ZERO_THRESHOLD

    # 4. Compute synergy score
    synergy_score = 0
    synergy_info = {}

    for tid, count in trait_counter.items():
        thresholds = trait_index[tid].thresholds

        # Highest threshold reached
        reached = max([t for t in thresholds if count >= t], default=None)

        if reached is None:
            continue


        # Weight synergy strength = reached * 10 (tune freely)
        synergy_score += reached * 10
        synergy_info[tid] = reached

    # 5. Quality score
    quality_score = sum(hero_index[hid].quality for hid in hero_ids)

    # 6. Final Score
    final_score = synergy_score + quality_score
    
    # FORCE METRO ZERO PRIORITY
    if metro_zero_active:
        final_score += METRO_ZERO_BONUS
    else:
        final_score -= METRO_ZERO_BONUS  # penalize teams without Metro Zero

    return final_score, synergy_info


def find_best_team(max_team_size, hero_index, trait_index, locked_heroes=None, top_k=5):
    """
    max_team_size  : final team size (ex: 5, 6, 7)
    locked_heroes  : list of hero IDs that must be in the team
    """

    if locked_heroes is None:
        locked_heroes = []

    locked_heroes = list(set(locked_heroes))  # dedupe just in case

    # Error handling: locked heroes exceed team size
    if len(locked_heroes) > max_team_size:
        raise ValueError(
            f"Locked heroes ({len(locked_heroes)}) exceed team size ({max_team_size})."
        )

    # All heroes except the locked ones
    all_hero_ids = list(range(len(hero_index)))
    free_pool = [h for h in all_hero_ids if h not in locked_heroes]

    # How many more we need
    remaining_slots = max_team_size - len(locked_heroes)

    best = []

    # Enumerate combinations for remaining slots
    for combo in itertools.combinations(free_pool, remaining_slots):
        team = tuple(sorted(locked_heroes + list(combo)))

        score, synergy = evaluate_team(team, hero_index, trait_index)
        best.append((score, team, synergy))

    best.sort(reverse=True, key=lambda x: x[0])
    return best[:top_k]

locked_board = [
    hero_index.index(next(h for h in hero_index if h.name == "Irithel")),
    hero_index.index(next(h for h in hero_index if h.name == "Hanabi")),
    hero_index.index(next(h for h in hero_index if h.name == "Claude")),
    hero_index.index(next(h for h in hero_index if h.name == "Layla")),
    hero_index.index(next(h for h in hero_index if h.name == "Ixia"))
]

results = find_best_team(5, hero_index, traits_index, locked_heroes=None, top_k=5)

for score, team, synergies in results:
    print("\nScore:", score)
    print("Heroes:", [hero_index[i].name for i in team])
    print("Synergies:", {traits_index[tid].name: lvl for tid, lvl in synergies.items()})

# print(hero_index[0].name)
# print(hero_index[0].trait_mask)
# print(trait_index[2].name)