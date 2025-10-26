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

## Filament Type Mapping

| Type Number | Filament Type |
|------------|---------------|
| 1          | PLA           |
| 2          | PETG          |
| 3          | ASA           |
| 4          | ABS           |
| 5          | TPU           |
| 6          | TPE           |
| 7          | (PA) Nylon    |
| 8          | PC            |
| 9          | PP            |
| 10         | PEEK          |
| 11         | PVA           |
| 12         | PVB           |
| 13         | CoPE          |
| 14         | PET           |
| 15         | PPS           |
| 16         | CoPA          |
| 17         | PET           |
| 18         | PPA           |
| 19         | HIPS          |

---

## Database ID Format

The universal filament ID format is structured as: .csv - this is to maintain compatiblity for the Brother P-Touch software. 

**Components explained:**

| Segment                  | Example | Meaning |
|--------------------------|---------|---------|
| `PCDB`                   | PCDB    | Prefix indicating Print Chip Database |
| `<manufacturer_code>`     | 005     | Manufacturer code (Overture in this case) |
| `<PCX_number>`            | 001     | Original PCX number for the filament |
| `<filament_type_number>`  | 3       | Filament type (ASA) |

**Example:**
PCDB-005-001-3

^ This would be the first ASA entry for Overture's filament.

## References

- [The Print Codex](https://theprintcodex.com/)
- [Original Print Chip Codex by James@ThePrintCodex](https://www.printables.com/refresh?redirectUrl=%2F%40JamesThePrint_699540)  

## Roadmap

Currently - this is mostly being updated manually - I have a few prototyped scripts to manually pull the filament options/colors/variations from different manufacturer websites. The end goal will be to create some workflow/actions to periodically pull the data and have this repository automatically update anytime new filaments are found on the popular manufacturers.

Automated Updates for Filaments for the following manufacturers:

| PolyMaker       |
| BambuLab        |
| Prusa           |
| Overture        |
| eSUN            |
| SUNLU           |
| ERYONE          |

## Additional Notes

I am open to adding additional manufacturers as well so long as they at least have their own websites (scraping popular ecommerce like amazon can be messy).
This is mostly a hobby project - so updates may be erradic. I'm also using this as a jumping off point to learning github - so PRs and commits may be a little messy. If I get to the point to where I can consistently pull from a fair few manufacturers and get adequate comparisons in python - I will split off between dev and stable branches to ensure entries aren't incidentally removed/changed.

As this is a redux of sorts of the PCX database - if the PCX db ever gets updated (shows last updated some time in 2024) - then the cross compatibility of this database will get a bit muddy. In the interest of maintaining the current numbers in this DB. The PCDB's entries will NOT be modifed to change any updates made to PCX simply to avoid having to reprint any labels or to comprimise the lookup system. If you've made it this far. Thanks for checking out the project!
