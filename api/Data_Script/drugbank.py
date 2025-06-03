import time
import os
import sys
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_drugbank_info(medication_name):
    """
    Scrape DrugBank for metabolism and route of elimination information.
    Returns a dictionary with the scraped data.
    """
    logger.info(f"Scraping DrugBank for {medication_name}")
    driver = None

    try:
        # Configure Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Now enabled with fixes
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")  # Helps with headless stability
        chrome_options.add_argument(
            "--window-size=1920,1080"
        )  # Set window size for headless
        chrome_options.add_argument(
            "--disable-web-security"
        )  # May help with some sites
        chrome_options.add_argument(
            "--disable-features=VizDisplayCompositor"
        )  # Stability fix
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        # Initialize the driver
        logger.info("Initializing Chrome driver")
        driver = webdriver.Chrome(options=chrome_options)
        wait_time = 20  # Increased wait time for headless mode

        result = {"metabolism": "N/A", "route_of_elimination": "N/A"}

        logger.info("Navigating to DrugBank")
        driver.get("https://go.drugbank.com/")

        # Don't maximize window in headless mode
        if not chrome_options.arguments.__contains__("--headless"):
            driver.maximize_window()

        # Initialize WebDriverWait
        wait = WebDriverWait(driver, wait_time)

        # Wait for page to fully load
        time.sleep(2)

        # Search for the medication with more robust approach
        logger.info(f"Searching for {medication_name}")

        # Try multiple selectors for the search box
        search_selectors = [
            (By.ID, "query"),
            (By.NAME, "query"),
            (By.CSS_SELECTOR, "input[type='search']"),
            (By.CSS_SELECTOR, "input[placeholder*='search']"),
            (By.XPATH, "//input[@type='search' or @type='text']"),
        ]

        search_box = None
        for selector in search_selectors:
            try:
                search_box = wait.until(EC.element_to_be_clickable(selector))
                logger.info(f"Found search box using selector: {selector[1]}")
                break
            except TimeoutException:
                continue

        if search_box is None:
            raise Exception("Could not find search box")

        # Clear any existing text and search
        search_box.clear()
        time.sleep(0.5)
        search_box.send_keys(medication_name)
        time.sleep(1)
        search_box.send_keys(Keys.RETURN)

        # Wait longer for results in headless mode
        time.sleep(3)

        # Wait for the results page and find the Metabolism text
        logger.info("Waiting for drug information page")

        # Try to find metabolism section with multiple approaches
        metabolism_found = False
        metabolism_selectors = [
            (By.ID, "metabolism"),
            (By.XPATH, "//dt[@id='metabolism']"),
            (By.XPATH, "//h3[contains(text(), 'Metabolism')]"),
            (
                By.XPATH,
                "//*[contains(@id, 'metabolism') or contains(text(), 'Metabolism')]",
            ),
        ]

        for selector in metabolism_selectors:
            try:
                wait.until(EC.presence_of_element_located(selector))
                logger.info("Drug page loaded - metabolism section found")
                metabolism_found = True
                break
            except TimeoutException:
                continue

        if not metabolism_found:
            logger.warning("Could not find metabolism section")

        # Get Metabolism information with multiple XPath attempts
        metabolism_xpaths = [
            "//dt[@id='metabolism']/following-sibling::dd[1]/p[1]",
            "//dt[@id='metabolism']/following-sibling::dd[1]",
            "//h3[contains(text(), 'Metabolism')]/following-sibling::p[1]",
            "//div[contains(@id, 'metabolism')]//p[1]",
            "//*[@id='metabolism']/parent::*/following-sibling::*//p[1]",
        ]

        for xpath in metabolism_xpaths:
            try:
                metabolism_element = wait.until(
                    EC.visibility_of_element_located((By.XPATH, xpath))
                )
                result["metabolism"] = metabolism_element.text.strip()
                logger.info("Retrieved metabolism information")
                break
            except (NoSuchElementException, TimeoutException):
                continue

        if result["metabolism"] == "N/A":
            logger.warning("Could not find metabolism information")

        # Get Route of Elimination information
        logger.info("Getting route of elimination information")

        # Scroll to route of elimination section
        route_selectors = [
            "route-of-elimination",
            "elimination",
            "route_of_elimination",
        ]

        route_found = False
        for route_id in route_selectors:
            try:
                route_heading_element = driver.find_element(By.ID, route_id)
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    route_heading_element,
                )
                time.sleep(1)
                route_found = True
                break
            except NoSuchElementException:
                continue

        # Try multiple XPaths for route of elimination
        route_xpaths = [
            "//dt[@id='route-of-elimination']/following-sibling::dd[1]/p[1]",
            "//dt[@id='route-of-elimination']/following-sibling::dd[1]",
            "//h3[contains(text(), 'Route of Elimination')]/following-sibling::p[1]",
            "//div[contains(@id, 'elimination')]//p[1]",
            "//*[contains(@id, 'route') and contains(@id, 'elimination')]/parent::*/following-sibling::*//p[1]",
        ]

        for xpath in route_xpaths:
            try:
                route_element = wait.until(
                    EC.visibility_of_element_located((By.XPATH, xpath))
                )
                result["route_of_elimination"] = route_element.text.strip()
                logger.info("Retrieved route of elimination information")
                break
            except (NoSuchElementException, TimeoutException):
                continue

        if result["route_of_elimination"] == "N/A":
            logger.warning("Could not find route of elimination information")

    except Exception as e:
        logger.error(f"Error scraping DrugBank: {e}")
        return {"metabolism": "N/A", "route_of_elimination": "N/A"}

    finally:
        logger.info("Closing browser")
        if driver is not None:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

    return result


# Test the function
if __name__ == "__main__":
    # Test with a common medication
    result = get_drugbank_info("Atorvastatin")
    logger.info(f"Results: {result}")
