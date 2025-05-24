import cv2
import numpy as np
import pyautogui
import os
import time


def picture(png, threshold=0.8, offset=(0, 0), click_times=1, region=None, angles = [0, -3, -6, 3, 6, 9, -9] ):
    if not png.endswith('.png'):
        png += '.png'
    image_path = os.path.join('pic', png)
    if not os.path.exists(image_path):
        return None
    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if template is None:
        return None
    if region is None:
        region = (0, 0, pyautogui.size().width, pyautogui.size().height)
    x1, y1, x2, y2 = region
    screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
    screen_img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    for angle in angles:
        center = (template.shape[1] // 2, template.shape[0] // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_template = cv2.warpAffine(template, matrix, (template.shape[1], template.shape[0]))
        result = cv2.matchTemplate(screen_img, rotated_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            center_x = max_loc[0] + rotated_template.shape[1] // 2 + x1 + offset[0]
            center_y = max_loc[1] + rotated_template.shape[0] // 2 + y1 + offset[1]
            position = (center_x, center_y)

            if click_times > 0:
                for _ in range(click_times):
                    pyautogui.moveTo(center_x, center_y)
                    print(f"found {png} ({center_x}, {center_y} angle={angle})")
                    time.sleep(0.2)
            return position
    print(f"not found {png}")
    return None


# 调用示例
picture("nut_t")