import requests
from bs4 import BeautifulSoup
import json
import os
import hashlib
import time

# Cache directory
CACHE_DIR = 'cache'

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

class WebSearch:
    def __init__(self):
        self.wikipedia_api_url = "https://en.wikipedia.org/w/api.php"
        self.query_cache = {}

    def make_cache_key(self, query):
        return hashlib.md5(query.encode()).hexdigest()

    def cache_results(self, query, results):
        cache_key = self.make_cache_key(query)
        with open(os.path.join(CACHE_DIR, f"{cache_key}.json"), 'w') as cache_file:
            json.dump(results, cache_file)

    def load_cached_results(self, query):
        cache_key = self.make_cache_key(query)
        try:
            with open(os.path.join(CACHE_DIR, f"{cache_key}.json"), 'r') as cache_file:
                return json.load(cache_file)
        except FileNotFoundError:
            return None

    def search_wikipedia(self, query):
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }
        response = requests.get(self.wikipedia_api_url, params=params)
        
        if response.status_code == 200:
            return response.json().get('query', {}).get('search', [])
        return []

    def scrape_website(self, url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            # Implement scraping logic based on the structure of the website content
            # Example: return [element.text for element in soup.find_all('h2')]
            return []
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []

    def fallback_search(self, query):
        # Implement a fallback search strategy, could be using another API
        print("Performing fallback search...")
        # Example: return self.scrape_website(f"http://example.com/search?q={query}")
        return []

    def rank_results(self, results):
        # Ranking logic can be based on various factors
        # This is just a placeholder for illustration
        return sorted(results, key=lambda x: len(x['title']))

    def search(self, query):
        cached_results = self.load_cached_results(query)
        if cached_results:
            print("Loaded results from cache.")
            return self.rank_results(cached_results)

        wikipedia_results = self.search_wikipedia(query)
        if not wikipedia_results:
            wikipedia_results = self.fallback_search(query)

        self.cache_results(query, wikipedia_results)
        return self.rank_results(wikipedia_results)

# Main execution
if __name__ == "__main__":
    web_search = WebSearch()
    query = input("Enter your search query: ")
    results = web_search.search(query)
    for result in results:
        print(result)
