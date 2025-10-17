import time
import pyautogui
import random
from datetime import datetime
# 复用现有的游戏控制与图像检测函数
from axie_origin import close_game, enter_game, enter_battle, loading, image

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
choice = 'go_second'

# 设置游戏结束时间（24小时制，例如：23:30表示23点30分）
end_time = "23:00"

# 设置投降等待时间，超过时间则投降
min_surrender_seconds = 70
max_surrender_seconds = 90

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
        
        # 检查当前时间是否超过设定的退出时间
        current_time_only = current_time.time()
        exit_time = datetime.strptime(end_time, '%H:%M').time()
        if current_time_only >= exit_time:
            print(f"[INFO] 当前时间 {current_time_only.strftime('%H:%M')} 已超过设定的退出时间 {end_time}")
            print("[INFO] 退出游戏...")
            # 这里可以添加退出游戏的逻辑，比如按ESC或关闭窗口
            pyautogui.press('esc')  # 按ESC键退出
            break
        else:
            print(f"[INFO] 当前时间 {current_time_only.strftime('%H:%M')} 预计退出时间 {end_time}")
            print(f"[INFO] 连续游玩时间: {continuous_play_minutes:.1f} 分钟 / 最大 {max_play_time} 分钟")

    close_game()

    victory_count = battle_results.count('victory')
    surrender_count = battle_results.count('surrender')
    print(f"[INFO] 胜利次数: {victory_count} 投降次数: {surrender_count}")
    print(f"[INFO] 总场次: {len(battle_results)}")
    print(f"[INFO] 胜率: {victory_count / len(battle_results)}")
    print(f"[INFO] 投降率: {surrender_count / len(battle_results)}")

if __name__ == "__main__":
    main()
