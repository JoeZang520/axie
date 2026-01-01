import cv2
import pyautogui
import numpy as np
import os
import time
import threading
from pynput import keyboard


def pause(seconds, pause_key=keyboard.Key.f1):
    """
    等待指定秒数，期间可以通过F1键暂停/继续程序
    
    Args:
        seconds: 等待的秒数
        pause_key: 暂停/继续的按键，默认为F1键
    """
    paused = False
    pause_event = threading.Event()
    
    def on_press(key):
        nonlocal paused
        if key == pause_key:
            if paused:
                print("\r[INFO] 程序继续运行...", end="", flush=True)
                paused = False
                pause_event.set()
            else:
                print("\r[INFO] 程序已暂停，按F1键继续...", end="", flush=True)
                paused = True
                pause_event.clear()
    
    def on_release(key):
        pass
    
    # 创建键盘监听器
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    print(f"[INFO] 等待{seconds}秒，按F1键可暂停/继续程序...")
    
    start_time = time.time()
    elapsed_time = 0
    
    try:
        while elapsed_time < seconds:
            if not paused:
                remaining = seconds - elapsed_time
                if remaining > 0:
                    print(f"\r[倒计时] 剩余 {remaining:.1f} 秒 (按F1暂停)", end="", flush=True)
                time.sleep(0.1)  # 每0.1秒检查一次
                elapsed_time = time.time() - start_time
            else:
                # 等待暂停事件被清除
                pause_event.wait()
                # 重新计算开始时间，保持总等待时间不变
                start_time = time.time() - elapsed_time
    
    finally:
        listener.stop()
        print("\r[INFO] 等待完成！", end="", flush=True)
        print()  # 换行


def image(png, threshold=0.85, offset=(0, 0), click_times=1, region=None, color=True, gray_diff_threshold=15):
    """
    图像识别和点击函数
    
    Args:
        png: 图片文件名
        threshold: 匹配阈值
        offset: 点击偏移量
        click_times: 点击次数
        region: 搜索区域
        color: 是否彩色匹配
        gray_diff_threshold: 灰度差异阈值
    
    Returns:
        匹配到的坐标或None
    """
    if not png.endswith('.png'):
        png += '.png'
    image_path = os.path.join('pic', png)
    if not os.path.exists(image_path):
        print(f"[ERROR] 图片不存在: {image_path}")
        return None

    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if template is None:
        print(f"[ERROR] 图片加载失败: {image_path}")
        return None

    region = region or (0, 0, *pyautogui.size())
    x1, y1, x2, y2 = region
    screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
    screen_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    if color:
        # 彩色匹配
        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
    else:
        # 灰度匹配
        screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)

    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    match_area = screen_img[
        max_loc[1]:max_loc[1] + template.shape[0],
        max_loc[0]:max_loc[0] + template.shape[1]
    ]

    if color:
        diff_rg = np.abs(match_area[:, :, 2] - match_area[:, :, 1])
        diff_rb = np.abs(match_area[:, :, 2] - match_area[:, :, 0])
        diff_gb = np.abs(match_area[:, :, 1] - match_area[:, :, 0])
        mean_diff = np.mean((diff_rg + diff_rb + diff_gb) / 3.0)

        if mean_diff < gray_diff_threshold:
            print(f"[FAIL] {png} 匹配区域颜色太灰（均差≈{mean_diff:.2f}, 未识别出图片")
            return None

    center_x = max_loc[0] + template.shape[1] // 2 + x1 + offset[0]
    center_y = max_loc[1] + template.shape[0] // 2 + y1 + offset[1]

    if click_times > 0:
        for _ in range(click_times):
            pyautogui.click(center_x, center_y)
            time.sleep(1)
    print(f"[ACTION]找到 {png} {center_x, center_y} {max_val}")

    return (center_x, center_y)


def loading(image_names, check_interval: float = 1, threshold=0.85, click_times=1, timeout=45):
    """
    循环检测任意一张指定图片出现，返回True或False
    
    Args:
        image_names: 要检测的图片名称列表
        check_interval: 检查间隔
        threshold: 匹配阈值
        click_times: 点击次数
        timeout: 超时时间
    
    Returns:
        找到的图片名称或None
    """
    start_time = time.time()
    print(f"正在加载 {image_names} ... ")

    while True:
        for image_name in image_names:
            pos = image(image_name, threshold=threshold, click_times=click_times, color=True)
            if pos is not None:
                print(f"找到 {image_names}")        
                return image_name

        if timeout and (time.time() - start_time) > timeout:
            print(f"加载 {image_names} 超时")
            return None

        time.sleep(check_interval)


def press(button):
    """
    按键函数
    
    Args:
        button: 要按的键
    """
    print(f'按键{button}')
    pyautogui.keyDown(button)
    pyautogui.keyUp(button)
    time.sleep(1)
    if button == 'esc':
        image('x_quit')


def drag(start_pos, end_pos, duration=1):
    """
    拖拽函数
    
    Args:
        start_pos: 起始位置
        end_pos: 结束位置
        duration: 持续时间
    """
    start_x, start_y = start_pos
    end_x, end_y = end_pos
    
    # 移动到起始位置
    pyautogui.moveTo(start_x, start_y)
    pyautogui.mouseDown(button='left')
    pyautogui.moveTo(end_x, end_y, duration=duration)
    pyautogui.mouseUp(button='left')
    time.sleep(1) 