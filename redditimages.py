import json
import re
import urllib
import os
import time
import sys
import calendar
import argparse

imgur = r"http://(i\.)?imgur\.com[/\w]+(.\w+)?"
allpics = r"http://[\w./]+(png|jpg|jpeg|gif)"

def convert_time(t):
  return calendar.timegm(time.strptime(t, "%m/%d/%Y"))

class GWAction(argparse.Action):
  def __call__(self, parser, namespace, values, option_string = None):
    setattr(namespace, 'archive', True)
    setattr(namespace, 'subreddit', 'gonewild')

parser = argparse.ArgumentParser(description="Download images from a user's "
                                             "Reddit history.")
parser.add_argument('--all', action="store_const", dest="image_regex",
                      const=allpics, default=imgur)
parser.add_argument('-a', action="store_true", dest="archive", help="Archives "
                          "the Reddit permalink for for each link it finds, "
                          "for later reference.")
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
parser.add_argument('--gw', action=GWAction, nargs=0, help="Enables GoneWild "
                "mode - equivalent to '-as GoneWild'")
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
archive_set = set()

def get_images_from_data(data):
  global imgur, page, args
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
        text = ""
        if 'body' in node:
          text += node['body']
        if 'url' in node:
          text += node['url']
        for match in re.finditer(args.image_regex, text):
          link = match.group()
          if not match.group(2): # the file extension
            link += '.jpg' # imgur renders photo with any arbitrary extension
          if args.archive:
            try:
              if 'permalink' in node:
                archive_set.add(node['permalink'])
              else:
                linkid = re.sub('t\d_', '', node['link_id'])
                title = re.sub(' ', '_', node['link_title'])
                title = re.sub('\W', '', title)
                permalink = ("http://reddit.com/r/%s/comments/%s/%s" %
                                    (node['subreddit'], linkid , title))
                archive_set.add(permalink)
            except Exception, e:
              if not args.quiet:
                print e
          links.append(link)
  return links

if not args.quiet:
  print "Loading page %s" % page
links = get_images_from_data(j['data'])

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
      links.extend(get_images_from_data(j['data']))
    except (ValueError, IOError), e:
      if not args.quiet:
        print e
except KeyboardInterrupt:
  pass

if not args.quiet and len(links) == 0:
  print "No links found."
else:
  while len(links) > 0:
    if not os.path.exists(args.user):
      os.mkdir("./%s/" % args.user)

    if args.archive:
      f = open(os.path.abspath(os.path.join(args.user, 'archive.txt')), 'w')
      for link in archive_set:
        f.write("%s\n"%link)
      f.close()
      if not args.quiet:
        print "Archive written."

    linksleft = len(links)
    if not args.quiet:
      print "Found %s links. Downloading..." % linksleft
    failed = []

    for url in links:
      filepath = os.path.abspath(os.path.join(args.user,url[url.rfind("/")+1:]))
      
      if not os.path.exists(filepath):
        if not args.quiet:
          print "Downloading %s (%s remaining)..." % (filepath, linksleft)
        try:
          urllib.urlretrieve(url, filepath)
        except:
          failed.append(url)
      else:
        if not args.quiet:
          print "%s exists, skipping." % filepath
      linksleft-=1

    links = []

    if not args.quiet:
      if len(failed) > 0:
        print "URLs failed:"
        for x in failed:
          print x
        cont = raw_input("Retry? y/n [n]: ")
        if cont.lower() == 'y':
          links = failed
    else:
      f = open(os.path.abspath(os.path.join(args.user, 'failed.txt')), 'w')
      for link in failed:
        f.write("%s\n" % link)
      f.close()
