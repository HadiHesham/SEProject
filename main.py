import os
import sys
import threading
import webbrowser
from datetime import datetime
from base64 import b64encode
from urllib.parse import urlencode

import requests
import mysql.connector
import assemblyai as aai
import cohere
from flask import Flask, request

from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
                             QTextEdit, QMessageBox, QScrollArea, QMainWindow, QTabWidget, QDialog, QHBoxLayout)
from PyQt5.QtGui import QPixmap, QFont, QCursor
from PyQt5.QtCore import Qt

# === ZOOM SETTINGS ===
CLIENT_ID = "8_5UvIPJQCWGkg7au8TJCg"
CLIENT_SECRET = "QH9ZEnKH6tJYuha56sy04fk2uev2I3eT"
REDIRECT_URI = "http://localhost:8000/callback"
access_token = None
user_id = None
meeting_id = None
meeting_link = None
HARDCODED_PATH = r"C:\\Users\\hadig\\OneDrive\\Documents\\Zoom"

# === FLASK FOR ZOOM OAUTH ===
app = Flask(__name__)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if code:
        window.handle_oauth_callback(code)
        return "Authentication successful! You can now close this window."
    return "Authentication failed."

def run_flask():
    app.run(host="localhost", port=8000)

# === DATABASE CONNECTION ===
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Dodo1977",
        database="notabot"
    )

# === DATABASE OPERATIONS ===
def save_meeting(meeting_id, ZOOM_USER_ID):
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT IGNORE INTO meetings (meetingID, host_username) VALUES (%s, %s)", (meeting_id, ZOOM_USER_ID))
    db.commit()
    cur.close()
    db.close()

def save_transcription(meeting_id, text):
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO transcriptions (meetingID, content, upload_date) VALUES (%s, %s, %s)",
                (meeting_id, text, datetime.now()))
    db.commit()
    cur.close()
    db.close()

def save_summary(meeting_id, summary):
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO summaries (meetingID, content, upload_date) VALUES (%s, %s, %s)",
                (meeting_id, summary, datetime.now()))
    db.commit()
    cur.close()
    db.close()

def save_recording(meeting_id, path):
    with open(path, "rb") as file:
        blob = file.read()
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO recordings (meetingID, data, upload_date) VALUES (%s, %s, %s)",
                (meeting_id, blob, datetime.now()))
    db.commit()
    cur.close()
    db.close()

def fetch_user_data(query):
    db = get_db()
    cur = db.cursor()
    cur.execute(query, (user_id,))
    results = cur.fetchall()
    cur.close()
    db.close()
    return results

# === ZOOM API FUNCTIONS ===
def get_zoom_auth_url():
    auth_url = "https://zoom.us/oauth/authorize"
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI
    }
    return f"{auth_url}?{urlencode(params)}"

def get_access_token_from_code(code):
    url = "https://zoom.us/oauth/token"
    headers = {
        "Authorization": "Basic " + b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def get_user_info(token):
    url = "https://api.zoom.us/v2/users/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json().get("id") if response.status_code == 200 else None

def create_permanent_meeting(uid, token):
    url = f"https://api.zoom.us/v2/users/{uid}/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    meeting_data = {
        "topic": "Always-On Meeting Room",
        "type": 3,
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "local",
            "mute_upon_entry": True,
        }
    }
    response = requests.post(url, headers=headers, json=meeting_data)
    if response.status_code == 201:
        data = response.json()
        return data.get("join_url"), data.get("id")
    return None, None

def delete_record_from_db(table, meeting_id):
    db = get_db()
    cur = db.cursor()
    cur.execute(f"DELETE FROM {table} WHERE meetingID = %s", (meeting_id,))
    db.commit()
    cur.close()
    db.close()

# === FILE OPERATIONS ===

def get_all_folders(path):
    return sorted([os.path.join(path, d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])

def get_audio_files_by_name(path):
    audio_files = []
    for foldername, _, filenames in os.walk(path):
        for filename in filenames:
            if 'audio' in filename.lower() or filename.endswith('.mp4'):
                audio_files.append(os.path.join(foldername, filename))
    return audio_files

def transcribe_and_summarize(callback):
    callback("🔄 Transcribing...")
    folders = get_all_folders(HARDCODED_PATH)
    if not folders:
        callback("❌ No folders found.")
        return
    audio_files = get_audio_files_by_name(folders[-1])
    if not audio_files:
        callback("❌ No audio files found.")
        return
    recording = audio_files[0]
    aai.settings.api_key = "9b6873a6c96d4447a3ab239f7e1f8ff6"
    transcript = aai.Transcriber().transcribe(recording)
    callback("✍️ Summarizing...")
    co = cohere.Client("sPWAMBrdIlQa47hpIiefcuuqW1bd9KO8JmCG9qER")
    prompt = f"The following is a transcript of a meeting. Please summarize it: {transcript.text}"
    summary = co.chat(model="command-r-plus-08-2024", message=prompt, temperature=0.5, max_tokens=500).text
    with open("meeting_minutes.txt", "w") as f:
        f.write(summary)
    save_transcription(meeting_id, transcript.text)
    save_summary(meeting_id, summary)
    callback("✅ Done! Meeting minutes saved.")
    os.startfile("meeting_minutes.txt")



class NotaBotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NotaBot")
        self.setStyleSheet("""
            QWidget {
                background-color: #e6f2ff;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                padding: 10px;
                font-size: 14px;
                border-radius: 6px;
                margin-right: 100px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #005f99;
            }
            QLabel#statusLabel {
                font-size: 14px;
                color: #444;
            }
            QLabel#titleLabel {
                font-size: 28px;
                font-weight: bold;
                color: #1a1a1a;
            }
            
        """)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        image_path = "WhatsApp Image 2025-03-17 at 2.56.27 PM.jpeg"
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path).scaled(300, 200, Qt.KeepAspectRatio)
            logo = QLabel()
            logo.setPixmap(pixmap)
            logo.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(logo)

        title = QLabel("NotaBot")
        title.setObjectName("titleLabel")
        title.setFont(QFont("Helvetica", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFont(QFont("Helvetica", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        content_layout = QHBoxLayout()
        content_layout.setAlignment(Qt.AlignTop)
        button_layout = QVBoxLayout()
        button_layout.setAlignment(Qt.AlignTop)
        login_btn = QPushButton("Log in to Zoom")
        login_btn.clicked.connect(self.open_zoom_login)
        button_layout.addWidget(login_btn)

        meeting_btn = QPushButton("Get Personal Meeting URL")
        meeting_btn.clicked.connect(self.start_meeting_logic)
        button_layout.addWidget(meeting_btn)

        transcribe_btn = QPushButton("Transcribe and Summarize Meeting")
        transcribe_btn.clicked.connect(lambda: threading.Thread(target=lambda: transcribe_and_summarize(self.update_status)).start())
        button_layout.addWidget(transcribe_btn)

        show_transcripts_btn = QPushButton("Show My Transcriptions")
        show_transcripts_btn.clicked.connect(lambda: self.show_user_data("Transcriptions", "SELECT content FROM transcriptions WHERE meetingID IN (SELECT meetingID FROM meetings WHERE host_username = %s)"))
        button_layout.addWidget(show_transcripts_btn)

        show_summaries_btn = QPushButton("Show My Summaries")
        show_summaries_btn.clicked.connect(lambda: self.show_user_data("Summaries", "SELECT content FROM summaries WHERE meetingID IN (SELECT meetingID FROM meetings WHERE host_username = %s)"))
        button_layout.addWidget(show_summaries_btn)

        show_recordings_btn = QPushButton("Show My Recordings")
        show_recordings_btn.clicked.connect(self.show_recordings)
        button_layout.addWidget(show_recordings_btn)

        content_layout.addLayout(button_layout)

        self.link_btn = QLabel("")
        self.link_btn.setFont(QFont("Helvetica", 12))
        self.link_btn.setStyleSheet("color: blue; text-decoration: underline;")
        self.link_btn.setAlignment(Qt.AlignCenter)
        self.link_btn.mousePressEvent = self.open_meeting_link
        button_layout.addWidget(self.link_btn)
        self.link_btn.hide()



        # Fullscreen Button
        fullscreen_btn = QPushButton("Toggle Fullscreen")
        fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        button_layout.addWidget(fullscreen_btn)

        # === Fetch and display the latest summary from the database ===
        summary_label = QLabel("Latest Summary:")
        summary_label.setFont(QFont("Arial", 14, QFont.Bold))
        summary_label.setAlignment(Qt.AlignLeft)
        content_layout.addWidget(summary_label)

        summary_text = self.get_latest_summary_text()
        summary_box = QTextEdit()
        summary_box.setText(summary_text[0])
        summary_box.setReadOnly(True)
        summary_box.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ccc;")
        summary_box.setAlignment(Qt.AlignLeft)
        content_layout.addWidget(summary_box)

        summary_box = QTextEdit()
        summary_box.setText(summary_text[1])
        summary_box.setReadOnly(True)
        summary_box.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ccc;")
        summary_box.setAlignment(Qt.AlignLeft)
        content_layout.addWidget(summary_box)

        summary_box = QTextEdit()
        summary_box.setText(summary_text[2])
        summary_box.setReadOnly(True)
        summary_box.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ccc;")
        summary_box.setAlignment(Qt.AlignLeft)
        content_layout.addWidget(summary_box)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    def delete_record(self, title, meeting_id, dialog=None):
        # Determine which table to delete from based on the title
        if "transcription" in title.lower():
            table = "transcriptions"
        elif "summary" in title.lower():
            table = "summaries"
        elif "recording" in title.lower():
            table = "recordings"
        else:
            QMessageBox.warning(self, "Error", "Unknown content type.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {title} for meeting {meeting_id}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                db = get_db()
                cur = db.cursor()
                # Use parameterized query to prevent SQL injection
                cur.execute(f"DELETE FROM {table} WHERE meetingID = %s", (meeting_id,))
                db.commit()
                cur.close()
                db.close()

                QMessageBox.information(self, "Deleted", f"{title} for meeting {meeting_id} has been deleted.")
                if dialog:
                    dialog.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete record: {str(e)}")

    def get_latest_summary_text(self):
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT content FROM summaries ORDER BY upload_date DESC LIMIT 3")
            results = cur.fetchall()
            cur.close()
            db.close()

            if results:
                # results is a list of tuples like [(summary1,), (summary2,), (summary3,)]
                return [row[0] for row in results]  # return just the summary text
            else:
                return ["No summaries available yet."]
        except Exception as e:
            return [f"Error fetching summaries: {str(e)}"]

    def update_status(self, text):
        self.status_label.setText(text)

    def open_zoom_login(self):
        webbrowser.open(get_zoom_auth_url())

    def handle_oauth_callback(self, code):
        global access_token, user_id
        access_token = get_access_token_from_code(code)
        if access_token:
            user_id = get_user_info(access_token)
            self.update_status("✅ Authentication successful!")
        else:
            self.update_status("❌ Authentication failed.")

    def start_meeting_logic(self):
        global meeting_link, meeting_id
        self.update_status("Creating meeting...")
        if not access_token or not user_id:
            self.update_status("❌ Please log in first.")
            return
        meeting_link, meeting_id = create_permanent_meeting(user_id, access_token)
        save_meeting(meeting_id, user_id)
        if meeting_link:
            self.link_btn.setText("Click to Join Meeting")
            self.link_btn.show()
            self.update_status("✅ Meeting created!")
        else:
            self.update_status("❌ Failed to create meeting.")

    def open_meeting_link(self, event):
        if meeting_link:
            webbrowser.open(meeting_link)

    def show_user_data(self, title, query):
        query_ids = "SELECT meetingID FROM meetings WHERE host_username = %s"
        meeting_ids = fetch_user_data(query_ids)
        if not meeting_ids:
            QMessageBox.information(self, title, "No meetings found.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()

        for (mid,) in meeting_ids:
            btn = QPushButton(f"View {title} for Meeting {mid}")
            btn.clicked.connect(lambda _, m=mid, q=query, t=title: self.show_content_for_meeting(t, q, m))
            layout.addWidget(btn)

        dialog.setLayout(layout)
        dialog.resize(400, 300)
        dialog.exec_()

    def show_content_for_meeting(self, title, query_template, meeting_id):
        db = get_db()
        cur = db.cursor()
        specific_query = query_template.replace("WHERE meetingID IN (SELECT meetingID FROM meetings WHERE host_username = %s)", "WHERE meetingID = %s")
        cur.execute(specific_query, (meeting_id,))
        result = cur.fetchone()
        cur.close()
        db.close()

        if result:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"{title} for Meeting {meeting_id}")
            layout = QVBoxLayout()
            text_area = QTextEdit()
            text_area.setReadOnly(True)
            text_area.setText(result[0])
            layout.addWidget(text_area)

            delete_btn = QPushButton(f"Delete {title} for Meeting {meeting_id}")
            delete_btn.clicked.connect(lambda: self.delete_record(title, meeting_id, dialog))
            layout.addWidget(delete_btn)

            dialog.setLayout(layout)
            dialog.resize(500, 400)
            dialog.exec_()
        else:
            QMessageBox.information(self, title, "This content has been deleted")

    def show_recordings(self):
        query = "SELECT meetingID, upload_date FROM recordings WHERE meetingID IN (SELECT meetingID FROM meetings WHERE host_username = %s)"
        data = fetch_user_data(query)
        if not data:
            QMessageBox.information(self, "Recordings", "No recordings found.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Recordings")
        layout = QVBoxLayout()
        for meeting_id, _ in data:
            btn = QPushButton(f"Play Recording {meeting_id}")
            btn.clicked.connect(lambda _, mid=meeting_id: self.play_recording_from_db(mid))
            layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec_()

    def play_recording_from_db(self, meeting_id):
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT data FROM recordings WHERE meetingID = %s", (meeting_id,))
        result = cur.fetchone()
        cur.close()
        db.close()
        if result:
            file_path = f"temp_recording_{meeting_id}.mp4"
            with open(file_path, "wb") as f:
                f.write(result[0])
            os.startfile(file_path)
        else:
            QMessageBox.warning(self, "Error", "Recording not found.")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

# === Run Flask & App ===
threading.Thread(target=run_flask, daemon=True).start()
app = QApplication(sys.argv)
window = NotaBotApp()
window.show()
sys.exit(app.exec_())
