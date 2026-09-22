"""Meaningful metric tests, including a separate CSV-level reconciliation.
Run after building: python3 -m unittest -v test_project.py
"""
import csv
from datetime import datetime
from decimal import Decimal
import json
import sqlite3
import unittest
from run_project import ROOT, aggregate


class ModelEdgeCases(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE orders(order_id,customer_id,order_status,order_purchase_timestamp,
                            order_delivered_customer_date,order_estimated_delivery_date);
        CREATE TABLE customers(customer_id,customer_unique_id,customer_state);
        CREATE TABLE items(order_id,order_item_id,product_id,seller_id,price_cents,freight_cents);
        CREATE TABLE reviews(order_id,review_score);
        CREATE TABLE sellers(seller_id,seller_city,seller_state);
        CREATE TABLE products(product_id,product_category_name);
        CREATE TABLE category_translation(product_category_name,product_category_name_english);
        INSERT INTO customers VALUES('c','unique-c','SP');
        INSERT INTO sellers VALUES('s1','city1','SP'),('s2','city2','RJ');
        INSERT INTO products VALUES('p1','cat1'),('p2','cat2');
        INSERT INTO orders VALUES
          ('same','c','delivered','2018-01-01 10:00:00','2018-01-05 23:59:59','2018-01-05 00:00:00'),
          ('late','c','delivered','2018-01-01 10:00:00','2018-01-06 00:00:01','2018-01-05 00:00:00'),
          ('missing','c','delivered','2018-01-01 10:00:00',NULL,'2018-01-05 00:00:00'),
          ('cancel','c','canceled','2018-01-01 10:00:00',NULL,'2018-01-05 00:00:00'),
          ('invalid','c','delivered','2018-01-01 10:00:00','2017-12-31 00:00:00','2018-01-05 00:00:00');
        INSERT INTO items VALUES
          ('same',1,'p1','s1',1000,100),('same',2,'p1','s1',2000,100),
          ('late',1,'p1','s1',4000,100),('late',2,'p2','s2',5000,100),
          ('missing',1,'p1','s1',6000,100),('cancel',1,'p1','s1',9000,100),
          ('invalid',1,'p1','s1',7000,100);
        INSERT INTO reviews VALUES('same',1),('same',5),('late',2);
        ''')
        self.db.executescript((ROOT / 'sql/model.sql').read_text())

    def tearDown(self):
        self.db.close()

    def test_same_promised_day_is_on_time(self):
        self.assertEqual(self.db.execute("SELECT is_late FROM order_fact WHERE order_id='same'").fetchone()[0], 0)

    def test_missing_canceled_and_invalid_dates_excluded(self):
        r = self.db.execute('SELECT SUM(eligible_delivery),SUM(is_late) FROM order_fact').fetchone()
        self.assertEqual(tuple(r), (2, 1))

    def test_multiple_items_and_reviews_do_not_multiply_sales(self):
        r = self.db.execute("SELECT item_sales_cents,review_score FROM order_fact WHERE order_id='same'").fetchone()
        self.assertEqual(tuple(r), (3000, 3))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM order_fact').fetchone()[0], 5)

    def test_multiseller_excluded_but_categories_reconcile(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM seller_fact WHERE order_id='late'").fetchone()[0], 0)
        r = self.db.execute("SELECT COUNT(*),SUM(category_sales_cents) FROM category_fact WHERE order_id='late'").fetchone()
        self.assertEqual(tuple(r), (2, 9000))

    def test_sales_include_delivered_with_missing_delivery_dates(self):
        # Status is enough for sales; delivery eligibility is a separate definition.
        r = aggregate(self.db, 'order_fact', 'purchase_month')[0]
        self.assertEqual(r['sales_cents'], 25000)
        self.assertEqual(r['sales_orders'], 4)
        self.assertEqual(r['eligible'], 2)


class RealDataControls(unittest.TestCase):
    def test_independent_csv_metrics(self):
        raw = ROOT / 'data/raw'
        if not (raw / 'olist_orders_dataset.csv').exists():
            self.skipTest('Download and run project first for real-data reconciliation')
        with (raw / 'olist_orders_dataset.csv').open(encoding='utf-8-sig', newline='') as f:
            orders = list(csv.DictReader(f))
        delivered = {r['order_id'] for r in orders if r['order_status'] == 'delivered'}
        eligible = late = 0
        for r in orders:
            if r['order_status'] != 'delivered':
                continue
            try:
                purchase = datetime.fromisoformat(r['order_purchase_timestamp'])
                actual = datetime.fromisoformat(r['order_delivered_customer_date'])
                promised = datetime.fromisoformat(r['order_estimated_delivery_date'])
            except ValueError:
                continue
            if actual < purchase or promised.date() < purchase.date():
                continue
            eligible += 1
            late += actual.date() > promised.date()
        with (raw / 'olist_order_items_dataset.csv').open(encoding='utf-8-sig', newline='') as f:
            sales = sum((Decimal(r['price']) for r in csv.DictReader(f) if r['order_id'] in delivered), Decimal(0))
        summary = json.loads((ROOT / 'reports/summary.json').read_text())
        self.assertEqual(len(orders), summary['all_orders'])
        self.assertEqual(len(delivered), summary['delivered_orders'])
        self.assertEqual(eligible, summary['eligible_orders'])
        self.assertEqual(late, summary['late_orders'])
        self.assertEqual(sales, Decimal(str(summary['delivered_sales_brl'])))


if __name__ == '__main__':
    unittest.main()
