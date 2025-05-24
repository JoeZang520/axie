import cv2
import pyautogui
import numpy as np
import os
import time
import subprocess
from axie_cards import axie_cards, card_priority, card_to_detect, thresholds, no_fragment_cards, exe_path


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
            time.sleep(0.5)
        print(f"[ACTION] 点击 {png}")

    return (center_x, center_y)



def image_multi(png_list, thresholds=thresholds, region=None, min_x_distance=60):
    if isinstance(png_list, str):
        png_list = [png_list]

    if not thresholds:
        raise ValueError("阈值字典 (thresholds) 必须提供")

    region = region or (0, 0, *pyautogui.size())
    x1, y1, x2, y2 = region

    screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
    screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

    results = {}

    def is_far_enough_x(cx, points, min_distance):
        for px, _, _ in points:
            if abs(cx - px) < min_distance:
                return False
        return True

    for role in png_list:
        templates = []
        i = 1
        while True:
            path = os.path.join('pic', f"{role}_{i}.png")
            if os.path.exists(path):
                templates.append(path)
                i += 1
            else:
                break

        if not templates:
            print(f"[ERROR] 未找到任何多模板图片：{role}_1.png, {role}_2.png 等")
            results[role] = []
            continue

        threshold = thresholds.get(role)
        if threshold is None:
            print(f"[WARN] 角色 {role} 没有设置阈值，跳过该角色")
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

                # print(f"匹配点: ({cx}, {cy}), 匹配度: {score:.3f}, 图片: {template_path}")

                if is_far_enough_x(cx, all_points, min_x_distance):
                    all_points.append((cx, cy, score))

        results[role] = all_points

    return results


def detect_all_hand_cards():
    matches = image_multi(card_to_detect)
    result = {}
    card_slot_index = 1  # 全局卡槽编号

    for role, points in matches.items():
        if role not in axie_cards:
            continue

        card_list = axie_cards[role]
        sorted_points = sorted(points, key=lambda p: p[0])

        matched_cards = set()
        role_cards_info = []

        for idx, (x, y, _) in enumerate(sorted_points, start=1):
            pyautogui.moveTo(x, y)
            time.sleep(0.2)

            matched_this_axie = []

            for card in card_list:
                name, energy, target, target_side, target_row = card

                if name in matched_cards:
                    continue

                x1 = int(x) - 100
                y1 = max(0, int(y) - 400)
                x2 = x1 + 300
                y2 = y1 + 400
                region = (x1, y1, x2, y2)

                pos = image(name, click_times=0, region=region)
                if pos:
                    matched_this_axie.append({
                        "name": name,
                        "energy": energy,
                        "target": target,
                        "target_side": target_side,
                        "target_row": target_row,
                        "target_pos": None
                    })
                    matched_cards.add(name)

            if not matched_this_axie:
                print(f"{role} 第 {card_slot_index} 张卡：无牌")
            else:
                for card in matched_this_axie:
                    print(
                        f"{role} 第 {card_slot_index} 张卡: {card['name']}，目标: {card['target']}"
                    )

            role_cards_info.append({
                "slot_index": card_slot_index,
                "cards": matched_this_axie
            })

            card_slot_index += 1
            pyautogui.moveRel(0, -500)

        result[role] = role_cards_info

    return result


def wait_for_load(image_name, check_interval=1, threshold=0.8, click_times=1, timeout=60):
    """循环检测指定图片出现，返回True或False"""
    start_time = time.time()
    print(f"正在加载 {image_name} ... ")
    while True:
        pos = image(image_name, threshold=threshold, click_times=click_times, color=True)
        if pos is not None:
            return True  # 图片找到了，返回True
        if timeout and (time.time() - start_time) > timeout:
            print(f"加载 {image_name} 超时")
            return False  # 超时，返回False
        time.sleep(check_interval)



def get_energy_info(timeout=2):
    check_interval = 0.5  # 每次尝试的间隔
    start_time = time.time()
    energy_value = 3      # 默认能量为3
    fragment_value = 0    # 默认碎片为0

    while time.time() - start_time < timeout:
        found_energy = False
        # 查找能量值
        for i in range(4, 0, -1):
            energy_pos = image(f"energy_{i}", threshold=0.8, click_times=0)
            if energy_pos:
                energy_value = i
                found_energy = True
                break
        if not found_energy:
            print("[INFO] 能量值未检测到，默认为3")

        found_fragment = False
        # 查找碎片值
        for i in range(12):
            fragment_pos = image(f"fragment_{i}", threshold=0.95, click_times=0, gray_diff_threshold=12)
            if fragment_pos:
                fragment_value = i
                found_fragment = True
                break
        if not found_fragment:
            print("[INFO] 碎片值未检测到")

        if found_energy:
            return energy_value, fragment_value

        time.sleep(check_interval)

    # 超时后返回默认或最后检测值
    return energy_value, fragment_value

current_energy = None
fragment_value = 0
if current_energy is None:
    current_energy, fragment_value = get_energy_info()


print(f"[INFO] 当前能量总数: {current_energy}, 当前碎片数量: {fragment_value}")