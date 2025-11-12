import ast
import re
import requests
import yaml

SOURCE_FILE = 'dbworker/update_master.py'
README_FILE = 'README.md'
TABLE_HEADER = "| Manufacturer | Code |\n|--------------|------|\n"
MATERIAL_TABLE_HEADER = "| Key | Name | Full name |\n|-----|------|-----------|\n"

def extract_mapping():
    with open(SOURCE_FILE, 'r') as f:
        content = f.read()
    match = re.search(r'manufacturer_ids\s*=\s*({.*?})', content, re.DOTALL)
    if not match:
        raise ValueError("manufacturer_ids dictionary not found")
    return ast.literal_eval(match.group(1))

def fetch_openprinttag_materials():
    """Fetch material codes from OpenPrintTag YAML"""
    url = "https://raw.githubusercontent.com/prusa3d/OpenPrintTag/main/data/material_type_enum.yaml"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return yaml.safe_load(response.text)
    except Exception as e:
        print(f"⚠️ Failed to fetch OpenPrintTag materials: {e}")
        return None

def update_readme(mapping):
    with open(README_FILE, 'r') as f:
        readme = f.read()

    # Update manufacturer table
    manufacturer_table = TABLE_HEADER + '\n'.join(
        f"| {manufacturer} | {code} |" for manufacturer, code in sorted(mapping.items())
    )

    # Update material table from OpenPrintTag
    opentag_materials = fetch_openprinttag_materials()
    if opentag_materials:
        material_rows = []
        for key, value in sorted(opentag_materials.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            name = value.get('abbreviation', '')
            full_name = value.get('name', '')
            material_rows.append(f"| {key} | `{name}` | {full_name} |")
        
        material_table = MATERIAL_TABLE_HEADER + "\n".join(material_rows)
        
        # Update both tables
        updated = re.sub(
            r"(<!-- manufacturer-table-start -->)(.*?)(<!-- manufacturer-table-end -->)",
            rf"\\1\n{manufacturer_table}\n\\3",
            readme,
            flags=re.DOTALL
        )
        
        updated = re.sub(
            r"(## Filament Type Mapping.*?)(\n---)",
            f"\\1\n\n{material_table}\\2",
            updated,
            flags=re.DOTALL
        )
    else:
        # Fallback to just updating manufacturer table
        updated = re.sub(
            r"(<!-- manufacturer-table-start -->)(.*?)(<!-- manufacturer-table-end -->)",
            rf"\\1\n{manufacturer_table}\n\\3",
            readme,
            flags=re.DOTALL
        )

    with open(README_FILE, 'w') as f:
        f.write(updated)

if __name__ == "__main__":
    mapping = extract_mapping()
    update_readme(mapping)
