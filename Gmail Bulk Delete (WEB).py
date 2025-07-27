# This project is doing bulk gmail deletes based on read versus unread email
# After download open finder (for mac) to copy and paste in the folder
# Installed appropriate Google client library for python in terminal
# Ensure that credentials.json is in desktop application

### Calling Gmail API
import os
import json
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

#Authetication
def main():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        #Call the Gmail API
        service = build("gmail", "v1", credentials=creds)

        # Simple test - just search for unread emails
        query = "is:unread" #add more queries
        messages = search_emails(service, query, max_results=500)

        if messages:
            confirm = input(f"Delete {len(messages)} unread emails? (y/n): ")
            if confirm.lower() == 'y':
                delete_emails(service, messages, query)
            else:
                print("Cancelled.")
        else:
            print("No unread emails found.")

    except HttpError as error:
        print(f"Main error: {error}")

def get_email_details(service, message_id):
    try:
        message = service.users().messages().get(userId="me", id=message_id, format='metadata').execute()

        # Extract headers
        headers = message['payload'].get('headers', [])
        subject = "No Subject"
        sender = "Unknown Sender"
        date = "Unknown Date"

        for header in headers:
            name = header['name'].lower()
            if name == 'subject':
                subject = header['value']
            elif name == 'from':
                sender = header['value']
            elif name == 'date':
                date = header['value']

        return {
            'id': message_id,
            'subject': subject[:60] + "..." if len(subject) > 60 else subject,
            'sender': sender,
            'date': date
        }
    except HttpError as error:
        print(f"Error getting details for message {message_id}: {error}")
        return {
            'id': message_id,
            'subject': "Error retrieving",
            'sender': "Error retrieving",
            'date': "Error retrieving"
        }

def search_emails(service, query, max_results=500):
    try:
        print(f"Searching for: {query}")
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        # Check if messages exist in the response
        messages = result.get('messages', [])
        if not messages:
            print("No messages found")
            return []

        print(f"Found {len(messages)} messages")

        # Get details for each message
        detailed_messages = []
        print("\nEmail Details:")
        print("-" * 120)
        print(f"{'#':<3} {'Subject':<62} {'Sender':<30} {'Date':<25}")
        print("-" * 120)

        for i, msg in enumerate(messages, 1):
            details = get_email_details(service, msg['id'])
            detailed_messages.append(details)

            # Truncate sender if too long
            sender_display = details['sender'][:28] + "..." if len(details['sender']) > 28 else details['sender']
            date_display = details['date'][:23] + "..." if len(details['date']) > 23 else details['date']

            print(f"{i:<3} {details['subject']:<62} {sender_display:<30} {date_display:<25}")

        print("-" * 120)
        return detailed_messages

    except HttpError as error:
        print(f"Search error: {error}")
        return []


def save_deleted_emails_log(messages, query):
    """Save deleted emails to a log file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"deleted_emails_{timestamp}.json"

    log_data = {
        "deletion_date": datetime.now().isoformat(),
        "total_deleted": len(messages),
        "emails": messages,
        "query": query,
    }

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        print(f"Deleted emails log saved to: {filename}")
    except Exception as e:
        print(f"Error saving log file: {e}")

def delete_emails(service, messages, query):
    if not messages:
        print("No messages to delete.")
        return

    print(f"About to delete {len(messages)} messages...")

    # Save log before deletion
    save_deleted_emails_log(messages, query)

    successful_deletions = 0
    failed_deletions = 0

    for i, message in enumerate(messages):
        try:
            print(f"Deleting message {i + 1}: {message['id']}")
            service.users().messages().trash(userId="me", id=message['id']).execute() # I want deleted emails to go to trash or a file
            print(f"✓ Successfully deleted message {i + 1}")
            successful_deletions += 1

        except HttpError as error:
            print(f"✗ Error deleting message {i + 1}: {error}")
            failed_deletions += 1

    print(f"\nDeletion Summary:")
    print(f"✓ Successfully deleted: {successful_deletions}")
    print(f"✗ Failed to delete: {failed_deletions}")


if __name__ == "__main__":
    main()


