import subprocess
import pyautogui
import time
import win32gui
import pygetwindow as gw

import sys, os
sys.path.append(os.path.abspath(".."))
from axie_cards import exe_path

subprocess.Popen(exe_path)
time.sleep(2)
win = gw.getWindowsWithTitle("AxieInfinity-Origins")[0]

hwnd = win._hWnd  # pygetwindow Window 对象里能拿到 hwnd
left, top, right, bottom = win32gui.GetClientRect(hwnd)
# 注意：ClientRect 是相对窗口客户区的，需要转屏幕坐标
pt = win32gui.ClientToScreen(hwnd, (left, top))
pt2 = win32gui.ClientToScreen(hwnd, (right, bottom))
client_region = (pt[0], pt[1], pt2[0]-pt[0], pt2[1]-pt[1])

print("region:", client_region)
img = pyautogui.screenshot(region=client_region)
img.save("test_images/window.png")
