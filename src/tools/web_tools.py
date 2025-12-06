
import os
from typing import Optional, List, Set, Dict, Tuple
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from langchain_core.tools import tool
import requests

def _duckduckgo_search(query: str) -> List[Dict[str, str]]:
    """
    Performs a search on DuckDuckGo's HTML version and parses the results.
    Returns a list of dictionaries, each containing 'title', 'link', and 'snippet'.
    """
    search_url = f"https://duckduckgo.com/html/?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ReactorAgent/1.0; +https://tensorify.io)'}
    results = []

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # DuckDuckGo HTML search results structure
        # Each result is typically within a div with class 'result'
        for result_div in soup.find_all('div', class_='result'):
            title_tag = result_div.find('a', class_='result__a')
            snippet_tag = result_div.find('a', class_='result__snippet')
            link_tag = result_div.find('a', class_='result__url') # This might be the actual URL

            title = title_tag.get_text(strip=True) if title_tag else 'No Title'
            link = link_tag['href'] if link_tag and 'href' in link_tag.attrs else (title_tag['href'] if title_tag and 'href' in title_tag.attrs else 'No Link')
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else 'No Snippet'
            
            # Clean up DuckDuckGo's redirect links if necessary
            if link.startswith('/l/?kh=-1&uddg='):
                link = requests.utils.unquote(link.split('uddg=')[1])
            
            results.append({
                'title': title,
                'link': link,
                'snippet': snippet
            })
            if len(results) >= 5: # Limit to top 5 results
                break

    except requests.exceptions.RequestException as e:
        print(f"Error during DuckDuckGo search for '{query}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred during parsing DuckDuckGo results: {e}")
    
    return results

def web_search(query: str) -> str:
    """
    Searches the web for the given query using DuckDuckGo and returns a summary of results.
    """
    search_results = _duckduckgo_search(query)
    
    if not search_results:
        return f"No relevant search results found for '{query}'."
    
    formatted_results = []
    for i, result in enumerate(search_results):
        formatted_results.append(f"Result {i+1}:")
        formatted_results.append(f"  Title: {result.get('title', 'N/A')}")
        formatted_results.append(f"  Link: {result.get('link', 'N/A')}")
        formatted_results.append(f"  Snippet: {result.get('snippet', 'N/A')}")
        formatted_results.append("") # Add a blank line for readability
        
    return "\n".join(formatted_results)

def fetch_page(url: str) -> Optional[str]:
    """
    Fetches the content of a given URL.
    Returns the HTML content as a string, or None if an error occurs.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; ReactorAgent/1.0; +https://tensorify.io)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_links(html_content: str, base_url: str) -> Set[str]:
    """
    Parses HTML content and extracts all unique, absolute URLs.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    links = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        absolute_url = urljoin(base_url, href)
        
        # Basic validation for HTTP/HTTPS links
        parsed_url = urlparse(absolute_url)
        if parsed_url.scheme in ['http', 'https']:
            links.add(absolute_url)
    return links
def extract_text_from_html(html_content: str, max_chars: int = 5000) -> str:
    """
    Extract clean text content from HTML, removing scripts, styles, and tags.
    
    Args:
        html_content: Raw HTML content
        max_chars: Maximum characters to return
    
    Returns:
        Clean text content
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(['script', 'style', 'nav', 'header', 'footer']):
        script.decompose()
    
    # Get text
    text = soup.get_text(separator='\n', strip=True)
    
    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = '\n'.join(lines)
    
    # Truncate if needed
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n... [Truncated {len(text) - max_chars} chars]"
    
    return text


@tool
async def recursive_crawl(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 5,
    max_content_per_page: int = 5000
) -> Dict:
    """
    Recursively crawl a website starting from a URL.
    
    Args:
        start_url: Starting URL to crawl
        max_depth: Maximum depth to crawl (default: 2)
        max_pages: Maximum number of pages to fetch (default: 5)
        max_content_per_page: Max chars of text per page (default: 5000)
    
    Returns:
        Dictionary with crawled pages and their text content (not HTML)
    """
    visited_urls: Set[str] = set()
    urls_to_visit: List[Tuple[str, int]] = [(start_url, 0)] # (url, depth)
    crawled_data: Dict[str, str] = {}

    while urls_to_visit and len(crawled_data) < max_pages:
        current_url, current_depth = urls_to_visit.pop(0)

        if current_url in visited_urls or current_depth > max_depth:
            continue

        print(f"Crawling: {current_url} (Depth: {current_depth})")
        html_content = fetch_page(current_url)
        visited_urls.add(current_url)

        if html_content:
            # Extract clean text instead of storing raw HTML (huge token savings!)
            clean_text = extract_text_from_html(html_content, max_content_per_page)
            crawled_data[current_url] = clean_text
            
            if current_depth < max_depth:
                new_links = extract_links(html_content, current_url)
                for link in new_links:
                    if link not in visited_urls:
                        urls_to_visit.append((link, current_depth + 1))
    
    return crawled_data

