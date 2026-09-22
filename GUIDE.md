# E-commerce Delivery & Seller Performance: Complete Project Guide

This guide explains how to run the project on a Mac, understand each analytical step, explore the dashboard, and present the work in a resume or interview. It includes a same-day schedule and checkpoints with expected results.

## 1. The business problem

Imagine you work as a data analyst for an online marketplace. The operations manager asks:

> “Some customers receive their orders late. Which regions, sellers and product categories should we investigate first?”

The project answers five questions:

1. How often do eligible delivered orders arrive late?
2. Which regions have the largest number of affected orders?
3. Which sellers should receive further investigation?
4. How do review scores differ between late and on-time deliveries?
5. What should the operations team investigate or test next?

The outcome is a reproducible analysis and decision-support dashboard. Recommendations are proposed actions, not claims of improvements already achieved.

## 2. Software required on a Mac

| Tool | Purpose | Why it is used |
|---|---|---|
| Python | Import CSV files, validate data, run SQL and generate reports | Automates the analysis so it can be reproduced |
| SQLite | Store tables and run SQL | Requires no database server, password or port setup |
| VS Code | Read and edit source files | Makes code and documentation easier to navigate |
| DBeaver | Inspect database tables and run SQL manually | Helps you learn and explain the queries |
| Chrome or Safari | View the offline dashboard | Opens the generated HTML report |
| Streamlit | Run the native Python dashboard | Provides filters, charts, tables and a cloud deployment option |
| GitHub | Store and share source code | Gives recruiters access to the project and supports Streamlit deployment |

The CSV/SQL pipeline uses Python's standard library. The Streamlit interface needs the packages in `requirements.txt`. Use Python 3.13 for a new setup; the app was also tested locally with Python 3.14.

Power BI Desktop requires Windows. This project uses an interface that runs on macOS and can be hosted with Streamlit. List the tools actually used in this version on your resume.

Official references: [Python for macOS](https://www.python.org/downloads/macos/), [SQLite in Python](https://docs.python.org/3/library/sqlite3.html), [Power BI requirements](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop).

## 3. Open the project

Download the repository using **Code > Download ZIP**, then extract it. Alternatively, clone it with Git. Open the project folder in VS Code using **File > Open Folder**.

On macOS, press **Command + Space**, type **Terminal**, and press Enter. Type `cd ` with a trailing space, drag the project folder from Finder into Terminal, and press Enter. This changes the working directory to the project folder.

Check Python:

```bash
python3 --version
```

### Option A: Run the Streamlit dashboard immediately

The repository contains a validated aggregate snapshot, so this option does not need a Kaggle download.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

- `venv` creates an isolated environment for the app's dependencies.
- `source` activates it in the current Terminal session.
- `pip install` installs the dashboard dependencies.
- `streamlit run` starts the app and displays its local address.

**Checkpoint:** the dashboard shows **99,441 orders** and a **6.77% late-delivery rate**. The local address is for your machine; it is not a public resume link. See `DEPLOYMENT.md` for public hosting.

Press **Control + C** in Terminal to stop the server.

### Option B: Rebuild the full analysis from source

```bash
python3 run_project.py --download
python3 -m unittest -v test_project.py
python3 prepare_streamlit.py
open reports/dashboard.html
```

Use `python3 run_project.py` without `--download` when the raw CSVs already exist in `data/raw`. Reruns rebuild generated reports and the database; they do not modify the raw CSVs.

**Checkpoint:** the pipeline prints `Validation: 15 checks passed`. The analytical tests print `Ran 6 tests` and `OK`. The headline order and late-rate results match Option A.

If the automatic download fails, download the ZIP from the [Olist source page](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Extract it and copy the seven CSVs listed in the README directly into `data/raw`, then rerun without `--download`.

## 4. A practical same-day schedule

| Time | Activity | Evidence of completion |
|---|---|---|
| 0:00–0:20 | Run the project and tests | Dashboard opens and tests pass |
| 0:20–1:00 | Understand the business question and table relationships | Explain the difference between an order and an item |
| 1:00–2:15 | Run the ten practice SQL queries | Write one sentence explaining each query |
| 2:15–3:00 | Trace the Python and SQL pipeline | Explain how raw files become metrics |
| 3:00–4:00 | Explore filters and write an additional query | Verify two filtered findings |
| 4:00–5:00 | Write your own business summary | Three findings, three actions and limitations |
| 5:00–6:00 | Prepare screenshots, repository and interview explanation | A portfolio package you can explain independently |

This schedule targets a complete first version and a defensible explanation. It is not a promise to master every tool in one day.

## 5. Understand the data and table grain

Source: [Brazilian E-commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). This snapshot contains purchase dates from **4 September 2016 to 17 October 2018**. Amounts are in **Brazilian real (BRL)**, not Indian rupees.

**Grain** means what one row represents.

| Table | One row represents | Analytical purpose |
|---|---|---|
| `orders` | One order | Status and purchase/delivery timestamps |
| `customers` | An order-linked customer record | Customer state and stable customer identity |
| `items` | One item within an order | Product, seller, price and freight |
| `sellers` | One seller | Seller location |
| `products` | One product | Product category |
| `reviews` | One review record | Customer experience; an order may have several records |
| `category_translation` | One category translation | Map Portuguese names to English |

```text
customers -- customer_id --> orders <-- order_id -- items
                               ^                    |
                               |                 product_id --> products --> category_translation
                            reviews              seller_id  --> sellers
```

For future repeat-customer analysis, use `customer_unique_id`. The order-linked `customer_id` is not a reliable repeat-customer identifier.

### Why direct joins can inflate sales

Suppose one order has two items, priced at BRL 100 and BRL 200, and two review records. Joining item rows directly to review rows can produce four rows and incorrectly report BRL 600 in sales.

This project first sums items to one row per order and averages reviews to one row per order. It then joins those summaries. The correct sales amount remains BRL 300, and the final order table contains one row per order.

## 6. Metric definitions and why they matter

| Metric | Exact definition | Business use |
|---|---|---|
| All orders | Count of order IDs across all statuses | Total order activity |
| Delivered merchandise sales | Sum of item prices for delivered orders | Delivered goods value |
| Merchandise AOV | Delivered item sales divided by delivered orders with item data | Typical order size |
| Late-delivery rate | Late orders divided by eligible delivered orders | Delivery reliability |
| Mean delivery days | Mean difference between delivery and purchase timestamps among eligible orders | Customer waiting time |
| Mean review score | Average reviews within each order, then average reviewed eligible orders | Experience comparison between delivery groups |

Merchandise sales exclude freight. They are not Olist commission revenue or profit. Costs, refunds and commissions are not available in this analysis.

**Late-delivery example:** an order promised for 10 January and delivered at 8 PM on 10 January is on time. Delivery on 11 January is late. Comparing full timestamps against a midnight estimate would incorrectly classify some same-day arrivals as late.

**Delivery eligibility:** delivered status, valid purchase/actual/estimated dates, actual delivery no earlier than purchase, and estimated calendar date no earlier than purchase date. Missing delivery dates are not treated as on time.

The overall order count is 99,441, but the late-rate denominator is 96,470. Canceled, undelivered and invalid-timeline orders cannot be used to measure delivered-order punctuality reliably.

## 7. Run SQL in DBeaver

First rebuild the analysis so `build/olist.sqlite` exists.

1. Open DBeaver.
2. Choose **Database > New Database Connection**.
3. Search for **SQLite**, select it and continue.
4. Select the existing `build/olist.sqlite` file inside the project folder.
5. If prompted, download the standard SQLite driver. This first connection may require internet access.
6. Select **Test Connection**, then Finish. SQLite does not require a host, port, username or password.
7. Right-click the connection and select **SQL Editor > New SQL Script**.
8. Run this query using the editor's Execute SQL button:

```sql
SELECT COUNT(*) AS total_orders FROM order_fact;
```

Expected result: **99441**.

Open `sql/practice.sql` and run each query separately:

| Query | What it teaches |
|---|---|
| 1 | Status distribution using GROUP BY |
| 2 | Conditional aggregation and correct denominators |
| 3 | Purchase-month trends |
| 4 | State comparisons: volume versus rate |
| 5 | Seller priorities and minimum sample sizes |
| 6 | Category comparisons and non-additive order counts |
| 7 | Review associations and causal limitations |
| 8 | Join-grain validation |
| 9 | A CTE and DENSE_RANK window function |
| 10 | A cancellation rate with a different denominator |

`WHERE` filters rows before grouping. `HAVING` filters groups after aggregation. `NULLIF(denominator,0)` prevents division by zero while keeping undefined rates unavailable rather than converting them to zero.

### Exercise: verify a dashboard filter

```sql
SELECT
    COUNT(*) AS all_orders,
    SUM(eligible_delivery) AS eligible_orders,
    SUM(is_late) AS late_orders,
    100.0 * SUM(is_late) / NULLIF(SUM(eligible_delivery), 0) AS late_pct
FROM order_fact
WHERE purchase_year = '2017' AND customer_state = 'RJ';
```

Expected: **6,225 orders, 5,968 eligible deliveries, 624 late deliveries and a 10.46% late rate**. Choose the same filters in the dashboard and confirm the values match.

Next, change the state priority query from `ORDER BY late_orders DESC` to `ORDER BY late_pct DESC`. Explain why the ranking changes: rate measures reliability, while count measures affected order volume.

## 8. How the source code works

```text
Raw CSVs
   → load(): types, tables, keys and relationships
   → sql/model.sql: order, seller and category facts
   → validate_model(): order counts and sales reconciliation
   → reports(): SQL metrics, exports, summary and offline dashboard
   → prepare_streamlit.py: compressed aggregate snapshot
   → streamlit_app.py: interactive app
```

In `run_project.py`:

- `download_data()` downloads the public dataset ZIP and extracts only the expected filenames.
- `load()` imports CSVs, keeps missing values as NULL, checks business keys and validates relationships.
- Monetary values are stored as integer cents: BRL 12.34 becomes 1234. This avoids floating-point rounding problems in sales sums.
- `validate_model()` reconciles fact-table counts and sales to the source.
- `aggregate()` stores additive components, so filtered rates are recalculated from total numerators and denominators rather than averaged percentages.
- `reports()` generates HTML, CSV, JSON and the executive summary.

In `sql/model.sql`:

- `item_totals` and `review_totals` reduce child tables to order grain.
- `order_fact` is the main table, with one row per order.
- `seller_fact` includes only single-seller orders because the delivery timestamp describes the whole order.
- `category_fact` has one row per order/category. Orders spanning categories appear in each; category order counts cannot be summed to produce overall orders. Category sales remain additive.

For permanent offline dashboard changes, edit `dashboard_template.html`. The generated `reports/dashboard.html` is overwritten on rebuild. The native Streamlit interface is implemented separately in `streamlit_app.py`.

## 9. Use and interpret the dashboard

- **Purchase year and customer state:** update all metrics and charts. The year is the purchase year, not the delivery year.
- **Minimum eligible orders:** applies to state, seller and category rankings, not headline metrics.
- **Monthly sales:** shows delivered merchandise sales by purchase month. Sparse boundary months are not comparable to full months.
- **Regional priorities:** compare both late counts and rates.
- **Seller queue:** consider sample size and order mix; the threshold is a screening rule, not a significance test.
- **Reviews:** compare scores alongside the number of reviewed eligible orders.
- **Download sellers:** exports all qualifying sellers in the current selection, not only the displayed top 15.

For example, SP's late rate is **4.49%**, below the overall **6.77%**. However, SP has **1,820 late orders**, making it the first priority by volume. Calling SP the worst-performing state would be an inaccurate interpretation.

## 10. Verified findings and proposed actions

1. **Delivery reliability:** 6,534 of 96,470 eligible deliveries were late, a 6.77% baseline.
2. **Review association:** reviewed on-time orders averaged 4.29/5; reviewed late orders averaged 2.27/5. This does not isolate the causal effect of delays.
3. **Seller screening:** the highest late-volume qualifying seller had 168 late deliveries among 1,673 eligible single-seller orders, a 10.04% rate.

Proposed actions: investigate high-volume delayed routes, review flagged sellers' dispatch and carrier handoffs, and test proactive delay notifications with a controlled experiment. No improvement has been implemented or measured in this project.

Read `reports/executive_summary.md`, then write your own one-page interpretation with the business problem, period, three findings, three actions, definitions and limitations.

## 11. Validation and quality limitations

The pipeline has 15 logged checks covering unique/non-null keys, matching references, one row per order, sales reconciliation, category reconciliation and SQLite integrity. Additional input checks reject invalid review scores and purchase timestamps.

Six analytical tests cover same-day delivery, missing/canceled/invalid timelines, join inflation, multi-seller handling, different sales/delivery populations and an independent raw-CSV reconciliation. `test_streamlit.py` separately checks rendering, filtered metrics, empty rankings and reset behavior.

Source quality counts:

- 547 orders have multiple review records; records are averaged per order.
- 8 delivered orders are excluded from delivery metrics.
- 1,278 multi-seller orders are excluded from seller rankings, but remain in overall analysis.
- 610 products have missing categories, mapped to Unknown where appropriate.
- 768 orders have no reviews; missing scores are not replaced with zero.

See `reports/validation.json` for source counts, SHA-256 hashes and exclusions.

## 12. Resume and interview presentation

**Title:** E-commerce Delivery & Seller Performance Analysis

**Tools:** Python, SQL, SQLite, DBeaver and Streamlit.

Suggested resume bullet after reproducing and understanding the work:

> Analyzed 99,441 Olist orders using Python and SQL, validated order-level joins and sales totals, and built an interactive dashboard identifying a 6.77% late-delivery rate and seller/regional investigation priorities.

Suggested interview explanation:

> “The goal was to prioritize delivery investigations. I loaded seven related CSVs into SQLite, validated keys and relationships, and aggregated item and review records before joining them to avoid inflating sales. Of 99,441 orders, 96,470 were eligible for delivery analysis and 6.77% were late. The dashboard supports year/state filters and seller comparisons. I documented missing-data rules and treated review differences as observational associations rather than causal effects.”

Be prepared to explain why direct joins can multiply sales, why the late-rate denominator excludes some orders, why same-day arrival is on time, why multi-seller orders are excluded from seller rankings, and how proposed actions differ from achieved outcomes.

## 13. Publish and maintain the project

Publish source, documentation, tests, aggregate data and selected reports. Keep raw CSVs, databases, virtual environments and secrets out of Git. The included `.gitignore` handles these exclusions.

Retain Olist attribution and the source link. Check the dataset's license before redistributing raw data. Add a dashboard screenshot and a concise summary to the repository. On macOS, **Shift + Command + 4** captures a selected area.

Use `DEPLOYMENT.md` to publish on Streamlit Community Cloud. Add only the verified deployed URL to the README and resume.

## 14. Troubleshooting

| Problem | Fix |
|---|---|
| Python cannot find `run_project.py` | Change Terminal to the project folder |
| Missing CSV error | Run with `--download` or copy the seven source files into `data/raw` |
| Kaggle returns an access/login error | Download the source ZIP manually; no Kaggle credentials are stored in this project |
| `python` is not found | Use `python3`; inside an activated virtual environment, `python` should also work |
| Streamlit module missing | Activate the virtual environment and install `requirements.txt` |
| DBeaver shows no tables | Select the generated `build/olist.sqlite`, not a new empty database |
| DBeaver driver download fails | Retry with internet access; the pipeline and dashboard do not depend on DBeaver |
| No seller groups appear | Broaden filters or reduce the minimum sample threshold |
| Snapshot is out of date | Rebuild with `run_project.py`, then run `prepare_streamlit.py` |
| Model edits disappear | Edit `sql/model.sql`, not only the generated database |

The project is complete for portfolio purposes when you can reproduce its results, explain its definitions and limitations, and describe your own interpretation clearly.
