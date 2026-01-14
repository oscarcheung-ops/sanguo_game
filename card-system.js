// ============================================================
// 卡牌系統 & 玩家數據 (完全按照原 Python 遊戲)
// ============================================================

// === Card 類 (卡牌) ===
class Card {
    constructor(name, unitType, rarity, level = 1, cardId = null, baseHp = 100, baseAtk = 20, baseSpeed = 3,
                stars = 1, exp = 0, shards = 0, equipment = {}) {
        this.id = cardId || Math.random().toString(36).substr(2, 9);
        this.name = name;
        this.unitType = unitType;
        this.rarity = rarity; // C/R/SR/SSR
        this.level = Math.max(1, Math.min(level, 50));
        this.exp = exp;
        this.baseHp = baseHp;
        this.baseAtk = baseAtk;
        this.baseSpeed = baseSpeed;
        this.stars = Math.max(1, Math.min(stars, 6)); // 1-6星
        this.shards = shards; // 同名碎片
        this.equipment = equipment || {};
        
        // 初始化裝備槽
        ["weapon", "horse", "book"].forEach(slot => {
            if (!this.equipment[slot]) {
                this.equipment[slot] = null;
            }
        });
    }

    // 計算最終屬性（包含等級、星級、裝備）
    stats() {
        // 基礎稀有度加成
        const rarityMult = { "C": 1.0, "R": 1.1, "SR": 1.25, "SSR": 1.45 }[this.rarity] || 1.0;

        // 等級曲線
        const lvMult = LEVEL_CURVE[this.level] || LEVEL_CURVE[50];
        
        let maxHp = Math.floor(this.baseHp * rarityMult * lvMult);
        let atk = Math.floor(this.baseAtk * rarityMult * lvMult);
        let speed = this.baseSpeed + Math.min(2.0, (this.level - 1) * 0.05);

        // 星級加成
        const starIdx = Math.max(0, Math.min(this.stars - 1, STAR_BONUSES.length - 1));
        const starBonus = STAR_BONUSES[starIdx];
        
        maxHp = Math.floor(maxHp * starBonus.hp_mult);
        atk = Math.floor(atk * starBonus.atk_mult);
        speed = speed * starBonus.speed_mult;

        // 簡化：暫不考慮裝備加成
        // TODO: 後續添加裝備系統

        return { maxHp, atk, speed };
    }

    // 獲取升級所需經驗
    expNeeded() {
        return LEVEL_EXP[this.level] || 1000;
    }

    // 增加經驗（自動升級）
    addExp(amount) {
        if (this.level >= 50) return false;
        
        this.exp += amount;
        let leveledUp = false;
        
        while (this.level < 50 && this.exp >= this.expNeeded()) {
            this.exp -= this.expNeeded();
            this.level += 1;
            leveledUp = true;
        }
        
        return leveledUp;
    }

    // 檢查是否可以升星
    canRankUp() {
        if (this.stars >= 6) {
            return [false, "已達最高星級"];
        }
        const needed = STAR_COST[this.stars];
        if (this.shards < needed) {
            return [false, `碎片不足 (${this.shards}/${needed})`];
        }
        return [true, ""];
    }

    // 升星（消耗碎片）
    rankUp() {
        const [canRankup, msg] = this.canRankUp();
        if (!canRankup) {
            return [false, msg];
        }
        
        this.shards -= STAR_COST[this.stars];
        this.stars += 1;
        
        return [true, `升至 ${this.stars} 星！`];
    }

    // 序列化
    toJSON() {
        return {
            id: this.id,
            name: this.name,
            unitType: this.unitType,
            rarity: this.rarity,
            level: this.level,
            exp: this.exp,
            baseHp: this.baseHp,
            baseAtk: this.baseAtk,
            baseSpeed: this.baseSpeed,
            stars: this.stars,
            shards: this.shards,
            equipment: this.equipment
        };
    }

    // 反序列化
    static fromJSON(data) {
        return new Card(
            data.name, data.unitType, data.rarity, data.level, data.id,
            data.baseHp, data.baseAtk, data.baseSpeed,
            data.stars, data.exp, data.shards, data.equipment
        );
    }
}

// === PlayerData 類 (玩家數據) ===
class PlayerData {
    constructor() {
        this.gold = 0;
        this.gems = 100;
        this.roster = []; // 已擁有的卡牌列表
        this.team = []; // 隊伍中的卡牌ID列表（最多3個）
        this.dailyQuests = JSON.parse(JSON.stringify(DAILY_QUESTS));
        this.weeklyQuests = JSON.parse(JSON.stringify(WEEKLY_QUESTS));
        this.questCompleted = new Set();
        this.selectedFriend = "無"; // 友軍協戰
        this.currentChapter = 1;
        this.totalWaves = 0;
        this.activeBufls = []; // 激活的Buff
        this.activeCurses = []; // 激活的詛咒
    }

    // 初始化玩家數據（開始新遊戲）
    init() {
        // 初始英雄：前3位
        HERO_POOL.slice(0, 3).forEach(heroData => {
            const card = new Card(
                heroData.name,
                heroData.type,
                "R", // 初始稀有度
                1,
                null,
                heroData.base_hp,
                heroData.base_atk,
                heroData.base_speed
            );
            this.roster.push(card);
        });
        
        this.team = this.roster.slice(0, 3).map(c => c.id);
        this.gold = 1000;
        this.gems = 100;
    }

    // 新增卡牌
    addCard(card) {
        this.roster.push(card);
    }

    // 通過ID查找卡牌
    findCard(cardId) {
        return this.roster.find(c => c.id === cardId);
    }

    // 獲取隊伍的卡牌
    getTeamCards() {
        return this.team.map(id => this.findCard(id)).filter(c => c);
    }

    // 抽卡
    gacha(times = 1) {
        const cost = times * 10;
        if (this.gems < cost) {
            return [false, "鑽石不足"];
        }
        
        this.gems -= cost;
        const results = [];
        
        for (let i = 0; i < times; i++) {
            const rarity = chooseWeighted(RARITY_WEIGHTS);
            const heroData = HERO_POOL[Math.floor(Math.random() * HERO_POOL.length)];
            
            const card = new Card(
                heroData.name,
                heroData.type,
                rarity,
                1,
                null,
                heroData.base_hp,
                heroData.base_atk,
                heroData.base_speed
            );
            
            this.roster.push(card);
            results.push(card);
        }
        
        return [true, results];
    }

    // 更新任務進度
    updateQuestProgress(questType, targetId) {
        const questList = questType === "daily" ? this.dailyQuests : this.weeklyQuests;
        
        for (const quest of questList) {
            if (quest.id === targetId && !this.questCompleted.has(quest.id)) {
                quest.progress = Math.min(quest.progress + 1, quest.target);
                
                if (quest.progress >= quest.target) {
                    this.questCompleted.add(quest.id);
                }
            }
        }
    }

    // 領取任務獎勵
    claimQuestReward(questType, questId) {
        const questList = questType === "daily" ? this.dailyQuests : this.weeklyQuests;
        const quest = questList.find(q => q.id === questId);
        
        if (!quest || !this.questCompleted.has(questId)) {
            return [false, "無法領取"];
        }
        
        this.gold += quest.reward_gold;
        this.gems += quest.reward_gems;
        
        return [true, `領取獎勵: +${quest.reward_gold}金幣 +${quest.reward_gems}鑽石`];
    }

    // 保存數據到 LocalStorage
    save() {
        const data = {
            gold: this.gold,
            gems: this.gems,
            roster: this.roster.map(c => c.toJSON()),
            team: this.team,
            dailyQuests: this.dailyQuests,
            weeklyQuests: this.weeklyQuests,
            questCompleted: Array.from(this.questCompleted),
            selectedFriend: this.selectedFriend,
            currentChapter: this.currentChapter,
            totalWaves: this.totalWaves,
            activeBufls: this.activeBufls,
            activeCurses: this.activeCurses
        };
        
        localStorage.setItem('sanguo_save', JSON.stringify(data));
    }

    // 從 LocalStorage 加載數據
    load() {
        const data = localStorage.getItem('sanguo_save');
        
        if (!data) {
            this.init();
            return;
        }
        
        const parsed = JSON.parse(data);
        
        this.gold = parsed.gold || 0;
        this.gems = parsed.gems || 100;
        this.roster = (parsed.roster || []).map(c => Card.fromJSON(c));
        this.team = parsed.team || [];
        this.dailyQuests = parsed.dailyQuests || [];
        this.weeklyQuests = parsed.weeklyQuests || [];
        this.questCompleted = new Set(parsed.questCompleted || []);
        this.selectedFriend = parsed.selectedFriend || "無";
        this.currentChapter = parsed.currentChapter || 1;
        this.totalWaves = parsed.totalWaves || 0;
        this.activeBufls = parsed.activeBufls || [];
        this.activeCurses = parsed.activeCurses || [];
    }

    // 清除數據
    clear() {
        localStorage.removeItem('sanguo_save');
        this.gold = 0;
        this.gems = 100;
        this.roster = [];
        this.team = [];
        this.dailyQuests = JSON.parse(JSON.stringify(DAILY_QUESTS));
        this.weeklyQuests = JSON.parse(JSON.stringify(WEEKLY_QUESTS));
        this.questCompleted = new Set();
        this.selectedFriend = "無";
        this.currentChapter = 1;
        this.totalWaves = 0;
        this.activeBufls = [];
        this.activeCurses = [];
    }
}

// === 全局玩家對象 ===
let player = new PlayerData();
