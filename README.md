# Olist 电商用户画像看板

基于巴西电商平台 Olist 的真实交易数据，构建端到端的用户画像分析与 RFM 分群看板。

## 项目背景

Olist 是巴西最大的电商平台之一，本数据集包含 2016-09 至 2018-10 期间约 10 万笔订单。本项目基于该数据，从 0 到 1 完成：

- 数据清洗与宽表构建
- RFM 用户价值分层
- 用户画像标签构建（偏好类目、活跃时段、地域）
- 交互式 Web 看板

## 核心发现

| 发现 | 数据 |
|---|---|
| 总用户数 | 93,358 |
| 总消费金额 | R$ 15,419,773.75 |
| 人均消费 | R$ 165.17 |
| 重要价值客户占比 | 6.21%（贡献 12% 营收） |
| 复购用户占比 | 约 3%（Olist 数据集特征） |
| 活跃高峰时段 | 下午 12-18 点（38.6%） |
| TOP 偏好类目 | bed_bath_table、health_beauty、sports_leisure |
| 用户地域集中度 | SP 州占 42%，前 3 州占 67% |

## 技术栈

- **数据处理**：DuckDB + Pandas + PyArrow
- **数据存储**：Parquet
- **可视化**：Streamlit + Plotly
- **环境管理**：Conda

## 项目结构

```text
olist-user-dashboard/
├── data/
│   ├── raw/                 # 原始 9 个 CSV
│   └── processed/           # 处理后的 Parquet 文件
├── notebooks/
│   └── 01_eda.ipynb         # 探索性分析
├── src/
│   ├── etl.py               # 构建订单宽表
│   ├── rfm.py               # RFM 计算与分群
│   └── tags.py              # 用户画像标签
├── app/
│   ├── app.py               # Streamlit 入口
│   └── pages/
│       ├── 1_overview.py    # 总览页
│       ├── 2_rfm_segment.py # RFM 分群页
│       ├── 3_preference.py  # 用户偏好页
│       └── 4_user_detail.py # 用户明细页
├── docs/
│   └── metrics.md           # 指标字典
├── requirements.txt
└── README.md