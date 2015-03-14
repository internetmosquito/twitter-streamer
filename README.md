# twitter-streamer
An example project that shows how to get all tweets from a specific user using the Streaming API and Tweepy.

It uses a Flask app to get the access token from the user we want to get tweets from and a Puller (puller.py) that gets 
data from Twitter once credentials are stored in credentials.txt

Incoming tweets are stored in a mongoDB database, using 2 collection. 

There is view /messages that will show all tweets from past 7 days stored in the db. 

I made this so other people could reuse it, it was kinda hard to find proper documentation on how to do this. 

Requirements
************

* Flask 0.10.1
* Jinja 2.7.3
* Tweepy 0.1.2
* Pymongo 2.8

You'll need to have mongoDB up and running in your test machine

Flask is used to handle callback methods while having the Oauth dance with Twitter and also to show incoming messages from the account that allows this app to get tweets from the timeline

Thus, you'll basically need to follow this steps to make this work:

1.- Go to dev.twitter.com and create your Twitter application
2.- You will then need to copy your application token and secret and put it in app.py and puller.py

```
CONSUMER_TOKEN = 'your_app_token'
CONSUMER_SECRET = 'your_app_secret'
```
3.- You'll need to specify the callback URL to finish the verification process. I recommend using something like ngrok if you're working locally, it will let you tweak Twitter to think your dev machine is a real server.

```
CALLBACK_URL = 'your_callback_url/verify'
```

3.- Install mongoDB or specify where your mongoDB server is at app.py and puller.py

4.- All the pulling logic can be done with puller.py, but if you haven't authenticated the user yet and there is no credentials file, you'll need to start the 
    Flask app in order to perform the oAuth dance, just go to / and if there is no credentials file you should be re-directed to Twitter 

4.- Fire up the app and then go to http://localhost:5000 (if you use the embedded Flask server), this will start the verification process, unless you already had an access token/secret stored in the credentials.txt file. If successfull, you'll be redirected to http://localhost:5000/messages, which is just a landing page that, well, does nothing.

5.- In order to see incoming messages, go to http://localhost:5000/messages, there is a table that will be filled with incoming messages from the user account that authorized the app (last 7 days of stored tweets)

Overall the code can be surely improved, so feel free to fork and do as you please, just let me know how it goes :)

