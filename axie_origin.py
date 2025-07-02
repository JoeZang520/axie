import cv2
import pyautogui
import numpy as np
import os
import time
import random
import subprocess
from datetime import datetime
from axie_cards import (
    axie_cards, card_priority, card_to_detect, thresholds, exe_path,
    MIDDLE_ROLE, CHOICE
)

# 全局变量存储初始位置信息
initial_positions = {
    'ally': {'前排': [], '中排': [], '后排': []},
    'enemy': {'前排': [], '中排': [], '后排': []}
}


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

    center_x = max_loc[0] + template.shape[1] // 2 + x + offset[0]
    center_y = max_loc[1] + template.shape[0] // 2 + y + offset[1]

    if click_times > 0:
        for _ in range(click_times):
            pyautogui.click(center_x, center_y)
            time.sleep(0.5)
        print(f"[ACTION] 点击 {png} {center_x, center_y} {max_val}")

    return (center_x, center_y)


def image_multi(png_list, thresholds=thresholds, region=None, min_x_distance=60, color=True):
    if isinstance(png_list, str):
        png_list = [png_list]

    if not thresholds:
        raise ValueError("阈值字典 (thresholds) 必须提供")

    # 如果没有指定区域，使用全屏
    if region is None:
        region = (0, 0, *pyautogui.size())

    # 确保region是(left, top, width, height)格式
    left, top, width, height = region
    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    screen_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)  # 转换为BGR彩色图

    results = {}

    def is_far_enough_x(cx, points, min_distance):
        for px, _, _ in points:
            if abs(cx - px) < min_distance:
                return False
        return True

    def check_color_diff(match_area, template, color_threshold=30):
        # 计算匹配区域和模板之间的颜色差异
        diff = cv2.absdiff(match_area, template)
        mean_diff = np.mean(diff)
        return mean_diff < color_threshold

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
            path = os.path.join('pic', f"{role}.png")
            if os.path.exists(path):
                templates = [path]
            else:
                print(f"[ERROR] 未找到图片：{role}.png")
                results[role] = []
                continue

        threshold = thresholds.get(role, 0.8)
        all_points = []
        for template_path in templates:
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                print(f"[ERROR] 无法读取图片：{template_path}")
                continue

            if color:
                # 彩色匹配
                result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
            else:
                # 灰度匹配
                screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)

            locations = np.where(result >= threshold)

            for pt in zip(*locations[::-1]):
                # 获取匹配区域
                match_area = screen_img[
                             pt[1]:pt[1] + template.shape[0],
                             pt[0]:pt[0] + template.shape[1]
                             ]

                # 检查颜色差异
                if color and not check_color_diff(match_area, template):
                    continue

                center_x = pt[0] + template.shape[1] // 2 + left
                center_y = pt[1] + template.shape[0] // 2 + top
                match_value = float(result[pt[1], pt[0]])  # 转换为Python float

                if is_far_enough_x(center_x, all_points, min_x_distance):
                    all_points.append((center_x, center_y, match_value))

        if not all_points:
            print(f"[MISS] 未找到 {role}")
        else:
            values = [f"{p[2]:.3f}" for p in all_points]  # 格式化为3位小数的字符串
            print(f"[MATCH] {role}: {values}")

        results[role] = all_points

    return results


def loading(image_names, check_interval: float = 1, threshold=0.8, click_times=1, timeout=50,
            return_all_positions=False, color=True):
    start_time = time.time()
    print(f"正在加载 {image_names} ... ")
    found_positions = {}

    while True:
        # 检查是否找到了所有图片
        all_found = True
        for image_name in image_names:
            if image_name not in found_positions:
                pos = image(image_name, threshold=threshold, click_times=click_times, color=color)  # 使用传入的color参数
                if pos is not None:
                    found_positions[image_name] = pos
                    if not return_all_positions:
                        return image_name  # 如果不需要所有位置，找到第一个就返回
                else:
                    all_found = False

        # 如果需要所有位置，且找到了所有图片，或者超时了，就返回结果
        if return_all_positions and (all_found or (timeout and (time.time() - start_time) > timeout)):
            if not found_positions:
                print(f"加载 {image_names} 超时")
                return None
            return found_positions

        # 如果不需要所有位置，且超时了，就返回None
        if not return_all_positions and timeout and (time.time() - start_time) > timeout:
            print(f"加载 {image_names} 超时")
            return None

        time.sleep(check_interval)


def detect_cards(color=True, quick_check=False):
    pyautogui.moveTo(100, 100)
    time.sleep(2)
    # 等待icon图片出现
    icon_result = loading(['icon'], click_times=0, timeout=5, return_all_positions=True)
    if icon_result is None:
        print("[ERROR] 未找到icon图片，无法定位手牌区域")
        return {}
    else:
        pyautogui.moveRel(0, 0)

    icon_x, icon_y = icon_result['icon']  # 从字典中获取icon的坐标
    # 计算搜索区域的左上角和右下角坐标
    x1 = int(icon_x - 420)  # 左上角x坐标
    y1 = int(icon_y + 660)  # 左上角y坐标
    x2 = int(icon_x + 730)  # 右下角x坐标
    y2 = int(icon_y + 870)  # 右下角y坐标

    # 定义搜索区域 (left, top, width, height)
    search_region = (x1, y1, x2 - x1, y2 - y1)

    # 角色位置检测始终使用彩色
    matches = image_multi(card_to_detect, region=search_region, color=True)
    result = {}
    card_slot_index = 1

    # 如果是快速检测模式，只返回检测到的卡片数量
    if quick_check:
        total_cards = sum(len(points) for points in matches.values())
        return {'total_cards': total_cards}

    for role, points in matches.items():
        card_list = axie_cards[role]
        # 按x坐标排序点位
        sorted_points = sorted(points, key=lambda p: p[0])

        # 只对前中后排的axie使用matched_cards
        matched_cards = set() if role in card_to_detect else None
        role_cards_info = []

        for idx, (x, y, _) in enumerate(sorted_points, start=1):
            # 移动鼠标到卡片位置
            pyautogui.moveTo(x, y)
            time.sleep(0.1)

            matched_this_axie = []
            found_card = False  # 添加标志来跟踪是否已找到卡片

            for card in card_list:
                # 如果已经找到卡片，跳过剩余的检测
                if found_card:
                    break

                name, energy, target, target_side, target_row = card

                # 只对前中后排的axie检查matched_cards
                if matched_cards is not None and name in matched_cards:
                    continue

                x1 = int(x - 100)
                y1 = int(y - 400)
                x2 = int(x1 + 300)
                y2 = int(y1 + 400)
                region = (x1, y1, x2 - x1, y2 - y1)

                pos = image(name, click_times=0, region=region, color=color)
                if pos:
                    matched_this_axie.append({
                        "name": name,
                        "energy": energy,
                        "target": target,
                        "target_side": target_side,
                        "target_row": target_row,
                        "target_pos": None
                    })
                    # 只对前中后排的axie添加到matched_cards
                    if matched_cards is not None:
                        matched_cards.add(name)
                    found_card = True  # 标记已找到卡片
                    break  # 找到卡片后立即跳出循环

            if matched_this_axie:
                for card in matched_this_axie:
                    print(f"{role} 第 {card_slot_index} 张卡: {card['name']}")
            else:
                print(f"{role} 第 {card_slot_index} 张卡：无牌")

            role_cards_info.append({
                "slot_index": card_slot_index,
                "cards": matched_this_axie or [
                    {"name": "unknown", "energy": 0, "target": None, "target_side": None, "target_row": None}]
                # 如果没有匹配到具体卡牌，也添加一个占位卡牌
            })

            card_slot_index += 1
            # 鼠标移动到卡片外
            pyautogui.moveRel(0, -500)

        result[role] = role_cards_info

    return result


def get_energy_info(timeout=3):  # 默认3秒超时
    check_interval = 0.1  # 检查间隔
    start_time = time.time()
    energy_value = 0  # 默认能量为3
    fragment_value = 0

    # 等待icon图片出现
    icon_result = loading(['icon'], click_times=0, threshold=0.95, timeout=5, return_all_positions=True)
    if icon_result is None:
        print("[ERROR] 未找到icon图片，无法定位能量和碎片区域")
        return energy_value, fragment_value
    else:
        pyautogui.moveRel(0, 0)

    icon_x, icon_y = icon_result['icon']  # 从字典中获取icon的坐标
    # 计算搜索区域的左上角和右下角坐标
    x1 = int(icon_x - 620)  # 左上角x坐标
    y1 = int(icon_y + 540)  # 左上角y坐标
    x2 = int(icon_x - 460)  # 右下角x坐标
    y2 = int(icon_y + 730)  # 右下角y坐标
    # 定义搜索区域 (left, top, width, height)
    search_region = (x1, y1, x2 - x1, y2 - y1)

    while time.time() - start_time < timeout:
        # 优化能量检测：从高到低检查，找到就立即返回
        for i in range(4, -1, -1):  # 从4到0检查
            # 对不同能量值使用不同的匹配参数
            if i == 0:
                # 0能量使用灰度图匹配
                energy_pos = image(f"energy_{i}", threshold=0.9, click_times=0, region=search_region, color=False)
            else:
                # 其他能量值使用彩色匹配
                energy_pos = image(f"energy_{i}", threshold=0.8, click_times=0, region=search_region, color=True,
                                   gray_diff_threshold=9)

            if energy_pos:
                energy_value = i
                # 找到能量后立即检查碎片
                for j in range(12):
                    fragment_pos = image(f"fragment_{j}", threshold=0.95, click_times=0, gray_diff_threshold=9,
                                         region=search_region)
                    if fragment_pos:
                        fragment_value = j
                        break
                print(f"[INFO] 当前能量总数: {energy_value}, 当前碎片数量: {fragment_value}")
                return energy_value, fragment_value

        time.sleep(check_interval)

    print(f"[INFO] 检测超时，使用默认能量值: {energy_value}, 当前碎片数量: {fragment_value}")
    return energy_value, fragment_value


def get_all_positions():
    """
    通过找到 'icon.png' 参照点，计算12个站位坐标，返回字典。
    需要你根据游戏界面实际偏移值调整offset_x和offset_y。
    """
    # 等待icon图片出现
    icon_result = loading(['icon'], click_times=0, threshold=0.95, timeout=5, return_all_positions=True)
    if icon_result is None:
        print("[ERROR] 未找到icon图片，无法定位手牌区域")
        return {}
    else:
        pyautogui.moveRel(0, 0)

    icon_x, icon_y = icon_result['icon']  # 从字典中获取icon的坐标

    # 4排每排起点坐标，基于icon点偏移确定（需你测量替换）
    # 这里的坐标是血条位置
    row_starts = {
        'A': (icon_x - 367, icon_y + 367),
        'B': (icon_x - 463, icon_y + 452),
        'C': (icon_x + 374, icon_y + 367),
        'D': (icon_x + 277, icon_y + 447)
    }

    x_spacing = 195  # 横向间距，单位像素
    all_positions = {}

    # 从血条位置转换为axie本体位置
    # axie本体位置在血条位置的右下方，x偏移30像素，y偏移70像素
    for row_letter, (start_x, start_y) in row_starts.items():
        for i in range(3):
            blood_x = start_x + i * x_spacing
            blood_y = start_y
            # 转换为axie本体位置
            axie_x = blood_x + 30
            axie_y = blood_y + 70
            all_positions[f"{row_letter}{i + 1}"] = (axie_x, axie_y)

    # print("[INFO] 计算得到12个位置的站位坐标：", all_positions)
    return all_positions


def analyze_blood_bar(x, y):
    """
    通过扫描血条像素来计算血量
    参数x, y是血条位置坐标
    返回：(血量百分比, 是否存活)
    """
    bar_start_x = x
    bar_y = y
    bar_length = 100
    bar_height = 1

    screenshot = pyautogui.screenshot(region=(bar_start_x, bar_y, bar_length, bar_height))
    img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # 只需要空血条的BGR颜色
    empty_color = np.array([70, 94, 147])  # 你可以用吸管工具取实际颜色
    tolerance = 30  # 容许色差

    health_pixels = 0
    total_pixels = bar_length * bar_height

    for y_ in range(bar_height):
        for x_ in range(bar_length):
            pixel = img[y_, x_]
            # 只要不是空血条色，就算作有血
            if np.sum(np.abs(pixel - empty_color)) > tolerance:
                health_pixels += 1

    health_percentage = int((health_pixels / total_pixels) * 100)
    health_percentage = max(0, min(100, health_percentage))
    return health_percentage, health_percentage > 0


def get_health_info(axie_positions):
    health_info = {}

    # 检查每个位置的血条
    for pos_name, (axie_x, axie_y) in axie_positions.items():
        # 血条位置在本体左上方
        blood_x = axie_x - 30
        blood_y = axie_y - 70

        # 获取血量信息
        health_percentage, is_alive = analyze_blood_bar(blood_x, blood_y)
        health_info[pos_name] = (health_percentage, is_alive)

    return health_info


def get_axie_info():
    all_positions = get_all_positions()
    if not all_positions:
        print("[ERROR] 无法获取位置信息")
        return None

    axie_info = {
        'ally': {'前排': [], '中排': [], '后排': []},
        'enemy': {'前排': [], '中排': [], '后排': []},
        'all': {}
    }

    # 直接在这里检测阵亡/空位
    dead_status = {}
    for pos_name, (axie_x, axie_y) in all_positions.items():
        region = (axie_x - 100, axie_y - 100, 200, 200)
        found = image(pos_name, region=region, threshold=0.75, click_times=0, color=True)
        dead_status[pos_name] = bool(found)

    # 获取血量信息
    health_info = get_health_info(all_positions)
    if not health_info:
        print("[ERROR] 无法获取血量信息")
        return None

    # 先收集所有存活的axie站位
    ally_order = ['A3', 'B3', 'A2', 'B2', 'A1', 'B1']
    enemy_order = ['D1', 'C1', 'D2', 'C2', 'D3', 'C3']
    ally_alive = []
    enemy_alive = []

    for pos_name, (axie_x, axie_y) in all_positions.items():
        if dead_status.get(pos_name):
            continue
        health_percentage, is_alive = health_info[pos_name]
        blood_x = axie_x - 30
        blood_y = axie_y - 70
        if is_alive:
            if pos_name in ally_order:
                ally_alive.append(
                    (ally_order.index(pos_name), pos_name, health_percentage, axie_x, axie_y, blood_x, blood_y))
            elif pos_name in enemy_order:
                enemy_alive.append(
                    (enemy_order.index(pos_name), pos_name, health_percentage, axie_x, axie_y, blood_x, blood_y))
            axie_info['all'][pos_name] = {
                'blood_coords': (blood_x, blood_y),
                'axie_coords': (axie_x, axie_y),
                'health': health_percentage,
                'is_alive': True
            }

    # 按顺序排序
    ally_alive.sort()
    enemy_alive.sort()
    ally_names = [x[1] for x in ally_alive]
    enemy_names = [x[1] for x in enemy_alive]

    # 分组函数
    def split_rows(names):
        n = len(names)
        if n == 1:
            return {'前排': names, '中排': [], '后排': []}
        elif n == 2:
            return {'前排': [names[0]], '中排': [], '后排': [names[1]]}
        elif n == 3:
            return {'前排': [names[0]], '中排': [names[1]], '后排': [names[2]]}
        elif n == 4:
            print('[WARN] 检测到4只axie，可能读图错误！')
            return {'前排': [names[0]], '中排': [names[1], names[2]], '后排': [names[3]]}
        elif n == 5:
            return {'前排': [names[0]], '中排': [names[1], names[2], names[3]], '后排': [names[4]]}
        elif n == 6:
            return {'前排': [names[0], names[1]], '中排': [names[2], names[3]], '后排': [names[4], names[5]]}
        else:
            return {'前排': [], '中排': [], '后排': []}

    axie_info['ally'].update(split_rows(ally_names))
    axie_info['enemy'].update(split_rows(enemy_names))

    print("\n=== AXIE 阵型信息 ===")
    for side, side_name in [('ally', '我方'), ('enemy', '敌方')]:
        print(f"【{side_name}】")
        for row in ['前排', '中排', '后排']:
            positions = axie_info[side][row]
            if positions:
                health_info_list = []
                for pos in positions:
                    health = axie_info['all'][pos]['health']
                    health_info_list.append(f"{pos}(血量:{health}%)")
                print(f"{row}: {', '.join(health_info_list)}")

    # 检测到A2阵亡时执行投降
    if 'A2' not in axie_info['all'] or not axie_info['all']['A2']['is_alive']:
        print("[INFO] 检测到A2阵亡，执行投降")
        image('menu')
        image('surrender')
        image('confirm_surrender')
        return 'GAME_OVER'

    return axie_info


def select_target(hand_cards, axie_info):
    all_cards = []
    for role, positions in hand_cards.items():
        for pos in positions:
            hotkey = pos['slot_index']
            for card in pos['cards']:
                if card.get('target'):
                    target_side = card.get('target_side')
                    target_row = card.get('target_row')

                    targets = []
                    # 只处理我方目标
                    if target_side == 'ally' and target_row == 'all':
                        # 优先处理confident和puppy_eye卡
                        if card['name'] in ['confident', 'puppy_eye', 'cuckoo']:
                            if 'A2' in axie_info['all'] and axie_info['all']['A2']['is_alive']:
                                targets = ['A2']
                        else:
                            # 其它卡
                            a2_alive = 'A2' in axie_info['all'] and axie_info['all']['A2']['is_alive']
                            a2_health = axie_info['all']['A2']['health'] if a2_alive else 999
                            if a2_alive and a2_health < 80:
                                targets = ['A2']
                            else:
                                # 所有存活目标，按血量从低到高排序
                                all_targets = []
                                for row in ['前排', '中排', '后排']:
                                    for pos_name in axie_info['ally'].get(row, []):
                                        if axie_info['all'][pos_name]['is_alive']:
                                            all_targets.append(pos_name)
                                all_targets.sort(key=lambda x: axie_info['all'][x]['health'])
                                targets = all_targets
                    # 敌方目标等其它逻辑保持不变
                    elif target_side == 'enemy' and target_row == 'front_back':
                        targets = []
                        for row in ['前排', '中排', '后排']:
                            for pos_name in axie_info['enemy'].get(row, []):
                                if axie_info['all'][pos_name]['is_alive']:
                                    targets.append(pos_name)
                    else:
                        targets = []

                    # 设置目标坐标
                    card['target_candidates'] = []
                    for pos_name in targets:
                        coords = axie_info['all'].get(pos_name, {}).get('axie_coords')
                        if coords:
                            card['target_candidates'].append(coords)
                    card['target_pos'] = card['target_candidates'][0] if card['target_candidates'] else None
                else:
                    card['target_pos'] = None
                    card['target_candidates'] = []

                card['role'] = role
                card['hotkey'] = hotkey
                all_cards.append(card)
    return all_cards


def play_zeal(cards):
    """
    处理zeal卡的使用策略
    :param cards: 包含zeal卡信息的列表
    """
    priority_cards = ['mini_little_branch', 'mini_shiba', 'mini_puppy_ear', 'mini_hero', 'mini_confident']
    zeal_count = len(cards)
    used_targets = set()  # 记录已使用的目标卡片

    print(f"[INFO] 检测到 {zeal_count} 张 zeal 卡")
    time.sleep(3)

    # 根据zeal卡数量决定策略
    if zeal_count == 1:
        # 只有一张就直接使用
        _use_single_zeal(cards[0], priority_cards, used_targets)
    elif zeal_count == 2:
        # 两张只使用一张
        _use_single_zeal(cards[0], priority_cards, used_targets)
    elif zeal_count >= 3:
        # 三张或以上使用两张
        for i in range(2):
            _use_single_zeal(cards[i], priority_cards, used_targets)


def keep_card(fragment_cost):
    """
    尝试保留卡片，尽可能用光碎片
    :param fragment_cost: 当前这次保留需要消耗的碎片数量
    :return: 是否成功保留任何卡片
    """
    # 点击保留按钮并设置搜索区域
    keep_pos = image('keep')
    if keep_pos:
        # 移动到keep按钮下方100像素的位置
        keep_x, keep_y = keep_pos
        print(f"[DEBUG] keep_x: {keep_x}, keep_y: {keep_y}")
        time.sleep(1)  # 等待动画效果
        
        # 设置搜索区域，以keep按钮位置为基准
        # 计算搜索区域的左上角坐标和宽高
        x1 = keep_x  # 左上角x坐标
        y1 = keep_y - 680  # 左上角y坐标（向上偏移）
        x2 = keep_x + 1150  # 向右搜索1150像素
        y2 = keep_y

        # 搜索区域：(左上角x, 左上角y, 宽度, 高度)
        search_region = (x1, y1, x2 - x1, y2 - y1)
        print(f"[DEBUG] 搜索区域: 左上({x1}, {y1}), 右下({x2}, {y2})")

        # 遍历所有优先保留的卡片
        keep_priority_cards = ['little_branch', 'shiba', 'ronin', 'zeal', 'puppy_ear', 'belieber', 'cattail', 'hero']
        found_count = 0  # 找到的卡片数量
        total_cost = 0  # 总消耗的碎片

        if image('origin_cancel', click_times=0):
            for card_name in keep_priority_cards:
                next_cost = found_count + 1
                if total_cost + next_cost > fragment_cost:
                    break
    
                mini_card_name = f"mini_{card_name}"
                print(f"[SEARCH] 查找要保留的卡片图片: {mini_card_name}")

                # 在指定区域内查找并点击对应的mini卡片
                if image(mini_card_name, region=search_region):
                    pyautogui.moveTo(100, 100)
                    print(f"[INFO] 找到卡片 {card_name}，选择保留")
                    found_count += 1
                    total_cost += next_cost

            # 如果找到了要保留的卡片
            if found_count > 0:
                # 按下回车确认保留
                pyautogui.press('enter')
                print(f"[INFO] 成功保留 {found_count} 张卡片，总共消耗 {total_cost} 碎片")
                return True
            else:
                # 如果没找到任何卡片
                image('origin_cancel')
                pyautogui.moveTo(100, 100)
                print("[INFO] 未找到任何可以保留的卡片")
                return False
        else:
            print("[INFO] 未找到origin_cancel按钮，跳过保留卡片")
            return False
    else:
        print("[INFO] 未找到keep按钮")
        return False


def _use_single_zeal(card, priority_cards, used_targets):
    """
    使用单张zeal卡的辅助函数
    """
    print(f"[ACTION] 按下快捷键 {card['hotkey']} 使用zeal卡")
    pyautogui.press(str(card['hotkey']))
    pyautogui.moveTo(100, 100)
    time.sleep(2)

    print("[INFO] 开始查找 zeal 目标卡片...")

    # 遍历优先级列表寻找未使用的目标
    for target in priority_cards:
        if target in used_targets:
            print(f"[SKIP] {target} 已被使用，跳过")
            continue

        print(f"[SEARCH] 正在查找 {target}...")
        if image(target):  # 如果找到并点击了卡牌
            print(f"[ACTION] 找到并选择 {target} 作为 zeal 目标")
            used_targets.add(target)  # 记录已使用的目标
            pyautogui.press('enter')
            pyautogui.moveTo(100, 100)
            time.sleep(1)
            return True
        else:
            print(f"[MISS] 未找到 {target}")

    print("[INFO] 已尝试所有优先级卡片但未找到可用目标，取消选择")
    image('origin_cancel')
    time.sleep(1)
    return False


def play_innocent_lamb(card):
    print(f"[ACTION] 按下快捷键 {card['hotkey']} 使用innocent_lamb")
    pyautogui.press(str(card['hotkey']))
    time.sleep(1)
    print("[ACTION] 按下快捷键 1 选择目标")
    pyautogui.press('1')
    print("[ACTION] 按下回车确认")
    pyautogui.press('enter')
    time.sleep(1)

def play_hero(hand_cards, used_cards, axie_info, energy):
    print("[INFO] 检测 hero 使用后的手牌数量...")
    # 计算当前理论剩余手牌数量
    total_cards = sum(len(pos['cards']) for positions in hand_cards.values() for pos in positions)
    remaining_cards = total_cards - used_cards
    print(f"[INFO] 总手牌数量: {total_cards}, 已使用: {used_cards}, 理论剩余: {remaining_cards}")

    # 快速检测手牌数量（不移动鼠标）
    time.sleep(2)
    current_cards = detect_cards(quick_check=True)
    if current_cards and 'total_cards' in current_cards:
        print(f"[INFO] 当前实际手牌数量: {current_cards['total_cards']}")

        # 如果实际手牌数量大于理论数量，说明hero增加了手牌
        if current_cards['total_cards'] > remaining_cards:
            print("[INFO] 手牌数量增加，重新检测手牌信息...")
            # 重新获取当前能量值
            energy, _ = get_energy_info()
            print(f"[INFO] 当前能量: {energy}")

            hand_cards = detect_cards()
            if not hand_cards:  # 如果检测失败，返回原始值
                print("[WARN] 手牌检测失败，跳过后续处理")
                return hand_cards, energy

            all_cards = select_target(hand_cards, axie_info)

            # 收集所有zeal卡
            zeal_cards = [card for card in all_cards if card['name'] == 'zeal']

            # 根据card_priority排序
            sorted_cards = sorted(all_cards,
                                key=lambda c: card_priority.index(c['name']) if c['name'] in card_priority else len(card_priority)
                                )

            # 检查是否有ronin卡
            has_ronin = any(card['name'] == 'ronin' for card in sorted_cards)
            ronin_card = next((card for card in sorted_cards if card['name'] == 'ronin'), None)

            # 如果有ronin，先从sorted_cards中移除它
            if has_ronin:
                sorted_cards = [card for card in sorted_cards if card['name'] != 'ronin']

            # 处理所有非zeal和非ronin卡片
            for card in sorted_cards:
                # 跳过unknown卡，只计入手牌数量，不尝试打出
                if card['name'] == 'unknown':
                    continue

                # 如果有ronin，保留最后一点能量给它
                if has_ronin and energy <= 1:
                    print(f"[INFO] 保留能量给ronin，跳过 {card['name']}")
                    continue

                # 检查能量是否足够
                if card['energy'] > energy:
                    print(f"[WARN] 能量不足，跳过 {card['name']}（需要 {card['energy']}，剩余 {energy}）")
                    continue

                # 根据卡牌名称执行不同的出牌策略
                if card['name'] == 'innocent_lamb':
                    print(f"[ACTION] 使用 {card['name']}（0 能量）")
                    play_innocent_lamb(card)
                    used_cards += 1  # 增加innocent_lamb的计数

                    # 检查是否有shiba或little_branch卡
                    has_2energy_cards = any(
                        card['name'] in ['shiba', 'little_branch'] 
                        for role, positions in hand_cards.items() 
                        for pos in positions 
                        for card in pos['cards']
                    )
                    
                    if not has_2energy_cards and zeal_cards:
                        print("[INFO] 检测到zeal卡，且没有shiba和little_branch，在innocent_lamb后立即使用")
                        used_zeal = zeal_cards[0]  # 记录使用的zeal卡
                        play_zeal([used_zeal])  # 只使用一张zeal
                        # 从zeal_cards中移除已使用的卡
                        zeal_cards = zeal_cards[1:]
                        # 从sorted_cards中也移除已使用的zeal卡
                        sorted_cards = [c for c in sorted_cards if c != used_zeal]
                    continue

                # 如果是zeal卡，跳过（因为可能已经在innocent_lamb后处理过）
                if card['name'] == 'zeal':
                    continue

                # 普通卡牌出牌逻辑
                print(f"[ACTION] 使用 {card['name']}（{card['energy']} 能量）")
                print(f"[ACTION] 按下快捷键 {card['hotkey']} 使用{card['name']}")
                pyautogui.press(str(card['hotkey']))
                used_cards += 1  # 记录使用的非zeal卡数量

                # 如果卡牌需要选择目标
                if card.get('target') and card.get('target_candidates'):
                    target = card['target_pos']
                    if target:
                        # 获取目标位置的名称（例如：A1, B2等）
                        pos_name = next((name for name, info in axie_info['all'].items() if info['axie_coords'] == target),
                                    "未知位置")
                        # 确定目标是敌方还是我方
                        side = "敌方" if pos_name.startswith(('C', 'D')) else "我方"
                        # 确定是前中后排
                        for row_name, positions in (axie_info['enemy' if side == "敌方" else 'ally']).items():
                            if pos_name in positions:
                                row = row_name
                                break
                        else:
                            row = "未知排"
                        print(f"[ACTION] 选择目标位置: {side}{row}（{pos_name}）")

                        # 检查middle4548是否出过牌
                        middle_role_played = False
                        for role, positions in hand_cards.items():
                            if role == MIDDLE_ROLE:
                                for pos in positions:
                                    for played_card in pos['cards']:
                                        if played_card['name'] != "unknown":
                                            middle_role_played = True
                                            break
                                    if middle_role_played:
                                        break
                                if middle_role_played:
                                    break

                        # 根据middle4548是否出过牌调整延时
                        if card['name'] in ['confident', 'puppy_eye']:
                            time.sleep(0.5)
                        elif middle_role_played:
                            print("[INFO] middle角色已出牌，延时3秒")
                            time.sleep(3)
                        else:
                            time.sleep(0.5)

                        pyautogui.moveTo(*target)
                        if not image('bless', click_times=0):
                            pyautogui.click()
                            image("background", threshold=0.65)
                        else:
                            print(f"[WARN] 找到祝福，出牌結束")
                            return hand_cards, energy

                if card['energy'] > 0:
                    energy = max(0, energy - card['energy'])
                    print(f"[INFO] 使用后剩余能量: {energy}")

                # 特殊卡检测逻辑
                if card['name'] in ['confident', 'puppy_eye', 'little_branch', 'shiba']:
                    print(f"[INFO] 检测 {card['name']} 使用后的能量值...")
                    hand_cards, energy, fury, zeal_handled = play_fury(hand_cards, energy, axie_info)

                    # 如果play_fury后能量增加，重新检查是否有足够能量打出ronin
                    if has_ronin and energy >= 1:
                        print(f"[INFO] 能量充足（{energy}），可以打出ronin")
                    else:
                        print(f"[INFO] 能量不足（{energy}），无法打出ronin")
                        has_ronin = False
                        ronin_card = None

                elif card['name'] == 'hero':
                    print("[INFO] 检测 hero 使用后的手牌数量...")
                    hand_cards, energy = play_hero(hand_cards, used_cards, axie_info, energy)

            # 最后，如果还有ronin且有足够能量，打出ronin
            if has_ronin and energy >= 1 and ronin_card:
                print(f"[ACTION] 最后使用 ronin（1 能量）")
                print(f"[ACTION] 按下快捷键 {ronin_card['hotkey']} 使用ronin")
                pyautogui.press(str(ronin_card['hotkey']))
                used_cards += 1
                energy = max(0, energy - 1)
                print(f"[INFO] 使用ronin后剩余能量: {energy}")

            if zeal_cards and not zeal_handled:
                print(f"[INFO] 开始处理 {len(zeal_cards)} 张zeal卡")
                play_zeal(zeal_cards)
                zeal_handled = True

            # 检查是否有需要保留的卡片
            time.sleep(2)
            _, current_fragment = get_energy_info()
            if current_fragment > 0:
                print(f"[INFO] 当前碎片数量: {current_fragment}，尝试保留优先卡片")
                keep_card(current_fragment)
            else:
                print("[INFO] 当前碎片为0，跳过保留卡片")

            print("[INFO] 出牌结束")
            pyautogui.press("E")
            # 如果本轮打出过confident或little_branch，点击end后调用send_cosmetic
            if fury:
                send_cosmetic()
                # for _ in range(random.randint(1, 3)):
                #     send_cosmetic()
                #     time.sleep(random.randint(2, 6))

    else:
        print("[WARN] 手牌检测失败，跳过后续处理")

    return hand_cards, energy

def play_fury(hand_cards, energy, axie_info):
    print(f"[INFO] 检测能量变化...")
    time.sleep(1)
    new_energy, _ = get_energy_info()
    fury = False  # 新增fury触发标记
    zeal_handled = False  # 新增zeal处理标记
    
    if new_energy > energy:  # 如果能量增加了
        print(f"[INFO] 能量值增加: {energy} -> {new_energy}")
        energy = new_energy
        fury = True  # 标记fury已触发

        # 重新检测手牌（使用彩色检测）
        print("[INFO] 检测能量变化后的手牌信息...")
        hand_cards = detect_cards()
        if not hand_cards:  # 如果检测失败，返回原始值
            print("[WARN] 手牌检测失败，跳过后续处理")
            return hand_cards, energy, fury, zeal_handled

        all_cards = select_target(hand_cards, axie_info)
        used_cards = 0  # 添加used_cards变量来跟踪已使用的卡片数量

        # 收集所有zeal卡
        zeal_cards = [card for card in all_cards if card['name'] == 'zeal']

        # 根据card_priority排序
        sorted_cards = sorted(all_cards,
                            key=lambda c: card_priority.index(c['name']) if c['name'] in card_priority else len(card_priority)
                            )

        # 检查是否有ronin卡
        has_ronin = any(card['name'] == 'ronin' for card in sorted_cards)
        ronin_card = next((card for card in sorted_cards if card['name'] == 'ronin'), None)

        # 如果有ronin，先从sorted_cards中移除它
        if has_ronin:
            sorted_cards = [card for card in sorted_cards if card['name'] != 'ronin']

        # 处理所有非zeal和非ronin卡片
        for card in sorted_cards:
            # 跳过unknown卡，只计入手牌数量，不尝试打出
            if card['name'] == 'unknown':
                continue

            # 如果有ronin，保留最后一点能量给它
            if has_ronin and energy <= 1:
                print(f"[INFO] 保留能量给ronin，跳过 {card['name']}")
                continue

            # 检查能量是否足够
            if card['energy'] > energy:
                print(f"[WARN] 能量不足，跳过 {card['name']}（需要 {card['energy']}，剩余 {energy}）")
                continue

            # 根据卡牌名称执行不同的出牌策略
            if card['name'] == 'innocent_lamb':
                print(f"[ACTION] 使用 {card['name']}（0 能量）")
                play_innocent_lamb(card)
                used_cards += 1  # 增加innocent_lamb的计数

                # 检查是否有shiba或little_branch卡
                has_2energy_cards = any(
                    card['name'] in ['shiba', 'little_branch'] 
                    for role, positions in hand_cards.items() 
                    for pos in positions 
                    for card in pos['cards']
                )
                
                if not has_2energy_cards and zeal_cards:
                    print("[INFO] 检测到zeal卡，且没有shiba和little_branch，在innocent_lamb后立即使用")
                    used_zeal = zeal_cards[0]  # 记录使用的zeal卡
                    play_zeal([used_zeal])  # 只使用一张zeal
                    # 从zeal_cards中移除已使用的卡
                    zeal_cards = zeal_cards[1:]
                    # 从sorted_cards中也移除已使用的zeal卡
                    sorted_cards = [c for c in sorted_cards if c != used_zeal]
                continue

            # 如果是zeal卡，跳过（因为可能已经在innocent_lamb后处理过）
            if card['name'] == 'zeal':
                continue

            # 普通卡牌出牌逻辑
            print(f"[ACTION] 使用 {card['name']}（{card['energy']} 能量）")
            print(f"[ACTION] 按下快捷键 {card['hotkey']} 使用{card['name']}")
            pyautogui.press(str(card['hotkey']))
            used_cards += 1  # 记录使用的非zeal卡数量

            # 如果卡牌需要选择目标
            if card.get('target') and card.get('target_candidates'):
                target = card['target_pos']
                if target:
                    # 获取目标位置的名称（例如：A1, B2等）
                    pos_name = next((name for name, info in axie_info['all'].items() if info['axie_coords'] == target),
                                "未知位置")
                    # 确定目标是敌方还是我方
                    side = "敌方" if pos_name.startswith(('C', 'D')) else "我方"
                    # 确定是前中后排
                    for row_name, positions in (axie_info['enemy' if side == "敌方" else 'ally']).items():
                        if pos_name in positions:
                            row = row_name
                            break
                    else:
                        row = "未知排"
                    print(f"[ACTION] 选择目标位置: {side}{row}（{pos_name}）")

                    # 检查middle4548是否出过牌
                    middle_role_played = False
                    for role, positions in hand_cards.items():
                        if role == MIDDLE_ROLE:
                            for pos in positions:
                                for played_card in pos['cards']:
                                    if played_card['name'] != "unknown":
                                        middle_role_played = True
                                        break
                                    if middle_role_played:
                                        break
                                if middle_role_played:
                                    break

                    # 根据middle4548是否出过牌调整延时
                    if card['name'] in ['confident', 'puppy_eye']:
                        time.sleep(0.5)
                    elif middle_role_played:
                        print("[INFO] middle角色已出牌，延时3秒")
                        time.sleep(3)
                    else:
                        time.sleep(0.5)

                    pyautogui.moveTo(*target)
                    if not image('bless', click_times=0):
                        pyautogui.click()
                        image("background", threshold=0.65)
                    else:
                        print(f"[WARN] 找到祝福，出牌結束")
                        return hand_cards, energy, fury, zeal_handled

            if card['energy'] > 0:
                energy = max(0, energy - card['energy'])
                print(f"[INFO] 使用后剩余能量: {energy}")

            # 特殊卡检测逻辑
            if card['name'] in ['confident', 'puppy_eye', 'little_branch', 'shiba']:
                print(f"[INFO] 检测 {card['name']} 使用后的能量值...")
                hand_cards, energy, fury, zeal_handled = play_fury(hand_cards, energy, axie_info)

                # 如果play_fury后能量增加，重新检查是否有足够能量打出ronin
                if has_ronin and energy >= 1:
                    print(f"[INFO] 能量充足（{energy}），可以打出ronin")
                else:
                    print(f"[INFO] 能量不足（{energy}），无法打出ronin")
                    has_ronin = False
                    ronin_card = None

            elif card['name'] == 'hero':
                print("[INFO] 检测 hero 使用后的手牌数量...")
                hand_cards, energy = play_hero(hand_cards, used_cards, axie_info, energy)

        # 处理所有zeal卡
        if zeal_cards:
            print(f"[INFO] 开始处理 {len(zeal_cards)} 张zeal卡")
            play_zeal(zeal_cards)
            zeal_handled = True  # 标记已处理zeal卡
 
    return hand_cards, energy, fury, zeal_handled

def play_cards(axie_info, hand_cards, energy):
    icon_result = loading(['icon'], click_times=0, threshold=0.95, timeout=5, return_all_positions=True)
    if icon_result is None:
        print("[ERROR] 未找到icon图片，无法定位手牌区域")
        return {}
    used_cards = 0  # 记录已使用的卡片数量（不包括zeal卡）
    fury = False  # 标记本轮是否打出过confident或little_branch
    zeal_handled = False  # 标记是否已处理过zeal卡

    # 检查A2血量和cattail卡
    a2_health = axie_info['all'].get('A2', {}).get('health', 100)
    has_cattail = any(
        card['name'] == 'cattail'
        for role, positions in hand_cards.items()
        for pos in positions
        for card in pos['cards']
    )

    # 获取处理过的卡牌列表（包含目标信息）
    all_cards = select_target(hand_cards, axie_info)

    # 收集所有zeal卡
    zeal_cards = [card for card in all_cards if card['name'] == 'zeal']
 
    if a2_health < 70 and has_cattail:
        print(f"[INFO] A2血量低（当前{a2_health}%），且有cattail卡，优先使用cattail")
        cattail_cards = [card for card in all_cards if card['name'] == 'cattail']
        if cattail_cards:
            cattail = cattail_cards[0]
            print(f"[ACTION] A2血量低，优先使用 {cattail['name']}（{cattail['energy']} 能量）")
            print(f"[ACTION] 按下快捷键 {cattail['hotkey']} 使用{cattail['name']}")
            pyautogui.press(str(cattail['hotkey']))
            if cattail.get('target') and cattail.get('target_candidates'):
                target = cattail['target_pos']
                if target:
                    time.sleep(3)
                    pyautogui.moveTo(*target)
                    if not image('bless', click_times=0):
                        pyautogui.click()
                        image("background", threshold=0.65)
                    else:
                        print(f"[WARN] 找到祝福，出牌結束")
                        return

            if cattail['energy'] > 0:
                energy = max(0, energy - cattail['energy'])
                print(f"[INFO] 使用后剩余能量: {energy}")

            # 从all_cards中移除已使用的cattail
            all_cards = [card for card in all_cards if card['name'] != 'cattail']

    # 根据card_priority排序
    sorted_cards = sorted(all_cards,
                          key=lambda c: card_priority.index(c['name']) if c['name'] in card_priority else len(card_priority)
                          )

    # 检查是否有ronin卡
    has_ronin = any(card['name'] == 'ronin' for card in sorted_cards)
    ronin_card = next((card for card in sorted_cards if card['name'] == 'ronin'), None)

    # 如果有ronin，先从sorted_cards中移除它
    if has_ronin:
        sorted_cards = [card for card in sorted_cards if card['name'] != 'ronin']

    # 处理所有非zeal和非ronin卡片
    for card in sorted_cards:
        # 跳过unknown卡，只计入手牌数量，不尝试打出
        if card['name'] == 'unknown':
            continue

        # 如果有ronin，保留最后一点能量给它
        if has_ronin and energy <= 1:
            print(f"[INFO] 保留能量给ronin，跳过 {card['name']}")
            continue

        # 检查能量是否足够
        if card['energy'] > energy:
            print(f"[WARN] 能量不足，跳过 {card['name']}（需要 {card['energy']}，剩余 {energy}）")
            continue

        # 根据卡牌名称执行不同的出牌策略
        if card['name'] == 'innocent_lamb':
            print(f"[ACTION] 使用 {card['name']}（0 能量）")
            play_innocent_lamb(card)
            used_cards += 1  # 增加innocent_lamb的计数

            # 检查是否有shiba或little_branch卡
            has_2energy_cards = any(
                card['name'] in ['shiba', 'little_branch'] 
                for role, positions in hand_cards.items() 
                for pos in positions 
                for card in pos['cards']
            )
            
            if not has_2energy_cards and zeal_cards:
                print("[INFO] 检测到zeal卡，且没有shiba和little_branch，在innocent_lamb后立即使用")
                used_zeal = zeal_cards[0]  # 记录使用的zeal卡
                play_zeal([used_zeal])  # 只使用一张zeal
                # 从zeal_cards中移除已使用的卡
                zeal_cards = zeal_cards[1:]
                # 从sorted_cards中也移除已使用的zeal卡
                sorted_cards = [c for c in sorted_cards if c != used_zeal]
            continue

        # 如果是zeal卡，跳过（因为可能已经在innocent_lamb后处理过）
        if card['name'] == 'zeal':
            continue

        # 普通卡牌出牌逻辑
        print(f"[ACTION] 使用 {card['name']}（{card['energy']} 能量）")
        print(f"[ACTION] 按下快捷键 {card['hotkey']} 使用{card['name']}")
        pyautogui.press(str(card['hotkey']))
        used_cards += 1  # 记录使用的非zeal卡数量

        # 如果卡牌需要选择目标
        if card.get('target') and card.get('target_candidates'):
            target = card['target_pos']
            if target:
                # 获取目标位置的名称（例如：A1, B2等）
                pos_name = next((name for name, info in axie_info['all'].items() if info['axie_coords'] == target),
                                "未知位置")
                # 确定目标是敌方还是我方
                side = "敌方" if pos_name.startswith(('C', 'D')) else "我方"
                # 确定是前中后排
                for row_name, positions in (axie_info['enemy' if side == "敌方" else 'ally']).items():
                    if pos_name in positions:
                        row = row_name
                        break
                else:
                    row = "未知排"
                print(f"[ACTION] 选择目标位置: {side}{row}（{pos_name}）")

                # 检查middle4548是否出过牌
                middle_role_played = False
                for role, positions in hand_cards.items():
                    if role == MIDDLE_ROLE:
                        for pos in positions:
                            for played_card in pos['cards']:
                                if played_card['name'] != "unknown":
                                    middle_role_played = True
                                    break
                                if middle_role_played:
                                    break
                            if middle_role_played:
                                break

                # 根据middle4548是否出过牌调整延时
                if card['name'] in ['confident', 'puppy_eye']:
                    time.sleep(0.5)
                elif middle_role_played:
                    print("[INFO] middle角色已出牌，延时3秒")
                    time.sleep(3)
                else:
                    time.sleep(0.5)

                pyautogui.moveTo(*target)
                if not image('bless', click_times=0):
                    pyautogui.click()
                    image("background", threshold=0.65)
                else:
                    print(f"[WARN] 找到祝福，出牌結束")
                    return

        if card['energy'] > 0:
            energy = max(0, energy - card['energy'])
            print(f"[INFO] 使用后剩余能量: {energy}")

        # 特殊卡检测逻辑
        if card['name'] in ['confident', 'puppy_eye', 'little_branch', 'shiba']:
            print(f"[INFO] 检测 {card['name']} 使用后的能量值...")
            hand_cards, energy, fury, zeal_handled = play_fury(hand_cards, energy, axie_info)

            # 如果play_fury后能量增加，重新检查是否有足够能量打出ronin
            if has_ronin and energy >= 1:
                print(f"[INFO] 能量充足（{energy}），可以打出ronin")
            else:
                print(f"[INFO] 能量不足（{energy}），无法打出ronin")
                has_ronin = False
                ronin_card = None

        elif card['name'] == 'hero':
            print("[INFO] 检测 hero 使用后的手牌数量...")
            hand_cards, energy = play_hero(hand_cards, used_cards, axie_info, energy)

    # 最后，如果还有ronin且有足够能量，打出ronin
    if has_ronin and energy >= 1 and ronin_card:
        print(f"[ACTION] 最后使用 ronin（1 能量）")
        print(f"[ACTION] 按下快捷键 {ronin_card['hotkey']} 使用ronin")
        pyautogui.press(str(ronin_card['hotkey']))
        used_cards += 1

        if ronin_card.get('target') and ronin_card.get('target_candidates'):
            target = ronin_card['target_pos']
            if target:
                # 获取目标位置的名称（例如：A1, B2等）
                pos_name = next((name for name, info in axie_info['all'].items() if info['axie_coords'] == target),
                                "未知位置")
                # 确定目标是敌方还是我方
                side = "敌方" if pos_name.startswith(('C', 'D')) else "我方"
                # 确定是前中后排
                for row_name, positions in (axie_info['enemy' if side == "敌方" else 'ally']).items():
                    if pos_name in positions:
                        row = row_name
                        break
                else:
                    row = "未知排"
                print(f"[ACTION] 选择目标位置: {side}{row}（{pos_name}）")

                # 检查middle4548是否出过牌
                middle_role_played = False
                for role, positions in hand_cards.items():
                    if role == MIDDLE_ROLE:
                        for pos in positions:
                            for played_card in pos['cards']:
                                if played_card['name'] != "unknown":
                                    middle_role_played = True
                                    break
                                if middle_role_played:
                                    break
                            if middle_role_played:
                                break

                # 根据middle4548是否出过牌调整延时
                if ronin_card['name'] in ['confident', 'puppy_eye']:
                    time.sleep(0.5)
                elif middle_role_played:
                    print("[INFO] middle角色已出牌，延时3秒")
                    time.sleep(3)
                else:
                    time.sleep(0.5)

                pyautogui.moveTo(*target)
                if not image('bless', click_times=0):
                    pyautogui.click()
                    image("background", threshold=0.65)
                else:
                    print(f"[WARN] 找到祝福，出牌結束")
                    return

        energy = max(0, energy - 1)
        print(f"[INFO] 使用ronin后剩余能量: {energy}")

    # 检查并处理zeal卡
    if zeal_cards and not zeal_handled:
        print(f"[INFO] ronin使用后，开始处理 {len(zeal_cards)} 张zeal卡")
        play_zeal(zeal_cards)
        zeal_handled = True         

        # 检查是否有需要保留的卡片
    time.sleep(2)
    _, current_fragment = get_energy_info()
    if current_fragment > 0:
        print(f"[INFO] 当前碎片数量: {current_fragment}，尝试保留优先卡片")
        keep_card(current_fragment)
    else:
        print("[INFO] 当前碎片为0，跳过保留卡片")

    print("[INFO] 出牌结束")
    pyautogui.press("E")
        # 如果本轮打出过confident或little_branch，点击end后调用send_cosmetic
    if fury:
        send_cosmetic()
        # for _ in range(random.randint(1, 3)):
        #     send_cosmetic()
        #     time.sleep(random.randint(2, 6))


def in_game():
    return image('origins', offset=(100, 0), gray_diff_threshold=12) is not None


def enter_game():
    if image("error"):
        close_game()
        time.sleep(60)
    if not in_game():
        print("当前不在游戏中。")
        subprocess.Popen(exe_path)
        loading(['play', 'x_origin'], check_interval=3, threshold=0.75, color=False)


def close_game():
    try:
        # 检查进程是否存在
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AxieInfinity-Origins.exe"],
                                capture_output=True, text=True, shell=True)
        if "AxieInfinity-Origins.exe" in result.stdout:
            print("正在关闭游戏进程...")
            subprocess.run(["taskkill", "/f", "/im", "AxieInfinity-Origins.exe"], shell=True)
            print("游戏进程已关闭")
        else:
            print("游戏进程未运行")
        time.sleep(10)
    except Exception as e:
        print(f"关闭游戏时发生错误: {str(e)}")
        time.sleep(10)


def in_rank_mode():
    return image('rank_mode') is not None


def enter_battle(choice=CHOICE):      
    if not in_rank_mode():
        print("当前不在排位賽中。")
        image('x_origin', threshold=0.75)
        if image('menu'):
            image('surrender')
            image('confirm_surrender', click_times=5)
            image('back'), time.sleep(5)

        if image('next'):
            loading(['x_origin'], check_interval=0.1, timeout=3, threshold=0.75, color=False, click_times=3)
            loading([choice])
        if image('ranked'):
            loading([choice])
        if image('play'):
            time.sleep(2)
            image('ranked')
            loading([choice])
    else:
        print("当前已经在战斗中。")


def surrender(n, rank_level='bear'):
    """投降n次"""
    for i in range(n):
        # 检查当前时间是否在10:30到13:00之间
        current_time = datetime.now().time()
        start_time = datetime.strptime('10:58', '%H:%M').time()
        end_time = datetime.strptime('13:00', '%H:%M').time()
        
        if start_time <= current_time <= end_time:
            print("[INFO] 当前时间在10:58到13:00之间，跳过投降")
            return
            
        if image("error"):
            close_game()
            enter_game()
        print(f"第 {i + 1} 次 surrender")  # 显示当前第几次，而不是总次数 n
        enter_game()
        image('tap', color=False)
        enter_battle()  # 使用默认的CHOICE

        loading(['menu'], check_interval=3, click_times=0, timeout=60)
        time.sleep(3)

        if image(rank_level, threshold=0.9):
            print(f"[INFO] 找到{rank_level}，开始战斗")
            print(f"[INFO] surrender结束")
            fight()          
            break  # 找到tiger后跳出循环
        else:
            print(f"[INFO] 未找到{rank_level}，投降")
            image('menu')
            image('surrender')
            image('confirm_surrender')

            loading(['tap'], check_interval=3, click_times=0, timeout=10, color=False)
            time.sleep(3)
            image('tap', color=False)


def fight():
    count = 0  # 记录战斗总次数
    victory_count = 0  # 记录胜利次数
    defeat_count = 0  # 记录失败次数
    last_result = None  # 记录最后一次战斗的结果
    in_battle = False  # 标记是否在同一场战斗中

    print("[INFO] 进入fight函数...")
    # 检查当前时间是否在10:30到13:00之间，用于设置n值
    current_time = datetime.now().time()
    start_time = datetime.strptime('10:58', '%H:%M').time()
    end_time = datetime.strptime('13:00', '%H:%M').time()
    
    # 根据时间范围设置不同的n值
    if start_time <= current_time <= end_time:
        n = 32
        print("[INFO] 当前时间在10:30到13:00之间，设置戰鬥次数为32次")
    else:
        n = 7
        print("[INFO] 当前时间不在10:58到13:00之间，设置戰鬥次数为7次")
    

    while count < n:
        try:
            if not in_battle:
                print(f"[INFO] 准备进入第 {count + 1}/{n} 场战斗...")
                enter_game()
                enter_battle()  # 使用默认的CHOICE
                in_battle = True

            # 等待 'end' 或 'tap' 图像加载，超时后进行胜负判断
            print("[INFO] 等待出牌...")
            found_image = loading(['end', 'tap'], check_interval=1, click_times=0, timeout=45, color=False)
            print(f"[INFO] 检测到图像: {found_image}")

            if found_image == 'tap':
                time.sleep(1)
                # 检查是否胜利或失败
                print("[INFO] 检查胜负状态...")
                defeat = loading(['defeat'], check_interval=0.1, click_times=0, threshold=0.99, timeout=1)
                victory = loading(['victory'], check_interval=0.1, click_times=0, threshold=0.99, timeout=1)

                if victory:
                    image("tap", color=False)
                    print("[INFO] 胜利！")
                    victory_count += 1
                    last_result = 'victory'
                elif defeat:
                    image("tap", color=False)
                    print("[INFO] 失败！")
                    defeat_count += 1
                    last_result = 'defeat'
                else:
                    print("[WARN] 未检测到战斗结果，记为失败")
                    defeat_count += 1
                    last_result = 'defeat'

                count += 1  # 战斗结束，总场次+1
                in_battle = False  # 重置战斗状态
                print(f"[INFO] 第 {count}/{n} 场战斗结束 | 胜利: {victory_count} 失败: {defeat_count}")
                continue  # 开始下一场战斗

            elif found_image == 'end':
                time.sleep(1)
                if image('turn_0', threshold=0.96):
                    time.sleep(8)
                print("[INFO] 读取axie站位信息...")
                axie_info = get_axie_info()

                # 如果检测到A2阵亡，等待投降结果
                if axie_info == 'GAME_OVER':
                    print("[INFO] 检测到A2阵亡，等待投降结果...")
                    time.sleep(5)  # 等待投降动画
                    continue  # 继续检查战斗结果

                print("[ACTION] 读取手牌信息...")
                hand_cards = detect_cards(color=False)

                print("[ACTION] 读取能量...")
                energy, _ = get_energy_info()  # 解包元组，只取energy值

                print("[ACTION] 开始出牌...")
                play_cards(axie_info, hand_cards, energy)

                time.sleep(3)  # 等待出牌动画
                continue  # 继续检查战斗结果

            else:
                # 超时，记为失败
                print("[ERROR] 等待超时，记为失败")
                defeat_count += 1
                last_result = 'defeat'
                count += 1
                in_battle = False  # 重置战斗状态
                print(f"[INFO] 第 {count}/{n} 场战斗超时 | 胜利: {victory_count} 失败: {defeat_count}")
                continue  # 开始下一场战斗

        except Exception as e:
            print(f"[ERROR] fight函数发生错误: {str(e)}")
            # 发生错误时不增加计数，继续尝试当前场次
            continue

    print("[INFO] fight循环结束")
    print(f"[INFO] 最终战绩 - 总场次: {count} | 胜利: {victory_count} | 失败: {defeat_count}")
    return last_result if last_result else 'defeat'


def send_cosmetic():
    image('cosmetic')
    # 找到icon坐标
    icon_pos = image('icon', click_times=0, threshold=0.95)
    if not icon_pos:
        print('[ERROR] 未找到icon')
        return
    icon_x, icon_y = icon_pos
    # 计算第一个点坐标
    start_x = icon_x - 540
    start_y = icon_y + 80
    # 4行3列
    rows, cols = 4, 3
    row_gap, col_gap = 150, 145
    # 随机选择一个点
    row = random.randint(0, rows - 1)
    col = random.randint(0, cols - 1)
    click_x = start_x + col * col_gap
    click_y = start_y + row * row_gap
    print(f'[ACTION] 点击第{row + 1}行,第{col + 1}列, 坐标({click_x},{click_y})')
    pyautogui.click(click_x, click_y)



if __name__ == "__main__":
    # surrender(40, 'tiger')
    fight()
    print("[INFO] 程序执行完毕")
    close_game()
















