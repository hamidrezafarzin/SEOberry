from setuptools import setup, find_packages

setup(
    name="SEOberry",
    version="1.0.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    author="Hamidreza Farzin",
    author_email="hamidfarzin1382@gmail.com",
    description="A Python tool to scrape Google rankings of domains for given keywords using Selenium.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/hamidrezafarzin/SEOberry",
    license="MIT",
    install_requires=[
        "selenium>=4.0.0",
        "tldextract>=3.0.0"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "seoberry=seoberry.cli:main",
        ]
    },
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Source": "https://github.com/hamidrezafarzin/SEOberry",
        "Tracker": "https://github.com/hamidrezafarzin/SEOberry/issues",
    },
    include_package_data=True,
    zip_safe=False,
)
