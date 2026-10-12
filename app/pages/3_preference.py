"""用户偏好页：偏好类目 + 活跃时段 + 地域分布"""

from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).resolve().parent.parent.parent
PROCESSED = BASE / "data" / "processed"

st.title("🎯 用户偏好分析")

profile = pd.read_parquet(PROCESSED / "user_profile.parquet")

col1, col2 = st.columns(2)

# ---------- 偏好类目 TOP 10 ----------
with col1:
    st.subheader("偏好类目 TOP 10")
    cat = profile["favorite_category"].value_counts().head(10).reset_index()
    cat.columns = ["类目", "用户数"]
    fig = px.bar(cat, x="用户数", y="类目", orientation="h",
                 color="用户数", color_continuous_scale="Blues")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")

# ---------- 活跃时段分布 ----------
with col2:
    st.subheader("活跃时段分布")
    period = profile["active_period"].value_counts().reset_index()
    period.columns = ["时段", "用户数"]
    fig = px.pie(period, names="时段", values="用户数", hole=0.4)
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------- 地域分布 ----------
st.subheader("用户地域分布 TOP 15")
state = profile["customer_state"].value_counts().head(15).reset_index()
state.columns = ["州", "用户数"]
fig = px.bar(state, x="州", y="用户数", color="用户数",
             color_continuous_scale="Greens", text="用户数")
fig.update_traces(textposition="outside")
fig.update_layout(coloraxis_showscale=False)
st.plotly_chart(fig, width="stretch")

st.divider()

# ---------- 分群 × 偏好类目交叉表 ----------
st.subheader("各分群的偏好类目（TOP 3）")
rows = []
for seg in sorted(profile["segment"].unique()):
    top3 = profile[profile["segment"] == seg]["favorite_category"] \
        .value_counts().head(3).index.tolist()
    rows.append({"分群": seg, "TOP1": top3[0] if len(top3) > 0 else "",
                 "TOP2": top3[1] if len(top3) > 1 else "",
                 "TOP3": top3[2] if len(top3) > 2 else ""})
st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)