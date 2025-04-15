import connectors
import db_email_manager
import dependencies
import gmail_handler
import mail_brain
import utils_email_core

def interactive_mode(service):
    """Interactive menu with comprehensive email management options"""
    while True:
        print("\n" + "="*50)
        print("📋 INTERACTIVE MODE".center(50))
        print("="*50)
        print("\n1. 📥 Check New Emails")
        print("2. 🏷️ View Labeled Emails")
        print("3. 🔍 Search Emails")
        print("4. 📧 Compose Email")
        print("5. 📝 Draft Management")
        print("6. 📊 Analyze Email Thread")
        print("7. 🗄️ Archive/Cleanup")
        print("8. ⚙️ Account Settings")
        print("9. ↩️ Back to Main Menu")
        
        choice = input("\nEnter your choice (1-9): ")
        
        if choice == "1":
            # Check new emails with enhanced analysis
            print("\n" + "="*20 + " NEW EMAILS " + "="*20)
            max_emails = int(input("How many recent emails to check? (5-50): ") or "10")
            emails = gmail_handler.get_latest_emails(max_results=max_emails)
            
            if not emails:
                print("\nNo new emails found.")
                continue
                
            for i, email in enumerate(emails, 1):
                print(f"\n{i}/{len(emails)}")
                print(f"📩 From: {email['from']}")
                print(f"📌 Subject: {email['subject']}")
                print(f"📅 Date: {email['date']}")
                print(f"🔍 Snippet: {email['snippet']}")
                
                print("\nAnalyzing the mail .......")
                # Enhanced analysis with sender context
                analysis = mail_brain.process_email(email['snippet'], email['from'])
                print(f"\n⚡ Quick Analysis:")
                print(f"• Type: {analysis['intent']['label']} ({analysis['intent']['score']:.0%} confidence)")
                if analysis['intent'].get('details', {}).get('group'):
                    print(f"• Category: {analysis['intent']['details']['group']}")
                print(f"• Priority: {analysis['importance'].upper()}")
                print(f"• Suggested Actions: {', '.join(analysis['actions']) if analysis['actions'] else 'None'}")
                
                action = input("\nActions: (v)iew, (r)eply, (f)orward, (a)rchive, (b)reak, (n)ext: ").lower()
                if action == 'v':
                    mail_brain.view_full_email(service, email['id'])
                elif action == 'r':
                    mail_brain.compose_reply(service, email)
                elif action == 'f':
                    mail_brain.forward_email(service, email['id'])
                elif action == 'a':
                    if mail_brain.change_email_label(service, email['id']):
                        print("Email archived")
                    else:
                        print("Failed to archive")
                elif action == 'b':
                    break

        elif choice == "2":
            # View labeled emails
            print("\nAvailable Labels:")
            mail_brain.list_labels()  # Shows available labels
            
            label_name = input("\nEnter label name to filter (or 'back'): ")
            if label_name.lower() == 'back':
                continue
                
            print(f"\nFetching emails with label: {label_name}")
            labeled_emails = mail_brain.get_latest_emails(label_ids=[label_name])
            
            if not labeled_emails:
                print(f"No emails found with label: {label_name}")
                continue
                
            for email in labeled_emails[:10]:  # Show first 10
                print(f"\n✉️ {email['subject']}")
                print(f"From: {email['from']}")
                print(f"Date: {email['date']}")
                
                # Quick analysis for context
                analysis = mail_brain.process_email(email.get('snippet', ''), email['from'])
                print(f"Type: {analysis['intent']['label']}")
                
                action = input("(v)iew, (c)hange label, (n)ext: ").lower()
                if action == 'v':
                    mail_brain.view_full_email(service, email['id'])
                elif action == 'c':
                    new_label = input("Enter new label: ")
                    mail_brain.change_email_label(service, email['id'], [label_name], [new_label])

        elif choice == "3":
            # Gmail API Search with enhanced results
            print("\n" + "="*20 + " GMAIL SEARCH " + "="*20)
            print("\nSearch Options:")
            print("1. Quick Search (keywords)")
            print("2. Advanced Search")
            print("3. Search Unread")
            print("4. Back to main menu")
            
            search_choice = input("Choose search type (1-4): ")
            
            if search_choice == "1":
                query = input("Enter search terms: ")
                if not query:
                    continue
                    
                try:
                    results = service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=20
                    ).execute()
                    gmail_handler.display_gmail_search_results(service, results)
                    
                except dependencies.HttpError as error:
                    print(f"Search failed: {error}")

            elif search_choice == "2":
                print("\nAdvanced Search Options:")
                print("a) From specific sender")
                print("b) With attachments")
                print("c) Within date range")
                print("d) Label-specific")
                print("e) Combination search")
                
                advanced_choice = input("Choose option (a-e): ").lower()
                
                query_parts = []
                if advanced_choice in ['a', 'e']:
                    sender = input("From address (leave blank to skip): ")
                    if sender:
                        query_parts.append(f"from:{sender}")
                        
                if advanced_choice in ['b', 'e']:
                    if input("Only with attachments? (y/n): ").lower() == 'y':
                        query_parts.append("has:attachment")
                        
                if advanced_choice in ['c', 'e']:
                    date_from = input("From date (YYYY-MM-DD or blank): ")
                    date_to = input("To date (YYYY-MM-DD or blank): ")
                    if date_from:
                        query_parts.append(f"after:{date_from}")
                    if date_to:
                        query_parts.append(f"before:{date_to}")
                        
                if advanced_choice in ['d', 'e']:
                    mail_brain.list_labels()
                    label = input("Label name to filter (blank for none): ")
                    if label:
                        query_parts.append(f"label:{label}")
                        
                query = " ".join(query_parts)
                if not query:
                    print("No search criteria specified")
                    continue
                    
                try:
                    results = service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=20
                    ).execute()
                    gmail_handler.display_gmail_search_results(service, results)
                    
                except dependencies.HttpError as error:
                    print(f"Advanced search failed: {error}")

            elif search_choice == "3":
                try:
                    results = service.users().messages().list(
                        userId='me',
                        q="is:unread",
                        maxResults=20
                    ).execute()
                    print("\n=== UNREAD EMAILS ===")
                    gmail_handler.display_gmail_search_results(service, results)
                    
                except dependencies.HttpError as error:
                    print(f"Failed to fetch unread emails: {error}")

        elif choice == "4":
            # Compose new email
            print("\n" + "="*20 + " COMPOSE " + "="*20)
            recipient = input("To: ")
            subject = input("Subject: ")
            body = input("Message (type '//end' on new line to finish):\n")
            
            while True:
                line = input()
                if line == "//end":
                    break
                body += "\n" + line
                
            confirm = input(f"\nSend to {recipient}? (y/n): ").lower()
            if confirm == 'y':
                gmail_handler.send_email(service, recipient, subject, body)
                print("Email sent successfully!")
                
        elif choice == "5":
            # Draft management
            print("\n" + "="*20 + " DRAFTS " + "="*20)
            drafts = gmail_handler.get_drafts(service)
            
            if not drafts:
                print("No drafts found.")
                continue
                
            for i, draft in enumerate(drafts, 1):
                print(f"\n{i}. {draft['subject']}")
                print(f"   Last modified: {draft['date']}")
                
            # action = input("\n(e)dit, (s)end, (d)elete, (b)ack: ").lower()
            # Draft management logic would go here

        elif choice == "6":
            # Thread analysis with enhanced processing
            thread_id = input("\nEnter thread ID to analyze: ")
            thread_emails = db_email_manager.get_thread_emails(thread_id)
            
            if not thread_emails:
                print("Thread not found.")
                continue
                
            print(f"\nThread Analysis ({len(thread_emails)} messages)")
            combined_text = "\n".join([e['body'] for e in thread_emails])
            analysis = mail_brain.process_email(combined_text)
            
            print(f"\n🧵 Thread Summary:")
            print(analysis['summary'])
            print(f"\n🔍 Key Insights:")
            print(f"- Primary Intent: {analysis['intent']['label']} (confidence: {analysis['intent']['score']:.0%})")
            if analysis['intent'].get('details', {}).get('group'):
                print(f"- Category Group: {analysis['intent']['details']['group']}")
            print(f"- Overall Sentiment: {analysis['sentiment']['label']}")
            print(f"- Required Actions: {', '.join(analysis['actions'])}")

        elif choice == "7":
            # Archive/cleanup
            print("\n" + "="*20 + " CLEANUP " + "="*20)
            print("1. Archive read emails older than 30 days")
            print("2. Delete spam emails")
            print("3. Cleanup large attachments")
            
            cleanup_choice = input("Choose action (1-3): ")
            # Cleanup logic would go here

        elif choice == "8":
            # Account settings
            print("\n" + "="*20 + " SETTINGS " + "="*20)
            print("1. Change notification preferences")
            print("2. Configure auto-responses")
            print("3. Manage connected apps")
            # Settings logic would go here

        elif choice == "9":
            break
            
        else:
            print("Invalid choice. Please try again.")

def initialize_automated():
    utils_email_core.clear_terminal()
    
    service = connectors.get_gmail_service()
    creds = connectors.get_gmail_credentials()

    print("\n" + "="*50)
    print("AUTOMATED MODE".center(50))
    print("="*50)

    print("\nStarting to check new mails ....")
    emails = gmail_handler.get_latest_emails(max_results=10)

    if not emails:
        print("No new emails found.")
        return
        
    for i, email in enumerate(emails, 1):
        print(f"\n{i}/{len(emails)}")
        print(f"📩 From: {email['from']}")
        print(f"📌 Subject: {email['subject']}")
        print(f"📅 Date: {email['date']}")
        print(f"🔍 Snippet: {email['snippet']}")

        print("\nAnalyzing the Mail ......")
        analysis = mail_brain.process_email(
            email['body'] if 'body' in email else email['snippet'],
            email.get('from', '')
        )
        
        #utils_email_core.log_email_action(email, analysis)  # Log email action

        print(f"\n🔍 Intent:    {analysis['intent']['label'].upper()}")
        print(f"📊 Importance: {analysis['importance'].upper()}")
        print(f"💭 Sentiment:  {analysis['sentiment']['label'].title()} ({analysis['sentiment']['score']:.0%})")
        print("\n📝 Summary:")
        print(utils_email_core.wrap_text(analysis['summary'], width=50))

        if analysis['intent']['label'] in ['newsletter', 'promotional']:
            if mail_brain.change_email_label(service, email['id']):
                print("📥 Auto-archived low-priority email.")
        elif analysis['intent']['score'] > 0.90:
            mail_brain.categorize_email(service, email['id'], analysis)
            print("✅ Automatically categorized based on confidence.")
        else:  
            action = utils_email_core.input_with_timeout(
                f"\nShould I categorize & label this email? (y/n): ",
                timeout=15
            )   
            try:
                if action is None:  # Timeout occurred
                    pass
                elif action.lower() in ["y", "yes"]:
                    mail_brain.categorize_email(service, email['id'], analysis)
                else:
                    pass
            except:
                pass 

        if analysis['importance'] == 'high':
            engine = dependencies.pyttsx3.init()
            engine.say(f"You received an important email from {email['from']}")
            engine.runAndWait()

        while(True):
            action = utils_email_core.input_with_timeout(
                "\nActions: (v)iew, (r)eply, (f)orward, (a)rchive, (b)reak, (n)ext : ",
                timeout=60
            )
            
            if action is None:  # Timeout occurred
                continue
            action = action.lower()

            if action == 'v':
                mail_brain.view_full_email(service, email['id'])
            elif action == 'r':
                mail_brain.compose_reply(service, email)
            elif action == 'f':
                mail_brain.forward_email(service, email['id'])
            elif action == 'n' :
                break
            elif action == 'a':
                if mail_brain.change_email_label(service, email['id']):
                    print("Email archived")
                else:
                    print("Failed to archive")
            elif action == 'b':
                break
    
    utils_email_core.waiting_message(10)

initialize_automated()