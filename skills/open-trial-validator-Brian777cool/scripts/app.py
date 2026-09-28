import csv
import json
import os

import pandas as pd
import streamlit as st

from validator import (EMR_DB_PATH, ALLOWED_ASCITES, ALLOWED_ENCEPHALOPATHY,
                       validate_trial)

st.set_page_config(page_title="臨床試驗收案驗證系統", page_icon="🏥", layout="centered")

st.title("🏥 臨床試驗收案驗證系統（規則式）")
st.markdown("請輸入研究端填報的收案資料，系統會先與 EMR 原始資料核對，一致後再依規則判斷是否符合收案條件。")
st.caption("⚠️ 本系統所有病患資料皆為模擬資料；BIA 與腫瘤尺寸的閾值為自訂的示範規則，非臨床用途。")


def get_patient_list():
    if not os.path.exists(EMR_DB_PATH):
        st.error("找不到 EMR 資料庫 mock_emr_db.csv。")
        return []
    with open(EMR_DB_PATH, mode='r', encoding='utf-8-sig') as f:
        return [row['patient_id'] for row in csv.DictReader(f)]


with st.form("clinical_form"):
    col1, col2 = st.columns(2)

    with col1:
        patient_id = st.selectbox("病患 ID (Patient ID)", get_patient_list())
        platelet_count = st.number_input("血小板 Platelet (/µL)", value=85000, step=1000)
        bilirubin = st.number_input("總膽紅素 Bilirubin (mg/dL)", value=1.0, step=0.1)
        albumin = st.number_input("白蛋白 Albumin (g/dL)", value=4.0, step=0.1)
        inr = st.number_input("PT-INR", value=1.1, step=0.01)
        ascites = st.selectbox("腹水 (Ascites)", ALLOWED_ASCITES)
        encephalopathy = st.selectbox("肝性腦病變 (West Haven)", ALLOWED_ENCEPHALOPATHY)

    with col2:
        ecw_ratio = st.number_input("ECW/TBW 比值", value=0.38, step=0.01)
        phase_angle = st.number_input("相位角 Phase Angle (°)", value=6.5, step=0.1)
        tumor_length = st.number_input("腫瘤長徑 (cm)", value=4.0, step=0.1)
        tumor_width = st.number_input("腫瘤寬徑 (cm)", value=3.0, step=0.1)
        tumor_height = st.number_input("腫瘤頭尾徑 (cm)", value=2.0, step=0.1)

    submitted = st.form_submit_button("執行收案驗證")

if submitted:
    input_data = {
        "patient_id": patient_id,
        "platelet_count": int(platelet_count),
        "bilirubin": float(bilirubin),
        "albumin": float(albumin),
        "inr": float(inr),
        "ecw_ratio": float(ecw_ratio),
        "phase_angle": float(phase_angle),
        "tumor_length_cm": float(tumor_length),
        "tumor_width_cm": float(tumor_width),
        "tumor_height_cm": float(tumor_height),
        "ascites": ascites,
        "encephalopathy": encephalopathy,
    }

    is_valid, result = validate_trial(input_data)

    if not is_valid:
        st.error(f"❌ 驗證未通過：{result}")
    else:
        st.success("✅ 與 EMR 原始資料一致，且符合本系統檢核的收案條件（條件不完整，見 README）。")
        st.markdown("### 📊 驗證與計算結果")
        st.json(result)
        st.download_button(
            label="📥 下載驗證結果 (JSON)",
            data=json.dumps(result, indent=4, ensure_ascii=False),
            file_name="validation_result.json",
            mime="application/json",
        )

st.markdown("---")
st.markdown("## 📁 批次驗證（上傳 CSV）")
st.markdown("上傳包含多筆填報資料的 CSV，系統將逐筆與 EMR 核對並產出驗證結果彙整表。")

uploaded_file = st.file_uploader("上傳批次驗證檔案（CSV）", type=["csv"])

if uploaded_file is not None:
    # 全部以字串讀入、空白保留為空字串，交給 validate_trial 統一檢查格式與缺漏
    df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)

    results = []
    for _, row in df.iterrows():
        record = row.to_dict()
        is_valid, result = validate_trial(record)
        results.append({
            "patient_id": record.get("patient_id", "未知"),
            "驗證結果": "✅ 通過" if is_valid else "❌ 未通過",
            "原因": "-" if is_valid else result,
        })

    result_df = pd.DataFrame(results)
    st.markdown("### 📊 批次驗證結果")
    st.dataframe(result_df, use_container_width=True)

    st.download_button(
        label="📥 下載批次驗證結果 (CSV)",
        data=result_df.to_csv(index=False).encode('utf-8-sig'),
        file_name="batch_validation_results.csv",
        mime="text/csv",
    )