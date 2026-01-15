// ============================================================
// 三國戰記 - 遊戲數據配置 (完全按照原 Python 遊戲)
// ============================================================

// === 英雄池 (6個英雄) ===
const HERO_POOL = [
    { name: "關羽", type: 0, base_hp: 130, base_atk: 22, base_speed: 3 },
    { name: "張飛", type: 0, base_hp: 140, base_atk: 21, base_speed: 2.8 },
    { name: "趙雲", type: 1, base_hp: 115, base_atk: 24, base_speed: 3.4 },
    { name: "馬超", type: 1, base_hp: 120, base_atk: 23, base_speed: 3.5 },
    { name: "黃忠", type: 2, base_hp: 100, base_atk: 26, base_speed: 3 },
    { name: "黃月英", type: 2, base_hp: 105, base_atk: 24, base_speed: 3 }
];

// 稀有度權重 (隨機抽卡時使用)
const RARITY_WEIGHTS = [
    ["SSR", 1],   // 1%
    ["SR", 9],    // 9%
    ["R", 30],    // 30%
    ["C", 60]     // 60%
];

// === 章節配置 ===
const CHAPTER_CONFIGS = [
    {
        chapter: 1,
        name: "初出茅廬",
        waves: 8,
        base_hp: 80,
        base_atk: 15,
        level: 1,
        has_boss: false
    },
    {
        chapter: 2,
        name: "嶄露頭角",
        waves: 9,
        base_hp: 120,
        base_atk: 20,
        level: 5,
        has_boss: false
    },
    {
        chapter: 3,
        name: "中原逐鹿",
        waves: 10,
        base_hp: 160,
        base_atk: 26,
        level: 10,
        has_boss: true
    }
];

// === Boss 配置 ===
const BOSS_CONFIG = {
    name: "黃巾賊首",
    hp: 1500,
    phase_hp: [500, 350, 200],
    base_atk: 35,
    abilities: [
        {
            phase: 1,
            name: "普通攻擊",
            damage: 1.0,
            cooldown: 2.0,
            effect: "single"
        },
        {
            phase: 2,
            name: "旋風斬",
            damage: 2.0,
            cooldown: 3.0,
            effect: "aoe",
            range: 150
        },
        {
            phase: 3,
            name: "絕命一擊",
            damage: 3.0,
            cooldown: 4.0,
            effect: "execute",
            threshold: 0.3
        }
    ]
};

// === 波間事件 ===
const WAVE_EVENTS = [
    {
        name: "補給",
        desc: "所有單位恢復25% HP",
        effect: "heal",
        type: "buff",
        color: "#2ECC71"
    },
    {
        name: "陷阱",
        desc: "敵方下波的攻擊降低20%",
        effect: "curse",
        type: "buff",
        color: "#2ECC71"
    },
    {
        name: "增援",
        desc: "下波敵人減少1個",
        effect: "fewer_enemies",
        type: "buff",
        color: "#2ECC71"
    },
    {
        name: "暴雨",
        desc: "所有單位速度降低30%",
        effect: "slow",
        type: "curse",
        color: "#E74C3C"
    }
];

// === Roguelite Buff ===
const ROGUELITE_BUFFS = [
    {
        name: "攻速+30%",
        desc: "攻擊速度提升30%",
        effect: "atk_speed",
        type: "buff",
        color: "#FF6B6B"
    },
    {
        name: "暴擊+25%",
        desc: "暴擊率提升25%（傷害翻倍）",
        effect: "crit",
        type: "buff",
        color: "#FFD700"
    },
    {
        name: "移速+40%",
        desc: "單位移動速度提升40%",
        effect: "move_speed",
        type: "buff",
        color: "#4169FF"
    },
    {
        name: "吸血+15%",
        desc: "造成傷害時恢復15%血量",
        effect: "lifesteal",
        type: "buff",
        color: "#FF1493"
    },
    {
        name: "護甲+25%",
        desc: "受傷減少25%",
        effect: "armor",
        type: "buff",
        color: "#708090"
    },
    {
        name: "技能冷卻-40%",
        desc: "技能冷卻時間減少40%",
        effect: "cooldown",
        type: "buff",
        color: "#9370DB"
    }
];

// === Roguelite 詛咒 ===
const ROGUELITE_CURSES = [
    {
        name: "詛咒：衰弱",
        desc: "攻擊力降低30%",
        effect: "weakness",
        type: "curse",
        color: "#8B0000"
    },
    {
        name: "詛咒：遲緩",
        desc: "移動速度降低50%",
        effect: "curse_slow",
        type: "curse",
        color: "#4B0082"
    },
    {
        name: "詛咒：脆弱",
        desc: "受傷增加40%",
        effect: "curse_fragile",
        type: "curse",
        color: "#FF4500"
    }
];

// === 每日任務 ===
const DAILY_QUESTS = [
    {
        id: "daily_1",
        name: "新手入門",
        desc: "通關任意關卡1次",
        reward_gold: 100,
        reward_gems: 10,
        type: "daily",
        progress: 0,
        target: 1
    },
    {
        id: "daily_2",
        name: "冠軍戰士",
        desc: "通關關卡3次",
        reward_gold: 200,
        reward_gems: 20,
        type: "daily",
        progress: 0,
        target: 3
    },
    {
        id: "daily_3",
        name: "升級狂魔",
        desc: "升級武將2次",
        reward_gold: 150,
        reward_gems: 15,
        type: "daily",
        progress: 0,
        target: 2
    },
    {
        id: "daily_4",
        name: "裝備收集者",
        desc: "裝備4件裝備",
        reward_gold: 120,
        reward_gems: 25,
        type: "daily",
        progress: 0,
        target: 4
    },
    {
        id: "daily_5",
        name: "抽卡狂人",
        desc: "進行抽卡1次",
        reward_gold: 80,
        reward_gems: 30,
        type: "daily",
        progress: 0,
        target: 1
    }
];

// === 週任務 ===
const WEEKLY_QUESTS = [
    {
        id: "weekly_1",
        name: "週賽冠軍",
        desc: "通關關卡10次",
        reward_gold: 500,
        reward_gems: 100,
        type: "weekly",
        progress: 0,
        target: 10
    },
    {
        id: "weekly_2",
        name: "升級大師",
        desc: "升級武將5次",
        reward_gold: 400,
        reward_gems: 80,
        type: "weekly",
        progress: 0,
        target: 5
    },
    {
        id: "weekly_3",
        name: "Boss獵人",
        desc: "擊敗Boss 2次",
        reward_gold: 600,
        reward_gems: 120,
        type: "weekly",
        progress: 0,
        target: 2
    }
];

// === 兵種技能 (0=槍, 1=騎, 2=弓) ===
const UNIT_SKILLS = {
    0: {
        // 槍兵：貫穿突刺
        name: "貫穿突刺",
        desc: "對前方敵人造成150%傷害+25%概率眩暈",
        cooldown: 4.0,
        damage_mult: 1.5,
        range: 60,
        effect: "pierce",
        special: "stun_chance:0.25"
    },
    1: {
        // 騎兵：衝鋒突擊
        name: "衝鋒突擊",
        desc: "衝向敵人造成180%傷害並減速50%，自身恢復25% HP",
        cooldown: 5.0,
        damage_mult: 1.8,
        range: 80,
        effect: "charge",
        special: "self_heal:0.25"
    },
    2: {
        // 弓兵：連射覆蓋
        name: "連射覆蓋",
        desc: "向範圍內射出3支箭，每支造成120%傷害，目標減速",
        cooldown: 3.5,
        damage_mult: 1.2,
        arrow_count: 3,
        range: 100,
        effect: "volley",
        special: "slow:0.4"
    }
};

// === 英雄專精 ===
const HERO_SPECIALIZATION = {
    "關羽": {
        bonus: "skill_cooldown",
        value: 0.8,
        desc: "技能冷卻-20%"
    },
    "張飛": {
        bonus: "hp_recovery",
        value: 0.1,
        desc: "戰鬥中每秒回復最大HP的10%"
    },
    "趙雲": {
        bonus: "damage_boost",
        value: 1.15,
        desc: "攻擊力+15%"
    },
    "馬超": {
        bonus: "speed_boost",
        value: 1.25,
        desc: "移動速度+25%"
    },
    "黃忠": {
        bonus: "crit_rate",
        value: 0.3,
        desc: "暴擊率+30%"
    },
    "黃月英": {
        bonus: "skill_damage",
        value: 1.3,
        desc: "技能傷害+30%"
    }
};

// === 星級加成 ===
const STAR_BONUSES = [
    { stars: 1, hp_mult: 1.0, atk_mult: 1.0, speed_mult: 1.0, cost: 100 },
    { stars: 2, hp_mult: 1.1, atk_mult: 1.1, speed_mult: 1.05, cost: 200 },
    { stars: 3, hp_mult: 1.2, atk_mult: 1.2, speed_mult: 1.1, cost: 300 },
    { stars: 4, hp_mult: 1.35, atk_mult: 1.35, speed_mult: 1.15, cost: 500 },
    { stars: 5, hp_mult: 1.5, atk_mult: 1.5, speed_mult: 1.2, cost: 800 },
    { stars: 6, hp_mult: 1.7, atk_mult: 1.7, speed_mult: 1.25, cost: 1200 }
];

// === 等級曲線 ===
const LEVEL_CURVE = {
    1: 1.0, 5: 1.15, 10: 1.35, 15: 1.6, 20: 1.9,
    25: 2.25, 30: 2.65, 35: 3.1, 40: 3.6, 45: 4.15, 50: 4.75
};

// === 升級成本 ===
const LEVEL_UP_GOLD_COST = {
    1: 100, 2: 150, 3: 200, 4: 250, 5: 300,
    10: 500, 15: 750, 20: 1000, 25: 1500, 30: 2000, 50: 5000
};

// === 等級經驗表 ===
const LEVEL_EXP = {
    1: 100, 2: 150, 3: 200, 4: 250, 5: 300,
    10: 500, 15: 750, 20: 1000, 25: 1500, 30: 2000, 50: 5000
};

// === 升級星級成本 ===
const STAR_COST = {
    1: 10,  // 1星升2星需10碎片
    2: 15,  // 2星升3星需15碎片
    3: 20,  // 3星升4星需20碎片
    4: 25,  // 4星升5星需25碎片
    5: 30   // 5星升6星需30碎片
};

// === 顏色常數 ===
const COLORS = {
    WHITE: "#FFFFFF",
    BLACK: "#000000",
    BLUE: "#4A90E2",
    RED: "#E74C3C",
    GREEN: "#2ECC71",
    YELLOW: "#F39C12",
    GRAY: "#2C3E50",
    LIGHT_GRAY: "#ECF0F1",
    CREAM: "#F4E4C1",
    PURPLE: "#9B59B6",
    CYAN: "#1ABC9C",
    DARK_GOLD: "#D4AF37",
    BG_MAIN: "#1A1A2E",
    TEXT_MAIN: "#ECF0F1",
    ACCENT: "#FF6B6B"
};

// === 戰鬥場地邊界 ===
const ARENA = {
    MIN_X: 30,
    MAX_X: 970,
    MIN_Y: 65,
    MAX_Y: 540,
    PLAYER_MIN_Y: 300,
    PLAYER_MAX_Y: 540,
    ENEMY_MIN_Y: 65,
    ENEMY_MAX_Y: 300
};

// === 攻擊範圍 ===
const UNIT_ATTACK_RANGES = {
    0: 60,   // 槍兵
    1: 50,   // 騎兵
    2: 120   // 弓兵
};

// === 兵種相剋計算 ===
function getMultiplier(attacker, defender) {
    if ((attacker === 0 && defender === 1) ||
        (attacker === 1 && defender === 2) ||
        (attacker === 2 && defender === 0)) {
        return 1.2;
    }
    return 1.0;
}

// === 隨機加權選擇 ===
function chooseWeighted(options) {
    const total = options.reduce((sum, [_, weight]) => sum + weight, 0);
    let random = Math.random() * total;
    
    for (const [value, weight] of options) {
        random -= weight;
        if (random <= 0) {
            return value;
        }
    }
    
    return options[options.length - 1][0];
}

// === 戰鬥商店系統 ===
const SHOP_ITEMS = [
    { name: "迅速恢復藥", desc: "恢復150 HP", cost: 80, effect: "heal", value: 150, icon: "💊" },
    { name: "傷害藥劑", desc: "攻擊力+20%", cost: 120, effect: "atk_boost", value: 0.2, icon: "⚡", duration: 30 },
    { name: "防護符", desc: "傷害減免15%", cost: 100, effect: "def_boost", value: 0.15, icon: "🛡️", duration: 30 },
    { name: "速度靴", desc: "移動速度+30%", cost: 110, effect: "speed_boost", value: 0.3, icon: "👢", duration: 30 },
    { name: "中等恢復", desc: "恢復250 HP", cost: 150, effect: "heal", value: 250, icon: "💊" },
    { name: "強力合劑", desc: "HP+100, ATK+30%", cost: 200, effect: "super_potion", value: 100, icon: "🔥" },
];
