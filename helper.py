from models import Trait, Hero

import itertools
from collections import Counter
import heapq

def get_hid(hero_index, hero_name):
    """
    Resolve a single hero name to hero ID (case-insensitive).

    Raises
    ------
    ValueError if hero name is unknown.
    """
    if not hero_name:
        raise ValueError("Hero name cannot be empty.")

    name_to_id = {h.name.lower(): h.id for h in hero_index}

    key = hero_name.lower().strip()

    if key not in name_to_id:
        raise ValueError(
            f"Unknown hero name: '{hero_name}'. "
            f"Available heroes: {sorted(h.name for h in hero_index)}"
        )

    return name_to_id[key]

def get_core_hid(hero_index, hero_names, allow_duplicates=False):
    """
    Convert hero names to hero IDs.

    Parameters
    ----------
    hero_names : list[str]
        List of hero names (case-insensitive).
    hero_index : list[Hero]
        Initialized hero list.
    allow_duplicates : bool
        Whether duplicate hero names are allowed.

    Returns
    -------
    list[int]
        List of hero IDs in the same order as input.

    Raises
    ------
    ValueError
        If hero name is unknown or duplicates are not allowed.
    """
    if not hero_names:
        return []

    resolved_ids = []
    seen = set()

    for name in hero_names:
        hid = get_hid(hero_index, name)

        if not allow_duplicates:
            if hid in seen:
                raise ValueError(f"Duplicate hero not allowed: '{name}'")
            seen.add(hid)

        resolved_ids.append(hid)

    return resolved_ids

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

    # Resolve heroes
    heroes = []
    for name in selected_heroes:
        hid = get_hid(hero_index, name)
        heroes.append(hero_index[hid])

    # Eligibility check
    for h in heroes:
        if h.name not in GLORY_LEAGUE_1_COST and h.name not in GLORY_LEAGUE_5_COST:
            raise ValueError(
                f"{h.name} is not eligible for Glory League.\n"
                f"1-cost: {sorted(GLORY_LEAGUE_1_COST)}\n"
                f"5-cost: {sorted(GLORY_LEAGUE_5_COST)}"
            )

    one_cost = [h for h in heroes if h.name in GLORY_LEAGUE_1_COST]
    five_cost = [h for h in heroes if h.name in GLORY_LEAGUE_5_COST]

    if len(one_cost) != 1 or len(five_cost) != 1:
        raise ValueError(
            "Glory League requires exactly one 1-cost "
            "and one 5-cost hero."
        )

    one_name = one_cost[0].name
    five_name = five_cost[0].name

    allowed_fives = GLORY_LEAGUE_ALLOWED_PAIRS.get(one_name, set())

    if five_name not in allowed_fives:
        raise ValueError(
            f"Invalid Glory League combination: {one_name} × {five_name}. "
            f"Allowed: {sorted(allowed_fives)}"
        )

    return {one_cost[0].id, five_cost[0].id}

# to future Miko: this is normalized to lowercase, don't change it just because you think it looks ugly
MAGIC_CRYSTAL_ALLOWED = {
    "bruiser",
    "dauntless",
    "defender",
    "weapon master",
    "marksman",
    "mage",
    "stargazer",
    "swiftblade",
    "soul vessels",
    "shadowcell",
    "starwing",
    "kof",
    "luminexus",
    "aspirants",
    "toy mischief",
}

def get_mcid(trait_index, magic_crystals):
    """
    Convert magic crystal trait names to trait IDs.

    Parameters
    ----------
    trait_index : list[Trait]
        Initialized trait list.
    magic_crystals : list[str]
        Trait names (case-insensitive).

    Returns
    -------
    dict[int, int]
        trait_id -> bonus count (each crystal = +1)

    Raises
    ------
    ValueError
        If trait is unknown or not eligible as a magic crystal.
    """
    if not magic_crystals:
        return {}

    # Build case-insensitive lookup
    name_to_trait = {
        t.name.lower(): t.id for t in trait_index
    }

    crystal_counter = {}

    for name in magic_crystals:
        key = name.lower().strip()

        if key not in name_to_trait:
            raise ValueError(
                f"Trait '{name}' cannot be used as a Magic Crystal. "
                f"Allowed Magic Crystals: {sorted(t.title() for t in MAGIC_CRYSTAL_ALLOWED)}"
            )

        if key not in MAGIC_CRYSTAL_ALLOWED:
            raise ValueError(
                f"Trait '{name}' cannot be used as a Magic Crystal. "
                f"Allowed Magic Crystals: {sorted(MAGIC_CRYSTAL_ALLOWED)}"
            )

        tid = name_to_trait[key]
        crystal_counter[tid] = crystal_counter.get(tid, 0) + 1

    return crystal_counter

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

def evaluate_team(hero_ids, hero_index, trait_index, glory_league_ids=None, magic_crystal_ids=None):
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
    
    # 2.5 Apply trait magic_crystal_ids (+1 per magic crystal)
    if magic_crystal_ids:
        for tid, bonus in magic_crystal_ids.items():
            trait_counter[tid] += bonus

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
    # NOTE: with find_best_team_m0_enforced, this case should never happen
    else:
        final_score -= METRO_ZERO_BONUS  # penalize teams without Metro Zero

    return final_score, synergy_info


def find_best_team(max_team_size, hero_index, trait_index, core_hero_ids=None, glory_league_ids=None, magic_crystal_ids=None, top_k=5):
    """
    max_team_size  : final team size (ex: 5, 6, 7)
    core_hero_ids  : list of hero IDs that must be in the team
    """

    if core_hero_ids is None:
        core_hero_ids = []

    # core_hero_ids = list(set(core_hero_ids))  # dedupe just in case

    # Error handling: Core heroes exceed team size
    if len(core_hero_ids) > max_team_size:
        raise ValueError(
            f"Core heroes ({len(core_hero_ids)}) exceed team size ({max_team_size})."
        )

    # All heroes except the core ones
    all_hero_ids = list(range(len(hero_index)))
    free_pool = [h for h in all_hero_ids if h not in core_hero_ids]

    # How many more we need
    remaining_slots = max_team_size - len(core_hero_ids)

    # MIN-HEAP of size <= top_k
    best_heap = []
    evaluated = 0

    for combo in itertools.combinations(free_pool, remaining_slots):
        team = tuple(sorted(core_hero_ids + list(combo)))

        score, synergy = evaluate_team(
            team,
            hero_index,
            trait_index,
            glory_league_ids=glory_league_ids,
            magic_crystal_ids=magic_crystal_ids,
        )

        evaluated += 1

        entry = (score, team, synergy)

        if len(best_heap) < top_k:
            heapq.heappush(best_heap, entry)
        else:
            # Only keep if better than worst in heap
            if score > best_heap[0][0]:
                heapq.heapreplace(best_heap, entry)

    print(f"Checked {evaluated:,} teams")

    # Return sorted best results (highest first)
    return sorted(best_heap, reverse=True, key=lambda x: x[0])

def find_best_team_m0_enforced(max_team_size, hero_index, trait_index, core_hero_ids=None, glory_league_ids=None, magic_crystal_ids=None, top_k=5):
    """
    max_team_size  : final team size (ex: 5, 6, 7)
    core_hero_ids  : list of hero IDs that must be in the team
    """

    if core_hero_ids is None:
        core_hero_ids = []

    # core_hero_ids = list(set(core_hero_ids))  # dedupe just in case

    # Error handling: Core heroes exceed team size
    if len(core_hero_ids) > max_team_size:
        raise ValueError(
            f"Core heroes ({len(core_hero_ids)}) exceed team size ({max_team_size})."
        )

    # All heroes except the core ones
    all_hero_ids = list(range(len(hero_index)))
    free_pool = [h for h in all_hero_ids if h not in core_hero_ids]

    # How many more we need
    remaining_slots = max_team_size - len(core_hero_ids)
    
    # Enforce Metro Zero condition
    metro_zero_heroes = {
        h.id for h in hero_index if METRO_ZERO_ID in h.trait_ids
    }

    core_metro_count = sum(
        1 for hid in core_hero_ids if hid in metro_zero_heroes
    )

    required_metro = max(0, METRO_ZERO_THRESHOLD - core_metro_count)

    metro_free = [h for h in free_pool if h in metro_zero_heroes]
    non_metro_free = [h for h in free_pool if h not in metro_zero_heroes]

    if required_metro > len(metro_free):
        return []  # impossible to satisfy Metro Zero

    # MIN-HEAP of size <= top_k
    best_heap = []
    evaluated = 0

    for k in range(required_metro, min(len(metro_free), remaining_slots) + 1):
        for metro_combo in itertools.combinations(metro_free, k):
            for rest_combo in itertools.combinations(
                non_metro_free,
                remaining_slots - k
            ):
                team = tuple(
                    sorted(core_hero_ids + list(metro_combo) + list(rest_combo))
                )

                score, synergy = evaluate_team(
                    team,
                    hero_index,
                    trait_index,
                    glory_league_ids=glory_league_ids,
                    magic_crystal_ids=magic_crystal_ids,
                )

                evaluated += 1
                entry = (score, team, synergy)

                if len(best_heap) < top_k:
                    heapq.heappush(best_heap, entry)
                else:
                    if score > best_heap[0][0]:
                        heapq.heapreplace(best_heap, entry)

    print(f"Checked {evaluated:,} teams")

    return sorted(best_heap, reverse=True, key=lambda x: x[0])

def find_best_team_increment_dfs(
    max_team_size,
    hero_index,
    trait_index,
    core_hero_ids=None,
    glory_league_ids=None,
    magic_crystal_ids=None,
    top_k=5,
):
    if core_hero_ids is None:
        core_hero_ids = []

    if glory_league_ids is None:
        glory_league_ids = set()

    if magic_crystal_ids is None:
        magic_crystal_ids = {}

    if len(core_hero_ids) > max_team_size:
        raise ValueError("Core heroes exceed team size")

    # Precompute Metro Zero hero set
    metro_zero_heroes = {
        h.id for h in hero_index if METRO_ZERO_ID in h.trait_ids
    }

    # Initial incremental state from core heroes
    trait_counts = {}
    current_quality = 0
    current_metro = 0
    team = []

    def add_hero(hid):
        nonlocal current_quality, current_metro
        hero = hero_index[hid]
        team.append(hid)
        current_quality += hero.quality

        for tid in hero.trait_ids:
            trait_counts[tid] = trait_counts.get(tid, 0) + 1

        if hid in glory_league_ids:
            trait_counts[GLORY_LEAGUE_ID] = trait_counts.get(GLORY_LEAGUE_ID, 0) + 1

        if hid in metro_zero_heroes:
            current_metro += 1

    def remove_hero(hid):
        nonlocal current_quality, current_metro
        hero = hero_index[hid]
        team.pop()
        current_quality -= hero.quality

        for tid in hero.trait_ids:
            trait_counts[tid] -= 1
            if trait_counts[tid] == 0:
                del trait_counts[tid]

        if hid in glory_league_ids:
            trait_counts[GLORY_LEAGUE_ID] -= 1
            if trait_counts[GLORY_LEAGUE_ID] == 0:
                del trait_counts[GLORY_LEAGUE_ID]

        if hid in metro_zero_heroes:
            current_metro -= 1

    # Apply core heroes
    for hid in core_hero_ids:
        add_hero(hid)

    # Apply magic crystals ONCE (static bonus)
    for tid, bonus in magic_crystal_ids.items():
        trait_counts[tid] = trait_counts.get(tid, 0) + bonus

    # MIN-HEAP for top K
    best_heap = []

    all_hero_ids = list(range(len(hero_index)))
    free_pool = [h for h in all_hero_ids if h not in core_hero_ids]
    
    evaluated = 0

    # Recursive DFS
    def dfs(start_idx):
        nonlocal evaluated
        
        # Stop condition
        if len(team) == max_team_size:
            
            evaluated += 1
            
            if current_metro < METRO_ZERO_THRESHOLD:
                return

            # Compute synergy score incrementally
            synergy_score = 0
            synergy_info = {}

            for tid, count in trait_counts.items():
                thresholds = trait_index[tid].thresholds
                reached = max((t for t in thresholds if count >= t), default=None)
                if reached:
                    synergy_score += reached * 10
                    synergy_info[tid] = reached

            score = synergy_score + current_quality + METRO_ZERO_BONUS

            entry = (score, tuple(sorted(team)), synergy_info)

            if len(best_heap) < top_k:
                heapq.heappush(best_heap, entry)
            else:
                if score > best_heap[0][0]:
                    heapq.heapreplace(best_heap, entry)

            return

        # Recursive expansion
        for i in range(start_idx, len(free_pool)):
            hid = free_pool[i]
            add_hero(hid)
            dfs(i + 1)
            remove_hero(hid)

    dfs(0)
    
    print(f"Checked {evaluated:,} teams")

    return sorted(best_heap, reverse=True, key=lambda x: x[0])

def find_best_team_m0_increment_dfs(
    max_team_size,
    hero_index,
    trait_index,
    core_hero_ids=None,
    glory_league_ids=None,
    magic_crystal_ids=None,
    top_k=5,
):
    """
    max_team_size  : final team size (ex: 5, 6, 7)
    core_hero_ids  : list of hero IDs that must be in the team
    """

    if core_hero_ids is None:
        core_hero_ids = []

    if glory_league_ids is None:
        glory_league_ids = set()

    if magic_crystal_ids is None:
        magic_crystal_ids = {}

    # Error handling: Core heroes exceed team size
    if len(core_hero_ids) > max_team_size:
        raise ValueError(
            f"Core heroes ({len(core_hero_ids)}) exceed team size ({max_team_size})."
        )

    # All heroes except the core ones
    all_hero_ids = list(range(len(hero_index)))
    free_pool = [h for h in all_hero_ids if h not in core_hero_ids]
    
    # Enforce Metro Zero condition
    metro_zero_heroes = {
        h.id for h in hero_index if METRO_ZERO_ID in h.trait_ids
    }

    core_metro_count = sum(
        1 for hid in core_hero_ids if hid in metro_zero_heroes
    )

    required_metro = max(0, METRO_ZERO_THRESHOLD - core_metro_count)

    metro_free = [h for h in free_pool if h in metro_zero_heroes]
    non_metro_free = [h for h in free_pool if h not in metro_zero_heroes]

    if required_metro > len(metro_free):
        return []  # impossible to satisfy Metro Zero

    # DFS pool = metro first, then non-metro
    dfs_pool = metro_free + non_metro_free
    dfs_is_metro = [True] * len(metro_free) + [False] * len(non_metro_free)

    # Suffix count for remaining Metro Zero heroes
    remaining_metro_suffix = [0] * (len(dfs_pool) + 1)
    for i in range(len(dfs_pool) - 1, -1, -1):
        remaining_metro_suffix[i] = remaining_metro_suffix[i + 1]
        if dfs_is_metro[i]:
            remaining_metro_suffix[i] += 1

    # -----------------------------
    # Incremental state
    # -----------------------------
    trait_counts = {}
    current_quality = 0
    current_metro = core_metro_count
    team = []

    def add_hero(hid):
        nonlocal current_quality, current_metro
        hero = hero_index[hid]
        team.append(hid)
        current_quality += hero.quality

        for tid in hero.trait_ids:
            trait_counts[tid] = trait_counts.get(tid, 0) + 1

        if hid in glory_league_ids:
            trait_counts[GLORY_LEAGUE_ID] = trait_counts.get(GLORY_LEAGUE_ID, 0) + 1

        if hid in metro_zero_heroes:
            current_metro += 1

    def remove_hero(hid):
        nonlocal current_quality, current_metro
        hero = hero_index[hid]
        team.pop()
        current_quality -= hero.quality

        for tid in hero.trait_ids:
            trait_counts[tid] -= 1
            if trait_counts[tid] == 0:
                del trait_counts[tid]

        if hid in glory_league_ids:
            trait_counts[GLORY_LEAGUE_ID] -= 1
            if trait_counts[GLORY_LEAGUE_ID] == 0:
                del trait_counts[GLORY_LEAGUE_ID]

        if hid in metro_zero_heroes:
            current_metro -= 1

    # -----------------------------
    # Apply core heroes
    # -----------------------------
    for hid in core_hero_ids:
        add_hero(hid)

    # Apply magic crystals ONCE
    for tid, bonus in magic_crystal_ids.items():
        trait_counts[tid] = trait_counts.get(tid, 0) + bonus

    # -----------------------------
    # Result tracking
    # -----------------------------
    best_heap = []
    evaluated = 0

    # -----------------------------
    # DFS with PRE-ENUMERATION pruning
    # -----------------------------
    def dfs(start_idx):
        nonlocal evaluated

        slots_left = max_team_size - len(team)

        # 🚨 Metro Zero feasibility prune (BEFORE enumeration)
        max_possible_metro = current_metro + remaining_metro_suffix[start_idx]
        if max_possible_metro < METRO_ZERO_THRESHOLD:
            return

        # Not enough slots to finish
        if slots_left < 0:
            return

        # Leaf
        if slots_left == 0:
            evaluated += 1

            # Guaranteed Metro Zero satisfied due to pruning
            synergy_score = 0
            synergy_info = {}

            for tid, count in trait_counts.items():
                thresholds = trait_index[tid].thresholds
                reached = max((t for t in thresholds if count >= t), default=None)
                if reached:
                    synergy_score += reached * 10
                    synergy_info[tid] = reached

            score = synergy_score + current_quality + METRO_ZERO_BONUS
            entry = (score, tuple(sorted(team)), synergy_info)

            if len(best_heap) < top_k:
                heapq.heappush(best_heap, entry)
            else:
                if score > best_heap[0][0]:
                    heapq.heapreplace(best_heap, entry)

            return

        # Expand
        for i in range(start_idx, len(dfs_pool)):
            hid = dfs_pool[i]
            add_hero(hid)
            dfs(i + 1)
            remove_hero(hid)

    dfs(0)

    print(f"Checked {evaluated:,} teams")

    return sorted(best_heap, reverse=True, key=lambda x: x[0])