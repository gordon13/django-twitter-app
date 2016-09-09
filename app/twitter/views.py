from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
import requests
import base64
import json
import csv
import os

COUNTRY_DATA_PATH = "%s\\data\\countries.csv"%os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSUMER_KEY = "rgvYj8SZvBpMOpJQtdWWRjbLN"
SECRET = "FCGns4cHNfyvhhuGDLNJ1AGFCgl1ruzCpFjb4EMlElXyBSPPhj"
BEAR_TOKEN = None

"""
Utility functions
"""
def read_csv_as_dict():
	with open(COUNTRY_DATA_PATH, "r") as file:
		return csv.DictReader(file)
		

def generate_key():
	return base64.b64encode("%s:%s"%(CONSUMER_KEY,SECRET))

def authenticate():

	# generate key from the various other keys
	FINAL_KEY = generate_key()

	# setup required headers for twitter API
	headers = {
		"Authorization":"Basic %s"%FINAL_KEY,
		"Content-Type":"application/x-www-form-urlencoded;charset=UTF-8"
	}
	r = requests.post("https://api.twitter.com/oauth2/token", data="grant_type=client_credentials", headers=headers) 
	return r.json()

def get_tweets(n):
	
	# authenticate
	BEAR_TOKEN = authenticate()

	# setup required headers for twitter API
	headers = {
		"Authorization": "Bearer %s"%BEAR_TOKEN['access_token']
	}

	# request MapleCroftRisk timeline
	r = requests.get('https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=MaplecroftRisk&count=%s'%n, headers=headers)
	return r.json()

"""
Views
"""
def index(request):
	
	# get last n tweets
	tweets = get_tweets(10)
	tweets = [{"text":tweet['text'],"location":tweet['coordinates'],"geo":tweet['geo'],"user_location":tweet['user']['location']} for tweet in tweets]
	print tweets

	# context object
	context = {
    	'tweets': tweets,
	}

	# template
	template = loader.get_template('twitter/index.html')
	
	return HttpResponse(template.render(context, request))