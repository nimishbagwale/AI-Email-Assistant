# AI Email Assistant 🤖📧

An intelligent email management system that automates email processing, categorization, and response generation using NLP and the Gmail API. It supports both **interactive** and **automated** modes for seamless email handling.

---

## 📚 Table of Contents

1. [How to Use the Project](#1-how-to-use-the-project)
2. [Gmail API Setup](#2-gmail-api-setup)
3. [Database Configuration](#3-database-configuration)
4. [Features](#4-features)
5. [Dependencies](#5-dependencies)
6. [Running the Project 🖥️](#6-running-the-project-️)
7. [Troubleshooting 🔧](#7-troubleshooting-)
8. [Contact 📬](#8-contact-)

---

## 1. How to Use the Project

The assistant provides two main modes:

### 🔹 Interactive Mode
- Menu-driven interface for manual email management
- View, reply, forward, and categorize emails
- Search and analyze email threads

### 🔹 Automated Mode
- Background processing of incoming emails
- Automatic categorization based on content
- Priority handling of important emails
- Scheduled email checks

---

## 2. Gmail API Setup

To use this project, set up Gmail API access:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (select "Desktop App")
5. Download the `credentials.json` file
6. Place it in the project root directory

On first run, the application will open a browser window for Gmail authentication and generate a `token.json`.

---

## 3. Database Configuration

This project uses MySQL for persistent email storage.

1. Install MySQL (if not already installed)
2. Create a database named `email_assistant_db`
3. Configure your credentials in `db_config.py` or a `.env` file:

```bash
# .env example
DB_HOST=localhost
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=email_assistant_db

---

## 4. Features

### 🔹 Smart Email Processing
- ✨ NLP-powered classification:
  - **Intent detection**
  - **Sentiment analysis**
  - **Importance assessment**
- 🏷️ Automatic labeling and categorization
- 🧵 Email thread analysis for tracking conversations

### 🔹 Email Management
- 🤖 AI-generated email replies with contextual understanding
- ⏰ Scheduled email checks at user-defined intervals
- 📎 Attachment handling with metadata extraction
- 💾 Full database storage for processed emails and interactions

### 🔹 User Interface
- 🖥️ Interactive command-line interface with intuitive menus
- ⚙️ Automated background mode for continuous monitoring
- 🔔 Notifications for priority or important messages

---

## 5. Dependencies

To run this project, the following Python libraries are required:

- `python >= 3.8`
- `google-api-python-client`
- `google-auth-oauthlib`
- `mysql-connector-python`
- `transformers`
- `torch`
- `python-dotenv`
- `pyttsx3`

You can install all dependencies using:
```bash
pip install -r requirements.txt
