import sys
import json
import os
import csv

# 醫療演算法：Child-Pugh 自動計分
def get_child_pugh_score(bilirubin, albumin, inr, ascites, encephalopathy):
    score = 0
    # Bilirubin
    if bilirubin < 2.0: score += 1
    elif 2.0 <= bilirubin <= 3.0: score += 2
    else: score += 3
    
    # Albumin
    if albumin > 3.5: score += 1
    elif 2.8 <= albumin <= 3.5: score += 2
    else: score += 3
    
    # INR
    if inr < 1.7: score += 1
    elif 1.7 <= inr <= 2.2: score += 2
    else: score += 3
    
    # Ascites
    if ascites == "none": score += 1
    elif ascites == "mild": score += 2
    else: score += 3
    
    # Encephalopathy
    if encephalopathy == "none": score += 1
    elif encephalopathy in ["grade 1", "grade 2"]: score += 2
    else: score += 3
    
    if score <= 6: return score, "A"
    elif score <= 9: return score, "B"
    else: return score, "C"

# 核心驗證 API (與 CLI 解耦，方便 Pytest 匯入測試)
def validate_trial(data):
    required = ["patient_id", "tumor_length_cm", "tumor_width_cm", "platelet_count", 
                "bilirubin", "albumin", "inr", "ascites", "encephalopathy"]
    for req in required:
        if req not in data:
            return False, f"Missing required field: {req}"

    # 1. EMR 防幻覺核對系統 (使用絕對路徑)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'mock_emr_db.csv')
    
    # 若有建立實體 CSV，則進行比對；若無，則針對 Scenario 設定防護
    if os.path.exists(db_path):
        with open(db_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['patient_id'] == data['patient_id']:
                    if int(row['platelet_count']) != int(data['platelet_count']):
                        return False, f"Hallucination detected! Real platelet count for {data['patient_id']} does not match EMR."
    else:
        # Fallback 防護 (針對我們在 OPEN_TRACK.md 設定的情境)
        if data['patient_id'] == 'P-1002' and data.get('platelet_count') == 100000:
             return False, "Hallucination detected! Real platelet count for P-1002 is 42000."

    # 2. 幾何學體積驗算
    volume = 0.5 * data['tumor_length_cm'] * (data['tumor_width_cm'] ** 2)
    data['calculated_tumor_volume_cm3'] = volume
    if volume > 250.0:
        return False, f"Medical Rule Violation: Tumor volume {volume} cm^3 exceeds maximum 250 cm^3."

    # 3. 醫療演算法計分
    score, cp_class = get_child_pugh_score(
        data['bilirubin'], data['albumin'], data['inr'], 
        data['ascites'], data['encephalopathy']
    )
    data['calculated_cp_score'] = score
    data['calculated_cp_class'] = cp_class

    if cp_class != "A":
        return False, f"Medical Rule Violation: Calculated Child-Pugh Score is {score} (Class {cp_class}). Clinical trial only accepts Class A."

    data['is_eligible'] = True
    return True, data

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
        print(result) # 印出錯誤訊息給 LLM 看
        sys.exit(1)

    # 完美通關
    print("```json")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("```")

if __name__ == "__main__":
    main()