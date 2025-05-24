import os
import time
import cv2
import numpy as np
import pyautogui

import os
import time
import cv2
import numpy as np
import pyautogui

def picture(png, threshold=0.8, offset=(0, 0), click_times=1, region=None, color=True):
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
        print(f"[MISS] 没有找到 {png} (匹配度: {max_val:.2f})")
        return None

    # 匹配区域坐标范围
    match_area = screen_img[
        max_loc[1]:max_loc[1] + template.shape[0],
        max_loc[0]:max_loc[0] + template.shape[1]
    ]

    # 如果是彩色匹配，进一步判断是否匹配到灰色区域
    if color:
        diff_rg = np.abs(match_area[:, :, 2] - match_area[:, :, 1])
        diff_rb = np.abs(match_area[:, :, 2] - match_area[:, :, 0])
        diff_gb = np.abs(match_area[:, :, 1] - match_area[:, :, 0])
        mean_diff = np.mean((diff_rg + diff_rb + diff_gb) / 3.0)

        if mean_diff < 15:  # 阈值可调，建议 5~15
            print(f"[FAIL] 匹配区域颜色太灰（均差≈{mean_diff:.2f}），跳过点击")
            return None

    # 计算中心点击位置
    center_x = max_loc[0] + template.shape[1] // 2 + x1 + offset[0]
    center_y = max_loc[1] + template.shape[0] // 2 + y1 + offset[1]

    if click_times > 0:
        print(f"[ACTION] 点击 {png} ({center_x}, {center_y})")

    return (center_x, center_y)


time.sleep(2)
picture("energy_3")