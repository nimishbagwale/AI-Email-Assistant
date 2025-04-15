import mail_brain
import dependencies
import db_email_manager


def store_attachments(db_conn, email_id, attachments):
    """Store attachment metadata in database"""
    if not attachments:
        return
        
    cursor = db_conn.cursor()
    try:
        for att in attachments:
            cursor.execute("""
                INSERT INTO attachments 
                (email_id, filename, mime_type, size) 
                VALUES (%s, %s, %s, %s)
            """, (email_id, att['filename'], att['mime_type'], att['size']))
        db_conn.commit()
    except dependencies.Error as e:
        db_conn.rollback()
        print(f"Error storing attachments: {e}")
    finally:
        cursor.close()

def fetch_and_store_emails(service, max_results=50):
    """Fetch emails from Gmail and store in MySQL database"""
    try:
        db = db_email_manager.get_db_connection(db_email_manager.db_config)
        cursor = db.cursor(dictionary=True)
        
        results = service.users().messages().list(
            userId="me",
            maxResults=max_results,
            labelIds=["INBOX"]
        ).execute()
        messages = results.get("messages", [])
        
        if not messages:
            print("No new messages found in inbox.")
            return

        print(f"\nProcessing {len(messages)} messages...")
        
        for message in messages:
            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=message["id"],
                    format="full"
                ).execute()
                
                parsed = mail_brain.parse_email(msg)
                headers = parsed['headers']
                
                email_data = {
                    "id": msg["id"],
                    "thread_id": msg["threadId"],
                    "from": headers.get("From", ""),
                    "to_recipients": headers.get("To", ""),
                    "cc_recipients": headers.get("Cc", ""),
                    "subject": headers.get("Subject", ""),
                    "body": parsed['body']['plain'] or msg.get("snippet", ""),
                    "received_on": dependencies.datetime.fromtimestamp(int(msg["internalDate"])/1000),
                    "is_read": "UNREAD" not in parsed['labels'],
                    "has_attachments": bool(parsed['attachments']),
                    "labels": ",".join(parsed['labels']),
                    "snippet": msg.get("snippet", "")[:200],
                    "size_kb": msg.get("sizeEstimate", 0) // 1024
                }
                
                cursor.execute("""
                    INSERT INTO emails (
                        id, thread_id, `from`, to_recipients, cc_recipients,
                        subject, body, received_on, is_read, has_attachments,
                        labels, snippet, size_kb
                    ) VALUES (
                        %(id)s, %(thread_id)s, %(from)s, %(to_recipients)s, %(cc_recipients)s,
                        %(subject)s, %(body)s, %(received_on)s, %(is_read)s, %(has_attachments)s,
                        %(labels)s, %(snippet)s, %(size_kb)s
                    )
                    ON DUPLICATE KEY UPDATE
                        labels = VALUES(labels),
                        is_read = VALUES(is_read),
                        has_attachments = VALUES(has_attachments),
                        snippet = VALUES(snippet)
                """, email_data)
                
                if parsed['attachments']:
                    store_attachments(db, msg["id"], parsed['attachments'])
                
                db.commit()
                print(f"Stored email: {email_data['subject'][:30]}...")
                
            except Exception as e:
                print(f"Error processing message {message['id']}: {str(e)}")
                db.rollback()
                
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()

def get_thread_emails(thread_id):
    """Retrieve full conversation thread"""
    try:
        db = db_email_manager.get_db_connection(db_email_manager.db_config)
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM emails 
            WHERE thread_id = %s 
            ORDER BY received_on
        """, (thread_id,))
        return cursor.fetchall()
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()

def search_emails_database(query, limit=50):
    """Basic full-text search"""
    try:
        db = db_email_manager.get_db_connection(db_email_manager.db_config)
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM emails 
            WHERE 
                MATCH(subject, body) AGAINST(%s IN NATURAL LANGUAGE MODE) OR
                `from` LIKE %s OR
                to_recipients LIKE %s
            LIMIT %s
        """, (query, f'%{query}%', f'%{query}%', limit))
        return cursor.fetchall()
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
