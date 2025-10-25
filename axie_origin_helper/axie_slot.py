import cv2
import numpy as np
from dataclasses import dataclass

def get_hsv_img_region(img, region=None):
    hsv_img = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    if region is None:
        return hsv_img

    x, y, w, h = region
    return hsv_img[y:y+h, x:x+w]

# Axie 截图窗口大小
axie_width = 180
axie_height = 120
axie_target_height = 50

# 目标黄圈HSV值
H0, S0, V0 = 24, 145, 251
dH, dS, dV = 2, 15, 50

lower = np.array([
    max(H0 - dH, 0),
    max(S0 - dS, 0),
    max(V0 - dV, 0)
], dtype=np.uint8)

upper = np.array([
    min(H0 + dH, 179),  # Hue 上限 179
    min(S0 + dS, 255),
    min(V0 + dV, 255)
], dtype=np.uint8)

# 目标黄圈的椭圆形状filter
target_filter = np.load("axie_origin_helper/axie_target_filter.npy")

@dataclass
class Slot:
    name: str
    region: tuple[int, int, int, int]
    region_center: tuple[int, int]
    target_region: tuple[int, int, int, int]
    threshold: float
    priority: int

    def __init__(self, name, region, priority=1, threshold=5):
        self.name = name
        self.region = region
        self.threshold = threshold
        self.priority = priority

        x, y, w, h = region
        self.target_region = (x, y + h - 25, w, axie_target_height)
        self.region_center = (x + w/2, y + h/2)

    def is_target(self, img):
        mask = cv2.inRange(get_hsv_img_region(img, self.target_region), lower, upper)
        mask = mask * target_filter
        return mask.mean() > self.threshold

    def get_mask_mean(self, img):
        mask = cv2.inRange(get_hsv_img_region(img, self.target_region), lower, upper)
        mask = mask * target_filter
        return mask.mean()

# 定义友方axie的位置
axie_slot_ally_1 = Slot("ally1", (585, 438, axie_width, axie_height), 6)
axie_slot_ally_2 = Slot("ally2", (485, 550, axie_width, axie_height), 5)
axie_slot_ally_3 = Slot("ally3", (385, 438, axie_width, axie_height), 4)
axie_slot_ally_4 = Slot("ally4", (285, 550, axie_width, axie_height), 3)
axie_slot_ally_5 = Slot("ally5", (185, 438, axie_width, axie_height), 2)
axie_slot_ally_6 = Slot("ally6", (85, 550, axie_width, axie_height), 1)
ally_slots = [
    axie_slot_ally_1,
    axie_slot_ally_2,
    axie_slot_ally_3,
    axie_slot_ally_4,
    axie_slot_ally_5,
    axie_slot_ally_6,
]

# 定义敌方axie的位置
axie_slot_enemy_1 = Slot("enemy1", (835, 550, axie_width, axie_height), 7)
axie_slot_enemy_2 = Slot("enemy2", (935, 438, axie_width, axie_height), 8)
axie_slot_enemy_3 = Slot("enemy3", (1035, 550, axie_width, axie_height), 9)
axie_slot_enemy_4 = Slot("enemy4", (1135, 438, axie_width, axie_height), 10)
axie_slot_enemy_5 = Slot("enemy5", (1235, 550, axie_width, axie_height), 11)
axie_slot_enemy_6 = Slot("enemy6", (1335, 438, axie_width, axie_height), 12)
enemy_slots = [
    axie_slot_enemy_1,
    axie_slot_enemy_2,
    axie_slot_enemy_3,
    axie_slot_enemy_4,
    axie_slot_enemy_5,
    axie_slot_enemy_6,
]

all_slots = ally_slots + enemy_slots
