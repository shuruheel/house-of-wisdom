import json
import os
from datetime import datetime, timedelta
import time
from newsapi import NewsApiClient
from api_wrapper import get_api
import logging
import asyncio
import hashlib

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class NewsEventGenerator:
    def __init__(self, provider="google", model="gemini-1.5-pro-exp-0827", temperature=0.2):
        self.api = get_api(provider, model, temperature)
        self.newsapi = NewsApiClient(api_key=os.getenv('NEWSAPI_KEY'))
        self.template = self.load_template()
        self.checkpoint_dir = "checkpoints"
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.processed_articles = self.load_processed_articles()

    def load_template(self):
        with open('prompts/_event_template.txt', 'r') as file:
            return file.read()

    def load_processed_articles(self):
        try:
            with open('processed_articles.json', 'r') as f:
                return set(json.load(f))
        except FileNotFoundError:
            return set()

    def save_processed_articles(self):
        with open('processed_articles.json', 'w') as f:
            json.dump(list(self.processed_articles), f)

    def get_article_hash(self, article):
        # Create a unique hash for the article based on its title and publication date
        return hashlib.md5(f"{article['title']}_{article['publishedAt']}".encode()).hexdigest()

    def fetch_news(self):
        queries = [
            ('United States OR Israel OR China OR Russia OR Ukraine OR Turkey OR Pakistan OR India OR '
             'Hezbollah OR Hamas OR Houthi OR Iran OR Palestine OR Saudi Arabia OR Afghanistan OR '
             'Taliban OR Imran Khan OR Yemen OR Syria OR Taiwan OR Philippines OR South Korea OR North Korea'),
            ('Lebanon OR Canada OR Mexico OR New York OR San Francisco OR Washington OR '
             'South China Sea OR West Bank OR Climate Change OR Elections OR Coup OR Protest OR Invention OR '
             'Artificial Intelligence OR Jihad OR AI Drones OR AI Weapons OR Consciousness OR Discovery OR '
             'General Relativity OR Quantum Mechanics OR Neuroscience OR Justice OR NATO OR EU OR European Union'),
            ('Cybersecurity OR Pandemic OR Vaccine OR Inflation OR Supply Chain OR Semiconductor OR Renewable OR '
             'Space Exploration OR Hypersonic OR Quantum Computing OR Autonomous Vehicles OR Trade War OR '
             'Nuclear Proliferation OR Refugee Crisis OR Rare Earth Minerals OR Water Scarcity OR Water Shortage OR '
             'Drought OR Flood OR Earthquake OR Hurricane OR Typhoon OR Tornado OR Tsunami OR Volcano OR Terror OR '
             'Arctic OR Biodiversity')
        ]
        
        sources = 'abc-news,cbs-news,bbc-news,al-jazeera-english'
        
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=24)
        
        from_date = start_date.strftime('%Y-%m-%dT%H:%M:%S')
        to_date = end_date.strftime('%Y-%m-%dT%H:%M:%S')
        
        all_articles = []
        
        for query in queries:
            try:
                articles = self.newsapi.get_everything(q=query,
                                                       sources=sources,
                                                       from_param=from_date,
                                                       to=to_date,
                                                       language='en',
                                                       sort_by='relevancy')
                
                if 'articles' in articles:
                    all_articles.extend(articles['articles'])
                    logger.info(f"Fetched {len(articles['articles'])} articles for query part")
                else:
                    logger.error(f"No 'articles' key in NewsAPI response: {articles}")
            except Exception as e:
                logger.error(f"Error fetching news for query part: {str(e)}")
        
        logger.info(f"Fetched a total of {len(all_articles)} articles")
        return all_articles

    async def process_articles(self, articles):
        all_data = {"stories": [], "events": [], "entities": [], "concepts": [], "concept_relationships": []}
        
        # Filter out already processed articles
        new_articles = [article for article in articles if self.get_article_hash(article) not in self.processed_articles]
        logger.info(f"Found {len(new_articles)} new articles out of {len(articles)} total")

        # Process articles in batches of 7
        for i in range(0, len(new_articles), 7):
            batch = new_articles[i:i+7]
            logger.info(f"Processing batch {i//7 + 1} of {(len(new_articles) + 6)//7}")
            batch_data = await self.process_batch(batch)
            for key in all_data:
                all_data[key].extend(batch_data.get(key, []))
            
            # Mark articles as processed
            for article in batch:
                self.processed_articles.add(self.get_article_hash(article))
        
        self.save_processed_articles()
        return all_data

    async def process_batch(self, batch):
        simplified_batch = []
        for article in batch:
            simplified_article = {
                'source': article.get('source', {}),
                'author': article.get('author'),
                'title': article.get('title'),
                'description': article.get('description'),
                'publishedAt': article.get('publishedAt'),
                'content': article.get('content')
            }
            simplified_batch.append(simplified_article)

        prompt = self.template + "\n\n"
        for article in simplified_batch:
            prompt += json.dumps(article, indent=2) + "\n\n"
        prompt += f"Please transform these {len(simplified_batch)} news articles into the required JSON format, focusing on significant events with impact on international relations or global conflicts."

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response_generator = self.api.generate_text(prompt)
                response = await self.get_full_response(response_generator)
                parsed_data = self.parse_response(response)
                if any(parsed_data.values()):  # Check if any data was successfully parsed
                    return parsed_data
                else:
                    logger.warning(f"Attempt {attempt + 1}: No valid data parsed. Retrying...")
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(5)  # Wait 5 seconds before retrying
        
        logger.error(f"Failed to process batch after {max_retries} attempts")
        return {"stories": [], "events": [], "entities": [], "concepts": [], "concept_relationships": []}

    async def get_full_response(self, response_generator):
        full_response = ""
        async for chunk in response_generator:
            full_response += chunk
        return full_response

    def parse_response(self, response):
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            
            data = json.loads(json_str)
            
            required_keys = ['stories', 'events', 'entities', 'concepts']
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                logger.warning(f"Missing required keys: {', '.join(missing_keys)}")
                # Initialize missing keys with empty lists
                for key in missing_keys:
                    data[key] = []
            
            # Ensure all required keys exist, even if empty
            for key in required_keys:
                if key not in data:
                    data[key] = []
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {str(e)}")
            # Attempt to salvage partial data
            partial_data = self.extract_partial_data(json_str)
            if partial_data:
                return partial_data
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
        
        # Return empty data structure if all else fails
        return {"stories": [], "events": [], "entities": [], "concepts": [], "concept_relationships": []}

    def extract_partial_data(self, json_str):
        # Attempt to extract partial data from malformed JSON
        partial_data = {"stories": [], "events": [], "entities": [], "concepts": [], "concept_relationships": []}
        try:
            # Use regex to find lists of objects
            import re
            for key in partial_data.keys():
                pattern = f'"{key}":\\s*\\[(.*?)\\]'
                match = re.search(pattern, json_str, re.DOTALL)
                if match:
                    items = json.loads(f"[{match.group(1)}]")
                    partial_data[key] = items
            return partial_data
        except:
            return None

    def save_events(self, data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"news_events/news_events_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(data.get('events', []))} events to {filename}")

async def main():
    generator = NewsEventGenerator()
    
    logger.info("Fetching news articles")
    start_time = time.time()
    articles = generator.fetch_news()
    fetch_time = time.time() - start_time
    
    logger.info(f"Fetched {len(articles)} articles in {fetch_time:.2f} seconds")
    logger.info(f"Processing {len(articles)} articles")
    
    start_time = time.time()
    data = await generator.process_articles(articles)
    process_time = time.time() - start_time
    
    logger.info(f"Processed {len(articles)} articles in {process_time:.2f} seconds")
    
    generator.save_events(data)

    total_time = fetch_time + process_time
    logger.info(f"Total execution time: {total_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())