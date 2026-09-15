import sys
import json
import os
import csv
import math

def calculate_tumor_volume(length, width, height):
    # 採用主流臨床三徑橢球公式 (pi/6 * L * W * H)
    volume = (math.pi / 6) * length * width * height
    return round(volume, 2)

def check_bia_safety(ecw_ratio, phase_angle, measured_weight_kg=70.0):
    BASE_DOSE = 5.0 
    if phase_angle < 4.0:
        return False, f"Medical Data Violation: 偵測到嚴重肌少症 (Phase Angle: {phase_angle})。細胞膜狀態極差，無法承受標靶奈米載體代謝負荷。"
    if ecw_ratio > 0.39:
        excess_water = ecw_ratio - 0.39
        dry_weight = measured_weight_kg * (1 - excess_water)
    else:
        dry_weight = measured_weight_kg
    safe_dose = dry_weight * BASE_DOSE
    return True, round(safe_dose, 2)
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
def check_bia_safety(ecw_ratio, phase_angle, measured_weight_kg=70.0):
    # 預設 PLGA 奈米藥物標準劑量
    BASE_DOSE = 5.0 
    
    # 1. 肌少症與細胞健康度絕對防線 (Phase Angle < 4.0 直接剔除)
    if phase_angle < 4.0:
        return False, f"Medical Data Violation: 偵測到嚴重肌少症 (Phase Angle: {phase_angle})。無法承受標靶奈米載體代謝負荷。"
        
    # 2. 腹水重量校正 (Dry Weight)
    if ecw_ratio > 0.39:
        excess_water = ecw_ratio - 0.39
        dry_weight = measured_weight_kg * (1 - excess_water)
    else:
        dry_weight = measured_weight_kg
        
    # 3. 輸出安全劑量
    safe_dose = dry_weight * BASE_DOSE
    return True, round(safe_dose, 2)
def validate_trial(data):
    try:
        platelet_count = int(data['platelet_count'])
        bilirubin = float(data['bilirubin'])
        albumin = float(data['albumin'])
        inr = float(data['inr'])
        tumor_length = float(data['tumor_length_cm'])
        tumor_width = float(data['tumor_width_cm'])
        tumor_height = float(data['tumor_height_cm'])
        if tumor_length > 20 or tumor_width > 20 or tumor_height > 20:
            return False, "Data Error: 腫瘤三徑尺寸超過人體解剖學極限（>20cm），請確認輸入數值。"

    except (ValueError, TypeError):
        return False, "Data Type Violation: 格式錯誤"
    except KeyError as e:
        return False, f"Missing required field: {e}"

    required = ["patient_id", "tumor_length_cm", "tumor_width_cm", "platelet_count",
                "bilirubin", "albumin", "inr", "ascites", "encephalopathy"]
    for req in required:
        if req not in data:
            return False, f"Missing required field: {req}"

    # 修改為直接抓取當前工作目錄
    db_path = os.path.abspath("mock_emr_db.csv")

    # 若有建立實體 CSV，則進行比對；若無，則針對 Scenario 設定防護
    if os.path.exists(db_path):
        with open(db_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            found_patient = False
            tolerance = 0.1  # 誤差容許值，避免浮點數精度問題誤判

            for row in reader:
                if row['patient_id'] == data['patient_id']:
                    found_patient = True

                    if int(row['platelet_count']) != int(data['platelet_count']):
                        return False, f"Hallucination detected! Real platelet count for {data['patient_id']} does not match EMR."

                    if abs(float(row['Bilirubin']) - float(data['bilirubin'])) > tolerance:
                        return False, f"Hallucination detected! Real bilirubin for {data['patient_id']} does not match EMR."
                    if abs(float(row['Albumin']) - float(data['albumin'])) > tolerance:
                        return False, f"Hallucination detected! Real albumin for {data['patient_id']} does not match EMR."
                    if abs(float(row['INR']) - float(data['inr'])) > tolerance:
                        return False, f"Hallucination detected! Real INR for {data['patient_id']} does not match EMR."
                    if row['Ascites'] != data['ascites']:
                        return False, f"Hallucination detected! Real ascites status for {data['patient_id']} does not match EMR."
                    if row['Encephalopathy'] != data['encephalopathy']:
                        return False, f"Hallucination detected! Real encephalopathy status for {data['patient_id']} does not match EMR."
                    if abs(float(row['Tumor_Length_cm']) - float(data['tumor_length_cm'])) > tolerance:
                        return False, f"Hallucination detected! Real tumor length for {data['patient_id']} does not match EMR."
                    if abs(float(row['Tumor_Width_cm']) - float(data['tumor_width_cm'])) > tolerance:
                        return False, f"Hallucination detected! Real tumor width for {data['patient_id']} does not match EMR."
                    if abs(float(row['Tumor_Height_cm']) - float(data['tumor_height_cm'])) > tolerance:
                        return False, f"Hallucination detected! Real tumor height for {data['patient_id']} does not match EMR."

                    if abs(float(row['ECW_Ratio']) - float(data['ecw_ratio'])) > tolerance:
                        return False, f"Hallucination detected! Real ECW ratio for {data['patient_id']} does not match EMR."
                    if abs(float(row['Phase_Angle']) - float(data['phase_angle'])) > tolerance:
                        return False, f"Hallucination detected! Real phase angle for {data['patient_id']} does not match EMR."

                    # BIA 防護網邏輯：使用 EMR 記錄的真實值進行安全計算
                    ecw_ratio = float(row['ECW_Ratio'])
                    phase_angle = float(row['Phase_Angle'])

                    bia_passed, bia_result = check_bia_safety(ecw_ratio, phase_angle)

                    if not bia_passed:
                        return False, bia_result

                    data['calibrated_safe_dose_mg'] = bia_result

            if not found_patient:
                return False, f"Data Error: 找不到病患 {data['patient_id']} 的 EMR 紀錄。"
    else:
        # Fallback 防護 (針對我們在 OPEN_TRACK.md 設定的情境)
        if data['patient_id'] == 'P-1002' and data.get('platelet_count') == 100000:
            return False, "Hallucination detected! Real platelet count for P-1002 is 42000."

    # 2. 幾何學體積驗算 (升級為臨床標準三徑橢球公式)
    length = float(data['tumor_length_cm'])
    width = float(data['tumor_width_cm'])
    height = float(data['tumor_height_cm'])

    volume = (math.pi / 6) * length * width * height
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
 # 自動將帶有計算結果的完整資料儲存為 Gold JSON
    output_filename = "output_gold.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✓ 已成功將運算結果匯出至 {output_filename}")
if __name__ == "__main__":
    main()
