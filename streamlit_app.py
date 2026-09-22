"""Streamlit deployment: streamlit run streamlit_app.py"""
import gzip
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Olist | Delivery & Seller Performance', page_icon='📦', layout='wide')


@st.cache_data
def load_data():
    with gzip.open(ROOT / 'reports/app_data.json.gz', 'rt', encoding='utf-8') as f:
        return json.load(f)


try:
    data = load_data()
except (OSError, ValueError):
    st.error('The analytics snapshot is missing or unreadable. Include reports/app_data.json.gz in the repository.')
    st.stop()

FIELDS = ['orders','delivered','sales_orders','sales_cents','eligible','late','days_sum','review_sum','reviewed']


def frame(name):
    df = pd.DataFrame(data[name])
    if year != 'All years':
        df = df[df['year'] == year]
    if state != 'All states':
        df = df[df['state'] == state]
    return df


def grouped(df, key='label'):
    return df.groupby(key, dropna=False)[FIELDS].sum().reset_index()


def ranked(df, key='label'):
    result = grouped(df, key)
    result = result[result.eligible >= minimum].copy()
    result['late_pct'] = 100 * result.late / result.eligible
    return result.sort_values(['late', key], ascending=[False, True])


def reset():
    st.session_state.year = 'All years'
    st.session_state.state = 'All states'
    st.session_state.minimum = 100


st.caption('OLIST / HISTORICAL MARKETPLACE ANALYSIS')
st.title('Delivery & seller performance')
st.write('Where should the operations team investigate delivery delays first?')
with st.sidebar:
    st.header('Explore the data')
    year = st.selectbox('Purchase year', ['All years'] + sorted({x['year'] for x in data['monthly']}), key='year')
    state = st.selectbox('Customer state', ['All states'] + sorted({x['state'] for x in data['monthly'] if x['state']}), key='state')
    if 'minimum' not in st.session_state:
        st.session_state.minimum = 100
    minimum = st.selectbox('Minimum eligible orders', [30, 100, 300], key='minimum')
    st.button('Reset filters', on_click=reset)
    st.caption('Minimum sample applies to state, seller and category rankings. Headline metrics use every order in scope.')
    st.divider()
    st.caption('Historical purchase dates: 4 September 2016 to 17 October 2018. Currency: Brazilian real (BRL).')
    st.markdown('[Source: Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)')

monthly = frame('monthly')
t = monthly[FIELDS].sum()
eligible, late = int(t.eligible), int(t.late)
c1,c2,c3,c4 = st.columns(4)
c1.metric('Orders in scope', f'{int(t.orders):,}')
c1.caption(f'{int(t.delivered):,} delivered orders')
c2.metric('Delivered item sales', f'R$ {t.sales_cents/100:,.0f}')
c2.caption(f'Item AOV: R$ {t.sales_cents/100/t.sales_orders:,.2f}' if t.sales_orders else 'Item AOV: N/A')
c3.metric('Late-delivery rate', f'{100*late/eligible:.2f}%' if eligible else 'N/A')
c3.caption(f'{late:,} late / {eligible:,} eligible')
c4.metric('Mean delivery time', f'{t.days_sum/eligible:.1f} days' if eligible else 'N/A')
c4.caption('Purchase to customer delivery')

states = ranked(monthly, 'state')
if not states.empty:
    r = states.iloc[0]
    st.info(f"Investigation focus: {r['state']} — {int(r.late):,} late orders / {int(r.eligible):,} eligible ({r.late_pct:.2f}%). Ranked by volume; investigate order mix and delivery promises before assigning responsibility.")

left,right = st.columns(2)
with left:
    st.subheader('Monthly merchandise sales')
    trend = grouped(monthly).sort_values('label')
    trend['Sales (BRL)'] = trend.sales_cents / 100
    if trend.empty:
        st.info('No orders for this selection.')
    else:
        st.bar_chart(trend.set_index('label')[['Sales (BRL)']], color='#287a62')
    st.caption('Delivered item sales by purchase month. Boundary months may be partial or sparse. Freight is excluded.')
with right:
    st.subheader('Regional investigation priorities')
    if states.empty:
        st.info('No states meet the selected sample threshold.')
    else:
        st.bar_chart(states.head(7).set_index('state')[['late']], horizontal=True, color='#b25b37')
        st.dataframe(states[['state','eligible','late','late_pct']].head(7), hide_index=True,
                     column_config={'late_pct':st.column_config.NumberColumn('Late rate (%)',format='%.2f')})

left,right = st.columns(2)
sellers = ranked(frame('sellers'))
with left:
    st.subheader('Seller investigation queue')
    st.caption('Top 15 by late volume. Single-seller orders only.')
    if sellers.empty:
        st.info('No sellers meet the selected sample threshold.')
    else:
        display = sellers[['label','eligible','late','late_pct']].rename(columns={'label':'Seller ID','eligible':'Eligible orders','late':'Late orders','late_pct':'Late rate (%)'})
        st.dataframe(display.head(15), hide_index=True, column_config={'Late rate (%)':st.column_config.NumberColumn(format='%.2f')})
        st.download_button('Download all qualifying sellers', display.to_csv(index=False).encode(), 'seller_priority.csv', 'text/csv')
with right:
    st.subheader('Delivery experience & reviews')
    rev = frame('reviews')
    for col,is_late,label in zip(st.columns(2),[0,1],['On time','Late']):
        group = rev[rev.is_late == is_late]
        n = int(group.reviewed.sum())
        with col:
            st.metric(label, f'{group.review_sum.sum()/n:.2f} / 5' if n else 'N/A')
            st.caption(f'{n:,} reviewed eligible orders')
    st.write('This is an observed association. Geography, product mix and other factors may influence both outcomes.')

st.subheader('Categories to investigate')
categories = ranked(frame('categories'))
if categories.empty:
    st.info('No categories meet the selected sample threshold.')
else:
    categories['Sales (BRL)'] = categories.sales_cents / 100
    st.dataframe(categories[['label','eligible','late','late_pct','Sales (BRL)']].head(10).rename(columns={'label':'Category'}), hide_index=True,
                 column_config={'late_pct':st.column_config.NumberColumn('Late rate (%)',format='%.2f'),'Sales (BRL)':st.column_config.NumberColumn(format='%.2f')})
st.caption('Orders spanning categories appear in each category. Category order counts are not additive; item sales are additive.')

with st.expander('Definitions, data quality and limitations'):
    st.markdown('''
    - **Sales:** item prices on delivered orders, excluding freight. Not profit or Olist commission revenue.
    - **Late:** actual delivery calendar date is after the estimated date. Same-day delivery is on time.
    - **Eligible:** delivered status, valid purchase/actual/estimated dates, and a valid nonnegative timeline.
    - **Review mean:** multiple review records are first averaged per order. Missing reviews are excluded.
    - **Seller ranking:** single-seller orders only. Minimum sample is a screening choice, not a significance test.
    - **Scope:** historical data; sparse boundary months should not be interpreted as full-month growth changes.
    - **Interpretation:** no causal effects or achieved business improvements are claimed.
    ''')
    st.write('Full-dataset quality counts (not changed by dashboard filters):')
    st.json(data['warnings'])
with st.expander('How to use this dashboard'):
    st.write('Use this dashboard to prioritize regions and sellers for delivery investigations. Late rate measures reliability; the number of late orders measures the volume of affected customers. Compare both, and investigate carrier, destination and order mix before assigning responsibility.')
st.caption('Built with Python, SQL and Streamlit. The published app reads a validated aggregate snapshot; no customer-level records or credentials are required.')
