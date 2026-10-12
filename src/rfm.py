"""
rfm.py
------
基于订单宽表计算每个用户的 RFM 分数，并按分数分群。

输入：
    data/processed/orders_wide.parquet

输出：
    data/processed/rfm_segments.parquet
"""

from pathlib import Path
import duckdb

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED = BASE_DIR / "data" / "processed"

ORDERS_WIDE = (PROCESSED / "orders_wide.parquet").as_posix()
OUTPUT = (PROCESSED / "rfm_segments.parquet").as_posix()

# 参考日期：数据中最晚购买时间 + 1 天
REFERENCE_DATE = "2018-08-30"


def build_rfm():
    print("开始计算 RFM...\n")

    duckdb.sql(f"""
        COPY (
            WITH user_agg AS (
                SELECT
                    customer_unique_id,
                    MIN(purchase_ts) AS first_purchase,
                    MAX(purchase_ts) AS last_purchase,
                    COUNT(DISTINCT order_id) AS frequency,
                    SUM(order_total) AS monetary
                FROM '{ORDERS_WIDE}'
                GROUP BY customer_unique_id
            ),
            scored AS (
                SELECT
                    customer_unique_id,
                    first_purchase,
                    last_purchase,
                    DATE_DIFF('day', last_purchase, DATE '{REFERENCE_DATE}') AS recency_days,
                    frequency,
                    ROUND(monetary, 2) AS monetary,
                    -- R: 越小越好（最近刚买过的分数高）
                    NTILE(5) OVER (ORDER BY DATE_DIFF('day', last_purchase, DATE '{REFERENCE_DATE}') DESC) AS r_score,
                    -- F: 越大越好
                    NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
                    -- M: 越大越好
                    NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
                FROM user_agg
            )
            SELECT
                customer_unique_id,
                first_purchase,
                last_purchase,
                recency_days,
                frequency,
                monetary,
                r_score,
                f_score,
                m_score,
                CASE
                    WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN '重要价值客户'
                    WHEN r_score >= 4 AND f_score >= 3 AND m_score >= 3 THEN '重要发展客户'
                    WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN '重要保持客户'
                    WHEN r_score >= 3 AND f_score <= 2 AND m_score <= 2 THEN '新客/潜力客户'
                    WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN '流失客户'
                    ELSE '一般价值客户'
                END AS segment
            FROM scored
        ) TO '{OUTPUT}' (FORMAT PARQUET)
    """)

    print(f"RFM 分群结果已保存到: {OUTPUT}")


def report():
    print("\n===== RFM 分群报告 =====")

    # 分群分布
    print("\n【各分群用户数、消费、占比】")
    df = duckdb.sql(f"""
        SELECT
            segment AS 分群,
            COUNT(*) AS 用户数,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比,
            ROUND(AVG(recency_days), 1) AS 平均R,
            ROUND(AVG(frequency), 2) AS 平均F,
            ROUND(AVG(monetary), 2) AS 平均M,
            ROUND(SUM(monetary), 2) AS 消费总额
        FROM '{OUTPUT}'
        GROUP BY segment
        ORDER BY 用户数 DESC
    """).df()
    print(df.to_string(index=False))

    # 总体统计
    print("\n【总体统计】")
    row = duckdb.sql(f"""
        SELECT
            COUNT(*) AS 用户总数,
            ROUND(AVG(recency_days), 1) AS 平均R,
            ROUND(AVG(frequency), 2) AS 平均F,
            ROUND(AVG(monetary), 2) AS 平均M,
            ROUND(SUM(monetary), 2) AS 总金额
        FROM '{OUTPUT}'
    """).fetchone()

    print(f"用户总数 : {row[0]:,}")
    print(f"平均 R   : {row[1]} 天")
    print(f"平均 F   : {row[2]} 次")
    print(f"平均 M   : R$ {row[3]:,.2f}")
    print(f"总金额   : R$ {row[4]:,.2f}")


if __name__ == "__main__":
    build_rfm()
    report()