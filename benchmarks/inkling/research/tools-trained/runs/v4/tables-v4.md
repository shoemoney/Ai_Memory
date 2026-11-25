**v1-template test** (400 requests: 280 need a command, 120 do not)

| Arm | First command right | First turn malformed | Well-formed calls | Exact sequence | Extra calls | No-tool specificity (Wilson 95%) | Prompt tok / episode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 277/280 (98.9%) | 0 | 377/377 (100.0%) | 277/280 (98.9%) | 0 | 120/120 (100.0%) [97, 100] | 207 |
| A2 | 280/280 (100.0%) | 0 | 442/442 (100.0%) | 279/280 (99.6%) | 62 | 61/120 (50.8%) [42, 60] | 224 |
| B-native-1call | 252/280 (90.0%) | 0 | 493/499 (98.8%) | 203/280 (72.5%) | 125 | 116/120 (96.7%) [92, 99] | 2,237 |
| C | 217/280 (77.5%) | 47 | 436/462 (94.4%) | 177/280 (63.2%) | 116 | 103/120 (85.8%) [78, 91] | 1,101 |

**v2-template test (in-template for A2)** (400 requests: 250 need a command, 150 do not)

| Arm | First command right | First turn malformed | Well-formed calls | Exact sequence | Extra calls | No-tool specificity (Wilson 95%) | Prompt tok / episode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 205/250 (82.0%) | 1 | 326/328 (99.4%) | 179/250 (71.6%) | 87 | 71/150 (47.3%) [40, 55] | 166 |
| A2 | 249/250 (99.6%) | 0 | 308/308 (100.0%) | 243/250 (97.2%) | 0 | 150/150 (100.0%) [98, 100] | 166 |
| B-native-1call | 237/250 (94.8%) | 1 | 380/381 (99.7%) | 186/250 (74.4%) | 84 | 144/150 (96.0%) [92, 98] | 1,928 |
| C | 154/250 (61.6%) | 72 | 280/320 (87.5%) | 120/250 (48.0%) | 69 | 147/150 (98.0%) [94, 99] | 873 |

**OOT-1 (development set)** (100 requests: 70 need a command, 30 do not)

| Arm | First command right | First turn malformed | Well-formed calls | Exact sequence | Extra calls | No-tool specificity (Wilson 95%) | Prompt tok / episode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 61/70 (87.1%) | 0 | 98/98 (100.0%) | 55/70 (78.6%) | 27 | 8/30 (26.7%) [14, 44] | 184 |
| A2 | 66/70 (94.3%) | 0 | 83/84 (98.8%) | 65/70 (92.9%) | 2 | 30/30 (100.0%) [89, 100] | 171 |
| B-native-1call | 65/70 (92.9%) | 0 | 112/112 (100.0%) | 50/70 (71.4%) | 27 | 30/30 (100.0%) [89, 100] | 2,080 |
| C | 41/70 (58.6%) | 20 | 83/96 (86.5%) | 30/70 (42.9%) | 29 | 30/30 (100.0%) [89, 100] | 919 |

**OOT-2 (blind)** (120 requests: 80 need a command, 40 do not)

| Arm | First command right | First turn malformed | Well-formed calls | Exact sequence | Extra calls | No-tool specificity (Wilson 95%) | Prompt tok / episode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 62/80 (77.5%) | 0 | 119/119 (100.0%) | 55/80 (68.8%) | 51 | 6/40 (15.0%) [7, 29] | 194 |
| A2 | 76/80 (95.0%) | 0 | 93/93 (100.0%) | 71/80 (88.8%) | 4 | 39/40 (97.5%) [87, 100] | 174 |
| B-native-1call | 76/80 (95.0%) | 0 | 153/156 (98.1%) | 41/80 (51.2%) | 64 | 40/40 (100.0%) [91, 100] | 2,178 |
| C | 52/80 (65.0%) | 25 | 103/111 (92.8%) | 32/80 (40.0%) | 44 | 40/40 (100.0%) [91, 100] | 910 |

**Paired bootstrap** (10,000 draws, seed 0, percentile 2.5 / 97.5; points)

| Test | Comparison | First command | No-tool specificity |
| --- | --- | ---: | ---: |
| v1-template test | A2-B-native-1call | +10.0 [+6.4, +13.6] (n=280) | -45.8 [-55.0, -35.8] (n=120) |
| v1-template test | A2-A | +1.1 [+0.0, +2.5] (n=280) | -49.2 [-58.3, -40.0] (n=120) |
| v2-template test (in-template for A2) | A2-B-native-1call | +4.8 [+2.0, +8.0] (n=250) | +4.0 [+1.3, +7.3] (n=150) |
| v2-template test (in-template for A2) | A2-A | +17.6 [+12.8, +22.4] (n=250) | +52.7 [+44.7, +60.7] (n=150) |
| OOT-1 (development set) | A2-B-native-1call | +1.4 [-5.7, +8.6] (n=70) | +0.0 [+0.0, +0.0] (n=30) |
| OOT-1 (development set) | A2-A | +7.1 [+0.0, +14.3] (n=70) | +73.3 [+56.7, +86.7] (n=30) |
| OOT-2 (blind) | A2-B-native-1call | +0.0 [-7.5, +6.2] (n=80) | -2.5 [-7.5, +0.0] (n=40) |
| OOT-2 (blind) | A2-A | +17.5 [+7.5, +27.5] (n=80) | +82.5 [+67.5, +95.0] (n=40) |

**Invented command names** (calls to names outside the eight; count of calls)

| Test | Arm | Calls | Names |
| --- | --- | ---: | --- |
| v1-template test | A | 0 | none |
| v1-template test | A2 | 24 | `capitalize` x20, `str_case` x3, `reverse` x1 |
| v1-template test | B-native-1call | 0 | none |
| v1-template test | C | 21 | `-h` x16, `bash` x3, `read` x1, `help` x1 |
| v2-template test (in-template for A2) | A | 43 | `translate` x8, `dictionary` x4, `rephrase` x4, `reword` x3, `define` x2, `explain` x2, `INVALID` x2, `brainstorm_ideas` x1, `smallest_prime` x1, `prime` x1, `suggest_hobby` x1, `explain_vaccines` x1, `count_vowels` x1, `ask_user` x1, `hasty` x1, `most_moons_planet` x1, `abbreviate` x1, `welcome_new_neighbors` x1, `explain_word` x1, `web` x1, `lookup` x1, `which_planet_has_most_moons` x1, `sort_letters` x1, `rewrite` x1, `Kyoto` x1 |
| v2-template test (in-template for A2) | A2 | 0 | none |
| v2-template test (in-template for A2) | B-native-1call | 0 | none |
| v2-template test (in-template for A2) | C | 20 | `-h` x15, `bash` x3, `help` x2 |
| OOT-1 (development set) | A | 15 | `INVALID` x1, `update_event` x1, `image_gen_caption` x1, `poem` x1, `synonyms` x1, `primary_colors` x1, `rhymes` x1, `who_wrote` x1, `days_in_leap_year` x1, `sign_off` x1, `up_planet_at_distance` x1, `rewrite` x1, `translate` x1, `plural` x1, `nickname` x1 |
| OOT-1 (development set) | A2 | 1 | `INVALID` x1 |
| OOT-1 (development set) | B-native-1call | 0 | none |
| OOT-1 (development set) | C | 5 | `-h` x4, `help` x1 |
| OOT-2 (blind) | A | 31 | `translate` x5, `INVALID` x5, `largest_planet` x1, `mortgage_rates` x1, `fix_grammar` x1, `rephrase` x1, `refrigerator` x1, `name_ideas` x1, `(287000` x1, `suggest_names` x1, `rewrite` x1, `3` x1, `language_of` x1, `unclutter` x1, `reduce_monday_stress` x1, `read_text_file` x1, `capital_of` x1, `suggest_date_ideas` x1, `1284` x1, `show_model_demand` x1, `nfl_snap_check_clinch` x1, `hours` x1, `dream` x1 |
| OOT-2 (blind) | A2 | 1 | `INVALID` x1 |
| OOT-2 (blind) | B-native-1call | 0 | none |
| OOT-2 (blind) | C | 1 | `-h` x1 |
