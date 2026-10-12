"""RFM 分群页：分群筛选 + R/F/M 分布 + 分群统计表 + 散点图"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).resolve().parent.parent.parent
PROCESSED = BASE / "data" / "processed"

st.title("👥 RFM 用户分群")

profile = pd.read_parquet(PROCESSED / "user_profile.parquet")

# ---------- 分群筛选 ----------
all_segments = sorted(profile["segment"].unique())
selected = st.multiselect("选择分群（可多选）", all_segments, default=all_segments)
filtered = profile[profile["segment"].isin(selected)]

st.caption(f"当前筛选出 {len(filtered):,} 位用户")

st.divider()

# ---------- R/F/M 分布 ----------
st.subheader("R / F / M 分布")
col1, col2, col3 = st.columns(3)
with col1:
    fig = px.histogram(filtered, x="recency_days", nbins=50,
                       title="R：最近购买距今天数")
    st.plotly_chart(fig, width="stretch")
with col2:
    fig = px.histogram(filtered, x="frequency", nbins=20,
                       title="F：购买次数")
    st.plotly_chart(fig, width="stretch")
with col3:
    fig = px.histogram(filtered, x="monetary", nbins=50,
                       title="M：消费金额 (R$)")
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------- 分群统计表 ----------
st.subheader("各分群统计")
stats = filtered.groupby("segment").agg(
    用户数=("customer_unique_id", "count"),
    平均R=("recency_days", "mean"),
    平均F=("frequency", "mean"),
    平均M=("monetary", "mean"),
    总M=("monetary", "sum"),
).round(1).reset_index().sort_values("用户数", ascending=False)
st.dataframe(stats, width="stretch")

st.divider()

# ---------- R vs M 散点图 ----------
st.subheader("R vs M 散点图（点大小 = 购买次数）")
fig = px.scatter(
    filtered.sample(min(5000, len(filtered)), random_state=42),
    x="recency_days", y="monetary",
    color="segment", size="frequency",
    opacity=0.6, hover_data=["customer_unique_id"],
)
fig.update_layout(xaxis_title="Recency（天）", yaxis_title="Monetary (R$)")
st.plotly_chart(fig, width="stretch")