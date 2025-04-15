import text_model_utils
import gmail_handler
import dependencies


def list_labels():
    service = gmail_handler.get_gmail_service()
    if not service:
        print("Failed to create Gmail service.")
        return

    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            print("No labels found.")
            return

        print("Labels:")
        for label in labels:
            print(f"{label['name']} - {label['id']}")
    except Exception as error:
        print(f'An error occurred: {error}')

def parse_email(msg):
    """Extract structured data from raw Gmail message"""
    payload = msg['payload']
    headers = {h['name']: h['value'] for h in payload['headers']}
    
    body = {
        'plain': extract_body(payload, 'text/plain'),
        'html': extract_body(payload, 'text/html')
    }
    
    attachments = [
        {
            'id': part['body']['attachmentId'],
            'filename': part['filename'],
            'mime_type': part['mimeType'],
            'size': part['body'].get('size', 0)
        }
        for part in payload.get('parts', [])
        if 'attachmentId' in part['body']
    ]
    
    return {
        'headers': headers,
        'body': body,
        'attachments': attachments,
        'labels': msg.get('labelIds', [])
    }

def extract_body(payload, mime_type):
    """Extract email body by MIME type from message payload"""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == mime_type and 'body' in part and 'data' in part['body']:
                return dependencies.base64.urlsafe_b64decode(part['body']['data']).decode()
    elif payload['mimeType'] == mime_type and 'body' in payload and 'data' in payload['body']:
        return dependencies.base64.urlsafe_b64decode(payload['body']['data']).decode()
    return None

def extract_body_from_mime(mime_msg):
    """Extract the plain text body from a MIME email message"""
    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode()
    else:
        return mime_msg.get_payload(decode=True).decode()

    return ""

def summarize_email(text):
    summary = text_model_utils.summarizer(text, max_length=60, min_length=25, do_sample=False)
    return summary[0]['summary_text']

def analyze_sentiment(text):
    result = text_model_utils.sentiment_analyzer(text)
    return result[0]['label'], result[0]['score']

def extract_actions(text):
    actions = dependencies.re.findall(r'\b(schedule|confirm|review|reply|attach|send|reschedule|cancel|approve|reject)\b', text.lower())
    return list(set(actions))

def classify_intent(text, sender_address=""):
    """
    Unified email classifier that predicts across all categories equally
    Returns: {'label': str, 'score': float, 'details': {subtypes: [], predictions: []}}
    """
    # Combined category system (platform + business)
    all_categories = [
        # Financial Services
        'bank_statement',
        'credit_card_statement',
        'investment_statement',
        'tax_document',
        'invoice',
        'payment_receipt',
        'fraud_alert',
        'credit_score_update',
        
        # E-Commerce/Retail
        'order_confirmation',
        'shipping_notification',
        'delivery_update',
        'return_processing',
        'promotional_offer',
        'loyalty_reward',
        'product_review_request',
        
        # Social/Networking
        'connection_request',
        'endorsement_notification',
        'profile_view_notification',
        'group_invitation',
        'event_invitation',
        'direct_message',
        
        # Job/Career
        'job_application',
        'interview_invite',
        'recruiter_inquiry',
        'offer_letter',
        'reference_request',
        'resume_request',
        'rejection_notice',
        
        # Education
        'course_enrollment',
        'assignment_submission',
        'grade_notification',
        'scholarship_opportunity',
        'campus_announcement',
        'alumni_newsletter',
        
        # Travel
        'flight_itinerary',
        'hotel_booking',
        'car_rental_confirmation',
        'boarding_pass',
        'travel_alert',
        'visa_application',
        
        # Health
        'appointment_confirmation',
        'medical_report',
        'prescription_refill',
        'insurance_claim',
        'wellness_tip',
        
        # Government
        'voter_registration',
        'tax_notice',
        'license_renewal',
        'public_alert',
        'census_survey',
        
        # Technology
        'software_update',
        'password_reset',
        'two_factor_auth',
        'data_breach_notice',
        'subscription_renewal',
        
        # Personal Communication
        'personal_message',
        'family_update',
        'holiday_greeting',
        'birthday_invitation',
        'wedding_announcement',
        
        # Business Operations
        'meeting_request',
        'project_update',
        'contract_review',
        'nda_request',
        'board_meeting_minutes',
        
        # Customer Support
        'complaint_response',
        'refund_processing',
        'technical_support',
        'feedback_request',
        'account_verification'
    ]

    # 1. First check for strong domain/keyword signals
    domain = sender_address.split('@')[-1].lower() if '@' in sender_address else ''
    text_lower = text.lower()
    
    # Domain-based boosts
    domain_boosts = {
        # Financial Institutions
        'bank': ['bank_statement', 'fraud_alert'],
        'paypal': ['payment_receipt', 'invoice'],
        'stripe': ['payment_processing', 'invoice'],
        
        # E-Commerce
        'amazon': ['order_confirmation', 'shipping_notification'],
        'ebay': ['bid_notification', 'auction_alert'],
        'aliexpress': ['order_update', 'tracking_notification'],
        
        # Social Media
        'facebook': ['friend_request', 'event_invitation'],
        'twitter': ['verification_request', 'trending_alert'],
        'instagram': ['direct_message', 'tag_notification'],
        
        # Job Portals
        'linkedin': ['connection_request', 'job_alert'],
        'indeed': ['application_confirmation', 'recruiter_message'],
        'monster': ['resume_view', 'career_suggestion'],
        
        # Email Providers
        'gmail': ['security_alert', 'storage_notice'],
        'outlook': ['login_attempt', 'quota_warning'],
        
        # Government
        'gov': ['tax_notice', 'license_renewal'],
        'irs': ['tax_document', 'refund_notice'],
        
        # Travel
        'expedia': ['hotel_booking', 'flight_change'],
        'airbnb': ['reservation_confirmation', 'host_message'],
        
        # Education
        'edu': ['grade_notification', 'tuition_notice'],
        'coursera': ['course_completion', 'certificate_ready']
    }
    
    # Keyword-based boosts
    keyword_boosts = {
        # Financial Triggers
        'your statement is ready': 'bank_statement',
        'payment of $': 'invoice',
        'unusual login attempt': 'fraud_alert',
        
        # E-Commerce Triggers
        'your order has shipped': 'shipping_notification',
        'tracking number': 'delivery_update',
        'limited time offer': 'promotional_offer',
        
        # Career Triggers
        'we would like to interview': 'interview_invite',
        'congratulations on being selected': 'offer_letter',
        'reference check': 'reference_request',
        
        # Travel Triggers
        'boarding pass for': 'boarding_pass',
        'flight cancellation': 'travel_alert',
        'check-in available': 'flight_itinerary',
        
        # Health Triggers
        'appointment reminder': 'appointment_confirmation',
        'test results': 'medical_report',
        'prescription ready': 'prescription_refill',
        
        # Urgent Triggers
        'action required': 'account_verification',
        'immediate attention': 'fraud_alert',
        'deadline approaching': 'project_update',
        
        # Personal Triggers
        'save the date': 'wedding_announcement',
        'you\'re invited to': 'birthday_invitation',
        'family reunion': 'family_update'
    }

    # 2. Prepare boosted candidates
    boosted_candidates = {}
    
    # Apply domain boosts
    for domain_part, categories in domain_boosts.items():
        if domain_part in domain:
            for cat in categories:
                boosted_candidates[cat] = 0.2  # Confidence boost

    # Apply keyword boosts
    for keyword, category in keyword_boosts.items():
        if keyword in text_lower:
            boosted_candidates[category] = 0.15  # Smaller boost for keywords alone

    # 3. Run classification on all categories
    base_result = text_model_utils.classifier(text, all_categories)
    
    # 4. Apply boosts to relevant categories
    final_scores = []
    for label, score in zip(base_result['labels'], base_result['scores']):
        boosted_score = score + boosted_candidates.get(label, 0)
        final_scores.append((label, min(boosted_score, 1.0)))  # Cap at 1.0

    # 5. Sort by final confidence
    final_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 6. Group related categories for subtype detection
    category_groups = {
        'financial': [
            'bank_statement',
            'credit_card_statement',
            'investment_statement',
            'tax_document',
            'invoice',
            'payment_receipt'
        ],
        'ecommerce': [
            'order_confirmation',
            'shipping_notification',
            'delivery_update',
            'return_processing',
            'promotional_offer'
        ],
        'career': [
            'job_application',
            'interview_invite',
            'recruiter_inquiry',
            'offer_letter',
            'reference_request'
        ],
        'urgent': [
            'fraud_alert',
            'travel_alert',
            'data_breach_notice',
            'technical_support',
            'payment_request'
        ],
        'social': [
            'connection_request',
            'event_invitation',
            'direct_message',
            'profile_view_notification',
            'group_invitation'
        ],
        'health': [
            'appointment_confirmation',
            'medical_report',
            'prescription_refill',
            'insurance_claim',
            'wellness_tip'
        ],
        'education': [
            'course_enrollment',
            'assignment_submission',
            'grade_notification',
            'scholarship_opportunity',
            'campus_announcement'
        ]
    }

    # Determine if primary label belongs to any group
    primary_label = final_scores[0][0]
    group = next(
        (g for g, members in category_groups.items() if primary_label in members),
        None
    )

    return {
        'label': primary_label,
        'score': final_scores[0][1],
        'details': {
            'group': group,
            'all_predictions': final_scores,
            'triggers': {
                'domain': domain if any(d in domain for d in domain_boosts) else None,
                'keywords': [k for k in keyword_boosts if k in text_lower] or None
            }
        }
    }

def classify_importance(text):
    """Enhanced importance classification with comprehensive keywords"""
    important_keywords = [
        # Urgency indicators
        'urgent', 'asap', 'immediately', 'time-sensitive', 
        'right away', 'without delay', 'prompt attention',
        
        # Priority markers
        'important', 'critical', 'high priority', 'top priority',
        'essential', 'vital', 'crucial',
        
        # Deadline language
        'deadline', 'due by', 'by EOD', 'by COB', 
        'today by', 'must respond by', 'time is of the essence',
        
        # Consequence language
        'action required', 'mandatory', 'cannot proceed without',
        'blocking issue', 'compliance matter', 'legal notice',
        
        # Executive language
        'ceo request', 'leadership directive', 'board matter',
        'investor concern', 'regulatory requirement',
        
        # Financial impact
        'revenue impact', 'cost saving', 'budget approval',
        'payment due', 'contract signing',
        
        # Risk language
        'security incident', 'data breach', 'system outage',
        'service disruption', 'emergency fix'
    ]
    
    text_lower = text.lower()
    if any(dependencies.re.search(rf'\b{dependencies.re.escape(word)}\b', text_lower) for word in important_keywords):
        return "High"
    elif any(word in text_lower for word in ['reminder', 'follow-up', 'when convenient']):
        return "Medium"
    else:
        return "Normal"

def process_email(email_content, sender_address=""):
    """
    Process email content using enhanced classification
    Returns dict with analysis results
    """
    if not email_content:
        return {
            'intent': {'label': 'unknown', 'score': 0},
            'summary': '',
            'importance': 'low',
            'actions': [],
            'sentiment': {'label': 'neutral', 'score': 0}
        }

    try:
        # 1. Enhanced Intent Classification
        intent_result = classify_intent(email_content, sender_address)
        
        # 2. Sentiment Analysis
        sentiment_result = text_model_utils.sentiment_analyzer(email_content)[0] if text_model_utils.sentiment_analyzer else {'label': 'neutral', 'score': 0}
        
        # 3. Importance Determination
        importance = 'low'
        if intent_result['score'] > 0.85 or intent_result['label'] in [
            'payment_request', 'technical_issue', 'deadline_extension',
            'zerodha_trade_alert', 'interview_invite'
        ]:
            importance = 'high'
        elif intent_result['score'] > 0.7 or intent_result['label'] in [
            'question', 'request', 'meeting', 'job_posting'
        ]:
            importance = 'medium'
            
        # 4. Action Determination
        actions = []
        if intent_result['label'] in ['question', 'request', 'recruiter_message']:
            actions.append('reply')
        if intent_result['label'] in ['meeting', 'interview_invite']:
            actions.append('calendar')
        if intent_result['label'] in ['payment_request', 'billing_question']:
            actions.append('finance')
        if intent_result['label'] in ['zerodha_statement', 'zerodha_notification']:
            actions.append('archive')
            
        # 5. Generate Summary
        summary = text_model_utils.summarizer(email_content, max_length=100, min_length=30, do_sample=False)[0]['summary_text'] if text_model_utils.summarizer else email_content[:200] + "..."
        
        return {
            'intent': intent_result,
            'summary': summary,
            'importance': importance,
            'actions': actions,
            'sentiment': sentiment_result
        }
        
    except Exception as e:
        print(f"Error processing email: {e}")
        return {
            'intent': {'label': 'error', 'score': 0},
            'summary': str(e),
            'importance': 'low',
            'actions': [],
            'sentiment': {'label': 'neutral', 'score': 0}
        }

def extract_name(email_address):
    """Extract name from email address"""
    if "@" not in email_address:
        return email_address
    name_part = email_address.split("@")[0]
    return " ".join([part.capitalize() for part in name_part.split(".")])

def get_gmail_label(intent_label,CATEGORY_GROUPS):
    for category, labels in CATEGORY_GROUPS.items():
        if intent_label in labels:
            return category
    return 'Uncategorized'

def categorize_email(service, email_id, analysis):
    CATEGORY_GROUPS = {
        'Finance': [
            'bank_statement', 'credit_card_statement', 'investment_statement',
            'tax_document', 'invoice', 'payment_receipt', 'credit_score_update'
        ],
        'Shopping': [
            'order_confirmation', 'shipping_notification', 'delivery_update',
            'return_processing', 'promotional_offer', 'loyalty_reward',
            'product_review_request'
        ],
        'Jobs': [
            'job_application', 'interview_invite', 'recruiter_inquiry',
            'offer_letter', 'reference_request', 'resume_request', 'rejection_notice'
        ],
        'Education': [
            'course_enrollment', 'assignment_submission', 'grade_notification',
            'scholarship_opportunity', 'campus_announcement', 'alumni_newsletter'
        ],
        'Social': [
            'connection_request', 'endorsement_notification', 'profile_view_notification',
            'group_invitation', 'event_invitation', 'direct_message'
        ],
        'Travel': [
            'flight_itinerary', 'hotel_booking', 'car_rental_confirmation',
            'boarding_pass', 'travel_alert', 'visa_application'
        ],
        'Health': [
            'appointment_confirmation', 'medical_report', 'prescription_refill',
            'insurance_claim', 'wellness_tip'
        ],
        'Government': [
            'voter_registration', 'tax_notice', 'license_renewal',
            'public_alert', 'census_survey'
        ],
        'Technology': [
            'software_update', 'password_reset', 'two_factor_auth',
            'data_breach_notice', 'subscription_renewal'
        ],
        'Personal': [
            'personal_message', 'family_update', 'holiday_greeting',
            'birthday_invitation', 'wedding_announcement'
        ],
        'Work': [
            'meeting_request', 'project_update', 'contract_review',
            'nda_request', 'board_meeting_minutes'
        ],
        'Support': [
            'complaint_response', 'refund_processing', 'technical_support',
            'feedback_request', 'account_verification'
        ],
        'Security': [
            'fraud_alert', 'travel_alert', 'data_breach_notice',
            'technical_support', 'payment_request', 'urgent'
        ]
    }

    try:
        intent_label = analysis['intent']['label']
        gmail_label = get_gmail_label(intent_label,CATEGORY_GROUPS)

        if analysis.get('importance') == 'high':
            gmail_label = f"Priority_{gmail_label}"


        label_id = get_or_create_label(service, gmail_label)
        print(f"✅ Applying label '{gmail_label}' with ID {label_id}")

        service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': [label_id]}
        ).execute()

        print(f"🏷️ Categorized as: {gmail_label}")
        return True

    except Exception as e:
        print(f"❌ Failed to categorize email: {str(e)}")
        return False

def get_or_create_label(service, label_name):
    """
    Get existing label ID or create new one
    
    Args:
        service: Gmail API service
        label_name: Desired label name
        
    Returns:
        str: Label ID
    """
    # Check if label exists
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    
    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']
    
    # Create new label if not exists
    label_body = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    
    created_label = service.users().labels().create(
        userId='me',
        body=label_body
    ).execute()
    
    print(f"🏷️ Created new label: {label_name}")
    return created_label['id']

