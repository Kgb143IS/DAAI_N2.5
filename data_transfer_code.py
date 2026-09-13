"""
ETL đơn giản, KHÔNG CẦN DATABASE:
    orders_enriched.csv  ->  transform (lọc/map đúng cột entity Order,
                              làm sạch dữ liệu)  ->  silver_orders.csv

Dùng khi bạn muốn có ngay 1 file "silver" sạch để dùng tạm, chưa cần
load vào SQL Server hay bất kỳ database nào.

Cách dùng:
    1. Sửa RAW_FILE_PATH trỏ đúng file orders_enriched.csv của bạn.
    2. Sửa OUTPUT_FILE_PATH nếu muốn đổi tên/vị trí file kết quả.
    3. Chỉnh COLUMN_MAPPING nếu tên cột thật khác với dưới đây.
    4. Chạy: python3 etl_orders_to_file.py
"""

import pandas as pd
from pathlib import Path

# =================================================================
# CẤU HÌNH
# =================================================================
# RAW_FILE_PATH = "./student_data/orders_enriched.csv"
# RAW_FILE_PATH = [
#     "./student_data/customers.csv",
#     "./student_data/eprom.json",
#     "./student_data/geography.csv",
#     "./student_data/inventory.csv",
#     "./student_data/order_items.csv",
#     "./student_data/orders_enriched.csv",
#     "./student_data/payments.csv",
#     "./student_data/products.csv",
#     "./student_data/promotions.csv",
#     "./student_data/returns.csv",
#     "./student_data/reviews.csv",
#     "./student_data/shipments_realistic.csv",
#     "./student_data/tf.json",
#     "./student_data/epd.json",
# ]
# OUTPUT_FILE_PATH = "silver_orders.csv"

ENTITIES = {
    "geography": {
        "raw_path": "./student_data/geography.csv", 
        "output_path": "./transfer_data/geography.csv",
        "primary_key": "zip",
        "date_columns": [],
        "column_mapping": {
            "zip": "zip",
            "city": "city",
            "district": "district",
        },
    },

    "shipper": {
        "raw_path": "./student_data/shipments_realistic.csv", 
        "output_path": "./transfer_data/shippers.csv",
        "primary_key": "shipper_id",
        "date_columns": ["join_date"],
        "column_mapping": {
            "shipper_id": "shipper_id",
            "shipper_name": "shipper_name",
            "shipper_phone": "shipper_phone",
            "shipper_company": "shipper_company",
            "shipper_vehicle": "shipper_vehicle",
            "shipper_rating": "shipper_rating",
            "delivery_success_rate": "delivery_success_rate",
            "average_delivery_time": "average_delivery_time",
            "shipper_experience_years": "shipper_experience_years",
            "shipper_education": "shipper_education",
            "shipper_marital_status": "shipper_marital_status",
            "shipper_gender": "shipper_gender",
            "shipper_age": "shipper_age",
            "working_shift": "working_shift",
            "join_date": "join_date",
        },
    },

    "promotion": {
        "raw_path": ["./student_data/promotions.csv","./student_data/eprom.json"], 
        "output_path": "./transfer_data/promotions.csv",
        "primary_key": "promo_id",
        "date_columns": ["start_date", "end_date"],
        "column_mapping": {
            "promo_id": "promo_id",
            "promo_name": "promo_name",
            "promo_type": "promo_type",
            "discount_value": "discount_value",
            "start_date": "start_date",
            "end_date": "end_date",
            "applicable_category": "applicable_category",
            "promo_channel": "promo_channel",
            "min_order_value": "min_order_value",
            "stackable_flag": "stackable_flag",
        },
    },

    "products": {
        "raw_path": ["./student_data/products.csv","./student_data/epd.json"], 
        "output_path": "./transfer_data/products.csv",
        "primary_key": "product_id",
        "date_columns": [],
        "column_mapping": {
            "product_id": "product_id",
            "product_name": "product_name",
            "category": "category",
            "price": "price",
            "cogs": "cogs",
            "color": "color",
            "segment": "segment",
            "size": "size",
        },
    },

    "customer": {
        "raw_path": "./student_data/customers.csv", 
        "output_path": "./transfer_data/customers.csv",
        "primary_key": "customer_id",
        "date_columns": ["signup_date"],
        "column_mapping": {
            "customer_id": "customer_id",
            "acquisition_channel": "acquisition_channel",
            "age_group": "age_group",
            "gender": "gender",
            "signup_date": "signup_date",
            "zip": "zip",
        },
    },

    "order": {
        "raw_path": "./student_data/orders_enriched.csv", 
        "output_path": "./transfer_data/orders.csv",
        "primary_key": "order_id",
        "date_columns": ["order_date"],
        "column_mapping": {
            "order_id": "order_id",
            "order_date": "order_date",
            "comment": "comment",
            "payment_method": "payment_method",
            "order_status": "order_status",
            "device_type": "device_type",
            "order_source": "order_source",
            "customer_id": "customer_id",
            "sales_employee_id": "sales_employee_id",
            "zip": "zip",
        },
    },

    "order_item": {
        "raw_path": "./student_data/order_items.csv", 
        "output_path": "./transfer_data/order_items.csv",
        "primary_key": ["order_id","product_id"],
        "date_columns": [],
        "column_mapping": {
            "order_id": "order_id",
            "product_id": "product_id",
            "quantity": "quantity",
            "unit_price": "unit_price",
            "discount_amount": "discount_amount",
            "promo_id": "promo_id",
            "promo_id_2": "promo_id_2",
        },
    },

    "return": {
        "raw_path": "./student_data/returns.csv", 
        "output_path": "./transfer_data/returns.csv",
        "primary_key": "return_id",
        "date_columns": ["return_date"],
        "column_mapping": {
            "return_id": "return_id",
            "return_date": "return_date",
            "return_quantity": "return_quantity",
            "refund_amount": "refund_amount",
            "return_reason": "return_reason",
            "order_id": "order_id",
            "product_id": "product_id",
        },
    },

    "employee": {
        "raw_path": "./student_data/orders_enriched.csv", 
        "output_path": "./transfer_data/employees.csv",
        "primary_key": "sales_employee_id",
        "date_columns": [],
        "column_mapping": {
            "sales_employee_id": "sales_employee_id",
            "sales_employee_name": "sales_employee_name",
            "years_experience": "years_experience",
            "education_level": "education_level",
            "marital_status": "marital_status",
        },
    },

    "payment": {
        "raw_path": "./student_data/payments.csv", 
        "output_path": "./transfer_data/payments.csv",
        "primary_key": "order_id",
        "date_columns": [],
        "column_mapping": {
            "order_id": "order_id",
            "payment_method": "payment_method",
            "installments": "installments",
            "payment_value": "payment_value",
        },
    },

    "shipment": {
        "raw_path": "./student_data/shipments_realistic.csv", 
        "output_path": "./transfer_data/shipments.csv",
        "primary_key": ["order_id", "shipper_id"],
        "date_columns": ["ship_date", "delivery_date"],
        "column_mapping": {
            "order_id": "order_id",
            "shipper_id": "shipper_id",
            "ship_date": "ship_date",
            "delivery_date": "delivery_date",
            "shipping_fee": "shipping_fee",
            "city": "city",
            "district": "district",
        },
    },

    "review": {
        "raw_path": "./student_data/reviews.csv", 
        "output_path": "./transfer_data/reviews.csv",
        "primary_key": "review_id",
        "date_columns": ["review_date"],
        "column_mapping": {
            "review_id": "review_id",
            "review_date": "review_date",
            "rating": "rating",
            "review_title": "review_title",
            "order_id": "order_id",
            "product_id": "product_id",
            "customer_id": "customer_id",
        },
    },

    "inventory": {
        "raw_path": "./student_data/inventory.csv", 
        "output_path": "./transfer_data/inventory.csv",
        "primary_key": ["product_id","snapshot_date"],
        "date_columns": ["snapshot_date"],
        "column_mapping": {
            "product_id": "product_id",
            "snapshot_date": "snapshot_date",
            "stock_on_hand": "stock_on_hand",
            "units_received": "units_received",
            "units_sold": "units_sold",
            "stockout_days": "stockout_days",
            "days_of_supply": "days_of_supply",
            "fill_rate": "fill_rate",
            "stockout_flag": "stockout_flag",
            "overstock_flag": "overstock_flag",
            "reorder_flag": "reorder_flag",
            "sell_through_rate": "sell_through_rate",
        },
    },

    "city_region": {
        "raw_path": "./student_data/geography.csv", 
        "output_path": "./transfer_data/city_regions.csv",
        "primary_key": "city",
        "date_columns": [],
        "column_mapping": {
            "city": "city",
            "region": "region",
        },
    },

    "district_region": {
        "raw_path": "./student_data/geography.csv", 
        "output_path": "./transfer_data/district_regions.csv",
        "primary_key": "district",
        "date_columns": [],
        "column_mapping": {
            "district": "district",
            "region": "region",
        },
    }
}
 
 
# =================================================================
# EXTRACT
# =================================================================
def extract(path_or_paths) -> pd.DataFrame:
    """
    Đọc 1 file HOẶC gộp nhiều file cùng cấu trúc thành 1 DataFrame.
    path_or_paths: str (1 file) hoặc list[str] (nhiều file cùng cấu trúc).
    """
    paths = [path_or_paths] if isinstance(path_or_paths, str) else list(path_or_paths)
 
    frames = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {p}")
 
        if p.suffix == ".csv":
            df = pd.read_csv(p, dtype=str)
        elif p.suffix in (".xlsx", ".xls"):
            df = pd.read_excel(p, dtype=str)
        elif p.suffix in (".json"):
            df = pd.read_json(p, dtype=str)
        else:
            raise ValueError(f"Định dạng chưa hỗ trợ: {p.suffix}")
 
        print(f"    Đọc {len(df)} dòng, {len(df.columns)} cột từ {p.name}")
        frames.append(df)
 
    combined = pd.concat(frames, ignore_index=True)
    if len(paths) > 1:
        print(f"    -> Gộp {len(paths)} file thành {len(combined)} dòng")
    return combined
 
 
# =================================================================
# TRANSFORM (dùng chung cho mọi entity, dựa trên cấu hình riêng)
# =================================================================
def transform(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    df = df.copy()
    mapping = cfg["column_mapping"]
 
    missing = [c for c in mapping if c not in df.columns]
    if missing:
        raise KeyError(
            f"Các cột sau có trong column_mapping nhưng KHÔNG có trong file raw: "
            f"{missing}. Kiểm tra lại tên cột."
        )
 
    df = df[list(mapping.keys())].rename(columns=mapping)
 
    str_cols = df.select_dtypes(include="object").columns
    for c in str_cols:
        df[c] = df[c].str.strip()
    df = df.replace({"": None, "nan": None, "NaN": None, "None": None})
 
    for col in cfg.get("date_columns", []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
 
    pk = cfg.get("primary_key")
    if pk:
        if isinstance(pk, list):
            if all(col in df.columns for col in pk):
                df = df.drop_duplicates(subset=pk)
        else:
            if pk in df.columns:
                df = df.drop_duplicates(subset=[pk])
 
    return df
 
 
# =================================================================
# EXPORT
# =================================================================
def export(df: pd.DataFrame, path: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"    Đã ghi {len(df)} dòng ra file: {path}")
 
 
# =================================================================
# MAIN — lặp qua từng entity, xử lý độc lập
# =================================================================
def run():
    for name, cfg in ENTITIES.items():
        print(f"\n=== Entity: {name} ===")
        print("  [1/3] Extract...")
        raw_df = extract(cfg["raw_path"])
 
        print("  [2/3] Transform...")
        clean_df = transform(raw_df, cfg)
        print(f"    Sau transform còn {len(clean_df)} dòng, cột: {list(clean_df.columns)}")
 
        print("  [3/3] Export...")
        export(clean_df, cfg["output_path"])
 
    print("\nHoàn tất tất cả entity!")
 
 
if __name__ == "__main__":
    run()
 