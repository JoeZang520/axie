import time
import pyautogui
import random
import win32gui
import pygetwindow as gw
from datetime import datetime

# 复用现有的游戏控制与图像检测函数
from axie_origin import close_game, enter_game, enter_battle, loading, image, detect_cards

# 根据窗口标题，获取窗口的region
def get_window_region(window_title):
    win = gw.getWindowsWithTitle(window_title)[0]
    hwnd = win._hWnd  # pygetwindow Window 对象里能拿到 hwnd
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    # 注意：ClientRect 是相对窗口客户区的，需要转屏幕坐标
    pt = win32gui.ClientToScreen(hwnd, (left, top))
    pt2 = win32gui.ClientToScreen(hwnd, (right, bottom))
    window_region = (pt[0], pt[1], pt2[0]-pt[0], pt2[1]-pt[1])

    return window_region

# 从左到右扫描手牌，获取卡牌能量并打出能量>1的牌
def play_cards(color: bool = True) -> None:
    """
    使用 detect_cards 扫描当前手牌（包含能量信息），
    遵循槽位从左到右顺序，若某槽位检测到的卡牌能量 > 1，则按该槽位索引键打出。
    """
    # 获取axie origin窗口位置信息
    win_x, win_y, win_width, win_height = get_window_region("AxieInfinity-Origins")

    # 读取卡牌起始坐标（窗口内坐标）
    read_win_x, read_win_y = 300, 780
    
    # 读取卡牌起始坐标（全局坐标）
    read_x, read_y = win_x + read_win_x, win_y + read_win_y
    pyautogui.moveTo(read_x, read_y)

    # 卡牌能量搜索区域
    energy_search_win_region = (0 + win_x, 300 + win_y, 1600, 300)

    for i in range(20):
        # pos = pyautogui.position()
        # print(pos)
        found = loading(
            ['card_charm_innate', 'card_energy_0', 'card_energy_1', 'card_energy_2', 'card_energy_1_grey', 'card_energy_2_grey'],
            check_interval=0.5,
            click_times=0,
            timeout=1,
            region=energy_search_region,
            gray_diff_threshold=0,
        )

        if found in ('card_charm_innate', 'card_energy_0', 'card_energy_2_grey'):
            pass
        elif found in ('card_energy_1', 'card_energy_2'):
            pyautogui.click()
            current_x, current_y = pyautogui.position()
            found_target = loading(
                ['card_target_enemy_1', 'card_target_ally_1', 'card_target_ally_2', 'card_target_ally_3'],
                check_interval=0.05,
                click_times=3,
                timeout=1,
                offset=(0, -30)
            )

            if found_target is not None:
                time.sleep(1)
            pyautogui.moveTo(current_x, current_y)

        elif found == 'card_energy_1_grey' or (i > 6 and found == None):
            break

        # 鼠标向右移动一段距离
        pyautogui.moveRel(100, 0)

    pyautogui.moveTo(read_x, read_y)

def end_turn_loop(max_wait_seconds: int = 120) -> str:
    """在一局对战中循环：
    - 首先检测是否在战斗中，若检测不到 arcade_battleground，则返回 'timeout'
    - 若检测到 end，则按 E 结束回合，继续等待下一次 end 或对局结算
    - 若检测到 tap/tap1（结算），则点击并返回 'victory'
    - 超时则返回 'surrender', 接上enter_battle函数可直接投降
    """
    # 首先检查是否在战斗场地中
    battleground_check = loading(['arcade_battleground'], check_interval=0.5, click_times=0, timeout=20, color=False)
    if battleground_check is None:
        print("[WARN] 未检测到 arcade_battleground，可能已离开战斗场地")
        return 'timeout'
    
    start_ts = time.time()
    while time.time() - start_ts < max_wait_seconds:
        found = loading(['end', 'tap', 'tap1'], check_interval=1, click_times=0, timeout=20, color=False)
        if found in ('tap', 'tap1'):
            # 结算页或继续提示，点击继续并退出本局循环
            image('tap', color=False)
            time.sleep(1)
            pyautogui.click()
            return 'victory'
        if found == 'end':
            play_cards()
            # 发现可结束回合，直接按 E
            pyautogui.press('E')
            # 给动画一点时间，避免过快触发
            time.sleep(2)
            continue
        # 未识别或超时，稍作等待重试
        time.sleep(1)
    return 'surrender'

# Arcade模式刷AXP设置，不建议修改
mode = 'arcade'
choice = 'go_first'

# 设置游戏结束时间（24小时制，例如：23:30表示23点30分）
end_time = "23:59"

# 设置投降等待时间，超过时间则投降
min_surrender_seconds = 120
max_surrender_seconds = 180

# 设置连续游玩时间，以分钟为单位
min_play_minutes = 180
max_play_minutes = 240

# 设置休息时间，以分钟为单位
min_rest_minutes = 20
max_rest_minutes = 40

def main():
    # 启动或切回游戏
    enter_game()

    battle_results=[]
    # 记录开始时间
    session_start_time = datetime.now()
    max_play_time = random.randint(min_play_minutes, max_play_minutes)
    
    # 记录连续timeout次数
    consecutive_timeout_count = 0
    
    # 持续打多把：每把只做"结束回合"
    while True:
        # 进入arcade模式对战，选择后手
        enter_battle(choice, mode)
        # 稍等以避免频繁操作
        time.sleep(2)
        
        # 在投降等待区间内随即设置一个等待时间，超过等待时间则结束end_turn_loop函数，直接投降
        random_wait_seconds = random.randint(min_surrender_seconds, max_surrender_seconds)

        # 一直结束回合等待对手投降或者超时我方投降
        result = end_turn_loop(random_wait_seconds)
        battle_results.append(result)
        
        # 检查连续timeout情况
        if result == 'timeout':
            consecutive_timeout_count += 1
            print(f"[WARN] 连续timeout次数: {consecutive_timeout_count}/3")
            
            if consecutive_timeout_count >= 3:
                print("[WARN] 连续3次timeout，重启游戏...")
                # 关闭游戏
                close_game()
                time.sleep(5)  # 等待游戏完全关闭
                
                # 重新启动游戏
                enter_game()
                consecutive_timeout_count = 0  # 重置计数器
                print("[INFO] 游戏已重启，继续游玩...")
                continue
        else:
            # 如果不是timeout，重置计数器
            consecutive_timeout_count = 0

        # 检查连续游玩时间是否超过设定时间
        current_time = datetime.now()
        continuous_play_minutes = (current_time - session_start_time).total_seconds() / 60
        if continuous_play_minutes >= max_play_time:
            print(f"[INFO] 连续游玩时间 {continuous_play_minutes:.1f} 分钟，超过设定时间 {max_play_time} 分钟")
            print("[INFO] 开始休息...")
            
            # 关闭游戏
            close_game()
            
            # 计算休息时间（分钟转秒）
            rest_minutes = random.randint(min_rest_minutes, max_rest_minutes)
            rest_seconds = rest_minutes * 60
            print(f"[INFO] 休息时间: {rest_minutes} 分钟")
            time.sleep(rest_seconds)
            print("[INFO] 休息结束，重新启动游戏...")
            
            # 重新启动游戏并重置开始时间
            enter_game()
            session_start_time = datetime.now()
            max_play_time = random.randint(min_play_minutes, max_play_minutes)
            print("[INFO] 游戏已重新启动，继续游玩...")
            continue
        
        # 检查当前时间是否超过设定的退出时间
        current_time_only = current_time.time()
        exit_time = datetime.strptime(end_time, '%H:%M').time()
        if current_time_only >= exit_time:
            print(f"[INFO] 当前时间 {current_time_only.strftime('%H:%M')} 已超过设定的退出时间 {end_time}")
            print("[INFO] 退出游戏...")
            close_game()
            break
        else:
            print(f"[INFO] 当前时间 {current_time_only.strftime('%H:%M')} 预计退出时间 {end_time}")
            print(f"[INFO] 连续游玩时间: {continuous_play_minutes:.1f} 分钟 / 最大 {max_play_time} 分钟")

    victory_count = battle_results.count('victory')
    surrender_count = battle_results.count('surrender')
    print(f"[INFO] 胜利次数: {victory_count} 投降次数: {surrender_count}")
    print(f"[INFO] 总场次: {len(battle_results)}")
    print(f"[INFO] 胜率: {victory_count / len(battle_results)}")
    print(f"[INFO] 投降率: {surrender_count / len(battle_results)}")

if __name__ == "__main__":
    main()
