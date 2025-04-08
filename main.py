import os
import requests
import assemblyai as aai
import cohere
from tkinter import Tk, Label, Button, ttk
from PIL import Image, ImageTk
import webbrowser
import threading
from urllib.parse import urlencode
from base64 import b64encode
from flask import Flask, request


HARDCODED_PATH = r"C:\Users\hadig\OneDrive\Documents\Zoom"

# ==== ZOOM API CLIENT SETUP ====
CLIENT_ID = "8_5UvIPJQCWGkg7au8TJCg"
CLIENT_SECRET = "QH9ZEnKH6tJYuha56sy04fk2uev2I3eT"
REDIRECT_URI = "http://localhost:8000/callback"

# Global variable to store the user's access token
access_token = None

# Flask app to handle OAuth callback
app = Flask(__name__)

@app.route("/callback")
def callback():
    """ Handle the callback from Zoom after user login """
    code = request.args.get("code")
    if code:
        handle_oauth_callback(code)
        return "Authentication successful! You can now close this window."
    return "Authentication failed. Please try again."

# ==== ZOOM API FUNCTIONS ====
def get_zoom_auth_url():
    """ Generate the Zoom OAuth authorization URL """
    auth_url = "https://zoom.us/oauth/authorize"
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI
    }
    return f"{auth_url}?{urlencode(params)}"

def get_access_token_from_code(code):
    """ Get access token from the authorization code (OAuth flow) """
    url = "https://zoom.us/oauth/token"
    headers = {
        "Authorization": "Basic " + b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI  # The redirect URI you set when creating the Zoom app
    }
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Failed to get access token: {response.text}")
        return None

def get_user_info(access_token):
    """ Get the logged-in user's information using the Zoom API """
    url = "https://api.zoom.us/v2/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        user_info = response.json()
        return user_info["id"]  # Return the user ID (not personal meeting URL)
    else:
        print(f"Error fetching user info: {response.text}")
        return None

def create_permanent_meeting(user_id, access_token):
    """ Create a permanent Zoom meeting with auto-recording enabled """
    url = f"https://api.zoom.us/v2/users/{user_id}/meetings"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    meeting_data = {
        "topic": "Always-On Meeting Room",
        "type": 3,  # Type 3 for an instant meeting with no start time
        "agenda": "Use this anytime without a scheduled start time",
        "settings": {
            "host_video": True,
            "participant_video": True,
            "approval_type": 2,
            "auto_recording": "local",  # Enable local recording automatically
            "mute_upon_entry": True,
        }
    }

    response = requests.post(url, headers=headers, json=meeting_data)
    if response.status_code == 201:
        return response.json().get("join_url")
    else:
        print(f"Failed to create meeting: {response.text}")
        return None

# ==== UI FUNCTIONS ====
def start_meeting_logic():
    """ Start meeting logic when the user clicks the button """
    global meeting_link
    update_status("Fetching personal meeting URL...")

    if not access_token:
        update_status("❌ Authentication required. Please log in to Zoom.")
        return

    # Retrieve user info dynamically using the access token
    user_id = get_user_info(access_token)
    if not user_id:
        update_status("❌ Failed to retrieve user information.")
        return

    # Create the Zoom meeting using the provided settings (with auto-recording)
    meeting_link = create_permanent_meeting(user_id, access_token)

    if meeting_link:
        link_btn.config(text="Click to Join Meeting", command=open_meeting_link)
        link_btn.pack(pady=10)
        update_status("Personal meeting URL fetched!")
    else:
        update_status("❌ Failed to create meeting.")

def update_status(text):
    """ Update the status label """
    status_label.config(text=text)

def open_meeting_link():
    """ Open the Zoom personal meeting link """
    webbrowser.open(meeting_link)

def open_zoom_login():
    """ Open the Zoom OAuth login page for user to authenticate """
    url = get_zoom_auth_url()
    webbrowser.open(url)

def handle_oauth_callback(code):
    """ Handle the callback from Zoom after user login """
    global access_token
    access_token = get_access_token_from_code(code)
    if access_token:
        update_status("Authentication successful!")
        print(f"Access Token: {access_token}")  # Log the access token for debugging
    else:
        update_status("❌ Authentication failed.")

def get_all_folders(path):
    return [foldername for foldername, _, _ in os.walk(path)]

def get_audio_files_by_name(path):
    audio_files = []
    for foldername, _, filenames in os.walk(path):
        for filename in filenames:
            if 'audio' in filename.lower():
                audio_files.append(os.path.join(foldername, filename))
    return audio_files

def transcribe_and_summarize(progress_callback=None):
    if progress_callback:
        progress_callback("Transcribing...")

    folders = get_all_folders(HARDCODED_PATH)
    newest_folder = folders[-1]  # Get the most recent folder
    audio_files = get_audio_files_by_name(newest_folder)
    if not audio_files:
        if progress_callback:
            progress_callback("❌ No audio files found.")
        return
    recording = audio_files[0]  # Assume the first audio file is the recording

    # Transcribe with AssemblyAI
    aai.settings.api_key = "9b6873a6c96d4447a3ab239f7e1f8ff6"
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(recording)

    if progress_callback:
        progress_callback("Summarizing...")

    # Summarize with Cohere
    co = cohere.Client("sPWAMBrdIlQa47hpIiefcuuqW1bd9KO8JmCG9qER")
    prompt = (
        "The following is a transcript of a meeting. Please summarize it into concise meeting minutes, "
        "including key points, decisions made, and action items:\n\n"
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

    if progress_callback:
        progress_callback("Done! Meeting minutes saved.")
        os.startfile("meeting_minutes.txt")

# ==== FLASK SERVER ====
def run_flask():
    """ Start the Flask server for OAuth callback """
    app.run(host="localhost", port=8000)
def start_transcribe_and_summarize():
    """ Trigger the transcribe and summarize process when button is clicked """
    threading.Thread(target=lambda: transcribe_and_summarize(update_status)).start()

# Start Flask server in a separate thread
threading.Thread(target=run_flask).start()


# ==== MAIN WINDOW ====
root = Tk()
root.title("NotaBot")
root.geometry("500x650")
root.configure(bg="#f0f4f8")

# Logo / image
image = Image.open("WhatsApp Image 2025-03-17 at 2.56.27 PM.jpeg")  # Update the path if needed
image = image.resize((300, 200))
photo = ImageTk.PhotoImage(image)
img_label = Label(root, image=photo, bg="#f0f4f8")
img_label.pack(pady=20)

# Title
title_label = Label(root, text="NotaBot", font=("Helvetica", 24, "bold"), bg="#f0f4f8", fg="#333")
title_label.pack()

# Status Label
status_label = Label(root, text="", font=("Helvetica", 12), bg="#f0f4f8", fg="#555")
status_label.pack(pady=10)

# Buttons
login_btn = ttk.Button(root, text="Log in to Zoom", style="Rounded.TButton", command=open_zoom_login)
login_btn.pack(pady=10)

start_btn = ttk.Button(root, text="Get Personal Meeting URL", style="Rounded.TButton", command=start_meeting_logic)
start_btn.pack(pady=10)

transcribe_btn = ttk.Button(root, text="Transcribe and Summarize Meeting", style="Rounded.TButton", command=start_transcribe_and_summarize)
transcribe_btn.pack(pady=10)

link_btn = Button(root, text="", font=("Helvetica", 12), fg="blue", bg="#f0f4f8", bd=0, cursor="hand2")

# Pack only after link is created

# Run the main window
root.mainloop()
