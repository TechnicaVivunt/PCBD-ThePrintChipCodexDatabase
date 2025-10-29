import csv
import time
import re
from io import StringIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Your product CSV list (replace this with reading a file if you prefer)
product_list_csv = """Product Name,Variant,Product URL
PLA Basic,(default),https://us.store.bambulab.com/products/pla-basic-filament
PLA Matte,(default),https://us.store.bambulab.com/products/pla-matte
PLA Silk+,(default),https://us.store.bambulab.com/products/pla-silk-upgrade
PETG HF,(default),https://us.store.bambulab.com/products/petg-hf
PETG Translucent,(default),https://us.store.bambulab.com/products/petg-translucent
ABS,(default),https://us.store.bambulab.com/products/abs-filament
PLA Tough+,(default),https://us.store.bambulab.com/products/pla-tough-upgrade
PLA Translucent,(default),https://us.store.bambulab.com/products/pla-translucent
PLA Silk Multi-Color,(default),https://us.store.bambulab.com/products/pla-silk-multi-color
PLA-CF,(default),https://us.store.bambulab.com/products/pla-cf
PLA Basic Gradient,(default),https://us.store.bambulab.com/products/pla-basic-gradient
PLA Sparkle,(default),https://us.store.bambulab.com/products/pla-sparkle
PLA Metal,(default),https://us.store.bambulab.com/products/pla-metal
PLA Marble,(default),https://us.store.bambulab.com/products/pla-marble
PLA Galaxy,(default),https://us.store.bambulab.com/products/pla-galaxy
PLA Wood,(default),https://us.store.bambulab.com/products/pla-wood
PLA Glow,(default),https://us.store.bambulab.com/products/pla-glow
TPU for AMS,(default),https://us.store.bambulab.com/products/tpu-for-ams
TPU 95A HF,(default),https://us.store.bambulab.com/products/tpu-95a-hf
TPU 85A / TPU 90A,(default),https://us.store.bambulab.com/products/tpu-85a-tpu-90a
PETG-CF,(default),https://us.store.bambulab.com/products/petg-cf
PAHT-CF,(default),https://us.store.bambulab.com/products/paht-cf
ASA,(default),https://us.store.bambulab.com/products/asa-filament
PA6-CF,(default),https://us.store.bambulab.com/products/pa6-cf
PC,(default),https://us.store.bambulab.com/products/pc-filament
PET-CF,(default),https://us.store.bambulab.com/products/pet-cf
PA6-GF,(default),https://us.store.bambulab.com/products/pa6-gf
ABS-GF,(default),https://us.store.bambulab.com/products/abs-gf
ASA-CF,(default),https://us.store.bambulab.com/products/asa-cf
PPA-CF,(default),https://us.store.bambulab.com/products/ppa-cf
PPS-CF,(default),https://us.store.bambulab.com/products/pps-cf
PLA Aero,(default),https://us.store.bambulab.com/products/pla-aero
ASA Aero,(default),https://us.store.bambulab.com/products/asa-aero
PC FR,(default),https://us.store.bambulab.com/products/pc-fr
Support for PLA/PETG,(default),https://us.store.bambulab.com/products/support-for-pla-petg
Support for PLA (New Version),(default),https://us.store.bambulab.com/products/support-for-pla-new
PVA,(default),https://us.store.bambulab.com/products/pva
Support for PA/PET,(default),https://us.store.bambulab.com/products/support-for-pa-pet
Support for ABS,(default),https://us.store.bambulab.com/products/support-for-abs"""

# Parse CSV string into list of dicts
products = list(csv.DictReader(StringIO(product_list_csv)))

# Setup headless Chrome
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=options)

# Output CSV file
output_file = "dbworker\bambu_filament_index.csv"

with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['brand_name', 'Variant', 'Color Index', 'color_name', 'Image URL', 'Product URL'])

    for product in products:
        product_name = product['Product Name']
        variant = product['Variant']
        url = product['Product URL']

        print(f"Scraping colors for: {product_name} - {url}")

        for attempt in range(3):
            try:
                driver.get(url)
                wait = WebDriverWait(driver, 10)

                swatch_ul = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.swatch-view-custom-image")))
                swatch_items = swatch_ul.find_elements(By.CSS_SELECTOR, "li.swatch-view-item")

                for idx, item in enumerate(swatch_items, 1):
                    color_name = driver.execute_script("return arguments[0].getAttribute('value')", item)
                    if not color_name:
                        color_name = item.get_attribute("value")

                    # Clean color name: remove trailing numbers in parentheses
                    clean_color_name = re.sub(r'\s*\(\d+\)$', '', color_name).strip()

                    style_div = item.find_element(By.CSS_SELECTOR, "div > div")
                    style = style_div.get_attribute("style")
                    url_start = style.find("url(")
                    url_end = style.find(")", url_start)
                    image_url = style[url_start + 4 : url_end].strip('"\'')
                    
                    writer.writerow([product_name, variant, idx, clean_color_name, image_url, url])

                time.sleep(15)  # Shorter delay
                break  # Success, exit retry loop

            except TimeoutException:
                print(f"Timeout on {url}, retrying ({attempt + 1}/3)...")
                time.sleep(5)
            except Exception as e:
                print(f"Failed to scrape {url}: {e}")
                break  # Don't retry on other exceptions

driver.quit()
print(f"Done! All data saved to {output_file}")
