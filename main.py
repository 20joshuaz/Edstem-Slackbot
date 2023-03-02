import os
import slack
import requests
from datetime import datetime, timedelta

PEOPLE_URL = os.environ["PEOPLE_URL"]
INTERACTS_URL = os.environ["INTERACTS_URL"]

SHOUTOUT_TEMPLATE = """
%s :tada: *Edstem Shoutouts* %s :tada:

For last week:
:speech_balloon: %s replied to %d posts!
:heart: %s got %d hearts!
:eyes: %s viewed %d posts!

Onto next week! :rocket:
"""


def post_message(channel, msg, oauth):
    client = slack.WebClient(token=oauth)
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


def get_message(top_repliers, top_hearted, top_viewers, prof_sticker):
    def join_names(names):
        return ", ".join(names)

    reply_count, reply_names = top_repliers
    heart_count, heart_names = top_hearted
    view_count, view_names = top_viewers

    reply_names = join_names(reply_names)
    heart_names = join_names(heart_names)
    view_names = join_names(view_names)

    return SHOUTOUT_TEMPLATE % (
        prof_sticker,
        prof_sticker,
        reply_names,
        reply_count,
        heart_names,
        heart_count,
        view_names,
        view_count,
    )


def main(event, context):
    data = event["attributes"]
    OAUTH_TOKEN = data["OAUTH_TOKEN"]
    EDSTEM_TOKEN = data["EDSTEM_TOKEN"]
    COURSE_NUMBER = data["COURSE_NUMBER"]
    CHAT_NAME = data["CHAT_NAME"]
    PROF_STICKER = data["PROF_STICKER"]

    header = {"X-Token": EDSTEM_TOKEN}

    people = requests.get(PEOPLE_URL % COURSE_NUMBER, headers=header)
    if people.status_code != 200:
        raise RuntimeError("error fetching people: " + people.text)

    admins = get_edstem_admins(people.json())

    interacts = requests.get(INTERACTS_URL % COURSE_NUMBER, headers=header)
    if interacts.status_code != 200:
        raise RuntimeError("error fetching people: " + interacts.text)

    interacts_json = interacts.json()
    replies = get_stats_from_week(interacts_json, admins, "replies")
    hearts = get_stats_from_week(interacts_json, admins, "hearts")
    views = get_stats_from_week(interacts_json, admins, "views")

    top_repliers = get_leaders(admins, replies)
    top_hearted = get_leaders(admins, hearts)
    top_viewers = get_leaders(admins, views)

    message = get_message(top_repliers, top_hearted, top_viewers, PROF_STICKER)
    post_message(CHAT_NAME, message, OAUTH_TOKEN)
