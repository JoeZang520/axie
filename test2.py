import cv2
import pyautogui
import numpy as np
import os
import time
import random
import subprocess
from axie_cards import (
    axie_cards, card_priority, card_to_detect, thresholds,exe_path
)

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
            time.sleep(0.5)
        print(f"[ACTION] 点击 {png}")

    return (center_x, center_y)



def image_multi(png_list, thresholds=thresholds, region=None, min_x_distance=60, color=True):
    if isinstance(png_list, str):
        png_list = [png_list]

    if not thresholds:
        raise ValueError("阈值字典 (thresholds) 必须提供")

    region = region or (0, 0, *pyautogui.size())
    x1, y1, x2, y2 = region

    screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
    screen_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)  # 转换为BGR彩色图

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
                center_x = pt[0] + template.shape[1] // 2 + x1
                center_y = pt[1] + template.shape[0] // 2 + y1
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


def loading(image_names, check_interval: float = 1, threshold=0.8, click_times=1, timeout=50, return_all_positions=False, color=True):
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
    x1 = icon_x - 420  # 左上角x坐标
    y1 = icon_y + 660  # 左上角y坐标
    x2 = icon_x + 730  # 右下角x坐标
    y2 = icon_y + 870  # 右下角y坐标
    
    # 定义搜索区域
    search_region = (x1, y1, x2, y2)
    
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

        matched_cards = set()
        role_cards_info = []

        for idx, (x, y, _) in enumerate(sorted_points, start=1):
            # 移动鼠标到卡片位置
            pyautogui.moveTo(x, y)
            time.sleep(0.1)

            matched_this_axie = []

            for card in card_list:
                name, energy, target, target_side, target_row = card

                if name in matched_cards:
                    continue

                x1 = int(x) - 100
                y1 = int(y) - 400
                x2 = x1 + 300
                y2 = y1 + 400
                region = (x1, y1, x2, y2)

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
                    matched_cards.add(name)

            if matched_this_axie:
                for card in matched_this_axie:
                    print(f"{role} 第 {card_slot_index} 张卡: {card['name']}")
            else:
                print(f"{role} 第 {card_slot_index} 张卡：无牌")

            role_cards_info.append({
                "slot_index": card_slot_index,
                "cards": matched_this_axie or [{"name": "unknown", "energy": 0, "target": None, "target_side": None, "target_row": None}]  # 如果没有匹配到具体卡牌，也添加一个占位卡牌
            })

            card_slot_index += 1
            # 鼠标移动到卡片外
            pyautogui.moveRel(0, -500)

        result[role] = role_cards_info

    return result


def get_energy_info(timeout=3):  # 默认3秒超时
    check_interval = 0.1  # 检查间隔
    start_time = time.time()
    energy_value = 3  # 默认能量为3
    fragment_value = 0

    # 等待icon图片出现
    icon_result = loading(['icon'], click_times=0, timeout=5, return_all_positions=True)
    if icon_result is None:
        print("[ERROR] 未找到icon图片，无法定位能量和碎片区域")
        return energy_value, fragment_value
    else:
        pyautogui.moveRel(0, 0)

    icon_x, icon_y = icon_result['icon']  # 从字典中获取icon的坐标
    # 计算搜索区域的左上角和右下角坐标
    x1 = icon_x - 620  # 左上角x坐标
    y1 = icon_y + 540  # 左上角y坐标
    x2 = icon_x - 460  # 右下角x坐标
    y2 = icon_y + 730  # 右下角y坐标
    
    # 定义搜索区域
    search_region = (x1, y1, x2, y2)

    while time.time() - start_time < timeout:
        # 优化能量检测：从高到低检查，找到就立即返回
        for i in range(4, -1, -1):  # 从4到0检查
            # 对不同能量值使用不同的匹配参数
            if i == 0:
                # 0能量使用灰度图匹配
                energy_pos = image(f"energy_{i}", threshold=0.9, click_times=0, region=search_region, color=False)
            else:
                # 其他能量值使用彩色匹配
                energy_pos = image(f"energy_{i}", threshold=0.8, click_times=0, region=search_region, color=True, gray_diff_threshold=12)
            
            if energy_pos:
                energy_value = i
                # 找到能量后立即检查碎片
                for j in range(12):
                    fragment_pos = image(f"fragment_{j}", threshold=0.95, click_times=0, gray_diff_threshold=12, region=search_region)
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
    icon_result = loading(['icon'], click_times=0, timeout=5, return_all_positions=True)
    if icon_result is None:
        print("[ERROR] 未找到icon图片，无法定位手牌区域")
        return {}
    else:
        pyautogui.moveRel(0, 0)

    icon_x, icon_y = icon_result['icon']  # 从字典中获取icon的坐标

    # 4排每排起点坐标，基于icon点偏移确定（需你测量替换）
    row_starts = {
        'A': (icon_x - 350, icon_y + 450),
        'B': (icon_x - 430, icon_y + 560),
        'C': (icon_x + 390, icon_y + 450),
        'D': (icon_x + 290, icon_y + 560)
    }

    x_spacing = 200  # 横向间距，单位像素
    all_positions = {}

    for row_letter, (start_x, start_y) in row_starts.items():
        for i in range(3):
            x = start_x + i * x_spacing
            y = start_y
            all_positions[f"{row_letter}{i + 1}"] = (x, y)

    # print("[INFO] 计算得到12个位置的站位坐标：", all_positions)
    return all_positions


def get_axie_info():
    all_positions = get_all_positions()
    axie_positions = {}

    for pos_name, (x, y) in all_positions.items():
        region = (x - 100, y - 100, x + 100, y + 100)
        template_name = pos_name.lower()
        match_pos = image(template_name, threshold=0.8, click_times=0, region=region, color=True)

        if match_pos is None:
            axie_positions[pos_name] = (x, y)

    # 阵营划分
    team_ally = {k: v for k, v in axie_positions.items() if k.startswith(('A', 'B'))}
    team_enemy = {k: v for k, v in axie_positions.items() if k.startswith(('C', 'D'))}

    # 排位分类函数
    def classify_rows(team_dict, reverse_x=True):
        sorted_items = sorted(team_dict.items(), key=lambda item: item[1][0], reverse=reverse_x)
        result = {'前排': [], '中排': [], '后排': []}
        n = len(sorted_items)

        if n == 1:
            result['前排'].append(sorted_items[0][0])
        elif n == 2:
            result['前排'].append(sorted_items[0][0])
            result['后排'].append(sorted_items[1][0])
        elif n == 3:
            result['前排'].append(sorted_items[0][0])
            result['中排'].append(sorted_items[1][0])
            result['后排'].append(sorted_items[2][0])
        else:
            part = n // 3
            for i, (pos_name, _) in enumerate(sorted_items):
                if i < part:
                    result['前排'].append(pos_name)
                elif i < 2 * part:
                    result['中排'].append(pos_name)
                else:
                    result['后排'].append(pos_name)
        return result

    ally_rows = classify_rows(team_ally, reverse_x=True)
    enemy_rows = classify_rows(team_enemy, reverse_x=False)

    # 最终结构，加入 all: 所有坐标
    axie_info = {
        'ally': ally_rows,
        'enemy': enemy_rows,
        'all': {}  # 新增：每个位置对应的坐标
    }

    for pos_name, coords in axie_positions.items():
        axie_info['all'][pos_name] = {'coords': coords}

    # 打印验证
    print("\n=== AXIE 阵型信息 ===")
    for side, side_name in [('ally', '我方'), ('enemy', '敌方')]:
        print(f"【{side_name}】")
        for row in ['前排', '中排', '后排']:
            positions = axie_info[side][row]
            if positions:  # 只打印有单位的排
                print(f"{row}: {', '.join(positions)}")

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

                    if target_side == 'enemy' and target_row == 'front_back':
                        targets = (
                            axie_info['enemy'].get('前排', []) +
                            axie_info['enemy'].get('中排', []) +
                            axie_info['enemy'].get('后排', [])
                        )
                    elif target_side == 'ally' and target_row == 'all':
                        # 对confident卡特殊处理,优先选择中排
                        if card['name'] == 'confident':
                            targets = (
                                axie_info['ally'].get('中排', []) +
                                axie_info['ally'].get('前排', []) +
                                axie_info['ally'].get('后排', [])
                            )
                        else:
                            targets = (
                                axie_info['ally'].get('前排', []) +
                                axie_info['ally'].get('中排', []) +
                                axie_info['ally'].get('后排', [])
                            )
                    else:
                        targets = []

                    card['target_candidates'] = []
                    for pos_name in targets:
                        coords = axie_info['all'].get(pos_name, {}).get('coords')
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
    priority_cards = ['mini_little_branch', 'mini_puppy_ear', 'mini_hero', 'mini_confident']
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
    # 在点击keep之前获取碎片数量
    _, current_fragment = get_energy_info()
    print(f"[INFO] 当前碎片数量: {current_fragment}，需要消耗: {fragment_cost}")
    
    # 检查是否有足够的碎片
    if current_fragment < fragment_cost:
        print(f"[WARN] 碎片不足，无法保留卡片（需要 {fragment_cost} 碎片，当前 {current_fragment} 碎片）")
        return False

    # 点击保留按钮并设置搜索区域
    keep_pos = image('keep')
    if keep_pos:
        # 移动到keep按钮下方100像素的位置
        keep_x, keep_y = keep_pos
        print(f"[DEBUG] keep_x: {keep_x}, keep_y: {keep_y}")
        pyautogui.moveTo(keep_x, keep_y + 100)
        time.sleep(1)  # 等待动画效果

        # 设置搜索区域，以keep按钮位置为基准
        # 计算搜索区域的左上角坐标和宽高
        x1 = keep_x  # 左上角x坐标
        y1 = keep_y - 680  # 左上角y坐标（向上偏移）
        x2 = keep_x + 1150 # 向右搜索1150像素
        y2 = keep_y  
        
        # 搜索区域：(左上角x, 左上角y, 宽度, 高度)
        search_region = (x1, y1, x2, y2)
        print(f"[DEBUG] 搜索区域: 左上({x1}, {y1}), 右下({x2}, {y2})")

        # 遍历所有优先保留的卡片
        keep_priority_cards = ['little_branch', 'zeal', 'puppy_ear', 'hero']
        found_count = 0  # 找到的卡片数量
        total_cost = 0  # 总消耗的碎片

        for card_name in keep_priority_cards:
            # 计算下一张卡需要的碎片
            next_cost = found_count + 1
            # 如果总消耗会超过当前碎片，就停止
            if total_cost + next_cost > current_fragment:
                break

            # 构建mini卡片名称
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
            image('cancel')
            pyautogui.moveTo(100, 100)
            print("[INFO] 未找到任何可以保留的卡片")
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
    image('cancel')
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

def play_cards(axie_info, hand_cards, energy):
    used_cards = 0  # 记录已使用的卡片数量（不包括zeal卡）
    fury = False  # 标记本轮是否打出过confident或little_branch

    # 获取处理过的卡牌列表（包含目标信息）
    all_cards = select_target(hand_cards, axie_info)
    
    # 收集所有zeal卡
    zeal_cards = [card for card in all_cards if card['name'] == 'zeal']
    
    # 根据card_priority排序
    sorted_cards = sorted(all_cards, 
        key=lambda c: card_priority.index(c['name']) if c['name'] in card_priority else len(card_priority)
    )

    # 第一轮：按优先级出所有牌
    for card in sorted_cards:
        # 跳过zeal卡，稍后统一处理
        if card['name'] == 'zeal':
            continue

        # 能量检查
        if card['energy'] > energy:
            print(f"[WARN] 能量不足，跳过 {card['name']}（需要 {card['energy']}，剩余 {energy}）")
            continue

        # 根据卡牌名称执行不同的出牌策略
        if card['name'] == 'innocent_lamb':
            print(f"[ACTION] 使用 {card['name']}（0 能量）")
            play_innocent_lamb(card)
            used_cards += 1  # 增加innocent_lamb的计数
            continue

        # 普通卡牌出牌逻辑
        print(f"[ACTION] 使用 {card['name']}（{card['energy']} 能量）")
        print(f"[ACTION] 按下快捷键 {card['hotkey']} 使用{card['name']}")
        pyautogui.press(str(card['hotkey']))
        if card['name'] != 'zeal':
            used_cards += 1  # 记录使用的非zeal卡数量
        
        # 如果卡牌需要选择目标
        if card.get('target') and card.get('target_candidates'):
            target = card['target_pos']
            if target:
                # 获取目标位置的名称（例如：A1, B2等）
                pos_name = next((name for name, info in axie_info['all'].items() if info['coords'] == target), "未知位置")
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
                time.sleep(3)
                pyautogui.moveTo(*target)             
                pyautogui.click()
                image("background", threshold=0.65)

        # 更新能量（只对非0费卡）
        if card['energy'] > 0:
            energy = max(0, energy - card['energy'])

        # 特殊卡检测逻辑
        if card['name'] in ['confident', 'little_branch']:
            
            print(f"[INFO] 检测 {card['name']} 使用后的能量值...")
            new_energy, new_fragment = get_energy_info()
            if new_energy > energy:  # 如果能量增加了
                fury = True
                print(f"[INFO] 能量值增加: {energy} -> {new_energy}")
                energy = new_energy
                
                # 重新检测手牌（使用彩色检测）
                print("[INFO] 检测能量变化后的手牌信息...")
                hand_cards = detect_cards()  # 中途检测不设置延时
                all_cards = select_target(hand_cards, axie_info)
                
                # 按优先级排序所有卡片
                sorted_cards = sorted(all_cards, 
                    key=lambda c: card_priority.index(c['name']) if c['name'] in card_priority else len(card_priority)
                )
                
                # 处理所有卡片
                for new_card in sorted_cards:
                    # 跳过zeal卡，稍后统一处理
                    if new_card['name'] == 'zeal':
                        continue

                    # 跳过unknown卡，只计入手牌数量，不尝试打出
                    if new_card['name'] == 'unknown':
                        continue

                    if new_card['energy'] > energy:
                        print(f"[WARN] 能量不足，跳过 {new_card['name']}（需要 {new_card['energy']}，剩余 {energy}）")
                        continue

                    print(f"[ACTION] 使用卡片 {new_card['name']}（{new_card['energy']} 能量）")
                    print(f"[ACTION] 按下快捷键 {new_card['hotkey']} 使用{new_card['name']}")
                    pyautogui.press(str(new_card['hotkey']))
                    
                    if new_card.get('target') and new_card.get('target_candidates'):
                        target = new_card['target_pos']
                        if target:
                            time.sleep(3)
                            pyautogui.moveTo(*target)                       
                            pyautogui.click()
                            image("background", threshold=0.65)
                    
                    if new_card['energy'] > 0:
                        energy = max(0, energy - new_card['energy'])
                        print(f"[INFO] 使用后剩余能量: {energy}")

        elif card['name'] == 'hero':
            print("[INFO] 检测 hero 使用后的手牌数量...")
            
            # 计算当前理论剩余手牌数量
            total_cards = sum(len(pos['cards']) for positions in hand_cards.values() for pos in positions)
            remaining_cards = total_cards - used_cards
            print(f"[INFO] 总手牌数量: {total_cards}, 已使用: {used_cards}, 理论剩余: {remaining_cards}")
            
            # 快速检测手牌数量（不移动鼠标）
            current_cards = detect_cards(quick_check=True)
            if current_cards and 'total_cards' in current_cards:
                print(f"[INFO] 当前实际手牌数量: {current_cards['total_cards']}")
                
                # 如果实际手牌数量大于理论数量，说明hero增加了手牌
                if current_cards['total_cards'] > remaining_cards:
                    print("[INFO] 手牌数量增加，重新检测手牌信息...")
                    # 重新获取当前能量值
                    energy, _ = get_energy_info()
                    print(f"[INFO] 当前能量: {energy}")
                    
                    hand_cards = detect_cards()  # 中途检测不设置延时
                    if not hand_cards:  # 如果检测失败，跳过后续处理
                        print("[WARN] 手牌检测失败，跳过后续处理")
                        continue
                        
                    all_cards = select_target(hand_cards, axie_info)
                    
                    # 按优先级排序所有卡片
                    sorted_cards = sorted(all_cards, 
                        key=lambda c: card_priority.index(c['name']) if c['name'] in card_priority else len(card_priority)
                    )
                    
                    # 更新zeal卡列表
                    zeal_cards = [card for card in sorted_cards if card['name'] == 'zeal']
                    
                    # 处理所有非zeal卡片
                    for new_card in sorted_cards:
                        # 跳过zeal卡，稍后统一处理
                        if new_card['name'] == 'zeal':
                            continue

                        # 跳过unknown卡，只计入手牌数量，不尝试打出
                        if new_card['name'] == 'unknown':
                            continue

                        if new_card['energy'] > energy:
                            print(f"[WARN] 能量不足，跳过 {new_card['name']}（需要 {new_card['energy']}，剩余 {energy}）")
                            continue

                        print(f"[ACTION] 使用卡片 {new_card['name']}（{new_card['energy']} 能量）")
                        print(f"[ACTION] 按下快捷键 {new_card['hotkey']} 使用{new_card['name']}")
                        pyautogui.press(str(new_card['hotkey']))
                        
                        if new_card['energy'] > 0:
                            energy = max(0, energy - new_card['energy'])
                            print(f"[INFO] 使用后剩余能量: {energy}")
            else:
                print("[WARN] 手牌检测失败，跳过后续处理")

    # 如果有zeal卡，处理zeal卡
    if zeal_cards:
        play_zeal(zeal_cards)

    # 检查是否有需要保留的卡片
    _, current_fragment = get_energy_info()
    if current_fragment == 0:
        print("[INFO] 当前碎片为0，跳过保留卡片")
    else:
        print(f"[INFO] 尝试保留优先卡片")
        keep_card(current_fragment)  

    print("[INFO] 出牌结束")
    pyautogui.press("E")
    # 如果本轮打出过confident或little_branch，点击end后调用send_cosmetic
    if fury:
        for _ in range(random.randint(1, 3)):
            send_cosmetic()
            time.sleep(random.randint(2, 6))
        


def in_game():
    return image('origins', offset=(100, 0), gray_diff_threshold=12) is not None

def enter_game():
    if image("error"):
        close_game()
        time.sleep(60)
    if not in_game():
        print("当前不在游戏中。")
        subprocess.Popen(exe_path)
        loading(['play', 'x_origin'], check_interval=3)

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

def in_battle():
    return image('icon') is not None

def enter_battle(choice):
    time.sleep(1)
    image("x_origin")
    if not in_battle():
        print("当前不在战斗中。")
        if image('next'):
            loading([choice])
        if image('ranked'):
            loading([choice])
        if image('play'):
            time.sleep(2)
            image('ranked')
            loading([choice])
    else:
        print("当前已经在战斗中。")



def surrender(n):
    for i in range(n):
        if image("error"):
            close_game()
        print(f"第 {i + 1} 次 surrender")  # 显示当前第几次，而不是总次数 n
        enter_game()
        image('tap', color=False)
        enter_battle("no_pref")

        loading(['icon'], check_interval=3, timeout=5)
        time.sleep(random.randint(5,15))

        image('menu')
        image('surrender')
        image('confirm_surrender')

        loading(['tap'], check_interval=3, click_times=0, color=False)
        time.sleep(3)
        image('tap', color=False)



def fight(n):
    count = 0  # 记录找到tap的次数
    victory_count = 0  # 记录胜利次数
    defeat_count = 0  # 记录失败次数

    while count < n:
        enter_game()
        enter_battle("go_second")
        
        # 等待 'end' 或 'tap' 图像加载，超时后进行胜负判断
        found_image = loading(['end', 'tap'], check_interval=1, click_times=0, timeout=45, color=False)

        if found_image == 'tap':
            time.sleep(1)
            print("[INFO] 总场次+1")
            count += 1  # 只在找到tap时累加
            # 检查是否胜利或失败

            defeat = loading(['defeat'], check_interval=0.1, click_times=0, threshold=0.99, timeout=1)
            victory = loading(['victory'], check_interval=0.1, click_times=0, threshold=0.99, timeout=1)

            if victory:
                image("tap", color=False)
                print("[INFO] 胜场+1")
                victory_count += 1  # 找到胜利图像时增加胜利次数
            elif defeat:
                image("tap", color=False)
                print("[INFO] 负场+1")
                defeat_count += 1  # 找到失败图像时增加失败次数

            print(f"第 {count} 次 fight | 胜利: {victory_count} 失败: {defeat_count}")  # 打印每次战斗的结果
            continue

        if found_image == 'end':
            print("[INFO] 读取axie站位信息...")
            axie_info = get_axie_info()

            print("[ACTION] 读取手牌信息...")
            hand_cards = detect_cards(color=False)  

            print("[ACTION] 读取能量...")
            energy, _ = get_energy_info()  # 解包元组，只取energy值
            
            print("[ACTION] 开始出牌...")
            play_cards(axie_info, hand_cards, energy)

    print("fight循环结束")
    # 返回最后一次战斗的结果
    if victory_count > defeat_count:
        return 'victory'
    else:
        return 'defeat'

def send_cosmetic():
    image('cosmetic')
    # 找到icon坐标
    icon_pos = image('icon', click_times=0)
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
    print(f'[ACTION] 点击第{row+1}行,第{col+1}列, 坐标({click_x},{click_y})')
    pyautogui.click(click_x, click_y)




surrender(30)  # 直接投降
  









