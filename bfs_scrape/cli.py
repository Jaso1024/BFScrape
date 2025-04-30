#!/usr/bin/env python
"""
Command-line interface for BFScrape.

This module provides a command-line interface to the BFScrape web scraper,
allowing users to start a scraping job from the terminal.
"""

import argparse
import json
import sys
from bfs_scrape import BFSWebScraper

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="BFScrape - AI-driven breadth-first web scraper")
    
    parser.add_argument("url", help="Starting URL to scrape")
    parser.add_argument(
        "--prompt", "-p", 
        help="User prompt describing what information to find", 
        default="Find all relevant information."
    )
    parser.add_argument(
        "--workers", "-w", 
        help="Number of concurrent workers", 
        type=int, 
        default=10
    )
    parser.add_argument(
        "--timeout", "-t", 
        help="Page load timeout in seconds", 
        type=int, 
        default=10
    )
    parser.add_argument(
        "--top-k", "-k", 
        help="Maximum number of links to traverse at each level", 
        type=int, 
        default=5
    )
    parser.add_argument(
        "--model", "-m", 
        help="AI model to use for link selection", 
        default="gpt-4o-mini"
    )
    parser.add_argument(
        "--api-key", "-a", 
        help="API key for the AI model"
    )
    parser.add_argument(
        "--base-url", "-b", 
        help="Base URL for the AI model API"
    )
    parser.add_argument(
        "--output", "-o", 
        help="Output file path to save results (JSON format)",
    )
    
    return parser.parse_args()

def main():
    """Run the BFScrape CLI."""
    args = parse_args()
    
    print(f"BFScrape - Starting scrape from {args.url}")
    print(f"Prompt: {args.prompt}")
    print(f"Workers: {args.workers}")
    
    try:
        scraper = BFSWebScraper(
            start_url=args.url,
            max_workers=args.workers,
            prompt=args.prompt,
            model_name=args.model,
            model_api_key=args.api_key,
            base_url=args.base_url,
            load_timeout=args.timeout,
            top_k=args.top_k
        )
        
        results = scraper.start_scraping()
        scraper.print_stats()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to {args.output}")
        else:
            # Print a sample of results
            print("\nResults sample:")
            for i, (url, content) in enumerate(results.items()):
                if i >= 3:  # Show only first 3 results
                    print(f"... and {len(results) - 3} more URLs")
                    break
                print(f"\n{url}:")
                # Print first 200 chars of content
                print(f"{content[:200]}..." if len(content) > 200 else content)
                
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 