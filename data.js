// === 遊戲數據配置 ===

// 英雄池（6個英雄）
const HEROES = [
    {
        id: 1,
        name: "關羽",
        type: 0, // 槍兵
        rarity: "SR",
        baseHP: 120,
        baseATK: 28,
        baseSpeed: 3,
        specialization: {
            bonus: "skill_cooldown",
            value: 0.8,
            desc: "技能冷卻-20%"
        },
        icon: "🔱",
        color: "#E74C3C"
    },
    {
        id: 2,
        name: "張飛",
        type: 0,
        rarity: "SR",
        baseHP: 150,
        baseATK: 25,
        baseSpeed: 2.5,
        specialization: {
            bonus: "hp_recovery",
            value: 0.1,
            desc: "戰鬥中每秒回復最大HP的10%"
        },
        icon: "🔱",
        color: "#E74C3C"
    },
    {
        id: 3,
        name: "趙雲",
        type: 1, // 騎兵
        rarity: "SSR",
        baseHP: 110,
        baseATK: 32,
        baseSpeed: 3.5,
        specialization: {
            bonus: "damage_boost",
            value: 1.15,
            desc: "攻擊力+15%"
        },
        icon: "🐎",
        color: "#F39C12"
    },
    {
        id: 4,
        name: "馬超",
        type: 1,
        rarity: "SR",
        baseHP: 100,
        baseATK: 30,
        baseSpeed: 4,
        specialization: {
            bonus: "speed_boost",
            value: 1.25,
            desc: "移動速度+25%"
        },
        icon: "🐎",
        color: "#F39C12"
    },
    {
        id: 5,
        name: "黃忠",
        type: 2, // 弓兵
        rarity: "SSR",
        baseHP: 80,
        baseATK: 36,
        baseSpeed: 2.5,
        specialization: {
            bonus: "crit_rate",
            value: 0.3,
            desc: "暴擊率+30%"
        },
        icon: "🏹",
        color: "#2ECC71"
    },
    {
        id: 6,
        name: "黃月英",
        type: 2,
        rarity: "R",
        baseHP: 75,
        baseATK: 28,
        baseSpeed: 3,
        specialization: {
            bonus: "skill_damage",
            value: 1.3,
            desc: "技能傷害+30%"
        },
        icon: "🏹",
        color: "#2ECC71"
    }
];

// 兵種技能配置
const UNIT_SKILLS = {
    0: { // 槍兵
        name: "貫穿突刺",
        desc: "對前方敵人造成150%傷害+25%概率眩暈",
        cooldown: 4.0,
        damage_mult: 1.5,
        range: 60,
        effect: "pierce",
        stun_chance: 0.25
    },
    1: { // 騎兵
        name: "衝鋒突擊",
        desc: "衝向敵人造成180%傷害並減速50%，自身恢復25% HP",
        cooldown: 5.0,
        damage_mult: 1.8,
        range: 80,
        effect: "charge",
        self_heal: 0.25
    },
    2: { // 弓兵
        name: "連射覆蓋",
        desc: "向範圍內射出3支箭，每支造成120%傷害，目標減速",
        cooldown: 3.5,
        damage_mult: 1.2,
        arrow_count: 3,
        range: 100,
        effect: "volley",
        slow_amount: 0.4
    }
};

// 兵種配置
const UNIT_CONFIG = {
    0: { // 槍兵
        name: "槍兵",
        attackRange: 60,
        icon: "🔱",
        color: "#E74C3C"
    },
    1: { // 騎兵
        name: "騎兵",
        attackRange: 50,
        icon: "🐎",
        color: "#F39C12"
    },
    2: { // 弓兵
        name: "弓兵",
        attackRange: 120,
        icon: "🏹",
        color: "#2ECC71"
    }
};

// 兵種相剋
function getMultiplier(attacker, defender) {
    if ((attacker === 0 && defender === 1) || 
        (attacker === 1 && defender === 2) || 
        (attacker === 2 && defender === 0)) {
        return 1.2; // 克制時傷害+20%
    }
    return 1.0;
}

// 稀有度顏色
const RARITY_COLORS = {
    "C": "#95A5A6",
    "R": "#3498DB",
    "SR": "#F39C12",
    "SSR": "#E74C3C"
};

// 星級加成
const STAR_BONUSES = [
    { stars: 1, hp_mult: 1.0, atk_mult: 1.0, speed_mult: 1.0 },
    { stars: 2, hp_mult: 1.1, atk_mult: 1.1, speed_mult: 1.05 },
    { stars: 3, hp_mult: 1.2, atk_mult: 1.2, speed_mult: 1.1 },
    { stars: 4, hp_mult: 1.35, atk_mult: 1.35, speed_mult: 1.15 },
    { stars: 5, hp_mult: 1.5, atk_mult: 1.5, speed_mult: 1.2 },
    { stars: 6, hp_mult: 1.7, atk_mult: 1.7, speed_mult: 1.25 }
];

// 等級曲線（影響屬性加成）
const LEVEL_CURVE = {
    1: 1.0, 5: 1.15, 10: 1.35, 15: 1.6, 20: 1.9,
    25: 2.25, 30: 2.65, 35: 3.1, 40: 3.6, 45: 4.15, 50: 4.75
};

// 關卡配置
const CHAPTERS = [
    { id: 1, name: "第1章：黃巾之亂", waves: 5, maxHp: 800 },
    { id: 2, name: "第2章：群雄割據", waves: 8, maxHp: 1200 },
    { id: 3, name: "第3章：官渡之戰", waves: 10, maxHp: 1600 },
    { id: 4, name: "第4章：赤壁之戰", waves: 12, maxHp: 2000 }
];

// 敵人配置
const ENEMY_POOL = [
    { name: "黃巾賊", type: 0, hp: 80, atk: 15, speed: 2.5 },
    { name: "黃巾弓手", type: 2, hp: 60, atk: 18, speed: 2 },
    { name: "黃巾騎士", type: 1, hp: 70, atk: 17, speed: 3 },
    { name: "董卓兵", type: 0, hp: 100, atk: 20, speed: 2.8 },
    { name: "呂布侍衛", type: 1, hp: 120, atk: 25, speed: 3.5 }
];

// 顏色常數
const COLORS = {
    WHITE: "#FFFFFF",
    BLACK: "#000000",
    BLUE: "#4A90E2",
    RED: "#E74C3C",
    GREEN: "#2ECC71",
    YELLOW: "#F39C12",
    GRAY: "#2C3E50",
    LIGHT_GRAY: "#ECF0F1",
    PURPLE: "#9B59B6",
    CYAN: "#1ABC9C",
    DARK_GOLD: "#D4AF37",
    BG_MAIN: "#1A1A2E",
    TEXT_MAIN: "#ECF0F1"
};

// 遊戲場地邊界
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
