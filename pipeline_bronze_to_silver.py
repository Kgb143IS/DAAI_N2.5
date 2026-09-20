"""
Bronze -> Silver pipeline (final, clean, self-contained).
Chạy 1 lần duy nhất, không phụ thuộc code cũ.
"""
import pandas as pd
import numpy as np
import os

RAW = "/mnt/user-data/uploads/"
OUT = "/home/claude/silver_pipeline/silver/"
os.makedirs(OUT, exist_ok=True)

# Nap truoc tap order_id goc (chi 1 cot, nhe) de cac bang fact khac dung check FK
# ma khong can doi xu ly xong bang orders truoc.
order_ids_set = set(
    pd.read_csv(RAW+"orders.csv", usecols=["order_id"], dtype={"order_id": "string"})
    ["order_id"].str.strip()
)

def log(msg):
    print(msg)

# ---------- Helper functions ----------
def normalize_code(series):
    """Nhóm B: code/phân loại hữu hạn -> UPPERCASE, strip. Giữ NaN nguyên vẹn."""
    return series.astype("string").str.strip().str.upper()

def normalize_id(series):
    """Nhóm A: ID/khóa -> chỉ strip, không đổi casing."""
    return series.astype("string").str.strip()

def normalize_text(series):
    """Nhóm C: danh từ riêng / free text -> chỉ strip, KHÔNG đổi casing."""
    return series.astype("string").str.strip()

def impute_categorical(df, col, fill_value="UNKNOWN"):
    n_null = int(df[col].isna().sum())
    if n_null:
        df[col] = df[col].fillna(fill_value)
    log(f"  - impute {col}: {n_null} dong -> '{fill_value}'")
    return df

def impute_numeric_median_by_group(df, col, group_col):
    n_null = int(df[col].isna().sum())
    if n_null:
        med = df.groupby(group_col)[col].transform("median")
        df[col] = df[col].fillna(med)
        df[col] = df[col].fillna(df[col].median())
    log(f"  - impute {col} (median by {group_col}): {n_null} dong")
    return df

def dedup_exact(df, name):
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    if before != after:
        log(f"  - dedup exact rows in {name}: {before-after} dong bi loai")
    return df

def dedup_pk(df, pk_cols, name):
    before = len(df)
    df = df.drop_duplicates(subset=pk_cols, keep="last")
    after = len(df)
    if before != after:
        log(f"  - dedup theo PK {pk_cols} trong {name}: {before-after} dong conflict bi loai (giu ban ghi cuoi)")
    return df

def check_fk(df, mask_valid, name):
    """Kiem tra FK va CHI IN CANH BAO ra report, khong gan cot vao du lieu output."""
    n_invalid = int((~mask_valid).sum())
    if n_invalid:
        log(f"  CANH BAO: {n_invalid}/{len(df)} dong co FK khong hop le trong {name}")
    else:
        log(f"  FK check {name}: OK, khong co dong nao vi pham")

# ================= PRODUCTS =================
log("=== products.csv ===")
products = pd.read_csv(RAW+"products.csv", dtype={
    "product_id": "string", "product_name": "string", "category": "string",
    "color": "string", "segment": "string", "size": "string"
})
log(f"  rows in: {len(products)}")

rejected_products = products[products["product_id"].isna()].copy()
products = products[products["product_id"].notna()].copy()

products["product_id"] = normalize_id(products["product_id"])
products["product_name"] = normalize_text(products["product_name"])          # Nhom C - KHONG doi case
products["category"] = normalize_code(products["category"])                  # Nhom B
products["color"] = normalize_code(products["color"])
products["segment"] = normalize_code(products["segment"])
products["size"] = normalize_code(products["size"])

products = dedup_pk(products, ["product_id"], "products")
products = impute_numeric_median_by_group(products, "price", "category")
products = impute_numeric_median_by_group(products, "cogs", "category")

# Chuan hoa do chinh xac cho gia tri tien te: lam tron 2 chu so thap phan
# (bronze co float-noise toi 15-16 chu so do sinh du lieu tong hop)
products["price"] = products["price"].round(2)
products["cogs"] = products["cogs"].round(2)
log("  - lam tron price, cogs ve 2 chu so thap phan")

rejected_products["_reject_reason"] = "missing product_id"
rejected_products.to_csv(OUT+"silver_rejected_products.csv", index=False, encoding="utf-8-sig")
products.to_csv(OUT+"silver_products.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(products)} (+ {len(rejected_products)} rejected)")

# ================= EMPLOYEES =================
log("=== employees.csv ===")
employees = pd.read_csv(RAW+"employees.csv", dtype={
    "sales_employee_id": "string", "sales_employee_name": "string",
    "education_level": "string", "marital_status": "string"
})
employees["sales_employee_id"] = normalize_id(employees["sales_employee_id"])
employees["sales_employee_name"] = normalize_text(employees["sales_employee_name"])  # Nhom C
employees["education_level"] = normalize_text(employees["education_level"])          # text TV giu nguyen
employees["marital_status"] = normalize_text(employees["marital_status"])
employees = dedup_pk(employees, ["sales_employee_id"], "employees")
employees.to_csv(OUT+"silver_employees.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(employees)}")

# ================= SHIPPERS =================
log("=== shippers.csv ===")
shippers = pd.read_csv(RAW+"shippers.csv", dtype={
    "shipper_id": "string", "shipper_name": "string", "shipper_phone": "string",
    "shipper_company": "string", "shipper_vehicle": "string", "shipper_education": "string",
    "shipper_marital_status": "string", "shipper_gender": "string", "working_shift": "string"
})
shippers["join_date"] = pd.to_datetime(shippers["join_date"], format="%Y-%m-%d", errors="coerce")
shippers["shipper_id"] = normalize_id(shippers["shipper_id"])
shippers["shipper_name"] = normalize_text(shippers["shipper_name"])
shippers["shipper_company"] = normalize_text(shippers["shipper_company"])
shippers["shipper_vehicle"] = normalize_code(shippers["shipper_vehicle"])
shippers["shipper_education"] = normalize_text(shippers["shipper_education"])
shippers["shipper_marital_status"] = normalize_text(shippers["shipper_marital_status"])
shippers["shipper_gender"] = normalize_code(shippers["shipper_gender"])
shippers["working_shift"] = normalize_code(shippers["working_shift"])
shippers = dedup_pk(shippers, ["shipper_id"], "shippers")
shippers.to_csv(OUT+"silver_shippers.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(shippers)}")

# ================= CUSTOMERS =================
log("=== customers.csv ===")
customers = pd.read_csv(RAW+"customers.csv", dtype={
    "customer_id": "string", "acquisition_channel": "string", "age_group": "string",
    "gender": "string", "zip": "string"
})
customers["signup_date"] = pd.to_datetime(customers["signup_date"], format="%Y-%m-%d", errors="coerce")
customers["customer_id"] = normalize_id(customers["customer_id"])
customers["zip"] = normalize_id(customers["zip"])
customers["acquisition_channel"] = normalize_code(customers["acquisition_channel"])
customers["age_group"] = normalize_code(customers["age_group"])
customers["gender"] = normalize_code(customers["gender"])
customers = dedup_pk(customers, ["customer_id"], "customers")
customers.to_csv(OUT+"silver_customers.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(customers)}")

# ================= PROMOTIONS =================
log("=== promotions.csv ===")
promotions = pd.read_csv(RAW+"promotions.csv", dtype={
    "promo_id": "string", "promo_name": "string", "promo_type": "string",
    "applicable_category": "string", "promo_channel": "string"
})
for _c in ["start_date", "end_date"]:
    promotions[_c] = pd.to_datetime(promotions[_c], format="%Y-%m-%d", errors="coerce")
promotions["promo_id"] = normalize_id(promotions["promo_id"])
promotions["promo_name"] = normalize_text(promotions["promo_name"])   # Nhom C
promotions["promo_type"] = normalize_code(promotions["promo_type"])
promotions["applicable_category"] = normalize_code(promotions["applicable_category"])
promotions["promo_channel"] = normalize_code(promotions["promo_channel"])
promotions = dedup_pk(promotions, ["promo_id"], "promotions")

# applicable_category null: kiem tra gia thuyet "toan san" bang cach xem discount_value / min_order_value
null_rows = promotions[promotions["applicable_category"].isna()]
log(f"  applicable_category null: {len(null_rows)}/{len(promotions)} - vi du ten CTKM: "
    f"{null_rows['promo_name'].dropna().unique()[:5].tolist()}")
# Gia dinh: null = ap dung toan bo category (khong gioi han theo category cu the)
n_null_cat = int(promotions["applicable_category"].isna().sum())
promotions["applicable_category"] = promotions["applicable_category"].fillna("ALL_CATEGORIES")
log(f"  - impute applicable_category: {n_null_cat} dong -> 'ALL_CATEGORIES'")
promotions = impute_categorical(promotions, "promo_channel", "UNKNOWN")

# promo_name null: khong the doan lai ten CTKM da mat, nhung van phai co gia tri
# de khong vo schema / gay loi khi hien thi bao cao -> gan placeholder co the truy vet
# theo promo_id.
n_null_name = int(promotions["promo_name"].isna().sum())
promotions.loc[promotions["promo_name"].isna(), "promo_name"] = (
    "UNKNOWN_PROMO_" + promotions.loc[promotions["promo_name"].isna(), "promo_id"]
)
log(f"  - impute promo_name: {n_null_name} dong -> 'UNKNOWN_PROMO_<promo_id>'")

promotions.to_csv(OUT+"silver_promotions.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(promotions)}")

# ================= GEOGRAPHY + REGIONS =================
log("=== geography.csv / city_regions.csv / district_regions.csv ===")
geography = pd.read_csv(RAW+"geography.csv", dtype={"zip":"string","city":"string","district":"string"})
city_regions = pd.read_csv(RAW+"city_regions.csv", dtype={"city":"string","region":"string"})
district_regions = pd.read_csv(RAW+"district_regions.csv", dtype={"district":"string","region":"string"})

geography["zip"] = normalize_id(geography["zip"])
geography["city"] = normalize_code(geography["city"])
geography["district"] = normalize_code(geography["district"])
city_regions["city"] = normalize_code(city_regions["city"])
city_regions["region"] = normalize_code(city_regions["region"])
district_regions["district"] = normalize_code(district_regions["district"])
district_regions["region"] = normalize_code(district_regions["region"])

geography = dedup_pk(geography, ["zip"], "geography")
city_regions = dedup_pk(city_regions, ["city"], "city_regions")
district_regions = dedup_pk(district_regions, ["district"], "district_regions")

# kiem tra 1 city chi thuoc 1 region, 1 district chi thuoc 1 region
dup_city = city_regions.groupby("city")["region"].nunique()
conflict_city = dup_city[dup_city > 1]
if len(conflict_city):
    log(f"  CANH BAO: {len(conflict_city)} city co nhieu hon 1 region: {conflict_city.index.tolist()}")
dup_dist = district_regions.groupby("district")["region"].nunique()
conflict_dist = dup_dist[dup_dist > 1]
if len(conflict_dist):
    log(f"  CANH BAO: {len(conflict_dist)} district co nhieu hon 1 region: {conflict_dist.index.tolist()}")

geography = geography.merge(city_regions, on="city", how="left")

geography.to_csv(OUT+"silver_geography.csv", index=False, encoding="utf-8-sig")
city_regions.to_csv(OUT+"silver_city_regions.csv", index=False, encoding="utf-8-sig")
district_regions.to_csv(OUT+"silver_district_regions.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: geography={len(geography)}, city_regions={len(city_regions)}, district_regions={len(district_regions)}")

# ================= RETURNS =================
log("=== returns.csv ===")
returns = pd.read_csv(RAW+"returns.csv", dtype={
    "return_id":"string","return_reason":"string","order_id":"string","product_id":"string"
})
returns["return_date"] = pd.to_datetime(returns["return_date"], format="%Y-%m-%d", errors="coerce")
returns["return_id"] = normalize_id(returns["return_id"])
returns["order_id"] = normalize_id(returns["order_id"])
returns["product_id"] = normalize_id(returns["product_id"])
returns["return_reason"] = normalize_code(returns["return_reason"])
returns = dedup_pk(returns, ["return_id"], "returns")
check_fk(returns, returns["product_id"].isin(products["product_id"]) &
                   returns["order_id"].isin(order_ids_set), "returns")
returns.to_csv(OUT+"silver_returns.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(returns)}")

# ================= REVIEWS =================
log("=== reviews.csv ===")
reviews = pd.read_csv(RAW+"reviews.csv", dtype={
    "review_id":"string","review_title":"string","order_id":"string",
    "product_id":"string","customer_id":"string"
})
reviews["review_date"] = pd.to_datetime(reviews["review_date"], format="%m/%d/%Y", errors="coerce")
reviews["review_id"] = normalize_id(reviews["review_id"])
reviews["order_id"] = normalize_id(reviews["order_id"])
reviews["product_id"] = normalize_id(reviews["product_id"])
reviews["customer_id"] = normalize_id(reviews["customer_id"])
reviews["review_title"] = normalize_text(reviews["review_title"])  # Nhom C
reviews = dedup_pk(reviews, ["review_id"], "reviews")
bad_rating = reviews[~reviews["rating"].between(1,5)]
if len(bad_rating):
    log(f"  CANH BAO: {len(bad_rating)} rating ngoai khoang 1-5")
check_fk(reviews, reviews["product_id"].isin(products["product_id"]) &
                   reviews["customer_id"].isin(customers["customer_id"]) &
                   reviews["order_id"].isin(order_ids_set), "reviews")
reviews.to_csv(OUT+"silver_reviews.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(reviews)}")

# ================= INVENTORY =================
log("=== inventory.csv ===")
inventory = pd.read_csv(RAW+"inventory.csv", dtype={"product_id":"string"})
inventory["snapshot_date"] = pd.to_datetime(inventory["snapshot_date"], format="%m/%d/%Y", errors="coerce")
inventory["product_id"] = normalize_id(inventory["product_id"])
inventory = dedup_pk(inventory, ["product_id","snapshot_date"], "inventory")
check_fk(inventory, inventory["product_id"].isin(products["product_id"]), "inventory")
inventory.to_csv(OUT+"silver_inventory.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(inventory)}")

# ================= ORDER_ITEMS =================
log("=== order_items.csv ===")
order_items = pd.read_csv(RAW+"order_items.csv", dtype={
    "order_id":"string","product_id":"string","promo_id":"string","promo_id_2":"string"
})
order_items["order_id"] = normalize_id(order_items["order_id"])
order_items["product_id"] = normalize_id(order_items["product_id"])
order_items["promo_id"] = normalize_id(order_items["promo_id"])
order_items["promo_id_2"] = normalize_id(order_items["promo_id_2"])
order_items = dedup_exact(order_items, "order_items")  # chi drop neu TOAN BO cot giong het
valid_promo_ids = set(promotions["promo_id"])
check_fk(order_items,
    order_items["product_id"].isin(products["product_id"]) &
    order_items["order_id"].isin(order_ids_set) &
    (order_items["promo_id"].isna() | order_items["promo_id"].isin(valid_promo_ids)) &
    (order_items["promo_id_2"].isna() | order_items["promo_id_2"].isin(valid_promo_ids)),
    "order_items")
order_items.to_csv(OUT+"silver_order_items.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(order_items)}")

# ================= PAYMENTS =================
log("=== payments.csv ===")
payments = pd.read_csv(RAW+"payments.csv", dtype={"order_id":"string","payment_method":"string"})
payments["order_id"] = normalize_id(payments["order_id"])
payments["payment_method"] = normalize_code(payments["payment_method"])
n_multi = payments["order_id"].duplicated().sum()
if n_multi:
    log(f"  CANH BAO: {n_multi} order_id co nhieu hon 1 dong payment")
check_fk(payments, payments["order_id"].isin(order_ids_set), "payments")
payments.to_csv(OUT+"silver_payments.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(payments)}")

# ================= SHIPMENTS =================
log("=== shipments.csv ===")
shipments = pd.read_csv(RAW+"shipments.csv", dtype={
    "order_id":"string","shipper_id":"string","city":"string","district":"string"
})
for _c in ["ship_date","delivery_date"]:
    shipments[_c] = pd.to_datetime(shipments[_c], format="%m/%d/%Y", errors="coerce")
shipments["order_id"] = normalize_id(shipments["order_id"])
shipments["shipper_id"] = normalize_id(shipments["shipper_id"])
shipments["city"] = normalize_code(shipments["city"])
shipments["district"] = normalize_code(shipments["district"])
n_dup_order = int(shipments["order_id"].duplicated().sum())
if n_dup_order:
    log(f"  CANH BAO: {n_dup_order} order_id co nhieu hon 1 dong shipment")
check_fk(shipments, shipments["shipper_id"].isin(shippers["shipper_id"]) &
                     shipments["order_id"].isin(order_ids_set), "shipments")
shipments.to_csv(OUT+"silver_shipments.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(shipments)}")

# ================= ORDERS =================
log("=== orders.csv ===")
orders = pd.read_csv(RAW+"orders.csv", dtype={
    "order_id":"string","comment":"string","payment_method":"string","order_status":"string",
    "device_type":"string","order_source":"string","customer_id":"string",
    "sales_employee_id":"string","zip":"string"
})
orders["order_date"] = pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="coerce")
orders["order_id"] = normalize_id(orders["order_id"])
orders["customer_id"] = normalize_id(orders["customer_id"])
orders["sales_employee_id"] = normalize_id(orders["sales_employee_id"])
orders["zip"] = normalize_id(orders["zip"])
orders["comment"] = normalize_text(orders["comment"])           # Nhom C
orders["payment_method"] = normalize_code(orders["payment_method"])
orders["order_status"] = normalize_code(orders["order_status"])
orders["device_type"] = normalize_code(orders["device_type"])
orders["order_source"] = normalize_code(orders["order_source"])
orders = dedup_pk(orders, ["order_id"], "orders")
check_fk(orders, orders["customer_id"].isin(customers["customer_id"]) &
                  orders["sales_employee_id"].isin(employees["sales_employee_id"]) &
                  orders["zip"].isin(geography["zip"]), "orders")
orders.to_csv(OUT+"silver_orders.csv", index=False, encoding="utf-8-sig")
log(f"  rows out: {len(orders)}")

# ================= CROSS-TABLE CONSISTENCY CHECKS =================
log("\n=== KIEM TRA NHAT QUAN CHEO (cross-table casing) ===")
def check_match(a, b, name_a, name_b, field):
    """Dung khi 2 tap PHAI khop tuyet doi (cung la danh sach du lieu goc, khong co quan he cha-con)."""
    sa, sb = set(a.dropna().unique()), set(b.dropna().unique())
    status = "PASS" if sa == sb else "FAIL"
    log(f"  [{status}] {field}: {name_a} vs {name_b} -> "
        f"{'khop' if status=='PASS' else f'lech: chi co o {name_a}={sa-sb}, chi co o {name_b}={sb-sa}'}")

def check_subset(sub, sup, name_sub, name_sup, field):
    """Dung khi name_sub VE LY THUYET la tap con cua name_sup (vd: khong phai city/district nao
    trong geography cung phat sinh don giao hang trong shipments). Chi FAIL khi co gia tri
    trong name_sub ma KHONG ton tai trong name_sup - do la dau hieu du lieu rac / sai chinh ta."""
    s_sub, s_sup = set(sub.dropna().unique()), set(sup.dropna().unique())
    extra = s_sub - s_sup
    status = "PASS" if not extra else "FAIL"
    log(f"  [{status}] {field}: {name_sub} phai la tap con cua {name_sup} -> "
        f"{'khop (moi gia tri trong ' + name_sub + ' deu ton tai trong ' + name_sup + ')' if status=='PASS' else f'gia tri la trong {name_sub} khong co trong {name_sup}: {extra}'}")

check_match(orders["payment_method"], payments["payment_method"], "orders", "payments", "payment_method")
check_match(city_regions["region"], district_regions["region"], "city_regions", "district_regions", "region")
check_match(geography["region"], city_regions["region"], "geography", "city_regions", "region")
# shipments la tap con cua geography (khong phai city/district nao cung co don duoc giao toi)
check_subset(shipments["city"], geography["city"], "shipments", "geography", "city")
check_subset(shipments["district"], geography["district"], "shipments", "geography", "district")

# ================= PRODUCT_NAME INTEGRITY ASSERTION =================
log("\n=== ASSERTION: product_name / promo_name / shipper_name / sales_employee_name / review_title khong bi doi casing ===")
def assert_unchanged(bronze_path, dtype_col, col, bronze_key, silver_df, silver_key):
    b = pd.read_csv(bronze_path, dtype={dtype_col:"string", col:"string"})
    b = b.dropna(subset=[bronze_key])
    b[bronze_key] = b[bronze_key].astype("string").str.strip()
    m = b.merge(silver_df[[silver_key, col]], left_on=bronze_key, right_on=silver_key, suffixes=("_b","_s"))
    mismatch = m[m[f"{col}_b"] != m[f"{col}_s"]]
    status = "PASS" if len(mismatch)==0 else "FAIL"
    log(f"  [{status}] {col}: {len(mismatch)}/{len(m)} dong lech so voi bronze")
    return mismatch

assert_unchanged(RAW+"products.csv", "product_id", "product_name", "product_id", products, "product_id")
assert_unchanged(RAW+"promotions.csv", "promo_id", "promo_name", "promo_id", promotions, "promo_id")
assert_unchanged(RAW+"shippers.csv", "shipper_id", "shipper_name", "shipper_id", shippers, "shipper_id")
assert_unchanged(RAW+"employees.csv", "sales_employee_id", "sales_employee_name", "sales_employee_id", employees, "sales_employee_id")

# ================= BUSINESS RULE CHECKS =================
log("\n=== BUSINESS RULE CHECKS ===")
merged_ret = returns.merge(order_items, on=["order_id","product_id"], how="left", suffixes=("_ret","_oi"))
bad_ret = merged_ret[merged_ret["return_quantity"] > merged_ret["quantity"]]
log(f"  return_quantity > quantity goc: {len(bad_ret)} dong")

log("\n=== HOAN TAT ===")

print("\nDA XONG. Xem file trong", OUT)
