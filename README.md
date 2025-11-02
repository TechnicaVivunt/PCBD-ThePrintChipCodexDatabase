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

| Code | Manufacturer     |
|------|----------------|
| 2    | PolyMaker       |
| 3    | BambuLab        |
| 4    | Prusa           |
| 5    | Overture        |
| 6    | eSUN            |
| 7    | AmazonBasics    |
| 9    | SUNLU           |
| 10   | ERYONE          |

---

## Filament Type Mapping (Updated to Match OpenPrintTag's Type Codes)

| Key | Name | Full name |
|-----|------|-----------|
| 0 | `PLA` | Polylactic Acid |
| 1 | `PETG` | Polyethylene Terephthalate Glycol |
| 2 | `TPU` | Thermoplastic Polyurethane |
| 3 | `ABS` | Acrylonitrile Butadiene Styrene |
| 4 | `ASA` | Acrylonitrile Styrene Acrylate |
| 5 | `PC` | Polycarbonate |
| 6 | `PCTG` | Polycyclohexylenedimethylene Terephthalate Glycol |
| 7 | `PP` | Polypropylene |
| 8 | `PA6` | Polyamide 6 |
| 9 | `PA11` | Polyamide 11 |
| 10 | `PA12` | Polyamide 12 |
| 11 | `PA66` | Polyamide 66 |
| 12 | `CPE` | Copolyester |
| 13 | `TPE` | Thermoplastic Elastomer |
| 14 | `HIPS` | High Impact Polystyrene |
| 15 | `PHA` | Polyhydroxyalkanoate |
| 16 | `PET` | Polyethylene Terephthalate |
| 17 | `PEI` | Polyetherimide |
| 18 | `PBT` | Polybutylene Terephthalate |
| 19 | `PVB` | Polyvinyl Butyral |
| 20 | `PVA` | Polyvinyl Alcohol |
| 21 | `PEKK` | Polyetherketoneketone |
| 22 | `PEEK` | Polyether Ether Ketone |
| 23 | `BVOH` | Butenediol Vinyl Alcohol Copolymer |
| 24 | `TPC` | Thermoplastic Copolyester |
| 25 | `PPS` | Polyphenylene Sulfide |
| 26 | `PPSU` | Polyphenylsulfone |
| 27 | `PVC` | Polyvinyl Chloride |
| 28 | `PEBA` | Polyether Block Amide |
| 29 | `PVDF` | Polyvinylidene Fluoride |
| 30 | `PPA` | Polyphthalamide |
| 31 | `PCL` | Polycaprolactone |
| 32 | `PES` | Polyethersulfone |
| 33 | `PMMA` | Polymethyl Methacrylate |
| 34 | `POM` | Polyoxymethylene |
| 35 | `PPE` | Polyphenylene Ether |
| 36 | `PS` | Polystyrene |
| 37 | `PSU` | Polysulfone |
| 38 | `TPI` | Thermoplastic Polyimide |


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

Automated Updates for Filaments for the following manufacturers:

| PolyMaker (Complete)      |
| BambuLab  (Complete)      |
| Prusa (requires graphql - actively working on) |
| Overture (parsing work is done, but filtering needs work) |
| eSUN (mostly complete, needs sorting and checks against master) |
| SUNLU   (parsing work is done, but filtering needs work) |
| ERYONE (parsing work is done, but filtering needs work) |
| VOXELPLA (Complete)          |
| HATCHBOX (Complete)         |

## Additional Notes

I am open to adding additional manufacturers as well so long as they at least have their own websites (scraping popular ecommerce like amazon can be messy). Shopify based retailers tend to be the easiest to work with based on their structure, custom sites tend to take more effort.
This is mostly a hobby project - so updates may be erradic. I'm also using this as a jumping off point to learning github - so PRs and commits may be a little messy. If I get to the point to where I can consistently pull from a fair few manufacturers and get adequate comparisons in python - I will split off between dev and stable branches to ensure entries aren't incidentally removed/changed.

As this is a redux of sorts of the PCX database - if the PCX db ever gets updated (shows last updated some time in 2024) - then the cross compatibility of this database will get a bit muddy. In the interest of maintaining the current numbers in this DB. The PCDB's entries will NOT be modifed to change any updates made to PCX simply to avoid having to reprint any labels or to comprimise the lookup system. If you've made it this far. Thanks for checking out the project!
