import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Chinook Music Dashboard", layout="wide")
st.title("Chinook Music Store Dashboard")

USER     = "readonly_user.tyxjmbptftftcqgozyfc"
PASSWORD = "your_secure_password"
HOST     = "aws-1-us-east-1.pooler.supabase.com"
PORT     = "6543"
DBNAME   = "postgres"

DB_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

@st.cache_data                          # ← added @ here ✅
def load_data():
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        invoices = pd.read_sql(text("""
            SELECT i.invoice_id, i.customer_id, i.invoice_date,
                   i.billing_country, i.total
            FROM invoice i
        """), conn)

        invoice_line_detail = pd.read_sql(text("""
            SELECT il.invoice_id,
                   ar.name AS artist,
                   il.unit_price * il.quantity AS line_total
            FROM invoice_line il
            JOIN track t  ON il.track_id  = t.track_id
            JOIN album al ON t.album_id   = al.album_id
            JOIN artist ar ON al.artist_id = ar.artist_id
        """), conn)

    invoices['invoice_date'] = pd.to_datetime(invoices['invoice_date'])

    return invoices, invoice_line_detail        # ← properly indented ✅

invoices, invoice_line_detail = load_data()

# ── Quick Preview to Test ─────────────────────────────
st.subheader("Invoice Preview")
st.dataframe(invoices.head())

st.subheader("Line Detail Preview")
st.dataframe(invoice_line_detail.head())

#Sidebar Filters
st.sidebar.header("Filters")

country_options = ["All Countries"] + sorted(invoices['billing_country'].unique())
selected_country = st.sidebar.selectbox("Country", options=country_options)

data_min_date = invoices['invoice_date'].min().date()
data_max_date = invoices['invoice_date'].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    value=(data_min_date, data_max_date)
)

# Guard: date_input returns a 1-tuple while user is still picking the end date
if len(date_range) != 2:
    st.info("Please select an end date to continue.")
    st.stop()

country_mask = True if selected_country == "All Countries" else invoices['billing_country'] == selected_country
invoices = invoices[
    country_mask &
    (invoices['invoice_date'].dt.date >= date_range[0]) &
    (invoices['invoice_date'].dt.date <= date_range[1])
]

# Artist revenue computed from filtered invoice IDs only
filtered_invoice_ids = invoices['invoice_id'].tolist()
artist_revenue = (
    invoice_line_detail[invoice_line_detail['invoice_id'].isin(filtered_invoice_ids)]
    .groupby('artist')['line_total']
    .sum()
    .round(2)
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
    .rename(columns={'line_total': 'revenue'})
)

#Key Metrics
st.header("Key Metrics")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Revenue", f"${invoices['total'].sum():,.2f}")

with col2:
    st.metric("Total Invoices", f"{len(invoices):,}")

with col3:
    st.metric("Total Customers", f"{invoices['customer_id'].nunique():,}")

st.divider()

#Top 10 Artists by Revenue
st.header("Top 10 Artists by Revenue")

fig1 = sns.catplot(x='revenue', y='artist', data=artist_revenue, kind='bar', height=6, aspect=1.6)
fig1.set_axis_labels('Revenue ($)', 'Artist')
fig1.ax.set_title('Top 10 Artists by Revenue')
for bar in fig1.ax.patches:
    fig1.ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                 f"${bar.get_width():,.2f}", va='center', ha='left', fontsize=9)
st.pyplot(fig1)

st.divider()

#Monthly Revenue Trend
st.header("Monthly Revenue Trend")

invoices['month'] = invoices['invoice_date'].dt.strftime('%Y-%m')
monthly = invoices.groupby('month')['total'].sum().reset_index()

fig2 = sns.relplot(x='month', y='total', data=monthly, kind='line', marker='o', height=5, aspect=2)
fig2.set_axis_labels('Month', 'Revenue ($)')
fig2.ax.set_title('Monthly Revenue Trend')
fig2.ax.grid(True, alpha=0.3)
plt.xticks(rotation=45)
st.pyplot(fig2)

st.divider()

#Revenue by Country
st.header("Revenue by Country")

country_rev = (
    invoices.groupby('billing_country')['total']
    .sum()
    .sort_values(ascending=False)
    .reset_index()
    .rename(columns={'billing_country': 'country', 'total': 'revenue'})
)

fig3 = sns.catplot(x='revenue', y='country', data=country_rev, kind='bar', height=8, aspect=1.2)
fig3.set_axis_labels('Revenue ($)', 'Country')
fig3.ax.set_title('Revenue by Country')
for bar in fig3.ax.patches:
    fig3.ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                 f"${bar.get_width():,.2f}", va='center', ha='left', fontsize=9)
st.pyplot(fig3)

st.divider()

#Raw Data Table
st.header("Raw Invoice Data")
st.dataframe(invoices, use_container_width=True)
