import pyautogui
import os
import time
import pyperclip


def join(id):
    os.startfile(r"C:\Users\hadig\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Zoom\Zoom Workplace.lnk")
    time.sleep(1)
    join1 = pyautogui.locateOnScreen('img.png')
    if join1 != None:
        pyautogui.click(join1)
    time.sleep(1)
    field = pyautogui.locateOnScreen('img_1.png')
    if field != None:
        pyautogui.click(field)
        time.sleep(1)
        pyautogui.typewrite(id)
    time.sleep(1)
    join2 = pyautogui.locateOnScreen('img_2.png')
    if field != None:
        pyautogui.click(join2)
    time.sleep(5)
    record = pyautogui.locateOnScreen('img_4.png')
    if record != None:
        time.sleep(1)
        pyautogui.click(record)

def create():
    os.startfile(r"C:\Users\hadig\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Zoom\Zoom Workplace.lnk")
    time.sleep(1)
    join1 = pyautogui.locateOnScreen('img_5.png')
    if join1 != None:
        pyautogui.click(join1)
    time.sleep(5)
    pyautogui.hotkey('r')
    ans = input("Do you want to end the meeting? (Y/N)")
    if ans.upper() == 'Y':
        os.startfile(r"C:\Users\hadig\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Zoom\Zoom Workplace.lnk")
        time.sleep(1)
        returnmeeting = pyautogui.locateOnScreen('img_3.png')
        time.sleep(1)
        pyautogui.click(returnmeeting)
        time.sleep(1)
        pyautogui.hotkey('w')
        time.sleep(1)
        pyautogui.click(pyautogui.locateOnScreen('img_7.png'))
        time.sleep(10)
        pyautogui.hotkey('ctrl', 'shift', 'c')
        time.sleep(1)
        os.startfile(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\JetBrains\PyCharm 2024.2.3.lnk")
        time.sleep(1)
        print("Copied text from clipboard:", pyperclip.paste())
create()