import os
import pandas as pd

# ============ CẤU HÌNH ĐƯỜNG DẪN ============
# INPUT_DIR = "./data"          # thư mục chứa file CSV đầu vào -> đổi lại cho đúng
OUTPUT_DIR = "./Problem_statement1_2"       # thư mục xuất kết quả

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data():
    """Đọc dữ liệu từ CSV vào DataFrame."""
    orders = pd.read_csv("./silver_data/silver_orders.csv", parse_dates=["order_date"])
    order_items = pd.read_csv("./silver_data/silver_order_items.csv")
    geography = pd.read_csv("./silver_data/silver_geography.csv")

    # QUAN TRỌNG: chỉ định rõ format ngày của file gốc để tránh pandas hiểu nhầm
    # MM/DD/YYYY (mặc định kiểu Mỹ) khi thực chất file đang ở DD/MM/YYYY (kiểu VN).
    # Nếu order_date trong orders.csv ở dạng "20/03/2024" -> dùng format dưới đây.
    # Nếu file gốc đã là "2024-03-20" (ISO) thì đổi format="%Y-%m-%d".
    orders["order_date"] = pd.to_datetime(orders["order_date"], format="%d/%m/%Y", errors="coerce")

    # LÀM SẠCH dữ liệu địa lý: strip khoảng trắng thừa + chuẩn hoá chữ hoa
    # để tránh "BAC NINH" và "Bac Ninh " bị group thành 2 dòng khác nhau.
    for col in ["city", "district", "region"]:
        geography[col] = geography[col].astype(str).str.strip().str.upper()

    # Kiểm tra: liệu 1 zip có bị map vào nhiều hơn 1 tổ hợp (city, district, region) không
    dup_check = geography.groupby("zip")[["city", "district", "region"]].nunique()
    inconsistent_zip = dup_check[(dup_check > 1).any(axis=1)]
    if len(inconsistent_zip) > 0:
        print(f"[CẢNH BÁO] Có {len(inconsistent_zip)} zip bị map không nhất quán "
              f"(cùng 1 zip nhưng khác city/district/region ở các dòng khác nhau). "
              f"Xem chi tiết: geography[geography['zip'].isin({list(inconsistent_zip.index)[:5]}...)]")

    return orders, order_items, geography


def build_base_table(orders, order_items, geography):
    """
    Join order_items -> orders (theo order_id) -> geography (theo zip)
    Loại bỏ đơn hàng bị hủy (order_status == 'cancelled') nếu có.
    Tính thêm cột 'month' và cột 'revenue' (Metric cấp dòng).
    """
    df = order_items.merge(orders, on="order_id", how="left")
    df = df.merge(geography, on="zip", how="left")

    if "order_status" in df.columns:
        df = df[~df["order_status"].str.lower().isin(["cancelled", "canceled", "returned"])]

    # month_dt: dùng NỘI BỘ để sort/tính toán (giữ kiểu datetime thật, sort đúng thứ tự thời gian)
    df["month_dt"] = df["order_date"].dt.to_period("M").dt.to_timestamp()
    df["year"] = df["order_date"].dt.year

    # Metric cấp dòng: doanh thu thực = quantity * unit_price - discount_amount
    df["revenue"] = df["quantity"] * df["unit_price"] - df["discount_amount"].fillna(0)

    return df


def calc_mom_growth(df, group_cols, value_col):
    """
    Tính % tăng trưởng tháng-so-tháng (MoM growth) cho 1 metric,
    theo từng nhóm (VD: theo city, hoặc theo region).
    Sắp xếp theo 'month_dt' (kiểu datetime thật) để đảm bảo đúng thứ tự thời gian,
    kể cả khi dữ liệu vắt qua nhiều năm.
    Trả về DataFrame có thêm cột 'mom_growth_pct'.
    """
    df = df.sort_values(group_cols + ["month_dt"]).copy()
    df["prev_value"] = df.groupby(group_cols)[value_col].shift(1)
    df["mom_growth_pct"] = (df[value_col] - df["prev_value"]) / df["prev_value"] * 100
    return df


def format_month_for_export(df):
    """Chuyển 'month_dt' (datetime) thành cột 'month' dạng chuỗi DD/MM/YYYY để xuất CSV,
    tránh bị Excel tự động đổi định dạng theo locale máy tính."""
    df = df.copy()
    df["month"] = df["month_dt"].dt.strftime("%d/%m/%Y")
    df = df.drop(columns=["month_dt"])
    return df


# ============ PROBLEM 1: DOANH THU PHÂN CẤP CITY / DISTRICT / REGION ============
def problem_1(df):
    group_cols = ["region", "district", "city"]

    # Metric: tổng doanh thu theo tháng, theo từng cấp địa lý (group theo month_dt để giữ đúng thứ tự)
    revenue_monthly = (
        df.groupby(group_cols + ["month_dt"], as_index=False)["revenue"]
        .sum()
        .rename(columns={"revenue": "total_revenue"})
    )
    revenue_monthly["year"] = revenue_monthly["month_dt"].dt.year

    # KPI: % tăng trưởng MoM (tính trên toàn bộ chuỗi tháng liên tục, không cắt theo năm,
    # vì tháng 1/2024 vẫn cần so với tháng 12/2023 để ra đúng % tăng trưởng)
    revenue_growth = calc_mom_growth(revenue_monthly, group_cols, "total_revenue")

    # KPI theo TỪNG NĂM: trung bình % tăng trưởng của các tháng TRONG năm đó
    kpi_by_year = (
        revenue_growth.groupby(group_cols + ["year"], as_index=False)
        .agg(
            avg_monthly_growth_pct=("mom_growth_pct", "mean"),
            total_revenue_in_year=("total_revenue", "sum"),
        )
        .sort_values(group_cols + ["year"])
    )
    kpi_by_year["avg_monthly_growth_pct"] = kpi_by_year["avg_monthly_growth_pct"].round(2)

    # KPI toàn thời gian (giữ lại để so sánh/tham khảo)
    kpi_summary = (
        revenue_growth.groupby(group_cols, as_index=False)
        .agg(
            avg_monthly_growth_pct=("mom_growth_pct", "mean"),
            total_revenue_all_time=("total_revenue", "sum"),
        )
        .sort_values("avg_monthly_growth_pct", ascending=False)
    )
    kpi_summary["avg_monthly_growth_pct"] = kpi_summary["avg_monthly_growth_pct"].round(2)

    # Format month -> chuỗi DD/MM/YYYY trước khi xuất file
    revenue_monthly = format_month_for_export(revenue_monthly)
    revenue_growth = format_month_for_export(revenue_growth)

    # Xuất file
    revenue_monthly.to_csv(os.path.join(OUTPUT_DIR, "p1_revenue_monthly.csv"), index=False)
    revenue_growth.to_csv(os.path.join(OUTPUT_DIR, "p1_revenue_growth_detail.csv"), index=False)
    kpi_by_year.to_csv(os.path.join(OUTPUT_DIR, "p1_kpi_by_year.csv"), index=False)
    kpi_summary.to_csv(os.path.join(OUTPUT_DIR, "p1_kpi_avg_monthly_growth.csv"), index=False)

    print("[Problem 1] Đã xuất: p1_revenue_monthly.csv, p1_revenue_growth_detail.csv, "
          "p1_kpi_by_year.csv, p1_kpi_avg_monthly_growth.csv")
    return kpi_summary


# ============ PROBLEM 2: SO SÁNH SẢN LƯỢNG TIÊU THỤ GIỮA CÁC VÙNG ============
def problem_2(df):
    group_cols = ["region"]

    # Metric: tổng sản lượng theo tháng, theo từng Region
    qty_monthly = (
        df.groupby(group_cols + ["month_dt"], as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "total_quantity"})
    )
    qty_monthly["year"] = qty_monthly["month_dt"].dt.year

    # Metric phụ: chênh lệch sản lượng so với vùng dẫn đầu trong cùng tháng
    qty_monthly["max_region_quantity"] = qty_monthly.groupby("month_dt")["total_quantity"].transform("max")
    qty_monthly["gap_to_top_region"] = qty_monthly["max_region_quantity"] - qty_monthly["total_quantity"]

    # KPI: % tăng trưởng MoM sản lượng theo từng Region (tính liên tục qua các năm)
    qty_growth = calc_mom_growth(qty_monthly, group_cols, "total_quantity")

    # KPI theo TỪNG NĂM
    kpi_by_year = (
        qty_growth.groupby(group_cols + ["year"], as_index=False)
        .agg(
            avg_monthly_qty_growth_pct=("mom_growth_pct", "mean"),
            total_quantity_in_year=("total_quantity", "sum"),
        )
        .sort_values(group_cols + ["year"])
    )
    kpi_by_year["avg_monthly_qty_growth_pct"] = kpi_by_year["avg_monthly_qty_growth_pct"].round(2)

    # KPI toàn thời gian (giữ lại để so sánh/tham khảo)
    kpi_summary = (
        qty_growth.groupby(group_cols, as_index=False)
        .agg(
            avg_monthly_qty_growth_pct=("mom_growth_pct", "mean"),
            total_quantity_all_time=("total_quantity", "sum"),
        )
        .sort_values("avg_monthly_qty_growth_pct", ascending=False)
    )
    kpi_summary["avg_monthly_qty_growth_pct"] = kpi_summary["avg_monthly_qty_growth_pct"].round(2)

    # Format month -> chuỗi DD/MM/YYYY trước khi xuất file
    qty_monthly = format_month_for_export(qty_monthly)
    qty_growth = format_month_for_export(qty_growth)

    # Xuất file
    qty_monthly.to_csv(os.path.join(OUTPUT_DIR, "p2_quantity_monthly_and_gap.csv"), index=False)
    qty_growth.to_csv(os.path.join(OUTPUT_DIR, "p2_quantity_growth_detail.csv"), index=False)
    kpi_by_year.to_csv(os.path.join(OUTPUT_DIR, "p2_kpi_by_year.csv"), index=False)
    kpi_summary.to_csv(os.path.join(OUTPUT_DIR, "p2_kpi_avg_monthly_growth.csv"), index=False)

    print("[Problem 2] Đã xuất: p2_quantity_monthly_and_gap.csv, p2_quantity_growth_detail.csv, "
          "p2_kpi_by_year.csv, p2_kpi_avg_monthly_growth.csv")
    return kpi_summary


def main():
    orders, order_items, geography = load_data()
    df = build_base_table(orders, order_items, geography)

    problem_1(df)
    problem_2(df)

    print(f"\nHoàn tất. Toàn bộ file kết quả nằm trong thư mục: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()