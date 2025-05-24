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


def get_all_positions():
    """
    通过找到 'icon.png' 参照点，计算12个站位坐标，返回字典。
    需要你根据游戏界面实际偏移值调整offset_x和offset_y。
    """
    icon_pos = image('icon')
    if icon_pos is None:
        print("[ERROR] 未找到icon图片，无法定位站位")
        return {}

    icon_x, icon_y = icon_pos

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
    for side in ['ally', 'enemy']:
        for row in ['前排', '中排', '后排']:
            positions = axie_info[side][row]
            for pos_name in positions:
                coords = axie_info['all'].get(pos_name, {}).get('coords', None)
                if coords is not None and coords != ('未知坐标',):
                    print(f"{pos_name} 坐标: {coords}")

    return axie_info

def play_ronin_card(card, current_energy):
    print(f"[ACTION] 使用 ronin（{card['energy']} 能量） [最后出牌]")
    pyautogui.press(str(card['hotkey']))
    time.sleep(1)
    return current_energy - card['energy']


def play_cottontail_card(card, current_energy, coord_to_name, fragment_value):
    if fragment_value < 8:
        print(f"[INFO] 碎片 {fragment_value} 不足，跳过 cottontail 出牌")
        return current_energy, fragment_value

    print(f"[ACTION] 使用 cottontail（{card['energy']} 能量） → 碎片满足出牌条件，出牌后能量+1")
    pyautogui.press(str(card['hotkey']))
    time.sleep(1)

    if card.get('target'):
        target = card.get('target_pos')
        if target:
            pos_name = coord_to_name.get(target, "未知位置")
            print(f"[ACTION] cottontail 目标坐标 {pos_name} : {target}")
            time.sleep(1)
            pyautogui.moveTo(*target)
            pyautogui.click()
        else:
            print("[WARN] 没有 cottontail 的 target_pos，跳过点击")

    current_energy += 1
    print(f"[INFO] cottontail 出牌后能量 +1，当前能量：{current_energy}")

    return current_energy, fragment_value


def select_target(hand_cards, axie_info, pending_cards=None):
    if pending_cards is not None:
        return pending_cards

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

def play_cards(hand_cards, axie_info, current_energy=None, fragment_value=0, extra_card_flag=False, pending_cards=None):
    if image("error"):
        close_game()
    if current_energy is None:
        current_energy, fragment_value = get_energy_info()

    coord_to_name = {info['coords']: pos_name for pos_name, info in axie_info['all'].items()}
    cards_to_play = select_target(hand_cards, axie_info, pending_cards)

    print(f"[INFO] 当前能量总数: {current_energy}, 当前碎片数量: {fragment_value}")

    ronin_card = next((c for c in cards_to_play if c['name'] == 'ronin' and c['energy'] <= current_energy), None)
    energy_reserved = ronin_card['energy'] if ronin_card else 0

    other_cards = [c for c in cards_to_play if c != ronin_card]
    cards_sorted = sorted(other_cards, key=lambda c: (
        card_priority.index(c['name']) if c['name'] in card_priority else len(card_priority)
    ))

    skipped_cards = []
    predicted_fragment = fragment_value + sum(
        c['energy'] for c in cards_sorted if c['energy'] > 0 and c['name'] not in no_fragment_cards
    )
    need_play_cottontail = predicted_fragment >= 8 and any(c['name'] == 'cottontail' for c in cards_sorted)

    for card in cards_sorted:
        if card['energy'] > current_energy - energy_reserved:
            print(f"[WARN] 能量不足，跳过 {card['name']}（需要 {card['energy']}，剩余 {current_energy}）")
            skipped_cards.append(card)
            continue

        if card['name'] == 'cottontail':
            if need_play_cottontail and fragment_value >= 8:
                current_energy, fragment_value = play_cottontail_card(card, current_energy, coord_to_name, fragment_value)
            else:
                print(f"[INFO] 碎片不足，不出 cottontail，跳过")
                skipped_cards.append(card)
            continue

        # 普通卡牌出牌逻辑
        if card.get('target'):
            target = card.get('target_pos')
            pos_name = coord_to_name.get(target, "未知位置")
            print(f"[ACTION] 使用 {card['name']}（{card['energy']} 能量）→ 目标坐标 {pos_name} : {target}")
        else:
            print(f"[ACTION] 使用 {card['name']}（{card['energy']} 能量）")

        pyautogui.press(str(card['hotkey']))
        time.sleep(1)

        if card.get('target'):
            time.sleep(1)
            for i, target in enumerate(card['target_candidates'], 1):
                pos_name = coord_to_name.get(target, "未知位置")
                print(f"[ACTION] 第 {i} 个目标 → 重按热键 {card['hotkey']} + 点击坐标 {pos_name} : {target}")
                pyautogui.press(str(card['hotkey']))
                pyautogui.moveTo(*target)
                pyautogui.click()
                time.sleep(1)
                image("background", threshold=0.65)
                time.sleep(1)

        current_energy -= card['energy']

        if card['energy'] > 0 and card['name'] not in no_fragment_cards:
            fragment_value += card['energy']
            print(f"[INFO] 出完 {card['name']} ，碎片数量: {fragment_value}")

        if extra_card_flag:
            print("[INFO] 额外出牌完成，退出。")
            return current_energy, fragment_value

    if ronin_card and not extra_card_flag:
        current_energy = play_ronin_card(ronin_card, current_energy)

    if not extra_card_flag:
        print("[INFO] 结束出牌")
        pyautogui.press("E")

    if not extra_card_flag and skipped_cards:
        print("[INFO] 触发额外出牌，只出之前跳过的牌")
        play_cards(hand_cards, axie_info, current_energy, fragment_value, extra_card_flag=True, pending_cards=skipped_cards)

    return current_energy, fragment_value

def in_game():
    """检查是否在战斗中，通过寻找icon图片"""
    return image('origins', offset=(100, 0), gray_diff_threshold=12) is not None

def enter_game():
    if not in_game():
        print("当前不在游戏中。")
        subprocess.Popen(exe_path)
        time.sleep(10)
def close_game():
    subprocess.run(["taskkill", "/f", "/im", "AxieInfinity-Origins.exe"], shell=True)
    time.sleep(10)

def in_battle():
    """检查是否在战斗中，通过寻找icon图片"""
    return image('icon') is not None

def enter_battle():
    # 如果不在战斗中，则进入战斗
    if not in_battle():
        print("当前不在战斗中。")
        if image('tap', threshold=0.7, color=False):
            image('tap', threshold=0.7)
            image('next')
            wait_for_load('go_second')
        if image('next'):
            wait_for_load('go_second')
        if image('ranked'):
            wait_for_load('go_second')
        if image('play'):
            time.sleep(2)
            image('ranked')
            wait_for_load('go_second')
    else:
        print("当前已经在战斗中。")

print("=== 主程序 ===")
while True:
    enter_game()
    enter_battle()

    # 等待 'end' 图像加载，超时后进行胜负判断
    if wait_for_load('end', click_times=0, timeout=45):
        print("[INFO] 开始读取axie站位信息...")
        axie_info = get_axie_info()

        print("[ACTION] 开始读取手牌信息...")
        hand_cards = detect_all_hand_cards()

        print("[ACTION] 开始出牌...")
        play_cards(hand_cards, axie_info)









