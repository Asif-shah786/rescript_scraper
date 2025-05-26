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
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_drugbank_info(medication_name):
    """
    Scrape DrugBank for metabolism and route of elimination information.
    Returns a dictionary with the scraped data.
    """
    logger.info(f"\nScraping DrugBank for {medication_name}...")

    # Print environment information
    logger.info("Environment information:")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"ChromeDriver path: {os.path.exists('/usr/local/bin/chromedriver')}")
    logger.info(f"DISPLAY environment variable: {os.environ.get('DISPLAY')}")

    try:
        # Configure Chrome options for headless mode
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument(
            "--disable-features=IsolateOrigins,site-per-process"
        )

        # Initialize the driver with ChromeDriver from /usr/local/bin
        service = Service("/usr/local/bin/chromedriver")
        logger.info("Initializing Chrome driver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome driver initialized successfully")

        wait_time = 15  # Max time to wait for elements in seconds

        result = {"metabolism": "N/A", "route_of_elimination": "N/A"}

        logger.info(f"Navigating to DrugBank...")
        driver.get("https://go.drugbank.com/")
        driver.maximize_window()

        # Initialize WebDriverWait
        wait = WebDriverWait(driver, wait_time)

        # Search for the medication
        logger.info(f"Searching for '{medication_name}'...")
        search_box_locator = (By.ID, "query")
        search_box = wait.until(EC.presence_of_element_located(search_box_locator))
        search_box.send_keys(medication_name)
        search_box.send_keys(Keys.RETURN)

        # Wait for the results page and find the Metabolism text
        logger.info("Waiting for drug information page...")
        metabolism_heading_locator = (By.ID, "metabolism")
        wait.until(EC.presence_of_element_located(metabolism_heading_locator))
        logger.info("Drug page loaded. Finding Metabolism info...")

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
            logger.info("Successfully retrieved metabolism information")
        except (NoSuchElementException, TimeoutException):
            logger.info("Could not find the Metabolism paragraph")

        # Get Route of Elimination information
        logger.info("Finding Route of Elimination info...")
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
            logger.info("Successfully retrieved route of elimination information")
        except (NoSuchElementException, TimeoutException):
            logger.info("Could not find the Route of Elimination paragraph")

    except Exception as e:
        logger.error(f"An error occurred while scraping DrugBank: {e}")

    finally:
        logger.info("Closing the browser...")
        driver.quit()

    return result
