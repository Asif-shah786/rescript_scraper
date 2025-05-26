import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import os


def get_drugbank_info(medication_name):
    """
    Scrape DrugBank for metabolism and route of elimination information.
    Returns a dictionary with the scraped data.
    """
    print(f"\nScraping DrugBank for {medication_name}...")

    # Configure Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--disable-gpu"
    )  # Required for headless mode on some systems
    chrome_options.add_argument("--window-size=1920,1080")  # Set a standard window size

    # Set Chrome binary location for Render
    if os.path.exists("/opt/render/project/.render/chrome/opt/google/chrome/chrome"):
        chrome_options.binary_location = (
            "/opt/render/project/.render/chrome/opt/google/chrome/chrome"
        )

    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    wait_time = 15  # Max time to wait for elements in seconds

    result = {"metabolism": "N/A", "route_of_elimination": "N/A"}

    try:
        print(f"Navigating to DrugBank...")
        driver.get("https://go.drugbank.com/")
        driver.maximize_window()

        # Initialize WebDriverWait
        wait = WebDriverWait(driver, wait_time)

        # Search for the medication
        print(f"Searching for '{medication_name}'...")
        search_box_locator = (By.ID, "query")
        search_box = wait.until(EC.presence_of_element_located(search_box_locator))
        search_box.send_keys(medication_name)
        search_box.send_keys(Keys.RETURN)

        # Wait for the results page and find the Metabolism text
        print("Waiting for drug information page...")
        metabolism_heading_locator = (By.ID, "metabolism")
        wait.until(EC.presence_of_element_located(metabolism_heading_locator))
        print("Drug page loaded. Finding Metabolism info...")

        # Get Metabolism information
        metabolism_text_locator = (
            By.XPATH,
            "//dt[@id='metabolism']/following-sibling::dd[1]/p[1]",
        )
        try:
            metabolism_element = wait.until(
                EC.visibility_of_element_located(metabolism_text_locator)
            )
            result["metabolism"] = metabolism_element.text
            print("Successfully retrieved metabolism information")
        except (NoSuchElementException, TimeoutException):
            print("Could not find the Metabolism paragraph")

        # Get Route of Elimination information
        print("Finding Route of Elimination info...")
        route_elimination_text_locator = (
            By.XPATH,
            "//dt[@id='route-of-elimination']/following-sibling::dd[1]/p[1]",
        )
        try:
            route_heading_element = driver.find_element(By.ID, "route-of-elimination")
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", route_heading_element
            )
            time.sleep(0.5)

            route_element = wait.until(
                EC.visibility_of_element_located(route_elimination_text_locator)
            )
            result["route_of_elimination"] = route_element.text
            print("Successfully retrieved route of elimination information")
        except (NoSuchElementException, TimeoutException):
            print("Could not find the Route of Elimination paragraph")

    except Exception as e:
        print(f"An error occurred while scraping DrugBank: {e}")

    finally:
        print("Closing the browser...")
        driver.quit()

    return result
