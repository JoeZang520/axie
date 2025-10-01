import schedule
import time
import subprocess
import os
import threading
import queue
import sys
from datetime import datetime, timedelta

# 使用相对路径
AXIE_ORIGIN_PATH = 'axie_origin.py'
AXIE_LAND_PATH = 'axie_land.py'
AXIE_CLASSIC_PATH = 'axie_classic.py'
PYTHON_EXECUTABLE = sys.executable  # 获取当前Python解释器路径

task_queue = queue.Queue()
current_task = None
last_status_print = 0  # 用于控制状态打印频率


# 是否启动时立即执行任务
IMMEDIATE_RUN_LAND = True   # 设置为False则不立即执行axie_land
IMMEDIATE_RUN_ORIGIN = True # 设置为False则不立即执行axie_origin
IMMEDIATE_RUN_CLASSIC = True  # 新增，是否启动时立即执行classic

def run_script(script_name):
    global current_task
    current_task = script_name
    print(f"[run_script] 正在启动 {script_name} ...")
    process = subprocess.Popen([PYTHON_EXECUTABLE, script_name], cwd=os.path.dirname(__file__))
    process.wait()
    print(f"[run_script] {script_name} 执行完毕。")
    current_task = None
    # if script_name == AXIE_CLASSIC_PATH:  # 如果是origin脚本
    #     print("origin脚本执行完毕，退出程序...")
    #     sys.exit(0)  # 直接退出程序

def worker():
    print("[worker] worker线程已启动")
    while True:
        script_name = task_queue.get()
        print(f"[worker] 取出任务: {script_name}")
        run_script(script_name)
        task_queue.task_done()

def print_queue_status():
    status = ""
    if current_task:
        status += f"正在执行: {current_task}；"
    if not task_queue.empty():
        status += f"等待中: {[task_queue.queue[i] for i in range(task_queue.qsize())]}"
    if not status:
        status = "无任务正在执行或等待"
    print(f"[schedule] 队列状态：{status}")

def print_heartbeat():
    global last_status_print
    current_time = time.time()
    # 每60秒打印一次状态
    if current_time - last_status_print >= 60:
        print(f"\n[heartbeat] 调度器正在运行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_queue_status()
        last_status_print = current_time

def print_schedule_status():
    if not task_queue:  # 如果队列为空
        print("[schedule] 当前没有待执行的任务")
    else:


        next_task = task_queue[0]  # 获取下一个要执行的任务
        print(f"[schedule] 当前任务状态：")
        print(f"- 正在执行：{current_task.name if current_task else '无'}")
        print(f"- 等待中的任务数：{len(task_queue)}")
        print(f"- 下一个任务：{next_task.name}")
        print(f"- 预计执行时间：{next_task.scheduled_time}")

# 移除定时任务，改为轮流执行两个脚本


# SCRIPTS = [AXIE_LAND_PATH, AXIE_ORIGIN_PATH]
# SCRIPTS = [ AXIE_LAND_PATH, AXIE_CLASSIC_PATH, AXIE_ORIGIN_PATH]
SCRIPTS = [AXIE_LAND_PATH, AXIE_CLASSIC_PATH]
IMMEDIATE_FLAGS = [IMMEDIATE_RUN_LAND, IMMEDIATE_RUN_ORIGIN, IMMEDIATE_RUN_CLASSIC]
script_index = -1
print("中控脚本已启动，将轮流执行axie_land、axie_origin和axie_classic...")

# 启动工作线程
t1 = threading.Thread(target=worker, daemon=True)
t1.start()

# 立即加入三个任务各一次
for i, (script, flag) in enumerate(zip(SCRIPTS, IMMEDIATE_FLAGS)):
    if flag:
        print(f"[schedule] 立即执行{script}任务")
        task_queue.put(script)
        script_index = i

while True:
    # 如果队列空了，自动加入下一个脚本
    if task_queue.empty() and current_task is None:
        script_index = (script_index + 1) % len(SCRIPTS)
        next_script = SCRIPTS[script_index]
        print(f"[schedule] 队列空，自动加入{next_script}任务")
        task_queue.put(next_script)
    print_heartbeat() 
     # 定期打印状态
    time.sleep(10)