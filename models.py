__author__ = 'mosquito'


class Message():

    def __init__(self, creation_time, author, lists, text, retweet_count, media):
        self.creation_time = creation_time
        self.author = author
        self.lists = lists
        self.text = text
        self.retweet_count = retweet_count
        self.media = media

    def __repr__(self):
        return '<text %r>' % (self.text)

