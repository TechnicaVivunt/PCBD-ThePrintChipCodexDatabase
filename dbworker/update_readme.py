import ast
import re

SOURCE_FILE = 'dbworker/update_master.py'
README_FILE = 'README.md'
TABLE_HEADER = "| Manufacturer | Code |\n|--------------|------|\n"

def extract_mapping():
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    match = re.search(r'manufacturer_ids\s*=\s*({.*?})', content, re.DOTALL)
    if not match:
        raise ValueError("manufacturer_ids dictionary not found")
    return ast.literal_eval(match.group(1))

def update_readme(mapping):
    with open(README_FILE, 'r') as f:
        readme = f.read()

    table = TABLE_HEADER + '\n'.join(
        f"| {manufacturer} | {code} |" for manufacturer, code in sorted(mapping.items())
    )

    updated = re.sub(
        r"(<!-- manufacturer-table-start -->)(.*?)(<!-- manufacturer-table-end -->)",
        rf"\1\n{table}\n\3",
        readme,
        flags=re.DOTALL
    )

    with open(README_FILE, 'w') as f:
        f.write(updated)

if __name__ == "__main__":
    mapping = extract_mapping()
    update_readme(mapping)
