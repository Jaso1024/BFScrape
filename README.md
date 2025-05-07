# BFScrape

A concurrent, AI-driven breadth-first web scraper using Selenium and BeautifulSoup. BFScrape explores web pages intelligently by using AI models to determine which links to follow, collecting text content in a structured way.

## Features

- **AI-Driven Link Selection**: Uses OpenAI language models to intelligently decide which links to follow
- **Multi-threaded BFS**: Traverses websites in breadth-first order with concurrent processing
- **Domain Restriction**: Restricts scraping to a single domain to prevent uncontrolled crawling
- **Customizable**: Configure workers, timeouts, model parameters, and more
- **Structured Output**: Returns organized results with URLs and extracted content
- **Robust Error Handling**: Handles common web scraping issues gracefully

## Installation

### From PyPI

```bash
pip install bfscrape
```

### From Source

```bash
git clone https://github.com/yourusername/bfscrape.git
cd bfscrape
pip install -e .
```

### NixOS

For NixOS users, a shell.nix file is provided. All dependencies are managed in the Python virtual environment, not directly through Nix.

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install BFScrape
pip install -e .
```

## Usage

### Basic Usage

```python
from bfs_scrape import BFSWebScraper

# Initialize scraper with a start URL and a prompt describing what to find
scraper = BFSWebScraper(
    start_url="https://example.com",
    prompt="Find all information about product features and pricing",
    max_workers=5,
    model_api_key="your-openai-api-key"  # Or set OPENAI_API_KEY environment variable
)

# Start scraping
results = scraper.start_scraping()

# Print stats
scraper.print_stats()

# Access the results
for url, content in results.items():
    print(f"URL: {url}")
    print(f"Content: {content[:200]}...")  # Print first 200 chars
```

### Advanced Configuration

```python
from bfs_scrape import BFSWebScraper
from selenium.webdriver.chrome.options import Options

# Custom browser options
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

# Initialize with custom settings
scraper = BFSWebScraper(
    start_url="https://example.com",
    prompt="Find all information about product features and pricing",
    max_workers=10,
    browser_options=chrome_options,
    model_name="gpt-4o-mini",
    model_api_key="your-openai-api-key",
    base_url="https://your-openai-compatible-api-endpoint.com/v1",  # Optional, for custom endpoints
    load_timeout=5,
    top_k=3,
    max_context_words_per_node=100,
    max_links_to_assess=30
)

results = scraper.start_scraping()
```

## How It Works

1. BFScrape starts with a single URL
2. It visits the page, extracts content, and finds all links
3. AI assessment ranks links by relevancy to the provided prompt
4. Top-ranked links are followed in the next iteration
5. This process continues breadth-first, level by level
6. When no more relevant links are found (or AI determines task complete), scraping stops
7. The collected text content is returned

## Requirements

- Python 3.8+
- Chrome browser and ChromeDriver (for Selenium)
- Internet connection
- OpenAI API key (or compatible alternative)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 
