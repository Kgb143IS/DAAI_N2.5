"""
PS4 — Phân tích Cơ cấu Doanh thu và Thị phần theo Khu vực Địa lý

Viết theo đúng phong cách và độ chi tiết của analyze_revenue_quantity.py (PS1):
không dùng những kỹ thuật/chỉ số mà đề bài không yêu cầu (không HHI, không cơ cấu
ngành hàng, không AOV/ARPU, không tăng trưởng — các phần đó thuộc PS1/PS2/PS3).

PS4 chỉ trả lời đúng 1 câu hỏi: DOANH THU mỗi khu vực địa lý (Region/District/City)
là bao nhiêu, CHIẾM BAO NHIÊU % trong tổng doanh thu công ty, và XẾP HẠNG thứ mấy.

Bảng tham gia -> Thước đo (cột gốc) -> Độ đo (doanh thu mỗi khu vực) ->
KPI (thị phần %, xếp hạng).

Quy ước đơn hàng tính doanh thu: giống hệt PS1 (analyze_revenue_quantity.py) —
loại đơn có order_status là cancelled/canceled/returned, doanh thu dòng =
quantity * unit_price - discount_amount.
"""

import os
import pandas as pd

DATA_DIR = "./silver_data/"           # thư mục chứa file CSV đầu vào -> đổi lại cho đúng
OUTPUT_DIR = "./Problem_statement4"   # thư mục xuất kết quả

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_data():
    """Đọc dữ liệu từ CSV vào DataFrame (giống PS1: orders, order_items, geography)."""
    orders = pd.read_csv(DATA_DIR + "silver_orders.csv", parse_dates=["order_date"])
    order_items = pd.read_csv(DATA_DIR + "silver_order_items.csv")
    geography = pd.read_csv(DATA_DIR + "silver_geography.csv")

    # Chỉ định rõ format ngày của file gốc (DD/MM/YYYY kiểu VN), tránh pandas hiểu
    # nhầm MM/DD/YYYY. Nếu file gốc là ISO ("2024-03-20") thì đổi format="%Y-%m-%d".
    orders["order_date"] = pd.to_datetime(orders["order_date"], format="%d/%m/%Y", errors="coerce")

    # Làm sạch dữ liệu địa lý: strip khoảng trắng thừa + chuẩn hoá chữ hoa,
    # tránh "BAC NINH" và "Bac Ninh " bị tính thành 2 khu vực khác nhau.
    for col in ["city", "district", "region"]:
        geography[col] = geography[col].astype(str).str.strip().str.upper()

    return orders, order_items, geography


def build_base_table(orders, order_items, geography):
    """
    Join order_items -> orders (theo order_id) -> geography (theo zip).
    Loại đơn cancelled/canceled/returned — ĐÚNG quy ước PS1 đang dùng, để doanh
    thu của PS4 khớp với doanh thu PS1 đã tính (đơn RETURNED bị loại nguyên đơn,
    không trừ riêng phần hoàn trả).
    Tính thêm cột 'revenue' (Thước đo -> Độ đo cấp dòng).
    """
    df = order_items.merge(orders, on="order_id", how="left")
    df = df.merge(geography, on="zip", how="left")

    if "order_status" in df.columns:
        df = df[~df["order_status"].str.lower().isin(["cancelled", "canceled", "returned"])]

    # Độ đo cấp dòng: doanh thu = quantity * unit_price - discount_amount
    df["revenue"] = df["quantity"] * df["unit_price"] - df["discount_amount"].fillna(0)

    return df


def market_share_by_level(df, level_col):
    """
    Độ đo: tổng doanh thu theo từng đơn vị của level_col (region/district/city).
    KPI: thị phần (%) = doanh thu đơn vị / tổng doanh thu toàn công ty x 100,
         và xếp hạng theo doanh thu giảm dần.
    """
    g = (
        df.groupby(level_col, as_index=False)["revenue"]
        .sum()
        .rename(columns={"revenue": "total_revenue"})
    )
    g["market_share_pct"] = (g["total_revenue"] / g["total_revenue"].sum() * 100).round(2)
    g["rank_by_revenue"] = g["total_revenue"].rank(ascending=False, method="dense").astype(int)
    g = g.sort_values("rank_by_revenue").reset_index(drop=True)
    return g


# ============ PROBLEM 4: CƠ CẤU DOANH THU VÀ THỊ PHẦN THEO KHU VỰC ĐỊA LÝ ============
def problem_4(df):
    # KPI theo Region
    region = market_share_by_level(df, "region")

    # KPI theo City — kèm cột region để biết thành phố đó thuộc vùng nào
    city = market_share_by_level(df, "city")
    city_region_map = df[["city", "region"]].drop_duplicates()
    city = city.merge(city_region_map, on="city", how="left")
    city = city[["rank_by_revenue", "city", "region", "total_revenue", "market_share_pct"]]

    # KPI theo District — kèm cột region
    district = market_share_by_level(df, "district")
    district_region_map = df[["district", "region"]].drop_duplicates()
    district = district.merge(district_region_map, on="district", how="left")
    district = district[["rank_by_revenue", "district", "region", "total_revenue", "market_share_pct"]]

    # Xuất file (đặt tên tiếng Việt cho dễ đọc khi ghép báo cáo chung)
    region.to_csv(os.path.join(OUTPUT_DIR, "p4_Thị_phần_theo_Vùng_miền.csv"), index=False, encoding="utf-8-sig")
    city.to_csv(os.path.join(OUTPUT_DIR, "p4_Thị_phần_theo_Thành_phố.csv"), index=False, encoding="utf-8-sig")
    district.to_csv(os.path.join(OUTPUT_DIR, "p4_Thị_phần_theo_Quận_huyện.csv"), index=False, encoding="utf-8-sig")

    print("[Problem 4] Đã xuất: p4_Thị_phần_theo_Vùng_miền.csv, p4_Thị_phần_theo_Thành_phố.csv, "
          "p4_Thị_phần_theo_Quận_huyện.csv")

    # Kiểm tra nhanh bằng mắt (giống tinh thần PS1 — không cần bộ assert phức tạp,
    # chỉ cần thị phần cộng lại đúng 100% là đủ tin tưởng số liệu không bị sai/sót/lặp).
    for name, g in [("Region", region), ("City", city), ("District", district)]:
        total_share = round(g["market_share_pct"].sum(), 1)
        print(f"  - Tổng thị phần {name}: {total_share}% (phải xấp xỉ 100%)")

    return region, city, district


def main():
    orders, order_items, geography = load_data()
    df = build_base_table(orders, order_items, geography)

    problem_4(df)

    print(f"\nHoàn tất. Toàn bộ file kết quả nằm trong thư mục: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
