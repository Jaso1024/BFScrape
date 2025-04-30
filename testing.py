import json
from bfs_scrape.bfs_web_scraper import BFSWebScraper
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    # Example usage
    start_url = "https://yale.downtownerapp.com/text/routes"
    
    # Create and configure the scraper
    scraper = BFSWebScraper(
        start_url, 
        max_workers=50, 
        load_timeout=5,
        model_name="gemini-2.0-flash",
        model_api_key=os.getenv("AI_API_KEY"),
        prompt="Find informationn on what routes are available to Union Station.",
        base_url=os.getenv("base_url"),
        top_k=20,
        max_links_to_assess=30,
        max_context_words_per_node=100
    )
    
    # Start scraping
    results = scraper.start_scraping()
    
    # Print results
    print("\n--- Collected Data ---")
    print(json.dumps(results, indent=2))
    
    # Print statistics
    scraper.print_stats() 