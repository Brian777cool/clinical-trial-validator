import csv
import json
import os

import pytest

import validator
from validator import validate_trial, get_child_pugh_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _record(pid="P-1001"):
    """讀取 EMR 中該病患的紀錄，轉成與 EMR 完全一致的填報資料。"""
    with open(os.path.join(SCRIPT_DIR, "mock_emr_db.csv"), encoding="utf-8") as f:
        row = next(r for r in csv.DictReader(f) if r["patient_id"] == pid)
    return {
        "patient_id": pid,
        "platelet_count": int(row["platelet_count"]),
        "bilirubin": float(row["Bilirubin"]),
        "albumin": float(row["Albumin"]),
        "inr": float(row["INR"]),
        "ecw_ratio": float(row["ECW_Ratio"]),
        "phase_angle": float(row["Phase_Angle"]),
        "tumor_length_cm": float(row["Tumor_Length_cm"]),
        "tumor_width_cm": float(row["Tumor_Width_cm"]),
        "tumor_height_cm": float(row["Tumor_Height_cm"]),
        "ascites": row["Ascites"],
        "encephalopathy": row["Encephalopathy"],
    }


# ---------- 正常通過 ----------

def test_matching_record_is_eligible():
    is_valid, result = validate_trial(_record("P-1001"))
    assert is_valid is True
    assert result["calculated_cp_class"] == "A"
    assert result["calculated_tumor_volume_cm3"] == 12.57


def test_input_dict_is_not_modified():
    data = _record("P-1001")
    before = dict(data)
    validate_trial(data)
    assert data == before


# ---------- 輸入格式 ----------

def test_missing_field_is_rejected():
    data = _record()
    del data["phase_angle"]
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "Missing required field" in result


def test_blank_value_is_treated_as_missing():
    data = _record()
    data["bilirubin"] = "  "
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "Missing required field" in result


@pytest.mark.parametrize("bad_value", ["NotANumber", float("nan"), float("inf"), -1.0, 0])
def test_invalid_numbers_are_rejected(bad_value):
    data = _record()
    data["albumin"] = bad_value
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "Data Type Violation" in result


def test_non_integer_platelet_is_rejected():
    data = _record()
    data["platelet_count"] = 85000.5
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "platelet_count" in result


def test_unknown_ascites_value_is_rejected():
    data = _record()
    data["ascites"] = "absent"
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "ascites" in result


def test_non_dict_input_is_rejected():
    is_valid, result = validate_trial(None)
    assert is_valid is False


def test_tumor_axis_over_limit_needs_manual_check():
    data = _record()
    data["tumor_length_cm"] = 22.0
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "人工確認" in result


# ---------- 原始資料核對 ----------

def test_unknown_patient_is_rejected():
    data = _record()
    data["patient_id"] = "P-9999"
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "找不到病患" in result


def test_missing_emr_database_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(validator, "EMR_DB_PATH", str(tmp_path / "missing.csv"))
    is_valid, result = validate_trial(_record())
    assert is_valid is False
    assert "找不到 EMR 資料庫" in result


def test_all_mismatched_fields_are_reported():
    data = _record("P-1001")
    data["bilirubin"] = 1.5
    data["ascites"] = "mild"
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "Source data mismatch" in result
    assert "bilirubin" in result and "ascites" in result


def test_encephalopathy_mismatch_is_detected():
    data = _record("P-1001")
    data["encephalopathy"] = "grade 1"
    is_valid, result = validate_trial(data)
    assert is_valid is False
    assert "encephalopathy" in result


def test_small_difference_within_reporting_precision_passes():
    data = _record("P-1001")
    data["inr"] = 1.104  # EMR 為 1.1，差 0.004，在 INR 容許誤差 0.005 內
    is_valid, _ = validate_trial(data)
    assert is_valid is True


# ---------- 收案條件 ----------

def test_all_failed_criteria_are_reported():
    # P-1002：Child-Pugh C 且相位角低於示範閾值，兩個原因都要列出
    is_valid, result = validate_trial(_record("P-1002"))
    assert is_valid is False
    assert "Class C" in result and "相位角" in result


@pytest.mark.parametrize("inr, expected_points", [(1.69, 1), (1.7, 2), (2.3, 2), (2.31, 3)])
def test_child_pugh_inr_cutoffs(inr, expected_points):
    # 其餘四項皆給 1 分，總分 - 4 即為 INR 的得分
    score, _ = get_child_pugh_score(1.0, 4.0, inr, "none", "none")
    assert score - 4 == expected_points


def test_child_pugh_moderate_ascites_scores_three():
    score, _ = get_child_pugh_score(1.0, 4.0, 1.0, "moderate", "none")
    assert score == 7


# ---------- 範例檔案 ----------

def test_example_json_files():
    with open(os.path.join(SCRIPT_DIR, "test_pass.json"), encoding="utf-8") as f:
        assert validate_trial(json.load(f))[0] is True
    with open(os.path.join(SCRIPT_DIR, "test_bia.json"), encoding="utf-8") as f:
        is_valid, result = validate_trial(json.load(f))
        assert is_valid is False and "相位角" in result


# 批次測試資料的預期結果（與 report.md 表格一致）
EXPECTED_BATCH = {
    "P-1001": (True, []),
    "P-1002": (False, ["Class C", "相位角"]),
    "P-1003": (False, ["Class B"]),
    "P-2001": (True, []),
    "P-2002": (False, ["Source data mismatch", "platelet_count"]),
    "P-2003": (False, ["相位角"]),
    "P-2004": (False, ["Class C", "相位角"]),
    "P-2005": (False, ["腫瘤體積"]),
    "P-2006": (False, ["Source data mismatch", "tumor_length_cm"]),
}


def test_batch_input_each_patient_independent():
    with open(os.path.join(SCRIPT_DIR, "batch_input_test.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(EXPECTED_BATCH)
    for row in rows:
        is_valid, result = validate_trial(dict(row))
        expected_valid, keywords = EXPECTED_BATCH[row["patient_id"]]
        assert is_valid is expected_valid, (row["patient_id"], result)
        for keyword in keywords:
            assert keyword in result, (row["patient_id"], result)