__author__ = 'mosquito'
import tweepy
import json
import os
import sys
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ConnectionFailure
import logging
from logging import Formatter, FileHandler
import time
from datetime import datetime

CONSUMER_TOKEN = 'your_app_token'
CONSUMER_SECRET = 'your_app_secret'
CREDENTIALS_FILENAME = 'credentials.txt'
MONGO_HOST = 'localhost'
MONGO_PORT = 27017


#Setup the logger
LOGGER = logging.getLogger('twitter_puller')
file_handler = FileHandler('twitter_puller.log')
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
    LOGGER.error('Could not connect to MongoDB, aborting Puller app...')
    sys.exit(-1)

session = dict()
cache = dict()
tweets = []


class StreamListener(tweepy.StreamListener):
    def on_status(self, tweet):
        LOGGER.info('Got status from streaming Twitter API!')

    def on_error(self, status_code):
        LOGGER.error('An error returned from Twitter API. Error code is ' + str(status_code))
        return False

    def on_data(self, data):
        payload = json.loads(data)
        #Check if the incoming tweet has the text field, which means it is a valid tweet for storing
        if 'text' in payload.keys():
            #Try to add the document in the collection
            try:
                users_lists = get_lists_from_user(payload['user']['id'])
                #Get the time as String and convert it to a real datetime
                date_str = payload['created_at']
                #Takes the string (date_str) and converts it to datetime
                time_struct = time.strptime(date_str, "%a %b %d %H:%M:%S +0000 %Y")
                date_datetime = datetime.fromtimestamp(time.mktime(time_struct))
                payload['datetime'] = date_datetime
                payload['user']['lists'] = users_lists
                tweet_collection.insert(payload)
                LOGGER.info('Got message from streaming Twitter API!')
            except OperationFailure:
                LOGGER.error('An error occured trying to insert document into collection')


def start_puller():
    '''
    Checks if we have stored credentials and if so, starts the Tweepy Streamer for the authenticated user
    '''
    #Check if we have credentials stored, if so, load them
    if os.path.isfile(CREDENTIALS_FILENAME):
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
        #Check if we need to get the users list
        LOGGER.debug('Getting user lists from Twitter....')
        get_lists()
        LOGGER.debug('Got user lists from Twitter')
        #Create and start the streamer
        l = StreamListener()
        streamer = tweepy.Stream(auth=auth, listener=l)
        #streamer.filter(follow=['3071126254'])
        LOGGER.info('Starting the streamer...')
        streamer.userstream(_with='followings', async=True)
    else:
        LOGGER.error('No credentials found, cannot start the puller, consider using Flask app to authorize app')
        sys.exit(-1)


def get_lists():
    '''
    Gets the lists for the authenticated users with all the users in each list and stores it in mongo
    :rtype : list
    :return: A list of List objects with a new field 'members' that has all the users found for that list
    '''
    #delete the existing documents in lists collection
    LOGGER.debug('Removing previous version of lists from user...')
    lists_collection.remove({})
    LOGGER.debug('Removed previous version of lists from user')
    api = cache['api']
    obtained_lists = list()
    LOGGER.debug('Querying API for users lists...')
    lists = api.lists_all()
    if len(lists) > 0:
        LOGGER.debug('Obtained lists from Twitter...')
        #Get the users each list have
        for current_list in lists:
            LOGGER.debug('Querying API for members of list...')
            members = api.list_members(list_id=current_list.id)
            aux_list = dict()
            aux_list['id'] = current_list.id
            aux_list['created_at'] = current_list.created_at
            aux_list['description'] = current_list.description
            aux_list['full_name'] = current_list.full_name
            aux_list['name'] = current_list.name
            aux_list['mode'] = current_list.mode
            aux_list['slug'] = current_list.slug
            aux_list['subscriber_count'] = current_list.subscriber_count
            aux_list['uri'] = current_list.uri
            aux_list['owner_id'] = current_list.user.id
            if len(members) > 0:
                #Add the list of members to the list dict and save it to mongo
                aux_members = list()
                for member in members:
                    aux_members.append(member.id)
                aux_list['members'] = aux_members
                obtained_lists.append(aux_list)
                lists_collection.insert(aux_list)
    return obtained_lists


def get_lists_from_user(user_id):
    '''
    Iterates all lists of the authenticated user and gets the list the specified user is member of
    :user_id: The user ID to be used for searching
    :rtype : dict
    :return: A list, where each entry is the list name
    '''
    lists_from_user = list()
    if lists_collection.count() <= 0:
        lists = get_lists()
    else:
        lists = lists_collection.find()

    for current_list in lists:
        #Get the members
        members = current_list['members']
        list_name = current_list['name']
        for member in members:
            if member == user_id:
                lists_from_user.append(list_name)
    return lists_from_user

if __name__ == '__main__':
    start_puller()
