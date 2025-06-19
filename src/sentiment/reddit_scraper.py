import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from ..config import Settings


logger = logging.getLogger(__name__)


class RedditScraper:
    """Scrapes market sentiment from Reddit"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.headers = {
            'User-Agent': 'SCRAP3R/1.0 (Market Sentiment Bot)'
        }
        
    def scrape_subreddit(self, subreddit: str = 'wallstreetbets', 
                        sort: str = 'hot', 
                        limit: int = 100) -> List[Dict]:
        """Scrape posts from a subreddit"""
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
        params = {'limit': limit}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            posts = []
            
            for post in data['data']['children']:
                post_data = post['data']
                
                # Filter posts from last N hours
                post_time = datetime.fromtimestamp(post_data['created_utc'])
                time_diff = datetime.now() - post_time
                
                if time_diff <= timedelta(hours=self.settings.sentiment.analysis_window_hours):
                    posts.append({
                        'title': post_data['title'],
                        'text': post_data.get('selftext', ''),
                        'score': post_data['score'],
                        'num_comments': post_data['num_comments'],
                        'created_utc': post_data['created_utc'],
                        'author': post_data['author'],
                        'id': post_data['id']
                    })
                    
            logger.info(f"Scraped {len(posts)} posts from r/{subreddit}")
            return posts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping Reddit: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Reddit response: {e}")
            return []
            
    def scrape_comments(self, post_id: str, subreddit: str = 'wallstreetbets', 
                       limit: int = 50) -> List[Dict]:
        """Scrape comments from a specific post"""
        url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        params = {'limit': limit}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            comments = []
            
            # The second element contains the comments
            if len(data) > 1:
                comment_data = data[1]['data']['children']
                
                for comment in comment_data:
                    if comment['kind'] == 't1':  # t1 = comment
                        comment_info = comment['data']
                        comments.append({
                            'text': comment_info.get('body', ''),
                            'score': comment_info.get('score', 0),
                            'created_utc': comment_info.get('created_utc', 0),
                            'author': comment_info.get('author', '')
                        })
                        
            return comments
            
        except Exception as e:
            logger.error(f"Error scraping comments for post {post_id}: {e}")
            return []
            
    def get_market_chatter(self) -> List[str]:
        """Get all market-related text from Reddit"""
        texts = []
        
        # Scrape posts
        posts = self.scrape_subreddit()
        
        for post in posts:
            # Add post title and text
            texts.append(post['title'])
            if post['text']:
                texts.append(post['text'])
                
            # Scrape top comments for popular posts
            if post['score'] > 100 or post['num_comments'] > 50:
                comments = self.scrape_comments(post['id'])
                for comment in comments[:10]:  # Top 10 comments
                    if comment['score'] > 5:  # Only positive score comments
                        texts.append(comment['text'])
                        
        logger.info(f"Collected {len(texts)} text samples from Reddit")
        return texts