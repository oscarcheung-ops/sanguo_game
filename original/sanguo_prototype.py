import tkinter as tk
from tkinter import Canvas, messagebox
import random
import math
import time
import os
import json
import uuid

# progression curves
from config import LEVEL_CURVE, STAR_COST, LEVEL_EXP, LEVEL_UP_GOLD_COST

# 顏色 - 美麗的手繪風格配色
WHITE = "#FFFFFF"
BLACK = "#000000"
BLUE = "#4A90E2"  # 溫和的藍色
RED = "#E74C3C"  # 溫暖的紅色
GREEN = "#2ECC71"  # 生機勃勃的綠色
YELLOW = "#F39C12"  # 金黃色
GRAY = "#2C3E50"  # 深灰色（主背景）
LIGHT_GRAY = "#ECF0F1"  # 淺灰色
CREAM = "#F4E4C1"  # 米色（卡片背景）
PURPLE = "#9B59B6"  # 紫色
CYAN = "#1ABC9C"  # 青綠色
DARK_GOLD = "#D4AF37"  # 暗金色（強調）
BG_MAIN = "#1A1A2E"  # 深藍黑色背景
TEXT_MAIN = "#ECF0F1"  # 淺色文字
ACCENT = "#FF6B6B"  # 強調色

# 戰鬥場地邊界
ARENa_MIN_X = 30
ARENa_MAX_X = 970
ARENa_MIN_Y = 65
ARENa_MAX_Y = 540
ARENa_PLAYER_MIN_Y = 300  # 玩家隊伍下方區域
ARENa_PLAYER_MAX_Y = 540
ARENa_ENEMY_MIN_Y = 65
ARENa_ENEMY_MAX_Y = 300   # 敵人隊伍上方區域

# 兵種：0=槍, 1=騎, 2=弓
# 攻击范围：枪兵60、骑兵50、弓兵120
UNIT_ATTACK_RANGES = {
    0: 60,   # 槍兵：中等范围
    1: 50,   # 騎兵：短范围
    2: 120   # 弓兵：长范围
}

def get_multiplier(attacker, defender):
    if (attacker == 0 and defender == 1) or (attacker == 1 and defender == 2) or (attacker == 2 and defender == 0):
        return 1.2
    return 1.0

def get_attack_range(unit_type):
    """获取兵种的攻击范围"""
    return UNIT_ATTACK_RANGES.get(unit_type, 60)

class Unit:
    def __init__(self, name, x, y, team, unit_type, hp=100, atk=20, speed=3, siege_atk=None):
        self.name = name
        self.pos = [x, y]
        self.team = team  # 0=玩家, 1=敵人
        self.type = unit_type
        self.hp = hp
        self.max_hp = hp
        self.atk = atk
        self.speed = speed
        self.siege_atk = siege_atk if siege_atk is not None else atk  # 攻城傷害 (預設等於普通攻擊)
        self.target_pos = None
        self.target_enemy = None
        self.selected = False
        
        # 状态效果
        self.stunned = False  # 击晕状态
        self.slow_factor = 1.0  # 减速倍数
        self.speed_recover_time = 0  # 减速恢复时间
        
        # 技能系统
        self.skill = UNIT_SKILLS.get(unit_type, {}).copy() if unit_type in UNIT_SKILLS else {}
        self.skill_cooldown = 0.0  # 当前冷却时间
        self.skill_ready = True
        
        # 专精系统
        self.specialization = HERO_SPECIALIZATION.get(name, {})
        self.apply_specialization()
    
    def apply_specialization(self):
        """应用英雄专精效果"""
        if not self.specialization:
            return
        
        bonus_type = self.specialization.get("bonus")
        bonus_value = self.specialization.get("value", 1.0)
        
        if bonus_type == "damage_boost":
            self.atk = int(self.atk * bonus_value)
        elif bonus_type == "speed_boost":
            self.speed = self.speed * bonus_value
        elif bonus_type == "crit_rate":
            # 存储到unit自身，后续在damage计算时使用
            self.crit_rate = bonus_value
        elif bonus_type == "skill_cooldown":
            if self.skill:
                self.skill["cooldown"] = self.skill.get("cooldown", 4.0) * bonus_value
        elif bonus_type == "skill_damage":
            if self.skill:
                self.skill["damage_mult"] = self.skill.get("damage_mult", 1.5) * bonus_value
        elif bonus_type == "hp_recovery":
            self.hp_recovery_rate = bonus_value

    def update(self, units, castles, game_window=None):
        # 更新技能冷却
        if self.skill_cooldown > 0:
            self.skill_cooldown -= 0.016  # 16ms per frame
            if self.skill_cooldown <= 0:
                self.skill_cooldown = 0
                self.skill_ready = True
        
        # 更新击晕状态（击晕只持续1秒）
        if self.stunned:
            self.speed_recover_time -= 0.016
            if self.speed_recover_time <= 0:
                self.stunned = False
                self.target_pos = None  # 清除目标，重新选择
        
        # 更新减速状态（逐步恢复速度）
        if self.slow_factor < 1.0:
            self.speed_recover_time -= 0.016
            if self.speed_recover_time <= 0:
                self.slow_factor = 1.0
        
        # 如果被击晕，不能移动和攻击
        if self.stunned:
            return 0
        
        # 移動（应用减速倍数）
        current_speed = self.speed * self.slow_factor
        # 允許自由移動：不論是否有敵人目標，只要有target_pos就移動
        if self.target_pos:
            dx = self.target_pos[0] - self.pos[0]
            dy = self.target_pos[1] - self.pos[1]
            dist = math.hypot(dx, dy)
            if dist > current_speed:
                self.pos[0] += dx / dist * current_speed
                self.pos[1] += dy / dist * current_speed
            else:
                self.target_pos = None
        
        # 限制在戰鬥場地內（完全移除隊伍區域限制，雙方可自由移動到全場）
        # X軸範圍: 30-970, Y軸範圍: 65-540（中線在y=300，完全可以跨越）
        self.pos[0] = max(ARENa_MIN_X, min(ARENa_MAX_X, self.pos[0]))
        self.pos[1] = max(ARENa_MIN_Y, min(ARENa_MAX_Y, self.pos[1]))
        # 找敵人（只在未指定攻擊目標時自動選擇）
        if not self.target_enemy or self.target_enemy.hp <= 0:
            # 所有單位都自動選擇最近的敵人
            enemies = [u for u in units if u.team != self.team and u.hp > 0]
            if enemies:
                self.target_enemy = min(enemies, key=lambda e: math.dist(self.pos, e.pos))
            else:
                # 沒敵人就清除目標，讓攻城邏輯接管
                self.target_enemy = None
        
        # 單位站在原地，只有以下情況才移動：
        # 1. 玩家手動設置 target_pos（玩家操作或自動戰鬥模式）
        # 不會自動靠近敵人，除非玩家主動移動隊伍
        # 當有目標敵人但超出攻擊範圍時，靜止等待
        # 這樣敵人會站在原地，直到玩家靠近
        
        # HP恢复（张飞专精）
        if hasattr(self, 'hp_recovery_rate') and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.max_hp * self.hp_recovery_rate * 0.016)

        # 攻擊和技能（允许边移动边攻击）
        if self.target_enemy and self.target_enemy.hp > 0:
            dist = math.dist(self.pos, self.target_enemy.pos)
            attack_range = get_attack_range(self.type)
            
            # 尝试释放技能
            if self.skill and self.skill_ready and dist < self.skill.get("range", attack_range):
                self.activate_skill(self.target_enemy, units, game_window)
                return 0
            
            # 普通攻击（在攻击范围内）
            if dist < attack_range:
                multiplier = get_multiplier(self.type, self.target_enemy.type)
                damage = self.atk * multiplier
                
                # 应用英雄暴击率（黄忠专精）
                if hasattr(self, 'crit_rate') and random.random() < self.crit_rate:
                    damage *= 1.5
                
                # 应用玩家方Roguelite效果
                if self.team == 0 and game_window:
                    # 暴击判定
                    if random.random() < game_window.crit_chance:
                        damage *= 1.5
                    # 生命偷取
                    if game_window.lifesteal_rate > 0 and hasattr(game_window, 'player_castle'):
                        heal_amount = damage * game_window.lifesteal_rate
                        game_window.player_castle.hp = min(game_window.player_castle.max_hp, 
                                                         game_window.player_castle.hp + heal_amount)
                
                # 应用目标方伤害减免
                if self.target_enemy.team == 0 and game_window:
                    if game_window.damage_reduction > 0:
                        damage *= (1 - game_window.damage_reduction)
                
                self.target_enemy.hp -= damage
                
                # 显示类型优势反馈（SanZhenZhi 风格）
                if game_window:
                    if multiplier > 1.0:
                        game_window.damage_texts.append((self.target_enemy.pos[:], "⭐克制!", 60))
                    elif multiplier < 1.0:
                        game_window.damage_texts.append((self.target_enemy.pos[:], "✗劣势", 60))
                return int(damage)
        return 0
    
    def activate_skill(self, target, units, game_window):
        """激活单位技能"""
        if not self.skill:
            return
        
        skill = self.skill
        damage = self.atk * skill.get("damage_mult", 1.5) * get_multiplier(self.type, target.type)
        
        # 应用技能伤害加成（黄月英专精）
        if hasattr(self, 'specialization') and self.specialization.get("bonus") == "skill_damage":
            # 伤害已经在apply_specialization中应用到skill["damage_mult"]
            pass
        
        effect = skill.get("effect")
        
        if effect == "pierce":  # 槍兵：贯穿突刺 - 有概率击晕
            target.hp -= damage
            # 击晕效果 (25%概率，持续1秒)
            if random.random() < 0.25:
                target.stunned = True
                target.speed_recover_time = 1.0
                if game_window:
                    game_window.damage_texts.append((target.pos[:], "击晕!", 60))
            if game_window:
                game_window.damage_texts.append((target.pos[:], int(damage), 30))
                game_window.particles.append(Particle(target.pos[0], target.pos[1], YELLOW, life=1.0, vx=0, vy=-40))
        
        elif effect == "charge":  # 騎兵：冲锋突击 - 减速目标，自身恢复
            target.hp -= damage
            # 减速目标50% (持续2秒)
            target.slow_factor = 0.5
            target.speed_recover_time = 2.0
            # 自身恢复25% HP
            self.hp = min(self.max_hp, self.hp + self.max_hp * 0.25)
            if game_window:
                game_window.damage_texts.append((target.pos[:], int(damage), 30))
                game_window.particles.append(Particle(target.pos[0], target.pos[1], WHITE, life=1.0, vx=0, vy=-40))
        
        elif effect == "volley":  # 弓兵：连射覆盖 - 多目标减速
            # 命中范围内的多个敌人
            arrow_count = skill.get("arrow_count", 3)
            nearby_enemies = [u for u in units if u.team != self.team and u.hp > 0 
                             and math.dist(u.pos, target.pos) < skill.get("range", 100)]
            for i, enemy in enumerate(nearby_enemies[:arrow_count]):
                arrow_damage = damage * 0.8  # 每支箭伤害降低
                enemy.hp -= arrow_damage
                # 减速效果 (40%减速，持续1.5秒)
                enemy.slow_factor = 0.6
                enemy.speed_recover_time = 1.5
                if game_window:
                    game_window.damage_texts.append((enemy.pos[:], int(arrow_damage), 30))
                    game_window.particles.append(Particle(enemy.pos[0], enemy.pos[1], CYAN, life=1.0, vx=0, vy=-40))
        
        # 启动技能冷却
        cooldown = skill.get("cooldown", 4.0)
        # 应用关羽冷却减免
        if hasattr(self, 'specialization') and self.specialization.get("bonus") == "skill_cooldown":
            cooldown = cooldown * self.specialization.get("value", 0.8)
        
        self.skill_cooldown = cooldown
        self.skill_ready = False

    def draw(self, canvas):
        color = BLUE if self.team == 0 else RED
        # 畫單位
        canvas.create_oval(
            int(self.pos[0])-25, int(self.pos[1])-25,
            int(self.pos[0])+25, int(self.pos[1])+25,
            fill=color, outline=WHITE, width=2
        )
        
        # 兵种图标
        unit_icons = {0: "🔱", 1: "🐎", 2: "🏹"}  # 枪、骑、弓
        icon = unit_icons.get(self.type, "⚔")
        canvas.create_text(self.pos[0], self.pos[1], text=icon, 
                          fill=WHITE, font=("Arial", 16))
        
        # 血條背景
        canvas.create_rectangle(
            self.pos[0]-25, self.pos[1]-40,
            self.pos[0]+25, self.pos[1]-32,
            fill=RED, outline=WHITE
        )
        # 血條
        hp_width = 50 * (self.hp / self.max_hp)
        canvas.create_rectangle(
            self.pos[0]-25, self.pos[1]-40,
            self.pos[0]-25 + hp_width, self.pos[1]-32,
            fill=GREEN, outline=GREEN
        )
        # 名稱
        canvas.create_text(self.pos[0], self.pos[1]+40, text=self.name, fill=WHITE, font=("Arial", 9))
        
        # 状态指示器
        status_text = ""
        status_color = WHITE
        if self.stunned:
            status_text = "💫击晕"
            status_color = YELLOW
        elif self.slow_factor < 1.0:
            status_text = f"⬇减速{int((1-self.slow_factor)*100)}%"
            status_color = CYAN
        
        if status_text:
            canvas.create_text(self.pos[0], self.pos[1]+52, text=status_text, fill=status_color, font=("Arial", 8))
        
        # 技能冷却指示
        if self.skill and not self.skill_ready:
            cooldown_pct = self.skill_cooldown / self.skill.get("cooldown", 4.0)
            cooldown_width = 50 * (1 - cooldown_pct)  # 从满到空
            # 冷却条（在血条下方）
            canvas.create_rectangle(
                self.pos[0]-25, self.pos[1]-28,
                self.pos[0]+25, self.pos[1]-24,
                fill="#333", outline="white", width=1
            )
            canvas.create_rectangle(
                self.pos[0]-25, self.pos[1]-28,
                self.pos[0]-25 + cooldown_width, self.pos[1]-24,
                fill="#FF9900", outline=""
            )
        elif self.skill and self.skill_ready:
            # 技能就绪指示
            canvas.create_rectangle(
                self.pos[0]-25, self.pos[1]-28,
                self.pos[0]+25, self.pos[1]-24,
                fill="#00FF00", outline="#00FF00", width=1
            )
        
        # 選中框
        if self.selected:
            canvas.create_oval(
                int(self.pos[0])-30, int(self.pos[1])-30,
                int(self.pos[0])+30, int(self.pos[1])+30,
                outline=YELLOW, width=3
            )

class Castle:
    def __init__(self, x, y, team, is_boss=False):
        self.pos = [x, y]
        self.team = team
        self.hp = 500
        self.max_hp = 500
        self.is_boss = is_boss
        self.boss_phase = 1  # Boss所在阶段 (1-3)
        self.boss_phase_hp = [500, 350, 200] if is_boss else [500]  # 各阶段HP上限
        
        if is_boss:
            self.hp = 1500  # Boss总HP为三个阶段之和
            self.max_hp = 1500

    def draw(self, canvas):
        # 颜色和标识
        if self.is_boss:
            color = "#9B59B6"  # Boss紫色
            icon = "👑"
        else:
            color = GREEN if self.team == 0 else RED
            icon = "🏰"
        
        # 城堡主体
        canvas.create_rectangle(
            self.pos[0]-60, self.pos[1]-40,
            self.pos[0]+60, self.pos[1]+40,
            fill=color, outline=DARK_GOLD, width=3
        )
        
        # 城堡图标
        canvas.create_text(self.pos[0], self.pos[1], text=icon, 
                          fill=WHITE, font=("Arial", 24))
        
        # 血條背景
        canvas.create_rectangle(
            self.pos[0]-60, self.pos[1]-50,
            self.pos[0]+60, self.pos[1]-42,
            fill="#2C3E50", outline=WHITE, width=2
        )
        # 血條
        hp_width = 120 * (self.hp / self.max_hp)
        hp_color = GREEN if self.hp > self.max_hp * 0.5 else (YELLOW if self.hp > self.max_hp * 0.2 else RED)
        canvas.create_rectangle(
            self.pos[0]-60, self.pos[1]-50,
            self.pos[0]-60 + hp_width, self.pos[1]-42,
            fill=hp_color, outline=""
        )
        
        # Boss标签
        if self.is_boss:
            canvas.create_text(self.pos[0], self.pos[1]+55, text=f"💀 BOSS 第{self.boss_phase}階段 💀", 
                              fill=ACCENT, font=("Arial", 11, "bold"))
        else:
            label = "🛡 友軍城堡" if self.team == 0 else "⚔ 敵軍城堡"
            canvas.create_text(self.pos[0], self.pos[1]+55, text=label, 
                              fill=CYAN if self.team == 0 else ACCENT, font=("Arial", 11, "bold"))
    
    def update_boss_phase(self):
        """更新Boss所在阶段"""
        if not self.is_boss:
            return
        
        total_hp = 1500
        if self.hp > 1000:  # 1500-1000
            self.boss_phase = 1
        elif self.hp > 500:  # 1000-500
            if self.boss_phase == 1:
                self.boss_phase = 2
                self.trigger_phase_transition()
        else:  # 500-0
            if self.boss_phase == 2:
                self.boss_phase = 3
                self.trigger_phase_transition()
    
    def trigger_phase_transition(self):
        """触发阶段转换效果"""
        # 可以在这里添加特殊效果，如全屏闪光、特殊攻击等
        pass

# --- New: Meta, Card and Player Data ---

RARITY_ORDER = ["C", "R", "SR", "SSR"]
RARITY_COLOR = {
    "C": "#B0B0B0",
    "R": "#4AA3FF",
    "SR": "#B26BFF",
    "SSR": "#FFA500",
}

HERO_POOL = [
    {"name": "關羽", "type": 0, "base_hp": 130, "base_atk": 22, "base_speed": 3},
    {"name": "張飛", "type": 0, "base_hp": 140, "base_atk": 21, "base_speed": 2.8},
    {"name": "趙雲", "type": 1, "base_hp": 115, "base_atk": 24, "base_speed": 3.4},
    {"name": "馬超", "type": 1, "base_hp": 120, "base_atk": 23, "base_speed": 3.5},
    {"name": "黃忠", "type": 2, "base_hp": 100, "base_atk": 26, "base_speed": 3},
    {"name": "黃月英", "type": 2, "base_hp": 105, "base_atk": 24, "base_speed": 3}
]

RARITY_WEIGHTS = [("SSR", 1), ("SR", 9), ("R", 30), ("C", 60)]

# --- 关卡系统 ---
CHAPTER_CONFIGS = [
    {"chapter": 1, "name": "初出茅庐", "waves": 8, "base_hp": 80, "base_atk": 15, "level": 1, "has_boss": False},
    {"chapter": 2, "name": "崭露头角", "waves": 9, "base_hp": 120, "base_atk": 20, "level": 5, "has_boss": False},
    {"chapter": 3, "name": "中原逐鹿", "waves": 10, "base_hp": 160, "base_atk": 26, "level": 10, "has_boss": True},
]

# --- Boss 系统 ---
BOSS_CONFIG = {
    "name": "黄巾贼首",
    "hp": 1500,  # 三个阶段总HP
    "phase_hp": [500, 350, 200],  # 每阶段HP
    "base_atk": 35,
    "abilities": [
        {
            "phase": 1,
            "name": "普通攻击",
            "damage": 1.0,
            "cooldown": 2.0,
            "effect": "single"  # 单体攻击
        },
        {
            "phase": 2,
            "name": "旋风斩",
            "damage": 2.0,
            "cooldown": 3.0,
            "effect": "aoe",  # 范围攻击
            "range": 150
        },
        {
            "phase": 3,
            "name": "绝命一击",
            "damage": 3.0,
            "cooldown": 4.0,
            "effect": "execute",  # 可能秒杀低血量单位
            "threshold": 0.3  # 血量低于30%时生效
        }
    ]
}

WAVE_EVENTS = [
    {"name": "补给", "desc": "所有单位恢复25% HP", "effect": "heal", "type": "buff", "color": GREEN},
    {"name": "陷阱", "desc": "敌方下波的攻击降低20%", "effect": "curse", "type": "buff", "color": GREEN},
    {"name": "增援", "desc": "下波敌人减少1个", "effect": "fewer_enemies", "type": "buff", "color": GREEN},
    {"name": "暴雨", "desc": "所有单位速度降低30%", "effect": "slow", "type": "curse", "color": RED},
]

# Roguelite Buff池
ROGUELITE_BUFFS = [
    {"name": "攻速+30%", "desc": "攻击速度提升30%", "effect": "atk_speed", "type": "buff", "color": "#FF6B6B"},
    {"name": "暴击+25%", "desc": "暴击率提升25%（伤害翻倍）", "effect": "crit", "type": "buff", "color": "#FFD700"},
    {"name": "移速+40%", "desc": "单位移动速度提升40%", "effect": "move_speed", "type": "buff", "color": "#4169FF"},
    {"name": "吸血+15%", "desc": "造成伤害时恢复15%血量", "effect": "lifesteal", "type": "buff", "color": "#FF1493"},
    {"name": "护甲+25%", "desc": "受伤减少25%", "effect": "armor", "type": "buff", "color": "#708090"},
    {"name": "技能冷却-40%", "desc": "技能冷却时间减少40%", "effect": "cooldown", "type": "buff", "color": "#9370DB"},
]

# Roguelite 诅咒
ROGUELITE_CURSES = [
    {"name": "诅咒：衰弱", "desc": "攻击力降低30%", "effect": "weakness", "type": "curse", "color": "#8B0000"},
    {"name": "诅咒：迟缓", "desc": "移动速度降低50%", "effect": "curse_slow", "type": "curse", "color": "#4B0082"},
    {"name": "诅咒：脆弱", "desc": "受伤增加40%", "effect": "curse_fragile", "type": "curse", "color": "#FF4500"},
]

# Roguelite 交易选项
ROGUELITE_TRADE = [
    {"name": "血契", "desc": "花费100金币，获得2个随机Buff", "effect": "trade_double_buff", "type": "trade", "cost": 100, "color": "#FF1493"},
    {"name": "商人", "desc": "花费80金币，移除1个诅咒", "effect": "trade_remove_curse", "type": "trade", "cost": 80, "color": "#20B2AA"},
    {"name": "赌徒", "desc": "花费50金币，随机获得Buff或诅咒", "effect": "trade_gamble", "type": "trade", "cost": 50, "color": "#FFB6C1"},
]

# --- 战斗商店系统 ---
SHOP_ITEMS = [
    {"name": "迅速恢复药", "desc": "恢复150 HP", "cost": 80, "effect": "heal", "value": 150, "icon": "💊"},
    {"name": "伤害药剂", "desc": "攻击力+20%", "cost": 120, "effect": "atk_boost", "value": 0.2, "icon": "⚡", "duration": 30},
    {"name": "防护符", "desc": "伤害减免15%", "cost": 100, "effect": "def_boost", "value": 0.15, "icon": "🛡️", "duration": 30},
    {"name": "速度靴", "desc": "移动速度+30%", "cost": 110, "effect": "speed_boost", "value": 0.3, "icon": "👢", "duration": 30},
    {"name": "中等恢复", "desc": "恢复250 HP", "cost": 150, "effect": "heal", "value": 250, "icon": "💊"},
    {"name": "强力合剂", "desc": "HP+100, ATK+30%", "cost": 200, "effect": "super_potion", "value": 100, "icon": "🔥"},
]

# --- 每日任务系统 ---
DAILY_QUESTS = [
    {"id": "daily_1", "name": "新手入门", "desc": "通关任意关卡1次", "reward_gold": 100, "reward_gems": 10, "type": "daily", "progress": 0, "target": 1},
    {"id": "daily_2", "name": "冠军战士", "desc": "通关关卡3次", "reward_gold": 200, "reward_gems": 20, "type": "daily", "progress": 0, "target": 3},
    {"id": "daily_3", "name": "升级狂魔", "desc": "升级武将2次", "reward_gold": 150, "reward_gems": 15, "type": "daily", "progress": 0, "target": 2},
    {"id": "daily_4", "name": "装备收集者", "desc": "装备4件装备", "reward_gold": 120, "reward_gems": 25, "type": "daily", "progress": 0, "target": 4},
    {"id": "daily_5", "name": "抽卡狂人", "desc": "进行抽卡1次", "reward_gold": 80, "reward_gems": 30, "type": "daily", "progress": 0, "target": 1},
]

WEEKLY_QUESTS = [
    {"id": "weekly_1", "name": "周赛冠军", "desc": "通关关卡10次", "reward_gold": 500, "reward_gems": 100, "type": "weekly", "progress": 0, "target": 10},
    {"id": "weekly_2", "name": "升级大师", "desc": "升级武将5次", "reward_gold": 400, "reward_gems": 80, "type": "weekly", "progress": 0, "target": 5},
    {"id": "weekly_3", "name": "Boss猎人", "desc": "击败Boss 2次", "reward_gold": 600, "reward_gems": 120, "type": "weekly", "progress": 0, "target": 2},
]


# --- 计略系统（三国志大战的核心） ---
# 兵种计略 (0=槍, 1=騎, 2=弓)
UNIT_SKILLS = {
    0: {  # 槍兵计略
        "name": "贯穿突刺",
        "desc": "对前方敌人造成150%伤害+25%概率击晕",
        "cooldown": 4.0,
        "damage_mult": 1.5,
        "range": 60,
        "effect": "pierce",
        "special": "stun_chance:0.25"
    },
    1: {  # 騎兵计略
        "name": "冲锋突击",
        "desc": "冲向敌人造成180%伤害并减速50%，自身恢复25% HP",
        "cooldown": 5.0,
        "damage_mult": 1.8,
        "range": 80,
        "effect": "charge",
        "special": "self_heal:0.25"
    },
    2: {  # 弓兵计略
        "name": "连射覆盖",
        "desc": "向范围内射出3支箭，每支造成120%伤害，目标减速",
        "cooldown": 3.5,
        "damage_mult": 1.2,
        "arrow_count": 3,
        "range": 100,
        "effect": "volley",
        "special": "slow:0.4"
    }
}

# 英雄专精（基于英雄名字的特殊能力）
HERO_SPECIALIZATION = {
    "關羽": {"bonus": "skill_cooldown", "value": 0.8, "desc": "技能冷却-20%"},
    "張飛": {"bonus": "hp_recovery", "value": 0.1, "desc": "战斗中每秒回复最大HP的10%"},
    "趙雲": {"bonus": "damage_boost", "value": 1.15, "desc": "攻击力+15%"},
    "馬超": {"bonus": "speed_boost", "value": 1.25, "desc": "移动速度+25%"},
    "黃忠": {"bonus": "crit_rate", "value": 0.3, "desc": "暴击率+30%"},
    "黃月英": {"bonus": "skill_damage", "value": 1.3, "desc": "技能伤害+30%"},
}

# --- 装备和星级系统 ---
# 装备类型
EQUIPMENT_TYPES = {
    "weapon": {"name": "武器", "stat": "atk", "rarity_bonus": {"C": 5, "R": 8, "SR": 12, "SSR": 18}},
    "armor": {"name": "护甲", "stat": "def", "rarity_bonus": {"C": 3, "R": 5, "SR": 8, "SSR": 12}},
    "accessory": {"name": "饰品", "stat": "hp", "rarity_bonus": {"C": 15, "R": 25, "SR": 40, "SSR": 60}},
}

# 星级加成
STAR_BONUSES = [
    {"stars": 1, "hp_mult": 1.0, "atk_mult": 1.0, "speed_mult": 1.0, "cost": 100},
    {"stars": 2, "hp_mult": 1.1, "atk_mult": 1.1, "speed_mult": 1.05, "cost": 200},
    {"stars": 3, "hp_mult": 1.2, "atk_mult": 1.2, "speed_mult": 1.1, "cost": 300},
    {"stars": 4, "hp_mult": 1.35, "atk_mult": 1.35, "speed_mult": 1.15, "cost": 500},
    {"stars": 5, "hp_mult": 1.5, "atk_mult": 1.5, "speed_mult": 1.2, "cost": 800},
    {"stars": 6, "hp_mult": 1.7, "atk_mult": 1.7, "speed_mult": 1.25, "cost": 1200},
]

# --- Item 9: 粒子效果系统 ---
class Particle:
    def __init__(self, x, y, color, life=1.0, vx=0, vy=0):
        self.x = x
        self.y = y
        self.color = color
        self.life = life  # 生命周期（秒）
        self.max_life = life
        self.vx = vx  # X速度
        self.vy = vy  # Y速度
    
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
    
    def draw(self, canvas, alpha=255):
        # Tkinter doesn't support transparency, so we draw with outline fading
        canvas.create_oval(
            int(self.x) - 3, int(self.y) - 3,
            int(self.x) + 3, int(self.y) + 3,
            fill=self.color, outline=self.color
        )

# --- Item 10: 教程系统 ---
TUTORIAL_TIPS = [
    {"step": 1, "title": "欢迎来到三国战争！", "msg": "点击【開始戰鬥】开始你的冒险！"},
    {"step": 2, "title": "队伍编成", "msg": "在【編成隊伍】中选择3名武将组成你的队伍"},
    {"step": 3, "title": "升级武将", "msg": "使用【養成升級】提升武将的等级和星级"},
    {"step": 4, "title": "抽卡获取", "msg": "在【抽卡】中消费钻石获取新的武将"},
    {"step": 5, "title": "完成任务", "msg": "每天完成任务获取金币和钻石奖励"},
]

# --- Item 12: 好友助战系统 ---
FRIEND_ASSIST_UNITS = [
    {"name": "友军-關羽", "type": 0, "base_hp": 150, "base_atk": 28, "base_speed": 3.2},
    {"name": "友军-趙雲", "type": 1, "base_hp": 130, "base_atk": 30, "base_speed": 3.5},
    {"name": "友军-黃忠", "type": 2, "base_hp": 100, "base_atk": 35, "base_speed": 3},
]

def choose_weighted(options):
    total = sum(w for _, w in options)
    r = random.uniform(0, total)
    upto = 0
    for val, w in options:
        if upto + w >= r:
            return val
        upto += w
    return options[-1][0]


class Card:
    def __init__(self, name, unit_type, rarity, level=1, cid=None, base_hp=100, base_atk=20, base_speed=3,
                 stars=1, exp=0, shards=0, equipment=None):
        self.id = cid or str(uuid.uuid4())
        self.name = name
        self.unit_type = unit_type
        self.rarity = rarity  # C/R/SR/SSR
        self.level = min(max(level, 1), 50)
        self.exp = exp  # 當前經驗
        self.base_hp = base_hp
        self.base_atk = base_atk
        self.base_speed = base_speed
        self.stars = max(1, min(stars, 5))  # 1-5星
        self.shards = shards  # 同名碎片
        # 裝備槽：weapon/horse/book，兼容舊數據
        self.equipment = equipment or {}
        for slot in ["weapon", "horse", "book"]:
            self.equipment.setdefault(slot, None)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "unit_type": self.unit_type,
            "rarity": self.rarity,
            "level": self.level,
            "exp": self.exp,
            "base_hp": self.base_hp,
            "base_atk": self.base_atk,
            "base_speed": self.base_speed,
            "stars": self.stars,
            "shards": self.shards,
            "equipment": self.equipment,
        }

    @staticmethod
    def from_dict(d):
        card = Card(
            name=d["name"], unit_type=d["unit_type"], rarity=d["rarity"], level=d.get("level", 1),
            cid=d.get("id"), base_hp=d.get("base_hp", 100), base_atk=d.get("base_atk", 20), base_speed=d.get("base_speed", 3),
            stars=d.get("stars", 1), exp=d.get("exp", 0), shards=d.get("shards", 0), equipment=d.get("equipment", {})
        )
        # 兼容舊存檔：填滿裝備槽
        for slot in ["weapon", "horse", "book"]:
            card.equipment.setdefault(slot, None)
        return card

    def stats(self):
        """計算卡牌的最終屬性（含等級/星級/裝備）"""
        # 基礎稀有度加成
        rarity_mult = {"C": 1.0, "R": 1.1, "SR": 1.25, "SSR": 1.45}.get(self.rarity, 1.0)

        # 等級曲線
        lv_mult = LEVEL_CURVE.get(self.level, LEVEL_CURVE[max(LEVEL_CURVE.keys())])
        max_hp = int(self.base_hp * rarity_mult * lv_mult)
        atk = int(self.base_atk * rarity_mult * lv_mult)
        speed = self.base_speed + min(2.0, (self.level - 1) * 0.05)

        # 星級加成
        star_idx = min(max(self.stars, 1), len(STAR_BONUSES)) - 1
        star_bonus = STAR_BONUSES[star_idx]
        max_hp = int(max_hp * star_bonus["hp_mult"])
        atk = int(atk * star_bonus["atk_mult"])
        speed = speed * star_bonus["speed_mult"]

        # 裝備加成
        from data import EQUIPMENT_CATALOG, EQUIPMENT_RARITY_COLOR
        equip_hp = 0
        equip_atk = 0
        equip_speed = 0
        
        for slot in ["weapon", "horse", "book"]:
            equip_id = self.equipment.get(slot)
            if not equip_id or equip_id == "None":
                continue
            
            # Find equipment in catalog
            if slot in EQUIPMENT_CATALOG:
                equip_data = next((e for e in EQUIPMENT_CATALOG[slot] if e["id"] == equip_id), None)
                if equip_data:
                    equip_hp += equip_data.get("hp", 0)
                    equip_atk += equip_data.get("atk", 0)
                    equip_speed += equip_data.get("speed", 0)
        
        # Apply flat bonuses from equipment
        max_hp += equip_hp
        atk += equip_atk
        speed += equip_speed * 0.1  # Convert speed stat to actual speed multiplier

        return max_hp, atk, speed
    
    def exp_needed(self):
        """當前等級升級所需經驗"""
        return LEVEL_EXP.get(self.level, 0)

    def add_exp(self, amount):
        """增加經驗，自動升級（返回是否升級）"""
        if self.level >= 50:
            return False
        self.exp += amount
        leveled_up = False
        while self.level < 50 and self.exp >= self.exp_needed():
            self.exp -= self.exp_needed()
            self.level += 1
            leveled_up = True
        return leveled_up

    def can_rank_up(self):
        """檢查是否可以升星"""
        if self.stars >= 5:
            return False, "已達最高星級"
        needed = STAR_COST[self.stars]  # 當前星級對應的碎片需求
        if self.shards < needed:
            return False, f"碎片不足 ({self.shards}/{needed})"
        return True, ""

    def rank_up(self):
        """升星（消耗碎片）"""
        can_rankup, msg = self.can_rank_up()
        if not can_rankup:
            return False, msg
        self.shards -= STAR_COST[self.stars]
        self.stars += 1
        return True, f"升至 {self.stars} 星！"


class PlayerData:
    def __init__(self, path):
        self.path = path
        self.gold = 0
        self.gems = 1200
        self.roster = []  # list of Card
        self.team = []    # list of card ids
        self.equipment_inventory = []  # list of equipment dicts with {id, slot, equipped_to}
        self.daily_quests = [q.copy() for q in DAILY_QUESTS]  # 每日任务进度
        self.weekly_quests = [q.copy() for q in WEEKLY_QUESTS]  # 周任务进度
        self.quest_completed = set()  # 已完成的任务ID
        self.selected_friend = "无"  # Friend assist unit name

    def save(self):
        data = {
            "gold": self.gold,
            "gems": self.gems,
            "roster": [c.to_dict() for c in self.roster],
            "team": self.team,
            "equipment_inventory": self.equipment_inventory,
            "daily_quests": self.daily_quests,
            "weekly_quests": self.weekly_quests,
            "quest_completed": list(self.quest_completed),
            "selected_friend": self.selected_friend,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        if not os.path.exists(self.path):
            # seed with starter units
            for meta in [HERO_POOL[0], HERO_POOL[2], HERO_POOL[4]]:
                rarity = "R"
                self.roster.append(Card(meta["name"], meta["type"], rarity, level=1,
                                         base_hp=meta["base_hp"], base_atk=meta["base_atk"], base_speed=meta["base_speed"]))
            self.team = [c.id for c in self.roster[:3]]
            self.gold = 999999
            self.gems = 999999
            
            # Give starter equipment
            from data import EQUIPMENT_CATALOG
            self.equipment_inventory = [
                {"id": "w005", "slot": "weapon", "equipped_to": None},
                {"id": "w006", "slot": "weapon", "equipped_to": None},
                {"id": "h005", "slot": "horse", "equipped_to": None},
                {"id": "b005", "slot": "book", "equipped_to": None},
            ]
            
            self.save()
            return
        with open(self.path, "r", encoding="utf-8") as f:
            d = json.load(f)
        self.gold = d.get("gold", 0)
        self.gems = d.get("gems", 0)
        self.roster = [Card.from_dict(x) for x in d.get("roster", [])]
        self.team = d.get("team", [])
        self.equipment_inventory = d.get("equipment_inventory", [])
        self.daily_quests = d.get("daily_quests", [q.copy() for q in DAILY_QUESTS])
        self.weekly_quests = d.get("weekly_quests", [q.copy() for q in WEEKLY_QUESTS])
        self.quest_completed = set(d.get("quest_completed", []))
        self.selected_friend = d.get("selected_friend", "无")

    def add_card(self, card: Card):
        self.roster.append(card)

    def cards_by_id(self):
        return {c.id: c for c in self.roster}
    
    def update_quest_progress(self, quest_type, target_id):
        """更新任务进度"""
        quest_list = self.daily_quests if quest_type == "daily" else self.weekly_quests
        for quest in quest_list:
            if quest['id'] == target_id and quest['id'] not in self.quest_completed:
                if quest['progress'] < quest['target']:
                    quest['progress'] += 1
                    if quest['progress'] >= quest['target']:
                        self.quest_completed.add(quest['id'])


def get_save_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "sanguo_save.json")

# Buff 選擇
def choose_buff_screen(root, units):
    buffs = [
        ("攻擊+25%", lambda u: setattr(u, 'atk', u.atk * 1.25)),
        ("血量+60", lambda u: (setattr(u, 'hp', u.hp + 60), setattr(u, 'max_hp', u.max_hp + 60))),
        ("速度+2", lambda u: setattr(u, 'speed', u.speed + 2))
    ]
    random.shuffle(buffs)
    
    result = [None]
    
    def on_buff(idx):
        for u in units:
            if u.team == 0 and u.hp > 0:
                buffs[idx][1](u)
        result[0] = True
        buff_window.destroy()
    
    buff_window = tk.Toplevel(root)
    buff_window.title("選擇強化")
    buff_window.geometry("500x400")
    buff_window.configure(bg=BLACK)
    
    label = tk.Label(buff_window, text="選擇一個強化！", font=("Arial", 14), fg=YELLOW, bg=BLACK)
    label.pack(pady=20)
    
    for i, (name, _) in enumerate(buffs):
        btn = tk.Button(
            buff_window,
            text=f"{i+1}. {name}",
            font=("Arial", 12),
            bg=GREEN,
            fg=BLACK,
            command=lambda idx=i: on_buff(idx),
            width=30,
            height=3
        )
        btn.pack(pady=10)
    
    root.wait_window(buff_window)
    return result[0] if result[0] else False

# 主遊戲
class GameWindow:
    def __init__(self, root, player: PlayerData, team_cards: list[Card], **kwargs):
        self.root = root
        self.root.title("⚔ 三國戰爭 - 戰鬥")
        self.root.geometry("1000x600")
        self.root.configure(bg=BG_MAIN)

        self.player = player
        self.team_cards = team_cards  # Store cards to award exp
        self.chapter = kwargs.get('chapter', 1)  # 当前章节
        self.stage_config = next((c for c in CHAPTER_CONFIGS if c['chapter'] == self.chapter), CHAPTER_CONFIGS[0])
        self.max_waves = self.stage_config['waves']

        # 创建渐变背景效果
        self.canvas = Canvas(self.root, width=1000, height=600, bg="#0F1419")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_motion)

        # 城堡位置：玩家下方，敌人上方
        self.player_castle = Castle(500, 550, 0)
        
        # 如果是Boss关卡，创建Boss城堡
        is_boss_stage = self.stage_config.get('has_boss', False)
        self.enemy_castle = Castle(500, 100, 1, is_boss=is_boss_stage)
        self.boss_skill_cooldown = 0.0  # Boss技能冷却
        
        # Build units from cards - 玩家单位在下方
        self.player_units = []
        x_positions = [300, 500, 700]  # 水平分布
        for i, card in enumerate(team_cards[:3]):
            max_hp, atk, speed = card.stats()
            # 玩家隊伍比敵人強5%
            max_hp = int(max_hp * 1.05)
            atk = int(atk * 1.05)
            # 攻城傷害 = 攻擊力的70% (減少攻城能力以保持平衡)
            siege_atk = int(atk * 0.7)
            self.player_units.append(Unit(f"{card.name} Lv{card.level}", x_positions[i], 480, 0, card.unit_type, hp=max_hp, atk=atk, speed=speed, siege_atk=siege_atk))

        # Add friend assist unit if selected - 放在中间位置
        if hasattr(self.player, 'selected_friend') and self.player.selected_friend and self.player.selected_friend != "无":
            friend_config = next((f for f in FRIEND_ASSIST_UNITS if f['name'] == self.player.selected_friend), None)
            if friend_config:
                self.player_units.append(Unit(f"{friend_config['name']}", 500, 500, 0, friend_config['type'], 
                                             hp=friend_config.get('hp', 400), atk=friend_config.get('atk', 50), 
                                             speed=friend_config.get('speed', 80)))

        self.all_enemies = []
        self.enemy_units = []  # 當前活躍的敵人單位列表
        self.wave = 1
        self.running = True
        self.selected_unit = None
        self.damage_texts = []
        self.particles = []  # Particle effects system
        self.last_time = time.time()
        self._after_id = None
        # UI/UX 新增
        self.game_speed = 1.0  # 游戏速度倍率 (1.0, 2.0, 3.0)
        self.auto_battle = False  # 自动战斗开关
        self.show_ranges = False  # 显示攻击范围
        self.wave_start_time = time.time()  # 波次开始时间
        
        # 波间事件系统
        self.wave_events = []  # 当前波的待处理事件
        self.prep_time = 3  # 波间准备时间（秒）
        self.prep_countdown = 0  # 准备时间倒计时
        self.event_choices = []  # 波间事件选择
        self.waiting_for_event = False  # 等待事件选择
        self.current_event = None  # 当前选中的事件
        
        # Roguelite状态
        self.active_buffs = []  # 激活的Buff列表
        self.active_curses = []  # 激活的诅咒列表
        self.crit_chance = 0.0  # 暴击概率
        self.damage_reduction = 0.0  # 伤害减免
        self.lifesteal_rate = 0.0  # 吸血率
        
        # 战斗商店状态
        self.shop_items = []  # 当前波次的商店物品（刷新）
        self.shop_locked = []  # 锁定的物品索引
        self.temp_buffs = {}  # 临时增益 {unit_id: [buff_list]}
        self.refresh_count = 0  # 商店刷新次数
        
        # Ensure safe close cancels timers
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # Defer starting loop until window is fully initialized
        self._after_id = self.root.after(16, self.update_game)
    
    def on_click(self, event):
        if not self.running:
            return
        for u in self.player_units:
            dist = math.sqrt((event.x - u.pos[0])**2 + (event.y - u.pos[1])**2)
            if u.hp > 0 and dist < 30:
                self.selected_unit = u
                u.selected = True
            else:
                u.selected = False
    
    def on_right_click(self, event):
        """右鍵點擊敵人單位，設置為攻擊目標"""
        if not self.running or not self.selected_unit:
            return
        # 檢查點擊的是否是敵人單位
        for u in self.player_units + self.enemy_units:
            if u.team == 1 and u.hp > 0:  # 敵人
                dist = math.sqrt((event.x - u.pos[0])**2 + (event.y - u.pos[1])**2)
                if dist < 30:
                    # 設置為攻擊目標
                    self.selected_unit.target_enemy = u
                    self.selected_unit.target_pos = None  # 清除移動目標
                    return
    
    def on_release(self, event):
        if self.selected_unit:
            self.selected_unit.target_pos = [event.x, event.y]
            self.selected_unit = None
    
    def on_motion(self, event):
        pass
    
    def update_game(self):
        # Guard against destroyed widgets or stopped loop
        if not self.running or not self.canvas.winfo_exists():
            return
        
        current_time = time.time()
        dt = (current_time - self.last_time) * self.game_speed
        self.last_time = current_time
        
        # 產生新波敵人
        current_enemy_units = [u for u in self.all_enemies if u.hp > 0]
        if not current_enemy_units:
            # 检查是否完成所有波次
            if self.wave > self.max_waves:
                self.running = False
                return
            
            # 生成敌人（基于章节配置） - 在上方水平分布
            base_hp = self.stage_config['base_hp'] + (self.wave - 1) * 20
            base_atk = self.stage_config['base_atk'] + (self.wave - 1) * 3
            
            self.all_enemies = [
                Unit(f"敵槍{self.wave}", 300, 150, 1, 0, hp=int(base_hp * 0.56), atk=int(base_atk * 0.7)),
                Unit(f"敵騎{self.wave}", 500, 150, 1, 1, hp=int(base_hp * 0.7), atk=int(base_atk * 0.7)),
                Unit(f"敵弓{self.wave}", 700, 150, 1, 2, hp=int(base_hp * 0.49), atk=int(base_atk * 0.7))
            ]
            self.enemy_units = self.all_enemies  # 更新當前敵人列表
            
            # 只在第2波及以後才觸發波間準備階段
            if self.wave > 1:
                # 触发波间准备阶段
                self.wave += 1
                self.wave_start_time = time.time()
                self.prep_countdown = self.prep_time
                self.waiting_for_event = True
                # Mix base events with Roguelite buffs and curses
                base_events = list(WAVE_EVENTS)
                buff_options = random.sample(ROGUELITE_BUFFS, min(2, len(ROGUELITE_BUFFS)))
                curse_options = random.sample(ROGUELITE_CURSES, min(1, len(ROGUELITE_CURSES)))
                all_options = base_events + buff_options + curse_options
                self.event_choices = random.sample(all_options, min(3, len(all_options)))
                # Possibly add a trade option if player has enough gold
                if random.random() < 0.4 and self.player.gold >= 50:
                    trade_opt = random.choice(ROGUELITE_TRADE)
                    if len(self.event_choices) > 0:
                        self.event_choices[random.randint(0, len(self.event_choices) - 1)] = trade_opt
            else:
                # 第一波直接開始
                self.wave += 1
                self.wave_start_time = time.time()
        
        units = self.player_units + self.all_enemies
        
        # 处理波间准备逻辑
        if self.waiting_for_event:
            self.prep_countdown -= dt
            if self.prep_countdown <= 0:
                # 准备时间结束，自动应用第一个事件
                self.waiting_for_event = False
                if self.event_choices:
                    self.apply_event(self.event_choices[0])
        
        # 自动战斗：让玩家单位自动向上方前进
        if self.auto_battle and not self.waiting_for_event:
            for u in self.player_units:
                if u.hp > 0 and not u.target_pos:
                    # 向敌方城堡方向移动（上方）
                    u.target_pos = [u.pos[0], self.enemy_castle.pos[1] + 80]
        
        # 更新單位
        for u in units:
            if u.hp > 0:
                dmg = u.update(units, [self.player_castle, self.enemy_castle], self)
                if dmg > 0:
                    target = u.target_enemy if u.target_enemy else self.enemy_castle
                    self.damage_texts.append((target.pos[:], dmg, 30))
                    # Emit particle on hit
                    self.particles.append(Particle(target.pos[0], target.pos[1], RED if target.team == 1 else BLUE, life=0.8, vx=0, vy=-30))
        
        # 攻擊城堡（當周圍沒有可攻擊的敵人時，優先攻城）
        for u in units:
            if u.hp > 0:
                attack_range = get_attack_range(u.type)
                # 是否有敵人在攻擊範圍內
                has_enemy_in_range = False
                for e in units:
                    if e.team != u.team and e.hp > 0:
                        if math.dist(u.pos, e.pos) < attack_range:
                            has_enemy_in_range = True
                            break

                if not has_enemy_in_range:
                    if u.team == 0:
                        if math.dist(u.pos, self.enemy_castle.pos) < attack_range:
                            # 使用攻城傷害值（較低於普通攻擊）
                            damage = int(u.siege_atk)
                            self.enemy_castle.hp -= damage
                            self.damage_texts.append((self.enemy_castle.pos[:], damage, 30))
                            self.particles.append(Particle(self.enemy_castle.pos[0], self.enemy_castle.pos[1], RED, life=0.8, vx=0, vy=-30))
                    else:
                        if math.dist(u.pos, self.player_castle.pos) < attack_range:
                            # 使用攻城傷害值（較低於普通攻擊）
                            damage = int(u.siege_atk)
                            self.player_castle.hp -= damage
                            self.damage_texts.append((self.player_castle.pos[:], damage, 30))
                            self.particles.append(Particle(self.player_castle.pos[0], self.player_castle.pos[1], BLUE, life=0.8, vx=0, vy=-30))
        
        # Boss技能攻击
        if self.enemy_castle.is_boss:
            self.enemy_castle.update_boss_phase()
            self.boss_skill_cooldown -= 0.016
            
            if self.boss_skill_cooldown <= 0:
                # 获取当前阶段Boss技能
                current_phase = self.enemy_castle.boss_phase
                boss_abilities = [a for a in BOSS_CONFIG['abilities'] if a['phase'] == current_phase]
                
                if boss_abilities:
                    ability = boss_abilities[0]
                    ability_damage = BOSS_CONFIG['base_atk'] * ability.get('damage', 1.0)
                    
                    if ability['effect'] == 'aoe':
                        # 范围攻击所有玩家单位
                        for u in self.player_units:
                            if u.hp > 0:
                                u.hp -= ability_damage
                                self.damage_texts.append((u.pos[:], int(ability_damage), 30))
                    
                    elif ability['effect'] == 'execute':
                        # 对低血量单位造成额外伤害
                        threshold = ability.get('threshold', 0.3)
                        for u in self.player_units:
                            if u.hp > 0 and (u.hp / u.max_hp) < threshold:
                                u.hp -= ability_damage * 2  # 对低血量目标伤害翻倍
                                self.damage_texts.append((u.pos[:], int(ability_damage * 2), 30))
                    
                    else:
                        # 普通单体攻击
                        if self.player_units:
                            target = random.choice([u for u in self.player_units if u.hp > 0])
                            target.hp -= ability_damage
                            self.damage_texts.append((target.pos[:], int(ability_damage), 30))
                    
                    self.boss_skill_cooldown = ability.get('cooldown', 3.0)
        
        # 畫面
        try:
            self.canvas.delete("all")
        except tk.TclError:
            # Canvas may have been destroyed; stop updating
            return
        
        # 背景 - 绘制战场分界线
        self.canvas.create_rectangle(0, 0, 1000, 600, fill="#0F1419")
        # 中线（战场中间）
        self.canvas.create_line(0, 300, 1000, 300, fill=DARK_GOLD, width=2, dash=(10, 5))
        self.canvas.create_text(500, 300, text="═══ 战场中线 ═══", fill=DARK_GOLD, font=("Arial", 10, "italic"))
        
        # 城堡
        self.player_castle.draw(self.canvas)
        self.enemy_castle.draw(self.canvas)
        
        # 單位
        for u in units:
            if u.hp > 0:
                # 显示选中单位的高亮圈
                if self.selected_unit == u:
                    self.canvas.create_oval(
                        u.pos[0]-35, u.pos[1]-35,
                        u.pos[0]+35, u.pos[1]+35,
                        outline=YELLOW, width=3, dash=(2, 2)
                    )
                
                # 显示攻击范围（如果开启） - 使用兵种攻击范围
                if self.show_ranges:
                    range_color = "#4040FF" if u.team == 0 else "#FF4040"
                    attack_range = get_attack_range(u.type)
                    self.canvas.create_oval(
                        u.pos[0]-attack_range, u.pos[1]-attack_range,
                        u.pos[0]+attack_range, u.pos[1]+attack_range,
                        outline=range_color, width=2, dash=(3, 3)
                    )
                # 显示仇恨线
                if u.target_enemy and u.target_enemy.hp > 0:
                    line_color = BLUE if u.team == 0 else RED
                    self.canvas.create_line(
                        u.pos[0], u.pos[1],
                        u.target_enemy.pos[0], u.target_enemy.pos[1],
                        fill=line_color, width=1, dash=(2, 2), arrow=tk.LAST
                    )
                u.draw(self.canvas)
        
        # 傷害數字
        new_damage_texts = []
        for pos, dmg, t in self.damage_texts:
            self.canvas.create_text(
                pos[0], pos[1] - (30 - t),
                text=str(dmg),
                fill=YELLOW,
                font=("Arial", 10)
            )
            if t > 1:
                new_damage_texts.append((pos, dmg, t - 1))
        self.damage_texts = new_damage_texts
        
        # Update and render particles
        new_particles = []
        for particle in self.particles:
            particle.update(dt)
            if particle.life > 0:
                # Calculate alpha for fade effect
                alpha_ratio = particle.life / particle.max_life
                particle.draw(self.canvas, int(255 * alpha_ratio))
                new_particles.append(particle)
        self.particles = new_particles
        
        # 檢查勝負
        if self.player_castle.hp <= 0:
            self.canvas.create_text(500, 300, text="失敗！", fill=RED, font=("Arial", 40))
            self.canvas.update()
            # Reward small consolation
            self.player.gold += 80
            self.player.save()
            self.root.after(1500, self.on_close)
            return
        elif self.enemy_castle.hp <= 0:
            # 检查是否完成全部波次
            if self.wave > self.max_waves:
                # 关卡完成
                self.canvas.delete("all")
                self.canvas.create_rectangle(0, 0, 1000, 600, fill=GRAY)
                self.canvas.create_text(500, 200, text="關卡完成！", fill=YELLOW, font=("Arial", 48, "bold"))
                reward_gold = 500 + (self.chapter - 1) * 100
                reward_gems = 100 + (self.chapter - 1) * 20
                
                # Award experience to surviving team members
                base_exp = 80 + (self.chapter - 1) * 20  # More exp for higher chapters
                exp_gains = []
                level_ups = []
                for i, card in enumerate(self.team_cards[:3]):
                    # Check if unit survived (corresponding player_unit still has hp > 0)
                    if i < len(self.player_units) and self.player_units[i].hp > 0:
                        exp_to_give = base_exp
                        leveled_up = card.add_exp(exp_to_give)
                        exp_gains.append(f"{card.name} +{exp_to_give}經驗")
                        if leveled_up:
                            level_ups.append(f"{card.name} 升級至 Lv{card.level}！")
                
                self.player.gold += reward_gold
                self.player.gems += reward_gems
                
                # Award equipment drops (random chance)
                from data import EQUIPMENT_CATALOG
                equipment_drops = []
                if random.random() < 0.6:  # 60% chance to drop equipment
                    # Select random equipment based on chapter
                    if self.chapter >= 3:
                        rarity_pool = ["SR", "SR", "R", "R", "C"]
                    elif self.chapter >= 2:
                        rarity_pool = ["R", "R", "R", "C", "C"]
                    else:
                        rarity_pool = ["R", "C", "C", "C"]
                    
                    drop_rarity = random.choice(rarity_pool)
                    slot = random.choice(["weapon", "horse", "book"])
                    available = [e for e in EQUIPMENT_CATALOG[slot] if e["rarity"] == drop_rarity]
                    
                    if available:
                        dropped = random.choice(available)
                        self.player.equipment_inventory.append({
                            "id": dropped["id"],
                            "slot": slot,
                            "equipped_to": None
                        })
                        equipment_drops.append(f"[{dropped['rarity']}] {dropped['name']}")
                
                self.player.save()
                
                # Display rewards
                y_offset = 300
                self.canvas.create_text(500, y_offset, text=f"獲得金幣: +{reward_gold}  鑽石: +{reward_gems}", 
                                       fill=WHITE, font=("Arial", 16))
                y_offset += 30
                
                # Display equipment drops
                if equipment_drops:
                    for equip_msg in equipment_drops:
                        self.canvas.create_text(500, y_offset, text=f"⚔ 獲得裝備: {equip_msg}", 
                                               fill=PURPLE, font=("Arial", 12, "bold"))
                        y_offset += 25
                
                # Display exp gains
                if exp_gains:
                    for exp_msg in exp_gains:
                        self.canvas.create_text(500, y_offset, text=exp_msg, fill=CYAN, font=("Arial", 12))
                        y_offset += 25
                
                # Display level ups
                if level_ups:
                    for lv_msg in level_ups:
                        self.canvas.create_text(500, y_offset, text=f"⭐ {lv_msg}", fill=YELLOW, font=("Arial", 13, "bold"))
                        y_offset += 25
                
                self.canvas.create_text(500, 480, text=f"第 {self.chapter} 章完成！", fill=YELLOW, font=("Arial", 14))
                self.canvas.update()
                self.root.after(3500, self.on_close)
                return
            self.canvas.create_text(500, 300, text="勝利！", fill=YELLOW, font=("Arial", 40))
            self.canvas.update()
            self.root.after(1500, self.on_close)
            return
        
        # 增强HUD显示
        wave_time = int(time.time() - self.wave_start_time)
        # 顶部信息栏背景 - 渐变效果
        self.canvas.create_rectangle(0, 0, 1000, 60, fill=BG_MAIN, outline="")
        self.canvas.create_line(0, 60, 1000, 60, fill=DARK_GOLD, width=2)
        
        # 左侧：玩家城堡血量
        self.canvas.create_text(20, 12, text="🏰 友軍城堡", fill=CYAN, font=("Arial", 11, "bold"), anchor="nw")
        castle_hp_pct = self.player_castle.hp / self.player_castle.max_hp
        self.canvas.create_rectangle(20, 35, 220, 52, fill="#2C3E50", outline=LIGHT_GRAY, width=2)
        self.canvas.create_rectangle(20, 35, 20 + 200*castle_hp_pct, 52, fill=GREEN, outline="")
        self.canvas.create_text(120, 43, text=f"{max(0, int(self.player_castle.hp))}/{self.player_castle.max_hp}", 
                               fill=WHITE, font=("Arial", 10, "bold"))
        
        # 中间：波数和时间（或Boss信息）
        if self.enemy_castle.is_boss:
            boss_text = f"⚔ BOSS 第 {self.enemy_castle.boss_phase} 階段 ⚔"
            self.canvas.create_text(500, 18, text=boss_text, fill=ACCENT, font=("Arial", 15, "bold"))
        else:
            self.canvas.create_text(500, 18, text=f"⚡ 第 {self.wave} 波 ⚡", fill=DARK_GOLD, font=("Arial", 15, "bold"))
        self.canvas.create_text(500, 43, text=f"⏱ {wave_time}s", fill=TEXT_MAIN, font=("Arial", 11))
        
        # 右侧：敌方城堡/Boss血量
        enemy_label = "💀 BOSS" if self.enemy_castle.is_boss else "🏰 敵軍城堡"
        enemy_color = ACCENT if self.enemy_castle.is_boss else RED
        self.canvas.create_text(980, 12, text=enemy_label, fill=enemy_color, font=("Arial", 11, "bold"), anchor="ne")
        enemy_hp_pct = self.enemy_castle.hp / self.enemy_castle.max_hp
        self.canvas.create_rectangle(780, 35, 980, 52, fill="#2C3E50", outline=LIGHT_GRAY, width=2)
        self.canvas.create_rectangle(780, 35, 780 + 200*enemy_hp_pct, 52, fill=RED, outline="")
        self.canvas.create_text(880, 43, text=f"{max(0, int(self.enemy_castle.hp))}/{self.enemy_castle.max_hp}", 
                               fill=WHITE, font=("Arial", 10, "bold"))
        
        # 底部控制栏
        if not self.waiting_for_event:
            self.draw_controls()
        else:
            self.draw_wave_prep()
        
        self.canvas.update()
        # Schedule next frame safely
        self._after_id = self.root.after(16, self.update_game)  # 60 FPS
    def draw_wave_prep(self):
        """绘制波间准备界面"""
        # 控制栏背景
        self.canvas.create_rectangle(0, 540, 1000, 600, fill=BG_MAIN, outline="")
        self.canvas.create_line(0, 540, 1000, 540, fill=DARK_GOLD, width=2)
        
        # 倒计时
        self.canvas.create_text(500, 555, text=f"⏳ 準備中... {max(0, int(self.prep_countdown))}s", 
                              fill=DARK_GOLD, font=("Arial", 16, "bold"))
        
        # 显示当前状态
        status_text = f"✨ 增益: {len(self.active_buffs)} | 💀 詛咒: {len(self.active_curses)}"
        status_color = GREEN if len(self.active_buffs) > len(self.active_curses) else ACCENT
        self.canvas.create_text(100, 555, text=status_text, fill=status_color, 
                              font=("Arial", 10, "bold"))
        
        # 商店按钮
        shop_btn_color = CYAN if not hasattr(self, '_shop_opened') or not self._shop_opened else BLUE
        self.canvas.create_rectangle(850, 550, 980, 590, fill=shop_btn_color, outline=WHITE, width=2, tags="shop_btn")
        self.canvas.create_text(915, 570, text=f"🏪 商店\n刷新x{self.refresh_count}", 
                              fill=BLACK, font=("Arial", 9, "bold"), tags="shop_btn")
        self.canvas.tag_bind("shop_btn", "<Button-1>", lambda e: self.open_shop())
        
        # 事件选择按钮（带类型颜色编码）
        btn_width = 250
        for i, event in enumerate(self.event_choices):
            x = 100 + i * 280
            
            # 根据事件类型选择颜色
            if 'type' in event:
                if event['type'] == 'buff':
                    color = GREEN
                    icon = "✨"
                elif event['type'] == 'curse':
                    color = RED
                    icon = "💀"
                elif event['type'] == 'trade':
                    color = DARK_GOLD
                    icon = "💰"
                else:
                    color = BLUE
                    icon = "⚔"
            else:
                color = BLUE
                icon = "⚔"
            
            self.canvas.create_rectangle(x, 570, x + btn_width, 595, fill=color, outline=CYAN, width=2, tags=f"event_{i}")
            desc_text = f"{icon} {event['name']}"
            self.canvas.create_text(x + btn_width//2, 582, text=desc_text, fill=BLACK if event.get('type') in ['buff', 'trade'] else WHITE, font=("Arial", 9, "bold"), tags=f"event_{i}")
            self.canvas.tag_bind(f"event_{i}", "<Button-1>", lambda e, idx=i: self.select_event(idx))
    
    def open_shop(self):
        """打开战斗商店"""
        # 生成商店物品（首次或刷新）
        if not self.shop_items or self.refresh_count == 0:
            self.shop_items = random.sample(SHOP_ITEMS, min(5, len(SHOP_ITEMS)))
            self.shop_locked = []
        
        shop_win = tk.Toplevel(self.root)
        shop_win.title("🏪 戰鬥商店")
        shop_win.geometry("500x400")
        shop_win.configure(bg=BG_MAIN)
        
        tk.Label(shop_win, text=f"💰 金幣: {self.player.gold}", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 13, "bold")).pack(pady=10)
        
        frame = tk.Frame(shop_win, bg=BG_MAIN)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for idx, item in enumerate(self.shop_items):
            item_frame = tk.Frame(frame, bg=GRAY, relief=tk.RIDGE, bd=2)
            item_frame.pack(fill=tk.X, pady=5)
            
            is_locked = idx in self.shop_locked
            lock_str = " [已锁]" if is_locked else ""
            item_label = f"{item['icon']} {item['name']}{lock_str}\n{item['desc']} - {item['cost']}金"
            
            btn_text = "已锁" if is_locked else ("买" if self.player.gold >= item['cost'] else "金币不足")
            btn_color = "#888" if is_locked else (GREEN if self.player.gold >= item['cost'] else "#555")
            
            def buy_item_func(item_idx=idx):
                if item_idx not in self.shop_locked:
                    item_data = self.shop_items[item_idx]
                    if self.player.gold >= item_data['cost']:
                        self.player.gold -= item_data['cost']
                        self.use_shop_item(item_data)
                        shop_win.destroy()
            
            def lock_item_func(item_idx=idx):
                if item_idx in self.shop_locked:
                    self.shop_locked.remove(item_idx)
                else:
                    self.shop_locked.append(item_idx)
            
            tk.Label(item_frame, text=item_label, fg=WHITE, bg="#333", justify=tk.LEFT, font=("Arial", 10)).pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
            tk.Button(item_frame, text=btn_text, bg=btn_color, fg=BLACK, width=8, command=buy_item_func).pack(side=tk.LEFT, padx=2)
            tk.Button(item_frame, text="🔒" if is_locked else "🔓", bg="#666", width=3, command=lock_item_func).pack(side=tk.LEFT, padx=2)
        
        btn_frame = tk.Frame(shop_win, bg=GRAY)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="刷新 (50金)", command=lambda: self.refresh_shop(shop_win)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="关闭", command=shop_win.destroy).pack(side=tk.LEFT, padx=5)
    
    def refresh_shop(self, window):
        """刷新商店物品"""
        if self.player.gold >= 50:
            self.player.gold -= 50
            self.refresh_count += 1
            # 保留锁定的物品，刷新其他
            locked_items = [self.shop_items[i] for i in self.shop_locked if i < len(self.shop_items)]
            refresh_count = max(0, 5 - len(locked_items))
            new_items = random.sample([i for i in SHOP_ITEMS if i not in locked_items], min(refresh_count, len(SHOP_ITEMS)))
            self.shop_items = locked_items + new_items
            self.shop_locked = []
            window.destroy()
            self.open_shop()
        else:
            messagebox.showwarning("金币不足", "刷新需要50金币！")
    
    def use_shop_item(self, item):
        """使用商店物品"""
        effect = item['effect']
        
        if effect == 'heal':
            # 恢复全部单位
            for u in self.player_units:
                if u.hp > 0:
                    u.hp = min(u.max_hp, u.hp + item['value'])
        
        elif effect == 'atk_boost':
            # 临时攻击力增益
            for u in self.player_units:
                u.atk = int(u.atk * (1 + item['value']))
        
        elif effect == 'def_boost':
            # 临时防御增益
            self.damage_reduction += item['value']
        
        elif effect == 'speed_boost':
            # 移动速度增益
            for u in self.player_units:
                u.speed *= (1 + item['value'])
        
        elif effect == 'super_potion':
            # 超级药水
            for u in self.player_units:
                u.hp = min(u.max_hp, u.hp + item['value'])
                u.atk = int(u.atk * 1.3)
        
        messagebox.showinfo("购买成功", f"已购买: {item['name']}")
    
    def select_event(self, idx):
        """选择波间事件"""
        if 0 <= idx < len(self.event_choices):
            self.apply_event(self.event_choices[idx])
            self.waiting_for_event = False
    
    def apply_event(self, event):
        """应用波间事件效果"""
        effect = event['effect']
        
        # 基础波间事件
        if effect == 'heal':
            # 恢复所有单位25% HP
            for u in self.player_units:
                if u.hp > 0:
                    u.hp = min(u.max_hp, u.hp + u.max_hp * 0.25)
        
        elif effect == 'curse':
            # 敌方下波攻击降低20%
            for u in self.all_enemies:
                u.atk *= 0.8
        
        elif effect == 'fewer_enemies':
            # 下波敌人减少1个
            if self.all_enemies:
                self.all_enemies.pop()
        
        elif effect == 'slow':
            # 所有单位速度降低30%
            for u in self.player_units + self.all_enemies:
                u.speed *= 0.7
        
        # Roguelite增益效果
        elif 'type' in event and event['type'] == 'buff':
            buff_name = event['name']
            self.active_buffs.append(buff_name)
            
            if buff_name == 'atk_speed':
                # 攻击速度+30%（缩短攻击间隔）
                for u in self.player_units:
                    u.attack_interval *= 0.7
            elif buff_name == 'crit':
                # 暴击率+25%
                self.crit_chance = 0.25
            elif buff_name == 'move_speed':
                # 移动速度+40%
                for u in self.player_units:
                    u.speed *= 1.4
            elif buff_name == 'lifesteal':
                # 生命偷取+15%
                self.lifesteal_rate = 0.15
            elif buff_name == 'armor':
                # 护甲+25%
                self.damage_reduction = 0.25
            elif buff_name == 'cooldown':
                # 技能冷却-40%
                for u in self.player_units:
                    if hasattr(u, 'cooldown'):
                        u.cooldown *= 0.6
        
        # Roguelite诅咒效果
        elif 'type' in event and event['type'] == 'curse':
            curse_name = event['name']
            self.active_curses.append(curse_name)
            
            if curse_name == 'weakness':
                # 攻击力-30%
                for u in self.player_units:
                    u.atk *= 0.7
            elif curse_name == 'curse_slow':
                # 移动速度-50%
                for u in self.player_units:
                    u.speed *= 0.5
            elif curse_name == 'curse_fragile':
                # 受伤增加40%
                self.damage_reduction = -0.4
        
        # Roguelite交易效果
        elif 'type' in event and event['type'] == 'trade':
            trade_name = event['name']
            
            if trade_name == 'trade_double_buff':
                # 花费100金币获得2个随机增益
                if self.player.gold >= 100:
                    self.player.gold -= 100
                    buffs = random.sample(ROGUELITE_BUFFS, min(2, len(ROGUELITE_BUFFS)))
                    for buff in buffs:
                        self.apply_event(buff)
            
            elif trade_name == 'trade_remove_curse':
                # 花费80金币移除一个诅咒
                if self.player.gold >= 80 and self.active_curses:
                    self.player.gold -= 80
                    removed_curse = self.active_curses.pop(0)
                    # 还原诅咒效果
                    if removed_curse == 'weakness':
                        for u in self.player_units:
                            u.atk /= 0.7
                    elif removed_curse == 'curse_slow':
                        for u in self.player_units:
                            u.speed /= 0.5
                    elif removed_curse == 'curse_fragile':
                        self.damage_reduction = 0
            
            elif trade_name == 'trade_gamble':
                # 花费50金币随机获得增益或诅咒
                if self.player.gold >= 50:
                    self.player.gold -= 50
                    if random.random() < 0.5:
                        buff = random.choice(ROGUELITE_BUFFS)
                        self.apply_event(buff)
                    else:
                        curse = random.choice(ROGUELITE_CURSES)
                        self.apply_event(curse)
        
        self.current_event = event

    def draw_controls(self):
        """绘制底部控制栏"""
        # 控制栏背景 - 更美观的设计
        self.canvas.create_rectangle(0, 540, 1000, 600, fill=BG_MAIN, outline="")
        self.canvas.create_line(0, 540, 1000, 540, fill=DARK_GOLD, width=2)
        
        # 左侧：显示玩家单位技能状态和攻击范围
        info_y = 550
        self.canvas.create_text(10, info_y, text="攻击范围: 🔱槍60 | 🐎騎50 | 🏹弓120", 
                              fill=CYAN, font=("Arial", 9, "bold"), anchor="w")
        
        # 显示兵种相克提示（SanZhenZhi 风格）
        matchup_text = "槍克弓 | 弓克騎 | 騎克槍"
        self.canvas.create_text(10, 568, text=matchup_text, fill=YELLOW, 
                              font=("Arial", 8), anchor="w")
        
        for i, unit in enumerate(self.player_units[:2]):
            if unit.hp > 0 and unit.skill:
                y_pos = 580 + i * 16
                skill_name = unit.skill.get("name", "技能")
                
                if unit.skill_ready:
                    status_text = f"⚡ {skill_name} 就緒"
                    status_color = GREEN
                else:
                    cd_remaining = max(0, unit.skill_cooldown)
                    status_text = f"⏳ {skill_name} {cd_remaining:.1f}s"
                    status_color = ACCENT
                
                self.canvas.create_text(10, y_pos, text=status_text, fill=status_color, 
                                      font=("Arial", 8), anchor="w")
        
        # 速度控制按钮 - 更美观的样式
        speeds = [1.0, 2.0, 3.0]
        for i, spd in enumerate(speeds):
            x = 250 + i * 80
            if self.game_speed == spd:
                color = BLUE
                text_color = WHITE
            else:
                color = GRAY
                text_color = LIGHT_GRAY
            self.canvas.create_rectangle(x, 550, x+70, 590, fill=color, outline=CYAN, width=2, tags=f"speed_{spd}")
            self.canvas.create_text(x+35, 570, text=f"⚡x{int(spd)}", fill=text_color, 
                                  font=("Arial", 11, "bold"), tags=f"speed_{spd}")
            self.canvas.tag_bind(f"speed_{spd}", "<Button-1>", lambda e, s=spd: self.set_speed(s))
        
        # 自动战斗开关
        if self.auto_battle:
            auto_color = GREEN
            text_color = BLACK
            auto_text = "🤖 自動:ON"
        else:
            auto_color = GRAY
            text_color = LIGHT_GRAY
            auto_text = "🤖 自動:OFF"
        self.canvas.create_rectangle(500, 550, 620, 590, fill=auto_color, outline=CYAN, width=2, tags="auto_toggle")
        self.canvas.create_text(560, 570, text=auto_text, fill=text_color, 
                              font=("Arial", 11, "bold"), tags="auto_toggle")
        self.canvas.tag_bind("auto_toggle", "<Button-1>", lambda e: self.toggle_auto())
        
        # 显示范围开关
        if self.show_ranges:
            range_color = PURPLE
            text_color = WHITE
            range_text = "👁 範圍:ON"
        else:
            range_color = GRAY
            text_color = LIGHT_GRAY
            range_text = "👁 範圍:OFF"
        self.canvas.create_rectangle(650, 550, 770, 590, fill=range_color, outline=CYAN, width=2, tags="range_toggle")
        self.canvas.create_text(710, 570, text=range_text, fill=text_color, 
                              font=("Arial", 11, "bold"), tags="range_toggle")
        self.canvas.tag_bind("range_toggle", "<Button-1>", lambda e: self.toggle_ranges())
        
        # 资源显示
        self.canvas.create_text(850, 560, text=f"💰 {self.player.gold}", fill=DARK_GOLD, 
                              font=("Arial", 12, "bold"), anchor="w")
        self.canvas.create_text(850, 580, text=f"💎 {self.player.gems}", fill=CYAN, 
                              font=("Arial", 12, "bold"), anchor="w")
    
    def set_speed(self, speed):
        """设置游戏速度"""
        self.game_speed = speed
    
    def toggle_auto(self):
        """切换自动战斗"""
        self.auto_battle = not self.auto_battle
    
    def toggle_ranges(self):
        """切换显示攻击范围"""
        self.show_ranges = not self.show_ranges
    
    def on_close(self):
        # Stop loop and close window safely
        self.running = False
        try:
            if self._after_id is not None:
                self.root.after_cancel(self._after_id)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

class MainMenu:
    def __init__(self, root):
        self.root = root
        self.root.title("三國戰爭")
        self.root.geometry("1000x600")
        self.root.configure(bg=BG_MAIN)

        self.save_path = get_save_path()
        self.player = PlayerData(self.save_path)
        self.player.load()
        
        # Current view tracking
        self.current_view = None
        
        # Main container with header and content area
        self.header_frame = tk.Frame(self.root, bg=BG_MAIN, height=100)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self.header_frame.pack_propagate(False)
        
        # Currency display in header
        self.lbl_currency = tk.Label(self.header_frame, text="", fg=DARK_GOLD, bg=BG_MAIN, font=("Arial", 13, "bold"))
        self.lbl_currency.pack(pady=10)
        
        # Back button in header (hidden on main menu)
        self.btn_back = tk.Button(self.header_frame, text="← 返回主選單", command=self.show_main_menu,
                                 bg=GRAY, fg=WHITE, font=("Arial", 11, "bold"))
        
        # Content area
        self.content_frame = tk.Frame(self.root, bg=BG_MAIN)
        self.content_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        # Show tutorial on first visit (disabled due to Tkinter compatibility)
        # if not hasattr(self.player, 'tutorial_step'):
        #     self.player.tutorial_step = 0
        # if self.player.tutorial_step == 0:
        #     self.show_tutorial_step(0)
        #     self.player.tutorial_step = 1
        #     self.player.save()

        self.show_main_menu()
        self.refresh_currency()
    
    def clear_content(self):
        """清空內容區域"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_main_menu(self):
        """顯示主選單"""
        self.current_view = "main"
        self.btn_back.pack_forget()  # Hide back button on main menu
        self.clear_content()
        
        frame = tk.Frame(self.content_frame, bg=BG_MAIN)
        frame.pack(fill=tk.BOTH, expand=True)

        # 標題
        lbl_title = tk.Label(frame, text="⚔ 三國戰爭 ⚔", fg=DARK_GOLD, bg=BG_MAIN, font=("Arial", 48, "bold"))
        lbl_title.pack(pady=30)

        # 副標題
        subtitle = tk.Label(frame, text="兵臨城下，群雄逐鹿", fg=CYAN, bg=BG_MAIN, font=("Arial", 14, "italic"))
        subtitle.pack(pady=5)

        # 按鈕容器
        btn_frame = tk.Frame(frame, bg=BG_MAIN)
        btn_frame.pack(pady=15)

        btn_play = tk.Button(btn_frame, text="⚡ 開始戰鬥", width=22, height=2, 
                            command=self.start_battle, bg=ACCENT, fg=WHITE, 
                            font=("Arial", 12, "bold"), relief=tk.RAISED, bd=2)
        btn_gacha = tk.Button(btn_frame, text="✨ 抽卡 (300/次)", width=22, height=2, 
                             command=self.open_gacha, bg=PURPLE, fg=WHITE, 
                             font=("Arial", 12, "bold"), relief=tk.RAISED, bd=2)
        btn_team = tk.Button(btn_frame, text="👥 編成隊伍", width=22, height=2, 
                            command=self.open_team, bg=BLUE, fg=WHITE, 
                            font=("Arial", 12, "bold"), relief=tk.RAISED, bd=2)
        btn_hero_detail = tk.Button(btn_frame, text="🎖 武將詳情", width=22, height=2, 
                                   command=self.open_hero_detail, bg=CYAN, fg=BLACK, 
                                   font=("Arial", 12, "bold"), relief=tk.RAISED, bd=2)
        btn_quests = tk.Button(btn_frame, text="📋 每日任務", width=22, height=2, 
                              command=self.open_quests, bg=DARK_GOLD, fg=BLACK, 
                              font=("Arial", 12, "bold"), relief=tk.RAISED, bd=2)

        btn_play.pack(pady=8)
        btn_gacha.pack(pady=8)
        btn_team.pack(pady=8)
        btn_hero_detail.pack(pady=8)
        btn_quests.pack(pady=8)

        self.refresh_currency()

    def refresh_currency(self):
        self.lbl_currency.config(text=f"金幣: {self.player.gold}    鑽石: {self.player.gems}    擁有武將: {len(self.player.roster)}")

    def start_battle(self):
        id_map = self.player.cards_by_id()
        team_cards = [id_map[cid] for cid in self.player.team if cid in id_map]
        if not team_cards:
            messagebox.showinfo("提示", "請先在【編成隊伍】中選擇至少 1 名武將。")
            return
        # 打开关卡选择
        self.open_stage_select(team_cards)
    
    def open_stage_select(self, team_cards):
        """打开关卡选择菜单"""
        stage_win = tk.Toplevel(self.root)
        stage_win.title("選擇關卡")
        stage_win.geometry("500x400")
        stage_win.configure(bg=GRAY)
        
        tk.Label(stage_win, text="選擇要挑戰的關卡", fg=YELLOW, bg=GRAY, font=("Arial", 14, "bold")).pack(pady=20)
        
        for cfg in CHAPTER_CONFIGS:
            btn_text = f"第 {cfg['chapter']} 章: {cfg['name']}\n({cfg['waves']} 波)"
            btn = tk.Button(
                stage_win,
                text=btn_text,
                width=30,
                height=3,
                command=lambda c=cfg['chapter']: self.start_stage(team_cards, c, stage_win)
            )
            btn.pack(pady=10)
    
    def start_stage(self, team_cards, chapter, stage_win):
        """开始关卡"""
        stage_win.destroy()
        w = tk.Toplevel(self.root)
        game = GameWindow(w, self.player, team_cards, chapter=chapter)
        self.root.wait_window(w)
        self.refresh_currency()

    def open_gacha(self):
        self.current_view = "gacha"
        self.btn_back.pack(side=tk.LEFT, padx=20)
        self.clear_content()
        self.show_gacha_view()

    def open_team(self):
        self.current_view = "team"
        self.btn_back.pack(side=tk.LEFT, padx=20)
        self.clear_content()
        self.show_team_view()

    def open_hero_detail(self):
        """打開武將詳情管理"""
        self.current_view = "hero"
        self.btn_back.pack(side=tk.LEFT, padx=20)
        self.clear_content()
        self.show_hero_view()
    
    def open_quests(self):
        self.current_view = "quest"
        self.btn_back.pack(side=tk.LEFT, padx=20)
        self.clear_content()
        self.show_quest_view()
    
    def on_child_close(self):
        """子窗口回調：刷新並清除無效引用"""
        self.refresh_currency()
        # 清理已關閉窗口引用
        for attr in ["win_team", "win_gacha", "win_hero", "win_upgrade", "win_quest"]:
            win = getattr(self, attr, None)
            try:
                if win and hasattr(win, "win") and not win.win.winfo_exists():
                    setattr(self, attr, None)
            except tk.TclError:
                setattr(self, attr, None)

    def refresh_all(self):
        """刷新所有UI"""
        self.refresh_currency()
        # 搜索並刷新所有打開的 TeamWindow
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    try:
                        if widget.winfo_exists() and hasattr(widget, 'refresh_lists'):
                            widget.refresh_lists()
                    except tk.TclError:
                        pass
        except tk.TclError:
            pass
        # 清除 team_window 引用
        if hasattr(self, 'team_window'):
            self.team_window = None

    def show_tutorial_step(self, step):
        """Display tutorial popup for given step"""
        if step >= len(TUTORIAL_TIPS):
            return
        tip = TUTORIAL_TIPS[step]
        messagebox.showinfo(f"教學 - {tip['title']}", tip['msg'])
    
    def show_hero_view(self):
        """在主窗口顯示武將詳情"""
        frame = tk.Frame(self.content_frame, bg=BG_MAIN)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側：武將列表
        left_frame = tk.Frame(frame, bg=BG_MAIN, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="武將列表", fg=DARK_GOLD, bg=BG_MAIN,
                font=("Arial", 13, "bold")).pack(pady=5)
        
        list_heroes = tk.Listbox(left_frame, bg=LIGHT_GRAY, fg=BLACK, font=("Arial", 10))
        list_heroes.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 右側：詳情面板
        right_frame = tk.Frame(frame, bg=BG_MAIN)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Populate hero list and setup selection
        for c in self.player.roster:
            stars_display = "★" * c.stars + "☆" * (5 - c.stars)
            display = f"[{c.rarity}] {c.name} Lv{c.level} {stars_display}"
            list_heroes.insert(tk.END, display)
        
        if self.player.roster:
            list_heroes.selection_set(0)
            self._show_hero_detail_inline(self.player.roster[0], right_frame, list_heroes)
        
        def on_select(event):
            sel = list_heroes.curselection()
            if sel:
                idx = sel[0]
                self._show_hero_detail_inline(self.player.roster[idx], right_frame, list_heroes)
        
        list_heroes.bind("<<ListboxSelect>>", on_select)
    
    def _show_hero_detail_inline(self, card, parent_frame, list_widget):
        """顯示武將詳細信息"""
        for w in parent_frame.winfo_children():
            w.destroy()
        
        hp, atk, spd = card.stats()
        
        # Scrollable frame
        canvas = tk.Canvas(parent_frame, bg=BG_MAIN, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent_frame, command=canvas.yview)
        detail_frame = tk.Frame(canvas, bg=BG_MAIN)
        detail_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=detail_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Display hero info (abbreviated for space)
        tk.Label(detail_frame, text=f"⚔ {card.name}", fg=DARK_GOLD, bg=BG_MAIN,
                font=("Arial", 18, "bold")).pack(pady=10)
        
        # Stars
        stars_display = "★" * card.stars + "☆" * (5 - card.stars)
        tk.Label(detail_frame, text=stars_display, fg=YELLOW, bg=BG_MAIN,
                font=("Arial", 16, "bold")).pack(pady=5)
        
        # Level/exp/stats frames (abbreviated)
        level_frame = tk.Frame(detail_frame, bg=GRAY, relief=tk.RAISED, bd=2)
        level_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(level_frame, text=f"等級: {card.level}/50 | 金幣: {self.player.gold}", 
                fg=WHITE, bg=GRAY, font=("Arial", 11, "bold")).pack(pady=5)
        
        # Buttons
        btn_frame = tk.Frame(detail_frame, bg=BG_MAIN)
        btn_frame.pack(pady=20)
        
        if card.level < 50:
            def level_up_wrapper(times):
                self._level_up_hero_inline(card, times, parent_frame, list_widget)
            tk.Button(btn_frame, text=f"升1級(-{LEVEL_UP_GOLD_COST})",
                     command=lambda: level_up_wrapper(1), bg=GREEN, fg=WHITE,
                     font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
            tk.Button(btn_frame, text="升到滿",
                     command=lambda: level_up_wrapper(None), bg=ACCENT, fg=WHITE,
                     font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
        
        if card.stars < 5 and card.can_rank_up():
            def rank_up_wrapper():
                self._rank_up_hero_inline(card, parent_frame, list_widget)
            tk.Button(btn_frame, text=f"升星(-{STAR_COST[card.stars]}碎片)",
                     command=rank_up_wrapper, bg=DARK_GOLD, fg=BLACK,
                     font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=2)
    
    def _level_up_hero_inline(self, card, times, parent_frame, list_widget):
        max_steps = 50 - card.level
        desired = max_steps if times is None else min(times, max_steps)
        affordable = self.player.gold // LEVEL_UP_GOLD_COST
        steps = min(desired, affordable)
        if steps <= 0:
            messagebox.showinfo("提示", "金幣不足或已滿級")
            return
        gold_used = steps * LEVEL_UP_GOLD_COST
        for _ in range(steps):
            card.add_exp(card.exp_needed())
        self.player.gold -= gold_used
        self.player.save()
        self.refresh_currency()
        self._refresh_hero_list(list_widget)
        self._show_hero_detail_inline(card, parent_frame, list_widget)
        messagebox.showinfo("成功", f"升級{steps}級，消耗{gold_used}金")
    
    def _rank_up_hero_inline(self, card, parent_frame, list_widget):
        if card.stars >= 5:
            messagebox.showinfo("提示", "已達最大星級")
            return
        if not card.can_rank_up():
            needed = STAR_COST[card.stars]
            messagebox.showinfo("提示", f"碎片不足！需要{needed}碎片，目前有{card.shards}碎片")
            return
        card.rank_up()
        self.player.save()
        self.refresh_currency()
        self._refresh_hero_list(list_widget)
        self._show_hero_detail_inline(card, parent_frame, list_widget)
        messagebox.showinfo("成功", f"{card.name} 升至 {card.stars}星！")
    
    def _refresh_hero_list(self, list_widget):
        list_widget.delete(0, tk.END)
        for c in self.player.roster:
            stars_display = "★" * c.stars + "☆" * (5 - c.stars)
            display = f"[{c.rarity}] {c.name} Lv{c.level} {stars_display}"
            list_widget.insert(tk.END, display)
    
    def show_gacha_view(self):
        frame = tk.Frame(self.content_frame, bg=BG_MAIN)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="✨ 武將招募池 ✨", fg=DARK_GOLD, bg=BG_MAIN,
                 font=("Arial", 18, "bold")).pack(pady=15)

        result_frame = tk.Frame(frame, bg=BG_MAIN)
        result_frame.pack(fill=tk.BOTH, expand=True)

        btns = tk.Frame(frame, bg=BG_MAIN)
        btns.pack(pady=12)
        btn_cfg = {"font": ("Arial", 11, "bold"), "relief": tk.RAISED, "bd": 2}

        def show_results(cards, shard_conversions=None, equipment_bonus=None):
            for w in result_frame.winfo_children():
                w.destroy()
            tk.Label(result_frame, text="🎉 抽取結果 🎉", fg=DARK_GOLD, bg=BG_MAIN,
                     font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=8)

            if cards:
                for c in cards:
                    color = RARITY_COLOR.get(c.rarity, CYAN)
                    rarity_icon = {"C": "🔲", "R": "🟦", "SR": "💜", "SSR": "⭐"}
                    icon = rarity_icon.get(c.rarity, "")
                    tk.Label(result_frame, text=f"{icon} [{c.rarity}] {c.name} Lv{c.level}",
                             fg=color, bg=BG_MAIN, font=("Arial", 11)).pack(anchor="w", padx=20, pady=3)

            if shard_conversions:
                tk.Label(result_frame, text="\n💎 重複武將轉換碎片", fg=ACCENT, bg=BG_MAIN,
                         font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=4)
                for name, shards, rarity in shard_conversions:
                    color = RARITY_COLOR.get(rarity, CYAN)
                    tk.Label(result_frame, text=f"  [{rarity}] {name} → +{shards} 碎片",
                             fg=color, bg=BG_MAIN, font=("Arial", 10)).pack(anchor="w", padx=20, pady=2)

            if equipment_bonus:
                tk.Label(result_frame, text="\n⚔ 十連贈送裝備", fg=PURPLE, bg=BG_MAIN,
                         font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=4)
                for equip_msg in equipment_bonus:
                    tk.Label(result_frame, text=f"  {equip_msg}",
                             fg=PURPLE, bg=BG_MAIN, font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=2)

        def summon(count):
            cost = 300 if count == 1 else 3000
            if self.player.gems < cost:
                messagebox.showwarning("鑽石不足", "鑽石不足，無法抽卡。")
                return
            self.player.gems -= cost
            pulls = []
            shard_conversions = []
            equipment_bonus = []

            for _ in range(count):
                rarity = choose_weighted(RARITY_WEIGHTS)
                hero = random.choice(HERO_POOL)
                existing_card = next((c for c in self.player.roster if c.name == hero["name"]), None)
                if existing_card:
                    shard_amount = 10
                    if rarity == "SSR":
                        shard_amount = 30
                    elif rarity == "SR":
                        shard_amount = 20
                    elif rarity == "R":
                        shard_amount = 15
                    existing_card.shards += shard_amount
                    shard_conversions.append((hero["name"], shard_amount, rarity))
                else:
                    c = Card(hero["name"], hero["type"], rarity, level=1,
                             base_hp=hero["base_hp"], base_atk=hero["base_atk"], base_speed=hero["base_speed"])
                    self.player.add_card(c)
                    pulls.append(c)

            if count == 10:
                from data import EQUIPMENT_CATALOG
                bonus_rarity = random.choices(["SR", "R", "R", "C"], weights=[15, 40, 30, 15])[0]
                bonus_slot = random.choice(["weapon", "horse", "book"])
                available = [e for e in EQUIPMENT_CATALOG[bonus_slot] if e["rarity"] == bonus_rarity]
                if available:
                    bonus_equip = random.choice(available)
                    self.player.equipment_inventory.append({
                        "id": bonus_equip["id"],
                        "slot": bonus_slot,
                        "equipped_to": None
                    })
                    equipment_bonus.append(f"[{bonus_equip['rarity']}] {bonus_equip['name']}")

            self.player.save()
            self.refresh_currency()
            show_results(pulls, shard_conversions, equipment_bonus)

        tk.Button(btns, text="單抽 (300 💎)", command=lambda: summon(1),
                  bg=BLUE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=10)
        tk.Button(btns, text="十連 (3000 💎)", command=lambda: summon(10),
                  bg=PURPLE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=10)
    
    def show_team_view(self):
        frame = tk.Frame(self.content_frame, bg=BG_MAIN)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="👥 編成隊伍 (支持多選)", fg=DARK_GOLD, bg=BG_MAIN,
                 font=("Arial", 14, "bold")).place(x=20, y=10)
        tk.Label(frame, text="⚔ 出戰隊伍 (最多3)", fg=DARK_GOLD, bg=BG_MAIN,
                 font=("Arial", 14, "bold")).place(x=470, y=10)

        list_roster = tk.Listbox(frame, width=40, height=22, selectmode=tk.MULTIPLE,
                                 bg=LIGHT_GRAY, fg=BLACK, font=("Arial", 10))
        list_roster.place(x=20, y=40)
        list_team = tk.Listbox(frame, width=40, height=10, bg=CREAM, fg=BLACK, font=("Arial", 10))
        list_team.place(x=470, y=40)

        def refresh_lists():
            list_roster.delete(0, tk.END)
            for c in self.player.roster:
                list_roster.insert(tk.END, f"[{c.rarity}] {c.name} Lv{c.level} ({['槍','騎','弓'][c.unit_type]})")
            list_team.delete(0, tk.END)
            id_map = self.player.cards_by_id()
            for cid in self.player.team:
                c = id_map.get(cid)
                if c:
                    list_team.insert(tk.END, f"[{c.rarity}] {c.name} Lv{c.level}")

        def add_to_team():
            sel = list_roster.curselection()
            if not sel:
                return
            idx = sel[0]
            card = self.player.roster[idx]
            if card.id in self.player.team:
                messagebox.showinfo("提示", "此武將已在隊伍中")
                return
            if len(self.player.team) >= 3:
                messagebox.showinfo("提示", "隊伍已滿(最多3人)")
                return
            self.player.team.append(card.id)
            refresh_lists()

        def add_to_team_multi():
            sel = list_roster.curselection()
            if not sel:
                messagebox.showinfo("提示", "請選擇至少一名武將")
                return
            added_count = 0
            for idx in sel:
                card = self.player.roster[idx]
                if card.id not in self.player.team and len(self.player.team) < 3:
                    self.player.team.append(card.id)
                    added_count += 1
            if added_count > 0:
                messagebox.showinfo("成功", f"已添加 {added_count} 名武將到隊伍")
            elif len(self.player.team) >= 3:
                messagebox.showinfo("提示", "隊伍已滿(最多3人)")
            else:
                messagebox.showinfo("提示", "所選武將已在隊伍中")
            refresh_lists()

        def remove_from_team():
            sel = list_team.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx < len(self.player.team):
                del self.player.team[idx]
            refresh_lists()

        def save_team():
            self.player.save()
            messagebox.showinfo("已儲存", "隊伍已儲存！")

        btn_cfg = {"bg": BLUE, "fg": WHITE, "font": ("Arial", 10, "bold"), "relief": tk.RAISED, "bd": 1}
        tk.Button(frame, text="加入隊伍 (多選)", command=add_to_team_multi, **btn_cfg).place(x=470, y=260, width=150)
        tk.Button(frame, text="移除選中", command=remove_from_team, bg=RED, fg=WHITE,
                  font=("Arial", 10, "bold"), relief=tk.RAISED, bd=1).place(x=630, y=260, width=120)
        tk.Button(frame, text="加入單個", command=add_to_team, **btn_cfg).place(x=470, y=290, width=150)
        tk.Button(frame, text="儲存", command=save_team, bg=GREEN, fg=WHITE,
                  font=("Arial", 10, "bold"), relief=tk.RAISED, bd=1).place(x=630, y=290, width=60)

        tk.Label(frame, text="🤝 好友助戰", fg=CYAN, bg=BG_MAIN,
                 font=("Arial", 11, "bold")).place(x=470, y=330)
        self.friend_combo = tk.StringVar(value=self.player.selected_friend)
        def on_friend_changed(*args):
            self.player.selected_friend = self.friend_combo.get()
            self.player.save()
        self.friend_combo.trace_add("write", on_friend_changed)
        friend_names = ["无"] + [u["name"] for u in FRIEND_ASSIST_UNITS]
        friend_menu = tk.OptionMenu(frame, self.friend_combo, *friend_names)
        friend_menu.place(x=470, y=355, width=200)
        tk.Label(frame, text="戰鬥中的輔助單位", fg=TEXT_MAIN, bg=BG_MAIN,
                 font=("Arial", 9)).place(x=470, y=385)

        refresh_lists()
    
    def show_quest_view(self):
        frame = tk.Frame(self.content_frame, bg=BG_MAIN)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="🎯 任務中心", fg=DARK_GOLD, bg=BG_MAIN,
                 font=("Arial", 14, "bold")).pack(pady=10)

        notebook = tk.Frame(frame, bg=BG_MAIN)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(frame, bg=BG_MAIN)
        btn_frame.pack(pady=8)
        btn_cfg = {"width": 20, "font": ("Arial", 10, "bold"), "relief": tk.RAISED, "bd": 1}

        content_frame = tk.Frame(notebook, bg=BG_MAIN)
        content_frame.pack(fill=tk.BOTH, expand=True)

        def clear_content():
            for widget in content_frame.winfo_children():
                widget.destroy()

        def show_daily():
            clear_content()
            tk.Label(content_frame, text="📅 每日任務", fg=CYAN, bg=BG_MAIN,
                     font=("Arial", 13, "bold")).pack(pady=10)
            for quest in self.player.daily_quests:
                is_completed = quest['id'] in self.player.quest_completed
                progress_str = f"{quest['progress']}/{quest['target']}"
                quest_text = f"🎯 {quest['name']}\n{quest['desc']}\n💰 獎勵: {quest['reward_gold']}金 + {quest['reward_gems']}💎\n📊 進度: {progress_str}"
                quest_frame = tk.Frame(content_frame, bg=GRAY, relief=tk.RIDGE, bd=2)
                quest_frame.pack(fill=tk.X, pady=6, padx=10)
                tk.Label(quest_frame, text=quest_text, fg=GREEN if is_completed else TEXT_MAIN,
                         bg=GRAY, justify=tk.LEFT, font=("Arial", 9)).pack(side=tk.LEFT, padx=10, pady=8, fill=tk.X, expand=True)
                if is_completed:
                    tk.Label(quest_frame, text="✓完成", fg=GREEN, bg=GRAY,
                             font=("Arial", 11, "bold")).pack(side=tk.RIGHT, padx=10)
                else:
                    progress_pct = int(quest['progress']*100/quest['target'])
                    tk.Label(quest_frame, text=f"{progress_pct}%", fg=DARK_GOLD, bg=GRAY,
                             font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=10)

        def show_weekly():
            clear_content()
            tk.Label(content_frame, text="周任務", fg=YELLOW, bg=GRAY, font=("Arial", 14, "bold")).pack(pady=10)
            for quest in self.player.weekly_quests:
                is_completed = quest['id'] in self.player.quest_completed
                progress_str = f"{quest['progress']}/{quest['target']}"
                quest_text = f"{quest['name']}: {quest['desc']}\n奖励: {quest['reward_gold']}金 + {quest['reward_gems']}钻\n进度: {progress_str}"
                quest_frame = tk.Frame(content_frame, bg="#333", relief=tk.RAISED, bd=1)
                quest_frame.pack(fill=tk.X, pady=5, padx=10)
                tk.Label(quest_frame, text=quest_text, fg=GREEN if is_completed else WHITE, bg="#333", justify=tk.LEFT, font=("Arial", 10)).pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
                if is_completed:
                    tk.Label(quest_frame, text="✓已完成", fg=GREEN, bg="#333", font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=10)
                else:
                    tk.Label(quest_frame, text=f"{int(quest['progress']*100/quest['target'])}%", fg="#FF9900", bg="#333", font=("Arial", 10)).pack(side=tk.RIGHT, padx=10)

        tk.Button(btn_frame, text="📅 每日任務", command=show_daily,
                  bg=BLUE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📆 周任務", command=show_weekly,
                  bg=PURPLE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)

        show_daily()


class HeroDetailWindow:
    """武將詳情與養成窗口"""
    def __init__(self, root, player: PlayerData, on_close=None):
        self.player = player
        self.on_close = on_close
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.title("🎖 武將詳情")
        self.win.geometry("900x600")
        self.win.configure(bg=BG_MAIN)
        
        # 左側：武將列表
        tk.Label(self.win, text="武將列表", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 13, "bold")).place(x=20, y=10)
        
        self.list_heroes = tk.Listbox(self.win, width=35, height=28,
                                      bg=LIGHT_GRAY, fg=BLACK, font=("Arial", 10))
        self.list_heroes.place(x=20, y=40)
        self.list_heroes.bind("<<ListboxSelect>>", self.on_select_hero)
        
        # 右側：詳情面板
        self.detail_frame = tk.Frame(self.win, bg=BG_MAIN)
        self.detail_frame.place(x=350, y=10, width=530, height=580)
        
        self.selected_card = None
        self.refresh_hero_list()
    
    def refresh_hero_list(self):
        """刷新武將列表"""
        self.list_heroes.delete(0, tk.END)
        for c in self.player.roster:
            hp, atk, spd = c.stats()
            stars_display = "★" * c.stars + "☆" * (5 - c.stars)
            display = f"[{c.rarity}] {c.name} Lv{c.level} {stars_display}"
            self.list_heroes.insert(tk.END, display)
            # Auto-select first hero if list is not empty
            if self.player.roster:
                self.list_heroes.selection_set(0)
                self.selected_card = self.player.roster[0]
                self.show_hero_detail()
    def on_select_hero(self, event):
        """選中武將時顯示詳情"""
        sel = self.list_heroes.curselection()
        if not sel:
            return
        idx = sel[0]
        self.selected_card = self.player.roster[idx]
        self.show_hero_detail()
    
    def show_hero_detail(self):
        """顯示武將詳細信息"""
        # 清空詳情面板
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
        
        if not self.selected_card:
            return
        
        c = self.selected_card
        hp, atk, spd = c.stats()
        
        # 標題
        tk.Label(self.detail_frame, text=f"⚔ {c.name}", fg=DARK_GOLD, bg=BG_MAIN,
                font=("Arial", 18, "bold")).pack(pady=10)
        
        # 稀有度和兵種
        info_frame = tk.Frame(self.detail_frame, bg=BG_MAIN)
        info_frame.pack(pady=5)
        rarity_color = RARITY_COLOR.get(c.rarity, WHITE)
        tk.Label(info_frame, text=f"[{c.rarity}]", fg=rarity_color, bg=BG_MAIN,
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        unit_type_name = ["槍兵", "騎兵", "弓兵"][c.unit_type]
        tk.Label(info_frame, text=unit_type_name, fg=CYAN, bg=BG_MAIN,
                font=("Arial", 12)).pack(side=tk.LEFT, padx=5)
        
        # 星級顯示
        stars_display = "★" * c.stars + "☆" * (5 - c.stars)
        tk.Label(self.detail_frame, text=stars_display, fg=YELLOW, bg=BG_MAIN,
                font=("Arial", 16, "bold")).pack(pady=5)
        
        # 等級與經驗
        level_frame = tk.Frame(self.detail_frame, bg=GRAY, relief=tk.RAISED, bd=2)
        level_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(level_frame, text=f"等級: {c.level}/50", fg=WHITE, bg=GRAY,
            font=("Arial", 12, "bold")).pack(pady=5)
        tk.Label(level_frame, text=f"金幣: {self.player.gold}", fg=YELLOW, bg=GRAY,
            font=("Arial", 11, "bold")).pack(pady=2)
        
        if c.level < 50:
            exp_needed = c.exp_needed()
            exp_pct = c.exp / exp_needed if exp_needed > 0 else 1.0
            tk.Label(level_frame, text=f"經驗: {c.exp}/{exp_needed}", fg=GREEN, bg=GRAY,
                    font=("Arial", 10)).pack()
            
            # 經驗條
            exp_bar_frame = tk.Frame(level_frame, bg=GRAY)
            exp_bar_frame.pack(pady=5)
            tk.Canvas(exp_bar_frame, width=300, height=20, bg=BLACK, highlightthickness=0).pack()
            exp_canvas = tk.Canvas(exp_bar_frame, width=300, height=20, bg=BLACK, highlightthickness=0)
            exp_canvas.pack()
            exp_canvas.create_rectangle(0, 0, 300 * exp_pct, 20, fill=GREEN, outline="")
        else:
            tk.Label(level_frame, text="等級已滿！", fg=YELLOW, bg=GRAY,
                    font=("Arial", 11, "bold")).pack(pady=5)
        
        # 碎片
        shards_frame = tk.Frame(self.detail_frame, bg=GRAY, relief=tk.RAISED, bd=2)
        shards_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(shards_frame, text=f"碎片: {c.shards}", fg=PURPLE, bg=GRAY,
                font=("Arial", 12, "bold")).pack(pady=5)
        
        if c.stars < 5:
            from config import STAR_COST
            needed = STAR_COST[c.stars]
            tk.Label(shards_frame, text=f"升至 {c.stars+1}★ 需要: {needed} 碎片", fg=YELLOW, bg=GRAY,
                    font=("Arial", 10)).pack()
        else:
            tk.Label(shards_frame, text="已達最高星級！", fg=YELLOW, bg=GRAY,
                    font=("Arial", 10)).pack()
        
        # 屬性顯示
        stats_frame = tk.Frame(self.detail_frame, bg=GRAY, relief=tk.RAISED, bd=2)
        stats_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(stats_frame, text="📊 當前屬性", fg=DARK_GOLD, bg=GRAY,
                font=("Arial", 12, "bold")).pack(pady=5)
        tk.Label(stats_frame, text=f"生命: {hp}", fg=RED, bg=GRAY,
                font=("Arial", 11)).pack(pady=2)
        tk.Label(stats_frame, text=f"攻擊: {atk}", fg=ACCENT, bg=GRAY,
                font=("Arial", 11)).pack(pady=2)
        tk.Label(stats_frame, text=f"速度: {spd:.1f}", fg=CYAN, bg=GRAY,
                font=("Arial", 11)).pack(pady=2)
        
        # 裝備顯示
        from data import EQUIPMENT_CATALOG, EQUIPMENT_RARITY_COLOR
        equip_frame = tk.Frame(self.detail_frame, bg=GRAY, relief=tk.RAISED, bd=2)
        equip_frame.pack(pady=10, padx=20, fill=tk.X)
        tk.Label(equip_frame, text="⚔ 裝備", fg=DARK_GOLD, bg=GRAY,
                font=("Arial", 12, "bold")).pack(pady=5)
        
        slot_names = {"weapon": "武器", "horse": "坐騎", "book": "寶物"}
        for slot in ["weapon", "horse", "book"]:
            slot_frame = tk.Frame(equip_frame, bg="#34495E", relief=tk.RIDGE, bd=1)
            slot_frame.pack(pady=3, padx=10, fill=tk.X)
            
            # Slot label
            tk.Label(slot_frame, text=f"{slot_names[slot]}:", fg=YELLOW, bg="#34495E",
                    font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
            
            # Current equipment display
            equip_id = c.equipment.get(slot)
            if equip_id and equip_id != "None":
                equip_data = next((e for e in EQUIPMENT_CATALOG[slot] if e["id"] == equip_id), None)
                if equip_data:
                    color = EQUIPMENT_RARITY_COLOR.get(equip_data["rarity"], WHITE)
                    equip_text = f"[{equip_data['rarity']}] {equip_data['name']}"
                    tk.Label(slot_frame, text=equip_text, fg=color, bg="#34495E",
                            font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
                else:
                    tk.Label(slot_frame, text="(無裝備)", fg=LIGHT_GRAY, bg="#34495E",
                            font=("Arial", 9, "italic")).pack(side=tk.LEFT, padx=5)
            else:
                tk.Label(slot_frame, text="(無裝備)", fg=LIGHT_GRAY, bg="#34495E",
                        font=("Arial", 9, "italic")).pack(side=tk.LEFT, padx=5)
            
            # Change button
            btn = tk.Button(slot_frame, text="更換", bg=CYAN, fg=BLACK,
                          font=("Arial", 8), width=6,
                          command=lambda s=slot: self.change_equipment(s))
            btn.pack(side=tk.RIGHT, padx=5)
        
        # 操作按鈕
        btn_frame = tk.Frame(self.detail_frame, bg=BG_MAIN)
        btn_frame.pack(pady=20)
        
        # 升級按鈕組
        if c.level < 50:
            lvl_row = tk.Frame(btn_frame, bg=BG_MAIN)
            lvl_row.pack(pady=4)
            tk.Button(lvl_row, text=f"升1級 (-{LEVEL_UP_GOLD_COST}金)",
                      command=lambda: self.level_up_multi(1), bg=GREEN, fg=WHITE,
                      font=("Arial", 10, "bold"), width=16, height=2).pack(side=tk.LEFT, padx=4)
            tk.Button(lvl_row, text=f"升5級 (-{LEVEL_UP_GOLD_COST*5}金)",
                      command=lambda: self.level_up_multi(5), bg=GREEN, fg=WHITE,
                      font=("Arial", 10, "bold"), width=16, height=2).pack(side=tk.LEFT, padx=4)
            tk.Button(lvl_row, text="升到滿/金幣用完",
                      command=lambda: self.level_up_multi(None), bg=ACCENT, fg=WHITE,
                      font=("Arial", 10, "bold"), width=18, height=2).pack(side=tk.LEFT, padx=4)
        
        # 升星按鈕
        if c.stars < 5:
            can_rankup, msg = c.can_rank_up()
            btn_text = f"⭐ 升星至{c.stars+1}星" if can_rankup else f"⭐ 升星 ({msg})"
            btn_color = YELLOW if can_rankup else GRAY
            btn_rank_up = tk.Button(btn_frame, text=btn_text,
                                    command=self.rank_up_hero, bg=btn_color, fg=BLACK,
                                    font=("Arial", 11, "bold"), width=20, height=2,
                                    state=tk.NORMAL if can_rankup else tk.DISABLED)
            btn_rank_up.pack(pady=5)
    
    def change_equipment(self, slot):
        """更換裝備的彈窗選擇"""
        c = self.selected_card
        if not c:
            return
        
        from data import EQUIPMENT_CATALOG, EQUIPMENT_RARITY_COLOR
        
        # Create selection window
        select_win = tk.Toplevel(self.win)
        select_win.title(f"選擇{['武器', '坐騎', '寶物'][['weapon', 'horse', 'book'].index(slot)]}")
        select_win.geometry("450x400")
        select_win.configure(bg=BG_MAIN)
        
        tk.Label(select_win, text=f"選擇裝備 - {c.name}", fg=DARK_GOLD, bg=BG_MAIN,
                font=("Arial", 14, "bold")).pack(pady=10)
        
        # List frame with scrollbar
        list_frame = tk.Frame(select_win, bg=BG_MAIN)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, bg=GRAY, fg=WHITE, font=("Arial", 10),
                            selectmode=tk.SINGLE, yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Add "卸下裝備" option
        listbox.insert(tk.END, "【卸下裝備】")
        equip_list = [None]  # None represents unequip
        
        # Get available equipment from inventory
        available_equipment = [e for e in self.player.equipment_inventory 
                              if e["slot"] == slot and (e.get("equipped_to") is None or e.get("equipped_to") == c.id)]
        
        # Add equipment to list
        for equip_item in available_equipment:
            equip_id = equip_item["id"]
            equip_data = next((e for e in EQUIPMENT_CATALOG[slot] if e["id"] == equip_id), None)
            if equip_data:
                is_equipped = c.equipment.get(slot) == equip_id
                status = " (已裝備)" if is_equipped else ""
                display_text = f"[{equip_data['rarity']}] {equip_data['name']} | HP+{equip_data['hp']} ATK+{equip_data['atk']} SPD+{equip_data['speed']}{status}"
                listbox.insert(tk.END, display_text)
                equip_list.append(equip_id)
        
        # Buttons
        btn_frame = tk.Frame(select_win, bg=BG_MAIN)
        btn_frame.pack(pady=10)
        
        def on_confirm():
            selection = listbox.curselection()
            if not selection:
                messagebox.showinfo("提示", "請先選擇一個選項")
                return
            
            selected_idx = selection[0]
            selected_equip_id = equip_list[selected_idx]
            
            # Unequip current equipment
            old_equip_id = c.equipment.get(slot)
            if old_equip_id and old_equip_id != "None":
                for inv_item in self.player.equipment_inventory:
                    if inv_item["id"] == old_equip_id and inv_item.get("equipped_to") == c.id:
                        inv_item["equipped_to"] = None
                        break
            
            # Equip new equipment
            if selected_equip_id:
                c.equipment[slot] = selected_equip_id
                for inv_item in self.player.equipment_inventory:
                    if inv_item["id"] == selected_equip_id:
                        inv_item["equipped_to"] = c.id
                        break
            else:
                c.equipment[slot] = None
            
            self.player.save()
            self.show_hero_detail()
            if self.on_close:
                self.on_close()
            
            select_win.destroy()
            messagebox.showinfo("成功", "裝備已更換！")
        
        tk.Button(btn_frame, text="確定", command=on_confirm, bg=GREEN, fg=WHITE,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=select_win.destroy, bg=GRAY, fg=WHITE,
                 font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)
    
    def level_up_multi(self, times=None):
        """多級升級：times=None 表示盡可能升級直到金幣或滿級"""
        c = self.selected_card
        if not c:
            return
        if c.level >= 50:
            messagebox.showinfo("提示", "已達最高等級！")
            return
        
        max_steps = 50 - c.level
        desired = max_steps if times is None else min(times, max_steps)
        affordable = self.player.gold // LEVEL_UP_GOLD_COST
        steps = min(desired, affordable)
        if steps <= 0:
            need_gold = LEVEL_UP_GOLD_COST if affordable == 0 else 0
            msg = "金幣不足！" if need_gold else "已達最高等級！"
            messagebox.showinfo("提示", msg)
            return
        
        start_level = c.level
        gold_used = steps * LEVEL_UP_GOLD_COST
        for _ in range(steps):
            exp_needed = c.exp_needed()
            c.add_exp(exp_needed)
            if c.level >= 50:
                break
        self.player.gold -= gold_used
        self.player.save()
        self.refresh_hero_list()
        self.show_hero_detail()
        if self.on_close:
            self.on_close()
        messagebox.showinfo("成功", f"{c.name} 升級 {c.level - start_level} 級，消耗 {gold_used} 金幣！")
    
    def rank_up_hero(self):
        """升星武將"""
        c = self.selected_card
        
        success, msg = c.rank_up()
        
        if success:
            self.player.save()
            self.refresh_hero_list()
            self.show_hero_detail()
            if self.on_close:
                self.on_close()
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showinfo("失敗", msg)
    
    def close(self):
        if self.on_close:
            self.on_close()
        self.win.destroy()


class GachaWindow:
    def __init__(self, root, player: PlayerData, on_close=None):
        self.player = player
        self.on_close = on_close
        self.win = tk.Toplevel(root)
        self.win.title("✨ 抽卡")
        self.win.geometry("600x480")
        self.win.configure(bg=BG_MAIN)

        tk.Label(self.win, text="✨ 武將招募池 ✨", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 18, "bold")).pack(pady=15)

        self.result_frame = tk.Frame(self.win, bg=BG_MAIN)
        self.result_frame.pack(fill=tk.BOTH, expand=True)

        btns = tk.Frame(self.win, bg=BG_MAIN)
        btns.pack(pady=12)
        btn_cfg = {"font": ("Arial", 11, "bold"), "relief": tk.RAISED, "bd": 2}
        tk.Button(btns, text="單抽 (300 💎)", command=lambda: self.summon(1), 
                 bg=BLUE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=10)
        tk.Button(btns, text="十連 (3000 💎)", command=lambda: self.summon(10), 
                 bg=PURPLE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=10)
        tk.Button(btns, text="關閉", command=self.close, 
                 bg=GRAY, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=10)

        self.refresh()

    def summon(self, count):
        cost = 300 if count == 1 else 3000
        if self.player.gems < cost:
            messagebox.showwarning("鑽石不足", "鑽石不足，無法抽卡。")
            return
        self.player.gems -= cost
        pulls = []
        shard_conversions = []  # Track duplicates converted to shards
        equipment_bonus = []  # Track equipment rewards from 10-pull
        
        for _ in range(count):
            rarity = choose_weighted(RARITY_WEIGHTS)
            hero = random.choice(HERO_POOL)
            
            # Check if player already has this hero
            existing_card = next((c for c in self.player.roster if c.name == hero["name"]), None)
            
            if existing_card:
                # Duplicate! Convert to shards instead
                shard_amount = 10  # Base shards per duplicate
                if rarity == "SSR":
                    shard_amount = 30
                elif rarity == "SR":
                    shard_amount = 20
                elif rarity == "R":
                    shard_amount = 15
                
                existing_card.shards += shard_amount
                shard_conversions.append((hero["name"], shard_amount, rarity))
            else:
                # New hero! Add to roster
                c = Card(hero["name"], hero["type"], rarity, level=1,
                         base_hp=hero["base_hp"], base_atk=hero["base_atk"], base_speed=hero["base_speed"])
                self.player.add_card(c)
                pulls.append(c)
        
        # 10-pull bonus: guaranteed equipment
        if count == 10:
            from data import EQUIPMENT_CATALOG
            # Higher chance for better equipment in 10-pull
            bonus_rarity = random.choices(["SR", "R", "R", "C"], weights=[15, 40, 30, 15])[0]
            bonus_slot = random.choice(["weapon", "horse", "book"])
            available = [e for e in EQUIPMENT_CATALOG[bonus_slot] if e["rarity"] == bonus_rarity]
            
            if available:
                bonus_equip = random.choice(available)
                self.player.equipment_inventory.append({
                    "id": bonus_equip["id"],
                    "slot": bonus_slot,
                    "equipped_to": None
                })
                equipment_bonus.append(f"[{bonus_equip['rarity']}] {bonus_equip['name']}")
        
        self.player.save()
        self.show_results(pulls, shard_conversions, equipment_bonus)

    def show_results(self, cards, shard_conversions=None, equipment_bonus=None):
        for w in self.result_frame.winfo_children():
            w.destroy()
        tk.Label(self.result_frame, text="🎉 抽取結果 🎉", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=8)
        
        # Display new heroes
        if cards:
            for c in cards:
                color = RARITY_COLOR.get(c.rarity, CYAN)
                rarity_icon = {"C": "🔲", "R": "🟦", "SR": "💜", "SSR": "⭐"}
                icon = rarity_icon.get(c.rarity, "")
                tk.Label(self.result_frame, text=f"{icon} [{c.rarity}] {c.name} Lv{c.level}", 
                        fg=color, bg=BG_MAIN, font=("Arial", 11)).pack(anchor="w", padx=20, pady=3)
        
        # Display shard conversions from duplicates
        if shard_conversions:
            tk.Label(self.result_frame, text="\n💎 重複武將轉換碎片", fg=ACCENT, bg=BG_MAIN, 
                    font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=4)
            for name, shards, rarity in shard_conversions:
                color = RARITY_COLOR.get(rarity, CYAN)
                tk.Label(self.result_frame, text=f"  [{rarity}] {name} → +{shards} 碎片", 
                        fg=color, bg=BG_MAIN, font=("Arial", 10)).pack(anchor="w", padx=20, pady=2)
        
        # Display equipment bonus from 10-pull
        if equipment_bonus:
            tk.Label(self.result_frame, text="\n⚔ 十連贈送裝備", fg=PURPLE, bg=BG_MAIN, 
                    font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=4)
            for equip_msg in equipment_bonus:
                tk.Label(self.result_frame, text=f"  {equip_msg}", 
                        fg=PURPLE, bg=BG_MAIN, font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=2)
        
        self.refresh()

    def refresh(self):
        pass

    def close(self):
        self.player.save()  # 確保保存
        
        # 首先調用主窗口的 on_close 回調
        if self.on_close:
            self.on_close()
        
        # 額外的保險：直接搜索並刷新所有打開的 TeamWindow
        root = self.win.master
        try:
            # 獲取所有頂級窗口
            for widget in root.winfo_children():
                try:
                    if isinstance(widget, tk.Toplevel) and widget.winfo_exists():
                        if hasattr(widget, 'refresh_lists'):
                            widget.refresh_lists()
                except tk.TclError:
                    pass
        except tk.TclError:
            pass
        
        self.win.destroy()


class TeamWindow:
    def __init__(self, root, player: PlayerData, on_close=None):
        self.player = player
        self.on_close = on_close
        self.win = tk.Toplevel(root)
        self.win.title("⚔ 編成隊伍")
        self.win.geometry("900x550")
        self.win.configure(bg=BG_MAIN)

        # 標題
        tk.Label(self.win, text="👥 編成隊伍 (支持多選)", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 14, "bold")).place(x=20, y=10)
        tk.Label(self.win, text="⚔ 出戰隊伍 (最多3)", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 14, "bold")).place(x=470, y=10)

        # 支持多选的列表框
        self.list_roster = tk.Listbox(self.win, width=40, height=22, selectmode=tk.MULTIPLE,
                                     bg=LIGHT_GRAY, fg=BLACK, font=("Arial", 10))
        self.list_roster.place(x=20, y=40)
        
        self.list_team = tk.Listbox(self.win, width=40, height=10, 
                                   bg=CREAM, fg=BLACK, font=("Arial", 10))
        self.list_team.place(x=470, y=40)

        # 按鈕容器
        btn_cfg = {"bg": BLUE, "fg": WHITE, "font": ("Arial", 10, "bold"), "relief": tk.RAISED, "bd": 1}
        tk.Button(self.win, text="加入隊伍 (多選)", command=self.add_to_team_multi, **btn_cfg).place(x=470, y=260, width=150)
        tk.Button(self.win, text="移除選中", command=self.remove_from_team, bg=RED, fg=WHITE, 
                 font=("Arial", 10, "bold"), relief=tk.RAISED, bd=1).place(x=630, y=260, width=120)
        tk.Button(self.win, text="加入單個", command=self.add_to_team, **btn_cfg).place(x=470, y=290, width=150)
        tk.Button(self.win, text="儲存", command=self.save_team, bg=GREEN, fg=WHITE, 
                 font=("Arial", 10, "bold"), relief=tk.RAISED, bd=1).place(x=630, y=290, width=60)
        tk.Button(self.win, text="關閉", command=self.close, bg=GRAY, fg=WHITE, 
                 font=("Arial", 10, "bold"), relief=tk.RAISED, bd=1).place(x=700, y=290, width=50)
        
        # 好友助战选择
        tk.Label(self.win, text="🤝 好友助戰", fg=CYAN, bg=BG_MAIN, 
                font=("Arial", 11, "bold")).place(x=470, y=330)
        self.friend_combo = tk.StringVar(value=self.player.selected_friend)
        self.friend_combo.trace_add("write", self.on_friend_changed)
        friend_names = ["无"] + [u["name"] for u in FRIEND_ASSIST_UNITS]
        friend_menu = tk.OptionMenu(self.win, self.friend_combo, *friend_names)
        friend_menu.place(x=470, y=355, width=200)
        tk.Label(self.win, text="戰鬥中的輔助單位", fg=TEXT_MAIN, bg=BG_MAIN, 
                font=("Arial", 9)).place(x=470, y=385)

        self.refresh_lists()

    def refresh_lists(self):
        self.list_roster.delete(0, tk.END)
        for c in self.player.roster:
            self.list_roster.insert(tk.END, f"[{c.rarity}] {c.name} Lv{c.level} ({['槍','騎','弓'][c.unit_type]})")
        self.list_team.delete(0, tk.END)
        id_map = self.player.cards_by_id()
        for cid in self.player.team:
            c = id_map.get(cid)
            if c:
                self.list_team.insert(tk.END, f"[{c.rarity}] {c.name} Lv{c.level}")

    def add_to_team(self):
        """添加单个卡片到队伍"""
        sel = self.list_roster.curselection()
        if not sel:
            return
        idx = sel[0]
        card = self.player.roster[idx]
        if card.id in self.player.team:
            messagebox.showinfo("提示", "此武將已在隊伍中")
            return
        if len(self.player.team) >= 3:
            messagebox.showinfo("提示", "隊伍已滿(最多3人)")
            return
        self.player.team.append(card.id)
        self.refresh_lists()
    
    def add_to_team_multi(self):
        """多选添加卡片到队伍"""
        sel = self.list_roster.curselection()
        if not sel:
            messagebox.showinfo("提示", "请选择至少一名武将")
            return
        
        added_count = 0
        for idx in sel:
            card = self.player.roster[idx]
            if card.id not in self.player.team and len(self.player.team) < 3:
                self.player.team.append(card.id)
                added_count += 1
        
        if added_count > 0:
            messagebox.showinfo("成功", f"已添加 {added_count} 名武将到队伍")
        elif len(self.player.team) >= 3:
            messagebox.showinfo("提示", "队伍已满(最多3人)")
        else:
            messagebox.showinfo("提示", "所选武将已在队伍中")
        
        self.refresh_lists()

    def remove_from_team(self):
        sel = self.list_team.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.player.team):
            del self.player.team[idx]
        self.refresh_lists()

    def on_friend_changed(self, *args):
        """Save friend selection when changed"""
        self.player.selected_friend = self.friend_combo.get()
        self.player.save()

    def save_team(self):
        self.player.save()
        messagebox.showinfo("已儲存", "隊伍已儲存！")

    def close(self):
        if self.on_close:
            self.on_close()
        self.win.destroy()


class UpgradeWindow:
    def __init__(self, root, player: PlayerData, on_close=None):
        self.player = player
        self.on_close = on_close
        self.win = tk.Toplevel(root)
        self.win.title("📈 養成升級")
        self.win.geometry("900x550")
        self.win.configure(bg=BG_MAIN)

        tk.Label(self.win, text="📊 選擇武將強化", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 13, "bold")).pack(pady=12)
        frame = tk.Frame(self.win, bg=BG_MAIN)
        frame.pack(fill=tk.BOTH, expand=True)

        self.list_roster = tk.Listbox(frame, width=35, height=18, 
                                     bg=CREAM, fg=BLACK, font=("Arial", 10))
        self.list_roster.pack(side=tk.LEFT, padx=10, pady=10)
        self.info = tk.Label(frame, text="", fg=TEXT_MAIN, bg=BG_MAIN, 
                           justify=tk.LEFT, font=("Arial", 10))
        self.info.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        btns = tk.Frame(self.win, bg=BG_MAIN)
        btns.pack(pady=10)
        btn_cfg = {"font": ("Arial", 10, "bold"), "relief": tk.RAISED, "bd": 1}
        tk.Button(btns, text="📋 資訊", command=self.show_info, bg=BLUE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="⬆ 升級", command=self.level_up, bg=GREEN, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="⭐ 升星", command=self.upgrade_stars, bg=DARK_GOLD, fg=BLACK, **btn_cfg).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="⚔ 換裝", command=self.equip_item, bg=PURPLE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)
        tk.Button(btns, text="關閉", command=self.close).pack(side=tk.LEFT, padx=5)

        self.refresh()

    def refresh(self):
        self.list_roster.delete(0, tk.END)
        for c in self.player.roster:
            stars_str = "⭐" * c.stars
            self.list_roster.insert(tk.END, f"[{c.rarity}] {c.name} Lv{c.level} {stars_str}")
        self.info.config(text=f"金幣: {self.player.gold}")

    def _selected_card(self):
        sel = self.list_roster.curselection()
        if not sel:
            return None
        return self.player.roster[sel[0]]

    def show_info(self):
        c = self._selected_card()
        if not c:
            return
        hp, atk, spd = c.stats()
        level_cost = self.level_cost(c)
        star_cost = self.star_cost(c)
        
        stars_str = "⭐" * c.stars
        info_text = f"{c.name} [{c.rarity}] {stars_str}\n\n"
        info_text += f"等級: {c.level}\n"
        info_text += f"HP: {hp}  ATK: {atk}  SPD: {spd:.2f}\n\n"
        
        info_text += f"等級升級花費: {level_cost} 金幣\n"
        info_text += f"星級升級花費: {star_cost} 金幣\n"
        
        if c.equipment:
            info_text += f"\n已裝備: "
            for eq_type, eq_data in c.equipment.items():
                if isinstance(eq_data, dict):
                    info_text += f"{eq_data.get('name', eq_type)} "
        else:
            info_text += f"\n未裝備任何物品\n"
        
        self.info.config(text=info_text)

    def level_cost(self, c: Card):
        base = {"C": 80, "R": 120, "SR": 200, "SSR": 320}[c.rarity]
        return base * c.level

    def star_cost(self, c: Card):
        if c.stars >= 6:
            return 0
        return STAR_BONUSES[c.stars]["cost"]

    def level_up(self):
        c = self._selected_card()
        if not c:
            return
        cost = self.level_cost(c)
        if self.player.gold < cost:
            messagebox.showwarning("金幣不足", "金幣不足，無法升級。")
            return
        self.player.gold -= cost
        c.level += 1
        self.player.save()
        self.show_info()
        self.refresh()

    def upgrade_stars(self):
        c = self._selected_card()
        if not c:
            return
        if c.stars >= 6:
            messagebox.showinfo("提示", "已達最大星級(6星)！")
            return
        cost = self.star_cost(c)
        if self.player.gold < cost:
            messagebox.showwarning("金幣不足", f"升星需要 {cost} 金幣！")
            return
        self.player.gold -= cost
        c.stars += 1
        self.player.save()
        messagebox.showinfo("成功", f"{c.name} 升級至 {c.stars} 星！")
        self.show_info()
        self.refresh()

    def equip_item(self):
        c = self._selected_card()
        if not c:
            return
        
        equip_win = tk.Toplevel(self.win)
        equip_win.title(f"為 {c.name} 換裝")
        equip_win.geometry("400x300")
        equip_win.configure(bg=GRAY)
        
        tk.Label(equip_win, text="選擇裝備類型", fg=WHITE, bg=GRAY, font=("Arial", 12, "bold")).pack(pady=10)
        
        for eq_type, eq_info in EQUIPMENT_TYPES.items():
            def equip_type_func(eq_t=eq_type):
                rarity = random.choice(list(RARITY_ORDER))
                bonus = EQUIPMENT_TYPES[eq_t]["rarity_bonus"].get(rarity, 0)
                c.equipment[eq_t] = {"name": f"{eq_info['name']} [{rarity}]", "rarity": rarity, "stat": eq_info["stat"], "bonus": bonus}
                self.player.save()
                messagebox.showinfo("成功", f"為 {c.name} 裝備了 {eq_info['name']} [{rarity}]！")
                equip_win.destroy()
                self.show_info()
                self.refresh()
            
            btn_text = f"裝備 {eq_info['name']}"
            tk.Button(equip_win, text=btn_text, width=30, height=2, command=equip_type_func).pack(pady=5)

    def close(self):
        if self.on_close:
            self.on_close()
        self.win.destroy()


class QuestWindow:
    def __init__(self, root, player: PlayerData, on_close=None):
        self.player = player
        self.on_close = on_close
        self.win = tk.Toplevel(root)
        self.win.title("📋 每日/周任務")
        self.win.geometry("700x600")
        self.win.configure(bg=BG_MAIN)
        
        # 標題
        tk.Label(self.win, text="🎯 任務中心", fg=DARK_GOLD, bg=BG_MAIN, 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        # 标签页
        self.notebook = tk.Frame(self.win, bg=BG_MAIN)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标签按钮
        btn_frame = tk.Frame(self.win, bg=BG_MAIN)
        btn_frame.pack(pady=8)
        btn_cfg = {"width": 20, "font": ("Arial", 10, "bold"), "relief": tk.RAISED, "bd": 1}
        tk.Button(btn_frame, text="📅 每日任務", command=self.show_daily, 
                 bg=BLUE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📆 周任務", command=self.show_weekly, 
                 bg=PURPLE, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="關閉", command=self.close, 
                 bg=GRAY, fg=WHITE, **btn_cfg).pack(side=tk.LEFT, padx=5)
        
        self.content_frame = tk.Frame(self.notebook, bg=BG_MAIN)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.show_daily()
    
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_daily(self):
        self.clear_content()
        tk.Label(self.content_frame, text="📅 每日任務", fg=CYAN, bg=BG_MAIN, 
                font=("Arial", 13, "bold")).pack(pady=10)
        
        for quest in self.player.daily_quests:
            is_completed = quest['id'] in self.player.quest_completed
            progress_str = f"{quest['progress']}/{quest['target']}"
            quest_text = f"🎯 {quest['name']}\n{quest['desc']}\n💰 獎勵: {quest['reward_gold']}金 + {quest['reward_gems']}💎\n📊 進度: {progress_str}"
            
            quest_frame = tk.Frame(self.content_frame, bg=GRAY, relief=tk.RIDGE, bd=2)
            quest_frame.pack(fill=tk.X, pady=6, padx=10)
            
            tk.Label(quest_frame, text=quest_text, fg=GREEN if is_completed else TEXT_MAIN, 
                    bg=GRAY, justify=tk.LEFT, font=("Arial", 9)).pack(side=tk.LEFT, padx=10, pady=8, fill=tk.X, expand=True)
            
            if is_completed:
                tk.Label(quest_frame, text="✓完成", fg=GREEN, bg=GRAY, 
                        font=("Arial", 11, "bold")).pack(side=tk.RIGHT, padx=10)
            else:
                progress_pct = int(quest['progress']*100/quest['target'])
                tk.Label(quest_frame, text=f"{progress_pct}%", fg=DARK_GOLD, bg=GRAY, 
                        font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=10)
    
    def show_weekly(self):
        self.clear_content()
        tk.Label(self.content_frame, text="周任務", fg=YELLOW, bg=GRAY, font=("Arial", 14, "bold")).pack(pady=10)
        
        for quest in self.player.weekly_quests:
            is_completed = quest['id'] in self.player.quest_completed
            progress_str = f"{quest['progress']}/{quest['target']}"
            quest_text = f"{quest['name']}: {quest['desc']}\n奖励: {quest['reward_gold']}金 + {quest['reward_gems']}钻\n进度: {progress_str}"
            
            quest_frame = tk.Frame(self.content_frame, bg="#333", relief=tk.RAISED, bd=1)
            quest_frame.pack(fill=tk.X, pady=5, padx=10)
            
            tk.Label(quest_frame, text=quest_text, fg=GREEN if is_completed else WHITE, bg="#333", justify=tk.LEFT, font=("Arial", 10)).pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
            
            if is_completed:
                tk.Label(quest_frame, text="✓已完成", fg=GREEN, bg="#333", font=("Arial", 12, "bold")).pack(side=tk.RIGHT, padx=10)
            else:
                tk.Label(quest_frame, text=f"{int(quest['progress']*100/quest['target'])}%", fg="#FF9900", bg="#333", font=("Arial", 10)).pack(side=tk.RIGHT, padx=10)
    
    def close(self):
        if self.on_close:
            self.on_close()
        self.win.destroy()


def main():
    root = tk.Tk()
    MainMenu(root)
    root.mainloop()

if __name__ == "__main__":
    main()
