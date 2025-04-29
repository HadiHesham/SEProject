import os
from datetime import datetime
import mysql.connector
import requests
import assemblyai as aai
import cohere
from tkinter import Tk, Label, Button, Text, ttk, messagebox, Toplevel, END
from PIL import Image, ImageTk
import webbrowser
import threading
from urllib.parse import urlencode
from base64 import b64encode
from flask import Flask, request
import pygame


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
    try:
        with open(path, "rb") as file:
            blob = file.read()
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO recordings (meetingID, data, upload_date) VALUES (%s, %s, %s)",
                    (meeting_id, blob, datetime.now()))
        db.commit()
        cur.close()
        db.close()
        messagebox.showinfo("Success", "Recording saved.")
    except Exception as e:
        messagebox.showerror("Error", str(e))


# === ZOOM SETTINGS ===
CLIENT_ID = "8_5UvIPJQCWGkg7au8TJCg"
CLIENT_SECRET = "QH9ZEnKH6tJYuha56sy04fk2uev2I3eT"
REDIRECT_URI = "http://localhost:8000/callback"
access_token = None
meeting_id = None
user_id = None

# === FLASK FOR ZOOM OAUTH ===
app = Flask(__name__)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if code:
        handle_oauth_callback(code)
        return "Authentication successful! You can now close this window."
    return "Authentication failed. Please try again."


def run_flask():
    app.run(host="localhost", port=8000)


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
    else:
        print(f"Failed to get access token: {response.text}")
        return None


def get_user_info(token):
    url = "https://api.zoom.us/v2/users/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["id"]
    else:
        print(f"Error fetching user info: {response.text}")
        return None


def create_permanent_meeting(uid, token):
    global meeting_id
    url = f"https://api.zoom.us/v2/users/{uid}/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    meeting_data = {
        "topic": "Always-On Meeting Room",
        "type": 3,
        "agenda": "Use this anytime without a scheduled start time",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "approval_type": 2,
            "auto_recording": "local",
            "mute_upon_entry": True,
        }
    }
    response = requests.post(url, headers=headers, json=meeting_data)
    if response.status_code == 201:
        data = response.json()
        meeting_id = data.get("id")
        return data.get("join_url"), data.get("id")
    else:
        print(f"Failed to create meeting: {response.text}")
        return None


# === FILE OPERATIONS ===
def get_audio_files_by_name(path):
    audio_files = []
    for foldername, _, filenames in os.walk(path):
        for filename in filenames:
            if 'audio' in filename.lower() or filename.endswith('.mp4'):
                audio_files.append(os.path.join(foldername, filename))
    return audio_files


# === NLP TRANSCRIBE & SUMMARIZE ===
def transcribe_and_summarize(progress_callback=None):
    if progress_callback:
        progress_callback("Transcribing...")
    folders = get_all_folders(HARDCODED_PATH)
    newest_folder = folders[-1]
    audio_files = get_audio_files_by_name(newest_folder)
    if not audio_files:
        if progress_callback:
            progress_callback("❌ No audio files found.")
        return
    recording = audio_files[0]
    aai.settings.api_key = "9b6873a6c96d4447a3ab239f7e1f8ff6"
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(recording)

    if progress_callback:
        progress_callback("Summarizing...")
    co = cohere.Client("sPWAMBrdIlQa47hpIiefcuuqW1bd9KO8JmCG9qER")
    prompt = (
        "The following is a transcript of a meeting. Please summarize it into concise meeting minutes:\n\n"
        f"{transcript.text}"
    )
    response = co.chat(
        model="command-r-plus-08-2024",
        message=prompt,
        temperature=0.5,
        max_tokens=500,
    )
    meeting_minutes = response.text
    with open("meeting_minutes.txt", "w") as f:
        f.write(meeting_minutes)
    save_transcription(meeting_id, transcript.text)
    save_summary(meeting_id, meeting_minutes)
    if progress_callback:
        progress_callback("✅ Done! Meeting minutes saved.")
        os.startfile("meeting_minutes.txt")


# === UI ===
def update_status(text):
    status_label.config(text=text)


def open_meeting_link():
    webbrowser.open(meeting_link)


def open_zoom_login():
    url = get_zoom_auth_url()
    webbrowser.open(url)


def handle_oauth_callback(code):
    global access_token, user_id
    access_token = get_access_token_from_code(code)
    if access_token:
        user_id = get_user_info(access_token)
        update_status("✅ Authentication successful!")
        show_user_data_buttons()
    else:
        update_status("❌ Authentication failed.")


def start_meeting_logic():
    global meeting_link
    update_status("Starting meeting...")
    if not access_token or not user_id:
        update_status("❌ Please log in first.")
        return
    meeting_link, mid = create_permanent_meeting(user_id, access_token)
    save_meeting(mid, user_id)
    if meeting_link:
        link_btn.config(text="Click to Join Meeting", command=open_meeting_link)
        link_btn.pack(pady=10)
        update_status("✅ Meeting created!")
    else:
        update_status("❌ Failed to create meeting.")


def start_transcribe_and_summarize():
    threading.Thread(target=lambda: transcribe_and_summarize(update_status)).start()


def play_recording(file_path):
    os.startfile(file_path)


def show_data(title, query):
    db = get_db()
    cur = db.cursor()
    cur.execute(query, (user_id,))
    rows = cur.fetchall()
    cur.close()
    db.close()
    win = Toplevel(root)
    win.title(title)
    text = Text(win, wrap="word")
    text.pack(expand=True, fill="both", padx=10, pady=10)
    for row in rows:
        text.insert(END, f"{row[0]}\n\n")


def show_recordings():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT meetingID, upload_date FROM recordings
        WHERE meetingID IN (SELECT meetingID FROM meetings WHERE host_username = %s)
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    db.close()

    if not rows:
        messagebox.showinfo("No recordings", "You don't have any recordings for this meeting.")
        return

    win = Toplevel(root)
    win.title("Available Recordings")

    for row in rows:
        recording_id, _ = row
        btn = Button(win, text=f"Play Recording {recording_id}",
                     command=lambda rec_id=recording_id: play_recording_from_db(rec_id))
        btn.pack(pady=5)


def play_recording_from_db(recording_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT data FROM recordings WHERE meetingID = %s", (recording_id,))
    recording_data = cur.fetchone()
    cur.close()
    db.close()

    if recording_data:
        with open(f"temp_recording_{recording_id}.mp4", "wb") as temp_file:
            temp_file.write(recording_data[0])

        play_recording(f"temp_recording_{recording_id}.mp4")
    else:
        messagebox.showerror("Error", "Recording not found.")


def show_user_data_buttons():
    Button(root, text="Show My Recordings", command=show_recordings).pack(pady=5)
    Button(root, text="Show My Transcriptions", command=lambda: show_data("Transcriptions",
                                                                          "SELECT content FROM transcriptions WHERE meetingID IN (SELECT meetingID FROM meetings WHERE host_username = %s)")).pack(
        pady=5)

    Button(root, text="Show My Summaries", command=lambda: show_data("Summaries",
                                                                     "SELECT content FROM summaries WHERE meetingID IN (SELECT meetingID FROM meetings WHERE host_username = %s)")).pack(
        pady=5)


# === MAIN TKINTER UI ===
root = Tk()
root.title("NotaBot")
root.geometry("500x700")
root.configure(bg="#f0f4f8")

image = Image.open("WhatsApp Image 2025-03-17 at 2.56.27 PM.jpeg")
image = image.resize((300, 200))
photo = ImageTk.PhotoImage(image)
Label(root, image=photo, bg="#f0f4f8").pack(pady=20)

Label(root, text="NotaBot", font=("Helvetica", 24, "bold"), bg="#f0f4f8", fg="#333").pack()
status_label = Label(root, text="", font=("Helvetica", 12), bg="#f0f4f8", fg="#555")
status_label.pack(pady=10)

ttk.Button(root, text="Log in to Zoom", command=open_zoom_login).pack(pady=10)
ttk.Button(root, text="Get Personal Meeting URL", command=start_meeting_logic).pack(pady=10)
ttk.Button(root, text="Transcribe and Summarize Meeting", command=start_transcribe_and_summarize).pack(pady=10)

link_btn = Button(root, text="", font=("Helvetica", 12), fg="blue", bg="#f0f4f8", bd=0, cursor="hand2")

threading.Thread(target=run_flask).start()
root.mainloop()
