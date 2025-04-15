import dependencies


def clear_terminal():
    """Clear the terminal screen cross-platform"""
    if dependencies.platform.system() == "Windows":
        dependencies.os.system('cls')  # For Windows
    else:
        dependencies.os.system('clear')  # For Linux/Mac

def input_with_timeout(prompt, timeout):
    """Get user input with a timeout"""
    print(prompt, end='', flush=True)
    result = [None]  # Using list to allow modification in nested function
    
    def get_input():
        try:
            result[0] = input()
        except:
            pass  # If input is interrupted
    
    input_thread = dependencies.threading.Thread(target=get_input)
    input_thread.daemon = True
    input_thread.start()
    input_thread.join(timeout)
    
    if input_thread.is_alive():
        clear_terminal()
        print("\nTimeout reached, continuing to next email...")
        return None
    return result[0]

def waiting_message(delay_minutes=5):
    """Display a professional waiting message with interrupt handling"""
    delay_seconds = delay_minutes * 60
    
    try:
        print("\n" + "="*50)
        print(f"📭 No new emails found".center(50))
        print("="*50)
        print(f"\n⏳ Next check in {delay_minutes} minutes (Press Ctrl+C to exit)")
        print("🔄 Monitoring continues automatically...")
        
        # Progress indicator during wait
        for remaining in range(delay_seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            print(f"\r⏱️  Next check in: {mins:02d}:{secs:02d}", end="", flush=True)
            dependencies.time.sleep(1)
            
        print("\n\n" + "="*50)
        print(f"🔄 Checking for new emails".center(50))
        print("="*50 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n" + "="*50)
        print(f"🛑 Automated monitoring stopped".center(50))
        print("="*50)
        print("\nThank you for using the email monitoring service.\n")
        dependencies.sys.exit(0)

def log_email_action(email, analysis):
    """
    Logs email info and analysis to a daily log file.

    Args:
        email (dict): Email data with keys like 'from', 'subject', 'date', 'id'.
        analysis (dict): Processed analysis containing 'intent', 'importance', 'sentiment', and 'summary'.
    """
    log_dir = "logs"
    dependencies.os.makedirs(log_dir, exist_ok=True)  # Ensure logs/ directory exists

    log_file = dependencies.os.path.join(log_dir, f"email_log_{dependencies.datetime.now().date()}.txt")

    try:
        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"\n[{email.get('date', dependencies.datetime.now())}] ID: {email.get('id', 'N/A')}\n")
            log.write(f"From    : {email.get('from', 'Unknown')}\n")
            log.write(f"Subject : {email.get('subject', 'No Subject')}\n")
            log.write(f"Intent  : {analysis['intent']['label']} | Importance: {analysis['importance']}\n")
            log.write(f"Sentiment: {analysis['sentiment']['label']} ({analysis['sentiment']['score']:.0%})\n")
            log.write(f"Summary : {analysis['summary']}\n")
            log.write("="*50 + "\n")
    except Exception as e:
        print(f"❌ Logging failed: {e}")

def wrap_text(text, width=50):
    from textwrap import fill
    return fill(text, width=width)
