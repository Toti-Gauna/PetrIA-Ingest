"""Algorithm spot: hash map well index.

Mode: AI-assisted (changed from no-AI on 2026-11-26 at the owner's request).
Claude wrote it; the owner validates it out loud: what it does, its cost, its edge cases.

    build_well_index([(101, "A"), (102, "A"), (201, "B")])
    -> {"A": [101, 102], "B": [201]}

- Input: a list of (idpozo, sigla) pairs: a record number and its physical well.
- Output: a dict, sigla -> sorted list of idpozo.
- The same idpozo under two different sigla raises ValueError (one record cannot
  belong to two wells). An identical repeated pair is fine and counted once.
- Cost: one pass over the pairs with two dictionaries, O(n). Sorting the lists
  adds O(n log n) in the worst case; here each well has 1 or 2 records, so it is tiny.
"""


def build_well_index(pairs):
    drawers = {}  # well (sigla) -> list of its records (idpozo). This is the result.
    seen = {}  # record (idpozo) -> the well it was first seen under. This is the check.

    for record, well in pairs:
        if record in seen:  # seen this record before?
            if seen[record] != well:  # ...under a DIFFERENT well: the file contradicts itself
                raise ValueError(
                    f"idpozo {record} appears under two wells: {seen[record]!r} and {well!r}"
                )
            continue  # ...under the SAME well: a repeat, nothing new to do

        seen[record] = well  # a new record: remember where it belongs
        if well not in drawers:  # this well has no drawer yet:
            drawers[well] = []  # create an empty one
        drawers[well].append(record)  # drop the record into its well's drawer

    for well in drawers:  # after the last pair: sort each drawer, small to big
        drawers[well] = sorted(drawers[well])
    return drawers
