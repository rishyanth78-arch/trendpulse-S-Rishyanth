import requests
import json
import os
import time
from datetime import datetime

# HackerNews API doesnt need any key or login which is why I chose it
# the idea is simple - get a list of story IDs first then fetch each one

headers = {"User-Agent": "TrendPulse/1.0"}

# I made a dictionary with all the keywords for each category
# just copied them from the task description
tech_words = ["AI", "software", "tech", "code", "computer", "data", "cloud", "API", "GPU", "LLM"]
world_words = ["war", "government", "country", "president", "election", "climate", "attack", "global"]
sport_words = ["NFL", "NBA", "FIFA", "sport", "game", "team", "player", "league", "championship"]
sci_words = ["research", "study", "space", "physics", "biology", "discovery", "NASA", "genome"]
entertain_words = ["movie", "film", "music", "Netflix", "game", "book", "show", "award", "streaming"]

# putting them together so I can loop over categories easily
categories = {
    "technology": tech_words,
    "worldnews": world_words,
    "sports": sport_words,
    "science": sci_words,
    "entertainment": entertain_words
}


# fetches the top 500 story IDs
def get_ids():
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        # I check the status code myself - 200 means it worked
        if resp.status_code == 200:
            all_ids = resp.json()
            # only take the first 500
            return all_ids[:500]
        else:
            print("got a bad response:", resp.status_code)
            return []
    except Exception as e:
        print("error getting IDs -", e)
        return []


# fetches one story using its ID number
def get_one_story(story_id):
    url = "https://hacker-news.firebaseio.com/v0/item/" + str(story_id) + ".json"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        # only return data if the request actually worked
        if resp.status_code == 200:
            return resp.json()
        else:
            print("bad status for story", story_id, "-", resp.status_code)
            return None
    except Exception as e:
        # just skip this story if something goes wrong
        print("skipping story", story_id, "because:", e)
        return None


# looks at the title and returns which category it fits in
def find_cat(title):
    if not title:
        return None

    # lowercase so AI matches ai, Tech matches tech etc
    lower = title.lower()

    for cat_name in categories:
        word_list = categories[cat_name]
        for w in word_list:
            if w.lower() in lower:
                return cat_name

    # didnt match any category
    return None


# ------- main code below -------

print("starting data collection...")
print("getting top story IDs from HackerNews")

ids = get_ids()
print("got", len(ids), "story IDs\n")

# loop through all IDs and download each story
stories_list = []
num = 0

for sid in ids:
    s = get_one_story(sid)

    # skip if request failed
    if s == None:
        continue

    # HackerNews has jobs and polls too, I only want type=story
    if s.get("type") != "story":
        continue

    stories_list.append(s)
    num = num + 1

    # print progress every 100 so I can see its still running
    if num % 100 == 0:
        print("downloaded", num, "stories...")

print("\ndone downloading,", len(stories_list), "stories in total")
print("now going through categories one by one\n")

# now go through each category and collect up to 25 stories per category
final_data = []

for cat_name in categories:

    cat_count = 0
    print("looking through stories for category:", cat_name)

    for s in stories_list:

        # once I have 25 for this category move on
        if cat_count == 25:
            break

        t = s.get("title", "")

        # check if this story belongs to current category
        if find_cat(t) != cat_name:
            continue

        # build the story entry with all 7 required fields
        story_entry = {}
        story_entry["post_id"] = s.get("id")
        story_entry["title"] = t
        story_entry["category"] = cat_name
        story_entry["score"] = s.get("score", 0)
        story_entry["num_comments"] = s.get("descendants", 0)
        story_entry["author"] = s.get("by", "")
        story_entry["collected_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        final_data.append(story_entry)
        cat_count = cat_count + 1

    print("  collected", cat_count, "stories for", cat_name)

    # the task sheet says to sleep 2 seconds between each category
    time.sleep(2)


# save results to the data folder as a json file
print("\nsaving results now...")

# create data folder if it isnt there already
if not os.path.exists("data"):
    os.mkdir("data")

# add the date to the filename
date_today = datetime.now().strftime("%Y%m%d")
file_name = "data/trends_" + date_today + ".json"

# write the json file
outfile = open(file_name, "w")
json.dump(final_data, outfile, indent=2)
outfile.close()

print(f"Collected {len(final_data)} stories. Saved to {file_name}")
