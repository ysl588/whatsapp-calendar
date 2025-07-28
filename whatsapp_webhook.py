from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import dateparser
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
import uuid
import os


# Google Calendar API
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import dateparser
from datetime import datetime, timedelta
import uuid
import os

# Google Calendar API
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request  # ✅ Add this line


# Flask app
app = Flask(__name__)

# 權限範圍（這是最小的可以新增事件的範圍）
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# ✅ Google Calendar 授權與服務建立
def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # 若無 token.json 或過期，重新登入
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

# ✅ 解析 WhatsApp 訊息中的事件
def parse_event_local(message):
    print("Original message:", message)

    import re
    time_part = re.findall(r'on .*|at .*', message, re.IGNORECASE)
    time_phrase = time_part[0] if time_part else message

    print("Time phrase extracted:", time_phrase)

    parsed_time = dateparser.parse(
        time_phrase,
        settings={'PREFER_DATES_FROM': 'future'}
    )

    print("Parsed time:", parsed_time)

    if not parsed_time:
        return None

    title = message.split(" on ")[0].strip().capitalize()
    start_time = parsed_time.isoformat()
    end_time = (parsed_time + timedelta(minutes=90)).isoformat()

    return {
        "title": title,
        "start_time": start_time,
        "end_time": end_time
    }

# ✅ WhatsApp webhook
@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body")
    sender = request.form.get("From")

    print(f"📩 Received message from {sender}: {incoming_msg}")

    event_data = parse_event_local(incoming_msg)

    if not event_data:
        reply = "❓ Sorry, I couldn't understand the time. Try something like: 'Dinner with Sam on Friday at 7pm'."
    else:
        try:
            service = get_calendar_service()

            event = {
                'summary': event_data['title'],
                'start': {
                    'dateTime': event_data['start_time'],
                    'timeZone': 'Asia/Taipei',  # ⚠️ 根據你的時區調整
                },
                'end': {
                    'dateTime': event_data['end_time'],
                    'timeZone': 'Asia/Taipei',
                },
            }

            created_event = service.events().insert(calendarId='primary', body=event).execute()
            print(f"✅ Event created: {created_event.get('htmlLink')}")

            reply = f"📅 Event created: *{event_data['title']}* at {event_data['start_time']}"

        except Exception as e:
            print("❌ Error creating event:", e)
            reply = "⚠️ Something went wrong while adding to your Google Calendar."

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(port=5000)
