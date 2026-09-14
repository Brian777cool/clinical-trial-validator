from validator import validate_trial

def test_bia_sarcopenia_rejection():
    mock_data = {
        "patient_id": "P-1002",
        "platelet_count": 42000,
        "tumor_length_cm": 5.0,
        "tumor_width_cm": 5.0,
        "tumor_height_cm": 4.0,
        "bilirubin": 1.5,
        "albumin": 3.0,
        "inr": 1.2,
        "ascites": "none",
        "encephalopathy": "none"
    }
    is_valid, result = validate_trial(mock_data)
    assert is_valid is False
    assert "肌少症" in result
    print("✓ BIA 測試成功通過！")

def test_type_violation_handling():
    mock_data = {
        "patient_id": "P-1001",
        "platelet_count": "NotANumber",
        "tumor_length_cm": 5.0,
        "tumor_width_cm": 5.0,
        "tumor_height_cm": 4.0,
        "bilirubin": 1.0,
        "albumin": 4.0,
        "inr": 1.1,
        "ascites": "none",
        "encephalopathy": "none"
    }
    is_valid, result = validate_trial(mock_data)
    assert is_valid is False
    assert "Data Type Violation" in result
    print("✓ 型別防護測試成功通過！")

if __name__ == "__main__":
    test_bia_sarcopenia_rejection()
    test_type_violation_handling()
    print("🎉 所有單元測試皆完美通過！")