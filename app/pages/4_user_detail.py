"""用户明细页：多条件筛选 + 下载"""

from pathlib import Path
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent.parent.parent
PROCESSED = BASE / "data" / "processed"

st.title("🔍 用户明细查询")

profile = pd.read_parquet(PROCESSED / "user_profile.parquet")

# ---------- 筛选器 ----------
col1, col2, col3 = st.columns(3)
with col1:
    seg = st.selectbox("分群", ["全部"] + sorted(profile["segment"].unique()))
with col2:
    state = st.selectbox("州", ["全部"] + sorted(profile["customer_state"].unique()))
with col3:
    period = st.selectbox("活跃时段", ["全部"] + sorted(profile["active_period"].dropna().unique()))

# 金额和 R 区间
col4, col5 = st.columns(2)
with col4:
    m_min, m_max = st.slider(
        "消费金额范围 (R$)",
        float(profile["monetary"].min()),
        float(profile["monetary"].max()),
        (float(profile["monetary"].min()), float(profile["monetary"].max())),
    )
with col5:
    r_min, r_max = st.slider(
        "Recency 范围（天）",
        int(profile["recency_days"].min()),
        int(profile["recency_days"].max()),
        (int(profile["recency_days"].min()), int(profile["recency_days"].max())),
    )

# ---------- 应用筛选 ----------
filtered = profile.copy()
if seg != "全部":
    filtered = filtered[filtered["segment"] == seg]
if state != "全部":
    filtered = filtered[filtered["customer_state"] == state]
if period != "全部":
    filtered = filtered[filtered["active_period"] == period]
filtered = filtered[
    (filtered["monetary"].between(m_min, m_max)) &
    (filtered["recency_days"].between(r_min, r_max))
]

st.success(f"共筛选出 **{len(filtered):,}** 位用户")

# ---------- 展示列 ----------
show_cols = [
    "customer_unique_id", "segment", "recency_days", "frequency",
    "monetary", "favorite_category", "active_period",
    "customer_city", "customer_state",
]
st.dataframe(filtered[show_cols].head(1000), width="stretch", height=500)
st.caption("最多显示前 1000 行，完整数据请点下方按钮下载")

# ---------- 下载 ----------
csv = filtered[show_cols].to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "📥 下载筛选结果 CSV",
    csv,
    f"filtered_users_{len(filtered)}.csv",
    "text/csv",
)