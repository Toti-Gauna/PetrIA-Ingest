# Test fixtures (SYNTHETIC)

`registry_synthetic.csv` is **made up**, not official data. It uses the real 26
column names of the Capítulo IV registry, and each row exercises one cleaning rule:

| sigla | idpozo | What it tests |
|---|---|---|
| SYN-A-1 | 101, 102 | two records, one physical well |
| SYN-B-2 | 201 | point published swapped (-38.59, -69.42), fixed and flagged |
| SYN-C-3 | 301 | a Santa Cruz point must not be touched |
| SYN-D-4 | 401 | no point: invalid, nothing invented |
| (empty) | 501 | no sigla: rejected |
| SYN-E-5 | abc | idpozo not a whole number: rejected |
| " SYN-F-6 " | 601 | spaces trimmed, broken geojson, a literal "NA" kept as text |
| SYN-G-7 | 701 | a point that fits neither way: invalid |
