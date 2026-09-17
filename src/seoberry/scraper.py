import csv
import time
import tldextract
import logging
import requests
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def create_driver() -> webdriver.Chrome:
    """
    Creates a Chrome WebDriver configured to avoid indefinite hangs.

    Google's post-captcha pages often keep loading background resources
    (ads, trackers, the captcha widget itself) that can delay or prevent
    the browser's "load" event from firing. With Selenium's default
    ("normal") page load strategy, every subsequent WebDriver command
    blocks until that event fires, which can freeze the script forever.
    "eager" only waits for the DOM to be ready, and the page load timeout
    below is a hard backstop in case a page never settles at all.
    """
    options = ChromeOptions()
    options.page_load_strategy = "eager"
    # Stock Selenium Chrome exposes navigator.webdriver = true and a
    # dedicated "enable-automation" flag, which Google's bot detection
    # checks for and uses to serve a captcha/"unusual traffic" challenge
    # far more aggressively than to a regular browser. Stripping these
    # doesn't guarantee a challenge-free session, but removes the most
    # obvious automation fingerprint.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    driver.set_page_load_timeout(30)
    return driver


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

    @staticmethod
    def _resolve_google_redirect(href: str) -> str:
        """
        Google increasingly wraps organic result links in a same-origin
        redirect instead of linking to the destination directly, so
        tldextract on the raw href resolves every result to "google.com"
        and no real domain is ever ranked. The older /url?q=<dest> form
        carries the destination in a plain query parameter; the newer
        /goto?url=<opaque-token> form does not (the token isn't decodable
        client-side), but a redirect-only request to it still returns the
        real destination in the Location header without needing cookies.
        """
        parsed = urlparse(href)
        if not parsed.netloc.endswith("google.com"):
            return href

        if parsed.path == "/url":
            query = parse_qs(parsed.query)
            if "q" in query and query["q"]:
                return query["q"][0]
            return href

        if parsed.path == "/goto":
            try:
                response = requests.get(href, allow_redirects=False, timeout=5)
                location = response.headers.get("Location")
                if location:
                    return location
            except requests.RequestException as e:
                logging.warning(f"Failed to resolve Google redirect '{href}': {e}")
            return href

        return href

    def _is_captcha_page(self) -> bool:
        """
        True only when the browser is actually on Google's captcha/"unusual
        traffic" interstitial. Google routes real challenges through a
        /sorry/ URL; checking for the word "captcha" anywhere in the raw
        page source is too broad, since normal search results pages embed
        reCAPTCHA/spam-protection scripts that also contain that word,
        which caused false positives and an infinite retry loop.
        """
        if "/sorry/" in self.driver.current_url.lower():
            return True
        return "unusual traffic from your computer network" in self.driver.page_source.lower()

    def wait_for_captcha(self) -> None:
        """
        Waits until the user has solved any encountered captcha.
        """
        while self._is_captcha_page():
            logging.warning("Captcha detected. Please solve it manually in the browser, then press Enter to continue...")
            input()

    def scrape_links_with_order(self) -> list:
        """
        Scrapes Google search result links and extracts their domains in order.
        """
        try:
            WebDriverWait(self.driver, 8).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[.//h3]"))
            )
        except TimeoutException as e:
            if self._is_captcha_page():
                logging.warning("Captcha detected during scraping. Waiting for you to solve it...")
                self.wait_for_captcha()
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//a[.//h3]"))
                )
            else:
                raise e

        a_elements = self.driver.find_elements(By.XPATH, "//a[.//h3]")
        domains = []
        for a in a_elements:
            href = a.get_attribute("href")
            if href and href.startswith("http"):
                resolved_href = self._resolve_google_redirect(href)
                domain = self.get_domain(resolved_href)
                if domain and domain != '.':
                    domains.append(domain)
        logging.info(f"Scraped {len(a_elements)} result link(s), extracted domains: {domains}")
        return domains

    def handle_google_consent(self) -> None:
        """
        Clicks on the Google consent button if present.
        """
        try:
            consent_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(text(),'I agree') or contains(text(),'\\u0642\\u0628\\u0648\\u0644') or contains(text(),'\\u0645\\u0648\\u0627\\u0641\\u0642\\u0645')]")
                )
            )
            consent_button.click()
        except Exception:
            pass

    def _submit_search(self, keyword: str) -> None:
        """
        Fills in the search box and submits the given keyword, prompting the
        user to solve a captcha manually if the search box can't be found.
        """
        try:
            search_box = WebDriverWait(self.driver, 2).until(
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

    def search_and_get_domain_ranks(self, keyword: str) -> dict:
        """
        Searches Google for a given keyword and returns a dictionary of domain ranks.
        """
        self.driver.get("https://www.google.com")
        self.handle_google_consent()
        self.wait_for_captcha()

        self._submit_search(keyword)
        self.wait_for_captcha()

        # Solving a captcha sometimes redirects back to the Google homepage
        # instead of the search results page, in which case the search above
        # never actually happened. Detect that and retry once instead of
        # silently scraping an empty/wrong page. A fixed sleep isn't reliable
        # here since the "eager" page load strategy hands control back before
        # the navigation/render is necessarily finished, so wait explicitly
        # for the URL to reflect a results page.
        try:
            WebDriverWait(self.driver, 8).until(EC.url_contains("/search"))
        except TimeoutException:
            logging.warning(
                "Landed on the Google homepage instead of search results "
                "(likely redirected here after solving a captcha); retrying the search..."
            )
            self._submit_search(keyword)
            self.wait_for_captcha()
            WebDriverWait(self.driver, 8).until(EC.url_contains("/search"))

        domains_first = self.scrape_links_with_order()
        domains_second = []

        try:
            next_button = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.CLASS_NAME, "oeN89d"))
            )
            if next_button.is_displayed() and next_button.size.get('height', 0) > 0 and next_button.size.get('width', 0) > 0:
                next_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "oeN89d"))
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
        logging.info(f"Domain ranks for keyword '{keyword}': {domain_ranks}")
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
            # Extend row to match header length if it's shorter
            row.extend([''] * (len(header) - len(row)))
            keyword = row[0].strip()
            logging.info(f"Processing keyword: {keyword}")
            try:
                domain_ranks = self.scraper.search_and_get_domain_ranks(keyword)
                search_failed = False
            except Exception as e:
                logging.error(f"Failed to process keyword '{keyword}': {e}. Skipping to next keyword.")
                domain_ranks = {}
                search_failed = True

            for website in websites:
                domain = website_domains[website]
                if website in website_indices:
                    # "100" means the domain genuinely wasn't among the
                    # scraped results; it must never stand in for a search
                    # that never completed (e.g. blocked by a captcha), or
                    # a real miss becomes indistinguishable from a failure.
                    if search_failed:
                        row[website_indices[website]] = "ERROR"
                    else:
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
    driver = create_driver()
    try:
        scraper = GoogleScraper(driver)
        processor = CSVProcessor(scraper)
        processor.process("input.csv", "output.csv")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()