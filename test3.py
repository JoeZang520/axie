# main.py
import cv2
import pyautogui
import numpy as np
import os
import time
from card_config import CARD_ENERGY, PRIORITY

# 常量配置
MAX_RETRY = 1  # 单张卡牌最大重试次数
SPECIAL_CARDS = ["cattail", "confusion"]  # 需要额外操作的特殊卡

# 初始化全局状态
available_cards = []
played_cards = []
current_energy = None


def picture(png, threshold=0.9, offset=(0, 0), click_times=1, region=None):
    """增强版图像识别函数"""
    try:
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

        # 截图并识别
        screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
        screen_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            print(f"[[MISS] 没有找到 {png} ")
            return None

        # 计算点击位置
        center_x = max_loc[0] + template.shape[1] // 2 + x1 + offset[0]
        center_y = max_loc[1] + template.shape[0] // 2 + y1 + offset[1]

        if click_times > 0:
            print(f"[ACTION] 点击 {png} ({center_x}, {center_y})")
            pyautogui.moveTo(center_x, center_y)
            for _ in range(click_times):
                pyautogui.click()
            pyautogui.moveTo(center_x, center_y - 500)  # 移开鼠标避免遮挡
        return (center_x, center_y, max_val)  # 返回匹配度用于调试

    except Exception as e:
        print(f"[ERROR] 图像识别异常: {str(e)}")
        return None

def should_retry(cards):
    """判断是否需要重试查找卡牌"""
    if not hasattr(should_retry, 'retry_records'):
        should_retry.retry_records = {}

    key = tuple(sorted(cards))
    should_retry.retry_records[key] = should_retry.retry_records.get(key, 0) + 1

    if should_retry.retry_records[key] >= MAX_RETRY:
        print(f"[LIMIT] 超过最大重试次数: {cards}")
        should_retry.retry_records.pop(key, None)
        return False
    return True


def move_to_play(position_type, current_energy, played_cards):
    """
    优化后的通用位置出牌函数
    :param position_type: 位置类型 ("middle"/"front"/"back")
    :param current_energy: 当前剩余能量
    :param played_cards: 已出卡牌列表
    :return: 更新后的剩余能量和已出卡牌列表
    """
    # 1. 定位目标位置（图片名自动使用position_type）
    positions = picture(position_type, threshold=0.5, click_times=0)

    # 去重处理
    unique_positions = []
    for pos in positions:
        if not any(abs(pos[0] - p[0]) < 60 and abs(pos[1] - p[1]) < 10 for p in unique_positions):
            unique_positions.append(pos)

    # 如果没有找到位置则直接返回
    if not unique_positions:
        print(f"[WARN] 未找到{position_type}位置目标")
        return current_energy, played_cards

    # 2. 获取当前能量等级下的可用卡牌
    energy_level = f"energy_{min(4, current_energy)}"
    available_cards = [card for card in PRIORITY[energy_level][position_type]
                       if card not in played_cards]

    # 3. 对每个位置执行出牌
    remaining_energy = current_energy
    for x, y in unique_positions:
        pyautogui.moveTo(x, y)
        time.sleep(0.5)  # 确保UI刷新

        for card in available_cards.copy():
            cost = CARD_ENERGY.get(card, 0)

            if remaining_energy - cost < 0:
                continue  # 跳过能量不足的卡牌

            if picture(card, click_times=0):
                print(f"[PLAY] {position_type.upper()}位置 {card} (消耗{cost}费)")
                picture(card, click_times=1)
                played_cards.append(card)
                remaining_energy -= cost
                available_cards.remove(card)

                # 特殊卡处理
                if card in SPECIAL_CARDS:
                    time.sleep(0.8)
                    picture("end", offset=(-1350, 0), click_times=1)

                print(f"[STATUS] 剩余能量: {remaining_energy}费")
                time.sleep(1)
                if remaining_energy <= 0:
                    break

        # 移开鼠标
        pyautogui.moveTo(x, y - 500)

    return remaining_energy, played_cards


# 主循环
print("===== 卡牌自动化脚本启动 =====")
while True:
    try:
        # 1. 检查游戏结束界面
        if picture("tap", click_times=0):
            print("[STATUS] 正在进入下一局...")
            time.sleep(1)
            picture("tap", click_times=1)
            picture("next", click_times=1)
            time.sleep(5)
            # 持续检测go_second（动态等待）
            for _ in range(10):
                if picture("go_second", click_times=1):
                    break
                time.sleep(3)
            time.sleep(5)
            available_cards = []
            played_cards = []
            current_energy = None
            continue

        # 2. 检测回合开始
        if picture("end", click_times=0):
            # 初始化回合状态
            if current_energy is None:
                print("[PHASE] 新回合开始")
                if picture("energy_4", click_times=0):
                    current_energy = 4
                elif picture("energy_3", click_times=0):
                    current_energy = 3
                elif picture("energy_2", click_times=0):
                    current_energy = 2
                else:
                    current_energy = 1

                played_cards = []  # 新回合重置已出卡牌
                print(f"[STATUS] 能量: {current_energy}费")
            time.sleep(3)

        # 3. 执行出牌序列（按优先级顺序）
        if current_energy and current_energy > 0:
            # 先出middle位置的牌
            current_energy, played_cards = move_to_play("middle", current_energy, played_cards)

            # 如果还有剩余能量，出front位置的牌
            if current_energy > 0:
                current_energy, played_cards = move_to_play("front", current_energy, played_cards)

            # 如果还有剩余能量，出back位置的牌
            if current_energy > 0:
                current_energy, played_cards = move_to_play("back", current_energy, played_cards)

        time.sleep(1)  # 主循环间隔

    except Exception as e:
        print(f"[ERROR] 发生异常: {str(e)}")
        time.sleep(5)