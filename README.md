# Olist Delivery & Seller Performance

An end-to-end analytics portfolio project for Mac: Python + SQL + SQLite + an interactive offline HTML dashboard.

**Business question:** Where should a marketplace operations team investigate delivery delays first?

**Start with [GUIDE.md](GUIDE.md)** for the complete English walkthrough, explanations, SQL exercises, resume wording and troubleshooting.

## Streamlit app

Run the interactive app using the included aggregate snapshot:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

No Kaggle login or data download is needed to view the Streamlit app. It reads `reports/app_data.json.gz`, a validated aggregate snapshot. To refresh it after rebuilding the analysis, run `python3 prepare_streamlit.py`.

For Streamlit Community Cloud, select branch `main`, entry point `streamlit_app.py`, and Python 3.13 in Advanced settings. See [DEPLOYMENT.md](DEPLOYMENT.md). A public app URL will be added after deployment is verified.

## Quick start

The CSV/SQL pipeline needs Python 3.10+ with sqlite3 and macOS curl. It does not require pip packages or a database server. The Streamlit interface uses the dependencies in `requirements.txt` and Python 3.11+.

```bash
python3 run_project.py --download
python3 -m unittest -v test_project.py
open reports/dashboard.html
```

If source CSVs already exist in `data/raw`, use `python3 run_project.py` without `--download`. The local project delivered with this guide already has source data and a built database. The portable source ZIP excludes raw data and the database to stay small; use `--download` after extracting it.

If Kaggle blocks the automatic download, download the dataset ZIP from the source link below, extract it, and copy these seven CSVs directly into `data/raw`:

- `olist_orders_dataset.csv`
- `olist_customers_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_sellers_dataset.csv`
- `olist_products_dataset.csv`
- `olist_order_reviews_dataset.csv`
- `product_category_name_translation.csv`

Then run `python3 run_project.py`. Payments and geolocation are intentionally not used: this scope measures merchandise sales and state-level delivery, not payment settlement or exact geography.

## Results from the supplied source snapshot

| Metric | Result |
|---|---:|
| Source orders | 99,441 |
| Delivered orders | 96,478 |
| Eligible delivered orders | 96,470 |
| Late orders | 6,534 |
| Late rate | 6.77% |
| Delivered merchandise sales | BRL 13,221,498.11 |
| Merchandise AOV | BRL 137.04 |
| Mean delivery duration | 12.56 days |

See `reports/executive_summary.md` for findings and proposed actions. These are historical results from purchase dates 2016-09-04 to 2018-10-17; source updates may change counts.

## Reproducible files

| File | Purpose |
|---|---|
| `run_project.py` | Download, import, validate, execute SQL and generate reports |
| `sql/model.sql` | Order, seller and category facts with documented grains |
| `sql/practice.sql` | Ten read-only analytical queries, including CTEs and a window function |
| `dashboard_template.html` | Dashboard source, with no external libraries |
| `test_project.py` | Edge cases and independent raw-CSV reconciliation |
| `streamlit_app.py` | Native Streamlit dashboard with filters, charts and exports |
| `prepare_streamlit.py` | Refresh the aggregate snapshot after a pipeline run |
| `test_streamlit.py` | Streamlit rendering and filter regression test |
| `build/olist.sqlite` | Generated database for DBeaver |
| `reports/dashboard.html` | Interactive report; works offline |
| `reports/validation.json` | Source row counts, hashes, checks and exclusions |
| `reports/*.csv` | Analysis exports for inspection or additional BI work |

## Methods

Item rows are summed to order level before joining reviews, which are averaged to order level. Monetary values are stored as integer cents. Late delivery is measured by calendar date, with invalid or missing delivery timelines excluded. Seller ranking includes only single-seller orders. Category order counts are non-additive; category sales are additive. Thresholds, sample sizes, status rules and missing-data treatment are visible in the dashboard and guide.

## Source and attribution

[Brazilian E-commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), downloaded on 21 September 2026. Raw-file SHA-256 hashes are recorded in `reports/validation.json`. Verify the dataset's current license on its source page before redistribution; retain Olist attribution. Raw CSVs are excluded from Git through `.gitignore`.

## Portfolio completion

Reproduce the results, explain the joins and denominators, and write your own interpretation before presenting this as your project. Publish source code, a dashboard screenshot and the business summary with attribution. The repository includes source code, aggregate dashboard data and reproducible reports. Public Streamlit deployment is tracked separately in DEPLOYMENT.md.
