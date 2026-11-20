# PetrIA-Ingest

Data pipeline: downloads, cleans and loads well, production and fracturing data into PostGIS.

Part of **[PetrIA](https://github.com/Toti-Gauna/PetrIA)**: a map of the Vaca
Muerta wells with a heat map of expected productivity, plus an AI assistant.
PetrIA estimates productivity from existing wells. It does not discover oil,
and it is not drilling or investment advice.

## Status
Planned: version 1.0 (data pipeline). Only the data-verification notebook exists so far, see `notebooks/`.

## Planned stack
Python, PostGIS, RabbitMQ

## Documentation
Architecture, decisions (ADRs) and the daily build log live in the
[PetrIA](https://github.com/Toti-Gauna/PetrIA) repository:
[docs](https://github.com/Toti-Gauna/PetrIA/tree/main/docs) and
[History](https://github.com/Toti-Gauna/PetrIA/tree/main/History).

## Configuration
Copy `.env.example` to `.env` and fill in the values. Never commit `.env`.
