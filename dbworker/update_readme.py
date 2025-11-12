#!/usr/bin/env python3
import requests
import yaml
import re
from pathlib import Path

# Paths and constants
README_PATH = Path(__file__).parent.parent / "README.md"
OPENPRINTTAG_YAML_URL = "https://raw.githubusercontent.com/prusa3d/OpenPrintTag/main/data/material_type_enum.yaml"

def fetch_material_codes():
    """
    Fetch material codes from OpenPrintTag YAML and return {key: abbreviation} dict.
    YAML structure:
    - key: 0
      abbreviation: PLA
      name: Polylactic Acid
      category: FFF
      description: ...
    """
    response = requests.get(OPENPRINTTAG_YAML_URL)
    response.raise_for_status()
    data = yaml.safe_load(response.text)

    # Extract key and abbreviation
    material_codes = {int(item["key"]): item["abbreviation"] for item in data}
    return material_codes

def generate_material_table(material_codes):
    """
    Generate a Markdown table for README.
    Columns: ID | Abbreviation
    """
    lines = ["| Key | Abbreviation |", "|-----|--------------|"]
    for key, abbrev in sorted(material_codes.items()):
        lines.append(f"| {key} | {abbrev} |")
    return "\n".join(lines)

def update_readme(material_table):
    """
    Replace the MATERIAL CODES section in README.md between markers:
    <!-- MATERIAL_CODES_START --> ... <!-- MATERIAL_CODES_END -->
    If markers don't exist, append at the end.
    """
    readme_text = README_PATH.read_text(encoding="utf-8")

    start_marker = "<!-- MATERIAL_CODES_START -->"
    end_marker = "<!-- MATERIAL_CODES_END -->"
    pattern = re.compile(f"{start_marker}.*?{end_marker}", re.DOTALL)

    new_section = f"{start_marker}\n{material_table}\n{end_marker}"

    if pattern.search(readme_text):
        updated_text = pattern.sub(new_section, readme_text)
    else:
        updated_text = readme_text + "\n\n" + new_section

    README_PATH.write_text(updated_text, encoding="utf-8")
    print("README.md updated successfully.")

if __name__ == "__main__":
    try:
        codes = fetch_material_codes()
        table = generate_material_table(codes)
        update_readme(table)
    except Exception as e:
        print(f"Error updating README: {e}")
        exit(1)
