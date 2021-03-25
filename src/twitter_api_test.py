#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
File name:  twitter_api_test.py
Authors:    Erwin Meijerhof (*******)
            Wessel Poelman (S2976129)
Date:       25-03-2021
Description:
    bla bla komt nog
Usage:
    python twitter_api_test.py
"""

import json
from os.path import isfile

import tweepy

# Program constants
CREDENTIALS_PATH = '../credentials.txt'
OUTPUT_PATH_TEST_DATA = '../data/test_response.json'


def read_in_credentials(path=CREDENTIALS_PATH):
    if not isfile(path):
        print('Credentials file not found.')
        exit(1)

    with open(path, 'r') as f:

        credentials = {}

        for line in f.readlines():
            key, value = line.strip().split('=')
            credentials[key] = value

    return credentials


def extract_converstation(api, response, acc=[]):
    acc.append(response)

    new = api.get_status(response['in_reply_to_status_id'])._json

    if not new['in_reply_to_status_id']:
        return acc

    # Again, not the prettiest, just for testing purposes.
    return extract_converstation(api, new, acc)


def main():
    creds = read_in_credentials()

    auth = tweepy.OAuthHandler(creds['API_KEY'], creds['API_SECRET'])
    auth.set_access_token(creds['ACCESS_TOKEN'], creds['ACCESS_SECRET'])

    api = tweepy.API(auth)
    i = 0
    possibly_interesting = []

    for status in tweepy.Cursor(api.user_timeline, id="twitter").items():
        if i == 20:
            break

        response = status._json

        if not response['in_reply_to_status_id']:
            continue

        # Passing the whole api object is not a great way of doing this, just
        # for testing purposes right now.
        possibly_interesting.append(extract_converstation(api, response))

        i += 1

    with open(OUTPUT_PATH_TEST_DATA, 'w') as out:
        json.dump({'conversations': possibly_interesting}, out)


if __name__ == '__main__':
    main()
