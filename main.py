__author__ = 'mosquito'
import tweepy
from flask import Flask
from flask import request
from models import Message
from threading import Lock
import flask
import json
import os


CONSUMER_TOKEN = 'your_app_token'
CONSUMER_SECRET = 'your_app_secret'
CALLBACK_URL = 'your_callback_url/verify'
FILENAME = 'credentials.txt'

app = Flask(__name__)
session = dict()
db = dict() #you can save these values to a database
tweets = []
lock = Lock()


@app.route("/")
def send_token():
    #Check if we have credentials stored, if so, load them
    if os.path.isfile(FILENAME):
        credentials = json.load(open("credentials.txt"))
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET)
        key = credentials['access_token_key']
        secret = credentials['access_token_secret']
        auth.set_access_token(key, secret)
        #now you have access!
        api = tweepy.API(auth)
        db['api'] = api
        l = StreamListener()
        streamer = tweepy.Stream(auth=auth, listener=l)
        #streamer.filter(follow=['3071126254'])
        streamer.userstream(_with='followings', async=True)
        return flask.redirect('/donothing')
    else:
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET, CALLBACK_URL)
        try:
            #get the request tokens
            redirect_url= auth.get_authorization_url()
            request_token = auth.request_token['oauth_token']
            request_secret = auth.request_token['oauth_token_secret']
            session['request_token'] = (request_token, request_secret)
            #session.set('request_token', auth.request_token)
        except tweepy.TweepError:
            print 'Error! Failed to get request token'
        #this is twitter's url for authentication
        return flask.redirect(redirect_url)

@app.route("/donothing")
def do_nothing():
    return flask.render_template('template.html')

@app.route("/verify")
def get_verification():
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
        auth.get_access_token(verifier)
    except Exception, e:
        print 'Error! Failed to get access token.'

    #save the api object reference for future use
    api = tweepy.API(auth)
    db['api'] = api
    saved_credentials = dict()
    saved_credentials['access_token_key'] = auth.access_token
    saved_credentials['access_token_secret'] = auth.access_token_secret

    #store access token in file for further use
    json.dump(saved_credentials, open(FILENAME, 'w'))

    return flask.redirect(flask.url_for('start'))

@app.route("/messages")
def start():
    return flask.render_template('tweets.html', messages=tweets)

class StreamListener(tweepy.StreamListener):
    def on_status(self, tweet):
        print 'Ran on_status'

    def on_error(self, status_code):
        print 'Error: ' + repr(status_code)
        return False

    def on_data(self, data):
        payload = json.loads(data)
        media_url = ''
        with lock:
            if 'text' in payload.keys():
                if 'extended_entities' in payload:
                    if len(payload['extended_entities']['media']) > 0:
                        if 'media_url' in payload['extended_entities']['media'][0]:
                            media_url = payload['extended_entities']['media'][0]['media_url']

                tweet = Message(payload['created_at'],
                                payload['user']['name'],
                                payload['text'],
                                payload['retweet_count'],
                                media_url)
                tweets.append(tweet)
            print payload
            print len(tweets)
