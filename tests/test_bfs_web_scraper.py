"""
Tests for the BFSWebScraper class.
"""

import unittest
from unittest.mock import patch, MagicMock
from bfs_scrape import BFSWebScraper
from bfs_scrape.structured_outputs import LinkAssessmentOutput, LinkAssessment

class TestBFSWebScraper(unittest.TestCase):
    """Test cases for the BFSWebScraper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the OpenAI client to avoid API calls during tests
        self.openai_patcher = patch('openai.OpenAI')
        self.mock_openai_class = self.openai_patcher.start()
        self.mock_openai_client = MagicMock()
        self.mock_openai_class.return_value = self.mock_openai_client
        
        # Mock chat completions
        self.mock_completion = MagicMock()
        self.mock_openai_client.chat.completions.create.return_value = self.mock_completion
        
        # Setup mock response
        self.mock_message = MagicMock()
        self.mock_message.content = '{"example": "response"}'
        self.mock_choice = MagicMock()
        self.mock_choice.message = self.mock_message
        self.mock_completion.choices = [self.mock_choice]
        
        # Create a test scraper
        self.scraper = BFSWebScraper(
            start_url="https://example.com",
            max_workers=1,
            prompt="Test prompt"
        )
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.openai_patcher.stop()
    
    def test_initialization(self):
        """Test that scraper initializes correctly."""
        self.assertEqual(self.scraper.start_url, "https://example.com")
        self.assertEqual(self.scraper.max_workers, 1)
        self.assertEqual(self.scraper.prompt, "Test prompt")
        self.assertEqual(self.scraper.top_k, 5)  # Default value
        self.assertEqual(self.scraper.base_domain, "example.com")
        self.assertIsNotNone(self.scraper.browser_options)
        self.assertEqual(self.scraper.current_state, "SEARCHING")  # Initial state
        
    def test_get_results_empty(self):
        """Test get_results with no data."""
        # Initially there should be no results
        results = self.scraper.get_results()
        self.assertEqual(results, {})
    
    def test_get_results_with_data(self):
        """Test get_results with some data."""
        # Add some test data
        self.scraper.scraped_data = {
            "https://example.com": ["Test content 1", "Test content 2"],
            "https://example.com/page": ["Test page content"]
        }
        
        results = self.scraper.get_results()
        self.assertEqual(len(results), 2)
        self.assertEqual(results["https://example.com"], "Test content 1\nTest content 2")
        self.assertEqual(results["https://example.com/page"], "Test page content")
    
    def test_generate_with_openai(self):
        """Test the OpenAI wrapper method."""
        # Set up mock response
        self.mock_message.content = '{"test": "value"}'
        
        # Call the method
        result = self.scraper._generate_with_openai("Test prompt")
        
        # Verify the result
        self.assertEqual(result, {"test": "value"})
        self.mock_openai_client.chat.completions.create.assert_called_once()
    
    @patch('bfs_scrape.bfs_web_scraper.webdriver.Chrome')
    def test_process_node_basic(self, mock_chrome):
        """Test processing a node."""
        # Mock the Chrome webdriver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock page source
        mock_driver.page_source = "<html><body><p>Test content</p></body></html>"
        
        # Create a test node
        node = self.scraper.root
        
        # Process the node
        self.scraper._process_node(node, 0, 10)
        
        # Verify results
        self.assertIn("https://example.com", self.scraper.scraped_data)
        self.assertEqual(node.text_content, "Test content")
        

if __name__ == '__main__':
    unittest.main() 