# Olist delivery and seller performance

Source: [Olist Brazilian E-commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Historical analysis, not current operations.
Purchase dates: 2016-09-04 to 2018-10-17. Sparse boundary months are included but should not be used as full-month growth comparisons.

## Verified results
- 99,441 orders; 96,478 have delivered status.
- Delivered merchandise sales: BRL 13,221,498.11; merchandise AOV: BRL 137.04.
- 6,534 late orders / 96,470 eligible delivered orders = 6.77%.
- Mean purchase-to-delivery duration: 12.56 days among eligible orders.
- On time: mean 4.29/5 across 89,443 reviewed eligible orders.
- Late: mean 2.27/5 across 6,381 reviewed eligible orders.

## Three proposed actions
1. Investigate customer state SP first by late-order volume: 1,820 late / 40,494 eligible (4.49%). Compare lanes and delivery promises within this region before changing operations.
2. Review seller 4a3ca9315b744ce9f8e9374361493884 (ibitinga, SP): 168 late / 1,673 eligible single-seller orders (10.04%). Inspect dispatch, destination mix and carrier handoffs; this is a screening priority, not proof of seller fault.
3. Test proactive delay notifications on a randomized eligible customer group; measure satisfaction and support contacts. Review-score differences are observational and do not establish the effect of delivery delays or the proposed intervention.

## Measurement and limits
- Sales are item prices on delivered orders, excluding freight. These are marketplace merchandise sales, not Olist commission revenue or profit. Refund/cost data are unavailable.
- Late means actual delivery CALENDAR DATE is later than estimated calendar date. Same-day delivery is on time.
- Delivery denominator requires delivered status, valid purchase/actual/estimated dates and nonnegative date sequence. Excluded delivered records: 8.
- Multiple reviews are averaged per order before comparing groups. Missing reviews are excluded from review means; group sample counts are reported.
- Seller comparison includes single-seller orders only, minimum 100 eligible orders. This is a practical screening threshold, not statistical significance.
- Category delivery is order/category exposure. Orders spanning categories appear in each category; category order counts are not additive.
- Geography, seasonality and order mix may confound comparisons. No intervention was implemented and no revenue/delivery uplift is claimed.

## Resume wording after reviewing and reproducing the project
Built a reproducible Python and SQL analysis of 99,441 Olist orders; validated join grain and merchandise-sales totals, measured a 6.77% late-delivery rate, and created an interactive dashboard to prioritize seller and regional investigations.

## Plain-English explanation
96,470 orders were eligible for delivery analysis. Of these, 6,534 arrived after their promised calendar date, giving a late rate of 6.77%. Canceled orders and records with missing or invalid delivery timelines are excluded from this denominator. The recommendations are proposed actions; their business impact has not been measured.
