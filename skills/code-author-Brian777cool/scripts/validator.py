import sys
import json
import ast

def validate_code(code_str):
    # 1. 語法檢查
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"Syntax Error detected in your Python code: {e}"

    # 2. 資安防護網 (阻擋危險模組)
    forbidden_modules = {'os', 'sys', 'subprocess', 'shlex'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_modules:
                    return False, f"Security Violation: Importing '{alias.name}' is strictly forbidden."
        elif isinstance(node, ast.ImportFrom):
            if node.module in forbidden_modules:
                return False, f"Security Violation: Importing from '{node.module}' is strictly forbidden."
                
    return True, "Passed"

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

    if "generated_code" not in data:
        print("Error: Missing 'generated_code' field.")
        sys.exit(1)

    is_valid, msg = validate_code(data["generated_code"])
    if not is_valid:
        print(msg)
        sys.exit(1)

    data["syntax_check"] = msg
    print("```json")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("```")

if __name__ == "__main__":
    main()