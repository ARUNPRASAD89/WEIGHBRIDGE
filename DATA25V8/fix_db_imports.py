import os
import re

def update_imports_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Replace imports
    new_content = re.sub(
        r'from db_utils import([^#\n]*?)\bget_connection\b([^#\n]*)',
        lambda m: f'from db_utils import{m.group(1)}get_new_connection{m.group(2)}',
        content
    )
    # Replace usage in code
    new_content = re.sub(r'\bget_connection\(', 'get_new_connection(', new_content)
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

def scan_and_update(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                update_imports_in_file(filepath)

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))  # Current directory
    scan_and_update(project_root)
    print("All imports updated!")