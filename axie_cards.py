# 可變信息
MIDDLE_ROLE = "middle4548"
BACK_ROLE = "back11638783"
FRONT_ROLE = "front11935341"
CHOICE = "go_first"  # 可以改为: "go_first" 或 "no_pref"
exe_path = r"E:\Axie Infinity - Origins\AxieInfinity-Origins.exe"

axie_cards = {

    "middle4548": [
        ("zeal", 0, False, None, None),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费
        ("little_branch", 2, False, None, None),
        ("puppy_ear", 1, False, None, None),      
        ("tiny_dino", 1, False, None, None),
        ("hero", 1, False, None, None)
     
    ],
    "middle12091318": [
        ("puppy_eye", 0, True, "ally", "all"),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费
        ("little_branch", 2, False, None, None),
        ("puppy_ear", 1, False, None, None),      
        ("shiba", 2, False, None, None),
        ("ronin", 1, False, None, None)
     
    ],
    "middle11563429": [
        ("zeal", 0, False, None, None),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费
        ("little_branch", 2, False, None, None),
        ("belieber", 1, False, None, None),      
        ("shiba", 2, False, None, None),
        ("ronin", 1, False, None, None)
     
    ],
    "back1523": [
        ("zeal", 0, False, None, None),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费 
        ("cattail", 1, True, "ally", "all"),
        ("innocent_lamb", 0, False, None, None),  
        ("strawberry", 2, True, "ally", "all"), 
        ("strawberry_son", 0, True, "ally", "all"),
        ("mint", 1, False, None, None)
    ],
    "back11638783": [
        ("zeal", 0, False, None, None),  # 0费
        ("silence", 1, True, "ally", "all"),   
        ("cattail", 1, True, "ally", "all"),
        ("innocent_lamb", 0, False, None, None),  
        ("rose_bud", 1, True, "ally", "all"), 
        ("mint", 1, False, None, None)
    ],
    "back11772419": [
        ("zeal", 0, False, None, None),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费  
        ("ant", 1, False, None, None),
        ("green1", 1, True, "ally", "all"), 
        ("green2", 1, True, "ally", "all"), 
        ("hermit", 1, True, "ally", "all"),
    ],
    "back11651972": [
        ("zeal", 0, False, None, None),  # 0费
        ("silence", 1, True, "ally", "all"),  
        ("cattail", 1, True, "ally", "all"),
        ("green1", 1, True, "ally", "all"), 
        ("green2", 1, True, "ally", "all"), 
        ("indian_star", 1, True, "ally", "all"),
    ],
    "front1409": [
        ("cattail", 1, True, "ally", "all"),
        ("confident", 0, True, "ally", "all"),  # 0费
        ("zeal", 0, False, None, None),  # 0费 
        ("lotus", 1, True, "ally", "all"),
        ("rose_bud", 1, True, "ally", "all"),
        ("bidens", 1, True, "ally", "all")
    ],
    "front11935341": [
        ("cattail", 1, True, "ally", "all"),
        ("silence", 1, True, "ally", "all"),
        ("zeal", 0, False, None, None),  # 0费 
        ("lotus", 1, True, "ally", "all"),
        ("rose_bud", 1, True, "ally", "all"),
        ("bidens", 1, True, "ally", "all")
    ],
    "front11358950": [
        ("green1", 1, True, "ally", "all"), 
        ("silence", 1, True, "ally", "all"),  
        ("zeal", 0, False, None, None),  # 0费 
        ("clover", 1, True, "ally", "all"),
        ("green2", 1, True, "ally", "all"), 
        ("shoal_star", 1, True, "enemy", "front_back")
    ],
    "front11901989": [
        ("zeal", 0, False, None, None),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费  
        ("cattail", 1, True, "ally", "all"),
        ("innocent_lamb", 0, False, None, None),  
        ("green1", 1, True, "ally", "all"), 
        ("cuckoo", 1, True, "ally", "all"),
    ],
    "blackmail": [
        ("blackmail_card", 0, False, None, None)
    ],
    "energy_coin": [
        ("energy_coin_card", 0, False, None, None)
    ],
    "glove": [
        ("glove_card", 0, True, "ally", "all")  # 0费
    ],
    "goo": [
        ("goo_card", 0, False, None, None)  # 0费
    ],
    "jinx": [
        ("jinx_card", 99, False, None, None)  # X费
    ],
    "confused": [
        ("confused_card", 99, False, None, None)  # X费
    ],
    "sword": [
        ("sword_card", 1, False, None, None)
    ],
    "shield": [
        ("shield_card", 1, True, "ally", "all")
    ],
    "knife": [
        ("knife_card", 1, True, "ally", "all")
    ],
    "helmet": [
        ("helmet_card", 2, True, "ally", "ally")  # 2费
    ],
    "axe": [
        ("axe_card", 2, False, None, None)  # 2费
    ]

}

card_priority = ['innocent_lamb',
    'confident', 'puppy_eye', 'little_branch', 'shiba', 'puppy_ear', 'belieber', 'ronin', 'zeal', 'tiny_dino','hero',
    'energy_coin_card', 'cattail', 'ant', 'mint', 'silence', 'biden', 'rose_bud','lotus', 'green1', 'green2', 'green3', 'cuckoo', 'hermit', 'clover', 'shoal_star',
    'glove', 'sword', 'knife', 'shield', 'axe'
]

# 读取手牌信息时需要用到的模板匹配阈值
thresholds = {
    "blackmail": 0.9,
    "energy_coin": 0.9,
    BACK_ROLE: 0.75,
    MIDDLE_ROLE: 0.65,
    FRONT_ROLE: 0.65,
    "goo": 0.9,
    "jinx": 0.9,
    "confused": 0.95,
    "glove": 0.9,
    "sword": 0.9,
    "shield": 0.85,
    "knife": 0.9,
    "axe": 0.9
}

# 通用卡牌列表
COMMON_CARDS = ['glove', 'helmet', 'sword', 'knife', 'shield', 'axe', "blackmail", "energy_coin", "goo", "jinx", "confused"]

# 使用常量定义检测卡牌列表
card_to_detect = COMMON_CARDS + [BACK_ROLE, MIDDLE_ROLE, FRONT_ROLE]