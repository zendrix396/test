from twilio.rest import Client
from decouple import config
account_sid = config("TWILIO_ACCOUNT_SID")
auth_token = config("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

from_phone_number = "+919540983277"

to_phone_number = "+919311189073"

twiml_url = "http://demo.twilio.com/docs/voice.xml"

try:
    call = client.calls.create(
        url=twiml_url,
        to=to_phone_number,
        from_=from_phone_number
    )
    print(f"Call initiated with SID: {call.sid}")
except Exception as e:
    print(f"Error initiating call: {e}")

