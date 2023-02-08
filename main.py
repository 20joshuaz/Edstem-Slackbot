import os
import slack
import requests
import dateparser
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

OAUTH_TOKEN = os.environ["OAUTH_TOKEN"]
EDSTEM_TOKEN = os.environ["EDSTEM_TOKEN"]
PEOPLE_URL = os.environ["PEOPLE_URL"]
INTERACTS_URL = os.environ["INTERACTS_URL"]
TIME_ZONE = ZoneInfo(os.environ["TIME_ZONE"])
CHAT_NAME = os.environ["CHAT_NAME"]
PROF_STICKER = os.environ["PROF_STICKER"]

SHOUTOUT_TEMPLATE = """
%s :tada: *Edstem Shoutouts* %s :tada:

For last week:
:speech_balloon: %s replied to %d posts!
"""

def post_message(channel, msg):
  client = slack.WebClient(token=OAUTH_TOKEN)
  client.chat_postMessage(channel=channel, text=msg)

def get_edstem_admins(people):
  res = {}
  for user in people["users"]:
    if user["course_role"] == "admin":
      res[user["user_id"]] = user["name"]

  return res

def get_replies_from_week(interacts, today, admins):
  res = {}
  last_week = today - timedelta(days=7)

  for reply in interacts["replies"]:
    date = dateparser.parse(reply["created_at"])
    replier = reply["user_id"]
    if last_week <= date <= today and replier in admins:
      res[replier] = res.get(replier, 0) + 1
  
  return res

def get_message(top, n):
  mentions = ["<@%s>" % name for name in top]
  return SHOUTOUT_TEMPLATE % (PROF_STICKER, PROF_STICKER, ", ".join(mentions), n)

def main(event, context):
  header = {"X-Token": EDSTEM_TOKEN}

  people = requests.get(PEOPLE_URL, headers=header)
  if people.status_code != 200:
    raise RuntimeError("error fetching people: " + people.text)
  
  admins = get_edstem_admins(people.json())

  interacts = requests.get(INTERACTS_URL, headers=header)
  if interacts.status_code != 200:
    raise RuntimeError("error fetching people: " + interacts.text)

  replies = get_replies_from_week(interacts.json(), datetime.now().astimezone(TIME_ZONE), admins)

  top_reply_count = max(replies.values())
  top_repliers = [admins[r] for r in replies if replies[r] == top_reply_count]

  post_message(CHAT_NAME, get_message(top_repliers, top_reply_count))

if __name__ == "__main__":
  main(None, None)
