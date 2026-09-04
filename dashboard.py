import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency

st.set_page_config(
    page_title="Brazilian E-Commerce Dashboard",
    layout="wide"
)
sns.set_theme(style='dark')
# HELPER FUNCTIONS

def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='D', on='order_purchase_timestamp').agg({
        "order_id": "nunique",
        "payment_value": "sum"
    }).reset_index()
    daily_orders_df.rename(columns={
        "order_id": "order_count",
        "payment_value": "revenue"
    }, inplace=True)
    return daily_orders_df

def create_monthly_orders_df(df):
    monthly_orders_df = df.resample(rule='ME', on='order_purchase_timestamp').agg({
        "order_id": "nunique"
    })
    monthly_orders_df.index = monthly_orders_df.index.strftime('%Y-%m')
    monthly_orders_df = monthly_orders_df.reset_index()
    monthly_orders_df.rename(columns={
        "order_id": "order_count"
    }, inplace=True)
    return monthly_orders_df

def create_manual_grouping_df(df):
    # Filter order terkirim
    delivered_df = df[df['order_status'] == 'delivered'].copy() if 'order_status' in df.columns else df.copy()
    
    # Spend Category
    def classify_spend(value):
        if value < 50:
            return 'Low Spender'
        elif 50 <= value <= 200:
            return 'Medium Spender'
        elif 200 < value <= 500:
            return 'High Spender'
        else:
            return 'Super Spender'
            
    # Basket Size
    def classify_basket(items):
        if items == 1:
            return 'Single Item'
        elif 2 <= items <= 4:
            return 'Small Bundle (2-4 items)'
        else:
            return 'Bulk Purchase (>4 items)'
            
    delivered_df['spend_category'] = delivered_df['payment_value'].apply(classify_spend)
    delivered_df['basket_size'] = delivered_df['order_item_id'].apply(classify_basket)
    return delivered_df

def create_payment_analysis_df(df):
    payment_df = df.groupby("payment_type").agg(
        total_transactions=('order_id', 'nunique'),
        avg_transaction_value=('payment_value', 'mean'),
        total_volume_value=('payment_value', 'sum')
    ).reset_index()
    
    total_vol = payment_df['total_volume_value'].sum()
    payment_df['proportion_%'] = (payment_df['total_volume_value'] / total_vol) * 100
    return payment_df.sort_values(by="total_transactions", ascending=False)

def create_top_categories_df(df):
    cat_df = df.groupby("product_category_name_english").agg(
        total_revenue=('payment_value', 'sum'),
        total_orders=('order_id', 'nunique')
    ).reset_index()
    return cat_df.sort_values(by="total_revenue", ascending=False)


# LOAD & FILTER DATA

all_df = pd.read_csv("main_data.csv.gz")

# Format kolom waktu
datetime_columns = ["order_purchase_timestamp", "order_delivered_customer_date"]
all_df.sort_values(by="order_purchase_timestamp", inplace=True)
all_df.reset_index(drop=locals().get('drop_index', True), inplace=True)

for column in datetime_columns:
    if column in all_df.columns:
        all_df[column] = pd.to_datetime(all_df[column])

# Filter Sidebar
min_date = all_df["order_purchase_timestamp"].min()
max_date = all_df["order_purchase_timestamp"].max()

# daftar order_status
status_list = sorted(all_df["order_status"].dropna().unique().tolist())

with st.sidebar:
    # Filter Rentang waktu
    start_date, end_date = st.date_input(
        label='Rentang Waktu Transaksi',    
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

    # Filter order status
    selected_status = st.multiselect(
        label='Status Pesanan',
        options=status_list,
        default=status_list 
    )

if not selected_status:
    # Jika status kosong, gunakan semua status
    selected_status = status_list

main_df = all_df[
    (all_df["order_purchase_timestamp"].dt.date >= start_date) & 
    (all_df["order_purchase_timestamp"].dt.date <= end_date) &
    (all_df["order_status"].isin(selected_status))
]
# Olah Data
daily_orders_df = create_daily_orders_df(main_df)
monthly_orders_df = create_monthly_orders_df(main_df)
grouping_df = create_manual_grouping_df(main_df)
payment_df = create_payment_analysis_df(main_df)
top_cat_df = create_top_categories_df(main_df)

# DASHBOARD LAYOUT

st.header('Brazilian E-Commerce Dashboard')

# METRIK UTAMA
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Orders", value=f"{daily_orders_df.order_count.sum():,}")
with col2:
    st.metric("Total Revenue", value=format_currency(daily_orders_df.revenue.sum(), "BRL", locale='pt_BR'))

st.markdown("---")
# Grafik tren jumlah pesanan per bulan
st.subheader("Monthly Orders Trend")

# Membuat plot tren bulanan
fig_monthly, ax_monthly = plt.subplots(figsize=(10, 4), dpi=150)

ax_monthly.plot(
    monthly_orders_df["order_purchase_timestamp"],
    monthly_orders_df["order_count"],
    marker='o', 
    linewidth=2,
    color="#313695"
)

# Kustomisasi Tampilan Grafik
ax_monthly.set_title("Total Orders Per Month", fontsize=14, fontweight='bold', pad=15)
ax_monthly.set_xlabel("Month", fontsize=10)
ax_monthly.set_ylabel("Number of Orders", fontsize=10)
ax_monthly.tick_params(axis='x', rotation=45, labelsize=8)
ax_monthly.tick_params(axis='y', labelsize=8)
ax_monthly.grid(axis='y', linestyle='--', alpha=0.5)

fig_monthly.tight_layout()

# Menampilkan di Streamlit
st.pyplot(fig_monthly, use_container_width=True)

st.markdown("---")

# TOP KATEGORI PRODUK & METODE PEMBAYARAN
col_p1, col_p2 = st.columns(2)

# --- LEFT CHART: Top Categories ---
with col_p1:
    st.subheader("Top Categories by Revenue")
    
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    top_cat = top_cat_df.head(10)
    
    sns.barplot(
        data=top_cat, 
        x='total_revenue', 
        y='product_category_name_english', 
        palette='Blues_r',
        ax=ax
    )
    
    #  Mengganti underscores dengan spasi & kapitalisasi
    formatted_labels = [label.get_text().replace('_', ' ').title() for label in ax.get_yticklabels()]
    ax.set_yticklabels(formatted_labels, fontsize=10)
    
    # X-axis tick interval 500,000 (500K)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(500000))

    # Format tick labels (e.g., R$ 0, R$ 500K, R$ 1.0M, R$ 1.5M)
    ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, p: f'R$ {x*1e-6:.1f}M' if x >= 1e6 else f'R$ {x*1e-3:.0f}K' if x > 0 else 'R$ 0')
    )
    ax.set_xlabel('Total Revenue', fontsize=12)
    ax.set_ylabel(None)
    ax.tick_params(axis='x', labelsize=11)
    
    # anotasi di akhir bar
    for p in ax.patches:
        width = p.get_width()
        if width > 0:
            ax.annotate(f'R$ {width:,.0f}', 
                        (width, p.get_y() + p.get_height() / 2.),
                        ha='left', va='center', fontsize=9, xytext=(5, 0), textcoords='offset points')
    
    # menambah X-axis limit untuk anotasi
    ax.set_xlim(0, top_cat['total_revenue'].max() * 1.25)
    
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)


# --- RIGHT CHART: Payment Methods ---
with col_p2:
    st.subheader("Payment Method Analysis")
    
    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    
    sns.barplot(
        data=payment_df, 
        x='total_transactions', 
        y='payment_type', 
        palette='Oranges_r', 
        ax=ax
    )
    
    formatted_payments = [label.get_text().replace('_', ' ').title() for label in ax.get_yticklabels()]
    ax.set_yticklabels(formatted_payments, fontsize=10)
    
    # Format X-axis dengan koma
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'))
    
    ax.set_xlabel('Total Transactions', fontsize=12)
    ax.set_ylabel(None)
    ax.tick_params(axis='x', labelsize=11)
    
    # anotasi di akhir bar
    for p in ax.patches:
        width = p.get_width()
        if width > 0:
            ax.annotate(f'{int(width):,}', 
                        (width, p.get_y() + p.get_height() / 2.),
                        ha='left', va='center', fontsize=9, xytext=(5, 0), textcoords='offset points')
            
    ax.set_xlim(0, payment_df['total_transactions'].max() * 1.2)
    
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)

st.markdown("---")

# HASIL MANUAL GROUPING

col_g1, col_g2 = st.columns(2)

# --- LEFT CHART: Spend Category ---
with col_g1:
    st.subheader("Distribusi Spend Category")
    
    order_spend = ['Low Spender', 'Medium Spender', 'High Spender', 'Super Spender']
    
    # mapping warna pada kategori
    color_map = {
        'Low Spender': '#abd9e9',
        'Medium Spender': '#74add1',
        'High Spender': '#4575b4',
        'Super Spender': '#313695'
    }
    
    spend_counts = grouping_df['spend_category'].value_counts().reindex(order_spend).fillna(0)
    spend_counts = spend_counts[spend_counts > 0]

    # Null check
    if spend_counts.empty or spend_counts.sum() == 0:
        st.warning("Tidak ada data transaksi delivered/valid untuk status pesanan yang dipilih.")
    else:
        # Ambil warna berdasarkan kategori yang benar-benar ada
        slice_colors = [color_map[cat] for cat in spend_counts.index]
        
        fig, ax = plt.subplots(figsize=(7, 5), dpi=150)

        # Format label gabungan (Nama + %) langsung di chart
        labels = [f"{cat}\n({val:.1f}%)" for cat, val in zip(spend_counts.index, (spend_counts / spend_counts.sum()) * 100)]

        wedges, texts = ax.pie(
            spend_counts,
            labels=labels,
            labeldistance=1.10,
            startangle=90,
            colors=slice_colors,
            wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2)
        )
        
        plt.setp(texts, size=9, weight="bold")
        
        ax.axis('equal')
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)


# --- RIGHT CHART: Basket Size ---
with col_g2:
    st.subheader("Distribusi Basket Size")

    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    
    order_basket = ['Single Item', 'Small Bundle (2-4 items)', 'Bulk Purchase (>4 items)']
    if grouping_df.empty:
        st.warning("Tidak ada data transaksi delivered/valid untuk status pesanan yang dipilih.")
    else:
        sns.countplot(data=grouping_df, x='basket_size', order=order_basket, palette='Greens_r', ax=ax)
        
        ax.set_xlabel(None)
        ax.set_ylabel('Jumlah Pesanan', fontsize=12)
        
        ax.tick_params(axis='x', rotation=15, labelsize=11)
        ax.tick_params(axis='y', labelsize=11)
        
        for p in ax.patches:
            height = p.get_height()
            if height > 0:
                ax.annotate(f'{int(height):,}', 
                            (p.get_x() + p.get_width() / 2., height),
                            ha='center', va='bottom', fontsize=10, xytext=(0, 4), textcoords='offset points')
    
        # Menyesuaikan batas y agar tinggi chart seimbang dengan grafik donut di kiri
        ax.set_ylim(0, grouping_df['basket_size'].value_counts().max() * 1.15)
    
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)    

st.caption('Dashboard Olist E-Commerce')