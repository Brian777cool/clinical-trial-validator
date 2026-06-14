import sys
import json
import os
import csv

def get_child_pugh_score(bili, alb, inr, ascites, encephalopathy):
    score = 0
    # 總膽紅素 (Bilirubin)
    if bili < 2.0: score += 1
    elif 2.0 <= bili <= 3.0: score += 2
    else: score += 3
    # 白蛋白 (Albumin)
    if alb > 3.5: score += 1
    elif 2.8 <= alb <= 3.5: score += 2
    else: score += 3
    # 凝血酶原時間 (INR)
    if inr < 1.7: score += 1
    elif 1.7 <= inr <= 2.2: score += 2
    else: score += 3
    # 腹水 (Ascites)
    if ascites == "none": score += 1
    elif ascites == "mild": score += 2
    else: score += 3
    # 肝性腦病變 (Encephalopathy)
    if encephalopathy == "none": score += 1
    elif encephalopathy in ["grade 1", "grade 2"]: score += 2
    else: score += 3
    return score

def main():
    if len(sys.argv) < 2:
        print("Error: Missing input JSON file path.")
        sys.exit(1)

    file_path = sys.argv[1]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Invalid JSON format. Details: {str(e)}")
        sys.exit(1)

    # 1. 確保 LLM 抽取了所有必須的原始數據
    required_keys = ["task_id", "patient_id", "tumor_length_cm", "tumor_width_cm", "platelet_count"]
    cp_keys = ["bilirubin", "albumin", "inr", "ascites", "encephalopathy"]
    
    for k in required_keys + cp_keys:
        if k not in data:
            print(f"Error: Missing required metric '{k}' in JSON.")
            sys.exit(1)

    # ==========================================
    # 🔥 功能一：Mock EMR 防幻覺驗證 (Data Grounding)
    # ==========================================
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "mock_emr_db.csv")
    
    emr_platelets = None
    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row["patient_id"] == data["patient_id"]:
                emr_platelets = int(row["platelet_count"])
                break
                
    if emr_platelets is None:
        print(f"Error: Patient ID {data['patient_id']} not found in EMR database.")
        sys.exit(1)
        
    if data["platelet_count"] != emr_platelets:
        print(f"Logical Contradiction: Hallucination detected! The extracted platelet count ({data['platelet_count']}) does NOT match the hospital EMR database ({emr_platelets}).")
        sys.exit(1)

    # ==========================================
    # 🔥 功能二：腫瘤體積幾何學驗證 (Mathematical Verification)
    # ==========================================
    L = float(data["tumor_length_cm"])
    W = float(data["tumor_width_cm"])
    
    # 針對奈米載體滲透率估算的體積公式 V = 0.5 * L * W * W
    calculated_volume = 0.5 * L * W * W
    data["calculated_tumor_volume_cm3"] = round(calculated_volume, 2)

    if calculated_volume > 250.0:
        print(f"Medical Rule Violation: Calculated tumor volume is {calculated_volume:.2f} cm^3. Exceeds maximum threshold for PLGA nanocarrier penetration (250 cm^3).")
        sys.exit(1)

    # ==========================================
    # 🔥 功能三：Child-Pugh 演算法計分 (Algorithmic Scoring)
    # ==========================================
    cp_score = get_child_pugh_score(
        data["bilirubin"], data["albumin"], data["inr"], 
        data["ascites"].lower(), data["encephalopathy"].lower()
    )
    
    cp_class = "A" if cp_score <= 6 else ("B" if cp_score <= 9 else "C")
    data["calculated_cp_score"] = cp_score
    data["calculated_cp_class"] = cp_class

    if cp_class != "A":
        print(f"Medical Rule Violation: Calculated Child-Pugh Score is {cp_score} (Class {cp_class}). Clinical trial only accepts Class A.")
        sys.exit(1)

    # 驗證全數通過！將計算結果整合進 JSON 並要求 LLM 輸出
    data["is_eligible"] = True
    print("Validation Passed! All medical and structural logics are solid.")
    print("Please output the following final JSON payload in a Markdown code block:")
    print("```json")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("```")

if __name__ == "__main__":
    main()