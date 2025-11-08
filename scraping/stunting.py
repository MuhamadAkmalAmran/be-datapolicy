from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    service = Service('chromedriver.exe')
    return webdriver.Chrome(service=service, options=options)

def get_scraped_table(driver, year, provinsi):
    url = "https://aksi.bangda.kemendagri.go.id/emonev/DashPrev"
    driver.get(url)

    # Select the desired year
    year_select = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "_inp_sel_per"))
    )
    Select(year_select).select_by_visible_text(str(year))

    # Click on the province
    prov_select = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, f"//table/tbody/tr/td[contains(text(), '{provinsi}')]"))
    )
    prov_select.click()

    # Wait for the table to load
    table = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[1]/div/div[2]/div/div/div[2]/ul/div/table/tbody"))
    )
    return table

def scrape_data(year, provinsi, kab_kota):
    data = []
    with init_driver() as driver:
        try:
            table = get_scraped_table(driver, year, provinsi)
            rows = table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 5 and kab_kota in cols[1].text:
                    data.append({
                        "year": year,
                        "city": cols[1].text.strip(),
                        "amount": float(cols[5].text.strip())
                    })
        except Exception as e:
            print(f"Error while scraping data for year {year}: {e}")
        return data
