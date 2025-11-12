#!/usr/bin/env python3
import requests
import yaml
import re
from pathlib import Path

README_PATH = Path(__file__).parent / "README.md"
OPENPRINTTAG_YAML_URL = "https://raw.githubusercontent.com/prusa3d/OpenPrintTag/main/data/material_type_enum.yaml"

def fetch_material_codes():
    """Fetch material codes from OpenPrintTag YAML and return {id: abbreviation} dict."""
    response = requests.get(OPENPRINTTAG_YAML_URL)
    response.raise_for_status()
    data = yaml.safe_load(response.text)
    return {int(k): v.get("abbreviation") for k, v in data.items()}

def generate_material_table(material_codes):
    """Generate a Markdown table for README."""
    lines = ["| ID | Abbreviation |", "|----|--------------|"]
    for mid, abbrev in sorted(material_codes.items()):
        lines.append(f"| {mid} | {abbrev} |")
    return "\n".join(lines)

def update_readme(material_table):
    """Replace the MATERIAL CODES section in README.md."""
    readme_text = README_PATH.read_text(encoding="utf-8")

    # Look for markers in README
    start_marker = "<!-- MATERIAL_CODES_START -->"
    end_marker = "<!-- MATERIAL_CODES_END -->"

    pattern = re.compile(f"{start_marker}.*?{end_marker}", re.DOTALL)
    new_section = f"{start_marker}\n{material_table}\n{end_marker}"

    if pattern.search(readme_text):
        updated_text = pattern.sub(new_section, readme_text)
    else:
        # If markers don't exist, append at the end
        updated_text = readme_text + "\n\n" + new_section

    README_PATH.write_text(updated_text, encoding="utf-8")
    print("README.md updated successfully.")

if __name__ == "__main__":
    codes = fetch_material_codes()
    table = generate_material_table(codes)
