# main.py
import cv2
import pyautogui
import numpy as np
import os
import time
import subprocess
import random
from datetime import datetime

def check_time(check_enabled=False):
    current_time = datetime.now()
    if check_enabled and not (11 <= current_time.hour < 15):
        print(f"当前时间 {current_time.strftime('%H:%M:%S')} 不在11:00-15:00范围内，程序结束。")
        return False
    print(f"当前时间 {current_time.strftime('%H:%M:%S')}，开始运行程序...")
    return True

def image(png, threshold=0.8, offset=(0, 0), click_times=1, region=None, color=True, gray_diff_threshold=15):
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

    if color:
        match_area = screen_img[
            max_loc[1]:max_loc[1] + template.shape[0],
            max_loc[0]:max_loc[0] + template.shape[1]
        ]

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
            time.sleep(0.1)
        print(f"[ACTION] 点击 {png}")

    return (center_x, center_y)

def loading(image_names, check_interval: float = 1, threshold=0.8, click_times=1, timeout=50,
            return_all_positions=False, color=True):
    start_time = time.time()
    print(f"正在加载 {image_names} ... ")
    found_positions = {}
    
    # 添加超时计数器
    if not hasattr(loading, 'timeout_count'):
        loading.timeout_count = 0

    while True:
        for image_name in image_names:
            # print(f"尝试匹配图片: {image_name}")
            pos = image(image_name, threshold=threshold, click_times=click_times, color=color)
            if pos is not None:
                print(f"成功匹配到图片: {image_name} 坐标: {pos}")
                found_positions[image_name] = pos
                # 找到任意一个图片就返回
                return {image_name: pos}

        # 检查是否超时
        if timeout and (time.time() - start_time) > timeout:
            elapsed_time = time.time() - start_time
            loading.timeout_count += 1
            print(f"加载超时 ({elapsed_time:.1f}秒) - 第 {loading.timeout_count} 次超时")
            
            # 如果超时超过3次，执行close_game()
            if loading.timeout_count >= 3:
                print("超时次数达到3次，正在关闭游戏...")
                close_game()
                loading.timeout_count = 0  # 重置计数器
                return None
            
            return None

        time.sleep(check_interval)

def in_game():
    return image('classic', offset=(600, 200), gray_diff_threshold=12) is not None

def enter_game():
    if not in_game():
        print("当前不在游戏中。")
        subprocess.Popen(r"E:\Axie Classic\axie_game.exe")
        loading(['classic_play'], check_interval=3)
        time.sleep(2)
        pyautogui.moveTo(100, 100)
        time.sleep(1)

    if image("free_spin", color=False):
        time.sleep(10)
        pyautogui.click()
        time.sleep(3)
        if image("free_spin", color=False):
            time.sleep(10)
            pyautogui.click()
            time.sleep(3)
    image("x_classic", color=False)  
    if image("classic_ok", color=False):
        close_game()
        time.sleep(30)                  
    if image("disconnect", gray_diff_threshold=13):
        close_game()
        time.sleep(30)
    if image("classic_exit"):
        close_game()
        time.sleep(30)
    if image("classic_cancel"):
        close_game()
        time.sleep(30)

def close_game():
    try:
        # 检查进程是否存在
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq axie_game.exe"],
                                capture_output=True, text=True, shell=True)
        if "axie_game.exe" in result.stdout:
            print("正在关闭游戏进程...")
            subprocess.run(["taskkill", "/f", "/im", "axie_game.exe"], shell=True)
            print("游戏进程已关闭")
        else:
            print("游戏进程未运行")
        time.sleep(10)
    except Exception as e:
        print(f"关闭游戏时发生错误: {str(e)}")
        time.sleep(10)

def in_rank_mode():
    return image('classic_rank_mode', click_times=0) is not None

def enter_battle():      
    if not in_rank_mode():
        print("当前不在排位賽中。")
        image('classic_arena')
        if image('box1'):
            time.sleep(2)
            image('open'), time.sleep(3)
            pyautogui.click(), time.sleep(2)
        if image('box2'):
            time.sleep(2)
            image('open'), time.sleep(3)
            pyautogui.click(), time.sleep(2)
        if image('box3'):
            time.sleep(2)
            image('open'), time.sleep(3)
            pyautogui.click(), time.sleep(2)  
        if image('classic_quest', threshold=0.95):
            time.sleep(2)
            image('classic_claim', color=False), time.sleep(2)
            pyautogui.click(), time.sleep(2)
            pyautogui.press('esc')
            image('classic_cancel')
        if image('classic_play'):
            time.sleep(2)
            pyautogui.moveTo(100, 100)
            time.sleep(1)
            image('classic_arena')
    else:
        print("当前已经在战斗中。")

def main(target_victories=1):
    # 初始化计数
    total_games = 0
    victories = 0
    defeats = 0
    
    # 记录开始时间
    start_time = time.time()
    max_runtime = 60 * 60  

    # 检查时间
    if not check_time():
        return

    while True:
        # 检查是否超过最大运行时间
        if time.time() - start_time > max_runtime:
            print(f"程序运行时间已达到{max_runtime//60}分钟，自动结束")
            close_game()
            break
            
        enter_game()
        enter_battle()
        print("开始检测战斗状态...")
        result = loading(['classic_end', 'classic_victory','classic_defeat', 'classic_draw'], 
                        click_times=0, 
                        threshold=0.7)
        
        if result:
            found_image = list(result.keys())[0]  # 获取找到的图片名称
            print(f"检测到状态: {found_image}")
            
            if 'classic_end' in result:
                time.sleep(3)
                for _ in range(5):
                    if image('classic_1.png', offset=(0, 60), click_times=2):
                        pyautogui.moveRel(0, -100)                  
                    if image('classic_0.png', offset=(0, 60), click_times=2): 
                        pyautogui.moveRel(0, -100)
                print("出牌结束")
                
            if 'classic_defeat' in result:
                print("失败")
                image('classic_defeat', click_times=1)
                time.sleep(3)
                pyautogui.moveRel(0, 0)
                pyautogui.click()
                total_games += 1
                defeats += 1
                current_time = datetime.now()
                print(f"\n战斗统计 [{current_time.strftime('%H:%M:%S')}]")
                print(f"总场数: {total_games}")
                print(f"胜利: {victories}")
                print(f"失败: {defeats}")
                if total_games > 0:
                    win_rate = (victories / total_games) * 100
                    print(f"胜率: {win_rate:.2f}%\n")
                
            if 'classic_draw' in result:
                print("平局")
                image('classic_draw', click_times=1)
                time.sleep(3)
                pyautogui.moveRel(0, 0)
                pyautogui.click()

            if 'classic_victory' in result:
                print("胜利")
                image('classic_victory', click_times=1)
                time.sleep(3)
                pyautogui.moveRel(0, 0)
                pyautogui.click(), time.sleep(3)
                pyautogui.click(), time.sleep(3), pyautogui.click()
                total_games += 1
                victories += 1
                current_time = datetime.now()
                print(f"\n战斗统计 [{current_time.strftime('%H:%M:%S')}]")
                print(f"总场数: {total_games}")
                print(f"胜利: {victories}")
                print(f"失败: {defeats}")
                if total_games > 0:
                    win_rate = (victories / total_games) * 100
                    print(f"胜率: {win_rate:.2f}%\n")
                if victories >= target_victories:
                    print(f"已达到目标胜利次数: {target_victories}，程序结束")
                    close_game()
                    break
        
        time.sleep(random.randint(1, 3))
        image('classic_end')

if __name__ == '__main__':
    # 设置目标胜利次数，默认为1
    current_hour = time.localtime().tm_hour
    if (11 <= current_hour < 14):
        main(target_victories=1)
    
    
                        
    