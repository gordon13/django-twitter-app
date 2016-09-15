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

COUNTRY_DATA_PATH = "%s\\twitter\\data\\countries.csv"%os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSUMER_KEY = "rgvYj8SZvBpMOpJQtdWWRjbLN"
SECRET = "FCGns4cHNfyvhhuGDLNJ1AGFCgl1ruzCpFjb4EMlElXyBSPPhj"
BEAR_TOKEN = None
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

	def set(self, data):
		self.last_updated = datetime.now()
		self.data = data

	def get(self):
		return self.data

tweet_cache = Cache( timedelta(minutes=CACHE_TIME) )
country_cache = Cache( timedelta(minutes=CACHE_TIME) )

"""
Read csv file and output dict. use caching class so we dont read the file too often
"""
def read_country_csv_as_dict():
	if country_cache.need_update:
		with open(COUNTRY_DATA_PATH, "r") as file:
			_countries_dict = {}
			for row in csv.DictReader(file):
				if type( row) is dict:
					lng = row["lng"] 
					lat = row["lat"]
					_countries_dict[row['code']] = {
						"name":row['name'].decode('utf-8'), 
						"lng": lng, 
						"lat": lat
					}
			return _countries_dict
	else:
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
	data = read_country_csv_as_dict()
	country_codes = data.keys()
	country_names = [country['name'] for country in data]
	words = string.split(" ")
	for word in words:
		if len(word) > 1:
			word = word.lower()
			for i, c in enumerate(country_codes):
				code = country_codes[i].lower()
				name = country_names[i].lower()
				if code in word or name in word:
					# make sure not to allow matches for things like like "US" and "business"
					# get difference between word in the text and country code and name
					code_difference = abs(len(code) - len(word))
					name_difference = abs(len(name) - len(word))
					# find which one is greater
					difference = code_difference if code_difference > name_difference else name_difference
					# use that as comparisson value to check whether we should append it
					if difference < 5:
						tags.append({"name": data[code]['name'], "lng": float(data[code]['lng']), "lat": float(data[code]['lat'])})
	# for key in country_codes:
	# 	if key in string or data[key]['name'] in string:
	# 		tags.append({"name": data[key]['name'], "lng": float(data[key]['lng']), "lat": float(data[key]['lat'])})
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
		tags = find_country_tags(text)
		print(text)
		print(tags)
		print("")
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