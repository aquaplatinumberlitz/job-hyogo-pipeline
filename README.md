# Job Hyogo Pipeline

Deterministic Python pipeline for crawling, filtering, deduplicating, ranking, and reporting job listings in Hyogo/Kansai, Japan.

## Architecture

```
job_hyogo_pipeline.py --config config/job_hyogo.yaml
        │
        ├── sources/jobhouse.py         (static HTML crawl)
        ├── sources/job_harima.py       (static HTML crawl)
        ├── sources/hello_work_info.py  (static HTML crawl)
        ├── sources/koujou_works.py     (static HTML crawl)
        ├── sources/kyujin_box.py       (static HTML crawl)
        ├── sources/facebook_search.py  (static fallback)
        ├── sources/facebook_browser.py (Playwright browser login + crawl)
        └── sources/official_careers.py (6 company career pages)
                │
        filter → deduplicate → rank
                │
        export JSON → render HTML → Telegram summary
```

## Usage

```bash
python3 scripts/job_hyogo_pipeline.py --config config/job_hyogo.yaml
```

## Requirements

- Python 3.10+
- `requests` (HTTP crawls)
- `pyyaml` (config parsing)
- `playwright` (optional, for Facebook browser crawl)

## Output

- `reports/job_hyogo/job_hyogo_report_YYYY-MM-DD.json` — normalized job data
- `reports/job_hyogo/job_hyogo_report_YYYY-MM-DD.html` — rendered HTML report
- `reports/job_hyogo/job_hyogo_report_YYYY-MM-DD_telegram.txt` — Telegram summary
- `reports/job_hyogo/facebook_raw_YYYYMMDD.json` — raw Facebook posts (if browser crawl enabled)

## Facebook Credentials

Credentials are stored separately at `~/.hermes/references/facebook_job_crawl_cred.json` (chmod 600) and never committed to the repo.

Config: `config/job_hyogo.yaml`
