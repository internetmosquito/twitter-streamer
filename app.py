__author__ = 'mosquito'
import tweepy
from tweepy import TweepError
from flask import Flask, request
from models import Message
from threading import Lock
import flask
import json
import os
import sys
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging
from logging import Formatter, FileHandler
from datetime import datetime, timedelta

CONSUMER_TOKEN = 'your_app_token'
CONSUMER_SECRET = 'your_app_secret'
CALLBACK_URL = 'http://your-server-ip-or-ngrok/verify'
FILENAME = 'credentials.txt'
MONGO_HOST = 'localhost'
MONGO_PORT = 27017


app = Flask(__name__)
#Setup the logger
LOGGER = logging.getLogger('streamer_logger')
file_handler = FileHandler('streamer.log')
handler = logging.StreamHandler()
file_handler.setFormatter(Formatter(
        '%(thread)d %(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
))
handler.setFormatter(Formatter(
        '%(thread)d %(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
))
LOGGER.addHandler(file_handler)
LOGGER.addHandler(handler)
LOGGER.setLevel(logging.DEBUG)
#Try to connect to MongoDB
try:
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    db = client.testdb
    tweet_collection = db.streamed_tweets
    lists_collection = db.user_lists
except ConnectionFailure:
    LOGGER.error('Could not connect to MongoDB, aborting Flask app...')
    sys.exit(-1)

session = dict()
cache = dict()
tweets = []
lock = Lock()
users_lists = dict()

@app.route('/shutdown')
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

@app.route("/")
def root():
    #Check if we have credentials stored, if so, load them
    if os.path.isfile(FILENAME):
        LOGGER.info('Getting credentials from stored file...')
        credentials = json.load(open("credentials.txt"))
        LOGGER.debug('Getting token from tweepy')
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET)
        key = credentials['access_token_key']
        secret = credentials['access_token_secret']
        auth.set_access_token(key, secret)
        LOGGER.debug('Got token from Twitter!')
        #now you have access!
        api = tweepy.API(auth)
        cache['api'] = api
        return flask.redirect('/messages')
    else:
        LOGGER.info('No credentials found, need to perform the oAuth dance...')
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET, CALLBACK_URL)
        try:
            #get the request tokens
            redirect_url= auth.get_authorization_url()
            request_token = auth.request_token['oauth_token']
            request_secret = auth.request_token['oauth_token_secret']
            session['request_token'] = (request_token, request_secret)
            #session.set('request_token', auth.request_token)
        except tweepy.TweepError:
            LOGGER.error('Error! Failed to get request token. Shutting down')
            return flask.redirect('/shutdown')
        #this is twitter's url for authentication
        return flask.redirect(redirect_url)


@app.route("/verify")
def get_verification():
    #Check if the request is coming from Twitter
    if 'oauth_verifier' in request.args:
        #get the verifier key from the request url
        verifier = request.args['oauth_verifier']
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET)
        new_dict = dict()
        new_dict['oauth_token'] = session['request_token'][0]
        new_dict['oauth_token_secret'] = session['request_token'][1]
        del session['request_token']
        auth.request_token = new_dict
        #auth.set_request_token(token[0], token[1])
        try:
            LOGGER.info('Trying to get the access token...')
            auth.get_access_token(verifier)
        except TweepError:
            LOGGER.error('Error! Failed to get access token. Shuting down')
            return flask.redirect('/shutdown')

        #save the api object reference for future use
        api = tweepy.API(auth)
        cache['api'] = api
        saved_credentials = dict()
        saved_credentials['access_token_key'] = auth.access_token
        saved_credentials['access_token_secret'] = auth.access_token_secret

        #store access token in file for further use
        json.dump(saved_credentials, open(FILENAME, 'w'))

        return flask.redirect('/')
    else:
        LOGGER.error('Incoming request to verify endpoint does not seem to be a legit Twitter request')
        return 'Incoming request to verify endpoint does not seem to be a legit Twitter request'

@app.route("/messages")
def get_messages():
    #get all message from last week
    tweets = []
    now = datetime.now()
    past_week = now.today() - timedelta(days=7)
    tweets_stored = tweet_collection.find({'datetime': {'$gte': past_week, '$lt': now}})\
                                    .sort('datetime', pymongo.ASCENDING)
    for tweet in tweets_stored:
        media_url = ''
        if 'extended_entities' in tweet:
                    if len(tweet['extended_entities']['media']) > 0:
                        if 'media_url' in tweet['extended_entities']['media'][0]:
                            media_url = tweet['extended_entities']['media'][0]['media_url']
        tweet = Message(tweet['datetime'],
                        tweet['user']['name'],
                        tweet['user']['lists'],
                        tweet['text'],
                        tweet['retweeted_status']['retweet_count'],
                        media_url)
        tweets.append(tweet)
    return flask.render_template('tweets.html', messages=tweets)


def shutdown_server():
    #This only works if the Werkzeug server is the one running the Flask app
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


if __name__ == '__main__':
    app.run()
