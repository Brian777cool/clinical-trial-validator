import sys
import json

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

    # 1. 檢查必填欄位是否齊全
    required_keys = ["task_id", "has_bug", "bug_description"]
    for key in required_keys:
        if key not in data:
            print(f"Error: Missing required field '{key}'.")
            sys.exit(1)

    # 2. 確定性防線：嚴格型別檢查
    if not isinstance(data["has_bug"], bool):
        print("Error: 'has_bug' must be a strict boolean (true or false).")
        sys.exit(1)

    if not isinstance(data["bug_description"], str):
        print("Error: 'bug_description' must be a string.")
        sys.exit(1)
        
    # 如果認為有 bug，說明不能太短
    if data["has_bug"] and len(data["bug_description"].strip()) < 10:
        print("Error: If a bug is found, 'bug_description' must be detailed (at least 10 characters).")
        sys.exit(1)

    # 3. 完美通過，產出期末規格 JSON
    print("```json")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("```")

if __name__ == "__main__":
    main()