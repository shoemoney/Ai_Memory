**In-template test (400 episodes: 280 need a tool, 120 do not)**

| Arm | First command right | First turn malformed (intended command right) | Well-formed calls | Exact sequence | Extra calls | No-tool specificity | Prompt tok / episode | Completion tok / episode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 278/280 (99.3%) | 0 (0) | 378/378 (100.0%) | 278/280 (99.3%) | 0 | 120/120 (100.0%) | 207 | 50 |
| B-native | 238/280 (85.0%) | 0 (0) | 423/463 (91.4%) | 181/280 (64.6%) | 91 | 118/120 (98.3%) | 2,046 | 237 |
| B-lean | 192/280 (68.6%) | 75 (65) | 371/456 (81.4%) | 144/280 (51.4%) | 105 | 113/120 (94.2%) | 3,956 | 208 |
| C | 211/280 (75.4%) | 46 (22) | 434/461 (94.1%) | 174/280 (62.1%) | 112 | 109/120 (90.8%) | 1,112 | 259 |
| B-native-1call | 258/280 (92.1%) | 0 (0) | 480/487 (98.6%) | 206/280 (73.6%) | 111 | 120/120 (100.0%) | 2,222 | 253 |

**Out-of-template test (100 episodes: 70 need a tool, 30 do not)**

| Arm | First command right | First turn malformed (intended command right) | Well-formed calls | Exact sequence | Extra calls | No-tool specificity | Prompt tok / episode | Completion tok / episode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 63/70 (90.0%) | 0 (0) | 101/101 (100.0%) | 57/70 (81.4%) | 28 | 7/30 (23.3%) | 187 | 53 |
| B-native | 61/70 (87.1%) | 0 (0) | 102/104 (98.1%) | 48/70 (68.6%) | 28 | 30/30 (100.0%) | 1,930 | 200 |
| C | 45/70 (64.3%) | 19 (4) | 85/90 (94.4%) | 33/70 (47.1%) | 26 | 30/30 (100.0%) | 921 | 202 |
| B-native-1call | 65/70 (92.9%) | 0 (0) | 105/105 (100.0%) | 53/70 (75.7%) | 24 | 30/30 (100.0%) | 2,000 | 214 |

**Paired bootstrap, first command, A minus B-native** (tool-needed episodes, 10,000 draws, seed 0, percentile 2.5 / 97.5)

| Test | A minus comparator (points) | 95% interval | n |
| --- | ---: | ---: | ---: |
| In-template | +14.29 | [+10.00, +18.57] | 280 |
| Out-of-template | +2.86 | [-7.14, +12.86] | 70 |
| In-template, vs B-native-1call (follow-up) | +7.14 | [+3.93, +10.71] | 280 |
| Out-of-template, vs B-native-1call (follow-up) | -2.86 | [-12.86, +7.14] | 70 |

**Multi-call first turns** (tool-needed episodes; the harness accepts one call per turn)

| Test | Arm | First turn issued several calls | First command right if such a turn is read by its first call |
| --- | --- | ---: | ---: |
| in | A | 0 | 278/280 (99.3%) |
| in | B-native | 21 | 245/280 (87.5%) |
| in | B-lean | 3 | 193/280 (68.9%) |
| in | C | 0 | 211/280 (75.4%) |
| in | B-native-1call | 2 | 258/280 (92.1%) |
| ood | A | 0 | 63/70 (90.0%) |
| ood | B-native | 2 | 62/70 (88.6%) |
| ood | C | 0 | 45/70 (64.3%) |
| ood | B-native-1call | 0 | 65/70 (92.9%) |

**Prompt-token ratio, A over each arm** (total prompt tokens over the whole test)

| Test | vs B-native | vs B-lean | vs C |
| --- | ---: | ---: | ---: |
| In-template | 10.1% | 5.2% | 18.6% |
| Out-of-template | 9.7% | not run | 20.3% |
