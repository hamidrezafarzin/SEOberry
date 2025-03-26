import csv
import time
import tldextract
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class GoogleScraper:
    """
    Handles Google search scraping and domain ranking extraction using Selenium.
    """

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    @staticmethod
    def get_domain(website: str) -> str:
        extracted = tldextract.extract(website)
        return f"{extracted.domain}.{extracted.suffix}"

    def wait_for_captcha(self) -> None:
        """
        Waits until the user has solved any encountered captcha.
        """
        while "captcha" in self.driver.page_source.lower() or "unusual traffic" in self.driver.page_source.lower():
            logging.warning("Captcha detected. Please solve it manually in the browser, then press Enter to continue...")
            input()

    def scrape_links_with_order(self) -> list:
        """
        Scrapes Google search result links and extracts their domains in order.
        """
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[.//h3]"))
            )
        except TimeoutException as e:
            if "captcha" in self.driver.page_source.lower() or "unusual traffic" in self.driver.page_source.lower():
                logging.warning("Captcha detected during scraping. Waiting for you to solve it...")
                self.wait_for_captcha()
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//a[.//h3]"))
                )
            else:
                raise e

        a_elements = self.driver.find_elements(By.XPATH, "//a[.//h3]")
        domains = []
        for a in a_elements:
            href = a.get_attribute("href")
            if href and href.startswith("http"):
                domain = self.get_domain(href)
                if domain and domain != '.':
                    domains.append(domain)
        return domains

    def handle_google_consent(self) -> None:
        """
        Clicks on the Google consent button if present.
        """
        try:
            consent_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(),'I agree') or contains(text(),'\\u0642\\u0628\\u0648\\u0644') or contains(text(),'\\u0645\\u0648\\u0627\\u0641\\u0642\\u0645')]")
                )
            )
            consent_button.click()
            time.sleep(0.5)
        except Exception:
            pass

    def search_and_get_domain_ranks(self, keyword: str) -> dict:
        """
        Searches Google for a given keyword and returns a dictionary of domain ranks.
        """
        self.driver.get("https://www.google.com")
        self.handle_google_consent()

        try:
            search_box = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.NAME, "q"))
            )
        except TimeoutException:
            logging.error("Search box not found (captcha overlay might be present). Please solve any captcha manually, then press Enter...")
            input()
            search_box = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.NAME, "q"))
            )

        self.driver.execute_script("arguments[0].value = '';", search_box)
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)

        self.wait_for_captcha()
        time.sleep(0.5)

        domains_first = self.scrape_links_with_order()
        domains_second = []

        try:
            next_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "pnnext"))
            )
            if next_button.is_displayed() and next_button.size.get('height', 0) > 0 and next_button.size.get('width', 0) > 0:
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "pnnext"))
                )
                next_button.click()
                self.wait_for_captcha()
                time.sleep(0.5)
                domains_second = self.scrape_links_with_order()
            else:
                logging.info("Next button is not interactable (zero size); skipping second page.")
        except Exception as e:
            logging.warning(f"No next page for keyword '{keyword}' or error occurred: {e}")

        all_domains = domains_first + domains_second
        domain_ranks = {}
        for index, domain in enumerate(all_domains, start=1):
            if domain not in domain_ranks:
                domain_ranks[domain] = index
        return domain_ranks


class CSVProcessor:
    """
    Processes input CSV files, applies GoogleScraper to fetch rankings, and outputs the updated CSV.
    """

    def __init__(self, scraper: GoogleScraper):
        self.scraper = scraper

    def process(self, input_file: str, output_file: str) -> None:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)

        websites = []
        website_indices = {}
        for i, col in enumerate(header):
            col_strip = col.strip()
            if " " not in col_strip and "." in col_strip:
                websites.append(col_strip)
                website_indices[col_strip] = i

        website_domains = {website: self.scraper.get_domain(website) for website in websites}

        for row in rows:
            keyword = row[0].strip()
            logging.info(f"Processing keyword: {keyword}")
            domain_ranks = self.scraper.search_and_get_domain_ranks(keyword)

            for website in websites:
                domain = website_domains[website]
                if website in website_indices:
                    row[website_indices[website]] = str(domain_ranks.get(domain, "100"))
                else:
                    logging.warning(f"Website column '{website}' not found in CSV header.")

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

        logging.info(f"Processing complete. Results saved to {output_file}")


def main():
    # Create the WebDriver instance (could be injected from outside for easier testing)
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    try:
        scraper = GoogleScraper(driver)
        processor = CSVProcessor(scraper)
        processor.process("input.csv", "output.csv")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()