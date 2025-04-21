import argparse
import logging
import os
import sys
from selenium import webdriver
from seoberry.scraper import GoogleScraper, CSVProcessor

EXAMPLE_HEADER = """Keyword,Site1.com,Site2.com,Site3.com
"best laptops","10","5","2"
"top smartphones","7","3","1"
"""

def main():
    parser = argparse.ArgumentParser(
        description="Google Rank Scraper - Extracts Google search rankings for given websites."
    )
    
    parser.add_argument(
        '-i', '--input',
        default="input.csv",
        required=False,
        help="Path to the input CSV file (default: input.csv). "
             "The file must contain a column named 'Keyword' and other columns should be website addresses."
    )
    
    parser.add_argument(
        '-o', '--output',
        default="output.csv",
        required=False,
        help="Path to the output CSV file where results will be saved (default: output.csv)."
    )

    parser.add_argument(
        '--example-header',
        action='store_true',
        help="Prints an example of the required CSV header format."
    )

    args = parser.parse_args()

    if args.example_header:
        print("Example CSV Format:\n")
        print(EXAMPLE_HEADER)
        return

    # Check if the input file exists
    if not os.path.isfile(args.input):
        logging.error(f"Input file '{args.input}' does not exist. Please provide a valid CSV file.")
        sys.exit(1)

    # Create the WebDriver instance
    driver = webdriver.Chrome()
    
    try:
        scraper = GoogleScraper(driver)
        processor = CSVProcessor(scraper)
        processor.process(args.input, args.output)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
