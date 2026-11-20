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
26 offline checks (toy data, a fake portal): both hosts working, everything
blocked, catalog up with the file host silent (with and without uploads),
duplicate resource names, and browser-renamed uploads. It has **not** yet run
on the real files.
