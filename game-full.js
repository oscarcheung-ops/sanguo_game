// === 遊戲核心邏輯 ===

// 遊戲狀態
let gameState = {
    gold: 1000,
    gems: 100,
    level: 1,
    roster: [...HEROES], // 已擁有英雄（默認全部）
    team: [HEROES[0].id, HEROES[1].id, HEROES[2].id], // 隊伍中的英雄ID
    currentChapter: 0
};

// 戰鬥狀態
let battleState = {
    playerCastle: null,
    enemyCastle: null,
    units: [],
    wave: 1,
    maxWaves: 5,
    running: false,
    autoMode: false,
    gameSpeed: 1.0,
    startTime: 0
};

// Canvas 設置
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    const battleScreen = document.getElementById('battleScreen');
    const topBar = document.getElementById('topBar');
    const controls = document.getElementById('battleControls');
    
    if (battleScreen.style.display === 'flex') {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight - topBar.offsetHeight - controls.offsetHeight;
    }
}

window.addEventListener('resize', resizeCanvas);

// === 城堡類 ===
class Castle {
    constructor(x, y, team, maxHp = 1000) {
        this.x = x;
        this.y = y;
        this.team = team; // 0=玩家, 1=敵人
        this.maxHp = maxHp;
        this.hp = maxHp;
        this.width = 80;
        this.height = 60;
    }

    takeDamage(damage) {
        this.hp = Math.max(0, this.hp - damage);
        if (this.hp <= 0) {
            battleState.running = false;
            showBattleResult(this.team === 1);
        }
    }

    draw() {
        const color = this.team === 0 ? '#4A90E2' : '#E74C3C';
        const icon = this.team === 0 ? '🏰' : '👑';
        
        // 城堡主體
        ctx.fillStyle = color;
        ctx.fillRect(this.x - this.width/2, this.y - this.height/2, this.width, this.height);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeRect(this.x - this.width/2, this.y - this.height/2, this.width, this.height);
        
        // 圖標
        ctx.font = '30px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(icon, this.x, this.y);
        
        // HP 條
        const barWidth = this.width;
        const barHeight = 8;
        const hpPercent = this.hp / this.maxHp;
        
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x - barWidth/2, this.y + this.height/2 + 5, barWidth, barHeight);
        
        ctx.fillStyle = hpPercent > 0.5 ? '#2ECC71' : hpPercent > 0.25 ? '#F39C12' : '#E74C3C';
        ctx.fillRect(this.x - barWidth/2, this.y + this.height/2 + 5, barWidth * hpPercent, barHeight);
        
        // HP 文字
        ctx.fillStyle = '#FFF';
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(Math.floor(this.hp), this.x, this.y);
    }
}

// === 單位類 ===
class Unit {
    constructor(heroData, x, y, team) {
        this.id = Math.random();
        this.name = heroData.name;
        this.type = heroData.type;
        this.team = team;
        this.x = x;
        this.y = y;
        
        // 屬性計算
        const multiplier = 1 + (gameState.level - 1) * 0.1;
        const starBonus = STAR_BONUSES[0]; // 簡化：使用1星加成
        
        this.maxHp = Math.floor(heroData.baseHP * multiplier * starBonus.hp_mult);
        this.hp = this.maxHp;
        this.atk = Math.floor(heroData.baseATK * multiplier * starBonus.atk_mult);
        this.speed = heroData.baseSpeed * multiplier * starBonus.speed_mult;
        
        // 狀態
        this.target = null;
        this.attackCooldown = 0;
        this.skillCooldown = 0;
        this.stunned = false;
        this.slowFactor = 1.0;
        this.radius = 15;
        
        // 技能
        this.skill = UNIT_SKILLS[this.type];
        this.specialization = heroData.specialization;
        this.applySpecialization();
    }

    applySpecialization() {
        if (!this.specialization) return;
        
        const { bonus, value } = this.specialization;
        
        switch(bonus) {
            case "damage_boost":
                this.atk = Math.floor(this.atk * value);
                break;
            case "hp_recovery":
                this.hpRecovery = value;
                break;
            case "speed_boost":
                this.speed *= value;
                break;
            case "crit_rate":
                this.critRate = value;
                break;
            case "skill_cooldown":
                this.skillCooldownMult = value;
                break;
            case "skill_damage":
                this.skillDamageMult = value;
                break;
        }
    }

    update(deltaTime) {
        // 更新冷卻時間
        if (this.attackCooldown > 0) {
            this.attackCooldown -= deltaTime;
        }
        if (this.skillCooldown > 0) {
            this.skillCooldown -= deltaTime;
        }

        // 更新眩暈
        if (this.stunned) {
            this.stunDuration -= deltaTime;
            if (this.stunDuration <= 0) {
                this.stunned = false;
            }
        }

        // 更新減速
        if (this.slowFactor < 1.0) {
            this.slowDuration -= deltaTime;
            if (this.slowDuration <= 0) {
                this.slowFactor = 1.0;
            }
        }

        // HP 恢復
        if (this.hpRecovery && this.hp < this.maxHp) {
            this.hp = Math.min(this.maxHp, this.hp + this.maxHp * this.hpRecovery * deltaTime);
        }

        if (this.stunned) return;

        // 尋找目標
        if (!this.target || this.target.hp <= 0) {
            this.findTarget();
        }

        // 移動和攻擊
        if (this.target) {
            const dx = this.target.x - this.x;
            const dy = this.target.y - this.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const attackRange = UNIT_CONFIG[this.type].attackRange;

            if (dist > attackRange) {
                // 移動
                const moveSpeed = this.speed * this.slowFactor;
                const moveX = (dx / dist) * moveSpeed * deltaTime;
                const moveY = (dy / dist) * moveSpeed * deltaTime;
                this.x += moveX;
                this.y += moveY;
            } else {
                // 攻擊
                if (this.attackCooldown <= 0) {
                    this.attack(this.target);
                    this.attackCooldown = 1.0; // 1秒攻擊間隔
                }
                
                // 釋放技能
                if (this.skillCooldown <= 0 && this.skill) {
                    this.activateSkill(this.target);
                    const cooldown = this.skill.cooldown * (this.skillCooldownMult || 1);
                    this.skillCooldown = cooldown;
                }
            }
        }
    }

    findTarget() {
        // 優先攻擊敵方單位
        const enemies = battleState.units.filter(u => u.team !== this.team && u.hp > 0);
        
        if (enemies.length > 0) {
            this.target = enemies.reduce((closest, u) => {
                const dist = Math.hypot(u.x - this.x, u.y - this.y);
                const closestDist = Math.hypot(closest.x - this.x, closest.y - this.y);
                return dist < closestDist ? u : closest;
            });
        } else {
            // 攻擊敵方城堡
            this.target = this.team === 0 ? battleState.enemyCastle : battleState.playerCastle;
        }
    }

    attack(target) {
        let damage = this.atk;
        
        if (target instanceof Unit) {
            damage *= getMultiplier(this.type, target.type);
            // 暴擊判定
            if (this.critRate && Math.random() < this.critRate) {
                damage *= 1.5;
            }
        }
        
        target.takeDamage(damage);
    }

    activateSkill(target) {
        if (!this.skill) return;
        
        const baseDamage = this.atk * this.skill.damage_mult * (this.skillDamageMult || 1);
        const damage = baseDamage * getMultiplier(this.type, target.type);
        
        switch(this.skill.effect) {
            case "pierce": // 槍兵技能
                target.takeDamage(damage);
                if (Math.random() < this.skill.stun_chance) {
                    target.stunned = true;
                    target.stunDuration = 1.0;
                }
                break;
                
            case "charge": // 騎兵技能
                target.takeDamage(damage);
                target.slowFactor = 0.5;
                target.slowDuration = 2.0;
                this.hp = Math.min(this.maxHp, this.hp + this.maxHp * this.skill.self_heal);
                break;
                
            case "volley": // 弓兵技能
                const nearby = battleState.units.filter(u => 
                    u.team !== this.team && u.hp > 0 &&
                    Math.hypot(u.x - target.x, u.y - target.y) < this.skill.range
                );
                nearby.slice(0, this.skill.arrow_count).forEach(u => {
                    u.takeDamage(damage * 0.8);
                    u.slowFactor = 0.6;
                    u.slowDuration = 1.5;
                });
                break;
        }
    }

    takeDamage(damage) {
        this.hp = Math.max(0, this.hp - damage);
        
        if (this.hp <= 0 && this.team === 1) {
            gameState.gold += 30; // 擊殺敵人獲得金幣
            updateUI();
        }
    }

    draw() {
        if (this.hp <= 0) return;
        
        // 單位圓形
        ctx.fillStyle = UNIT_CONFIG[this.type].color;
        ctx.globalAlpha = this.team === 0 ? 1.0 : 0.8;
        
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        ctx.globalAlpha = 1.0;
        
        // 類型圖標
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#FFF';
        ctx.fillText(UNIT_CONFIG[this.type].icon, this.x, this.y);
        
        // HP 條
        const barWidth = this.radius * 2.5;
        const barHeight = 4;
        const hpPercent = this.hp / this.maxHp;
        
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x - barWidth/2, this.y - this.radius - 8, barWidth, barHeight);
        
        ctx.fillStyle = hpPercent > 0.5 ? '#2ECC71' : hpPercent > 0.25 ? '#F39C12' : '#E74C3C';
        ctx.fillRect(this.x - barWidth/2, this.y - this.radius - 8, barWidth * hpPercent, barHeight);
        
        // 名稱
        ctx.font = '10px Arial';
        ctx.fillStyle = '#FFF';
        ctx.fillText(this.name, this.x, this.y + this.radius + 15);
    }
}

// === UI 更新 ===
function updateUI() {
    document.getElementById('playerHP').textContent = Math.floor(battleState.playerCastle.hp);
    document.getElementById('enemyHP').textContent = Math.floor(battleState.enemyCastle.hp);
    document.getElementById('waveNum').textContent = `${battleState.wave}/${battleState.maxWaves}`;
    document.getElementById('battleGold').textContent = gameState.gold;
    
    const elapsed = (Date.now() - battleState.startTime) / 1000;
    const mins = Math.floor(elapsed / 60);
    const secs = Math.floor(elapsed % 60);
    document.getElementById('battleTime').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
}

// === 遊戲循環 ===
let lastTime = 0;
let enemySpawnTimer = 0;

function gameLoop(currentTime) {
    if (!battleState.running) return;
    
    const deltaTime = Math.min((currentTime - lastTime) / 1000, 0.016) * battleState.gameSpeed;
    lastTime = currentTime;
    
    // 清空畫布
    ctx.fillStyle = 'rgba(15, 20, 25, 0.3)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 繪製中線
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 10]);
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
    ctx.setLineDash([]);
    
    // 更新和繪製城堡
    battleState.playerCastle.draw();
    battleState.enemyCastle.draw();
    
    // 更新和繪製單位
    battleState.units = battleState.units.filter(u => u.hp > 0);
    battleState.units.forEach(unit => {
        unit.update(deltaTime);
        unit.draw();
    });
    
    // 敵人生成
    enemySpawnTimer += deltaTime;
    const spawnInterval = Math.max(1.5, 4 - battleState.wave * 0.2);
    if (enemySpawnTimer > spawnInterval && battleState.wave <= battleState.maxWaves) {
        spawnEnemyUnit();
        enemySpawnTimer = 0;
    }
    
    // 檢查波數完成
    if (battleState.wave <= battleState.maxWaves && 
        battleState.units.every(u => u.team === 0 || u.hp <= 0)) {
        battleState.wave++;
    }
    
    updateUI();
    requestAnimationFrame(gameLoop);
}

// === 敵人生成 ===
function spawnEnemyUnit() {
    const enemyConfig = ENEMY_POOL[Math.floor(Math.random() * ENEMY_POOL.length)];
    const x = canvas.width / 2 + (Math.random() - 0.5) * 200;
    const y = 100 + Math.random() * 100;
    
    const unit = new Unit(enemyConfig, x, y, 1);
    battleState.units.push(unit);
}

// === 主選單功能 ===
function startNewGame() {
    // 初始化戰鬥
    resizeCanvas();
    
    const chapter = CHAPTERS[gameState.currentChapter];
    battleState.maxWaves = chapter.waves;
    battleState.playerCastle = new Castle(canvas.width / 2, canvas.height - 80, 0, 1000);
    battleState.enemyCastle = new Castle(canvas.width / 2, 80, 1, chapter.maxHp);
    battleState.units = [];
    battleState.wave = 1;
    battleState.running = true;
    battleState.startTime = Date.now();
    
    // 創建玩家單位
    gameState.team.forEach((heroId, idx) => {
        const heroData = HEROES.find(h => h.id === heroId);
        if (heroData) {
            const x = canvas.width / 2 - 100 + idx * 100;
            const y = canvas.height - 150;
            battleState.units.push(new Unit(heroData, x, y, 0));
        }
    });
    
    // 顯示戰鬥畫面
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('battleScreen').style.display = 'flex';
    
    lastTime = Date.now();
    requestAnimationFrame(gameLoop);
}

function backToMenu() {
    battleState.running = false;
    document.getElementById('battleScreen').style.display = 'none';
    document.getElementById('mainMenu').style.display = 'flex';
    gameState.currentChapter = Math.min(gameState.currentChapter + 1, CHAPTERS.length - 1);
}

function showBattleResult(victory) {
    battleState.running = false;
    
    if (victory) {
        alert(`🎉 恭喜勝利！\n獲得金幣: ${gameState.gold}`);
    } else {
        alert(`💀 戰敗\n保留金幣: ${gameState.gold}`);
    }
    
    backToMenu();
}

// === 隊伍編成 ===
function showTeamScreen() {
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('teamScreen').style.display = 'flex';
    refreshTeamScreen();
}

function hideTeamScreen() {
    document.getElementById('teamScreen').style.display = 'none';
    document.getElementById('mainMenu').style.display = 'flex';
}

function refreshTeamScreen() {
    // 當前隊伍
    const currentTeam = document.getElementById('currentTeam');
    currentTeam.innerHTML = '';
    gameState.team.forEach(heroId => {
        const hero = HEROES.find(h => h.id === heroId);
        if (hero) {
            const div = createHeroCard(hero, true);
            currentTeam.appendChild(div);
        }
    });
    
    // 可用英雄
    const available = document.getElementById('availableHeroes');
    available.innerHTML = '';
    HEROES.forEach(hero => {
        if (!gameState.team.includes(hero.id)) {
            const div = createHeroCard(hero, false);
            available.appendChild(div);
        }
    });
}

function createHeroCard(hero, selected) {
    const div = document.createElement('div');
    div.className = 'hero-card' + (selected ? ' selected' : '');
    div.innerHTML = `
        <div class="hero-name">${hero.icon} ${hero.name}</div>
        <div class="hero-stats">
            <div>類型: ${UNIT_CONFIG[hero.type].name}</div>
            <div>稀有: ${hero.rarity}</div>
            <div>HP: ${hero.baseHP}</div>
            <div>ATK: ${hero.baseATK}</div>
        </div>
    `;
    
    div.onclick = () => {
        if (!selected && gameState.team.length < 3) {
            gameState.team.push(hero.id);
            refreshTeamScreen();
        } else if (selected) {
            gameState.team = gameState.team.filter(id => id !== hero.id);
            refreshTeamScreen();
        }
    };
    
    return div;
}

function confirmTeam() {
    if (gameState.team.length === 0) {
        alert('請至少選擇1個英雄！');
        return;
    }
    hideTeamScreen();
}

// === 抽卡系統 ===
function showGachaScreen() {
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('gachaScreen').style.display = 'flex';
    document.getElementById('gachGold').textContent = gameState.gold;
    document.getElementById('gachGems').textContent = gameState.gems;
}

function hideGachaScreen() {
    document.getElementById('gachaScreen').style.display = 'none';
    document.getElementById('mainMenu').style.display = 'flex';
}

function gacha(times) {
    const cost = times * 10;
    if (gameState.gems < cost) {
        alert('鑽石不足！');
        return;
    }
    
    gameState.gems -= cost;
    const results = [];
    
    for (let i = 0; i < times; i++) {
        const random = Math.random();
        let hero;
        
        if (random < 0.5) { // 50% 低稀有
            hero = HEROES[Math.floor(Math.random() * 4)];
        } else if (random < 0.85) { // 35% 中稀有
            hero = HEROES[Math.floor(Math.random() * 6)];
        } else { // 15% 高稀有
            hero = HEROES[Math.floor(Math.random() * 3) + 3];
        }
        
        results.push(hero);
    }
    
    const resultDiv = document.getElementById('gachaResult');
    resultDiv.innerHTML = '🎁 抽卡結果：<br>' + 
        results.map(h => `${h.icon} ${h.name} (${h.rarity})`).join('<br>');
    
    document.getElementById('gachGems').textContent = gameState.gems;
}

// === 設置頁面 ===
function showSettingsScreen() {
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('settingsScreen').style.display = 'flex';
    
    document.getElementById('settingsLevel').textContent = gameState.level;
    document.getElementById('settingsGold').textContent = gameState.gold;
    document.getElementById('settingsGems').textContent = gameState.gems;
    document.getElementById('settingsHeroes').textContent = gameState.roster.length;
}

function hideSettingsScreen() {
    document.getElementById('settingsScreen').style.display = 'none';
    document.getElementById('mainMenu').style.display = 'flex';
}

function clearData() {
    if (confirm('確定要重置所有數據嗎？')) {
        gameState.gold = 1000;
        gameState.gems = 100;
        gameState.level = 1;
        gameState.team = [HEROES[0].id, HEROES[1].id, HEROES[2].id];
        hideSettingsScreen();
    }
}

// === 戰鬥控制 ===
function toggleAuto() {
    battleState.autoMode = !battleState.autoMode;
    const btn = document.getElementById('autoBtn');
    btn.style.background = battleState.autoMode ? 
        'linear-gradient(145deg, #27AE60, #1E8449)' : 
        'linear-gradient(145deg, #1ABC9C, #16A085)';
}

function changeSpeed() {
    const speeds = [1.0, 1.5, 2.0, 3.0];
    const currentIndex = speeds.indexOf(battleState.gameSpeed);
    battleState.gameSpeed = speeds[(currentIndex + 1) % speeds.length];
    
    const btn = document.getElementById('speedBtn');
    btn.innerHTML = `⏱️ ${battleState.gameSpeed.toFixed(1)}x 速度`;
}

function toggleRanges() {
    battleState.showRanges = !battleState.showRanges;
}

// 初始化
window.addEventListener('load', () => {
    console.log('遊戲已加載');
});
