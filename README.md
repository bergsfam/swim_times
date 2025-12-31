# swim_times

Pull swim times for comparison.

## Usage

The repository provides a lightweight scraper packaged as `swimmeet_scraper`.
Use the CLI to fetch a single event into CSV:

```bash
python -m swimmeet_scraper.cli fetch \
  --season 2024-2025 \
  --phase finals \
  --gender girls \
  --division d1 \
  --event-slug 50-freestyle \
  --state ohio \
  --out _data/girls-d1-50-freestyle.csv \
  --timeout 15
```

To fetch multiple events in one run, create a JSON or YAML config file. The
file can either be a list of event dictionaries or wrap them in an `events`
list. Each event requires `season`, `phase`, `gender`, `division`, `event_slug`,
`state`, and `out` keys.

```yaml
events:
  - season: 2024-2025
    phase: finals
    gender: girls
    division: d1
    event_slug: 50-freestyle
    state: ohio
    out: _data/girls-d1-50-freestyle.csv
  - season: 2024-2025
    phase: finals
    gender: boys
    division: d1
    event_slug: 100-butterfly
    state: ohio
    out: _data/boys-d1-100-butterfly.csv
```

Then run:

```bash
python -m swimmeet_scraper.cli fetch-all --config events.yaml
```

Fetching multiple seasons of the same event
-------------------------------------------
If you want several seasons (for example 2024-2025, 2023-2024, and 2022-2023),
you can supply a `seasons` list in the config. The `out` path must include a
`{season}` placeholder so each CSV ends up in its own file:

```yaml
events:
  - seasons: [2024-2025, 2023-2024, 2022-2023]
    phase: finals
    gender: girls
    division: d1
    event_slug: 50-freestyle
    state: ohio
    out: _data/{season}-girls-d1-50-freestyle.csv
```

This expands into three fetches, producing `_data/2024-2025-girls-d1-50-freestyle.csv`,
`_data/2023-2024-girls-d1-50-freestyle.csv`, and `_data/2022-2023-girls-d1-50-freestyle.csv`.

Adjust `--base-url` if your swim meet data lives elsewhere (defaults to
`https://example.com/swimmeets`). Use `--timeout` to override the request
timeout per call and `--verbose` for debug logging.
