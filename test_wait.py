#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pynput import keyboard
import threading

def wait_with_pause(seconds, pause_key=keyboard.Key.space):
    """
    等待指定秒数，期间可以通过space键暂停/继续程序
    
    Args:
        seconds: 等待的秒数
        pause_key: 暂停/继续的按键，默认为space键
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
                print("\r[INFO] 程序已暂停，按space键继续...", end="", flush=True)
                paused = True
                pause_event.clear()
    
    def on_release(key):
        pass
    
    # 创建键盘监听器
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    print(f"[INFO] 等待{seconds}秒，按space键可暂停/继续程序...")
    
    start_time = time.time()
    elapsed_time = 0
    
    try:
        while elapsed_time < seconds:
            if not paused:
                remaining = seconds - elapsed_time
                if remaining > 0:
                    print(f"\r[倒计时] 剩余 {remaining:.1f} 秒 (按space暂停)", end="", flush=True)
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

if __name__ == "__main__":
    print("测试wait_with_pause函数...")
    print("程序将等待6秒，你可以按space键暂停/继续")
    wait_with_pause(6)
    print("测试完成！") 