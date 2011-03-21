import json
import re
import urllib
import os
import time
import sys
import calendar
import argparse

def convert_time(t):
  return calendar.timegm(time.strptime(t, "%m/%d/%Y"))

parser = argparse.ArgumentParser(description="Calculate user's average karma.")
parser.add_argument('-l', action="store", dest="pagelimit", type=int,
                          help="Searches only the last PAGELIMIT pages.")
parser.add_argument('-t', action="store", dest="start_time", type=convert_time,
                    help="Starting date in MM/DD/YY format. Only checks links "
                        "on/after this date.")
parser.add_argument('-e', action="store", dest="end_time", type=convert_time,
                    help="Ending date in MM/DD/YY format. Will not check links "
                        "after this date.")
parser.add_argument('-s', action="store", dest="subreddit")
parser.add_argument('-q', action="store_true", dest="quiet", help="Disables "
                "verbose mode - nothing will be printed to the screen.")
parser.add_argument('user', action="store")


args = parser.parse_args()

baseurl = "http://www.reddit.com/user/%s/.json" % args.user

results = urllib.urlopen(baseurl).read()
try:
  j = json.loads(results)
except:
  print "Error parsing response:", results
  sys.exit(-1)

page = 1
num_posts = 0
tot_karma = 0

def get_karma_from_page(data):
  global num_posts, tot_karma
  links = []
  for entry in data['children']:
    node = entry['data']
    if args.start_time and node['created_utc'] < args.args.start_time:
      if not args.pagelimit:
        args.pagelimit = 0
      else:
        page = args.pagelimit
      break
    if not args.end_time or node['created_utc'] < args.args.end_time:
      if not args.subreddit or args.subreddit==node['subreddit']:
        if 'ups' in node and 'downs' in node:
          num_posts+=1
          tot_karma += node['ups'] - node['downs']

if not args.quiet:
  print "Loading page %s" % page
links = get_karma_from_page(j['data'])

try:
  while j['data']['after'] and (not args.pagelimit or page < args.pagelimit):
    time.sleep(2)# Reddit humbly requests a 2 second rate limit - please honor it.
    page+=1
    if not args.quiet:
      print "Loading page %s" % page
    query = urllib.urlencode({'after' : j['data']['after']})
    newurl = baseurl+"?"+query
    results = urllib.urlopen(newurl)
    try:
      j = json.loads(results.read())
      get_karma_from_page(j['data'])
    except (ValueError, IOError), e:
      if not args.quiet:
        print e
except KeyboardInterrupt:
  pass

print "Total Karma:", tot_karma
print "Average Karma:", (1.0 * tot_karma / num_posts)
