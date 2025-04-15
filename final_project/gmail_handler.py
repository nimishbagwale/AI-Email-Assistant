import mail_brain
import dependencies
import connectors
import text_model_utils

def create_draft(service, to, subject, message_text, sender="me"):
    """Create and insert a draft email."""
    try:
        message = dependencies.MIMEText(message_text)
        message["to"] = to
        message["from"] = sender
        message["subject"] = subject
        
        raw = dependencies.base64.urlsafe_b64encode(message.as_bytes())
        raw = raw.decode()
        
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()
        
        print(f"Draft created with ID: {draft['id']}")
        return draft
        
    except dependencies.HttpError as error:
        print(f"Error creating draft: {error}")
        return None

def send_email(service, to_email, subject, message_body, from_email="me"):
    """Send an email using the Gmail API."""
    try:
        message = dependencies.EmailMessage()
        message.set_content(message_body)
        message["To"] = to_email
        message["From"] = from_email
        message["Subject"] = subject

        encoded_message = dependencies.base64.urlsafe_b64encode(message.as_bytes()).decode()
        raw_message = {"raw": encoded_message}
        
        sent_message = service.users().messages().send(
            userId="me",
            body=raw_message
        ).execute()
        
        print(f"Message sent successfully! Message ID: {sent_message['id']}")
        return sent_message
        
    except dependencies.HttpError as error:
        print(f"Error sending email: {error}")
        if error.resp.status == 403:
            print("Make sure you have the 'gmail.send' scope authorized")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_latest_emails(max_results=5, label_ids=['INBOX'], unread_only=True, days=3):
    """
    Retrieve the latest emails from the specified label, restricted to the last N days.
    Marks them as READ if unread_only=True.

    Args:
        max_results (int): Maximum number of emails to retrieve.
        label_ids (list): List of Gmail label IDs (default: INBOX).
        unread_only (bool): If True, only returns unread emails.
        days (int): Number of past days to include.

    Returns:
        list: List of email dictionaries or None if error occurs.
    """
    service = connectors.get_gmail_service()
    if not service:
        return None

    try:
        from datetime import datetime, timedelta

        # Step 1: Calculate time range
        after_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y/%m/%d')
        query = f"after:{after_date}"
        if unread_only:
            query += " is:unread"

        # Step 2: Get UNREAD label ID if needed
        unread_label_id = None
        if unread_only:
            labels = service.users().labels().list(userId='me').execute().get('labels', [])
            unread_label_id = next(
                (label['id'] for label in labels if label['name'].upper() == 'UNREAD'),
                None
            )

        # Step 3: Fetch messages using query
        results = service.users().messages().list(
            userId='me',
            q=query,
            labelIds=label_ids,
            maxResults=max_results * 2  # Fetch extras in case of skips
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            print('No messages found.')
            return []

        email_list = []
        for message in messages:
            msg_detail = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date'],
                fields='id,threadId,payload(headers),snippet,labelIds'
            ).execute()

            label_ids_in_msg = msg_detail.get('labelIds', [])
            if unread_only and unread_label_id and unread_label_id not in label_ids_in_msg:
                continue

            headers = {h['name']: h['value'] for h in msg_detail.get('payload', {}).get('headers', [])}
            email_list.append({
                'id': msg_detail.get('id', 'Unknown'),
                'threadId': msg_detail.get('threadId', 'Unknown'),
                'from': headers.get('From', 'Unknown'),
                'subject': headers.get('Subject', 'No Subject'),
                'date': headers.get('Date', ''),
                'snippet': (msg_detail.get('snippet', '')[:100] + '...') if msg_detail.get('snippet') else '',
                'is_unread': unread_label_id in label_ids_in_msg if unread_label_id else False
            })

            # ✅ Mark the email as READ
            if unread_only and unread_label_id:
                service.users().messages().modify(
                    userId='me',
                    id=msg_detail['id'],
                    body={'removeLabelIds': [unread_label_id]}
                ).execute()

            if unread_only and len(email_list) >= max_results:
                break

        if unread_only and not email_list:
            print('No unread messages found.')

        return email_list[:max_results]

    except Exception as error:
        print(f'An error occurred: {error}')
        return None

def get_drafts(service):
    """Get list of email drafts (simplest version)"""
    try:
        results = service.users().drafts().list(userId='me').execute()
        return results.get('drafts', [])
    except Exception as e:
        print(f"Error getting drafts: {e}")
        return []

def display_gmail_search_results(service, results):
    """Display formatted search results from Gmail API"""
    messages = results.get('messages', [])
    if not messages:
        print("No messages found matching your search")
        return
        
    print(f"\nFound {len(messages)} results:")
    for i, msg in enumerate(messages, 1):
        full_msg = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()
        
        headers = {h['name']: h['value'] for h in full_msg['payload']['headers']}
        print(f"\n{i}. {headers.get('Subject', 'No Subject')}")
        print(f"   From: {headers.get('From', 'Unknown')}")
        print(f"   Date: {headers.get('Date', 'Unknown')}")
        print(f"   ID: {msg['id']}")
        
    print("\nActions: (v)iew, (e)xport, (b)ack")
    action = input("Choose action: ").lower()
    if action == 'v' and messages:
        view_full_email(service, messages[0]['id'])

def forward_email(service, email_id, recipient=None, add_note=True, keep_labels=False):
    """
    Forward an email with various customization options
    
    Args:
        service: Gmail API service instance
        email_id: ID of the email to forward
        recipient: Email address to forward to (None = prompt user)
        add_note: Whether to add a forwarding note
        keep_labels: Whether to preserve original labels on forwarded copy
        
    Returns:
        dict: {'status': bool, 'new_id': str} containing operation status and new message ID
    """
    try:
        # Get original email data
        original = service.users().messages().get(
            userId='me',
            id=email_id,
            format='raw'
        ).execute()
        
        # Decode raw email
        import email
        msg_str = dependencies.base64.urlsafe_b64decode(original['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)
        
        # Get recipient if not provided
        if not recipient:
            recipient = input("Enter recipient email address: ").strip()
            if not recipient:
                return {'status': False, 'error': 'No recipient specified'}
        
        # Create forwarded message
        forwarded_msg = dependencies.EmailMessage()
        
        # 1. Add forwarding note if requested
        if add_note:
            original_subject = mime_msg.get('Subject', 'No Subject')
            original_from = mime_msg.get('From', 'Unknown Sender')
            forwarded_msg.set_content(
                f"\n\n---------- Forwarded message ----------\n"
                f"From: {original_from}\n"
                f"Subject: {original_subject}\n"
                f"Date: {mime_msg.get('Date', 'Unknown Date')}\n\n"
                + (mime_msg.get_payload() if mime_msg.is_multipart() else mime_msg.get_payload(decode=True).decode())
            )
        else:
            forwarded_msg.set_content(mime_msg.get_payload() if mime_msg.is_multipart() 
                                    else mime_msg.get_payload(decode=True).decode())
        
        # 2. Set headers
        forwarded_msg['To'] = recipient
        forwarded_msg['From'] = 'me'
        forwarded_msg['Subject'] = f"Fwd: {mime_msg.get('Subject', '')}"
        forwarded_msg['References'] = mime_msg.get('Message-ID', '')
        
        # 3. Handle attachments
        if mime_msg.is_multipart():
            for part in mime_msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                forwarded_msg.add_attachment(
                    part.get_payload(decode=True),
                    maintype=part.get_content_maintype(),
                    subtype=part.get_content_subtype(),
                    filename=part.get_filename()
                )
        
        # Create message
        encoded_msg = dependencies.base64.urlsafe_b64encode(forwarded_msg.as_bytes()).decode()
        body = {'raw': encoded_msg}
        
        # Send the email
        sent_msg = service.users().messages().send(
            userId='me',
            body=body
        ).execute()
        
        # 4. Optionally preserve labels
        if keep_labels:
            original_labels = original.get('labelIds', [])
            if original_labels:
                service.users().messages().modify(
                    userId='me',
                    id=sent_msg['id'],
                    body={'addLabelIds': original_labels}
                ).execute()
        
        return {
            'status': True,
            'new_id': sent_msg['id'],
            'threadId': sent_msg.get('threadId'),
            'recipient': recipient
        }
        
    except dependencies.HttpError as error:
        return {'status': False, 'error': f"Gmail API error: {error}"}
    except Exception as e:
        return {'status': False, 'error': f"Unexpected error: {str(e)}"}

def change_email_label(service, email_id, old_label=['INBOX'], new_label=['ARCHIVED']):
    """Change email labels with enhanced handling
    
    Args:
        service: Authorized Gmail API service instance
        email_id: ID of the email to modify
        old_label: List of labels to remove
        new_label: List of labels to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current labels to preserve existing ones
        msg = service.users().messages().get(
            userId='me',
            id=email_id,
            format='metadata',
            fields='labelIds'
        ).execute()
        
        current_labels = msg.get('labelIds', [])
        
        # Special handling for ARCHIVED (remove INBOX)
        if 'ARCHIVED' in new_label:
            new_labels = {
                'removeLabelIds': ['INBOX'],
                'addLabelIds': [label for label in current_labels if label != 'INBOX']
            }
        else:
            new_labels = {
                'removeLabelIds': old_label,
                'addLabelIds': new_label
            }

        # Update labels
        service.users().messages().modify(
            userId='me',
            id=email_id,
            body=new_labels
        ).execute()
        
        print(f"✅ Email labels updated successfully (ID: {email_id})")
        return True
        
    except dependencies.HttpError as error:
        print(f"❌ Failed to update email labels: {error}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error updating labels: {e}")
        return False

def view_full_email(service, email_id):
    """Display full email content with formatting"""
    try:
        email = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()
        
        headers = {h['name']:h['value'] for h in email['payload']['headers']}
        print("\n" + "="*50)
        print(f"FROM: {headers.get('From','')}")
        print(f"TO: {headers.get('To','')}")
        print(f"DATE: {headers.get('Date','')}")
        print(f"SUBJECT: {headers.get('Subject','')}")
        print("-"*50)
        
        # Extract and display body
        body = mail_brain.extract_body(email['payload'], 'text/plain') or "No text content"
        print(body[:2000])  # Limit display length
        print("="*50)
        
        # Show attachments if any
        if 'parts' in email['payload']:
            attachments = [
                p for p in email['payload']['parts'] 
                if 'filename' in p and p['filename']
            ]
            if attachments:
                print("\n📎 Attachments:")
                for att in attachments:
                    print(f"- {att['filename']} ({att['mimeType']})")
    
    except Exception as e:
        print(f"Error viewing email: {e}")

def compose_reply(service, original_email):
    # 1. Analyze original email with sender context
    try:
        analysis = mail_brain.process_email(
            original_email['body'] if 'body' in original_email else original_email['snippet'],
            original_email.get('from', '')
        )
    except Exception as e:
        print(f"⚠️ Analysis failed: {str(e)}")
        analysis = {
            'intent': {'label': 'unknown'},
            'summary': original_email.get('snippet', ''),
            'actions': []
        }
    
    print(f"\n🔍 Analysis:")
    print(f"- Intent: {analysis['intent']['label']} (confidence: {analysis['intent']['score']:.0%})")
    if analysis['intent'].get('details', {}).get('triggers'):
        triggers = analysis['intent']['details']['triggers']
        if triggers['domain']:
            print(f"- Domain: {triggers['domain']}")
        if triggers['keywords']:
            print(f"- Keywords: {', '.join(triggers['keywords'])}")
    print(f"- Key Points: {analysis['summary'][:200]}...")
    
    # 2. Generate reply using available methods
    if text_model_utils.reply_generator:
        try:
            prompt = f"""Reply to this {analysis['intent']['label']} email:
From: {original_email.get('from', '')}
Subject: {original_email.get('subject', '')}
Content: {analysis['summary'][:500]}

Professional reply:"""
            
            generated_reply = text_model_utils.reply_generator(
                prompt,
                max_length=300,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True
            )[0]['generated_text'].split("Professional reply:")[-1].strip()
        except Exception as e:
            print(f"⚠️ Generation failed: {str(e)}")
            generated_reply = f"Dear {mail_brain.extract_name(original_email.get('from', ''))},\n\nThank you for your email. "
    else:
        # Fallback template-based reply
        sender_name = mail_brain.extract_name(original_email.get('from', ''))
        if analysis['intent']['label'] in ['job_posting', 'interview_invite']:
            generated_reply = f"Dear {sender_name},\n\nThank you for reaching out about the opportunity. {analysis['summary'][:100]}\n\nBest regards,\n[Your Name]"
        elif "question" in analysis['intent']['label'].lower():
            generated_reply = f"Dear {sender_name},\n\nThank you for your question. {analysis['summary'][:100]}\n\nBest regards,\n[Your Name]"
        else:
            generated_reply = f"Dear {sender_name},\n\nThank you for your email. {analysis['summary'][:100]}\n\nBest regards,\n[Your Name]"
    
    # 3. Present to user
    print("\n📝 Draft Reply:")
    print("="*50)
    print(generated_reply)
    print("="*50)
    
    # 4. Editing options
    print("\nOptions:")
    print("1. Edit and send")
    print("2. Send as-is")
    print("3. Cancel")
    
    while True:
        choice = input("\nChoose (1-3): ")
        if choice == "1":
            print("Edit your reply (type END on new line to finish):")
            lines = [generated_reply]
            while True:
                line = input()
                if line == "END":
                    break
                lines.append(line)
            generated_reply = "\n".join(lines)
            
            if input("Send this version? (y/n): ").lower() == 'y':
                send_email(service, original_email['from'], f"Re: {original_email['subject']}", generated_reply)
                print("✅ Reply sent!")
            break
            
        elif choice == "2":
            send_email(service, original_email['from'], f"Re: {original_email['subject']}", generated_reply)
            print("✅ Reply sent!")
            break
            
        elif choice == "3":
            print("Reply cancelled.")
            break


