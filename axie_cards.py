axie_cards = {

    "middle_axie": [
        ("nut_t", 1, False, None, None),
        ("nut_m", 1, False, None, None),
        ("nut_e", 1, False, None, None),
        ("peas", 1, False, None, None),
        ("imp", 1, False, None, None),
        ("ronin", 1, False, None, None)
    ],
    "back_axie": [
        ("pogona", 1, False, None, None),
        ("confusion", 1, True, "ally", "all"),
        ("cottontail", 0, True, "ally", "all"),  # 0费
        ("unko", 1, True, "ally", "all"),
        ("pigeon_post", 1, True, "enemy", "front_back"),
        ("tiny_turtle", 1, True, "enemy", "front_back")
    ],
    "front_axie": [
        ("cattail", 1, True, "ally", "all"),
        ("babylon", 1, True, "enemy", "front_back"),
        ("lam", 1, False, None, None),
        ("confusion", 1, True, "ally", "all"),
        ("leafy", 1, False, None, None),
        ("hermit", 1, True, "ally", "all")
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
    'nut_t', 'nut_m', 'nut_e', 'peas', 'imp', 'ronin',
    'pogona', 'babylon', 'tiny_turtle', 'cattail', 'lam', 'leafy', 'pigeon_post',
    'confusion', 'unko', 'hermit', 'cottontail', "glove", "sword", "knife", "shield", "axe"
]
card_to_detect= ["blackmail", "energy_coin", "sword", "shield", "knife", "axe", "goo", "jinx", "confused", "back_axie", "middle_axie", "front_axie"]

# 读取手牌信息时需要用到的模板匹配阈值
thresholds = {
    "blackmail": 0.9,
    "energy_coin": 0.95,
    "back_axie": 0.65,
    "middle_axie": 0.65,
    "front_axie": 0.65,
    "goo": 0.95,
    "jinx": 0.95,
    "confused": 0.9,
    "sword": 0.9,
    "shield": 0.9,
    "knife": 0.9,
    "axe": 0.95
}

no_fragment_cards = ['nut_t']
exe_path = r"E:\Axie Infinity - Origins\AxieInfinity-Origins.exe"