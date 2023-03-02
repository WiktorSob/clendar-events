import requests
import html
from bs4 import BeautifulSoup
import unicodedata
from unidecode import unidecode
from datetime import datetime, timezone
import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def update_calendar():  

    months_dict = {'stycznia' : '1',
                'lutego' : '2',
                'marca' : '3',
                'kwietnia' : '4',
                'maja' : '5',
                'czerwca' : '6',
                'lipca' : '7',
                'sierpnia' : '8',
                'września': '9',
                'października' : '10',
                'listopada' : '11',
                'grudnia' : '12'}

    link = 'https://atlasarena.pl/wydarzenia'
    cal_id = 'google_calendar_id'


    response = requests.get(link)
    content = response.content.decode('utf-8')
    content = html.unescape(content)
    content = unicodedata.normalize("NFKD", content)
    soup = BeautifulSoup(content, 'html.parser')
    
    
    # get data from Atlas Arena page - obtain event titles and dates
    
    dates = soup.find_all('div', {'class': 'date'})
    titles = soup.find_all('h2')

    events_insert = []
    for date, title in zip(dates, titles):
        
        event_metadata = {}

        event_date = date.get_text().strip().split()
        event_date[1] = months_dict.get(event_date[1].lower())
        # change time to use info about summer/winter time (or check if date is between given period)
        start_date = '/'.join(map(str, event_date)) + ' 17:00:00'
        start_date = datetime.datetime.strptime(start_date,
                                       '%d/%m/%Y %H:%M:%S').astimezone().isoformat()

        end_date = '/'.join(map(str, event_date)) + ' 18:30:00'
        end_date = datetime.datetime.strptime(end_date,
                                     '%d/%m/%Y %H:%M:%S').astimezone().isoformat()

        event_title = title.get_text().strip()

        '''
        create json style object with event metadata
        in format used by google calendar API 
        '''
        event_metadata = {'summary': 'Atlas Arena Event',
                          'description': event_title,
                          'start': {'dateTime': start_date},
                          'end': {'dateTime': end_date},
                          'reminders': {'useDefault': False,
                                        'overrides': [
                                            {'method': 'popup',
                                             'minutes': 15}]}}
        
        events_insert.append(event_metadata)

    events_insert_keys = [event['description'].replace(' ', '') +
                          '_' + event['start']['dateTime'].split('T')[0]
                          for event in events_insert]
    
    '''
    Connect to google calendar API and download all events from atlas calendar
    create event keys to compare them with events obtained from atlas website
    if given key matches then event wont be added as it already exists in calendar
    '''
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
             
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=50589)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        
        events_result = service.events().list(calendarId= cal_id, timeMin=now,
                                                singleEvents=True,
                                                orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            
        events_keys = [event['description'].replace(' ', '') + '_' +
                    event['start']['dateTime'].split('T')[0]
                    for event in events]
        print('---Events in calendar---')
        for event in events:
            print(event['start']['dateTime'],"-",event['description'])
        
    except HttpError as error:
        print('An error occurred: %s' % error)
    
    

    

    # inser new events to calenar
    print('---Adding Events---')    
    for event_key, event in zip(events_insert_keys, events_insert):
        if event_key in events_keys:
            print(f'Event ID: {event_key} - already in calendar')
        else:
            event = service.events().insert(calendarId = cal_id, body = event).execute()
            print(f"event created: { event['description'] }")    

update_calendar()
