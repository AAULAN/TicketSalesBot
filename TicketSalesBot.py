import requests
import hashlib
import xml.etree.ElementTree as ET
import os
import time
import re
import argparse
from slackclient import SlackClient

parser = argparse.ArgumentParser(description='Ticket Sales Bot for Slack')
parser.add_argument('--stuser', required=True)
parser.add_argument('--stsecret', required=True)
parser.add_argument('--stevents', required=True)
parser.add_argument('--slacktoken', required=True)
args = vars(parser.parse_args())

ST_USER = args['stuser']
ST_SECRET = args['stsecret']
ST_EVENTS = args['stevents'].split(',')
SLACK_TOKEN = args['slacktoken']
ST_VERSION = "1"
ST_CASH = "1"
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
COMMAND = "!sales"

slack_client = SlackClient(SLACK_TOKEN)

def getAPIResponse(event):
    hash_string = ":".join([ST_VERSION,ST_USER,event,ST_CASH,ST_SECRET])
    sha = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

    try:
        r = requests.post("https://studentersamfundet.safeticket.dk/api/stats/" + event, data={'version': ST_VERSION, 'user': ST_USER, 'event': event, 'cash': ST_CASH, 'sha': sha})
        return r.text
    except Exception as e:
        print("type error: " + str(e))

def parseTicketsSold(response):
    ticketsSold = 0
    try:
        tree = ET.ElementTree(ET.fromstring(response))
    except Exception as e:
        print("type error: " + str(e))
        return ticketsSold
    root = tree.getroot()
    tickets = root.find('tickets')
    refunded = root.find('refunded')
    for count in tickets.iter('count'):
        ticketsSold += int(count.text)
    for count in refunded.iter('count'):
        ticketsSold -= int(count.text)

    return ticketsSold

def totalSold(events):
    totalSold = 0

    for event in events:
        response = getAPIResponse(event)
        ticketsSold = parseTicketsSold(response)
        totalSold += ticketsSold

    return totalSold

def handle_command(slack_events):
    response = None
    channel = None

    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            if event["text"].startswith(COMMAND):
                ticketsSold = totalSold(ST_EVENTS)
                response = str(ticketsSold) + " tickets sold!"
                channel = event["channel"]

    if response:
        # Sends the response back to the channel
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=response
        )

oldepoch = 0
oldTicketsSold = totalSold(ST_EVENTS)
if slack_client.rtm_connect(with_team_state=False):
    print("Bot connected and running!")

    while True:
        handle_command(slack_client.rtm_read())
        time.sleep(RTM_READ_DELAY)

        if time.time() - oldepoch >= 60:
            oldepoch = time.time()
            ticketsSold = totalSold(ST_EVENTS)
            if ticketsSold > oldTicketsSold:
                oldTicketsSold = ticketsSold
                response = "@channel New ticket sold, total is now at " + str(ticketsSold) + "!"
                slack_client.api_call(
                    "chat.postMessage",
                    link_names=1,
                    channel='soldtickets',
                    text=response
                )
else:
    print("Connection failed. Exception traceback printed above.")
