import sys
import json
import sqlite3

def setup_mock_db():
    # 在記憶體中光速建立一個虛擬資料庫，執行完就消失，不留痕跡
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # 建立員工資料表
    cursor.execute('''
        CREATE TABLE employees (
            emp_id INTEGER PRIMARY KEY,
            name TEXT,
            department TEXT,
            salary INTEGER,
            hire_date DATE
        )
    ''')
    
    # 塞入四筆測試用的假資料
    cursor.executemany('''
        INSERT INTO employees (name, department, salary, hire_date)
        VALUES (?, ?, ?, ?)
    ''', [
        ('Alice', 'Engineering', 60000, '2023-01-15'),
        ('Bob', 'HR', 45000, '2023-02-20'),
        ('Charlie', 'Engineering', 75000, '2022-11-01'),
        ('Diana', 'Marketing', 52000, '2024-01-10')
    ])
    conn.commit()
    return conn

def main():
    if len(sys.argv) < 2:
        print("Error: Missing input JSON file path.")
        sys.exit(1)

    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Invalid JSON format. Details: {str(e)}")
        sys.exit(1)

    # 1. 檢查必填欄位
    if "generated_sql" not in data:
        print("Error: Missing 'generated_sql' field. You must output the SQL query.")
        sys.exit(1)

    sql_query = data["generated_sql"]

    # 2. 確定性防線：真實 SQLite 執行測試
    conn = setup_mock_db()
    cursor = conn.cursor()

    try:
        # 嘗試在虛擬資料庫中執行 LLM 寫的 SQL 語法
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        # 執行成功！將結果加回 JSON 中
        data["execution_status"] = "Success"
        data["row_count"] = len(results)
        data["query_results"] = results  # 把撈出來的資料也秀出來

    except sqlite3.Error as e:
        # 如果 SQL 語法寫錯（例如欄位拼錯、選到不存在的 table），直接報錯打臉！
        print(f"SQLite Execution Error: {str(e)}")
        print("Please fix your SQL syntax based on the provided schema and try again.")
        sys.exit(1)
    finally:
        conn.close()

    # 3. 完美通過，產出期末要求的 JSON 格式
    print("```json")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("```")

if __name__ == "__main__":
    main()