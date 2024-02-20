from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse, urljoin
import json # Import json for pretty printing the output
import concurrent.futures
import threading
import traceback # Import traceback for detailed error logging
import openai # Import OpenAI package instead of StatefulModel
import os # For environment variables
from typing import Dict, Any, Optional, List, Type, TypeVar, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException, 
    StaleElementReferenceException, 
    ElementNotInteractableException,
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)
from bfs_scrape.structured_outputs import LinkAssessmentOutput, LinkDecision, LinkAssessment
from bfs_scrape.system_prompt import SYSTEM_PROMPT

T = TypeVar('T')

class Node:
    """
    Represents a node in the BFS traversal tree.
    
    Each node corresponds to a URL and maintains links to its parent and children nodes.
    
    Attributes:
        url (str): The URL this node represents
        parent (Node, optional): The parent node that led to this URL
        children (list): List of child nodes (discovered from this URL)
        should_traverse (bool): Whether this URL should be visited during traversal
        text_content (str, optional): The extracted text content from this URL
    """
    def __init__(self, url, parent=None):
        self.url = url
        self.parent = parent
        self.children = []
        self.should_traverse = True  # Will be set by AI
        self.text_content = None  # Optionally store page text

class BFSWebScraper:
    """
    A concurrent web scraper that uses a breadth-first search strategy with AI-driven link selection.
    
    This scraper builds a tree of URLs starting from a given URL and uses an AI model to
    determine which links are most relevant to the user's goal, exploring those preferentially.
    
    The scraper operates in levels (BFS), processing all URLs at the current depth before
    moving to the next level. For each URL, it extracts text content and discovers new links.
    The AI model then evaluates all discovered links and selects which ones to traverse next.
    
    Attributes:
        start_url (str): The URL to start scraping from
        max_workers (int): Maximum number of concurrent threads to use
        base_domain (str): Domain name to restrict scraping to
    """
    def __init__(self, start_url, max_workers=20, browser_options=None, model_name="gpt-4o-mini", model_api_key=None, prompt=None, base_url=None, load_timeout=10, top_k=5, max_context_words_per_node=200, max_links_to_assess=50):
        """
        Initialize the BFS web scraper with the given configuration.
        
        Args:
            start_url (str): The URL to start scraping from.
            max_workers (int, optional): Maximum number of concurrent threads to use. Defaults to 20.
            browser_options (selenium.webdriver.chrome.options.Options, optional): Custom Selenium Chrome options. 
                If None, default options optimized for headless scraping will be used.
            model_name (str, optional): Name of the LLM to use for link selection. Defaults to "gpt-4o-mini".
            model_api_key (str, optional): API key for the LLM provider. Required unless using a local model.
            prompt (str, optional): A string describing what you want the model to find (user goal).
                Defaults to "Find all relevant information."
            base_url (str, optional): Base URL for the API if using a custom endpoint.
            load_timeout (int, optional): Time to wait for page load in seconds. Defaults to 10.
            top_k (int, optional): Maximum number of links to traverse at each level. Defaults to 5.
            max_context_words_per_node (int, optional): Maximum number of words to include from each 
                parent node's context when assessing links. Defaults to 200.
            max_links_to_assess (int, optional): Maximum number of candidate links to assess in a single
                AI call. Defaults to 50.
        """
        self.start_url = start_url
        self.max_workers = max_workers
        self.parsed_start_url = urlparse(start_url)
        self.base_domain = self.parsed_start_url.netloc
        self.visited_urls = set()
        self.scraped_data = {}
        self.load_timeout = load_timeout
        self.data_lock = threading.Lock()
        self.top_k = top_k
        self.max_context_words_per_node = max_context_words_per_node
        self.max_links_to_assess = max_links_to_assess
        if browser_options is None:
            self.browser_options = self._create_default_browser_options()
        else:
            self.browser_options = browser_options
        self.root = Node(start_url)
        self.all_nodes = {start_url: self.root}
        self.prompt = prompt or "Find all relevant information."
        
        # Initialize OpenAI client
        self.model_name = model_name
        self.api_key = model_api_key or os.environ.get("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=base_url)
        
        # Current state - simplified from the StatefulModel approach
        self.current_state = "SEARCHING"  # Can be "SEARCHING" or "COMPLETE"
    
    def _create_default_browser_options(self):
        """
        Create default Chrome options optimized for headless scraping and speed.
        
        Returns:
            selenium.webdriver.chrome.options.Options: Configured Chrome options.
        """
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--log-level=3")  # Suppress excessive logging
        opts.add_experimental_option('excludeSwitches', ['enable-logging'])
        # Block images, CSS, and other non-essential resources
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.cookies": 2,
            "profile.managed_default_content_settings.plugins": 2,
            "profile.managed_default_content_settings.popups": 2,
            "profile.managed_default_content_settings.geolocation": 2,
            "profile.managed_default_content_settings.notifications": 2,
            "profile.managed_default_content_settings.media_stream": 2,
        }
        opts.add_experimental_option("prefs", prefs)
        return opts
    
    def _generate_with_openai(self, prompt: str, structured_output: Optional[Type[T]] = None, raw_response: bool = False) -> Union[str, Dict[str, Any], T]:
        """
        Generate text using OpenAI API with structured output support.
        
        Args:
            prompt (str): The prompt to send to the model
            structured_output (Type, optional): Pydantic model class for structured output
            raw_response (bool, optional): Whether to return the raw response text
            
        Returns:
            Union[str, Dict, T]: Either raw text, structured data, or Pydantic model instance
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"} if structured_output else None,
            )
            
            result = response.choices[0].message.content
            
            if raw_response:
                return result
            
            if structured_output:
                try:
                    # Parse the JSON response
                    parsed_data = json.loads(result)
                    
                    # If we got a dictionary, try to create a structured output
                    if isinstance(parsed_data, dict):
                        return structured_output(**parsed_data)
                    else:
                        print(f"[AI WARNING] Expected dictionary in JSON response, got {type(parsed_data)}")
                        return {"structured_output": parsed_data}
                        
                except Exception as e:
                    print(f"[AI ERROR] Failed to parse structured output: {e}")
                    # Return a simpler structure with the raw result
                    return {"structured_output": None, "raw_result": result}
            
            # No structured output requested, return parsed JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
                
        except Exception as e:
            print(f"[AI ERROR] OpenAI API call failed: {e}")
            if raw_response:
                return f"ERROR: {str(e)}"
            return {"error": str(e)}
    
    def start_scraping(self):
        """
        Start the breadth-first web scraping process.
        
        This method initiates the BFS traversal from the root URL and continues until 
        either the maximum depth is reached, there are no more URLs to traverse, or the
        AI model determines the task is complete.
        
        After scraping, if the state is COMPLETE, a final report
        is generated summarizing the scraped content in relation to the user's goal.
        
        Returns:
            dict: A dictionary mapping URLs to their extracted text content.
        """
        print(f"Starting breadth-first scrape from: {self.start_url}")
        print(f"Restricting to domain: {self.base_domain}")
        print(f"Using up to {self.max_workers} worker threads.")
        current_level = [self.root]
        depth = 0
        max_depth = 10
        self.current_state = "SEARCHING"
        final_report = None
        while current_level and depth <= max_depth and self.current_state != "COMPLETE":
            print(f"\nProcessing level {depth} with {len(current_level)} nodes...")
            next_level = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for node in current_level:
                    if node.should_traverse:
                        futures.append(executor.submit(self._process_node, node, depth, max_depth))
                concurrent.futures.wait(futures)
                # After all nodes at this level are processed, collect children for next level
                for node in current_level:
                    for child in node.children:
                        child.should_traverse = False  # Default to False, will be set by AI
                        next_level.append(child)
                # AI selection for all children at this level
                if next_level:
                    self.current_state = self._ai_select_links(next_level, current_level, depth)
            current_level = [n for n in next_level if n.should_traverse]
            depth += 1
        # If we exited because state is COMPLETE, ask for a final report
        if self.current_state == "COMPLETE":
            print("\n[AI] Scraping process reached COMPLETE state. Requesting final report from the model...")
            all_text = "\n\n".join([n.text_content or "" for n in self.all_nodes.values()])
            report_prompt = f"User goal: {self.prompt}\n\nAll collected page content (truncated to 8000 chars):\n{all_text[:8000]}\n\nPlease write a comprehensive report summarizing the desired output based on the above content."
            try:
                final_report = self._generate_with_openai(
                    prompt=report_prompt,
                    raw_response=True,
                )
                print("\n[AI FINAL REPORT]\n" + str(final_report))
            except Exception as e:
                print(f"[AI ERROR] Failed to generate final report: {e}")
        print("\nBFS traversal finished.")
        return self.get_results()
    
    def get_results(self):
        """
        Get the scraped results in a structured format.
        
        Returns:
            dict: A dictionary mapping URLs to their combined text content.
        """
        # Sort by URL for consistent output
        sorted_data = dict(sorted(self.scraped_data.items()))
        # Join the list of text blocks for each URL for final output
        final_output = {url: "\n".join(texts) for url, texts in sorted_data.items()}
        return final_output
    
    def print_stats(self):
        """
        Print statistics about the scraping process.
        
        This includes the total number of pages scraped and unique URLs visited.
        """
        print(f"\nTotal pages scraped: {len(self.scraped_data)}")
        print(f"Total unique URLs visited (including checks): {len(self.visited_urls)}")
    
    def _process_node(self, node, depth, max_depth):
        """
        Process a single node (URL) in the BFS tree.
        
        This method:
        1. Loads the URL using Selenium
        2. Extracts text content from the page
        3. Discovers links and adds them as children to the node
        
        Args:
            node (Node): The node to process
            depth (int): Current depth in the BFS traversal
            max_depth (int): Maximum depth to traverse
            
        Returns:
            None
        """
        url = node.url
        if url in self.visited_urls or depth > max_depth:
            return
        thread_id = threading.get_ident()
        print(f"[Thread {thread_id}] START Scraping: {url} (Depth: {depth})")
        driver = None
        try:
            driver = webdriver.Chrome(options=self.browser_options)
            driver.implicitly_wait(2)
            driver.get(url)

            time.sleep(self.load_timeout)

            initial_html = driver.page_source
            initial_soup = BeautifulSoup(initial_html, "html.parser")
            initial_text = initial_soup.get_text(separator="\n", strip=True)
            node.text_content = initial_text
            with self.data_lock:
                self.visited_urls.add(url)
                self.scraped_data[url] = [initial_text]
            # Find links and add as children (do not traverse yet)
            links = initial_soup.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if not href or href.startswith('#') or href.startswith('mailto:') or href.startswith('javascript:'):
                    continue
                absolute_url = urljoin(url, href)
                parsed_link = urlparse(absolute_url)
                cleaned_url = parsed_link._replace(fragment="", query="").geturl()
                if parsed_link.netloc == self.base_domain and cleaned_url not in self.all_nodes:
                    child_node = Node(cleaned_url, parent=node)
                    node.children.append(child_node)
                    self.all_nodes[cleaned_url] = child_node
        except Exception as e:
            print(f"[Thread {thread_id}] FATAL ERROR processing {url}: {e}")
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()
        print(f"[Thread {thread_id}] FINISHED Processing: {url} (Depth: {depth})")
    
    def _ai_select_links(self, candidate_nodes, parent_nodes, depth):
        """
        Use AI to select which links to traverse in the next level.
        
        This method:
        1. Extracts context from parent nodes
        2. Submits candidate links to the AI model for assessment
        3. Processes the AI's response to select links to traverse
        4. Updates the should_traverse flag on each node
        
        Args:
            candidate_nodes (list): List of Node objects representing candidate links
            parent_nodes (list): List of Node objects that were processed at the current level
            depth (int): Current depth in the BFS traversal
            
        Returns:
            str: Current state ("SEARCHING" or "COMPLETE")
        """
        # Limit the number of candidate links to assess
        links_to_assess = candidate_nodes[:self.max_links_to_assess]
        candidate_links_urls = [n.url for n in links_to_assess]
        if len(candidate_nodes) > self.max_links_to_assess:
            print(f"[AI INFO] Limiting AI assessment to {self.max_links_to_assess} links (out of {len(candidate_nodes)}). Links not assessed will default to not being traversed.")

        # Limit context from each parent node
        parent_contexts = []
        for node in parent_nodes:
            text = node.text_content or ""
            words = text.split()
            if len(words) > self.max_context_words_per_node:
                parent_contexts.append(" ".join(words[:self.max_context_words_per_node]) + "...")
            else:
                parent_contexts.append(text)
        parent_context = "\n---\n".join(parent_contexts)

        model_input = f"User goal: {self.prompt}\nCurrent depth: {depth}\nCandidate links: {json.dumps(candidate_links_urls, indent=2)}\nParent context: {parent_context[:1000]}"
        print("\n[AI DEBUG] Submitting the following candidate links to the AI for assessment:")
        for url in candidate_links_urls:
            print(f"  - {url}")
        try:
            raw_result = self._generate_with_openai(
                prompt=model_input,
                structured_output=LinkAssessmentOutput,
                raw_response=False,
            )
            print("[AI DEBUG] Raw AI output:")
            print(raw_result)

            structured_data = None
            if isinstance(raw_result, LinkAssessmentOutput):
                structured_data = raw_result
            else:
                print(f"[AI WARNING] Failed to get valid LinkAssessmentOutput. Got: {type(raw_result)}")
                
                # Try to parse manually if it's a dictionary with the right structure
                if isinstance(raw_result, dict) and 'assessed_links' in raw_result:
                    try:
                        structured_data = LinkAssessmentOutput(**raw_result)
                        print("[AI DEBUG] Successfully parsed raw dictionary into LinkAssessmentOutput")
                    except Exception as parse_error:
                        print(f"[AI WARNING] Failed to manually parse into LinkAssessmentOutput: {parse_error}")

            # Initialize assessment results for all nodes
            assessment_results = {node.url: {"should_traverse": False, "rank": 999} for node in candidate_nodes}

            if structured_data and hasattr(structured_data, 'assessed_links'):
                print("[AI DEBUG] Assessed links from AI:")
                # Update results based on AI assessment
                for la in structured_data.assessed_links:
                    if la.url in assessment_results:
                        assessment_results[la.url]["should_traverse"] = la.should_traverse
                        assessment_results[la.url]["rank"] = la.rank
                        assessment_results[la.url]["reason"] = la.reason

                # Filter links marked should_traverse=True and sort by rank
                relevant_links_data = [
                    (url, data)
                    for url, data in assessment_results.items()
                    if data["should_traverse"]
                ]
                ranked_relevant_data = sorted(relevant_links_data, key=lambda x: x[1]["rank"])

                # Select the top_k from the relevant and ranked list
                selected_urls = set(url for url, data in ranked_relevant_data[:self.top_k])

                # Print the full assessment and decision for debugging
                print("[AI DEBUG] Final Assessment & Decision:")
                for node in candidate_nodes:
                    url = node.url
                    assessed_data = assessment_results.get(url)
                    if assessed_data:
                        ai_traversed = assessed_data["should_traverse"]
                        ai_rank = assessed_data["rank"]
                        ai_reason = assessed_data.get("reason")
                        final_decision = "TRAVERSE" if url in selected_urls else ("IGNORE (Marked False)" if not ai_traversed else "IGNORE (Low Rank)")
                        print(f"  - URL: {url} | AI Traverse: {ai_traversed} | AI Rank: {ai_rank} | Reason: {ai_reason} | Decision: {final_decision}")
                    else:
                        # This case shouldn't happen with the current logic, but for safety:
                        print(f"  - URL: {url} | Decision: IGNORE (Not Assessed)")
                        node.should_traverse = False
                
                # Set should_traverse on the actual Node objects
                for node in candidate_nodes:
                    node.should_traverse = node.url in selected_urls

                if structured_data.model_notes:
                    print(f"[AI DEBUG] Model notes: {structured_data.model_notes}")
                notes = (structured_data.model_notes or "").lower()
                # Consider it complete if no relevant links were chosen or model says complete
                if "complete" in notes or "finished" in notes or not selected_urls:
                    return "COMPLETE"
                return "SEARCHING"
            else:
                print("[AI WARNING] Model output did not contain valid structured_output. Setting all assessed links to True for traversal (up to top_k), others False.")
                # Fallback: traverse top_k of the assessed links
                selected_urls = set(url for url in candidate_links_urls[:self.top_k])
                for node in candidate_nodes:
                    node.should_traverse = node.url in selected_urls
                return "SEARCHING"
        except Exception as e:
            print(f"AI model selection failed: {e}")
            traceback.print_exc()
            # Fallback: traverse top_k of the assessed links
            selected_urls = set(url for url in candidate_links_urls[:self.top_k])
            for node in candidate_nodes:
                node.should_traverse = node.url in selected_urls
            return "SEARCHING"


