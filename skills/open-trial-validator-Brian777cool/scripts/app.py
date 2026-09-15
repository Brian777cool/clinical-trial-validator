import pandas as pd
import streamlit as st
import json
import csv
import os
from validator import validate_trial

st.set_page_config(page_title="臨床試驗智慧驗證系統", page_icon="🏥", layout="centered")

st.title("🏥 臨床試驗智慧驗證與安全評估平台")
st.markdown("請輸入病患的 EMR 數據、BIA 身體組成與腫瘤三徑尺寸，系統將自動進行多維度安全檢核。")

def get_patient_list():
    db_path = os.path.abspath("mock_emr_db.csv")
    if not os.path.exists(db_path):
        return ["P-1001", "P-1002", "P-1003"]  # 找不到檔案時的預設值
    with open(db_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [row['patient_id'] for row in reader]

with st.form("clinical_form"):
    col1, col2 = st.columns(2)

    with col1:
        patient_id = st.selectbox("病患 ID (Patient ID)", get_patient_list())
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

    is_valid, result = validate_trial(input_data)

    if not is_valid:
        st.error(f"❌ 驗證未通過：{result}")
    else:
        st.success("✅ 數據已成功通過驗證引擎！")
        st.markdown("### 📊 驗證與計算結果")
        st.json(result)

        json_str = json.dumps(result, indent=4, ensure_ascii=False)
        st.download_button(
            label="📥 下載 Gold JSON 驗證結果",
            data=json_str,
            file_name="output_gold.json",
            mime="application/json"
        )
        st.markdown("---")
st.markdown("## 📁 批次驗證（上傳 CSV）")
st.markdown("上傳包含多筆病患申請資料的 CSV，系統將逐筆比對 EMR 並產出驗證結果彙整表。")

uploaded_file = st.file_uploader("上傳批次驗證檔案（CSV）", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    results = []
    for _, row in df.iterrows():
        input_data = row.to_dict()
        try:
            input_data["platelet_count"] = int(input_data["platelet_count"])
            input_data["tumor_length_cm"] = float(input_data["tumor_length_cm"])
            input_data["tumor_width_cm"] = float(input_data["tumor_width_cm"])
            input_data["tumor_height_cm"] = float(input_data["tumor_height_cm"])
            input_data["bilirubin"] = float(input_data["bilirubin"])
            input_data["albumin"] = float(input_data["albumin"])
            input_data["inr"] = float(input_data["inr"])
            input_data["ecw_ratio"] = float(input_data["ecw_ratio"])
            input_data["phase_angle"] = float(input_data["phase_angle"])
        except (ValueError, KeyError) as e:
            results.append({
                "patient_id": input_data.get("patient_id", "未知"),
                "驗證結果": "❌ 格式錯誤",
                "原因": str(e)
            })
            continue

        is_valid, result = validate_trial(input_data)

        if is_valid:
            results.append({
                "patient_id": input_data["patient_id"],
                "驗證結果": "✅ 通過",
                "原因": "-"
            })
        else:
            results.append({
                "patient_id": input_data["patient_id"],
                "驗證結果": "❌ 未通過",
                "原因": result
            })

    result_df = pd.DataFrame(results)
    st.markdown("### 📊 批次驗證結果")
    st.dataframe(result_df, use_container_width=True)

    csv_output = result_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載批次驗證結果 (CSV)",
        data=csv_output,
        file_name="batch_validation_results.csv",
        mime="text/csv"
    )