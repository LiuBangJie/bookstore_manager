import sqlite3
import datetime
from typing import Any

DB_NAME: str = 'bookstore.db'


def connect_db() -> sqlite3.Connection:
    """
    建立並返回 SQLite 資料庫連線，設置 row_factory = sqlite3.Row。
    Returns:
        sqlite3.Connection: 設定好 row_factory 的資料庫連線
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    """
    初始化資料庫，建立資料表與初始資料。
    參數:
        conn (sqlite3.Connection): SQLite 資料庫連線物件
    """
    cursor = conn.cursor()
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS member (
        mid TEXT PRIMARY KEY,
        mname TEXT NOT NULL,
        mphone TEXT NOT NULL,
        memail TEXT
    );

    CREATE TABLE IF NOT EXISTS book (
        bid TEXT PRIMARY KEY,
        btitle TEXT NOT NULL,
        bprice INTEGER NOT NULL,
        bstock INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sale (
        sid INTEGER PRIMARY KEY AUTOINCREMENT,
        sdate TEXT NOT NULL,
        mid TEXT NOT NULL,
        bid TEXT NOT NULL,
        sqty INTEGER NOT NULL,
        sdiscount INTEGER NOT NULL,
        stotal INTEGER NOT NULL
    );

    INSERT OR IGNORE INTO member VALUES ('M001', 'Alice', '0912-345678', 'alice@example.com');
    INSERT OR IGNORE INTO member VALUES ('M002', 'Bob', '0923-456789', 'bob@example.com');
    INSERT OR IGNORE INTO member VALUES ('M003', 'Cathy', '0934-567890', 'cathy@example.com');

    INSERT OR IGNORE INTO book VALUES ('B001', 'Python Programming', 600, 50);
    INSERT OR IGNORE INTO book VALUES ('B002', 'Data Science Basics', 800, 30);
    INSERT OR IGNORE INTO book VALUES ('B003', 'Machine Learning Guide', 1200, 20);

    INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) SELECT '2024-01-15', 'M001', 'B001', 2, 100, 1100
    WHERE NOT EXISTS (SELECT 1 FROM sale WHERE sid = 1);
    INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) SELECT '2024-01-16', 'M002', 'B002', 1, 50, 750
    WHERE NOT EXISTS (SELECT 1 FROM sale WHERE sid = 2);
    INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) SELECT '2024-01-17', 'M001', 'B003', 3, 200, 3400
    WHERE NOT EXISTS (SELECT 1 FROM sale WHERE sid = 3);
    INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) SELECT '2024-01-18', 'M003', 'B001', 1, 0, 600
    WHERE NOT EXISTS (SELECT 1 FROM sale WHERE sid = 4);
    ''')
    conn.commit()


def add_sale(conn: sqlite3.Connection) -> tuple[bool, str]:
    """
    新增銷售記錄，驗證會員、書籍編號和庫存，計算總額並更新庫存。
    回傳:
        tuple: (是否成功, 訊息)
    """
    try:
        sdate = input('請輸入銷售日期 (YYYY-MM-DD)：')
        if len(sdate) != 10 or sdate.count('-') != 2:
            return False, '=> 錯誤：日期格式應為 YYYY-MM-DD'

        mid = input('請輸入會員編號：')
        bid = input('請輸入書籍編號：')

        try:
            sqty = int(input('請輸入購買數量：'))
            if sqty <= 0:
                return False, '=> 錯誤：數量必須為正整數'
        except ValueError:
            return False, '=> 錯誤：數量必須為整數'

        try:
            sdiscount = int(input('請輸入折扣金額：'))
            if sdiscount < 0:
                return False, '=> 錯誤：折扣金額不得為負'
        except ValueError:
            return False, '=> 錯誤：折扣金額必須為整數'

        cursor = conn.cursor()

        cursor.execute('SELECT * FROM member WHERE mid = ?', (mid,))
        if not cursor.fetchone():
            return False, '=> 錯誤：會員編號不存在'

        cursor.execute('SELECT bprice, bstock FROM book WHERE bid = ?', (bid,))
        row = cursor.fetchone()
        if not row:
            return False, '=> 錯誤：書籍編號不存在'

        bprice, bstock = row['bprice'], row['bstock']
        if bstock < sqty:
            return False, f'=> 錯誤：庫存不足 (現有庫存: {bstock})'

        stotal = (bprice * sqty) - sdiscount

        try:
            cursor.execute('INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES (?, ?, ?, ?, ?, ?)',
                           (sdate, mid, bid, sqty, sdiscount, stotal))
            cursor.execute('UPDATE book SET bstock = bstock - ? WHERE bid = ?', (sqty, bid))
            conn.commit()
            return True, f'=> 銷售記錄已新增！(銷售總額: {stotal:,})'
        except sqlite3.Error:
            conn.rollback()
            return False, '=> 錯誤：新增銷售記錄失敗，交易已回復'

    except Exception as e:
        return False, f'=> 系統錯誤：{e}'


def update_sale(conn: sqlite3.Connection) -> None:
    """
    顯示銷售記錄列表，讓使用者選擇更新哪一筆折扣金額，並重新計算與更新總額。
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.sid, m.mname, s.sdate
        FROM sale s
        JOIN member m ON s.mid = m.mid
        ORDER BY s.sid
    ''')
    sales = cursor.fetchall()

    if not sales:
        print('=> 沒有可更新的銷售記錄')
        return

    print("\n======== 銷售記錄列表 ========")
    for i, row in enumerate(sales, start=1):
        print(f"{i}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
    print("================================")

    choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ")
    if not choice.strip():
        return

    try:
        index = int(choice) - 1
        if not (0 <= index < len(sales)):
            print("=> 錯誤：請輸入有效的選項")
            return
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
        return

    sid = sales[index]['sid']

    try:
        sdiscount = int(input("請輸入新的折扣金額："))
        if sdiscount < 0:
            print("=> 錯誤：折扣金額不得為負")
            return
    except ValueError:
        print("=> 錯誤：折扣金額必須為整數")
        return

    cursor.execute('SELECT bid, sqty FROM sale WHERE sid = ?', (sid,))
    row = cursor.fetchone()
    bid, sqty = row['bid'], row['sqty']

    cursor.execute('SELECT bprice FROM book WHERE bid = ?', (bid,))
    bprice = cursor.fetchone()['bprice']

    stotal = (bprice * sqty) - sdiscount

    cursor.execute('UPDATE sale SET sdiscount = ?, stotal = ? WHERE sid = ?',
                   (sdiscount, stotal, sid))
    conn.commit()
    print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {stotal:,})")


def delete_sale(conn: sqlite3.Connection) -> None:
    """
    顯示銷售記錄列表，提示使用者輸入要刪除的銷售編號，執行刪除操作並提交。
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.sid, m.mname, s.sdate
        FROM sale s
        JOIN member m ON s.mid = m.mid
        ORDER BY s.sid
    ''')
    sales = cursor.fetchall()

    if not sales:
        print('=> 沒有可刪除的銷售記錄')
        return

        print("\n======== 銷售記錄列表 ========")
    for i, row in enumerate(sales, start=1):
        print(f"{i}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
    print("================================")

    choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ")
    if not choice.strip():
        return

    try:
        index = int(choice) - 1
        if not (0 <= index < len(sales)):
            print("=> 錯誤：請輸入有效的數字")
            return
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
        return

    sid = sales[index]['sid']
    cursor.execute('DELETE FROM sale WHERE sid = ?', (sid,))
    conn.commit()
    print(f"=> 銷售編號 {sid} 已刪除")


# 顯示銷售報表

def show_sales() -> None:
    """
    顯示所有銷售報表，包括銷售編號、日期、會員姓名、書籍標題、單價、數量、折扣與總額。
    使用千位符號格式化金額。
    """
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, s.sqty, s.sdiscount, s.stotal
            FROM sale s
            JOIN member m ON s.mid = m.mid
            JOIN book b ON s.bid = b.bid
            ORDER BY s.sid
        ''')
        rows = cursor.fetchall()

        print('\n' + '=' * 20 + ' 銷售報表 ' + '=' * 20)

        for idx, row in enumerate(rows, start=1):
            print(f'銷售 #{idx}')
            print(f'銷售編號: {row["sid"]}')
            print(f'銷售日期: {row["sdate"]}')
            print(f'會員姓名: {row["mname"]}')
            print(f'書籍標題: {row["btitle"]}')
            print('-' * 50)
            print(f'單價\t數量\t折扣\t小計')
            print('-' * 50)
            print(f'{row["bprice"]:,}\t{row["sqty"]}\t{row["sdiscount"]}\t{row["stotal"]:,}')
            print('-' * 50)
            print(f'銷售總額: {row["stotal"]:,}')
            print('=' * 50)


# 主程式執行流程
conn = connect_db()
initialize_db(conn)

while True:
    try:
        print('*' * 15 + '選單' + '*' * 15)
        print('1. 新增銷售記錄')
        print('2. 顯示銷售報表')
        print('3. 更新銷售記錄')
        print('4. 刪除銷售記錄')
        print('5. 離開')
        print('*' * 34)

        choice = input('請選擇操作項目(Enter 離開)：')

        if choice == '1':
            success, message = add_sale(conn)
            print(message)
        elif choice == '2':
            show_sales()
        elif choice == '3':
            update_sale(conn)
        elif choice == '4':
            delete_sale(conn)
        elif choice == '5' or choice == '':
            print('程式結束！')
            break
        else:
            print('=> 請輸入有效的選項（1-5）')
    except ValueError:
        print('=> 錯誤：輸入格式錯誤（非整數）')
    except sqlite3.OperationalError as oe:
        print(f'=> 錯誤：資料庫操作錯誤 - {oe}')
    except sqlite3.DatabaseError as de:
        print(f'=> 錯誤：資料庫錯誤 - {de}')
