"""
app.py
------
Streamlit 多页面看板入口。
运行方式（在项目根目录）：
    streamlit run app/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="电商用户画像看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 用新的 st.navigation 组织多页面（Streamlit >= 1.36）
pages = [
    st.Page("pages/1_overview.py", title="📊 总览", default=True),
    st.Page("pages/2_rfm_segment.py", title="👥 RFM 分群"),
    st.Page("pages/3_preference.py", title="🎯 用户偏好"),
    st.Page("pages/4_user_detail.py", title="🔍 用户明细"),
]

pg = st.navigation(pages)
pg.run()