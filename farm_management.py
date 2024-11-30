from tkinter import *
from tkinter import messagebox, ttk
from datetime import datetime
import pymysql
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# DB 연결
def connect_db():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="farm_management",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

# Crop Name -> Crop ID 변환
def get_crop_id(crop_name):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT CropID FROM Crop WHERE CropName = %s", (crop_name,))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result['CropID'] if result else None

# Zone Name -> Zone ID 변환
def get_zone_id(zone_name, farmer_id):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT ZoneID FROM Zone WHERE ZoneName = %s AND FarmerID = %s", (zone_name, farmer_id))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result['ZoneID'] if result else None

def get_stock_id(farmer_id, crop_name):
    db = connect_db()
    cursor = db.cursor()
    crop_id = get_crop_id(crop_name)
    cursor.execute("SELECT StockID FROM Stock WHERE FarmerID = %s AND CropID = %s", (farmer_id, crop_id))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result['StockID'] if result else None

# 1. 재배 등록
def add_cultivation(farmer_id, crop_name, zone_name, crop_count):
    crop_id = get_crop_id(crop_name)
    zone_id = get_zone_id(zone_name, farmer_id)

    if not crop_id or not zone_id:
        messagebox.showerror("오류", "존재하지 않는 작물 이름 또는 구역 이름입니다.")
        return

    db = connect_db()
    cursor = db.cursor()
    query = """
    INSERT INTO Cultivation (ZoneID, CropID, CropCount, CultivationDate)
    VALUES (%s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (zone_id, crop_id, crop_count, datetime.now().date()))
        db.commit()
        messagebox.showinfo("성공", "재배 정보가 등록되었습니다.")
    except pymysql.MySQLError as err:
        db.rollback()
        messagebox.showerror("오류", f"재배 등록 실패: {err}")
    finally:
        cursor.close()
        db.close()

# 2. 수확 기록
def record_harvest(farmer_id, crop_name, zone_name, quantity):
    zone_id = get_zone_id(zone_name, farmer_id)
    crop_id = get_crop_id(crop_name)

    if not crop_id or not zone_id:
        messagebox.showerror("오류", "존재하지 않는 작물 이름 또는 구역 이름입니다.")
        return

    db = connect_db()
    cursor = db.cursor()
    query = """
    SELECT CultivationID FROM Cultivation WHERE ZoneID = %s AND CropID = %s
    """
    cursor.execute(query, (zone_id, crop_id))
    cultivation_id = cursor.fetchone()
    if not cultivation_id:
        messagebox.showerror("오류", "해당 구역에서 작물이 재배되고 있지 않습니다.")
        cursor.close()
        db.close()
        return
    # 수확량 > 재배수량 일때의 예외 처리
    try:
        cursor.execute("INSERT INTO Harvest (CultivationID, HarvestDate, Quantity) VALUES (%s, %s, %s)",
                       (cultivation_id['CultivationID'], datetime.now().date(), quantity))
        db.commit()
        messagebox.showinfo("성공", "수확 정보가 기록되었습니다.")
    except pymysql.MySQLError as err:
        db.rollback()
        messagebox.showerror("오류", f"수확 기록 실패: {err}")
    finally:
        cursor.close()
        db.close()


# 3. 판매 기록
def record_sale(farmer_id, crop_name, quantity, sale_price):
    db = connect_db()
    cursor = db.cursor()

    stock_id = get_stock_id(farmer_id, crop_name)

    if not stock_id:
        messagebox.showerror("오류", "재고 내역이 없습니다")
        cursor.close()
        db.close()
        return
    # 판매 수량 > 재고 수량 일때의 예외 처리
    try:
        cursor.execute("INSERT INTO Sales (StockID, SaleDate, SalePrice, Quantity) VALUES (%s, %s, %s, %s)",
                       (stock_id, datetime.now().date(), sale_price, quantity))
        db.commit()
        messagebox.showinfo("성공", "판매가 기록되었습니다.")
    except pymysql.MySQLError as err:
        db.rollback()
        messagebox.showerror("오류", f"판매 기록 실패: {err}")
    finally:
        cursor.close()
        db.close()


# 4. 경작지 등록
def add_zone(farmer_id, zone_name):

    db = connect_db()
    cursor = db.cursor()

    # 경작지 이름 중복 처리함(constraint)

    try:
        query = """
        INSERT INTO Zone (FarmerID, ZoneName)
        VALUES (%s, %s)
        """
        cursor.execute(query, (farmer_id, zone_name))
        db.commit()
        messagebox.showinfo("성공", "경작지가 등록되었습니다.")
    except pymysql.MySQLError as err:
        db.rollback()
        messagebox.showerror("오류", f"경작지 등록 실패: {err}")
    finally:
        cursor.close()
        db.close()

# 센서 데이터 파악
def plot_sensor_data(farmer_id, zone_name):
    db = connect_db()
    cursor = db.cursor()

    # FarmerID와 ZoneName으로 ZoneID 검색
    cursor.execute("SELECT ZoneID FROM Zone WHERE FarmerID = %s AND ZoneName = %s", (farmer_id, zone_name))
    zone = cursor.fetchone()
    
    if not zone:
        messagebox.showerror("오류", "존재하지 않는 구역입니다.")
        cursor.close()
        db.close()
        return
    
    zone_id = zone['ZoneID']

    # end_time = datetime.now()
    # start_time = end_time - timedelta(hours=24)


    # end_time을 2024-11-29 14:50:39로 설정 ----- test data에 맞게 시간 설정 
    end_time = datetime.strptime("2024-11-29 14:50:39", "%Y-%m-%d %H:%M:%S")
    # start_time은 end_time으로부터 24시간 전
    start_time = end_time - timedelta(hours=24)

    # 1시간 단위 평균 온도와 습도 데이터 검색
    query = """
    SELECT Type, HOUR(Timestamp) AS Hour, AVG(Value) AS AvgValue
    FROM SensorData
    INNER JOIN Sensor ON SensorData.SensorID = Sensor.SensorID
    WHERE Sensor.ZoneID = %s AND Timestamp BETWEEN %s AND %s
    GROUP BY Type, Hour
    ORDER BY Hour
    """
    cursor.execute(query, (zone_id, start_time, end_time))
    data = cursor.fetchall()
    cursor.close()
    db.close()

    # 데이터 분류 및 그래프 생성
    temperature = [d['AvgValue'] for d in data if d['Type'] == 'Temperature']
    humidity = [d['AvgValue'] for d in data if d['Type'] == 'Humidity']

    # 0 ~ 23
    hours = list(range(24))

    fig, ax1 = plt.subplots(figsize=(10, 5))
    # 온도 y축 (왼쪽)
    ax1.plot(hours, temperature, label="Temperature (°C)", color="red", linewidth=2.5, linestyle='-', marker='o', alpha=0.8)
    ax1.set_xlabel("Hours (Last 24)")
    ax1.set_ylabel("Temperature (°C)", color="red")
    ax1.tick_params(axis='y', labelcolor='red')
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)

    # 습도 y축 (오른쪽)
    ax2 = ax1.twinx()
    ax2.plot(hours, humidity, label="Humidity (%)", color="blue", linewidth=2.5, linestyle='--', marker='s', alpha=0.8)
    ax2.set_ylabel("Humidity (%)", color="blue")
    ax2.tick_params(axis='y', labelcolor='blue')

    # 겹치는 부분 강조
    # fig.tight_layout()  # 레이아웃 조정
    plt.title(f"Avg Temperature & Humidity per Hour (Last 24 Hours)")
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    plt.show()

# 재고 분석
def get_stock(farmer_id):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT c.CropName, s.Quantity, 
                   (SELECT SalePrice FROM Sales WHERE StockID = s.StockID ORDER BY SaleDate DESC LIMIT 1) AS RecentSalePrice,
                   (SELECT SalePrice FROM Sales WHERE StockID = s.StockID ORDER BY SaleDate DESC LIMIT 1) * s.Quantity AS ExpectedRevenue,
                   COALESCE(SUM(sa.Quantity) / 30, 0) AS AverageDailySales,
                   CASE WHEN SUM(sa.Quantity) / 30 > 0 THEN s.Quantity / (SUM(sa.Quantity) / 30) ELSE NULL END AS DaysToDepletion
            FROM Stock s
            JOIN Crop c ON s.CropID = c.CropID
            LEFT JOIN Sales sa ON s.StockID = sa.StockID AND sa.SaleDate >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            WHERE s.FarmerID = %s
            GROUP BY s.StockID;
            """
            cursor.execute(query, (farmer_id,))
            results = cursor.fetchall()

        if results:
            stock_window = Tk()
            stock_window.title("재고 조회 결과")

            columns = ("CropName", "Quantity", "RecentSalePrice", "ExpectedRevenue", "AverageDailySales", "DaysToDepletion")
            tree = ttk.Treeview(stock_window, columns=columns, show="headings")
            tree.heading("CropName", text="작물 이름")
            tree.heading("Quantity", text="재고 개수")
            tree.heading("RecentSalePrice", text="최근 판매가")
            tree.heading("ExpectedRevenue", text="예상 수익")
            tree.heading("AverageDailySales", text="하루 평균 판매량")
            tree.heading("DaysToDepletion", text="재고 소진 시기 (~일 후)")

            total_revenue = 0
            for row in results:
                tree.insert("", "end", values=(
                    row["CropName"], 
                    row["Quantity"], 
                    row["RecentSalePrice"], 
                    row["ExpectedRevenue"], 
                    row["AverageDailySales"], 
                    f'{row["DaysToDepletion"]:.2f}' if row["DaysToDepletion"] is not None else "N/A"
                ))
                if not row["ExpectedRevenue"]:
                    continue
                total_revenue += int(row["ExpectedRevenue"])
            tree.pack()
            Label(stock_window, text=f"총 예상 수익: {total_revenue:.2f}").pack(pady=5)
            
            stock_window.mainloop()
        else:
            print("재고가 없습니다.")
    finally:
        connection.close()

    
# 경작 대비 수확량 파악
def get_cultivation_yield(farmer_id):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT z.ZoneName, c.CropName, cl.CropCount, cl.CultivationDate, 
                   COALESCE(h.Quantity, 0) AS HarvestedQuantity,
                   COALESCE((h.Quantity / (cl.CropCount + h.Quantity)) * 100, 0) AS HarvestRatio
            FROM Cultivation cl
            JOIN Zone z ON cl.ZoneID = z.ZoneID
            JOIN Crop c ON cl.CropID = c.CropID
            LEFT JOIN Harvest h ON cl.CultivationID = h.CultivationID
            WHERE z.FarmerID = %s
            ORDER BY z.ZoneName;
            """
            cursor.execute(query, (farmer_id,))
            results = cursor.fetchall()

        if results:
            cultivation_window = Tk()
            cultivation_window.title("경작 대비 수확량 조회 결과")

            columns = ("ZoneName", "CropName", "CropCount", "CultivationDate", "HarvestedQuantity", "HarvestRatio")
            tree = ttk.Treeview(cultivation_window, columns=columns, show="headings")
            tree.heading("ZoneName", text="경작지 이름")
            tree.heading("CropName", text="작물 이름")
            tree.heading("CropCount", text="경작 수량")
            tree.heading("CultivationDate", text="경작 날짜")
            tree.heading("HarvestedQuantity", text="수확량")
            tree.heading("HarvestRatio", text="수확 비율 (%)")

            for row in results:
                tree.insert("", "end", values=(row["ZoneName"], row["CropName"], row["CropCount"], row["CultivationDate"], row["HarvestedQuantity"], f'{row["HarvestRatio"]:.2f}%'))

            tree.pack()
            cultivation_window.mainloop()
        else:
            print("경작 대비 수확량 데이터가 없습니다.")
    finally:
        connection.close()

# 판매 기록 조회
def get_sales_records(farmer_id):
    connection = connect_db()
    try:
        with connection.cursor() as cursor:
            query = """
            SELECT c.CropName, sa.SalePrice, sa.Quantity, sa.SaleDate, (sa.SalePrice * sa.Quantity) AS Revenue
            FROM Sales sa
            JOIN Stock s ON sa.StockID = s.StockID
            JOIN Crop c ON s.CropID = c.CropID
            WHERE s.FarmerID = %s
            ORDER BY sa.SaleDate DESC;
            """
            cursor.execute(query, (farmer_id,))
            results = cursor.fetchall()

        if results:
            sales_window = Tk()
            sales_window.title("판매 기록 조회")

            columns = ("CropName", "SalePrice", "Quantity", "SaleDate", "Revenue")
            tree = ttk.Treeview(sales_window, columns=columns, show="headings")
            tree.heading("CropName", text="작물 이름")
            tree.heading("SalePrice", text="개당 가격")
            tree.heading("Quantity", text="판매 수량")
            tree.heading("SaleDate", text="판매 일자")
            tree.heading("Revenue", text="수익")

            for row in results:
                tree.insert("", "end", values=(row["CropName"], row["SalePrice"], row["Quantity"], row["SaleDate"], row["Revenue"]))

            tree.pack()
            sales_window.mainloop()
        else:
            print("판매 기록이 없습니다.")
    finally:
        connection.close()

# UI 설계 ########################################
root = Tk()
root.title("Farm_Managemant")
root.geometry("900x900")

# 재배 등록 ########################################
Label(root, text="--- 재배 등록 ---").grid(row=0, column=0, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=1, column=0, padx=10, pady=5)
farmer_id_entry1 = Entry(root)
farmer_id_entry1.grid(row=1, column=1)

Label(root, text="Crop Name").grid(row=2, column=0, padx=10, pady=5)
crop_name_entry1 = Entry(root)
crop_name_entry1.grid(row=2, column=1)

Label(root, text="Zone Name").grid(row=3, column=0, padx=10, pady=5)
zone_name_entry1 = Entry(root)
zone_name_entry1.grid(row=3, column=1)

Label(root, text="Crop Count").grid(row=4, column=0, padx=10, pady=5)
crop_count_entry1 = Entry(root)
crop_count_entry1.grid(row=4, column=1)

Button(root, text="재배 등록", command=lambda: add_cultivation(
    farmer_id_entry1.get(),
    crop_name_entry1.get(),
    zone_name_entry1.get(),
    int(crop_count_entry1.get())
)).grid(row=5, column=0, columnspan=2, pady=10)

# 수확 기록 ########################################
Label(root, text="--- 수확 기록 ---").grid(row=6, column=0, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=7, column=0, padx=10, pady=5)
farmer_id_entry2 = Entry(root)
farmer_id_entry2.grid(row=7, column=1)

Label(root, text="Crop Name").grid(row=8, column=0, padx=10, pady=5)
harvest_crop_name_entry2 = Entry(root)
harvest_crop_name_entry2.grid(row=8, column=1)

Label(root, text="Zone Name").grid(row=9, column=0, padx=10, pady=5)
harvest_zone_name_entry2 = Entry(root)
harvest_zone_name_entry2.grid(row=9, column=1)

Label(root, text="Quantity").grid(row=10, column=0, padx=10, pady=5)
harvest_quantity_entry2 = Entry(root)
harvest_quantity_entry2.grid(row=10, column=1)

Button(root, text="수확 기록", command=lambda: record_harvest(
    farmer_id_entry2.get(),
    harvest_crop_name_entry2.get(),
    harvest_zone_name_entry2.get(),
    int(harvest_quantity_entry2.get())
)).grid(row=11, column=0, columnspan=2, pady=10)

# 판매 기록 ########################################
Label(root, text="--- 판매 기록 ---").grid(row=12, column=0, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=13, column=0, padx=10, pady=5)
farmer_id_entry3 = Entry(root)
farmer_id_entry3.grid(row=13, column=1)

Label(root, text="Crop Name").grid(row=14, column=0, padx=10, pady=5)
sale_crop_name_entry3 = Entry(root)
sale_crop_name_entry3.grid(row=14, column=1)

Label(root, text="Quantity").grid(row=15, column=0, padx=10, pady=5)
sale_quantity_entry3 = Entry(root)
sale_quantity_entry3.grid(row=15, column=1)

Label(root, text="Sale Price").grid(row=16, column=0, padx=10, pady=5)
sale_price_entry3 = Entry(root)
sale_price_entry3.grid(row=16, column=1)

Button(root, text="판매 기록", command=lambda: record_sale(
    farmer_id_entry3.get(),
    sale_crop_name_entry3.get(),
    int(sale_quantity_entry3.get()),
    float(sale_price_entry3.get())
)).grid(row=17, column=0, columnspan=2, pady=10)

# 경작지 등록 ########################################

Label(root, text="--- 경작지 등록 ---").grid(row=18, column=0, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=19, column=0, padx=10, pady=5)
farmer_id_entry4 = Entry(root)
farmer_id_entry4.grid(row=19, column=1)

Label(root, text="Zone Name").grid(row=20, column=0, padx=10, pady=5)
zone_name_entry4 = Entry(root)
zone_name_entry4.grid(row=20, column=1)

Button(root, text="경작지 등록", command=lambda: add_zone(
    farmer_id_entry4.get(),
    zone_name_entry4.get()
)).grid(row=21, column=0, columnspan=2, pady=10)


################################### 조회기능 시작

# 온/습도 현황 조회 ########################################
Label(root, text="--- 온/습도 현황 조회 ---").grid(row=0, column=2, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=1, column=2, padx=10, pady=5)
farmer_id_entry_sensor = Entry(root)
farmer_id_entry_sensor.grid(row=1, column=3)

Label(root, text="Zone Name").grid(row=2, column=2, padx=10, pady=5)
zone_name_entry_sensor = Entry(root)
zone_name_entry_sensor.grid(row=2, column=3)

Button(root, text="온/습도 현황 조회", command=lambda: plot_sensor_data(
    farmer_id_entry_sensor.get(),
    zone_name_entry_sensor.get()
)).grid(row=3, column=2, columnspan=2, pady=10)

# 재고 분석 ########################################
Label(root, text="--- 재고 분석 ---").grid(row=4, column=2, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=5, column=2, padx=10, pady=5)
farmer_id_entry_stock = Entry(root)
farmer_id_entry_stock.grid(row=5, column=3)

Button(root, text="재고 분석", command=lambda: get_stock(
    farmer_id_entry_stock.get(),
)).grid(row=6, column=2, columnspan=2, pady=10)

# 경작 대비 수확량 조회 ########################################
Label(root, text="--- 경작 대비 수확량 조회 ---").grid(row=7, column=2, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=8, column=2, padx=10, pady=5)
farmer_id_entry_cultharv = Entry(root)
farmer_id_entry_cultharv.grid(row=8, column=3)

Button(root, text="경작 대비 수확량 조회", command=lambda: get_cultivation_yield(
    farmer_id_entry_cultharv.get()
)).grid(row=9, column=2, columnspan=2, pady=10)

# 판매 기록 조회 ########################################
Label(root, text="--- 판매 기록 조회 ---").grid(row=10, column=2, columnspan=2, pady=10)
Label(root, text="Farmer ID").grid(row=11, column=2, padx=10, pady=5)
farmer_id_entry_sales = Entry(root)
farmer_id_entry_sales.grid(row=11, column=3)

Button(root, text="판매 기록 조회", command=lambda: get_sales_records(
    farmer_id_entry_sales.get()
)).grid(row=12, column=2, columnspan=2, pady=10)

root.mainloop()