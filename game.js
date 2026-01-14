// ============================================================
// 遊戲主邏輯 - game.js
// 核心遊戲循環、UI 更新、遊戲控制
// ============================================================

// === 全局遊戲狀態 ===
let gameState = {
    playerCastle: null,
    enemyCastle: null,
    units: [],
    wave: 1,
    maxWaves: 8,
    running: false,
    autoMode: false,
    gameSpeed: 1.0,
    startTime: 0,
    lastTime: 0,
    damageTexts: [],
    particles: []
};

// Canvas 設置
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// 根據窗口大小調整 canvas
function resizeCanvas() {
    const gameScreen = document.getElementById('gameScreen');
    const topBar = document.getElementById('topBar');
    const controls = document.getElementById('gameControls');
    
    if (gameScreen && gameScreen.style.display !== 'none') {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight - (topBar?.offsetHeight || 0) - (controls?.offsetHeight || 0);
    }
}

window.addEventListener('resize', resizeCanvas);

// === UI 更新函數 ===
function updateUI() {
    const playerHPElem = document.getElementById('playerHP');
    const enemyHPElem = document.getElementById('enemyHP');
    const waveNumElem = document.getElementById('waveNum');
    const goldElem = document.getElementById('gold');
    const timerElem = document.getElementById('timer');
    
    if (playerHPElem) playerHPElem.textContent = Math.max(0, Math.floor(gameState.playerCastle.hp));
    if (enemyHPElem) enemyHPElem.textContent = Math.max(0, Math.floor(gameState.enemyCastle.hp));
    if (waveNumElem) waveNumElem.textContent = `${gameState.wave}/${gameState.maxWaves}`;
    if (goldElem) goldElem.textContent = player.gold;
    
    if (timerElem) {
        const elapsed = (Date.now() - gameState.startTime) / 1000;
        const mins = Math.floor(elapsed / 60);
        const secs = Math.floor(elapsed % 60);
        timerElem.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// === 主遊戲循環 ===
function gameLoop(currentTime) {
    if (!gameState.running) return;
    
    const deltaTime = Math.min((currentTime - gameState.lastTime) / 1000, 0.016) * gameState.gameSpeed;
    gameState.lastTime = currentTime;
    
    // 清空畫布
    ctx.fillStyle = 'rgba(15, 20, 25, 0.5)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 繪製中線分割區域
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 10]);
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
    ctx.setLineDash([]);
    
    // 更新和繪製城堡
    if (gameState.playerCastle) gameState.playerCastle.draw(ctx);
    if (gameState.enemyCastle) gameState.enemyCastle.draw(ctx);
    
    // 更新和繪製單位
    gameState.units = gameState.units.filter(u => u.hp > 0);
    gameState.units.forEach(unit => {
        unit.update(gameState.units, [gameState.playerCastle, gameState.enemyCastle], gameState);
        unit.draw(ctx);
    });
    
    // 更新粒子效果
    gameState.particles = gameState.particles.filter(p => p.life > 0);
    gameState.particles.forEach(p => {
        p.update(deltaTime);
        p.draw(ctx);
    });
    
    // 更新傷害文字浮動
    gameState.damageTexts = gameState.damageTexts.filter(([_, __, life]) => life > 0);
    gameState.damageTexts.forEach(text => {
        text[2]--;
        const alpha = text[2] / 60;
        ctx.fillStyle = `rgba(255, 100, 100, ${alpha})`;
        ctx.font = 'bold 18px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(text[1], text[0][0], text[0][1] - 10 * (1 - alpha));
    });
    
    // 敵人生成邏輯
    if (gameState.units.filter(u => u.team === 1).length < 8) {
        // 根據波數增加敵人數量
        const enemyLimit = Math.min(3 + gameState.wave, 8);
        if (gameState.units.filter(u => u.team === 1).length < enemyLimit && Math.random() < 0.02) {
            spawnEnemyUnit();
        }
    }
    
    // 檢查波數完成
    if (gameState.wave <= gameState.maxWaves && 
        gameState.units.filter(u => u.team === 1).length === 0 &&
        gameState.units.filter(u => u.team === 0).length > 0) {
        gameState.wave++;
    }
    
    // 檢查遊戲結束
    if (gameState.playerCastle.hp <= 0) {
        endGame(false);
        return;
    }
    if (gameState.wave > gameState.maxWaves && gameState.units.filter(u => u.team === 1).length === 0) {
        // 所有波次完成
        endGame(true);
        return;
    }
    
    updateUI();
    requestAnimationFrame(gameLoop);
}

// === 生成敵人單位 ===
function spawnEnemyUnit() {
    const heroData = HERO_POOL[Math.floor(Math.random() * HERO_POOL.length)];
    
    // 根據波數計算敵人屬性倍數
    const levelMult = 1 + (gameState.wave - 1) * 0.15;
    const hp = Math.floor(heroData.base_hp * levelMult);
    const atk = Math.floor(heroData.base_atk * levelMult);
    const speed = heroData.base_speed * levelMult;
    
    // 隨機生成位置（敵人上方）
    const x = canvas.width / 2 + (Math.random() - 0.5) * 400;
    const y = 80 + Math.random() * 80;
    
    const unit = new Unit(
        `敵-${heroData.name}`,
        x, y,
        1, // team = 1（敵方）
        heroData.type,
        hp, atk, speed
    );
    
    gameState.units.push(unit);
}

// === 開始遊戲 ===
function startGame() {
    const teamCards = player.getTeamCards();
    
    if (teamCards.length === 0) {
        alert('❌ 請先組建隊伍！(需要 3 名英雄)');
        return;
    }
    
    resizeCanvas();
    
    // 初始化戰鬥配置
    const chapterIdx = Math.max(0, Math.min(player.currentChapter - 1, 2));
    const chapter = CHAPTER_CONFIGS[chapterIdx];
    
    gameState.maxWaves = chapter.waves;
    gameState.playerCastle = new Castle(canvas.width / 2, canvas.height - 120, 0);
    gameState.enemyCastle = new Castle(canvas.width / 2, 80, 1, chapter.has_boss);
    gameState.units = [];
    gameState.wave = 1;
    gameState.running = true;
    gameState.autoMode = false;
    gameState.gameSpeed = 1.0;
    gameState.startTime = Date.now();
    gameState.lastTime = Date.now();
    gameState.damageTexts = [];
    gameState.particles = [];
    
    // 創建玩家單位（隊伍中的英雄）
    teamCards.forEach((card, idx) => {
        const { maxHp, atk, speed } = card.stats();
        
        // 按陣容排列
        const spacing = 180;
        const centerX = canvas.width / 2;
        const x = centerX - spacing + idx * spacing;
        const y = canvas.height - 180;
        
        const unit = new Unit(
            `${card.name} Lv${card.level}`,
            x, y,
            0, // team = 0（玩家方）
            card.unitType,
            maxHp, atk, speed
        );
        
        // 應用英雄專精
        unit.applySpecialization(card.name);
        
        gameState.units.push(unit);
    });
    
    // 切換到遊戲畫面
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('gameScreen').style.display = 'flex';
    
    gameState.lastTime = Date.now();
    requestAnimationFrame(gameLoop);
}

// === 遊戲結束 ===
function endGame(victory) {
    gameState.running = false;
    
    if (victory) {
        const goldReward = 500 * gameState.wave;
        const gemReward = 50 + 10 * gameState.wave;
        
        player.gold += goldReward;
        player.gems += gemReward;
        player.currentChapter = Math.min(player.currentChapter + 1, 3);
        player.save();
        
        alert(`🎉 勝利！\n\n獲得金幣: +${goldReward}\n獲得鑽石: +${gemReward}\n\n推進章節 → 第 ${player.currentChapter} 章`);
    } else {
        player.save();
        alert(`💀 戰敗\n\n堅持到第 ${gameState.wave} 波`);
    }
    
    backToMenu();
}

// === 返回菜單 ===
function backToMenu() {
    gameState.running = false;
    document.getElementById('gameScreen').style.display = 'none';
    document.getElementById('mainMenu').style.display = 'flex';
}

// === 控制功能 ===
function toggleAuto() {
    if (!gameState.running) return;
    gameState.autoMode = !gameState.autoMode;
    const btn = document.querySelector('#gameControls button:nth-child(1)');
    if (btn) {
        btn.textContent = gameState.autoMode ? '🤖 自動 ON' : '🤖 自動 OFF';
    }
}

function changeSpeed() {
    if (!gameState.running) return;
    const speeds = [1.0, 1.5, 2.0];
    const currentIdx = speeds.indexOf(gameState.gameSpeed);
    gameState.gameSpeed = speeds[(currentIdx + 1) % speeds.length];
    
    const btn = document.querySelector('#gameControls button:nth-child(2)');
    if (btn) {
        btn.textContent = `⏱️ ${gameState.gameSpeed.toFixed(1)}x`;
    }
}

// === 隊伍管理功能 ===
function showTeam() {
    const roster = player.roster;
    if (roster.length === 0) {
        alert('📭 還沒有英雄，進行 10 連抽獲取！');
        return;
    }
    
    const cardListText = roster.map((card, i) =>
        `${i + 1}. ${card.name} Lv${card.level} ${card.stars}⭐ (${card.rarity})`
    ).join('\n');
    
    const currentTeam = player.getTeamCards().map(c => c.name).join(', ') || '(空)';
    
    alert(`📚 英雄圖鑑：\n${cardListText}\n\n當前隊伍：${currentTeam}`);
}

// === 抽卡功能 ===
function showGacha() {
    const times = parseInt(prompt('輸入抽卡次數：\n1 = 單抽 (10鑽)\n10 = 十連 (100鑽)', '10'));
    
    if (!times || times < 1 || times > 10) {
        alert('❌ 輸入的次數無效');
        return;
    }
    
    const cost = times * 10;
    if (player.gems < cost) {
        alert(`❌ 鑽石不足！需要 ${cost} 顆鑽石`);
        return;
    }
    
    const results = player.gacha(times);
    player.gems -= cost;
    player.save();
    
    const resultText = results
        .map(r => `✨ ${r.name} (${r.rarity})`)
        .join('\n');
    
    alert(`🎁 抽卡結果：\n${resultText}\n\n當前鑽石: ${player.gems}`);
}

// === 任務系統 ===
function showQuests() {
    const daily = player.dailyQuests
        .map(q => `✓ ${q.name}: ${q.progress}/${q.target}`)
        .join('\n');
    
    alert(`📋 每日任務：\n${daily}`);
}

// === 初始化遊戲 ===
window.addEventListener('DOMContentLoaded', () => {
    // 載入玩家數據
    player.load();
    
    // 首次遊戲初始化
    if (player.roster.length === 0) {
        // 進行首次 10 連抽
        const results = player.gacha(10);
        player.team = results.slice(0, 3).map(r => r.id);
        player.save();
        
        alert(`🎬 歡迎遊戲！\n\n首次 10 連抽結果：\n${results.map(r => r.name).join('\n')}`);
    }
    
    console.log('✅ 遊戲已加載完成');
    console.log('玩家數據:', player);
});
