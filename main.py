from heroes_and_traits import traits, heroes
from helper import get_core_hid, get_glory_league_hid, initialize_traits_and_heroes, find_best_team

import time

traits_index, hero_index = initialize_traits_and_heroes(traits, heroes)

core_heroes = [
    "Benedetta",
    "Benedetta"
]

glory_league_heroes = [
    "Benedetta",
    "Kula"
]

start_time = time.perf_counter()

core_hero_ids = get_core_hid(hero_index, core_heroes, allow_duplicates=True)

glory_league_ids = get_glory_league_hid(hero_index, selected_heroes=glory_league_heroes)

results = find_best_team(5, hero_index, traits_index, core_hero_ids=core_hero_ids, glory_league_ids=glory_league_ids, top_k=5)

for score, team, synergies in results:
    print("\nScore:", score)
    print("Heroes:", [hero_index[i].name for i in team])
    print("Synergies:", {traits_index[tid].name: lvl for tid, lvl in synergies.items()})

end_time = time.perf_counter()

elapsed = end_time - start_time

print(f"\n⏱️ Optimization time: {elapsed:.4f} seconds")
