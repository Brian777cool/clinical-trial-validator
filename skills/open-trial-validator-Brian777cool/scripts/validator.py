import sys
import json
import os
import csv
import math

# 注意：本系統所有病患資料皆為模擬資料；BIA 相位角與腫瘤尺寸的閾值為自訂的示範規則，
# 並非真實臨床試驗的收案標準，不可用於臨床決策。

# EMR 資料庫固定讀取與本檔案同一資料夾的 mock_emr_db.csv，不受執行時工作目錄影響
EMR_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_emr_db.csv")

# 數值欄位：(填報資料欄名, EMR 欄名, 比對容許誤差)
# 容許誤差依各欄位的報告精度設定（約為報告最小單位的一半）
NUMERIC_FIELDS = [
    ("bilirubin", "Bilirubin", 0.05),              # mg/dL，報告至 0.1
    ("albumin", "Albumin", 0.05),                  # g/dL，報告至 0.1
    ("inr", "INR", 0.005),                         # PT-INR，報告至 0.01
    ("ecw_ratio", "ECW_Ratio", 0.005),             # ECW/TBW，本模擬資料記錄至 0.01
    ("phase_angle", "Phase_Angle", 0.05),          # 度（50 kHz），報告至 0.1
    ("tumor_length_cm", "Tumor_Length_cm", 0.05),  # cm，報告至 0.1
    ("tumor_width_cm", "Tumor_Width_cm", 0.05),
    ("tumor_height_cm", "Tumor_Height_cm", 0.05),
]

ALLOWED_ASCITES = ["none", "mild", "moderate", "severe"]
ALLOWED_ENCEPHALOPATHY = ["none", "grade 1", "grade 2", "grade 3", "grade 4"]  # West Haven 分級

REQUIRED_FIELDS = (["patient_id", "platelet_count"]
                   + [field for field, _, _ in NUMERIC_FIELDS]
                   + ["ascites", "encephalopathy"])

# 示範規則的閾值
DEMO_PHASE_ANGLE_MIN = 4.0         # 相位角下限（示範規則）
DEMO_TUMOR_AXIS_MAX_CM = 20.0      # 單一徑長上限（超過時請人工確認）
DEMO_TUMOR_VOLUME_MAX_CM3 = 250.0  # 腫瘤體積上限（示範規則）


def calculate_tumor_volume(length, width, height):
    # 三徑橢球體積估算公式 (pi/6 * L * W * H)，為常用的近似公式
    volume = (math.pi / 6) * length * width * height
    return round(volume, 2)


# 醫療演算法：Child-Pugh 自動計分
def get_child_pugh_score(bilirubin, albumin, inr, ascites, encephalopathy):
    score = 0
    # Bilirubin (mg/dL)
    if bilirubin < 2.0: score += 1
    elif bilirubin <= 3.0: score += 2
    else: score += 3

    # Albumin (g/dL)
    if albumin > 3.5: score += 1
    elif albumin >= 2.8: score += 2
    else: score += 3

    # PT-INR
    if inr < 1.7: score += 1
    elif inr <= 2.3: score += 2
    else: score += 3

    # Ascites
    if ascites == "none": score += 1
    elif ascites == "mild": score += 2
    elif ascites in ["moderate", "severe"]: score += 3
    else: raise ValueError(f"未知的腹水分級: {ascites}")

    # Hepatic encephalopathy (West Haven)
    if encephalopathy == "none": score += 1
    elif encephalopathy in ["grade 1", "grade 2"]: score += 2
    elif encephalopathy in ["grade 3", "grade 4"]: score += 3
    else: raise ValueError(f"未知的肝性腦病變分級: {encephalopathy}")

    if score <= 6: return score, "A"
    elif score <= 9: return score, "B"
    else: return score, "C"


def _parse_positive_number(value):
    """轉成正的有限數值；空白、NaN、無限大、零或負值都視為無效，回傳 None。"""
    try:
        number = float(str(value).strip())
    except (ValueError, TypeError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _parse_platelet(value):
    """血小板計數必須是正整數（單位 /µL）。"""
    number = _parse_positive_number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _parse_record(record):
    """把一筆資料（填報資料或 EMR 紀錄）轉成標準格式；有問題時回傳 (None, 錯誤訊息)。"""
    parsed = {}
    platelet = _parse_platelet(record.get("platelet_count"))
    if platelet is None:
        return None, "platelet_count 必須是正整數（/µL）"
    parsed["platelet_count"] = platelet

    for field, emr_col, _ in NUMERIC_FIELDS:
        raw = record.get(field, record.get(emr_col))
        number = _parse_positive_number(raw)
        if number is None:
            return None, f"{field} 必須是大於 0 的數值"
        parsed[field] = number

    ascites = str(record.get("ascites", record.get("Ascites", ""))).strip()
    if ascites not in ALLOWED_ASCITES:
        return None, f"ascites 只接受 {ALLOWED_ASCITES}"
    encephalopathy = str(record.get("encephalopathy", record.get("Encephalopathy", ""))).strip()
    if encephalopathy not in ALLOWED_ENCEPHALOPATHY:
        return None, f"encephalopathy 只接受 {ALLOWED_ENCEPHALOPATHY}"
    parsed["ascites"] = ascites
    parsed["encephalopathy"] = encephalopathy
    return parsed, None


def _find_emr_record(patient_id):
    """從 EMR 資料庫中找出該病患的紀錄；找不到回傳 None。"""
    with open(EMR_DB_PATH, mode='r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row.get('patient_id', '').strip() == patient_id:
                return row
    return None


# 核心驗證 API (與 CLI 解耦，方便 Pytest 匯入測試)
def validate_trial(data):
    if not isinstance(data, dict):
        return False, "Data Type Violation: 輸入必須是 JSON 物件"

    # 1. 欄位完整性檢查（空白也視為缺漏）
    for req in REQUIRED_FIELDS:
        if req not in data or str(data[req]).strip() == "":
            return False, f"Missing required field: {req}"

    # 2. 型別與數值範圍檢查
    reported, error = _parse_record(data)
    if error:
        return False, f"Data Type Violation: {error}"
    pid = str(data["patient_id"]).strip()

    # 3. 資料合理性檢查（示範上限）
    axes = [reported["tumor_length_cm"], reported["tumor_width_cm"], reported["tumor_height_cm"]]
    if max(axes) > DEMO_TUMOR_AXIS_MAX_CM:
        return False, (f"Data Error: 腫瘤單一徑長超過示範上限 {DEMO_TUMOR_AXIS_MAX_CM:.0f} cm，"
                       f"請人工確認數值。")

    # 4. 原始資料核對：填報資料 vs EMR；EMR 資料庫不存在或查無病患時，一律拒絕，不靜默放行
    if not os.path.exists(EMR_DB_PATH):
        return False, "Data Error: 找不到 EMR 資料庫 mock_emr_db.csv，無法進行核對。"

    row = _find_emr_record(pid)
    if row is None:
        return False, f"Data Error: 找不到病患 {pid} 的 EMR 紀錄。"

    emr, error = _parse_record(row)
    if error:
        return False, f"Data Error: {pid} 的 EMR 紀錄格式錯誤（{error}）。"

    mismatched = []
    if reported["platelet_count"] != emr["platelet_count"]:
        mismatched.append("platelet_count")
    for field, _, tolerance in NUMERIC_FIELDS:
        if round(abs(reported[field] - emr[field]), 6) > tolerance:
            mismatched.append(field)
    for field in ["ascites", "encephalopathy"]:
        if reported[field] != emr[field]:
            mismatched.append(field)
    if mismatched:
        return False, (f"Source data mismatch（與 EMR 原始資料不符）: {pid} 的 "
                       f"{', '.join(mismatched)} 與 EMR 不一致，請核對原始文件。")

    # 5. 收案條件判定：一律以 EMR 原始資料計算，並列出所有未符合的條件
    result = dict(data)
    score, cp_class = get_child_pugh_score(
        emr["bilirubin"], emr["albumin"], emr["inr"], emr["ascites"], emr["encephalopathy"]
    )
    volume = calculate_tumor_volume(emr["tumor_length_cm"], emr["tumor_width_cm"], emr["tumor_height_cm"])
    result["calculated_cp_score"] = score
    result["calculated_cp_class"] = cp_class
    result["calculated_tumor_volume_cm3"] = volume

    reasons = []
    if cp_class != "A":
        reasons.append(f"Child-Pugh {score} 分（Class {cp_class}），本試驗僅收 Class A")
    if emr["phase_angle"] < DEMO_PHASE_ANGLE_MIN:
        reasons.append(f"相位角 {emr['phase_angle']} 低於示範閾值 {DEMO_PHASE_ANGLE_MIN}（示範規則）")
    if volume > DEMO_TUMOR_VOLUME_MAX_CM3:
        reasons.append(f"腫瘤體積 {volume} cm³ 超過示範上限 {DEMO_TUMOR_VOLUME_MAX_CM3:.0f} cm³（示範規則）")
    if reasons:
        return False, f"Not eligible（未符合收案條件）: {'；'.join(reasons)}"

    result["is_eligible"] = True
    return True, result


# CLI 執行入口
def main():
    if len(sys.argv) < 2:
        print("Error: Missing input JSON")
        sys.exit(1)

    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        sys.exit(1)

    is_valid, result = validate_trial(data)

    if not is_valid:
        print(result)
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    output_filename = "validation_result.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    print(f"✓ 已將驗證結果匯出至 {output_filename}")


if __name__ == "__main__":
    main()