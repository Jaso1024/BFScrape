from setuptools import setup, find_packages

setup(
    name="bfscrape",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "selenium>=4.0.0",
        "beautifulsoup4>=4.9.0",
        "pydantic>=1.8.0",
        "openai>=1.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "bfscrape=bfs_scrape.cli:main",
        ],
    },
) 