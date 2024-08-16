# trying to extract the useful information from the garmin data api access file
import datetime
import json
import logging
import os
import sys
from getpass import getpass
import pandas as pd
import matplotlib.pyplot as plt

import readchar
import requests
from garth.exc import GarthHTTPError

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Configure debug logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables if defined
email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
tokenstore = os.getenv("GARMINTOKENS") or "~/.garminconnect"
tokenstore_base64 = os.getenv("GARMINTOKENS_BASE64") or "~/.garminconnect_base64"
api = None

# Example selections and settings
today = datetime.date.today()
startdate = today - datetime.timedelta(days=30)  # Select past 30 days
start = 0
limit = 100
start_badge = 1  # Badge related calls calls start counting at 1
activitytype = ""  # Possible values are: cycling, running, swimming, multi_sport, fitness_equipment, hiking, walking, other
activityfile = "MY_ACTIVITY.fit"  # Supported file types are: .fit .gpx .tcx
weight = 80.00
weightunit = 'kg'

def display_json(api_call, output):
    """Format API output for better readability."""

    dashed = "-" * 20
    header = f"{dashed} {api_call} {dashed}"
    footer = "-" * len(header)

    print(header)

    if isinstance(output, (int, str, dict, list)):
        print(json.dumps(output, indent=4))
    else:
        print(output)

    print(footer)


def display_text(output):
    """Format API output for better readability."""

    dashed = "-" * 60
    header = f"{dashed}"
    footer = "-" * len(header)

    print(header)
    print(json.dumps(output, indent=4))
    print(footer)


def get_credentials():
    """Get user credentials."""

    email = input("Login e-mail: ")
    password = getpass("Enter password: ")

    return email, password


def init_api(email, password):
    """Initialize Garmin API with your credentials."""

    try:
        # Using Oauth1 and OAuth2 token files from directory
        print(
            f"Trying to login to Garmin Connect using token data from directory '{tokenstore}'...\n"
        )

        # Using Oauth1 and Oauth2 tokens from base64 encoded string
        # print(
        #     f"Trying to login to Garmin Connect using token data from file '{tokenstore_base64}'...\n"
        # )
        # dir_path = os.path.expanduser(tokenstore_base64)
        # with open(dir_path, "r") as token_file:
        #     tokenstore = token_file.read()

        garmin = Garmin()
        garmin.login(tokenstore)

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        # Session is expired. You'll need to log in again
        print(
            "Login tokens not present, login with your Garmin Connect credentials to generate them.\n"
            f"They will be stored in '{tokenstore}' for future use.\n"
        )
        try:
            # Ask for credentials if not set as environment variables
            if not email or not password:
                email, password = get_credentials()

            garmin = Garmin(email=email, password=password, is_cn=False, prompt_mfa=get_mfa)
            garmin.login()
            # Save Oauth1 and Oauth2 token files to directory for next login
            garmin.garth.dump(tokenstore)
            print(
                f"Oauth tokens stored in '{tokenstore}' directory for future use. (first method)\n"
            )
            # Encode Oauth1 and Oauth2 tokens to base64 string and safe to file for next login (alternative way)
            token_base64 = garmin.garth.dumps()
            dir_path = os.path.expanduser(tokenstore_base64)
            with open(dir_path, "w") as token_file:
                token_file.write(token_base64)
            print(
                f"Oauth tokens encoded as base64 string and saved to '{dir_path}' file for future use. (second method)\n"
            )
        except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError, requests.exceptions.HTTPError) as err:
            logger.error(err)
            return None

    return garmin


def get_mfa():
    """Get MFA."""

    return input("MFA one-time code: ")


if not api:
    api = init_api(email, password)

"""
Save rhr to a df for selected timeframe
"""
params = {
    "fromDate": str(startdate),
    "untilDate": str(today),
    "metricId": 60
}
url = f"{api.garmin_connect_rhr_url}/{api.display_name}"
rhrData = api.connectapi(url, params=params)

rhrDF = pd.DataFrame(rhrData["allMetrics"]["metricsMap"]['WELLNESS_RESTING_HEART_RATE']).set_index("calendarDate")
#plot = rhrDF.plot(title="Resting Heart Rate", xlabel="Date", ylabel="Heart Rate")
#plt.show()

"""
Save time in zones for each day to a df
get list of activities. for each activity in the list, return the time in zones
"""
activities = api.get_activities_by_date(startdate,today)

totalTimeInZones=[]
for activity in activities:
    activityId = activity['activityId']
    activityDate = activity['startTimeGMT']
    timeInZones = api.get_activity_hr_in_timezones(activityId)
    totalTimeInZones.append([activityDate,timeInZones])

timeInZonesDict = {}
for activity in totalTimeInZones:
    activityZones = []
    for zone in activity[1]:
        activityZones.append(zone["secsInZone"])
    date = datetime.datetime.strptime(activity[0], "%Y-%m-%d %H:%M:%S").date()
    if date in timeInZonesDict.keys():
        for num,i in enumerate(timeInZonesDict[date]):
            timeInZonesDict[date][num]+=activityZones[num]
    else:
        timeInZonesDict[date]=activityZones

timeInZonesDF = pd.DataFrame.from_dict(timeInZonesDict).transpose()
print(timeInZonesDF)

wellnessData = pd.concat([timeInZonesDF, rhrDF]).to_csv("wellnessData.csv")
