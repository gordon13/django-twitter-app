from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from urlparse import urlparse
from datetime import datetime, timedelta
import requests
import httplib
import urllib
import base64
import socket
import json
import csv
import os

# path where the country csv lives
COUNTRY_DATA_PATH = "%s\\twitter\\data\\countries.csv"%os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# key information for the for twitter api
CONSUMER_KEY = "rgvYj8SZvBpMOpJQtdWWRjbLN"
SECRET = "FCGns4cHNfyvhhuGDLNJ1AGFCgl1ruzCpFjb4EMlElXyBSPPhj"
# token generated for the twitter api
BEAR_TOKEN = None
# time for which to hold the data in the cache
CACHE_TIME = 5 # minutes


"""
Utility classes
"""
class Cache:
	# inititialises with the current date and an empty array
	def __init__(self, max_time):
		self.last_updated = datetime.now()
		self.max_time = max_time
		self.data = None

	# returns last time cache was updated
	def need_update(self):
		difference = datetime.now() - self.last_updated
		return difference > self.max_time or self.data is None

	# force set the cache to a given dict
	def set(self, data):
		self.last_updated = datetime.now()
		self.data = data

	# get the data
	def get(self):
		return self.data

# store result of the "get tweets" function and give a time for which to hold the cache
tweet_cache = Cache( timedelta(minutes=CACHE_TIME) )
# store result of the "get country csv as dict" function and give a time for which to hold the cache
country_cache = Cache( timedelta(minutes=CACHE_TIME) )

"""
Read csv file and output dict. use caching class so we dont read the file too often
"""
def read_country_csv_as_dict():
	# check if cache needs updating
	if country_cache.need_update:
		# open the csv file
		with open(COUNTRY_DATA_PATH, "r") as file:
			_countries_dict = {}
			for row in csv.DictReader(file):
				# make sure type of row is dict otherwise it will break
				if type( row) is dict:
					# get the lng and lat of the country
					lng = row["lng"] 
					lat = row["lat"]
					# build new dict with the information from the csv file
					_countries_dict[row['code']] = {
						"name":row['name'].decode('utf-8'), 
						"lng": lng, 
						"lat": lat
					}
			return _countries_dict
	else:
		# get the existing data and return it if the cache needs to be updated
		return country_cache.get()

"""
Used for authentication with Twitter API
"""
def generate_key():
	return base64.b64encode("%s:%s"%(CONSUMER_KEY,SECRET))

def authenticate():
	# generate key from the various other keys
	_final_key = generate_key()
	# setup required headers for twitter API
	headers = {
		"Authorization":"Basic %s"%_final_key,
		"Content-Type":"application/x-www-form-urlencoded;charset=UTF-8"
	}
	r = requests.post("https://api.twitter.com/oauth2/token", data="grant_type=client_credentials", headers=headers) 
	return r.json()

"""
Get a number of tweets using hte api. use the cache class again to ensure we dont cal the api too often
@n: number of tweets to get
"""
def get_tweets(n):
	# authenticate
	_bearer_token = authenticate()

	# setup required headers for twitter API
	headers = {
		"Authorization": "Bearer %s"%_bearer_token['access_token']
	}
	# request MapleCroftRisk timeline
	if (tweet_cache.need_update()):
		r = requests.get('https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=MaplecroftRisk&count=%s'%n, headers=headers)
		tweet_cache.set(r)
	else:
		r = tweet_cache.get()
	return r.json()

"""
get references to countries in the tweet text
"""
def find_country_tags(string):
	tags = []
	# get country data. use cache class for performance
	data = read_country_csv_as_dict()
	# create lists of the country codes and names
	country_codes = data.keys()
	country_names = [data[key]['name'] for key in data.keys()]
	# strip all characters that might cause us issues
	string = "".join(c for c in string if c not in ",.:;")
	print(string)
	# split the text of the tweet by space
	words = string.split(" ")
	# for every word, check if length is greater than one and find all the tags and country names
	for word in words:
		if len(word) > 1:
			word = word.lower()
			for i, c in enumerate(country_codes):
				code = country_codes[i].lower()
				name = country_names[i].lower()
				if ((word[0] == "#" or word[0] == "@") and (code == word[1:-1] or name in word[1:-1])) or name == word:
					tags.append({"name": data[country_codes[i]]['name'], "lng": float(data[country_codes[i]]['lng']), "lat": float(data[country_codes[i]]['lat'])})
	return tags

"""
Views
"""
def index(request):
	# get tweets
	raw_tweets = get_tweets(10)
	coordinates = []
	tweets = []
	for tweet in raw_tweets:
		# need to handle cases where a tweet is a retweet, so use "retweeted_Status" in those cases
		text = tweet["retweeted_status"]['text'] if "retweeted_status" in tweet else tweet['text']
		# find all the tags and countries related to those tags in the text
		tags = find_country_tags(text)
		# build coordinates list
		coordinates.append(tags)
		# append to list of tweets
		tweets.append({
			"text": text
		})
	# context object
	context = {
    	'tweets': tweets,
    	'coordinates': json.dumps(coordinates)
	}

	# template
	template = loader.get_template('twitter/index.html')
	
	return HttpResponse(template.render(context, request))