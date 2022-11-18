"""
Module for Twitter Bot which replies to tweets containing a mention to it, with a generated AI
drawing from DALL-E 2.
"""

import re
import time
import logging
import os
from io import BytesIO
from datetime import datetime, timedelta
from dotenv import load_dotenv
from twython import Twython
from tqdm import tqdm
from PIL import Image
import requests
import openai
import deepl


# Load DOTENV environment variables
load_dotenv(dotenv_path = '.env')

API_KEY = os.getenv('API_KEY')
API_KEY_SECRET = os.getenv('API_KEY_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Set up logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def connect_twitter(api_key, api_key_secret, access_token, access_token_secret):
    """Takes the API credentials and defines a connection object to Twitter"""

    return Twython(api_key, api_key_secret, access_token, access_token_secret)

def connect_openai(api_key):
    """Takes the API Key to connect to OpenAI and loads the models list"""

    openai.api_key = api_key
    openai.Model.list()

def get_tweets_last_5_minutes(twitter):
    """Given the connection to Twitter, it gets the tweets from last 5 minutes"""

    tweets = twitter.search(q="@aidrawit")
    date_limit = datetime.utcnow() - timedelta(minutes=5)

    tweets = [
        twt for twt in tweets.get('statuses') if datetime.strptime(
            twt.get('created_at'), '%a %b %d %H:%M:%S +0000 %Y') > date_limit
    ]

    return tweets


def get_topic(tweet, twitter):
    """Gets the topic of the image, retrieving it from the original tweet or mentioned one"""

    if tweet.get('in_reply_to_status_id'):
        mentioned_tweet = twitter.show_status(
            id=tweet.get('in_reply_to_status_id'))
        topic = mentioned_tweet.get('text')
    else:
        topic = tweet.get('text')

    return ' '.join(
        re.sub(r"(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ",
               topic).split())


def create_image(tweet, twitter):
    """
    Given the tweet and twitter connection, it calls OpenAI and generates the corresponding
    image with the topic from tweet
    """

    openai_img = openai.Image.create(prompt=get_topic(tweet, twitter),
                                     n=1,
                                     size="1024x1024")
    response = requests.get(openai_img.get('data')[0].get('url'), timeout=100)
    img = Image.open(BytesIO(response.content))
    img.save('/home/carlos/dalle2/tweet.jpg')

    return open('/home/carlos/dalle2/tweet.jpg', 'rb')


def tweet_image(tweet, img, twitter):
    """Give the image from OpenAI, it tweets replying to the tweet calling the bot"""
    response = twitter.upload_media(media=img)
    topic = get_topic(tweet, twitter)
    twitter.update_status(
        status=f'Checkout this cool image! It contains "{topic}"',
        media_ids=[response['media_id']],
        in_reply_to_status_id=tweet.get('id'),
        auto_populate_reply_metadata=True)

if __name__ == "__main__":

    tc = connect_twitter(API_KEY, API_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    connect_openai(OPENAI_API_KEY)

    logger.info('AI Draw It! Bot has been initialized.')

    while True:
        twts = get_tweets_last_5_minutes(tc)
        logger.info('Detected %s tweets. Starting to process them.', len(twts))

        for twt in tqdm(twts):
            image = create_image(twt, tc)
            tweet_image(twt, image, tc)
        logger.info('All tweets has been processed.')
        time.sleep(60 * 5)
