import psutil
import pyautogui
import os
import pyperclip
import assemblyai as aai
import cohere
import time


def is_explorer_running():
    for process in psutil.process_iter(['name']):
        if process.info['name'] == 'explorer.exe':  # File Explorer process name
            return True
    return False
def close_explorer():
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == 'explorer.exe':  # File Explorer process name
            try:
                os.system("taskkill /F /IM explorer.exe")  # Forcefully close Explorer
                print("File Explorer closed successfully.")
                return
            except Exception as e:
                print(f"Error closing File Explorer: {e}")
if is_explorer_running():
    print("File Explorer is open.")
else:
    print("File Explorer is closed.")

def create():
    os.startfile(r"C:\Users\hadig\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Zoom\Zoom Workplace.lnk")
    found = False
    while found == False:
        try:
            join1 = pyautogui.locateOnScreen('img_5.png')
            found = True
        except:
            print("wait")
    if join1 != None:
        pyautogui.click(join1)
    time.sleep(5)
    pyautogui.hotkey('r')
    ans = input("Do you want to end the meeting? (Y/N)")
    if ans.upper() == 'Y':
        os.startfile(r"C:\Users\hadig\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Zoom\Zoom Workplace.lnk")
        found = False
        while found == False:
            try:
                returnmeeting = pyautogui.locateOnScreen('img_3.png')
                found = True
            except:
                print("wait")
        pyautogui.click(returnmeeting)
        time.sleep(1)
        pyautogui.hotkey('w')
        time.sleep(1)
        pyautogui.click(pyautogui.locateOnScreen('img_7.png'))
        close_explorer()
        while is_explorer_running() == False:
            print("wait")
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'shift', 'c')
        time.sleep(1)
create()
aai.settings.api_key = "9b6873a6c96d4447a3ab239f7e1f8ff6"
transcriber = aai.Transcriber()
print("transcribing")
transcript = transcriber.transcribe(pyperclip.paste().strip('"'))
print("summarising")
co = cohere.Client("sPWAMBrdIlQa47hpIiefcuuqW1bd9KO8JmCG9qER")
prompt = (
            "The following is a transcript of a meeting. Please summarize it into concise meeting minutes, "
            "including key points, decisions made, and action items:\n\n"
            f"{transcript.text}"
)
response = co.chat(
    model="command-r-plus-08-2024",  # Use the appropriate Cohere model
    message=prompt,
    temperature=0.5,  # Adjust for creativity vs. precision
    max_tokens=500,  # Adjust based on the desired length of the summary
)
meeting_minutes = response.text
file_path = "meeting_minutes.txt"
with open(file_path, "w") as file:
    file.write(meeting_minutes)
