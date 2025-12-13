from models import Trait, Hero

import itertools
from collections import Counter

GLORY_LEAGUE_ID = 8

# Credits to pHeeDr for the Glory League rules in their YouTube video:
# https://www.youtube.com/watch?v=hMNUVVA42E8

GLORY_LEAGUE_1_COST = {"Alucard", "Lolita", "Kula", "Cecilion"}
GLORY_LEAGUE_5_COST = {"Akai", "X.Borg", "Benedetta", "Vexana", "Harley"}

GLORY_LEAGUE_ALLOWED_PAIRS = {
    "Alucard":   {"Akai", "Harley", "Vexana", "X.Borg"},
    "Kula":      {"Akai", "Benedetta", "Harley", "X.Borg"},
    "Cecilion":  {"Akai", "Harley", "Vexana", "X.Borg"},
    "Lolita":    {"Akai", "Benedetta", "Harley", "Vexana"},
}

def get_glory_league_hid(hero_index, selected_heroes=None):
    if not selected_heroes:
        return set()   # Glory League disabled

    if len(selected_heroes) != 2:
        raise ValueError("Glory League requires exactly 2 heroes.")

    name_to_hero = {h.name: h for h in hero_index}
    heroes = []

    for name in selected_heroes:
        if name not in name_to_hero:
            raise ValueError(f"Unknown hero: {name}")
        heroes.append(name_to_hero[name])

    for h in heroes:
        if h.name not in GLORY_LEAGUE_1_COST and h.name not in GLORY_LEAGUE_5_COST:
            raise ValueError(
                f"{h.name} is not eligible for Glory League. "
                f"Allowed 1-cost heroes: {sorted(GLORY_LEAGUE_1_COST)} | "
                f"Allowed 5-cost heroes: {sorted(GLORY_LEAGUE_5_COST)}"
            )

    one_cost = [h for h in heroes if h.name in GLORY_LEAGUE_1_COST]
    five_cost = [h for h in heroes if h.name in GLORY_LEAGUE_5_COST]
    
    if len(one_cost) != 1 or len(five_cost) != 1:
        raise ValueError(
            "Glory League requires exactly one eligible 1-cost "
            "and one eligible 5-cost hero."
        )

    one_cost_hero = one_cost[0].name
    five_cost_hero = five_cost[0].name
    
    allowed_fives = GLORY_LEAGUE_ALLOWED_PAIRS.get(one_cost_hero, set())

    if five_cost_hero not in allowed_fives:
        raise ValueError(
            f"Invalid Glory League combination: {one_cost_hero} × {five_cost_hero}. "
            f"Allowed 5-cost heroes for {one_cost_hero}: {sorted(allowed_fives)}"
        )
    
    return {one_cost[0].id, five_cost[0].id}


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

METRO_ZERO_ID = 9
METRO_ZERO_THRESHOLD = 2 
METRO_ZERO_BONUS = 500

def evaluate_team(hero_ids, hero_index, trait_index, glory_league_ids=None):
    """Returns (score, synergy_info) for a team of hero objects."""
    
    # 0. Check current match's Glory League heroes
    if glory_league_ids is None:
        glory_league_ids = set()
    
    # 1. Combine traits using bitmask OR
    combined_mask = 0
    for hid in hero_ids:
        combined_mask |= hero_index[hid].trait_mask

    # 2. Count how many heroes per trait
    trait_counter = Counter()
    for hid in hero_ids:
        hero = hero_index[hid]
        
        # base traits
        for tid in hero.trait_ids:
            trait_counter[tid] += 1
        
        # random Glory League trait
        if hid in glory_league_ids:
            trait_counter[GLORY_LEAGUE_ID] += 1

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


def find_best_team(max_team_size, hero_index, trait_index, locked_heroes=None, glory_league_ids=None, top_k=5):
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
    
    evaluated = 0

    # Enumerate combinations for remaining slots
    for combo in itertools.combinations(free_pool, remaining_slots):
        team = tuple(sorted(locked_heroes + list(combo)))

        score, synergy = evaluate_team(team, hero_index, trait_index, glory_league_ids=glory_league_ids)
        best.append((score, team, synergy))
        
        evaluated += 1

    print(f"Checked {evaluated:,} teams")
    
    best.sort(reverse=True, key=lambda x: x[0])
    return best[:top_k]