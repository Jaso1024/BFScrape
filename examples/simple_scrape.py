#!/usr/bin/env python
"""
Simple example of using BFScrape to scrape a website.

This example demonstrates the basic usage of BFScrape to scrape
a website and save the results to a JSON file.
"""

import json
import os
from bfs_scrape import BFSWebScraper

def main():
    """Run a simple scraping example."""
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        print("Warning: No OpenAI API key found in OPENAI_API_KEY environment variable.")
        print("You must provide an API key to use the scraper.")
        return
    
    # Initialize the scraper with example.com as the start URL
    scraper = BFSWebScraper(
        start_url="https://example.com",
        prompt="Find information about what this domain is used for",
        max_workers=5,
        model_api_key=api_key,
        model_name="gpt-4o-mini",  # Change to a model you have access to
        top_k=3,  # Maximum of 3 links to traverse at each level
        load_timeout=5  # Wait 5 seconds for page load
    )
    
    # Start scraping
    print("Starting scrape...")
    results = scraper.start_scraping()
    
    # Print statistics
    scraper.print_stats()
    
    # Save results to a JSON file
    with open("scrape_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to scrape_results.json")
    
    # Print a sample of the results
    print("\nSample of results:")
    for url, content in list(results.items())[:2]:
        print(f"\nURL: {url}")
        print(f"Content preview: {content[:200]}...")

if __name__ == "__main__":
    main() 