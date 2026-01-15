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
    particles: [],
    // 波間準備系統
    waitingForEvent: false,
    prepCountdown: 0,
    prepTime: 3,
    eventChoices: [],
    // Roguelite 狀態
    activeBuffs: [],
    activeCurses: [],
    critChance: 0,
    damageReduction: 0,
    lifestealRate: 0,
    // 商店狀態
    shopItems: [],
    shopLocked: [],
    refreshCount: 0
};

// Canvas 設置
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// === 滑鼠事件處理 ===
let selectedUnit = null;

canvas.addEventListener('click', (event) => {
    if (!gameState.running || gameState.waitingForEvent) return;
    
    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    
    // 查找被點擊的玩家單位
    const playerUnits = gameState.units.filter(u => u.team === 0 && u.hp > 0);
    playerUnits.forEach(unit => {
        const dist = Math.hypot(mouseX - unit.pos[0], mouseY - unit.pos[1]);
        if (dist < 30) {
            selectedUnit = unit;
            unit.selected = true;
        } else {
            unit.selected = false;
        }
    });
});

canvas.addEventListener('contextmenu', (event) => {
    event.preventDefault();
    if (!gameState.running || !selectedUnit || gameState.waitingForEvent) return;
    
    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    
    // 查找敵人單位作為攻擊目標
    const enemyUnits = gameState.units.filter(u => u.team === 1 && u.hp > 0);
    let targetFound = false;
    
    enemyUnits.forEach(unit => {
        const dist = Math.hypot(mouseX - unit.pos[0], mouseY - unit.pos[1]);
        if (dist < 30) {
            selectedUnit.targetEnemy = unit;
            selectedUnit.targetPos = null;
            targetFound = true;
        }
    });
    
    if (!targetFound) {
        selectedUnit.targetEnemy = null;
    }
});

canvas.addEventListener('mouseup', (event) => {
    if (!gameState.running || !selectedUnit || gameState.waitingForEvent) return;
    
    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    
    // 設置移動目標
    selectedUnit.targetPos = [mouseX, mouseY];
    selectedUnit = null;
});

// Canvas 設置

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
    
    // 自動戰鬥邏輯：玩家單位自動向敵方城堡方向移動
    if (gameState.autoMode) {
        gameState.units.forEach(unit => {
            if (unit.team === 0 && unit.hp > 0 && !unit.targetPos) {
                // 向敵方城堡方向移動
                unit.targetPos = [gameState.enemyCastle.pos[0], gameState.enemyCastle.pos[1] + 80];
            }
        });
    }
    
    // === 波次敵人生成邏輯（按波生成，非持續） ===
    const currentEnemies = gameState.units.filter(u => u.team === 1 && u.hp > 0);
    
    if (currentEnemies.length === 0) {
        // 檢查是否完成所有波次
        if (gameState.wave > gameState.maxWaves) {
            endGame(true);
            return;
        }
        
        // 如果是第2波或以後，觸發波間準備階段
        if (gameState.wave > 1 && !gameState.waitingForEvent) {
            startWavePreparation();
        } else if (!gameState.waitingForEvent) {
            // 第一波直接開始
            spawnWave();
        }
    }
    
    // 處理波間準備倒計時
    if (gameState.waitingForEvent) {
        gameState.prepCountdown -= deltaTime;
        if (gameState.prepCountdown <= 0) {
            // 準備時間結束，自動應用第一個事件
            if (gameState.eventChoices.length > 0) {
                applyEvent(gameState.eventChoices[0]);
            }
            gameState.waitingForEvent = false;
            spawnWave();
        }
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

// === 按波次生成敵人（根據章節配置） ===
function spawnWave() {
    gameState.wave++;  // 先遞增波數
    
    const chapterIdx = Math.max(0, Math.min(player.currentChapter - 1, 2));
    const chapter = CHAPTER_CONFIGS[chapterIdx];
    
    const baseHp = chapter.base_hp + (gameState.wave - 2) * 20;  // 調整計算
    const baseAtk = chapter.base_atk + (gameState.wave - 2) * 3;
    
    // 生成3個敵人（槍、騎、弓各1）
    const types = [0, 1, 2];
    const xPositions = [canvas.width/2 - 200, canvas.width/2, canvas.width/2 + 200];
    
    types.forEach((type, idx) => {
        const hp = Math.floor(baseHp * (type === 0 ? 0.56 : type === 1 ? 0.7 : 0.49));
        const atk = Math.floor(baseAtk * 0.7);
        const speed = 3 + Math.random();
        
        const typeNames = ['槍', '騎', '弓'];
        const unit = new Unit(
            `敵${typeNames[type]}${gameState.wave}`,
            xPositions[idx],
            120,
            1,
            type,
            hp,
            atk,
            speed
        );
        gameState.units.push(unit);
    });
}

// === 開始波間準備階段 ===
function startWavePreparation() {
    gameState.waitingForEvent = true;
    gameState.prepCountdown = gameState.prepTime;
    
    // 混合基礎事件、Buff 和 Curse
    const baseEvents = [...WAVE_EVENTS];
    const buffOptions = ROGUELITE_BUFFS.slice(0, 2).sort(() => Math.random() - 0.5);
    const curseOptions = ROGUELITE_CURSES.slice(0, 1).sort(() => Math.random() - 0.5);
    
    let allOptions = [...baseEvents, ...buffOptions, ...curseOptions];
    
    // 隨機選擇3個事件
    gameState.eventChoices = [];
    for (let i = 0; i < 3 && allOptions.length > 0; i++) {
        const randomIdx = Math.floor(Math.random() * allOptions.length);
        gameState.eventChoices.push(allOptions[randomIdx]);
        allOptions.splice(randomIdx, 1);
    }
    
    // 顯示波間準備UI
    showWavePrepUI();
}

// === 應用事件效果 ===
function applyEvent(event) {
    const effect = event.effect;
    
    // 基礎波間事件
    if (effect === 'heal') {
        gameState.units.forEach(u => {
            if (u.team === 0 && u.hp > 0) {
                u.hp = Math.min(u.maxHp, u.hp + u.maxHp * 0.25);
            }
        });
    } else if (effect === 'curse') {
        gameState.units.forEach(u => {
            if (u.team === 1) {
                u.atk *= 0.8;
            }
        });
    } else if (effect === 'fewer_enemies') {
        // 標記下波少生成1個敵人（在 spawnWave 中處理）
        gameState.fewerEnemies = true;
    } else if (effect === 'slow') {
        gameState.units.forEach(u => {
            u.speed *= 0.7;
        });
    }
    
    // Roguelite Buff 效果
    if (event.type === 'buff') {
        gameState.activeBuffs.push(event.name);
        
        if (effect === 'atk_speed') {
            gameState.units.forEach(u => {
                if (u.team === 0) u.attackInterval *= 0.7;
            });
        } else if (effect === 'crit') {
            gameState.critChance = 0.25;
        } else if (effect === 'move_speed') {
            gameState.units.forEach(u => {
                if (u.team === 0) u.speed *= 1.4;
            });
        } else if (effect === 'lifesteal') {
            gameState.lifestealRate = 0.15;
        } else if (effect === 'armor') {
            gameState.damageReduction = 0.25;
        } else if (effect === 'cooldown') {
            gameState.units.forEach(u => {
                if (u.team === 0 && u.skill) {
                    u.skill.cooldown *= 0.6;
                }
            });
        }
    }
    
    // Roguelite Curse 效果
    if (event.type === 'curse') {
        gameState.activeCurses.push(event.name);
        
        if (effect === 'weakness') {
            gameState.units.forEach(u => {
                if (u.team === 0) u.atk *= 0.7;
            });
        } else if (effect === 'curse_slow') {
            gameState.units.forEach(u => {
                if (u.team === 0) u.speed *= 0.5;
            });
        } else if (effect === 'curse_fragile') {
            gameState.damageReduction = -0.4;
        }
    }
}

// === 開始遊戲 ===
function startGame() {
    const teamCards = player.getTeamCards();
    
    if (teamCards.length === 0) {
        alert('❌ 請先組建隊伍！(需要 3 名英雄)');
        return;
    }
    
    // 切換到遊戲畫面
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('gameScreen').style.display = 'flex';
    
    // 現在畫面已顯示，設置 Canvas 大小
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
    // 初始化波間準備系統
    gameState.waitingForEvent = false;
    gameState.prepCountdown = 0;
    gameState.eventChoices = [];
    gameState.activeBuffs = [];
    gameState.activeCurses = [];
    gameState.critChance = 0;
    gameState.damageReduction = 0;
    gameState.lifestealRate = 0;
    
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
    
    // 現在畫面已顯示，設置 Canvas 大小
    resizeCanvas();
    
    gameState.lastTime = Date.now();
    // 開始遊戲循環 (60 FPS)
    setInterval(() => {
        if (gameState.running) {
            gameLoop(Date.now());
        }
    }, 16);
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
    updateMenuResources();
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
    
    const cardListText = roster.map((card, i) => {
        const stats = card.stats();
        const typeIcon = { 0: '🔱槍', 1: '🐎騎', 2: '🏹弓' }[card.unitType];
        return `${i + 1}. ${card.name} ${typeIcon} Lv${card.level} ${card.stars}⭐ (${card.rarity})\n   HP:${Math.floor(stats.maxHp)} ATK:${Math.floor(stats.atk)} SPD:${stats.speed.toFixed(1)}`;
    }).join('\n\n');
    
    const currentTeam = player.getTeamCards();
    const teamText = currentTeam.length > 0 
        ? currentTeam.map((c, i) => `${i + 1}. ${c.name} Lv${c.level}`).join('\n') 
        : '(空)';
    
    alert(`📚 英雄圖鑑 (${roster.length}名)：\n\n${cardListText}\n\n━━━━━━━━━━━━━━━━━━\n⚔️ 當前隊伍：\n${teamText}\n\n💡 提示：隊伍自動選擇前3名英雄`);
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
    updateMenuResources();
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
        
        const heroList = results.map((r, i) => `${i + 1}. ${r.name} (${r.rarity})`).join('\n');
        alert(`🎉 歡迎來到三國戰記！\n\n🎁 新手禮包：免費 10 連抽\n\n獲得英雄：\n${heroList}\n\n✅ 已自動組建隊伍（前3名英雄）\n\n💡 點擊「開始遊戲」開始戰鬥！`);
    }
    
    console.log('✅ 遊戲已加載完成');
    console.log('💰 金幣:', player.gold, '💎 鑽石:', player.gems);
    console.log('🎴 擁有英雄:', player.roster.length, '名');
    console.log('⚔️ 當前隊伍:', player.getTeamCards().map(c => c.name).join(', '));
    
    // 更新主菜單資源顯示
    updateMenuResources();
});

// 更新主菜單資源顯示
function updateMenuResources() {
    const goldElem = document.getElementById('menuGold');
    const gemsElem = document.getElementById('menuGems');
    if (goldElem) goldElem.textContent = `💰 金幣: ${player.gold}`;
    if (gemsElem) gemsElem.textContent = `💎 鑽石: ${player.gems}`;
}

// === 波間準備UI顯示 ===
function showWavePrepUI() {
    const overlay = document.getElementById('wavePrepOverlay');
    const prepButtons = document.getElementById('prepButtons');
    const prepStatus = document.getElementById('prepStatus');
    
    if (!overlay || !prepButtons) return;
    
    // 顯示浮層
    overlay.style.display = 'flex';
    
    // 更新狀態顯示
    prepStatus.textContent = `✨ 增益: ${gameState.activeBuffs.length} | 💀 詛咒: ${gameState.activeCurses.length}`;
    
    // 清空並生成事件按鈕
    prepButtons.innerHTML = '';
    gameState.eventChoices.forEach((event, idx) => {
        const button = document.createElement('button');
        button.className = event.type === 'curse' ? 'event-btn curse' : 'event-btn';
        
        const icon = event.type === 'buff' ? '✨' : event.type === 'curse' ? '💀' : '⚔';
        button.textContent = `${icon} ${event.name} - ${event.desc}`;
        
        button.onclick = () => {
            applyEvent(event);
            hideWavePrepUI();
            spawnWave();
        };
        
        prepButtons.appendChild(button);
    });
    
    // 啟動倒計時更新
    updatePrepCountdown();
}

function updatePrepCountdown() {
    const countdownElem = document.getElementById('prepCountdownText');
    if (countdownElem && gameState.waitingForEvent) {
        countdownElem.textContent = Math.max(0, Math.ceil(gameState.prepCountdown));
        setTimeout(updatePrepCountdown, 100);
    }
}

function hideWavePrepUI() {
    const overlay = document.getElementById('wavePrepOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// === 商店系統 ===
function openShop() {
    const shopHtml = `
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                    background: rgba(0,0,0,0.9); z-index: 1000; display: flex; 
                    justify-content: center; align-items: center;" id="shopModal">
            <div style="background: linear-gradient(135deg, #1A1A2E, #16213E); 
                        border-radius: 20px; padding: 30px; max-width: 500px; max-height: 80vh; 
                        overflow-y: auto;">
                <h2 style="color: #F39C12; text-align: center; margin-bottom: 20px;">🏪 戰鬥商店</h2>
                <p style="color: #BDC3C7; text-align: center; margin-bottom: 20px;">
                    💰 金幣: ${player.gold}
                </p>
                <div id="shopItemsContainer">
                    ${generateShopItems()}
                </div>
                <button onclick="closeShop()" 
                        style="width: 100%; padding: 15px; background: #E74C3C; color: white; 
                               border: none; border-radius: 10px; font-size: 16px; font-weight: bold; 
                               cursor: pointer; margin-top: 20px;">
                    關閉
                </button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', shopHtml);
}

function generateShopItems() {
    // 獲取 SHOP_ITEMS（確保從 config.js 導入）
    const items = typeof SHOP_ITEMS !== 'undefined' ? SHOP_ITEMS : [];
    
    if (items.length === 0) {
        return '<p style="color: #BDC3C7; text-align: center;">商店暫時無貨</p>';
    }
    
    return items.slice(0, 5).map((item, idx) => {
        const canAfford = player.gold >= item.cost;
        const btnColor = canAfford ? '#2ECC71' : '#95A5A6';
        
        return `
            <div style="background: rgba(255,255,255,0.1); border-radius: 10px; 
                        padding: 15px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #ECF0F1; font-size: 18px; font-weight: bold;">
                            ${item.icon} ${item.name}
                        </div>
                        <div style="color: #BDC3C7; font-size: 14px; margin-top: 5px;">
                            ${item.desc}
                        </div>
                        <div style="color: #F39C12; font-size: 16px; font-weight: bold; margin-top: 8px;">
                            ${item.cost} 金幣
                        </div>
                    </div>
                    <button onclick="buyShopItem(${idx})" 
                            style="padding: 10px 20px; background: ${btnColor}; color: white; 
                                   border: none; border-radius: 8px; font-size: 14px; font-weight: bold; 
                                   cursor: ${canAfford ? 'pointer' : 'not-allowed'};"
                            ${canAfford ? '' : 'disabled'}>
                        購買
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function buyShopItem(idx) {
    const items = typeof SHOP_ITEMS !== 'undefined' ? SHOP_ITEMS : [];
    if (idx < 0 || idx >= items.length) return;
    
    const item = items[idx];
    if (player.gold < item.cost) {
        alert('❌ 金幣不足！');
        return;
    }
    
    player.gold -= item.cost;
    player.save();
    
    // 應用商店物品效果
    useShopItem(item);
    
    // 重新渲染商店
    closeShop();
    openShop();
}

function useShopItem(item) {
    const effect = item.effect;
    
    if (effect === 'heal') {
        gameState.units.forEach(u => {
            if (u.team === 0 && u.hp > 0) {
                u.hp = Math.min(u.maxHp, u.hp + item.value);
            }
        });
        alert(`✅ 恢復了 ${item.value} HP`);
    } else if (effect === 'atk_boost') {
        gameState.units.forEach(u => {
            if (u.team === 0) {
                u.atk = Math.floor(u.atk * (1 + item.value));
            }
        });
        alert(`✅ 攻擊力提升 ${Math.floor(item.value * 100)}%`);
    } else if (effect === 'def_boost') {
        gameState.damageReduction += item.value;
        alert(`✅ 傷害減免提升 ${Math.floor(item.value * 100)}%`);
    } else if (effect === 'speed_boost') {
        gameState.units.forEach(u => {
            if (u.team === 0) {
                u.speed *= (1 + item.value);
            }
        });
        alert(`✅ 移動速度提升 ${Math.floor(item.value * 100)}%`);
    } else if (effect === 'super_potion') {
        gameState.units.forEach(u => {
            if (u.team === 0 && u.hp > 0) {
                u.hp = Math.min(u.maxHp, u.hp + item.value);
                u.atk = Math.floor(u.atk * 1.3);
            }
        });
        alert(`✅ HP+${item.value}，攻擊力+30%`);
    }
}

function closeShop() {
    const modal = document.getElementById('shopModal');
    if (modal) {
        modal.remove();
    }
}
