import dependencies


def get_db_connection(db_config):
    """Establish MySQL connection with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = dependencies.mysql.connector.connect(
                host=db_config['host'],
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                autocommit=False
            )
            return conn
        except dependencies.Error as err:
            if attempt == max_retries - 1:
                raise err
            print(f"Connection failed (attempt {attempt + 1}): {err}")
            dependencies.time.sleep(2)

def get_gmail_credentials():
    """Get valid credentials for Gmail API with improved error handling."""
    creds = None
    token_file = "token.json"
    credentials_file = "credentials.json"
    
    if not dependencies.os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"'{credentials_file}' not found. Please download it from Google Cloud Console."
        )

    if dependencies.os.path.exists(token_file):
        try:
            creds = dependencies.Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception as e:
            print(f"Error loading token: {e}")
            dependencies.os.remove(token_file)
            creds = None

    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(dependencies.Request())
            else:
                flow = dependencies.InstalledAppFlow.from_client_secrets_file(
                    credentials_file,
                    SCOPES,
                    redirect_uri="http://localhost:8080"
                )
                creds = flow.run_local_server(port=8080, open_browser=True)
            
            with open(token_file, "w") as token:
                token.write(creds.to_json())
                
        except Exception as e:
            print(f"Authentication failed: {e}")
            print("Make sure:")
            print("1. You've enabled Gmail API in Google Cloud Console")
            print("2. You've added your email as a test user in OAuth consent screen")
            print("3. Your 'credentials.json' is valid")
            raise

    return creds

def get_gmail_service():
    """Build and return the Gmail API service with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            creds = get_gmail_credentials()
            return dependencies.build("gmail", "v1", credentials=creds)
        except dependencies.HttpError as error:
            if error.resp.status == 403 and attempt < max_retries - 1:
                print(f"Rate limited, retrying... (Attempt {attempt + 1}/{max_retries})")
                continue
            raise
        except Exception as e:
            print(f"Failed to create Gmail service: {e}")
            raise

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
]

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'email_assistant_db'
}
