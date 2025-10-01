import cv2
import pyautogui
import numpy as np
import os
import time
import sys
import subprocess
from datetime import datetime
from pynput import keyboard
import threading
from collections import Counter

# 可选OCR支持
try:
    import pytesseract  # 需要本地安装 Tesseract OCR 可执行文件并配置环境变量
    from PIL import Image
    _TESS_AVAILABLE = True
    # 显式指定 Tesseract 可执行文件与语言数据目录
    pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'
    os.environ['TESSDATA_PREFIX'] = r'D:\Tesseract-OCR\tessdata'
except Exception:
    _TESS_AVAILABLE = False

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


def image(png, threshold=0.9, offset=(0, 0), click_times=1, region=None, color=True, gray_diff_threshold=15):
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
        # print(f"[MISS] 没有找到 {png}")
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


thresholds = {
    "tree1": 0.85,
    "tree2": 0.8,
    "tree3": 0.85,
    "tree4": 0.8,
    "tree5": 0.95,
    "tree6": 0.95,  
    "tree7": 0.9,
    "tree8": 0.9,
    "tree9": 0.9,
    "stone1": 0.95,
    "stone2": 0.9,
    "stone4": 0.9,
    "precious": 0.8,
    "metal": 0.8
}


def image_multi(png_list, thresholds=thresholds, region=None, min_x_distance=40, min_y_distance=40, click_times=0,
                excluded_points=None):
    if isinstance(png_list, str):
        png_list = [png_list]

    if not thresholds:
        raise ValueError("阈值字典 (thresholds) 必须提供")

    region = region or (0, 0, *pyautogui.size())
    x1, y1, x2, y2 = region

    screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - x1))
    screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
    results = {}

    first_valid_point = None
    first_valid_template = None
    first_valid_threshold = None

    def is_far_enough(cx, cy, points, min_dx, min_dy):
        for px, py, _ in points:
            if abs(cx - px) < min_dx and abs(cy - py) < min_dy:
                return False
        for ex, ey in excluded_points:
            if abs(cx - ex) < min_dx and abs(cy - ey) < min_dy:
                return False
        return True

    for picture in png_list:
        templates = []
        for file in os.listdir('pic'):
            if file.startswith(f"{picture}_") and file.endswith('.png'):
                templates.append(os.path.join('pic', file))

        if not templates:
            print(f"[ERROR] 未找到任何多模板图片：{picture}_*.png")
            results[picture] = []
            continue

        threshold = thresholds.get(picture)
        if threshold is None:
            print(f"[WARN] 图片 {picture} 没有设置阈值，跳过该角色")
            continue

        all_points = []
        for template_path in templates:
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                print(f"[ERROR] 图片加载失败: {template_path}")
                continue

            result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(result >= threshold)

            w, h = template.shape[1], template.shape[0]

            for pt, score in zip(zip(*loc[::-1]), result[loc]):
                cx = pt[0] + w // 2 + x1
                cy = pt[1] + h // 2 + y1

                if is_far_enough(cx, cy, all_points, min_x_distance, min_y_distance):
                    all_points.append((cx, cy, score))
                    # print(f"[DEBUG] 找到匹配点: ({cx}, {cy}), 匹配度: {score:.3f}, 图片: {template_path}")

                    if first_valid_point is None:
                        first_valid_point = (cx, cy)
                        first_valid_template = template_path
                        first_valid_threshold = score

        results[picture] = all_points

    # 点击全局第一个通过筛选的点
    if click_times > 0 and first_valid_point:
        cx, cy = first_valid_point
        print(f"[INFO] 点击匹配点：({first_valid_template} {cx}, {cy})，匹配度：{first_valid_threshold:.3f}")
        pyautogui.click(cx, cy)
        time.sleep(1)

    return results


def loading(image_names, check_interval: float = 1, threshold=0.85, click_times=1, timeout=45):
    """循环检测任意一张指定图片出现，返回True或False"""
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

def drag(start_pos, end_pos, duration=1):
    start_x, start_y = start_pos
    end_x, end_y = end_pos
    
    # 移动到起始位置
    pyautogui.moveTo(start_x, start_y)
    pyautogui.mouseDown(button='left')
    pyautogui.moveTo(end_x, end_y, duration=duration)
    pyautogui.mouseUp(button='left')
    time.sleep(1)


def press(button):
    print(f'按键{button}')
    pyautogui.keyDown(button)
    pyautogui.keyUp(button)
    time.sleep(1)
    if button == 'esc':
        image('x_quit')


def in_game():
    return image('homeland', offset=(100, 0), gray_diff_threshold=12, click_times=0) is not None

def enter_game():
    image('homeland', offset=(100, 0), threshold=0.95, gray_diff_threshold=12)
    if image('join'):
        time.sleep(3)
        image('join')
        loading(["acoin"])
        if not image('atia', click_times=0):
            for _ in range(6):
                pyautogui.scroll(30)
                time.sleep(1)
            pyautogui.press("A"), time.sleep(2)       
    if image('1axie_mode', click_times=0):
        image('tab')
        loading(["acoin"])
    if not in_game():
        print("当前不在游戏中。")
        subprocess.Popen(r"E:\Axie Infinity - Homeland\Homeland.exe")
        time.sleep(10)     
        loading(["join"], click_times=2)
        loading(["acoin"])
        image('x_land')
        image('M')
    if image('exit', threshold=0.95):
        countdown('等待下一次重启', 60)
        enter_game()
        for _ in range(6):
            pyautogui.scroll(30)
            time.sleep(1)
        pyautogui.press("A"), time.sleep(3)
    if image('close'):
        countdown('等待下一次重启', 60)
        enter_game()
        for _ in range(6):
            pyautogui.scroll(30)
            time.sleep(1)
        pyautogui.press("A"), time.sleep(3)
    if image('maintenance') or image('maintenance2'):
        print("维护中，程序退出")
        close_game()
        sys.exit() 

def close_game():
    subprocess.run(["taskkill", "/f", "/im", "Homeland.exe"], shell=True)
    time.sleep(10)


def collect(tree_count, stone_count):
    if image('0_idle', click_times=0, threshold=0.95):
        print("沒有閑置axie")
        return
    # 按下并保持Shift+Q
    pyautogui.keyDown('shift')
    pyautogui.keyDown('q')

    # 采集树
    clicked_points = []
    tree_keys = ['tree9', 'tree9', 'tree7', 'tree6', 'tree5', 'tree4', 'tree3', 'tree2', 'tree1']

    for _ in range(tree_count):
        result = image_multi(
            png_list=tree_keys,
            thresholds=thresholds,
            click_times=1,
            excluded_points=clicked_points
        )

        tree_points = []
        matched_key = None
        for key in tree_keys:
            if result.get(key):
                tree_points = result[key]
                matched_key = key
                break

        if tree_points:
            cx, cy, _ = tree_points[0]
            clicked_points.append((cx, cy))
            # 根据匹配到的图片类型执行不同的点击操作
            if matched_key == 'tree1':
                press('space')
                pyautogui.click(cx, cy + 25)
                time.sleep(1)
                press('space')
            else:
                press('space')
        else:
            print("[MISS] 没有可砍的树了。")
            break
    print("[INFO] 树木采集结束")

    # 采集石头
    clicked_points = []  # 重置已点击的点
    stone_keys = ['stone1', 'stone2', 'stone4']

    for _ in range(stone_count):
        result = image_multi(
            png_list=stone_keys,
            thresholds=thresholds,
            click_times=1,
            excluded_points=clicked_points
        )

        stone_points = []
        for key in stone_keys:
            if result.get(key):
                stone_points = result[key]
                break

        if stone_points:
            cx, cy, _ = stone_points[0]
            clicked_points.append((cx, cy))
            press('space')
        else:
            print("[MISS] 没有可采的石头了。")
            break
    print("[INFO] 石头采集结束")

    # 释放按键
    pyautogui.keyUp('q')
    pyautogui.keyUp('shift')
    time.sleep(3)
    
    pos = image('storage', click_times=0)
    if pos is not None:
        x, y = pos
        pyautogui.moveTo(x, y)
        pause(3)

def mine(plot=None, iron_ore=False, cutting_tree=False):
    enter_game()
    if image('0_idle', click_times=0, threshold=0.97):
        print("沒有闲置axie")
        pause(3)
        return
    image('acoin')
    image('P')
    press('3')
    time.sleep(10)

    # 获取home位置作为基准点
    home_pos = image('home', threshold=0.8, click_times=0)
    if home_pos is None:
        print("[ERROR] 未找到home坐标")
        press('1')
        time.sleep(5.1)
        return

    base_x, base_y = home_pos

    # 按地块组织坐标
    # 57_119地块
    plot57119_trees = [
        (-200, 140), (-350, 210), (-340, 60), (-640, 280), (-500, -30)
    ]
    plot57119_mines = [
        (-28,89),(63,42),(-431,-249),(-350,-210),(-390,-87),(-302,-130),(-148,-182),(-59,-138),(48,-91),(135,-135),
        (210,70),(310,120),(240,-176),(540,-150),(620,75),(227,317),(322,367),(92,282),(497,22),(416,62),
        (-217,377),(-308,326)
    ]
    
    # 105_128地块
    plot105128_trees = []  # 没有树木坐标
    plot105128_mines = [
        (70, 45), (-462, 85), (-16, 85), (45, -195), (25, -70),
        (120, -20), (-115, 188), (-163, 112), (-208, 240), (-250, 69),
        (-654, 124), (-531, -248), (333, -40), (475, -67), (563, -27),
        (381, 214), (-397, 277), (-498, 329),(-325, -28),
        (-400, -68), (-350, -275), (-270, -240), (417, -137),
        (300, 260), (94, 407), (-450, 418), (210, 62), (260, 0)
    ]

    # 123_122地块
    plot123122_trees = [
        (-140,-190),(-30,-120),(170,-20),(410,100),(290, 270),(70,380),
        (0,-260),(-140,-330)
    ]
    plot123122_mines = [
        (75,165),(162,213),(45,298),(-42,345),
        (-442,249),(-528,199),
        (-342,309),(-447,365),
        (-592,-111),(-526,-133),(-225,-244)
    ]
    
    # 119_56地块
    plot11956_trees = [
        (-435,0),(-556,-68),(-652,-133),(-580,120), (-773, 199)
    ]
    plot11956_mines = []  # 没有挖矿坐标

    # 根据plot参数选择要操作的坐标组
    if plot == '57_119':
        mines = plot57119_mines
        trees = plot57119_trees
    elif plot == '105_128':
        mines = plot105128_mines
        trees = plot105128_trees
    elif plot == '123_122':
        mines = plot123122_mines
        trees = plot123122_trees
    elif plot == '119_56':
        mines = plot11956_mines
        trees = plot11956_trees
    else:
        mines = []
        trees = []

    # 遍历选定组的每个点
    for dx, dy in trees:
        # 移动到目标位置
        target_x = base_x + dx
        target_y = base_y + dy
        pyautogui.moveTo(target_x, target_y)
        time.sleep(1)
        # if image('cutting_tree', threshold=0.94, click_times=0) and cutting_tree==False:
        #     print('已经有axie在砍树')
        #     break
        press('space')      
        if loading(['no_avail'], check_interval=0.1, click_times=0, timeout=1):
            break
        press('space')
        time.sleep(3)
        if image('cutting_tree', threshold=0.94, click_times=0) and cutting_tree==False:
            print('axie开始砍一棵树')
            break

    for dx, dy in mines:
        # 移动到目标位置
        target_x = base_x + dx
        target_y = base_y + dy
        pyautogui.moveTo(target_x, target_y)
        time.sleep(1)
        if iron_ore==True:
            press('space')  
            if loading(['no_avail'], check_interval=0.1, click_times=0, timeout=1):
              break     
        if image('gem_ore', offset=(80,80), click_times=1) or image('precious_ore', offset=(80,80), click_times=1):
            print('找到gem_ore或precious_ore')  
            image('close') 
            if loading(['no_avail'], check_interval=0.1, click_times=0, timeout=3):
              break
            time.sleep(3)  
        

    print(f"[INFO] {plot}矿采集结束")
    press('1')
    pause(3)

    
def craft_food(plot=None):
    enter_game()
    image('acoin', offset=(-410, 810))  # 左下角收菜的位置
    image('P')
    if plot=='105_128':
        image('acoin')
        pyautogui.moveRel(-144, 368)
        pyautogui.click(), time.sleep(1), pyautogui.click()
        time.sleep(2)
        if image('#2', click_times=0):
            image('left_arrow'), time.sleep(1)
        image('boiled_carrot')
        image('craft')
        time.sleep(1)  

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('boiled_carrot')
        image('craft')
        time.sleep(1)       

        # image('left_arrow', offset=(835, 0)), time.sleep(1)

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('cotton_paper')
        image('craft')
        time.sleep(1)

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('cotton_paper')
        image('craft')
        time.sleep(1)

        image('x_land')
        image('acoin', offset=(-100, 0))

    
    if plot=='122_138':
        image('acoin')
        pyautogui.moveRel(-136, 327)
        pyautogui.click(), time.sleep(1), pyautogui.click()
        time.sleep(2)
        image('boiled_carrot')
        image('craft')
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('boiled_carrot')
        image('craft')
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('stew')
        if image('x1', threshold=0.95, click_times=1):
            pyautogui.moveRel(-50, 0)
            pyautogui.click(), time.sleep(1)
        

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        # image('large_potion_of_shield', gray_diff_threshold=9)
        # image('craft')
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        # image('large_potion_of_shield', gray_diff_threshold=9)
        # image('craft')

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('cotton_paper')
        image('craft')  
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('cotton_paper')
        image('craft')
        

        image('x_land')
        image('acoin', offset=(-100, 0))

   
    if plot=='57_119':
        image('acoin')
        pyautogui.moveRel(-228, 363)
        pyautogui.click(), time.sleep(1), pyautogui.click()
        time.sleep(2)
        image('stew')
        if image('x1', threshold=0.95, click_times=1):
            pyautogui.moveRel(-50, 0)
        image('beeswax')
        if image('x1', threshold=0.95):
            pyautogui.moveRel(-50, 0)
            pyautogui.click(), time.sleep(1)               

        image('left_arrow', offset=(835, 0)), time.sleep(1)   
        image('stew')
        if image('x1', threshold=0.95, click_times=1):
            pyautogui.moveRel(-50, 0)                 
        image('beeswax')
        if image('x1', threshold=0.95):
            pyautogui.moveRel(-50, 0)
            pyautogui.click(), time.sleep(1)
        

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('stew')
        if image('x1', threshold=0.95):
            pyautogui.moveRel(-50, 0)
            pyautogui.click(), time.sleep(1)

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('large_haste_potion')
        image('craft')
  
        
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        # image('large_haste_potion')
        # image('craft')
        
        

        image('left_arrow', offset=(835, 0)), time.sleep(1)     
        image('cotton_paper')
        image('craft')
        
        image('left_arrow', offset=(835, 0)), time.sleep(1)               
        image('shell_of_large_area_damage')
        image('craft')
           

        image('x_land')
        image('acoin', offset=(-100, 0))
    

    if image('exit', threshold=0.95):
        countdown('等待下一次重启', 60)
        enter_game()
        switch_plot(plot)
        craft_food(plot)
    if image('close'):
        countdown('等待下一次重启', 60)
        enter_game()
        switch_plot(plot)
        craft_food(plot)


    pause(3)


def craft_equip(plot=None):
    enter_game()
    pending_buys = []
    image('acoin', offset=(-410, 810))  # 左下角收菜的位置
    if plot=='105_128':
        image('acoin')
        pyautogui.moveRel(605, 332)
        pyautogui.click(), time.sleep(1), pyautogui.click()
        time.sleep(2)
        # image('silver_staff')
        # image('craft') 

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        # image('silver_staff')
        # image('craft')

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        # image('leather_shoes')
        # image('craft') 

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        # image('leather_shoes')
        # image('craft')
        
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('gold_bracelet')
        image('craft')      
        image('gold_emerald_bracelet', gray_diff_threshold=4)
        image('craft')
        

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('gold_emerald_bracelet', gray_diff_threshold=4)
        image('craft')      
        image('gold_bracelet')
        image('craft')
        
        
        image('x_land')
        image('acoin', offset=(-100, 0))       

    
    if plot=='122_138':
        image('acoin')
        pyautogui.moveRel(470, 566)
        pyautogui.click(), time.sleep(1), pyautogui.click()
        time.sleep(2)
        image('platinum_sphere')
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('platinum_sphere')
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('platinum_helmet')
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                if loading(['not'], check_interval=0.1, click_times=0, timeout=3):
                    print('[WARN] 材料数量不够')
                    pending_buys.append((plot,'platinum i', None, 0))
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('platinum_plate_mail')
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('gold_bracelet')
        image('craft')
        image('gold_diamond_bracelet', gray_diff_threshold=4)
        image('craft')
        
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('gold_diamond_bracelet', gray_diff_threshold=4)
        image('craft')
        image('gold_bracelet')
        image('craft')
              

        image('x_land')
        image('acoin', offset=(-100, 0))
        


    if plot=='57_119':
        image('acoin')
        pyautogui.moveRel(887, 352)
        pyautogui.click(), time.sleep(1), pyautogui.click()
        time.sleep(2)
        image('platinum_long_sword', gray_diff_threshold=9)
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                if loading(['not'], check_interval=0.1, click_times=0, timeout=3):
                    print('[WARN] 材料数量不够')
                    pending_buys.append((plot,'platinum i', None, 0))
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('platinum_long_sword', gray_diff_threshold=9)
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)               
        

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        # image('talaria_shoes')
        # if image('x1', threshold=0.95):
        #     pyautogui.moveRel(-50, 0)
        #     # pyautogui.click(), time.sleep(1) 
        # image('platinum_shield')
        # if image('x1', threshold=0.95):
        #     pyautogui.moveRel(-50, 0)
        #     # pyautogui.click(), time.sleep(1) 
        image('platinum_shoes')
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)                                         
        
        image('left_arrow', offset=(835, 0)), time.sleep(1)   
        # image('talaria_shoes')
        # if image('x1', threshold=0.95):
        #     pyautogui.moveRel(-50, 0)
        #     # pyautogui.click(), time.sleep(1) 
        # image('platinum_shield')
        # if image('x1', threshold=0.95):
        #     pyautogui.moveRel(-50, 0)
        #     # pyautogui.click(), time.sleep(1) 
        image('platinum_chain_mail')
        if not (image('rare_platinum_ingot', threshold=0.98, click_times=0) or image('uncommon_platinum_ingot', threshold=0.98, click_times=0)):
            if image('x1', threshold=0.95):
                pyautogui.moveRel(-50, 0)
                pyautogui.click(), time.sleep(1)              
        
        
        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('gold_bracelet')
        image('craft')      
        image('gold_emerald_bracelet', gray_diff_threshold=4)
        image('craft')
        

        image('left_arrow', offset=(835, 0)), time.sleep(1)
        image('gold_emerald_bracelet', gray_diff_threshold=4)
        image('craft')      
        image('gold_bracelet')
        image('craft')
        

        image('x_land')  
        image('acoin', offset=(-100, 0))
    

    if image('exit', threshold=0.95):
        countdown('等待下一次重启', 60)
        enter_game()
        switch_plot(plot)
        craft_food(plot)
    if image('close'):
        countdown('等待下一次重启', 60)
        enter_game()
        switch_plot(plot)
        craft_food(plot)

    if pending_buys:
        for buy_info in pending_buys:
            # 使用 buy_auction 购买的物品 
            if buy_info[1] == 'platinum i':
                buy_auction(buy_info[0], buy_info[1], buy_info[2], buy_info[3])
  
    pause(3)


def countdown(activity, seconds):
    for i in range(seconds, 0, -1):
        sys.stdout.write(f"\r{activity}倒计时：{i} 秒")
        sys.stdout.flush()
        time.sleep(1)
    print("\r倒计时结束！      ")

def switch_plot(plot):
    enter_game()
    image('plot')
    if plot == '57_119' or plot == '123_122' or plot == '119_56' or plot == '122_138':
        image('acoin', offset=(-420, 280))  # 自己的地
        image(plot)
    time.sleep(4)
    if plot == '105_128':
        image('acoin', offset=(-340, 280))  # 别人的地
        image(plot)
    time.sleep(4)
    for _ in range(6):
        pyautogui.scroll(30)
        time.sleep(1)
    pyautogui.press("A"), time.sleep(2)
    image('acoin') 
    pause(3)

def discard(*ores):
    enter_game()
    """
    丢弃指定的矿石
    :param ores: 要丢弃的矿石名称列表
    """
    press('v')
    time.sleep(3)
    
    # 点击必要的UI元素
    image('inventory', offset=(-50, 110))  # 苹果
    image('inventory', offset=(615, 110))  # Metalwork
    image('miners_mass')
    # image('down_arrow')
    # image('down_arrow', offset=(-180, 180))
    # pyautogui.moveRel(0, -200)
    time.sleep(1)
    
    # 处理每个矿石
    for ore in ores:
        if ore:  # 只处理非None的矿石
            for _ in range(5):
                if image(ore, threshold=0.93):
                    time.sleep(1)
                    image('discard')
                    time.sleep(1)
                    press('enter')
                    time.sleep(6)
                else:
                    print(f"[INFO] 未找到{ore}")
    
    image('x_land')
    time.sleep(1)


def collect_post(Transfers=True, Orders=False):
    enter_game()
    press('g')
    time.sleep(1)

    if Transfers == True:
        image('post', offset=(-200, 130))  # Transfers
        for _ in range(12):
            if image('arrived'):
                time.sleep(2)
                image('claim')
                if loading(['no_avail'], check_interval=0.1, click_times=0, timeout=3):
                    break

    if Orders == True:
        image('post', offset=(-50, 130))  # Orders
        time.sleep(3)
        pos = image('post', click_times=0)
        if pos:
            x, y = pos
            start_x = x - 610
            # 检查当前时间是否在规定时间之间
            current_hour = time.localtime().tm_hour
            is_claim_time = (8 <= current_hour < 11)
            mini_claimed = False

            for offset_y in [230, 430, 630]:
                start_y = y + offset_y
                for i in range(4):
                    pyautogui.click(start_x + i * 280, start_y)
                    time.sleep(2)
                    if not image('claim', click_times=0):
                        break
                    print(f'{start_x + i * 280, start_y}')
                    search_region = ((start_x + i * 280) - 40, start_y, (start_x + i * 280) + 40, start_y + 160)
                    print(f'{search_region}')
                    mini_pos = (image('mini_platinum_dust', threshold=0.95, region=search_region, click_times=0)
                                # or image('mini_platinum_ingot', threshold=0.95, region=search_region, click_times=0)
                                or image('mini_platinum_ore', threshold=0.95, region=search_region, click_times=0)
                                or image('mini_wood', threshold=0.95, region=search_region, click_times=0)
                                or image('mini_stone', threshold=0.92, gray_diff_threshold=8, region=search_region,
                                         click_times=0))

                    if is_claim_time:
                        if mini_pos and not mini_claimed:
                            print(f"规定时间期间找到mini，执行claim（仅一次）")
                            image('claim')
                            mini_claimed = True
                        elif mini_pos and mini_claimed:
                            print(f"规定时间期间找到mini，但已经claim过，跳过")
                        else:
                            print(f"规定时间期间没有找到mini，执行claim")
                            image('claim')
                    else:
                        if not mini_pos:
                            print(f"非规定时间期间，没有找到mini，执行claim")
                            image('claim')
                    if loading(['no_avail'], check_interval=0.1, click_times=0, timeout=2):
                        break

    pause(3)  # 等待取件

    if Transfers == True:
        image('post', offset=(-200, 130))  # Transfers
        time.sleep(3)
        for _ in range(12):
            if image('arrived'):
                time.sleep(2)
                image('claim')
                time.sleep(3)
            if image('unpacking'):
                time.sleep(3)
                if image('enough', offset=(-180, 0)):
                    time.sleep(4)
                    for _ in range(12):
                        if image('unpacking'):
                            time.sleep(3)
                            image('enough', offset=(-180, 0))
                            time.sleep(4)
                    break
                else:
                    pause(10)  # 等待取件
            else:
                break

    if Orders == True:
        image('post', offset=(-50, 130))  # Orders
        for _ in range(12):
            if image('unpacking'):
                time.sleep(3)
                if image('enough', offset=(-180, 0)):
                    time.sleep(4)
                    for _ in range(12):
                        if image('unpacking'):
                            time.sleep(3)
                            image('enough', offset=(-180, 0))
                            time.sleep(4)
                    break
                else:
                    pause(10)  # 等待取件                                      
            else:
                break

    image('x_land')
    time.sleep(3)


def transfer(plot=None, item=False, material=False, name=None, target_plot=None):  
    enter_game()
    press('r')
    time.sleep(0.5)
    if image('available_0', threshold=0.97, gray_diff_threshold=13, click_times=0):
        print('没有空位')
        press('esc')
        time.sleep(0.5)
        return
    if item:
        image('transfer', offset=(-520, 105))  # item
        pos = image('transfer', click_times=0)
        if pos:
            x, y = pos
            start_x = x - 700
            for offset_y in [290, 410, 530, 650]:
                start_y = y + offset_y
                for i in range(5):
                    pyautogui.click(start_x + i * 140, start_y)
                    image('mini_gold_bracelet', offset=(600, 0))  # 表示不传送gold_bracelet
                    # if plot == '122_138':
                    #     image('mini_boiled_carrot', offset=(600, 0))  # 该地也不传送boiled_carrot
                    #     image('mini_cotton_paper', offset=(600, 0))  # 该地也不传送cotton_paper
                        
                    if not image('transfer_x', click_times=0):
                        print('没有物品')
                        press('esc')
                        return           
        image('destination'), time.sleep(6)
        if image(target_plot):
            image('confirm_transfer')
            image('transfer', offset=(640, 790))
            image('remember_destination')
            press('enter'), time.sleep(4) 
        else:
            press('esc') 
        image('x_land')
        # time.sleep(1)
            
    if material:
        # image('down_arrow')
        # image('down_arrow', offset=(-180, 140))
        image('transfer', offset=(-360, 105))  # material
        time.sleep(0.5)
        image('transfer', offset=(-420, 165))  # 輸入框
        time.sleep(0.3)
        pyautogui.typewrite(name, interval=0.12)  
        # pyautogui.click()
        if name in ('ruby'):
            pyautogui.moveRel(0, 145)
            pyautogui.click()
        else:
            pyautogui.click()
            image('transfer', offset=(-316, 166))  # 搜索
        # pyautogui.click()
        time.sleep(2)
        if not image(name, threshold=0.95, click_times=0):
            print(f'没有找到{name}')
            image('transfer_x')
       
            press('esc')
            return               
        
        pos = image('transfer', click_times=0)
        if pos:
            x, y = pos
            start_x = x - 710
            start_y = y + 280
            if name in ('platinum d', 'platinum o', 'gol'):
                image(name)
            else:
                for i in range(5):
                     pyautogui.click(start_x + i * 140, start_y)
                     time.sleep(0.2)
                                                     
        image('destination')
        pause(3)
        if image(target_plot):
            image('confirm_transfer')
            image('transfer', offset=(640, 790))
            image('remember_destination')
            press('enter')
            time.sleep(4)
        else:
            press('esc')  
        image('x_land')
        # time.sleep(1)






def adventure(plot=None, equip=False):   
    enter_game()
    switch_plot(plot=plot)
               
    press('n')
    time.sleep(3)
    if image('start_count') or image('release'):
        time.sleep(3)
        press('enter')
        time.sleep(3)
    else:
        press('n')
        time.sleep(3)
        image('start_count')
        time.sleep(3)
        press('enter')
        time.sleep(3)
    image('land_cancel')
    image('close')
    
    image('3_axies', click_times=0, gray_diff_threshold=5)
    image('1_axie', threshold=0.95)  

    time.sleep(1)

    for _ in range(21):
        if not image('release', click_times=0):
            break

        pos = image('refresh', click_times=0, gray_diff_threshold=5)
      
        if pos:
            x, y = pos
            print(f'{x, y}')
            pyautogui.moveTo(x, y)
            pyautogui.click()
            time.sleep(4)
        else:
            print('沒有找到refresh')
        
        serch_region=(x, y, x + 180, y + 570)
        print(f'{serch_region}')
        if image('+', region=serch_region):  
            if equip == True: 
                 press('space')                                       
            image('+', region=serch_region)
            if equip == True: 
                 press('space') 
            image('+', region=serch_region)
            if equip == True: 
                 press('space') 
            press('enter')
            time.sleep(1)
            press('enter')
            if loading(['fail'], check_interval=0.1, click_times=0, timeout=2):
                break
            if equip == True:
                pause(60)
            if equip == False:
                pause(30)
                       
        else:
            print('未找到 + ')
            break  
    image('x_land')
    time.sleep(3)
  
        
def sell(item, price):
    press('u')
    time.sleep(3)
    image('auction_house', offset=(-680, 330))  # sell
    image('auction_house', offset=(-430, 380))  # +
    if image(item, threshold=0.97):
        image('sell', offset=(0, -345))  # 輸入價格処
        pyautogui.click()
        pyautogui.click()
        pyautogui.typewrite(price)
        image('sell', offset=(94, -217))  # 數量最大処
        image('sell')
        press('enter')
        time.sleep(3)  
        press('esc')
    else:
        print(f'没有找到 {item}')
        press('esc')
        press('esc')   
    time.sleep(3)

def buy_favor(plot=None, target=None, item=None):
    enter_game()
    press('u')
    time.sleep(3)
    image('auction_house', offset=(-680, 260))  # buy
    image('auction_house', offset=(-450, 790))  # browse seller
    image('favor')
    image(target, offset=(80, 100))
    time.sleep(3)
    

    if plot in ['57_119', '119_56', '122_138']:  
        if item:
            for _ in range(1):
                image(item)  
                time.sleep(2)
                image('purchase', offset=(199, -175))  # 数量最大处
                image('purchase')
                press('enter')
                if loading(['not'], check_interval=0.1, click_times=0, timeout=3):
                    break
                time.sleep(7)
                if image('close'):
                    break  
    
    press('esc')
    press('esc') 
    pause(3)


# 从屏幕区域读取数字（仅数字）。region 格式为 (x1, y1, x2, y2)
def read_digits_from_region(region):
    if not _TESS_AVAILABLE:
        print("[WARN] 未安装pytesseract或Tesseract不可用，跳过数字识别")
        return None
    x1, y1, x2, y2 = region
    try:
        screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. 增加图像尺寸
        gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        
        # 2. 增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # 3. 二值化处理，尝试多个阈值
        _, th1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        th2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
        th3 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 10)
        
        # 4. 降噪
        kernel = np.ones((2, 2), np.uint8)
        th1 = cv2.morphologyEx(th1, cv2.MORPH_OPEN, kernel, iterations=1)
        th2 = cv2.morphologyEx(th2, cv2.MORPH_OPEN, kernel, iterations=1)
        th3 = cv2.morphologyEx(th3, cv2.MORPH_OPEN, kernel, iterations=1)

        # 5. 使用更严格的OCR配置
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789 --dpi 300'
        
        # 6. 尝试多个处理后的图像
        results = []
        for img in [th1, th2, th3]:
            try:
                result = pytesseract.image_to_string(img, lang='eng', config=config)
                digits = ''.join(ch for ch in result if ch.isdigit())
                if digits:
                    results.append(digits)
            except Exception as e:
                print(f"[WARN] OCR处理异常: {e}")
                continue
        
        # 7. 选择最可能的结果
        if results:
            # 选择出现次数最多的结果
            most_common = Counter(results).most_common(1)[0][0]
            # print(f"[DEBUG] OCR结果候选: {results}, 选择: {most_common}")
            return most_common
            
        return None
    except Exception as e:
        print(f"[WARN] 数字识别异常: {e}")
        return None

def read_price_from_region(x, y, width=30, height=30):
    """
    从指定区域读取价格
    x, y: 区域左上角坐标
    width, height: 区域宽高
    """
    try:
        roi = (x, y, x + width, y + height)
        price_str = read_digits_from_region(roi)
        if price_str:
            return int(price_str)
        return None
    except Exception as e:
        print(f"[ERROR] 读取价格失败: {e}")
        return None

def find_best_platinum_quality():
    """
    查找最优性价比的platinum quality
    返回: (quality名称, 建议购买数量) 或 (None, None)
    """
    qualities = [
        ('a_common_platinum_i', 800),
        ('a_uncommon_platinum_i', 400),
        ('a_rare_platinum_i', 200),
        ('a_epic_platinum_i', 100),
        ('a_legendary_platinum_i', 50),
        ('a_mythical_platinum_i', 25)
    ]
    
    best_quality = None
    best_price = float('inf')
    best_qty = 0
    prev_price = None
    
    for quality, qty in qualities:
        pos = image(quality, click_times=0, threshold=0.96)
        if pos:
            x, y = pos
            # 价格区域在物品右侧偏下
            price_x = x + 160
            price_y = y + 10
            # 保存价格区域截图到桌面
            # try:
            #     roi = (price_x, price_y, price_x + 30, price_y + 30)
            #     x1, y1, x2, y2 = map(int, roi)
            #     _shot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
            #     desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', f'price_roi_{quality}_{int(time.time())}.png')
            #     _shot.save(desktop_path)
            #     # print(f"[INFO] 已保存{quality}价格区域截图到: {desktop_path}")
            # except Exception as e:
            #     print(f"[WARN] 保存价格区域截图失败: {e}")
            
            price = read_price_from_region(price_x, price_y)
            if price:
                print(f"[INFO] {quality} 价格: {price}")
            else:
                print(f"[WARN] {quality} 价格识别失败")
                
            if prev_price is not None and price:
                # 如果当前价格小于前一个品质价格的2倍，说明更划算
                if price < prev_price * 2:
                    best_quality = quality
                    best_price = price
                    best_qty = qty
            elif best_price == float('inf') and price:  # 第一个有效价格
                best_quality = quality
                best_price = price
                best_qty = qty
            if price:
                prev_price = price
    
    if best_quality:
        print(f"[INFO] 最佳购买选择: {best_quality}, 建议数量: {best_qty}, 价格: {best_price}")
        return best_quality, best_qty
    return None, None


# 添加在文件开头的全局变量区域
last_platinum_purchase_time = 0  # 记录上次购买platinum的时间戳

def buy_auction(plot=None, item=None, quality=None, total_qty=0):
    enter_game()

    global last_platinum_purchase_time  # 声明使用全局变量
    
    # 如果是购买platinum，检查时间间隔
    if item == 'platinum i':
        current_time = time.time()
        time_diff = current_time - last_platinum_purchase_time
        if time_diff < 8 * 3600:  # 8小时 = 8 * 3600秒
            hours_left = (8 * 3600 - time_diff) / 3600
            print(f"[INFO] 距离上次购买platinum还不到8小时（还需等待{hours_left:.1f}小时），跳过本次购买")
            return

    press('u')
    time.sleep(3)
    image('auction_house', offset=(-680, 260))  # buy
    time.sleep(3)
    image('auction_house', offset=(-530, 135))  # All
    image('auction_house', offset=(-90, 135))  # 输入框
    pyautogui.typewrite(item)
    time.sleep(3)
    if item in ['emerald', 'diamond', 'topaz', 'amethyst']:
        image('auction_house', offset=(-90, 280))  # 点击第二行商品
    image('auction_house', offset=(-90, 200))  # 点击商品
    time.sleep(3)

    # 处理platinum ingot的特殊逻辑
    if item == 'platinum i':
        best_quality, suggested_qty = find_best_platinum_quality()
        if best_quality:
            quality = best_quality
            if total_qty == 0:  # 如果没有指定数量，使用建议数量
                total_qty = suggested_qty
            print(f"[INFO] 选择购买 {quality}，计划数量: {total_qty}")
        else:
            print("[WARN] 未找到合适的platinum quality，使用默认设置")

    if quality:
        image(quality, offset=(120, 125))  # 点击需要购买品质的物品
    time.sleep(6)

    if plot in ('57_119', '122_138', '123_122', '113_18', '105_128'):   
        if item:
            try:
                total_qty = int(total_qty)
            except Exception:
                print('[ERROR] total_qty 不是有效整数')
                return
            purchase_sum = 0
            for _ in range(10):
                remaining = max(0, total_qty - purchase_sum)
                image('auction_house', offset=(-40, 300))  # 点击第一个商品
                time.sleep(2)
                pos = image('purchase', click_times=0)
                if pos is not None:
                    px, py = pos
                    roi = (px + 200, py - 195, px + 260, py - 155)
                    # # 保存 ROI 到桌面（临时调试用，后续可注释）
                    # try:
                    #     x1, y1, x2, y2 = map(int, roi)
                    #     _shot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
                    #     desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', f'roi_{int(time.time())}.png')
                    #     _shot.save(desktop_path)
                    #     print(f"[INFO] 已保存区域截图到: {desktop_path}")
                    # except Exception as e:
                    #     print(f"[WARN] 保存区域截图失败: {e}")
                    digits = read_digits_from_region(roi)
                    if digits is not None:
                        print(f"[INFO] 识别到订单数量: {digits}")
                        completed_batch = False
                        if int(digits) < int(remaining):
                            image('purchase', offset=(199, -175))  # 数量最大处                          
                            purchase_sum += int(digits)
                            print(f"[INFO] 本次不足购买计划 {remaining}，实际 {digits}；累计 {purchase_sum}/{total_qty}，剩余 {max(0, total_qty - purchase_sum)}")
                            image('purchase')
                            press('enter')
                        else:
                            # 等于或大于剩余额度
                            purchase_sum += int(remaining)
                            print(f"[INFO] 本次满足购买计划 {remaining}, 实际 {remaining}；累计 {purchase_sum}/{total_qty}，剩余 {max(0, total_qty - purchase_sum)}")
                            image('purchase', offset=(100, -210))  # 输入购买数量处
                            pyautogui.typewrite(str(remaining))
                            time.sleep(2)
                            image('purchase')
                            press('enter')
                            completed_batch = True
                        if purchase_sum >= total_qty:
                            print(f"[INFO] 已累计识别数量达到 {purchase_sum}，达到购买量 {total_qty}，停止循环")
                            break
                        if completed_batch:
                            # 如果这次按计划已经满足剩余额度，则退出循环
                            break
                    else:
                        print("[INFO] 未识别到有效数字")
                
                
                # 若上面的分支未覆盖（未识别到数字等），继续进行常规退出条件判断
                if loading(['not'], check_interval=0.1, click_times=0, timeout=5):
                    print('[WARN] 背包空位不足，停止购买')
                    break
                if image('close'):
                    print('[INFO] 检测到关闭按钮，退出本次商品页')
                    break
                press('enter')
                if purchase_sum >= total_qty:
                    print(f"[INFO] 已累计识别数量达到 {purchase_sum}，达到购买量 {total_qty}，停止循环")
                    break

            # 循环结束后的总结输出
            remaining_final = max(0, total_qty - purchase_sum)
            if purchase_sum >= total_qty:
                print(f"[SUCCESS] 购买完成：已购 {purchase_sum}/{total_qty}，已达成目标")
            else:
                print(f"[INFO] 购买未达成：已购 {purchase_sum}/{total_qty}，剩余 {remaining_final}")
    
    # 如果是platinum且购买成功，更新购买时间
    if item == 'platinum i' and purchase_sum > 0:
        last_platinum_purchase_time = time.time()
        print(f"[INFO] 更新platinum购买时间记录: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_platinum_purchase_time))}")

    press('esc')
    press('esc') 
    press('esc') 
    pause(3)


def claim_rewards():
    enter_game()
    current_hour = time.localtime().tm_hour
    if not (4 <= current_hour < 8):
        print('当前不在4-8点,不领取任务奖励')
        return
    press('8')
    time.sleep(3)    
    image('land_8claim_all') 
    time.sleep(3)
    press('enter')
    press('enter')
    time.sleep(4)
    image('x_land')

    press('k')
    time.sleep(3)    
    image('land_kclaim_all') 
    time.sleep(3)
    press('enter')
    press('enter')
    time.sleep(4)
    image('land_week')
    time.sleep(3)
    image('land_kclaim_all') 
    time.sleep(3)
    press('enter')
    press('enter')
    time.sleep(4)

    press('esc')
    pause(3)


def alchemy(plot=None, name=None):
    enter_game()
    if image('claim_alchemy'):
        time.sleep(5)
        if image('deleted', offset=(-200, 290)):
            print('储存空间不够')
            return
        else:
            press('enter')
    else:
        print('不需要claim')
        # return
    if plot == '57_119':
        image('acoin', offset=(54, 450), click_times=2)
    if plot == '119_56':
        image('acoin', offset=(413, 442), click_times=2)
    if plot == '123_122':
        image('acoin', offset=(120, 320), click_times=2)
    if plot == '122_138':
        image('acoin', offset=(72, 363), click_times=2)
    if plot == '105_128':
        image('acoin', offset=(237, 440), click_times=2)
    if plot == '113_18':
        image('acoin', offset=(293, 448), click_times=2)

    time.sleep(2)
    image('alchemy', offset=(-190, 100), click_times=2)  # Dismantle
    image('alchemy', offset=(0, 300))  # 输入框
    time.sleep(0.3)
    pyautogui.typewrite(name, interval=0.12)
    time.sleep(1.0)
    if not image('platinum_ingot', click_times=2, region=(0, 0, 1000, 1000)):
        image('platinum_ore', click_times=2, region=(0, 0, 1000, 1000))
        image('platinum_dust', threshold=0.92, click_times=2, region=(0, 0, 1000, 1000))
        image('gold_ore', click_times=2, offset=(0, -20), region=(0, 0, 1000, 1000))
    image('alchemy', offset=(525, 795), click_times=6)  # max
    press('space')
    time.sleep(2)
    press('esc')
    image('acoin', offset=(-100, 0))
    pause(3)

def stuck(plot=None):
    enter_game()

    pending_buys = []
    
    if plot == '122_138':
        image('stuck')
        time.sleep(2)
        if image('stuck_leather'):
            if image('not_enough_resources'):
                pending_buys.append(('122_138','cow feed', 'a_uncommon_cow_feed', '600'))
        if image('stuck_sheep_meat'):
            if image('not_enough_resources'):
                pending_buys.append(('122_138', 'sheep feed', 'a_uncommon_sheep_feed', '500'))
        if image('stuck_gold'):
            if image('not_enough_resources'):
                pending_buys.append(('122_138','gold ore', 'a_common_gold_ore', '1000'))
        if image('stuck_amethyst'):
            if image('not_enough_resources'):
                pending_buys.append(('122_138','amethyst ore', 'a_common_amethyst_ore', '1000'))
        if image('stuck_diamond'):
            if image('not_enough_resources'):
                pending_buys.append(('122_138','diamond ore', 'a_common_diamond_ore', '1000'))
        if image('stuck_coal_dust', threshold=0.92):
            if image('full'):
                press('esc')
                sell('uncommon_coal_dust', '1')
                sell('rare_coal_dust', '2')
                sell('epic_coal_dust', '4') 
                sell('common_charcoal', '3')     
                sell('uncommon_charcoal', '3')
                sell('rare_charcoal', '4')
                sell('epic_charcoal', '5')
            if image('not_enough_resources'):
               pending_buys.append(('122_138', 'SMG', 'coal_dust'))
               pending_buys.append(('122_138', 'SMG', 'charcoal'))
        
            
    elif plot == '57_119':
        image('stuck')
        time.sleep(2)
        if image('stuck_leather'):
            if image('not_enough_resources'):
                pending_buys.append(('57_119','cow feed', 'a_uncommon_cow_feed', '1200'))
        if image('stuck_sheep_meat'):
            if image('not_enough_resources'):
                pending_buys.append(('57_119', 'sheep feed', 'a_uncommon_sheep_feed', '500'))
        if image('stuck_gold'):
            if image('not_enough_resources'):
                pending_buys.append(('57_119','gold ore', 'a_common_gold_ore', '1000'))
        if image('stuck_silver'):
            if image('not_enough_resources'):
                pending_buys.append(('57_119','silver ore', 'a_common_silver_ore', '1000'))
        if image('stuck_emerald'):
            if image('not_enough_resources'):
                pending_buys.append(('57_119','emerald ore', 'a_common_emerald_ore', '500'))
        if image('stuck_topaz'):
            if image('not_enough_resources'):
                pending_buys.append(('57_119','topaz ore', 'a_common_topaz_ore', '500'))
        if image('stuck_coal_dust'):
            if image('full'):
                press('esc')
                sell('uncommon_coal_dust', '2')
                sell('rare_coal_dust', '3')
                sell('epic_coal_dust', '4') 
                sell('common_charcoal', '3')     
                sell('uncommon_charcoal', '3')
                sell('rare_charcoal', '4')
                sell('epic_charcoal', '5')
            if image('not_enough_resources'):
               pending_buys.append(('57_119', 'SMG', 'coal_dust'))
               
    
    elif plot == '105_128':
        image('stuck')
        time.sleep(2)
        if image('stuck_gold'):
            if image('not_enough_resources'):
                pending_buys.append(('105_128','gold ore', 'a_common_gold_ore', '500'))
        if image('stuck_emerald'):
            if image('not_enough_resources'):
                pending_buys.append(('105_128','emerald ore', 'a_common_emerald_ore', '500'))
        if image('stuck_coal_dust'):
            if image('not_enough_resources'):
               pending_buys.append(('105_128', 'SMG', 'coal_dust'))
               pending_buys.append(('105_128','SMG', 'charcoal'))
                

    if pending_buys:
        press('esc')
        for buy_info in pending_buys:
            # 使用 buy_auction 购买的物品 
            if buy_info[1] in ['emerald ore', 'topaz ore', 'diamond ore', 'amethyst ore', 'gold ore', 'silver ore', 'cow feed', 'sheep feed']:
                buy_auction(buy_info[0], buy_info[1], buy_info[2], buy_info[3])
            
            # 使用 buy_favor 购买的物品 
            if buy_info[2] in ['coal_dust', 'charcoal']:
                buy_favor(buy_info[0], buy_info[1], buy_info[2])

    press('esc')
    pause(3)


def main():
    switch_plot('57_119')
    collect_post(Transfers=True, Orders=True)
    stuck('57_119')
    alchemy('57_119', 'platinum')
    discard('copper_ore', 'iron_ore')   
    # buy_favor('57_119','Joyy', 'buy_cotton', None) 
    # current_hour = time.localtime().tm_hour
    # if (8 <= current_hour < 12) or (17 <= current_hour < 20):
    #     # buy_auction(plot='57_119', item='gold ore', quality='a_common_gold_ore', total_qty=200)
    #     # buy_auction(plot='57_119', item='silver ore', quality='a_common_silver_ore', total_qty=100)
    #     # buy_auction(plot='57_119', item='cow feed', quality='a_uncommon_cow_feed', total_qty=500)
    #     buy_auction(plot='57_119', item='platinum i', quality='a_rare_platinum_i', total_qty=200)
    #     # buy_favor(plot='57_119',target='1eea6', item1=None, item2='buy_feather') 
    claim_rewards()
    craft_equip('57_119')
    craft_food('57_119')
    transfer(plot='57_119', item=False, material=True, name='ame', target_plot='sand_122_138')
    transfer(plot='57_119', item=False, material=True, name='dia', target_plot='sand_122_138') 
    # transfer(plot='57_119', item=False, material=True, name='rub', target_plot='sand_105_128')

    # current_hour = time.localtime().tm_hour
    # if (13 <= current_hour < 16):   
    #     transfer(item=False, material=True, name='wood', target_plot='sand_105_128') 
    mine('57_119', iron_ore=False, cutting_tree=False)
    collect(5, 0)



    switch_plot('122_138')
    collect_post(Transfers=True, Orders=True)
    stuck('122_138')
    alchemy('122_138', 'platinum')
    discard('copper_ore', 'iron_ore')
    current_hour = time.localtime().tm_hour
    if (8 <= current_hour < 12) or (17 <= current_hour < 19):
        buy_auction(plot='122_138', item='diamond', quality='a_rare_diamond', total_qty=100)
    claim_rewards()
    # sell('uncommon_coal_dust', '1') 
    craft_equip('122_138')
    craft_food('122_138')

    transfer(plot='122_138', item=True, material=False, name=None, target_plot='arctic_57_119') 
    transfer(plot='122_138', item=False, material=True, name='top', target_plot='arctic_57_119') 
    transfer(plot='122_138', item=False, material=True, name='eme', target_plot='arctic_57_119')       
    # transfer(plot='122_138', item=False, material=True, name='rub', target_plot='sand_105_128')

    # mine('122_138', iron_ore=False, cutting_tree=False)
    collect(5, 0)


    switch_plot('105_128')
    collect_post(Transfers=True, Orders=True)
    stuck('105_128')
    alchemy('105_128', 'platinum')
    discard('copper_ore', 'iron_ore')
    # current_hour = time.localtime().tm_hour
    # if (8 <= current_hour < 12) or (17 <= current_hour < 20):
    #     # buy_auction(plot='105_128', item='gold ore', quality='a_common_gold_ore', total_qty=50)
    #     buy_auction(plot='105_128', item='platinum i', quality=None, total_qty=0)
    claim_rewards() 
    # sell('uncommon_coal_dust', '1')
    craft_equip('105_128')
    craft_food('105_128')

    transfer(plot='105_128', item=True, material=False, name=None, target_plot='arctic_57_119') 
    transfer(plot='105_128', item=False, material=True, name='cot', target_plot='arctic_57_119')
    transfer(plot='105_128', item=False, material=True, name='platinum i', target_plot='arctic_57_119')  
    # transfer(plot='105_128', item=False, material=True, name='ruby', target_plot='sand_122_138')  

    # mine('105_128', iron_ore=False, cutting_tree=False)
    collect(5, 0)


if __name__ == "__main__": 
    for _ in range(1):
        main()
        current_hour = time.localtime().tm_hour
        if (8 <= current_hour < 12) or (17 <= current_hour < 19):
            adventure(plot='57_119', equip=False)
            adventure(plot='122_138', equip=False)    
            adventure(plot='105_128', equip=False) 
            close_game()      
            countdown('下一次收菜', 2)
        else:
            close_game()      
            countdown('下一次收菜', 4)
    
    