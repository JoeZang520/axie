import schedule
import time
import subprocess
import os
import threading
import queue

# 使用相对路径
AXIE_ORIGIN_PATH = 'axie_origin.py'
AXIE_LAND_PATH = 'axie_land.py'

task_queue = queue.Queue()
current_task = None

def run_script(script_name):
    global current_task
    current_task = script_name
    print(f"[run_script] 正在启动 {script_name} ...")
    process = subprocess.Popen(['python', script_name], cwd=os.path.dirname(__file__))
    process.wait()
    print(f"[run_script] {script_name} 执行完毕。")
    current_task = None

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

# 启动工作线程
t1 = threading.Thread(target=worker, daemon=True)
t1.start()

# 定时任务：只有没有任务在执行时才加入新任务，否则打印当前队列内容
schedule.every(3600).seconds.do(
    lambda: (print("[schedule] 加入axie_origin任务"), task_queue.put(AXIE_ORIGIN_PATH))
    if not current_task
    else print_queue_status()
)
schedule.every(3600).seconds.do(
    lambda: (print("[schedule] 加入axie_land任务"), task_queue.put(AXIE_LAND_PATH))
    if not current_task
    else print_queue_status()
)

print("中控脚本已启动，等待定时任务执行...")

# 立即执行一次任务
print("[schedule] 立即执行axie_origin任务")
task_queue.put(AXIE_ORIGIN_PATH)
print("[schedule] 立即执行axie_land任务")
task_queue.put(AXIE_LAND_PATH)

while True:
    schedule.run_pending()
    time.sleep(1)