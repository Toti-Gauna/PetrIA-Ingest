# Notebooks

## 00_verify_sources.ipynb

Checks the claims of the research report against the real portal and files.
The report could not open any official page, so every dataset fact is
unverified until this notebook has run on the files.

[Open in Colab](https://colab.research.google.com/github/Toti-Gauna/PetrIA-Ingest/blob/main/notebooks/00_verify_sources.ipynb)

### Run 1 (2026-11-20): what we learned
- The catalog `datos.gob.ar` answered (CKAN API). Metadata for the production,
  fracturing and concessions datasets is now verified, see
  [`docs/data-sources.md`](https://github.com/Toti-Gauna/PetrIA/blob/main/docs/data-sources.md).
- The file host `datos.energia.gob.ar` did **not** answer from Colab (connection
  timeouts on ports 80 and 443). No file was downloaded.
- The run took 12 minutes, mostly waiting on timeouts. Version 2 stops waiting
  on a host that does not answer.

### Run 2: upload the files you downloaded yourself
Download these files on your own device (the links come from the official
catalog metadata; file sizes are unknown), then run the notebook and pick them
in section 3. Keep the original file names.

| File | Link |
|---|---|
| Wells registry (CSV) | http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/cb5c0f04-7835-45cd-b982-3e25ca7d7751/download/capitulo-iv-pozos.csv |
| Wells with first production date (CSV) | http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/5578dd48-d0dd-487e-8ddc-bd3ebb1afef0/download/padrn-de-pozos-de-captulo-iv-con-fecha-de-primera-produccin.csv |
| Production, unconventional (CSV) | http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv |
| Fracturing, Adjunto IV (CSV) | http://datos.energia.gob.ar/dataset/71fa2e84-0316-4a1b-af68-7f35e41f58d7/resource/2280ad92-6ed3-403e-a095-50139863ab0d/download/datos-de-fractura-de-pozos-de-hidrocarburos-adjunto-iv-actualizacin-diaria.csv |
| Wells shapefile (ZIP) | http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/3fcda0c5-68aa-4f33-bbe2-0180e6dbeebe/download/shapefile-de-pozos.zip |
| Concessions (ZIP) | http://datos.energia.gob.ar/dataset/81cfad0a-4162-4f85-ad71-837f5a5fae57/resource/48a306a3-d5da-4f28-8ab5-7f80767ffdec/download/produccin-hidrocarburos-concesiones-de-explotacin.zip |

If a link does not open on your device either, that is a finding: report it.
Never commit these files; the repository ignores them.

### Run 3: targeted checks (notebook v2.1)
Run 2 read the real files and left open questions. Section 7 of the notebook
answers them, each check reading only the columns it needs:
1. **Swapped coordinates:** how many points fall outside a box around
   Argentina, and how many a longitude/latitude swap would fix (registry, production, shapefile).
2. **Freshness:** the first and last month in each file, rows per year, and what share of
   wells have a first-production date of 2006-01 (cut off).
3. **Fracturing zeros:** how often lateral length, stages and sand are `0` or empty (Vaca Muerta rows).
4. **Repeated well names:** do the repeated `sigla` values differ by formation or by location?
5. **Formation spellings:** every value in production, and every Vaca Muerta or Quintuco spelling in the registry.
6. **Flags and numbers:** `rectificado`, `habilitado`, and a numeric summary of production.
7. **Concession keys:** do concession codes and names match the registry and production area columns?
8. **Training set size:** how many Vaca Muerta wells have 12 complete months of oil, are not cut
   off at 2006, and have a fracturing record.

If the Colab session is still open, files uploaded before are reused (the report
says so and keeps their fingerprints). A skipped upload now prints a `SKIPPED` line.

### The reachability probe
`.github/workflows/probe-file-host.yml` asks one question: does the file host
answer from GitHub's servers? It sends HEAD requests only (nothing is downloaded).
Run it from the Actions tab (Run workflow). The answer decides where the monthly
ingestion job can run.

### What it does
1. Asks the CKAN API about each candidate dataset: license, last modified,
   files. Retries temporary failures, gives up on a 404, and stops waiting on
   a host that does not answer.
2. Picks resources by name (the most recently modified when names repeat).
3. Uses the files you uploaded, or downloads them (max 400 MB each).
4. Profiles each CSV: encoding, delimiter, columns, nulls, real distinct values
   of the formation and resource columns, coordinate ranges, duplicate keys.
5. Reads each shapefile's real coordinate system, geometry type and attributes.
6. Measures how the datasets join, and compares the real columns with the claims.

It writes nothing to a database and never invents a value. Every failure goes
into `errors` in the report.

### Tested
41 offline checks (toy data with the structure of the real files, and a fake portal):
both hosts working, everything blocked, catalog up with the file host silent (with and
without uploads), reuse of files in the same session, duplicate resource names,
browser-renamed uploads, and each run 3 check against a known answer. The checks have
**not** yet run on the real files.
