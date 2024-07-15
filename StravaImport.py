import requests
import datetime
import urllib3
import matplotlib.pyplot as plt
import pandas as pd
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

auth_url = "https://www.strava.com/oauth/token"
activites_url = "https://www.strava.com/api/v3/athlete/activities"

client_id = input("Enter your client ID: ")
client_secret = input("Enter your client secret: ")
refresh_token = input("Enter your refresh token: ")

payload = {
    'client_id': client_id,
    'client_secret': client_secret,
    'refresh_token': refresh_token,
    'grant_type': "refresh_token",
    'f': 'json'
}

#print("Requesting Token...\n")
res = requests.post(auth_url, data=payload, verify=False)
access_token = res.json()['access_token']
#print("Access Token = {}\n".format(access_token))

header = {'Authorization': 'Bearer ' + access_token}
param = {'per_page': 200, 'page': 1}
my_dataset = requests.get(activites_url, headers=header, params=param).json()

types = []
moving_times = []
distances = []
dates = []
sessions = {}
num_sessions = len(my_dataset)

for i in range(num_sessions-1,-1,-1):
    if my_dataset[i]['has_heartrate']:
        sessions["session{0}".format(i)] = [my_dataset[i]['start_date'],my_dataset[i]['type'],my_dataset[i]['moving_time'],my_dataset[i]['average_heartrate'],my_dataset[i]['distance']]
    else:
        sessions["session{0}".format(i)] = [my_dataset[i]['start_date'],my_dataset[i]['type'],my_dataset[i]['moving_time'],0,my_dataset[i]['distance']]

    m, s = divmod(my_dataset[i]['moving_time'], 60)
    h, m = divmod(m, 60)
    
    distances.append(my_dataset[i]['distance'])
    moving_times.append(my_dataset[i]['moving_time'])
    dates.append(my_dataset[i]['start_date'])

print(type(sessions))
SessionsDF = pd.DataFrame(sessions).T
print(SessionsDF.tail())


date_time = pd.to_datetime(dates)
df = pd.DataFrame({'Date':date_time})
df['Time']=df['Date'].dt.time
df['Date']=df['Date'].dt.date
df['Week']=df['Date'].apply(lambda x: str(x.isocalendar()[0])+"-"+str(x.isocalendar()[1]))
df['Week']=df['Week'].apply(lambda x: datetime.datetime.strptime(x + '-1', "%Y-%W-%w"))
df['Moving_Time'] = moving_times
df['Distance'] = distances
print(df.head())
print(sessions)


plt.figure(1)
plt.bar(df.Week, df.Moving_Time)
plt.gcf().autofmt_xdate()

plt.figure(2)
plt.bar(df.Date, df.Moving_Time)
plt.gcf().autofmt_xdate()

plt.show()