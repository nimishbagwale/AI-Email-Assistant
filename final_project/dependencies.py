import os.path
import base64
import time
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage
import mysql.connector
from datetime import datetime
from mysql.connector import Error
import torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
import random
import threading
import platform
import sys
import pyttsx3
import os
import regex as re
from datetime import timedelta
from email import message_from_bytes