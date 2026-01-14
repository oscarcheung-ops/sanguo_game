// 遊戲配置
const CONFIG = {
    UNIT_COSTS: { 0: 50, 1: 60, 2: 55 }, // 槍、騎、弓
    UNIT_NAMES: { 0: '槍兵', 1: '騎兵', 2: '弓兵' },
    UNIT_COLORS: { 0: '#E74C3C', 1: '#F39C12', 2: '#2ECC71' },
    UNIT_ATTACK_RANGES: { 0: 60, 1: 50, 2: 120 },
    UPGRADE_COST: 100,
    GOLD_PER_KILL: 30,
    INITIAL_GOLD: 100
};

// 遊戲狀態
let gameState = {
    gold: CONFIG.INITIAL_GOLD,
    level: 1,
    playerCastle: null,
    enemyCastle: null,
    units: [],
    running: false,
    autoMode: false,
    autoTimer: 0,
    playerStats: {
        atkBonus: 1.0,
        hpBonus: 1.0,
        speedBonus: 1.0
    }
};

// Canvas 設置
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

function resizeCanvas() {
    const container = document.getElementById('gameContainer');
    const topBar = document.getElementById('topBar');
    const controls = document.getElementById('controls');
    const availableHeight = window.innerHeight - topBar.offsetHeight - controls.offsetHeight;
    
    canvas.width = window.innerWidth;
    canvas.height = availableHeight;
}

window.addEventListener('resize', resizeCanvas);
resizeCanvas();

// 兵種相剋
function getMultiplier(attacker, defender) {
    if ((attacker === 0 && defender === 1) || 
        (attacker === 1 && defender === 2) || 
        (attacker === 2 && defender === 0)) {
        return 1.2;
    }
    return 1.0;
}

// 城堡類
class Castle {
    constructor(x, y, team) {
        this.x = x;
        this.y = y;
        this.team = team; // 0=玩家, 1=敵人
        this.maxHp = 1000;
        this.hp = 1000;
        this.width = 80;
        this.height = 60;
    }

    takeDamage(damage) {
        this.hp = Math.max(0, this.hp - damage);
        if (this.hp <= 0) {
            gameOver(this.team === 1);
        }
    }

    draw() {
        const color = this.team === 0 ? '#4A90E2' : '#E74C3C';
        
        // 城堡主體
        ctx.fillStyle = color;
        ctx.fillRect(this.x - this.width/2, this.y - this.height/2, this.width, this.height);
        
        // 城堡細節
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeRect(this.x - this.width/2, this.y - this.height/2, this.width, this.height);
        
        // 旗幟
        ctx.fillStyle = this.team === 0 ? '#2ECC71' : '#9B59B6';
        ctx.beginPath();
        ctx.moveTo(this.x, this.y - this.height/2);
        ctx.lineTo(this.x, this.y - this.height/2 - 30);
        ctx.lineTo(this.x + 20, this.y - this.height/2 - 20);
        ctx.lineTo(this.x, this.y - this.height/2 - 10);
        ctx.fill();
        ctx.stroke();
        
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

// 單位類
class Unit {
    constructor(x, y, team, type) {
        this.x = x;
        this.y = y;
        this.team = team;
        this.type = type; // 0=槍, 1=騎, 2=弓
        
        const baseHp = type === 1 ? 80 : type === 2 ? 70 : 100;
        const baseAtk = type === 1 ? 25 : type === 2 ? 18 : 20;
        const baseSpeed = type === 1 ? 4 : type === 2 ? 2.5 : 3;
        
        if (team === 0) {
            this.maxHp = baseHp * gameState.playerStats.hpBonus;
            this.hp = this.maxHp;
            this.atk = baseAtk * gameState.playerStats.atkBonus;
            this.speed = baseSpeed * gameState.playerStats.speedBonus;
        } else {
            this.maxHp = baseHp * (1 + gameState.level * 0.1);
            this.hp = this.maxHp;
            this.atk = baseAtk * (1 + gameState.level * 0.1);
            this.speed = baseSpeed;
        }
        
        this.target = null;
        this.attackCooldown = 0;
        this.radius = 8;
    }

    update(deltaTime) {
        if (this.attackCooldown > 0) {
            this.attackCooldown -= deltaTime;
        }

        // 尋找目標
        if (!this.target || this.target.hp <= 0) {
            this.findTarget();
        }

        // 移動和攻擊
        if (this.target) {
            const dx = this.target.x - this.x;
            const dy = this.target.y - this.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const attackRange = CONFIG.UNIT_ATTACK_RANGES[this.type];

            if (dist > attackRange) {
                // 移動向目標
                const moveX = (dx / dist) * this.speed;
                const moveY = (dy / dist) * this.speed;
                this.x += moveX;
                this.y += moveY;
                
                // 限制在場地內
                this.x = Math.max(20, Math.min(canvas.width - 20, this.x));
                this.y = Math.max(20, Math.min(canvas.height - 20, this.y));
            } else {
                // 攻擊
                if (this.attackCooldown <= 0) {
                    this.attack(this.target);
                    this.attackCooldown = 1000; // 1秒攻擊間隔
                }
            }
        }
    }

    findTarget() {
        // 優先攻擊敵方單位，其次攻擊城堡
        const enemies = gameState.units.filter(u => u.team !== this.team && u.hp > 0);
        
        if (enemies.length > 0) {
            this.target = enemies.reduce((closest, u) => {
                const dist = Math.sqrt((u.x - this.x) ** 2 + (u.y - this.y) ** 2);
                const closestDist = Math.sqrt((closest.x - this.x) ** 2 + (closest.y - this.y) ** 2);
                return dist < closestDist ? u : closest;
            });
        } else {
            // 攻擊敵方城堡
            this.target = this.team === 0 ? gameState.enemyCastle : gameState.playerCastle;
        }
    }

    attack(target) {
        let damage = this.atk;
        
        if (target instanceof Unit) {
            damage *= getMultiplier(this.type, target.type);
        }
        
        target.takeDamage(damage);
        
        // 視覺效果 - 攻擊線
        if (target instanceof Unit || target instanceof Castle) {
            ctx.strokeStyle = CONFIG.UNIT_COLORS[this.type];
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(this.x, this.y);
            ctx.lineTo(target.x, target.y);
            ctx.stroke();
        }
    }

    takeDamage(damage) {
        this.hp = Math.max(0, this.hp - damage);
        
        if (this.hp <= 0) {
            // 給予金幣獎勵（只有擊殺敵人時）
            if (this.team === 1) {
                gameState.gold += CONFIG.GOLD_PER_KILL;
                updateUI();
            }
        }
    }

    draw() {
        if (this.hp <= 0) return;
        
        // 單位圓形
        ctx.fillStyle = CONFIG.UNIT_COLORS[this.type];
        if (this.team === 1) {
            ctx.globalAlpha = 0.7; // 敵人略透明
        }
        
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        ctx.globalAlpha = 1.0;
        
        // 類型標記
        ctx.fillStyle = '#FFF';
        ctx.font = 'bold 10px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const icon = this.type === 0 ? '槍' : this.type === 1 ? '騎' : '弓';
        ctx.fillText(icon, this.x, this.y);
        
        // HP 條
        const barWidth = this.radius * 2.5;
        const barHeight = 4;
        const hpPercent = this.hp / this.maxHp;
        
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x - barWidth/2, this.y - this.radius - 8, barWidth, barHeight);
        
        ctx.fillStyle = hpPercent > 0.5 ? '#2ECC71' : hpPercent > 0.25 ? '#F39C12' : '#E74C3C';
        ctx.fillRect(this.x - barWidth/2, this.y - this.radius - 8, barWidth * hpPercent, barHeight);
    }
}

// 召喚單位
function spawnUnit(type) {
    const cost = CONFIG.UNIT_COSTS[type];
    
    if (gameState.gold < cost) {
        return;
    }
    
    gameState.gold -= cost;
    
    // 在玩家城堡附近隨機位置生成
    const x = gameState.playerCastle.x + (Math.random() - 0.5) * 100;
    const y = gameState.playerCastle.y + (Math.random() - 0.5) * 80;
    
    const unit = new Unit(x, y, 0, type);
    gameState.units.push(unit);
    
    updateUI();
}

// 生成敵方單位
function spawnEnemyUnit() {
    const types = [0, 1, 2];
    const type = types[Math.floor(Math.random() * types.length)];
    
    const x = gameState.enemyCastle.x + (Math.random() - 0.5) * 100;
    const y = gameState.enemyCastle.y + (Math.random() - 0.5) * 80;
    
    const unit = new Unit(x, y, 1, type);
    gameState.units.push(unit);
}

// 升級菜單
function showUpgradeMenu() {
    if (gameState.gold < CONFIG.UPGRADE_COST) {
        return;
    }
    
    const options = [
        '攻擊力 +20%',
        '生命值 +20%',
        '移動速度 +20%'
    ];
    
    const choice = confirm(`選擇升級 (💰${CONFIG.UPGRADE_COST}):\n1. ${options[0]}\n2. ${options[1]}\n3. ${options[2]}\n\n點擊確定升級攻擊力，取消可選其他`);
    
    gameState.gold -= CONFIG.UPGRADE_COST;
    
    if (choice) {
        gameState.playerStats.atkBonus *= 1.2;
    } else {
        const choice2 = confirm('升級生命值？(確定=生命值，取消=速度)');
        if (choice2) {
            gameState.playerStats.hpBonus *= 1.2;
        } else {
            gameState.playerStats.speedBonus *= 1.2;
        }
    }
    
    updateUI();
}

// 自動模式
function toggleAuto() {
    gameState.autoMode = !gameState.autoMode;
    const btn = document.getElementById('autoBtn');
    btn.innerHTML = gameState.autoMode ? '自動<br>開啟' : '自動<br>關閉';
    btn.style.background = gameState.autoMode ? 
        'linear-gradient(145deg, #27AE60, #1E8449)' : 
        'linear-gradient(145deg, #1ABC9C, #16A085)';
}

// 下一波
function nextWave() {
    gameState.level++;
    gameState.gold += 50;
    
    // 重置敵方城堡
    gameState.enemyCastle.hp = gameState.enemyCastle.maxHp * (1 + gameState.level * 0.1);
    gameState.enemyCastle.maxHp = gameState.enemyCastle.hp;
    
    // 清除所有敵方單位
    gameState.units = gameState.units.filter(u => u.team === 0);
    
    updateUI();
}

// 更新 UI
function updateUI() {
    document.getElementById('gold').textContent = Math.floor(gameState.gold);
    document.getElementById('level').textContent = gameState.level;
    document.getElementById('playerHP').textContent = Math.floor(gameState.playerCastle.hp);
    document.getElementById('enemyHP').textContent = Math.floor(gameState.enemyCastle.hp);
}

// 遊戲結束
function gameOver(victory) {
    gameState.running = false;
    
    const screen = document.getElementById('gameOverScreen');
    const title = document.getElementById('gameOverTitle');
    const stats = document.getElementById('gameOverStats');
    
    if (victory) {
        title.textContent = '🎉 勝利！';
        title.style.color = '#2ECC71';
        stats.textContent = `完成關卡：${gameState.level}\n獲得金幣：${Math.floor(gameState.gold)}`;
    } else {
        title.textContent = '💀 失敗';
        title.style.color = '#E74C3C';
        stats.textContent = `堅持到關卡：${gameState.level}`;
    }
    
    screen.classList.remove('hidden');
}

// 遊戲循環
let lastTime = 0;
let enemySpawnTimer = 0;

function gameLoop(currentTime) {
    if (!gameState.running) return;
    
    const deltaTime = currentTime - lastTime;
    lastTime = currentTime;
    
    // 清空畫布
    ctx.fillStyle = 'rgba(44, 62, 80, 0.3)';
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
    gameState.playerCastle.draw();
    gameState.enemyCastle.draw();
    
    // 更新和繪製單位
    gameState.units = gameState.units.filter(u => u.hp > 0);
    gameState.units.forEach(unit => {
        unit.update(deltaTime);
        unit.draw();
    });
    
    // 敵人生成邏輯
    enemySpawnTimer += deltaTime;
    const spawnInterval = Math.max(2000, 5000 - gameState.level * 200);
    if (enemySpawnTimer > spawnInterval) {
        spawnEnemyUnit();
        enemySpawnTimer = 0;
    }
    
    // 自動模式
    if (gameState.autoMode) {
        gameState.autoTimer += deltaTime;
        if (gameState.autoTimer > 1500) {
            const types = [0, 1, 2];
            const type = types[Math.floor(Math.random() * types.length)];
            if (gameState.gold >= CONFIG.UNIT_COSTS[type]) {
                spawnUnit(type);
            }
            gameState.autoTimer = 0;
        }
    }
    
    updateUI();
    requestAnimationFrame(gameLoop);
}

// 開始遊戲
function startGame() {
    document.getElementById('startScreen').classList.add('hidden');
    
    // 初始化城堡
    gameState.playerCastle = new Castle(canvas.width / 2, canvas.height - 80, 0);
    gameState.enemyCastle = new Castle(canvas.width / 2, 80, 1);
    
    gameState.running = true;
    lastTime = performance.now();
    requestAnimationFrame(gameLoop);
}

// 觸控支援
canvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
}, { passive: false });

// 阻止雙指縮放
document.addEventListener('gesturestart', (e) => {
    e.preventDefault();
});
