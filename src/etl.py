"""
etl.py
------
从 Olist 原始 CSV 构建订单宽表。

输入：
    data/raw/olist_orders_dataset.csv
    data/raw/olist_customers_dataset.csv
    data/raw/olist_order_items_dataset.csv

输出：
    data/processed/orders_wide.parquet
"""

from pathlib import Path
import duckdb

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "data" / "raw"
PROCESSED = BASE_DIR / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

ORDERS = (RAW / "olist_orders_dataset.csv").as_posix()
CUSTOMERS = (RAW / "olist_customers_dataset.csv").as_posix()
ORDER_ITEMS = (RAW / "olist_order_items_dataset.csv").as_posix()

OUTPUT = (PROCESSED / "orders_wide.parquet").as_posix()


def build_orders_wide():
    print("开始构建订单宽表...\n")

    # Step 1: 先把订单商品明细聚合到订单级别
    # 一张订单可能有多个商品，先按 order_id 汇总价格和运费
    duckdb.sql(f"""
        CREATE OR REPLACE TEMP TABLE order_revenue AS
        SELECT
            order_id,
            SUM(price)          AS item_total,
            SUM(freight_value)  AS freight_total,
            COUNT(*)            AS item_count
        FROM '{ORDER_ITEMS}'
        GROUP BY order_id
    """)

    # Step 2: 主查询 —— join 三张表，只保留 delivered 订单
    duckdb.sql(f"""
        COPY (
            SELECT
                o.order_id,
                c.customer_unique_id,
                c.customer_city,
                c.customer_state,
                CAST(o.order_purchase_timestamp AS TIMESTAMP) AS purchase_ts,
                r.item_total,
                r.freight_total,
                r.item_total + r.freight_total AS order_total,
                r.item_count
            FROM '{ORDERS}' o
            JOIN '{CUSTOMERS}' c
                ON o.customer_id = c.customer_id
            JOIN order_revenue r
                ON o.order_id = r.order_id
            WHERE o.order_status = 'delivered'
              AND o.order_purchase_timestamp IS NOT NULL
        ) TO '{OUTPUT}' (FORMAT PARQUET)
    """)

    print(f"宽表已保存到: {OUTPUT}")


def report():
    print("\n===== 数据校验报告 =====")

    row = duckdb.sql(f"""
        SELECT
            COUNT(*)                          AS 订单数,
            COUNT(DISTINCT customer_unique_id) AS 用户数,
            MIN(purchase_ts)                  AS 最早时间,
            MAX(purchase_ts)                  AS 最晚时间,
            ROUND(SUM(order_total), 2)        AS 总金额,
            ROUND(AVG(order_total), 2)        AS 平均客单价
        FROM '{OUTPUT}'
    """).fetchone()

    print(f"订单数     : {row[0]:,}")
    print(f"用户数     : {row[1]:,}")
    print(f"时间范围   : {row[2]}  ~  {row[3]}")
    print(f"总金额     : R$ {row[4]:,.2f}")
    print(f"平均客单价 : R$ {row[5]:,.2f}")

    # 复购用户数（下过 2 单及以上的用户）
    repeat = duckdb.sql(f"""
        SELECT COUNT(*) FROM (
            SELECT customer_unique_id
            FROM '{OUTPUT}'
            GROUP BY customer_unique_id
            HAVING COUNT(*) >= 2
        )
    """).fetchone()[0]

    print(f"复购用户数 : {repeat:,}  (下过 2 单及以上)")


if __name__ == "__main__":
    build_orders_wide()
    report()