axie_cards = {

    "middle4548": [
        ("zeal", 0, False, None, None),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费
        ("little_branch", 2, False, None, None),
        ("puppy_ear", 1, False, None, None),
        ("hero", 1, False, None, None),
        ("tiny_dino", 1, False, None, None)
     
    ],
    "back1523": [
        ("zeal", 0, False, None, None),  # 0费
        ("confident", 0, True, "ally", "all"),  # 0费 
        ("cattail", 1, True, "ally", "all"),
        ("innocent_lamb", 0, False, None, None),  # 0费
        ("lagging", 1, True, "ally", "all"),  
        ("mint", 1, False, None, None)
    ],
    "front1409": [
        ("cattail", 1, True, "ally", "all"),
        ("confident", 0, True, "ally", "all"),  # 0费
        ("zeal", 0, False, None, None),  # 0费
        ("lotus", 1, True, "ally", "all"),
        ("rose_bud", 1, True, "ally", "all"),
        ("bidens", 1, True, "ally", "all")
    ],
    "blackmail": [
        ("blackmail_card", 0, False, None, None)
    ],
    "energy_coin": [
        ("energy_coin_card", 0, False, None, None)
    ],
    "glove": [
        ("energy_coin_card", 0, True, "ally", "all")  # 0费
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
    "axe": [
        ("axe_card", 2, False, None, None)  # 2费
    ]

}

card_priority = [
    'innocent_lamb', 'confident', 'little_branch', 'puppy_ear', 'hero', 'zeal', 'tiny_dino',
    'energy_coin_card', 'cattail', 'mint', 'rose_bud', 'biden', 'lotus', 'lagging',
    'glove', 'sword', 'knife', 'shield', 'axe'
]
card_to_detect= ['glove', 'sword', 'knife', 'shield', 'axe', "blackmail", "energy_coin", "goo", "jinx", "confused", 
                 "back1523", "middle4548", "front1409"]

# 读取手牌信息时需要用到的模板匹配阈值
thresholds = {
    "blackmail": 0.9,
    "energy_coin": 0.9,
    "back1523": 0.65,
    "middle4548": 0.65,
    "front1409": 0.65,
    "goo": 0.9,
    "jinx": 0.9,
    "confused": 0.95,
    "glove": 0.9,
    "sword": 0.9,
    "shield": 0.85,
    "knife": 0.9,
    "axe": 0.9
}

exe_path = r"E:\Axie Infinity - Origins\AxieInfinity-Origins.exe"
go_second = 'go_second'
no_pref = 'no_pref'