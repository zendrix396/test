import concurrent.futures
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from decouple import config

TEST_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
TEST_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default="")  

TWILIO_TEST_FROM_NUMBER = "+15005550006"

AI_VOICE_MESSAGE_URL = "http://twimlets.com/message?Message%5B0%5D=Hello%2C%20this%20is%20a%20test%20call%20from%20our%20automated%20system.%20Thank%20you%20for%20your%20time.%20Goodbye.&Voice=alice&"

def get_phone_numbers():
    print("How would you like to provide the phone numbers?")
    print("1. Paste a comma-separated list of numbers")
    print("2. Provide a path to a text file (one number per line)")
    print("3. Use a default list of test numbers")
    choice = input("Enter your choice (1, 2, or 3): ")

    if choice == '1':
        numbers_str = input("Paste the numbers here: ")
        return [num.strip() for num in numbers_str.split(',')]
    elif choice == '2':
        file_path = input("Enter the file path: ")
        try:
            with open(file_path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("Error: File not found.")
            return []
    elif choice == '3':
        print("Using a default list of Twilio's magic test numbers.")
        return [
            "+14108675310",  # Valid number for testing
            "+15005550001",  # Invalid number
            "+15005550002",  # Not routable
            "+15005550003",  # International permissions needed
            "+15005550004",  # Blocked number
        ]
    else:
        print("Invalid choice.")
        return []

def make_call(phone_number, client):
    try:
        call = client.calls.create(
            to=phone_number,
            from_=TWILIO_TEST_FROM_NUMBER,
            url=AI_VOICE_MESSAGE_URL
        )
        return {"number": phone_number, "status": call.status, "sid": call.sid}
    except TwilioRestException as e:
        return {"number": phone_number, "status": "failed", "error": e.msg}

def main():
    if not TEST_ACCOUNT_SID or not TEST_AUTH_TOKEN:
        print("\nError: Twilio test credentials are not set.")
        print("Please create a .env file and add your TWILIO_TEST_ACCOUNT_SID and TWILIO_TEST_AUTH_TOKEN.")
        return

    client = Client(TEST_ACCOUNT_SID, TEST_AUTH_TOKEN)
    phone_numbers = get_phone_numbers()

    if not phone_numbers:
        print("No phone numbers to dial.")
        return

    call_logs = []
    print("\nInitiating calls...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_number = {executor.submit(make_call, num, client): num for num in phone_numbers}
        for future in concurrent.futures.as_completed(future_to_number):
            try:
                result = future.result()
                call_logs.append(result)
            except Exception as exc:
                call_logs.append({"number": future_to_number[future], "status": "exception", "error": str(exc)})

    print("\n--- Call Logs ---")
    status_counts = {}
    
    call_logs.sort(key=lambda x: x['number'])

    for log in call_logs:
        status = log.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if status == 'failed' or status == 'exception':
            print(f"Number: {log['number']:<15} | Status: {status:<8} | Info: {log.get('error', 'N/A')}")
        else:
            print(f"Number: {log['number']:<15} | Status: {status:<8} | Info: SID {log.get('sid', 'N/A')}")

    print("\n--- Summary ---")
    for status, count in status_counts.items():
        print(f"Total calls with status '{status}': {count}")

if __name__ == "__main__":
    main()