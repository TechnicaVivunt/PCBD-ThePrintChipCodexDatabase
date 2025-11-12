# Print Chip Codex Database (PCDB)

The **Print Chip Codex Database (PCDB)** is a universal filament lookup system designed as a companion to the existing [Print Chip Codex (PCX)](https://www.printables.com/refresh?redirectUrl=%2F%40JamesThePrint_699540) maintained by James@ThePrintCodex.  

This project extends the functionality of the original PCX database by supporting multiple filament types and manufacturers while maintaining compatibility with existing PCX IDs for those who have purchased/printed their own filaments.

---

## Background

The original **Print Chip Codex (PCX)** is a great system, but lacks a lot of filament brands as they expand. The PCDB expands that system to include:

- More Manufacturers
- Strives to stay up to date with automated updating via various methods
- Suffix indicating filament type for additional reference.

**Key points:**

- Existing PCX numbers remain unchanged.  
- New entries include a `-1` suffix to differentiate the different filament types.  
- The first three digits represent the **manufacturer code**.
- The second three digits represent the number entry. This will restart for each filament type.  
- The last digit represents the **filament type**.  

---

## Manufacturer Mapping

<!-- manufacturer-table-start -->
| Manufacturer | Code |
|--------------|------|
| AmazonBasics | 7 |
| Bambu Lab | 3 |
| ERYONE | 10 |
| HATCHBOX | 11 |
| Overture | 5 |
| Polymaker | 2 |
| Prusa | 4 |
| SUNLU | 9 |
| Unknown | 999 |
| VOXELPLA | 8 |
| eSUN | 6 |
<!-- manufacturer-table-end -->

---

## Filament Type Mapping (Updated to Match OpenPrintTag's Type Codes)


<!-- MATERIAL_CODES_START -->
| Key | Abbreviation |
|-----|--------------|
| 0 | PLA |
| 1 | PETG |
| 2 | TPU |
| 3 | ABS |
| 4 | ASA |
| 5 | PC |
| 6 | PCTG |
| 7 | PP |
| 8 | PA6 |
| 9 | PA11 |
| 10 | PA12 |
| 11 | PA66 |
| 12 | CPE |
| 13 | TPE |
| 14 | HIPS |
| 15 | PHA |
| 16 | PET |
| 17 | PEI |
| 18 | PBT |
| 19 | PVB |
| 20 | PVA |
| 21 | PEKK |
| 22 | PEEK |
| 23 | BVOH |
| 24 | TPC |
| 25 | PPS |
| 26 | PPSU |
| 27 | PVC |
| 28 | PEBA |
| 29 | PVDF |
| 30 | PPA |
| 31 | PCL |
| 32 | PES |
| 33 | PMMA |
| 34 | POM |
| 35 | PPE |
| 36 | PS |
| 37 | PSU |
| 38 | TPI |
| 39 | SBS |
<!-- MATERIAL_CODES_END -->


---

## Database ID Format

The universal filament ID format is structured as: .csv - this is to maintain compatiblity for the Brother P-Touch software. 

**Components explained:**

| Segment                  | Example | Meaning |
|--------------------------|---------|---------|
| `PCDB`                   | PCDB    | Prefix indicating Print Chip Database |
| `<manufacturer_code>`     | 005     | Manufacturer code (Overture in this case) |
| `<PCX_number>`            | 001     | Original PCX number for the filament |
| `<filament_type_number>`  | 4       | Filament type (ASA) |

**Example:**
PCDB-005-001-4

^ This would be the first ASA entry for Overture's filament.

## References

- [The Print Codex](https://theprintcodex.com/)
- [Original Print Chip Codex by James@ThePrintCodex](https://www.printables.com/refresh?redirectUrl=%2F%40JamesThePrint_699540)
- [OpenPrintTag Standards](https://specs.openprinttag.org/#/material_types)  

## Roadmap

Currently - this is mostly being updated manually - I have a few prototyped scripts to manually pull the filament options/colors/variations from different manufacturer websites. The end goal will be to create some workflow/actions to periodically pull the data and have this repository automatically update anytime new filaments are found on the popular manufacturers.

Automated Updates for Filaments for the following manufacturers as of writing:

| Brand      | Status/Notes                                      |
|------------|---------------------------------------------------|
| PolyMaker  | Complete                                          |
| BambuLab   | Complete                                          |
| Prusa      | Complete           |
| VOXELPLA   | Complete                                          |
| HATCHBOX   | Complete                                          |

Future filament manufacturers will be added soon - you can keep track of my progress on manufacturers on the Project board: 
[Project Roadmap](https://github.com/users/TechnicaVivunt/projects/5)

If you don't see a filament brand that you'd like to see - Raise an issue here:
[Filament Manufacter Additions List](https://github.com/TechnicaVivunt/PCBD-ThePrintChipCodexDatabase/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22Manufacturer%20Addition%22)


## Additional Notes

I am open to adding additional manufacturers as well so long as they at least have their own websites (scraping popular ecommerce like amazon can be messy). Shopify based retailers tend to be the easiest to work with based on their structure, custom sites tend to take more effort.
This is mostly a hobby project - so updates may be erradic. I'm also using this as a jumping off point to learning github - so PRs and commits may be a little messy. If I get to the point to where I can consistently pull from a fair few manufacturers and get adequate comparisons in python - I will split off between dev and stable branches to ensure entries aren't incidentally removed/changed.

As this is a redux of sorts of the PCX database - if the PCX db ever gets updated (shows last updated some time in 2024) - then the cross compatibility of this database will get a bit muddy. In the interest of maintaining the current numbers in this DB. The PCDB's entries will NOT be modifed to change any updates made to PCX simply to avoid having to reprint any labels or to comprimise the lookup system. If you've made it this far. Thanks for checking out the project!
