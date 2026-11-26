"""Algorithm spot: hash map well index (mode: no-AI).

The project owner writes this function by hand. See lesson 1.1.

    build_well_index([(101, "A"), (102, "A"), (201, "B")])
    -> {"A": [101, 102], "B": [201]}

- Input: a list of (idpozo, sigla) pairs: a record number and its physical well.
- Output: a dict, sigla -> sorted list of idpozo.
- The same idpozo under two different sigla raises ValueError (one record cannot
  belong to two wells). An identical repeated pair is fine and counted once.
- Expected: O(n) time and memory, one pass with dictionaries.
"""


def build_well_index(pairs):
    raise NotImplementedError("Owner's exercise (lesson 1.1, algorithm spot): not written yet.")
