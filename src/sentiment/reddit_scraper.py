import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import time

from ..config import Settings
from ..utils.exceptions import DataError


logger = logging.getLogger(__name__)


class RedditScraper:
    """Scrapes market sentiment from Reddit"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.headers = {
            'User-Agent': 'SCRAP3R/1.0 (Market Sentiment Bot)'
        }
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
    def scrape_subreddit(self, subreddit: str = 'wallstreetbets', 
                        sort: str = 'hot', 
                        limit: int = 100) -> List[Dict]:
        """Scrape posts from a subreddit with retry logic"""
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params = {'limit': limit}
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=10
                )
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Reddit rate limit hit. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                    
                response.raise_for_status()
                
                # Parse JSON
                data = response.json()
                
                # Validate response structure
                if 'data' not in data or 'children' not in data['data']:
                    logger.error(f"Unexpected Reddit response structure: {data.keys()}")
                    return []
                    
                posts = []
                
                for post in data['data']['children']:
                    if 'data' not in post:
                        continue
                        
                    post_data = post['data']
                    
                    # Filter posts from last N hours
                    try:
                        post_time = datetime.fromtimestamp(post_data['created_utc'])
                        time_diff = datetime.now() - post_time
                        
                        if time_diff <= timedelta(hours=self.settings.sentiment.analysis_window_hours):
                            posts.append({
                                'title': post_data.get('title', ''),
                                'text': post_data.get('selftext', ''),
                                'score': post_data.get('score', 0),
                                'num_comments': post_data.get('num_comments', 0),
                                'created_utc': post_data.get('created_utc', 0),
                                'author': post_data.get('author', '[deleted]'),
                                'id': post_data.get('id', '')
                            })
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Skipping malformed post: {e}")
                        continue
                        
                logger.info(f"Successfully scraped {len(posts)} posts from r/{subreddit}")
                return posts
                
            except requests.exceptions.Timeout:
                logger.error(f"Reddit request timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Reddit request error: {e} (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Reddit response: {e}")
                return []
                
            except Exception as e:
                logger.error(f"Unexpected error scraping Reddit: {e}")
                return []
                
        # All retries failed
        logger.error(f"Failed to scrape Reddit after {self.max_retries} attempts")
        return []
            
    def scrape_comments(self, post_id: str, subreddit: str = 'wallstreetbets', 
                       limit: int = 50) -> List[Dict]:
        """Scrape comments from a specific post"""
        if not post_id:
            return []
            
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        params = {'limit': limit}
        
        try:
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params, 
                timeout=10
            )
            
            if response.status_code == 429:
                logger.warning("Rate limited on comments, skipping...")
                return []
                
            response.raise_for_status()
            
            data = response.json()
            comments = []
            
            # The second element contains the comments
            if len(data) > 1 and isinstance(data[1], dict):
                if 'data' in data[1] and 'children' in data[1]['data']:
                    comment_data = data[1]['data']['children']
                    
                    for comment in comment_data:
                        if comment.get('kind') == 't1' and 'data' in comment:
                            comment_info = comment['data']
                            comments.append({
                                'text': comment_info.get('body', ''),
                                'score': comment_info.get('score', 0),
                                'created_utc': comment_info.get('created_utc', 0),
                                'author': comment_info.get('author', '[deleted]')
                            })
                            
            return comments
            
        except Exception as e:
            # Don't crash on comment errors - they're less critical
            logger.debug(f"Error scraping comments for post {post_id}: {e}")
            return []
            
    def get_market_chatter(self) -> List[str]:
        """Get all market-related text from Reddit"""
        texts = []
        
        try:
            # Scrape posts
            posts = self.scrape_subreddit(
                subreddit='wallstreetbets',
                sort='hot',
                limit=self.settings.sentiment.reddit_limit
            )
            
            if not posts:
                logger.warning("No posts retrieved from Reddit")
                # Don't raise error - let system use default symbols
                return texts
                
            for post in posts:
                # Add post title and text
                if post['title']:
                    texts.append(post['title'])
                if post['text']:
                    texts.append(post['text'])
                    
                # Scrape top comments for popular posts
                if post['score'] > 100 or post['num_comments'] > 50:
                    comments = self.scrape_comments(
                        post['id'], 
                        subreddit='wallstreetbets'
                    )
                    for comment in comments[:10]:  # Top 10 comments
                        if comment['score'] > 5 and comment['text']:
                            texts.append(comment['text'])
                            
            logger.info(f"Collected {len(texts)} text samples from Reddit")
            return texts
            
        except Exception as e:
            logger.error(f"Failed to get market chatter: {e}")
            # Return empty list instead of crashing
            return texts