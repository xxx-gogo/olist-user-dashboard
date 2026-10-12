"""总览页：KPI 卡片 + 分群消费占比 + 月度订单趋势"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).resolve().parent.parent.parent
PROCESSED = BASE / "data" / "processed"

st.title("📊 用户画像总览")

profile = pd.read_parquet(PROCESSED / "user_profile.parquet")
orders = pd.read_parquet(PROCESSED / "orders_wide.parquet")

# ---------- KPI 卡片 ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("总用户数", f"{len(profile):,}")
col2.metric("总消费金额", f"R$ {profile['monetary'].sum():,.0f}")
col3.metric("人均消费", f"R$ {profile['monetary'].mean():,.1f}")
col4.metric("总订单数", f"{orders['order_id'].nunique():,}")

st.divider()

# ---------- 各分群消费金额 ----------
st.subheader("各分群用户数与消费金额")
seg = profile.groupby("segment").agg(
    用户数=("customer_unique_id", "count"),
    消费总额=("monetary", "sum"),
).reset_index().sort_values("消费总额", ascending=False)

fig = px.bar(
    seg, x="segment", y="消费总额", color="segment",
    text="用户数", title="分群消费金额（柱上数字为对应分群用户数）",
)
fig.update_traces(textposition="outside")
fig.update_layout(showlegend=False, xaxis_title="分群", yaxis_title="消费总额 (R$)")
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------- 月度订单趋势 ----------
st.subheader("月度订单趋势")
orders["month"] = pd.to_datetime(orders["purchase_ts"]).dt.to_period("M").astype(str)
monthly = orders.groupby("month").agg(订单数=("order_id", "nunique")).reset_index()

fig2 = px.line(monthly, x="month", y="订单数", markers=True)
fig2.update_layout(xaxis_title="月份", yaxis_title="订单数")
st.plotly_chart(fig2, width="stretch")