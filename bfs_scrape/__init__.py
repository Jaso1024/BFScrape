"""
BFScrape - A concurrent, AI-driven breadth-first web scraper

A package for exploring websites using breadth-first search and AI-driven link selection.
"""

__version__ = "0.1.0"

from bfs_scrape.bfs_web_scraper import BFSWebScraper
from bfs_scrape.structured_outputs import LinkAssessmentOutput, LinkAssessment, LinkDecision

__all__ = [
    "BFSWebScraper",
    "LinkAssessmentOutput", 
    "LinkAssessment", 
    "LinkDecision", 
] 