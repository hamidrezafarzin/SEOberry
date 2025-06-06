# SEOberry

**SEOberry** is a Python tool that scrapes Google search results to extract the SEO rankings of websites based on given keywords. Simply provide a CSV file, and SEOberry will automatically retrieve and update the ranking positions for each domain.

## Features

- **Automated Google Scraping:** Uses Selenium to fetch Google search results.
- **Domain Ranking Extraction:** Identifies and ranks domains found in search results.
- **CSV Integration:** Updates CSV files with ranking data.
- **Customizable CLI:** Run the tool with custom input/output file names.
- **Captcha Handling:** Prompts you to solve captchas when detected.

## Requirements

- Python 3.8 or higher
- [Selenium](https://pypi.org/project/selenium/)
- [tldextract](https://pypi.org/project/tldextract/)

## Installation

You can install SEOberry via pip (once published on PyPI):

```bash
pip install seoberry
```

Alternatively, if you want to install it from the source, clone the repository and run:

```bash
git clone https://github.com/hamidrezafarzin/SEOberry.git
cd SEOberry
pip install -e .
```

## Usage

SEOberry provides a command-line interface (CLI). The basic usage is:

```bash
seoberry -i input.csv -o output.csv
```

Where:
- `-i` or `--input` specifies the path to your input CSV file.
- `-o` or `--output` specifies the path to the output CSV file where the results will be saved.

You can also print an example of the required CSV header format by running:

```bash
seoberry --example-header
```

help command :

```bash
seoberry --help
```

### Example Command

```bash
python -m seoberry.cli -i my_keywords.csv -o my_results.csv
```


# Attention (captcha)  !
After every 100 searches, Google usually triggers a captcha that you need to solve. To avoid frequent interruptions, it's best to run searches in batches of 90 to 100 to minimize captcha challenges. **Once you solve the captcha, press the Enter key in the open terminal.**

## CSV Format

Your input CSV file **must** have a column named `Keyword`. All additional columns should contain website addresses whose rankings you want to track.

Here’s an example of the expected CSV format:

```csv
Keyword,Site1.com,Site2.com,Site3.com
"best laptops",,,
"top smartphones",,,
```

- **Keyword:** Contains the search term.
- **Site1.com, Site2.com, ...:** Columns with website URLs. SEOberry will extract the domain and determine its rank in the search results.

# Acknowledgments
Special thanks to **Reza Najibi (SEO Specialist)** for his insightful idea and invaluable assistance in developing and refining this module. Your support and collaboration have been truly appreciated!

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/hamidrezafarzin/SEOberry/issues) if you want to contribute.

## License

This project is licensed under the MIT License.
