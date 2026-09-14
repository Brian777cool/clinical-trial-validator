import streamlit as st
import json
import os

# 直接從同一個資料夾匯入驗證核心
from validator import validate_trial, calculate_tumor_volume, get_child_pugh_score
from validator import validate_trial, calculate_tumor_volume, get_child_pugh_score

st.set_page_config(page_title="臨床試驗智慧驗證系統", page_icon="🏥", layout="centered")

st.title("🏥 臨床試驗智慧驗證與安全評估平台")
st.markdown("請輸入病患的 EMR 數據、BIA 身體組成與腫瘤三徑尺寸，系統將自動進行多維度安全檢核。")

with st.form("clinical_validation_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        patient_id = st.selectbox("病患 ID (Patient ID)", ["P-1001", "P-1002", "P-1003"])
        platelet_count = st.number_input("血小板計數 (Platelet)", value=85000, step=1000)
        ecw_ratio = st.number_input("細胞外液比率 (ECW Ratio)", value=0.38, step=0.01)
        phase_angle = st.number_input("相位角 (Phase Angle)", value=6.5, step=0.1)
        bilirubin = st.number_input("膽紅素 (Bilirubin)", value=1.0, step=0.1)
        albumin = st.number_input("白蛋白 (Albumin)", value=4.0, step=0.1)
        
    with col2:
        inr = st.number_input("凝血酶原時間比 (INR)", value=1.1, step=0.1)
        ascites = st.selectbox("腹水狀況 (Ascites)", ["none", "mild", "severe"])
        encephalopathy = st.selectbox("肝腦病變 (Encephalopathy)", ["none", "grade 1", "grade 2"])
        tumor_length = st.number_input("腫瘤長度 (Length cm)", value=4.0, step=0.1)
        tumor_width = st.number_input("腫瘤寬度 (Width cm)", value=3.0, step=0.1)
        tumor_height = st.number_input("腫瘤高度 (Height cm)", value=2.0, step=0.1)

    submitted = st.form_submit_button("執行臨床試驗驗證")

if submitted:
    input_data = {
        "patient_id": patient_id,
        "platelet_count": int(platelet_count),
        "ecw_ratio": float(ecw_ratio),
        "phase_angle": float(phase_angle),
        "tumor_length_cm": float(tumor_length),
        "tumor_width_cm": float(tumor_width),
        "tumor_height_cm": float(tumor_height),
        "bilirubin": float(bilirubin),
        "albumin": float(albumin),
        "inr": float(inr),
        "ascites": ascites,
        "encephalopathy": encephalopathy
    }
    
    # 實際呼叫 validator.py 的檢核引擎
    is_valid, message = validate_trial(input_data)
    
    if not is_valid:
        st.error(f"❌ **臨床試驗驗證未通過（安全攔截）**\n\n原因：{message}")
    else:
        st.success("✅ **驗證完全通過！病患符合臨床試驗收案標準。**")
        
        # 計算附加數值呈現
        input_data["calculated_tumor_volume_cm3"] = calculate_tumor_volume(
            tumor_length, tumor_width, tumor_height
        )
        score, c_class = get_child_pugh_score(bilirubin, albumin, inr, ascites, encephalopathy)
        input_data["calculated_cp_score"] = score
        input_data["calculated_cp_class"] = c_class
        input_data["is_eligible"] = True
        
        st.markdown("### 📊 產出之 Gold JSON 結果")
        st.json(input_data)
        
        json_str = json.dumps(input_data, indent=4, ensure_ascii=False)
        st.download_button(
            label="📥 下載 Gold JSON 驗證結果",
            data=json_str,
            file_name="output_gold.json",
            mime="application/json"
        )