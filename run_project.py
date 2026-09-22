"""Olist analytics pipeline. Run: python3 run_project.py --download

Standard library only: CSV -> validated SQLite -> SQL metrics -> offline report.
Run without --download to reuse data/raw. Existing generated outputs are rebuilt.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCE = 'https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce'
DOWNLOAD = 'https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce'
FILES = {
    'orders': 'olist_orders_dataset.csv',
    'customers': 'olist_customers_dataset.csv',
    'items': 'olist_order_items_dataset.csv',
    'sellers': 'olist_sellers_dataset.csv',
    'products': 'olist_products_dataset.csv',
    'reviews': 'olist_order_reviews_dataset.csv',
    'category_translation': 'product_category_name_translation.csv',
}
KEYS = {'orders': ['order_id'], 'customers': ['customer_id'],
        'items': ['order_id', 'order_item_id'], 'sellers': ['seller_id'],
        'products': ['product_id'], 'category_translation': ['product_category_name']}


def rows(db, query):
    return [dict(r) for r in db.execute(query)]


def scalar(db, query):
    return db.execute(query).fetchone()[0]


def download_data(raw):
    archive = ROOT / 'data' / 'olist.zip'
    print('Downloading public Olist data from Kaggle...')
    subprocess.run(['curl', '-L', '--fail', '--max-time', '180', DOWNLOAD,
                    '-o', str(archive)], check=True)
    if not zipfile.is_zipfile(archive):
        raise ValueError('Kaggle returned a non-ZIP response. Download manually; see README.')
    with zipfile.ZipFile(archive) as z:
        # Extract only known filenames. No arbitrary archive paths are trusted.
        for filename in FILES.values():
            (raw / filename).write_bytes(z.read(filename))


def load(db, raw):
    audit = {'source': SOURCE, 'generated_utc': datetime.now(timezone.utc).isoformat(),
             'tables': {}, 'checks': [], 'warnings': {}}
    for table, filename in FILES.items():
        path = raw / filename
        if not path.exists():
            raise FileNotFoundError(f'Missing {path}. Run with --download or copy Kaggle CSVs into data/raw.')
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames
            if not columns or any(not c.replace('_', '').isalnum() for c in columns):
                raise ValueError(f'Unexpected CSV headers: {filename}')
            data = [tuple(None if v == '' else v for v in row.values()) for row in reader]
        extra = ', price_cents INTEGER, freight_cents INTEGER' if table == 'items' else ''
        db.execute(f'CREATE TABLE {table} (' + ','.join(f'"{c}" TEXT' for c in columns) + extra + ')')
        if table == 'items':
            pi, fi = columns.index('price'), columns.index('freight_value')
            def cents(value):
                if value is None:
                    raise ValueError('Missing price/freight: inspect source before analysis.')
                x = Decimal(value) * 100
                if not x.is_finite() or x != x.to_integral_value() or x < 0:
                    raise ValueError(f'Invalid monetary value: {value}')
                return int(x)
            data = [r + (cents(r[pi]), cents(r[fi])) for r in data]
        if not data:
            raise ValueError(f'Empty source table: {table}')
        db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in data[0])})', data)
        audit['tables'][table] = {'rows': len(data), 'file': filename,
                                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        if table in KEYS:
            keys = KEYS[table]
            nulls = scalar(db, f'SELECT COUNT(*) FROM {table} WHERE ' + ' OR '.join(f'{k} IS NULL' for k in keys))
            if nulls:
                raise ValueError(f'{table}: {nulls} missing keys')
            # Unique index fails clearly on duplicate business keys.
            db.execute(f'CREATE UNIQUE INDEX key_{table} ON {table} ({",".join(keys)})')
            audit['checks'].append(f'PASS: {table} keys are non-null and unique')
    for child, key, parent in [('orders', 'customer_id', 'customers'),
                                ('items', 'order_id', 'orders'),
                                ('items', 'product_id', 'products'),
                                ('items', 'seller_id', 'sellers'),
                                ('reviews', 'order_id', 'orders')]:
        n = scalar(db, f'SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p USING({key}) WHERE p.{key} IS NULL')
        if n:
            raise ValueError(f'{child}: {n} unmatched {key} values')
        audit['checks'].append(f'PASS: {child}.{key} references {parent}')
    bad_scores = scalar(db, "SELECT COUNT(*) FROM reviews WHERE review_score IS NULL OR review_score NOT IN ('1','2','3','4','5')")
    if bad_scores:
        raise ValueError(f'{bad_scores} invalid review scores')
    bad_purchases = scalar(db, 'SELECT COUNT(*) FROM orders WHERE julianday(order_purchase_timestamp) IS NULL')
    if bad_purchases:
        raise ValueError(f'{bad_purchases} invalid purchase timestamps')
    audit['warnings']['orders_with_multiple_reviews'] = scalar(db,
        'SELECT COUNT(*) FROM (SELECT order_id FROM reviews GROUP BY order_id HAVING COUNT(*)>1)')
    audit['warnings']['products_without_category'] = scalar(db,
        'SELECT COUNT(*) FROM products WHERE product_category_name IS NULL')
    return audit


def validate_model(db, audit):
    original = scalar(db, 'SELECT COUNT(*) FROM orders')
    fact = scalar(db, 'SELECT COUNT(*) FROM order_fact')
    if original != fact:
        raise AssertionError('Order grain changed during joins')
    audit['checks'].append(f'PASS: order grain preserved ({fact:,} rows)')
    source_sales = scalar(db, 'SELECT SUM(price_cents) FROM items')
    fact_sales = scalar(db, 'SELECT SUM(item_sales_cents) FROM order_fact')
    if source_sales != fact_sales:
        raise AssertionError('Item sales reconciliation failed')
    audit['checks'].append(f'PASS: all-status item sales reconcile exactly ({source_sales} cents)')
    source_delivered = scalar(db, "SELECT SUM(i.price_cents) FROM items i JOIN orders o USING(order_id) WHERE o.order_status='delivered'")
    category_delivered = scalar(db, "SELECT SUM(category_sales_cents) FROM category_fact WHERE order_status='delivered'")
    if source_delivered != category_delivered:
        raise AssertionError('Category sales reconciliation failed')
    audit['checks'].append('PASS: delivered category sales reconcile to source items')
    audit['warnings']['delivered_orders_excluded_from_delivery_kpis'] = scalar(db,
        "SELECT COUNT(*) FROM order_fact WHERE order_status='delivered' AND eligible_delivery=0")
    audit['warnings']['delivered_orders_missing_items'] = scalar(db,
        "SELECT COUNT(*) FROM order_fact WHERE order_status='delivered' AND item_sales_cents IS NULL")
    audit['warnings']['multi_seller_orders_excluded_from_seller_ranking'] = scalar(db,
        'SELECT COUNT(*) FROM order_fact WHERE seller_count>1')
    audit['warnings']['orders_without_reviews'] = scalar(db,
        'SELECT COUNT(*) FROM order_fact WHERE review_score IS NULL')
    audit['warnings']['orders_without_items'] = scalar(db,
        'SELECT COUNT(*) FROM order_fact WHERE item_sales_cents IS NULL')
    audit['warnings']['missing_customer_states'] = scalar(db,
        'SELECT COUNT(*) FROM order_fact WHERE customer_state IS NULL')
    audit['checks'].append('PASS: SQLite integrity_check = ' + scalar(db, 'PRAGMA integrity_check'))


def aggregate(db, table, dimension, sales='item_sales_cents'):
    # Additive components allow correct weighted reaggregation for dashboard filters.
    return rows(db, f'''SELECT purchase_year AS year,customer_state AS state,
      {dimension} AS label,COUNT(*) AS orders,
      SUM(order_status='delivered') AS delivered,
      SUM(order_status='delivered' AND {sales} IS NOT NULL) AS sales_orders,
      COALESCE(SUM(CASE WHEN order_status='delivered' THEN {sales} END),0) AS sales_cents,
      SUM(eligible_delivery) AS eligible,COALESCE(SUM(is_late),0) AS late,
      COALESCE(SUM(delivery_days),0) AS days_sum,
      COALESCE(SUM(CASE WHEN eligible_delivery=1 THEN review_score END),0) AS review_sum,
      SUM(eligible_delivery=1 AND review_score IS NOT NULL) AS reviewed
      FROM {table} GROUP BY purchase_year,customer_state,{dimension}''')


def export_csv(path, records):
    if records:
        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)


def reports(db, audit, dest):
    overall = rows(db, '''SELECT COUNT(*) AS all_orders,
        MIN(date(order_purchase_timestamp)) AS first_purchase,
        MAX(date(order_purchase_timestamp)) AS last_purchase,
        SUM(order_status='delivered') AS delivered_orders,
        SUM(CASE WHEN order_status='delivered' THEN item_sales_cents END)/100.0 AS delivered_sales_brl,
        SUM(CASE WHEN order_status='delivered' THEN item_sales_cents END)/100.0/
          NULLIF(SUM(order_status='delivered' AND item_sales_cents IS NOT NULL),0) AS aov_brl,
        SUM(eligible_delivery) AS eligible_orders,SUM(is_late) AS late_orders,
        100.0*SUM(is_late)/NULLIF(SUM(eligible_delivery),0) AS late_pct,
        AVG(delivery_days) AS avg_delivery_days FROM order_fact''')[0]
    states = rows(db, '''SELECT customer_state,SUM(eligible_delivery) AS eligible_orders,
        SUM(is_late) AS late_orders,100.0*SUM(is_late)/SUM(eligible_delivery) AS late_pct
        FROM order_fact GROUP BY customer_state HAVING SUM(eligible_delivery)>=100 ORDER BY late_orders DESC''')
    sellers = rows(db, '''SELECT sole_seller_id AS seller_id,seller_city,seller_state,
        SUM(eligible_delivery) AS eligible_orders,SUM(is_late) AS late_orders,
        100.0*SUM(is_late)/SUM(eligible_delivery) AS late_pct
        FROM seller_fact GROUP BY sole_seller_id,seller_city,seller_state
        HAVING SUM(eligible_delivery)>=100 ORDER BY late_orders DESC,seller_id''')
    reviews = rows(db, '''SELECT CASE WHEN is_late=1 THEN 'Late' ELSE 'On time' END AS delivery_group,
        COUNT(*) AS eligible_orders,COUNT(review_score) AS reviewed_orders,AVG(review_score) AS mean_review
        FROM order_fact WHERE eligible_delivery=1 GROUP BY is_late''')
    payload = {'overall': overall, 'warnings': audit['warnings'],
               'monthly': aggregate(db, 'order_fact', 'purchase_month'),
               'sellers': aggregate(db, 'seller_fact', 'sole_seller_id'),
               'categories': aggregate(db, 'category_fact', 'category', 'category_sales_cents'),
               'reviews': rows(db, '''SELECT purchase_year AS year,customer_state AS state,is_late,
                  COUNT(*) AS eligible,COUNT(review_score) AS reviewed,COALESCE(SUM(review_score),0) AS review_sum
                  FROM order_fact WHERE eligible_delivery=1 GROUP BY purchase_year,customer_state,is_late''')}
    for name, data in [('monthly', payload['monthly']), ('seller_priority', sellers),
                       ('state_priority', states), ('reviews_by_delivery', reviews),
                       ('category_by_year_state', payload['categories'])]:
        export_csv(dest / f'{name}.csv', data)
    (dest / 'summary.json').write_text(json.dumps(overall, indent=2), encoding='utf-8')
    (dest / 'validation.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    template = (ROOT / 'dashboard_template.html').read_text(encoding='utf-8')
    embedded = json.dumps(payload, separators=(',', ':')).replace('<', '\\u003c')
    (dest / 'dashboard.html').write_text(template.replace('__ANALYTICS_DATA__', embedded), encoding='utf-8')
    top_state, top_seller = states[0], sellers[0]
    review_text = '\n'.join(f"- {r['delivery_group']}: mean {r['mean_review']:.2f}/5 across {r['reviewed_orders']:,} reviewed eligible orders." for r in reviews)
    memo = f'''# Olist delivery and seller performance

Source: [Olist Brazilian E-commerce]({SOURCE}). Historical analysis, not current operations.
Purchase dates: {overall['first_purchase']} to {overall['last_purchase']}. Sparse boundary months are included but should not be used as full-month growth comparisons.

## Verified results
- {overall['all_orders']:,} orders; {overall['delivered_orders']:,} have delivered status.
- Delivered merchandise sales: BRL {overall['delivered_sales_brl']:,.2f}; merchandise AOV: BRL {overall['aov_brl']:,.2f}.
- {overall['late_orders']:,} late orders / {overall['eligible_orders']:,} eligible delivered orders = {overall['late_pct']:.2f}%.
- Mean purchase-to-delivery duration: {overall['avg_delivery_days']:.2f} days among eligible orders.
{review_text}

## Three proposed actions
1. Investigate customer state {top_state['customer_state']} first by late-order volume: {top_state['late_orders']:,} late / {top_state['eligible_orders']:,} eligible ({top_state['late_pct']:.2f}%). Compare lanes and delivery promises within this region before changing operations.
2. Review seller {top_seller['seller_id']} ({top_seller['seller_city']}, {top_seller['seller_state']}): {top_seller['late_orders']:,} late / {top_seller['eligible_orders']:,} eligible single-seller orders ({top_seller['late_pct']:.2f}%). Inspect dispatch, destination mix and carrier handoffs; this is a screening priority, not proof of seller fault.
3. Test proactive delay notifications on a randomized eligible customer group; measure satisfaction and support contacts. Review-score differences are observational and do not establish the effect of delivery delays or the proposed intervention.

## Measurement and limits
- Sales are item prices on delivered orders, excluding freight. These are marketplace merchandise sales, not Olist commission revenue or profit. Refund/cost data are unavailable.
- Late means actual delivery CALENDAR DATE is later than estimated calendar date. Same-day delivery is on time.
- Delivery denominator requires delivered status, valid purchase/actual/estimated dates and nonnegative date sequence. Excluded delivered records: {audit['warnings']['delivered_orders_excluded_from_delivery_kpis']}.
- Multiple reviews are averaged per order before comparing groups. Missing reviews are excluded from review means; group sample counts are reported.
- Seller comparison includes single-seller orders only, minimum 100 eligible orders. This is a practical screening threshold, not statistical significance.
- Category delivery is order/category exposure. Orders spanning categories appear in each category; category order counts are not additive.
- Geography, seasonality and order mix may confound comparisons. No intervention was implemented and no revenue/delivery uplift is claimed.

## Resume wording after reviewing and reproducing the project
Built a reproducible Python and SQL analysis of {overall['all_orders']:,} Olist orders; validated join grain and merchandise-sales totals, measured a {overall['late_pct']:.2f}% late-delivery rate, and created an interactive dashboard to prioritize seller and regional investigations.

## Plain-English explanation
{overall['eligible_orders']:,} orders were eligible for delivery analysis. Of these, {overall['late_orders']:,} arrived after their promised calendar date, giving a late rate of {overall['late_pct']:.2f}%. Canceled orders and records with missing or invalid delivery timelines are excluded from this denominator. The recommendations are proposed actions; their business impact has not been measured.
'''
    (dest / 'executive_summary.md').write_text(memo, encoding='utf-8')
    return overall


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Download source CSVs from Kaggle')
    args = parser.parse_args()
    raw, build, dest = ROOT / 'data/raw', ROOT / 'build', ROOT / 'reports'
    for directory in [raw, build, dest]:
        directory.mkdir(parents=True, exist_ok=True)
    if args.download:
        download_data(raw)
    pending = build / 'olist.pending.sqlite'
    if pending.exists():
        pending.unlink()
    with sqlite3.connect(pending) as db:
        db.row_factory = sqlite3.Row
        audit = load(db, raw)
        db.executescript((ROOT / 'sql/model.sql').read_text())
        validate_model(db, audit)
        overall = reports(db, audit, dest)
        db.commit()
    db.close()
    pending.replace(build / 'olist.sqlite')
    print(json.dumps(overall, indent=2))
    print(f"Validation: {len(audit['checks'])} checks passed")
    print('Dashboard:', dest / 'dashboard.html')
    print('DBeaver database:', build / 'olist.sqlite')


if __name__ == '__main__':
    main()
