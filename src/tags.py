"""
tags.py
-------
在 RFM 分群结果的基础上，为用户补充画像标签：
    - favorite_category  偏好类目
    - active_period      活跃时段
    - customer_state     所在州
    - customer_city      所在城市

输入：
    data/processed/rfm_segments.parquet
    data/processed/orders_wide.parquet
    data/raw/olist_order_items_dataset.csv
    data/raw/olist_products_dataset.csv
    data/raw/product_category_name_translation.csv

输出：
    data/processed/user_profile.parquet
"""

from pathlib import Path
import duckdb

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "data" / "raw"
PROCESSED = BASE_DIR / "data" / "processed"

RFM = (PROCESSED / "rfm_segments.parquet").as_posix()
ORDERS_WIDE = (PROCESSED / "orders_wide.parquet").as_posix()
ORDER_ITEMS = (RAW / "olist_order_items_dataset.csv").as_posix()
PRODUCTS = (RAW / "olist_products_dataset.csv").as_posix()
CATEGORY_TRANS = (RAW / "product_category_name_translation.csv").as_posix()

OUTPUT = (PROCESSED / "user_profile.parquet").as_posix()


def build_profile():
    print("开始构建用户画像标签...\n")

    # ---------- 1. 偏好类目 ----------
    # 思路：join 订单商品表 + 商品表 + 翻译表，统计每个用户在每个品类下的购买次数，
    #       取购买次数最多的那个品类作为 favorite_category。
    print("[1/3] 计算偏好类目...")
    duckdb.sql(f"""
        CREATE OR REPLACE TEMP TABLE user_fav_category AS
        WITH user_category_count AS (
            SELECT
                w.customer_unique_id,
                t.product_category_name_english AS category,
                COUNT(*) AS purchase_count,
                ROW_NUMBER() OVER (
                    PARTITION BY w.customer_unique_id
                    ORDER BY COUNT(*) DESC, t.product_category_name_english
                ) AS rn
            FROM '{ORDERS_WIDE}' w
            JOIN '{ORDER_ITEMS}' i
                ON w.order_id = i.order_id
            JOIN '{PRODUCTS}' p
                ON i.product_id = p.product_id
            JOIN '{CATEGORY_TRANS}' t
                ON p.product_category_name = t.product_category_name
            WHERE t.product_category_name_english IS NOT NULL
            GROUP BY w.customer_unique_id, t.product_category_name_english
        )
        SELECT
            customer_unique_id,
            category AS favorite_category
        FROM user_category_count
        WHERE rn = 1
    """)

    # ---------- 2. 活跃时段 ----------
    # 思路：提取每次下单的小时，统计每个用户在每个小时的下单次数，
    #       取下单次数最多的小时，再映射到时段（凌晨/上午/下午/晚间）。
    print("[2/3] 计算活跃时段...")
    duckdb.sql(f"""
        CREATE OR REPLACE TEMP TABLE user_active_period AS
        WITH user_hour_count AS (
            SELECT
                customer_unique_id,
                EXTRACT(HOUR FROM purchase_ts) AS hour_of_day,
                COUNT(*) AS cnt,
                ROW_NUMBER() OVER (
                    PARTITION BY customer_unique_id
                    ORDER BY COUNT(*) DESC, EXTRACT(HOUR FROM purchase_ts)
                ) AS rn
            FROM '{ORDERS_WIDE}'
            GROUP BY customer_unique_id, EXTRACT(HOUR FROM purchase_ts)
        )
        SELECT
            customer_unique_id,
            hour_of_day,
            CASE
                WHEN hour_of_day BETWEEN 0  AND 5  THEN '凌晨(0-6)'
                WHEN hour_of_day BETWEEN 6  AND 11 THEN '上午(6-12)'
                WHEN hour_of_day BETWEEN 12 AND 17 THEN '下午(12-18)'
                ELSE '晚间(18-24)'
            END AS active_period
        FROM user_hour_count
        WHERE rn = 1
    """)

    # ---------- 3. 地域 ----------
    # 思路：取用户最后一次下单时的城市和州（用户可能搬家，取最近的最准）。
    print("[3/3] 计算地域...")
    duckdb.sql(f"""
        CREATE OR REPLACE TEMP TABLE user_region AS
        SELECT
            customer_unique_id,
            customer_city,
            customer_state
        FROM (
            SELECT
                customer_unique_id,
                customer_city,
                customer_state,
                ROW_NUMBER() OVER (
                    PARTITION BY customer_unique_id
                    ORDER BY purchase_ts DESC
                ) AS rn
            FROM '{ORDERS_WIDE}'
        )
        WHERE rn = 1
    """)

    # ---------- 4. 合并到 RFM 表 ----------
    print("\n合并所有标签到用户画像表...")
    duckdb.sql(f"""
        COPY (
            SELECT
                r.customer_unique_id,
                r.first_purchase,
                r.last_purchase,
                r.recency_days,
                r.frequency,
                r.monetary,
                r.r_score,
                r.f_score,
                r.m_score,
                r.segment,
                c.favorite_category,
                a.hour_of_day,
                a.active_period,
                g.customer_city,
                g.customer_state
            FROM '{RFM}' r
            LEFT JOIN user_fav_category c
                ON r.customer_unique_id = c.customer_unique_id
            LEFT JOIN user_active_period a
                ON r.customer_unique_id = a.customer_unique_id
            LEFT JOIN user_region g
                ON r.customer_unique_id = g.customer_unique_id
        ) TO '{OUTPUT}' (FORMAT PARQUET)
    """)

    print(f"用户画像表已保存到: {OUTPUT}")


def report():
    print("\n===== 用户画像表校验 =====")

    row = duckdb.sql(f"""
        SELECT
            COUNT(*) AS 用户总数,
            COUNT(favorite_category) AS 有类目标签,
            COUNT(active_period) AS 有时段标签,
            COUNT(customer_state) AS 有地域标签,
            COUNT(DISTINCT favorite_category) AS 类目数,
            COUNT(DISTINCT customer_state) AS 州数
        FROM '{OUTPUT}'
    """).fetchone()

    print(f"用户总数     : {row[0]:,}")
    print(f"有类目标签   : {row[1]:,}  ({row[1]/row[0]*100:.1f}%)")
    print(f"有时段标签   : {row[2]:,}  ({row[2]/row[0]*100:.1f}%)")
    print(f"有地域标签   : {row[3]:,}  ({row[3]/row[0]*100:.1f}%)")
    print(f"类目数       : {row[4]}")
    print(f"州数         : {row[5]}")

    print("\n【偏好类目 TOP 10】")
    df = duckdb.sql(f"""
        SELECT
            favorite_category AS 类目,
            COUNT(*) AS 用户数
        FROM '{OUTPUT}'
        GROUP BY favorite_category
        ORDER BY 用户数 DESC
        LIMIT 10
    """).df()
    print(df.to_string(index=False))

    print("\n【活跃时段分布】")
    df = duckdb.sql(f"""
        SELECT
            active_period AS 时段,
            COUNT(*) AS 用户数,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比
        FROM '{OUTPUT}'
        GROUP BY active_period
        ORDER BY 用户数 DESC
    """).df()
    print(df.to_string(index=False))

    print("\n【地域 TOP 10】")
    df = duckdb.sql(f"""
        SELECT
            customer_state AS 州,
            COUNT(*) AS 用户数
        FROM '{OUTPUT}'
        GROUP BY customer_state
        ORDER BY 用户数 DESC
        LIMIT 10
    """).df()
    print(df.to_string(index=False))


if __name__ == "__main__":
    build_profile()
    report()