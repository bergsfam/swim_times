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
  --timeout 15
```

If you omit `--out`, the CLI now writes to `_data/` using the deterministic
filename pattern, which keeps the output automatically available to Jekyll.

To fetch multiple events in one run, create a JSON or YAML config file. Provide
an `events` list alongside optional defaults for `state` and the output
`folder` (defaults to `_data`). Each event uses a deterministic filename
pattern of `{season}-{phase}-{gender}-{division}-{event_slug}.csv` inside the
chosen folder, and you can override `state` or `folder` per event as needed.

```yaml
state: ohio
folder: _data/ohio
events:
  - season: 2024-2025
    phase: finals
    gender: girls
    division: d1
    event_slug: 50-freestyle
  - season: 2024-2025
    phase: finals
    gender: boys
    division: d1
    event_slug: 100-butterfly
    state: indiana  # per-event override
```

Then run:

```bash
python -m swimmeet_scraper.cli fetch-all --config events.yaml
python -m swimmeet_scraper.cli fetch-all --config events.yaml --dry-run  # show plan only
```

### Browsing the data with Jekyll

A simple Jekyll page at `events.html` loops over every CSV in `_data/`,
rendering an HTML table per event along with metadata (season, phase, division,
last updated timestamp from the CSV's file modification time, and a link to the
source compilation URL). Adjust `swimmeet_base_url` or
`swimmeet_default_state` in `_config.yml` if you need to point at another data
host or state.

Fetching multiple seasons of the same event
-------------------------------------------
If you want several seasons (for example 2024-2025, 2023-2024, and 2022-2023),
you can list each season explicitly in `events` with the deterministic filename
pattern. Each download is written directly into the configured `_data` folder
with no additional templating required.

Adjust `--base-url` if your swim meet data lives elsewhere (defaults to
`https://www.swimmeet.com` which builds URLs like
`https://www.swimmeet.com/ohio/2023-2024/compilation/finals/boys-d2-200-medley-relay.html`).
Use `--timeout` to override the request timeout per call and `--verbose` for
debug logging.
