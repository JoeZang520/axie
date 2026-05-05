import cv2
import pyautogui
import numpy as np
import os
import time
import random
import subprocess
import sys
from datetime import datetime

exe_path = r"E:\WildForesto05uM\WildForest.exe"

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

    # region统一为(left, top, width, height)
    if region is None:
        region = (0, 0, *pyautogui.size())
    x, y, w, h = region
    # 区域尺寸不能小于模板，否则 matchTemplate 会报错
    t_h, t_w = template.shape[:2]
    if w < t_w or h < t_h:
        return None
    screenshot = pyautogui.screenshot(region=(x, y, w, h))
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
        # print(f"[DEBUG] 没有找到 {png}，匹配度: {max_val:.3f} < {threshold}")
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

    center_x = max_loc[0] + template.shape[1] // 2 + x + offset[0]
    center_y = max_loc[1] + template.shape[0] // 2 + y + offset[1]

    if click_times > 0:
        for _ in range(click_times):
            pyautogui.click(center_x, center_y)
            time.sleep(0.5)
        print(f"[ACTION] 点击 {png} {center_x, center_y} {max_val}")

    return (center_x, center_y)


def loading(image_names, check_interval: float = 1, threshold=0.8, click_times=1, timeout=3,
            region=None, return_all_positions=False, color=True, gray_diff_threshold=15):
    start_time = time.time()
    found_positions = {}
    # 本轮 loading 内因检测到 wild 而关游戏重启的次数，最多 3 次
    wild_recovery_count = 0

    while True:
        elapsed = time.time() - start_time
        if timeout and timeout > 0:
            remaining = max(0, int(timeout - elapsed))
            sys.stdout.write(f"\r加载 {image_names} 剩余 {remaining} 秒 ... ")
            sys.stdout.flush()

        # 检查是否找到了所有图片
        # region 可为单个 (x,y,w,h) 或 列表 [(x,y,w,h), ...]，列表时在多个区域内依次查找
        regions_to_try = [region] if (region is not None and not isinstance(region, list)) else (region or [None])
        all_found = True
        for image_name in image_names:
            if image_name not in found_positions:
                pos = None
                for r in regions_to_try:
                    pos = image(
                        image_name,
                        threshold=threshold,
                        click_times=click_times,
                        region=r,
                        color=color,
                        gray_diff_threshold=gray_diff_threshold
                    )
                    if pos is not None:
                        break
                if pos is not None:
                    found_positions[image_name] = pos
                    if not return_all_positions:
                        print()  # 换行，结束倒计时行
                        return image_name  # 如果不需要所有位置，找到第一个就返回
                else:
                    all_found = False

        # 如果需要所有位置，且找到了所有图片，或者超时了，就返回结果
        if return_all_positions and (all_found or (timeout and elapsed > timeout)):
            if not found_positions:
                print(f"\n加载 {image_names} 超时")
                # 仅在超时后才检测；命中 logined 则直接关游戏退出
                if os.path.exists(os.path.join("pic", "logined.png")) and image(
                        "logined", threshold=threshold, click_times=0, gray_diff_threshold=gray_diff_threshold):
                    print("[FATAL] 超时后检测到 logined，关闭游戏并退出 wildforest 脚本")
                    close_game()
                    sys.exit(1)
                # 命中 wild 则关游戏重开并重试，最多 3 次
                if os.path.exists(os.path.join("pic", "wild.png")) and image(
                        "wild", threshold=threshold, click_times=0, gray_diff_threshold=gray_diff_threshold):
                    wild_recovery_count += 1
                    if wild_recovery_count > 3:
                        print("[FATAL] 超时后 wild 已恢复 3 次仍异常，关闭游戏并退出 wildforest 脚本")
                        close_game()
                        sys.exit(1)
                    print(f"[INFO] 超时后检测到 wild，关闭游戏并重启 ({wild_recovery_count}/3)")
                    close_game()
                    enter_game()
                    start_time = time.time()
                    found_positions = {}
                    continue
                return None
            print()
            return found_positions

        # 如果不需要所有位置，且超时了，就返回None
        if not return_all_positions and timeout and elapsed > timeout:
            print(f"\n加载 {image_names} 超时")
            # 仅在超时后才检测；命中 logined 则直接关游戏退出
            if os.path.exists(os.path.join("pic", "logined.png")) and image(
                    "logined", threshold=threshold, click_times=0, gray_diff_threshold=gray_diff_threshold):
                print("[FATAL] 超时后检测到 logined，关闭游戏并退出 wildforest 脚本")
                close_game()
                sys.exit(1)
            if os.path.exists(os.path.join("pic", "wild.png")) and image(
                    "wild", threshold=threshold, click_times=0, gray_diff_threshold=gray_diff_threshold):
                wild_recovery_count += 1
                if wild_recovery_count > 3:
                    print("[FATAL] 超时后 wild 已恢复 3 次仍异常，关闭游戏并退出 wildforest 脚本")
                    close_game()
                    sys.exit(1)
                print(f"[INFO] 超时后检测到 wild，关闭游戏并重启 ({wild_recovery_count}/3)")
                close_game()
                enter_game()
                start_time = time.time()
                found_positions = {}
                continue
            return None

        time.sleep(check_interval)


def in_game():
    return image('wild_forest', offset=(100, 0), gray_diff_threshold=12) is not None


def enter_game():
    if image('retry_wf'):
        time.sleep(60)
    if not in_game():
        print("当前不在游戏中。")
        # Epic 链接需用 start 打开，不能当 exe 直接 Popen
        if exe_path.startswith("com.") or "://" in exe_path:
            subprocess.Popen(["cmd", "/c", "start", "", exe_path], shell=True)
        else:
            subprocess.Popen(exe_path)
    time.sleep(3)


def close_game():
    try:
        # 检查进程是否存在
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WildForest.exe"],
                                capture_output=True, text=True, shell=True)
        if "WildForest.exe" in result.stdout:
            print("正在关闭游戏进程...")
            subprocess.run(["taskkill", "/f", "/im", "WildForest.exe"], shell=True)
            print("游戏进程已关闭")
        else:
            print("游戏进程未运行")
        time.sleep(10)
    except Exception as e:
        print(f"关闭游戏时发生错误: {str(e)}")
        time.sleep(10)


def in_battle():
    # 仅检测，不点击（避免误触/日志混淆）
    return image('wf_icon', threshold=0.6, click_times=0) is not None
           


def battle(n=11, elixers=None):
    success_count = 0
    while success_count < n:
        saved_opponent_pos = None  # 首次找到 opponent 时记下坐标，ninja 循环里复用
        if not in_battle():
            enter_game()
            print("当前不在战斗中。")
            if image('continue'):
                if loading(['to_battle'], timeout=120, click_times=0):
                    if image('0', threshold=0.95, click_times=0):
                        print("[INFO] 找到 0，胜利次数达到最大值，退出循环")
                        success_count = n
                        break
                    else:
                        image('to_battle')
            else:
                if loading(['to_battle'], timeout=120, click_times=0):
                    if image('0', threshold=0.95, click_times=0):
                        print("[INFO] 找到 0，胜利次数达到最大值，退出循环")
                        success_count = n
                        break
                    else:
                        image('to_battle')
            # 仅等待出现，不点击（避免把 wf_icon 点击日志当成“附近找到 opponent”）
            if elixers is not None:
                loading([elixers], timeout=100)
            found = loading(['wf_icon', 'continue'], threshold=0.75, timeout=180, click_times=0)
            if not found:
                continue
            if found == 'continue':
                pass
            # found == 'wf_icon'：在排除矩形之外查找 opponent。排除矩形：左上 wf_icon+(-60,-100)，右下 wf_icon+(400,150)
            elif found == 'wf_icon':
                wf_pos = image('wf_icon', threshold=0.75, click_times=0)
                opponent_regions = None
                if wf_pos:
                    wx, wy = wf_pos
                    screen_w, screen_h = pyautogui.size()
                    ex1 = max(0, wx - 60)
                    ey1 = max(0, wy - 100)
                    ex2 = min(screen_w, wx + 400)
                    ey2 = min(screen_h, wy + 150)
                    print(f"[INFO] wf_icon 坐标: ({wx}, {wy}), 排除矩形: 左上({ex1}, {ey1}), 右下({ex2}, {ey2})")
                    min_side = 20
                    regions_list = []
                    if ex1 >= min_side:
                        regions_list.append((0, 0, ex1, screen_h))
                    if screen_w - ex2 >= min_side:
                        regions_list.append((ex2, 0, screen_w - ex2, screen_h))
                    if ey1 >= min_side:
                        regions_list.append((ex1, 0, ex2 - ex1, ey1))
                    if screen_h - ey2 >= min_side:
                        regions_list.append((ex1, ey2, ex2 - ex1, screen_h - ey2))
                    if regions_list:
                        opponent_regions = regions_list
                found_opponent = loading(['opponent1', 'opponent2', 'opponent3'], threshold=0.76, timeout=30,
                                         region=opponent_regions, click_times=0)
                if found_opponent:
                    pos_result = loading([found_opponent], threshold=0.76, timeout=5, region=opponent_regions,
                                         click_times=0, return_all_positions=True)
                    if not pos_result or found_opponent not in pos_result:
                        continue
                    saved_opponent_pos = pos_result[found_opponent]  # 从 opponent_regions 中查到的坐标
                    ox, oy = saved_opponent_pos
                    inside = (
                        wf_pos
                        and (ex1 <= ox <= ex2)
                        and (ey1 <= oy <= ey2)
                    )
                    print(f"[INFO] opponent 坐标: ({ox}, {oy}), 在排除矩形内? {inside}")
                    if inside:
                        print("[INFO] opponent 在排除矩形内，忽略该点，继续等待...")
                        continue
                    time.sleep(2)
                    pyautogui.click(saved_opponent_pos[0], saved_opponent_pos[1])
                    time.sleep(0.2)
                    pyautogui.click(saved_opponent_pos[0], saved_opponent_pos[1])
                    time.sleep(1)
                else:
                    continue
        blue_pos = None
        print("[DEBUG] 开始查找 blue+")
        blue_result = loading(['blue+'], threshold=0.7, click_times=0, timeout=10, return_all_positions=True)
        if blue_result and 'blue+' in blue_result:
            blue_pos = blue_result['blue+']  # 直接从 loading 返回结果中获取坐标
            print(f"[INFO] 找到 blue+，坐标: {blue_pos}")
            # 保持原逻辑：找到后点击一次 blue+
            pyautogui.click(blue_pos[0], blue_pos[1])
        else:
            print("[WARN] 在超时时间内未找到 blue+")

        if blue_pos:
            bx, by = blue_pos
            time.sleep(1)
            image('upgrade_barrack1', threshold=0.6)
            # 全屏找 archer，找到后不点击，马上点击 blue+ 坐标，再完成后续
            if loading(['archer'], threshold=0.65, click_times=0, timeout=15):
                print("[INFO] 找到 archer，准备再次点击 blue+ 并升级 barrack2")
                pyautogui.click(bx, by)
                time.sleep(1)               
                image('upgrade_barrack2')
                if loading(['snipper'], threshold=0.65, click_times=0, timeout=15):
                    print("[INFO] 找到 snipper，准备再次点击 blue+ 并升级 barrack3")
                    pyautogui.click(bx, by)
                    time.sleep(1)               
                    image('upgrade_barrack3')
            else:
                print("[WARN] 在超时时间内未找到 archer，跳过 barrack2 升级")
        # 与首次一致：排除矩形 左上 wf_icon+(-60,-60)，右下 wf_icon+(400,150)，在此矩形之外查找 opponent
        opponent_regions = None
        wf_pos = image('wf_icon', threshold=0.75, click_times=0) if in_battle() else None
        if wf_pos:
            wx, wy = wf_pos
            screen_w, screen_h = pyautogui.size()
            ex1 = max(0, wx - 60)
            ey1 = max(0, wy - 60)
            ex2 = min(screen_w, wx + 400)
            ey2 = min(screen_h, wy + 150)
            min_side = 20
            regions_list = []
            if ex1 >= min_side:
                regions_list.append((0, 0, ex1, screen_h))
            if screen_w - ex2 >= min_side:
                regions_list.append((ex2, 0, screen_w - ex2, screen_h))
            if ey1 >= min_side:
                regions_list.append((ex1, 0, ex2 - ex1, ey1))
            if screen_h - ey2 >= min_side:
                regions_list.append((ex1, ey2, ex2 - ex1, screen_h - ey2))
            if regions_list:
                opponent_regions = regions_list
        juggernaut_result = loading(['juggernaut'], threshold=0.6, click_times=0, timeout=15, return_all_positions=True)
        if juggernaut_result and 'juggernaut' in juggernaut_result:
            saved_pos = juggernaut_result['juggernaut']
            time.sleep(2)
            for _ in range(10):
                # ninja / opponent 坐标均复用前面已获取的，不再在循环内重复查找
                if saved_pos and saved_opponent_pos:
                    drag(saved_pos[0], saved_pos[1], saved_opponent_pos[0], saved_opponent_pos[1])
                    time.sleep(0.5)
                    pyautogui.moveRel(0, 130)
                    pyautogui.click()
                    time.sleep(0.2)
                    pyautogui.click()
                    time.sleep(1)
                if loading(['continue'], click_times=0, timeout=2):
                    break
        # 每轮战斗结束后检查是否出现胜利画面
        if image('victory_wf', threshold=0.8, click_times=0):
            success_count += 1
            print(f"[INFO] 检测到胜利画面 victory_wf，当前成功次数: {success_count}/{n}")
        loading(['continue'], timeout=2)
            


def drag(start_x, start_y, end_x, end_y, duration=1.0):
    """从起点坐标按住鼠标左键拖拽到终点坐标后松开"""
    try:
        pyautogui.moveTo(start_x, start_y)
        pyautogui.mouseDown()
        pyautogui.moveTo(end_x, end_y, duration=duration)
        pyautogui.mouseUp()
        print(f"[ACTION] 从 ({start_x}, {start_y}) 拖拽到 ({end_x}, {end_y})")
    except Exception as e:
        print(f"[警告] 拖拽失败: {str(e)}")
        print("[INFO] 继续执行后续操作...")

def train():
    enter_game()
    loading(['castle'], timeout=60)  
    time.sleep(2)
    image('gold_wf')   
    time.sleep(2)
    image('camp')
    if loading(['collect_all'], gray_diff_threshold=10, timeout=10):
        time.sleep(10)
    trained_any = False
    for i in range(6):
        if image(f"train{i}", threshold=0.9):
            print(f"[INFO] 找到 train{i}，开始训练")
            time.sleep(2)
            if image('train', gray_diff_threshold=13):
                time.sleep(5)
            image('x_wf')
            time.sleep(1)
            trained_any = True
        else:
            print(f"[WARN] 未找到 train{i}，继续尝试下一个")
            continue

    if not trained_any:
        print("[WARN] train1~train8 全部未找到")
    # 无论是否找到/训练，全部尝试完后都执行一次返回与关闭
    image('return')
    image('x_wf')
           
def shutdown_computer():
    # 仅在 Windows 上执行关机，避免在非 Windows 环境报错
    if os.name != "nt":
        print("[WARN] 当前不是 Windows 系统，跳过关机。")
        return
    try:
        print("[ACTION] 关闭计算机...")
        # /s: 关机, /t: 倒计时(秒)。这里设置为 0，表示立即执行
        subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
    except Exception as e:
        print(f"[ERROR] 关机失败: {str(e)}")       


if __name__ == "__main__":  
    train()
    # battle(3, elixers='stormrage')
    # battle(4, elixers='skybreaker')
    # battle(4, elixers='manasaver')
    # battle(4, elixers='tireless')
    
    battle(5, elixers=None)
    close_game()
    # shutdown_computer()
    














