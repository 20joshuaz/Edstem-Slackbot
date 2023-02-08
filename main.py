import os
import slack
import requests
from datetime import datetime, timedelta

OAUTH_TOKEN = os.environ["OAUTH_TOKEN"]
EDSTEM_TOKEN = os.environ["EDSTEM_TOKEN"]
PEOPLE_URL = os.environ["PEOPLE_URL"]
INTERACTS_URL = os.environ["INTERACTS_URL"]
CHAT_NAME = os.environ["CHAT_NAME"]
PROF_STICKER = os.environ["PROF_STICKER"]

SHOUTOUT_TEMPLATE = """
%s :tada: *Edstem Shoutouts* %s :tada:

For last week:
:speech_balloon: %s replied to %d posts!
:heart: %s got %d hearts!
:eyes: %s viewed %d posts!

Onto next week! :rocket:
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

def get_stats_from_week(interacts, admins, field):
  res = {}
  last_week = datetime.today().date() - timedelta(days=7)

  def get_edstem_date(date):
    return datetime.strptime(date[:10], "%Y-%m-%d").date()

  for entry in interacts[field]:
    date = get_edstem_date(entry["created_at"])
    doer = entry["user_id"]
    if last_week <= date and doer in admins:
      res[doer] = res.get(doer, 0) + entry.get("counts", 1)
  
  return res

def get_leaders(admins, action):
  top_count = max(action.values())
  top_doers = [admins[r] for r in action if action[r] == top_count]
  return top_count, top_doers

def get_message(top_repliers, top_hearted, top_viewers):
  def get_mentions(names):
    mentions = ["<@%s>" % name for name in names]
    return ", ".join(mentions)

  reply_mentions = get_mentions(top_repliers[1])
  heart_mentions = get_mentions(top_hearted[1])
  view_mentions = get_mentions(top_viewers[1])

  return SHOUTOUT_TEMPLATE % (
    PROF_STICKER, 
    PROF_STICKER, 
    reply_mentions, 
    top_repliers[0],
    heart_mentions,
    top_hearted[0],
    view_mentions,
    top_viewers[0]
  )

def main(event, context):
  header = {"X-Token": EDSTEM_TOKEN}

  people = requests.get(PEOPLE_URL, headers=header)
  if people.status_code != 200:
    raise RuntimeError("error fetching people: " + people.text)
  
  admins = get_edstem_admins(people.json())

  interacts = requests.get(INTERACTS_URL, headers=header)
  if interacts.status_code != 200:
    raise RuntimeError("error fetching people: " + interacts.text)

  interacts_json = interacts.json()
  replies = get_stats_from_week(interacts_json, admins, "replies")
  hearts = get_stats_from_week(interacts_json, admins, "hearts")
  views = get_stats_from_week(interacts_json, admins, "views")

  top_repliers = get_leaders(admins, replies)
  top_hearted = get_leaders(admins, hearts)
  top_viewers = get_leaders(admins, views)

  message = get_message(top_repliers, top_hearted, top_viewers)
  post_message(CHAT_NAME, message)

if __name__ == "__main__":
  main(None, None)
