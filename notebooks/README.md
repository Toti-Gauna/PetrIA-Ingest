# Notebooks

## 00_verify_sources.ipynb

Checks the claims of the Day 2 research report against the real portal files.
The report could not open any official page, so every dataset fact (columns,
coordinate system, license, keys) is unverified until this notebook runs.

**Run it:** open it in Google Colab and choose Runtime → Run all.

[Open in Colab](https://colab.research.google.com/github/Toti-Gauna/PetrIA-Ingest/blob/main/notebooks/00_verify_sources.ipynb)

**What it does**
1. Asks the portal's CKAN API about each candidate dataset: license, last
   modified, list of files.
2. Downloads the chosen files (at most 400 MB each) into the Colab disk.
3. Profiles each CSV: encoding, delimiter, columns, nulls, real distinct values
   of the formation and resource columns, coordinate ranges, duplicate keys.
4. Reads each shapefile's real coordinate system, geometry type and attributes.
5. Measures how the datasets join (share of wells found in the other file).
6. Compares the real columns with the research claims.

**What it does not do:** write to any database, or hide a failure. Every failure
goes into `errors` in the report.

**Output:** a JSON report printed in the last cell and saved as
`verification_report.json` (in Colab only, never committed).

**Tested:** 21 offline checks against toy fixtures and a fake portal, including
the blocked-network case. It has not run against the real portal yet.
