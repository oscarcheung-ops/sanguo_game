// ============================================================
// 戰鬥系統 (Unit 類、城堡、粒子效果)
// ============================================================

// 顏色常數
const COLORS = {
    BLUE: '#4A90E2',
    RED: '#E74C3C',
    GREEN: '#2ECC71',
    YELLOW: '#F39C12',
    WHITE: '#FFFFFF',
    CYAN: '#1ABC9C',
    PURPLE: '#9B59B6'
};

// === Unit 類 (戰鬥單位) ===
class Unit {
    constructor(name, x, y, team, unitType, hp = 100, atk = 20, speed = 3, siegeAtk = null) {
        this.id = Math.random();
        this.name = name;
        this.pos = [x, y];
        this.team = team; // 0=玩家, 1=敵人
        this.type = unitType; // 0=槍, 1=騎, 2=弓
        this.hp = hp;
        this.maxHp = hp;
        this.atk = atk;
        this.speed = speed;
        this.siegeAtk = siegeAtk !== null ? siegeAtk : atk; // 攻城傷害
        
        // 目標
        this.targetPos = null;
        this.targetEnemy = null;
        this.selected = false;
        
        // 狀態效果
        this.stunned = false;
        this.slowFactor = 1.0;
        this.speedRecoverTime = 0;
        
        // 技能系統
        this.skill = UNIT_SKILLS[unitType] ? { ...UNIT_SKILLS[unitType] } : {};
        this.skillCooldown = 0.0;
        this.skillReady = true;
        
        // 專精系統
        this.specialization = {};
    }

    // 應用專精效果
    applySpecialization(heroName) {
        const spec = HERO_SPECIALIZATION[heroName];
        if (!spec) return;
        
        this.specialization = spec;
        
        const { bonus, value } = spec;
        
        switch (bonus) {
            case "damage_boost":
                this.atk = Math.floor(this.atk * value);
                break;
            case "speed_boost":
                this.speed = this.speed * value;
                break;
            case "crit_rate":
                this.critRate = value;
                break;
            case "hp_recovery":
                this.hpRecovery = value;
                break;
            case "skill_cooldown":
                this.skillCooldownMult = value;
                break;
            case "skill_damage":
                this.skillDamageMult = value;
                break;
        }
    }

    // 更新單位
    update(units, castles, gameWindow = null) {
        // 更新技能冷卻
        if (this.skillCooldown > 0) {
            this.skillCooldown -= 0.016; // 16ms per frame
            if (this.skillCooldown <= 0) {
                this.skillCooldown = 0;
                this.skillReady = true;
            }
        }
        
        // 更新眩暈狀態（只持續1秒）
        if (this.stunned) {
            this.speedRecoverTime -= 0.016;
            if (this.speedRecoverTime <= 0) {
                this.stunned = false;
                this.targetPos = null; // 清除目標，重新選擇
            }
        }
        
        // 更新減速狀態
        if (this.slowFactor < 1.0) {
            this.speedRecoverTime -= 0.016;
            if (this.speedRecoverTime <= 0) {
                this.slowFactor = 1.0;
            }
        }
        
        // 如果被眩暈，不能移動和攻擊
        if (this.stunned) {
            return 0;
        }
        
        // 移動
        const currentSpeed = this.speed * this.slowFactor;
        if (this.targetPos) {
            const dx = this.targetPos[0] - this.pos[0];
            const dy = this.targetPos[1] - this.pos[1];
            const dist = Math.hypot(dx, dy);
            
            if (dist > currentSpeed) {
                this.pos[0] += dx / dist * currentSpeed;
                this.pos[1] += dy / dist * currentSpeed;
            } else {
                this.targetPos = null;
            }
        }
        
        // 限制在戰鬥場地內
        this.pos[0] = Math.max(ARENA.MIN_X, Math.min(ARENA.MAX_X, this.pos[0]));
        this.pos[1] = Math.max(ARENA.MIN_Y, Math.min(ARENA.MAX_Y, this.pos[1]));
        
        // 尋找敵人
        if (!this.targetEnemy || this.targetEnemy.hp <= 0) {
            const enemies = units.filter(u => u.team !== this.team && u.hp > 0);
            if (enemies.length > 0) {
                this.targetEnemy = enemies.reduce((closest, enemy) => {
                    const dist1 = Math.hypot(this.pos[0] - enemy.pos[0], this.pos[1] - enemy.pos[1]);
                    const dist2 = Math.hypot(this.pos[0] - closest.pos[0], this.pos[1] - closest.pos[1]);
                    return dist1 < dist2 ? enemy : closest;
                });
            } else {
                this.targetEnemy = null;
            }
        }
        
        // HP 恢復（張飛專精）
        if (this.hpRecovery && this.hp < this.maxHp) {
            this.hp = Math.min(this.maxHp, this.hp + this.maxHp * this.hpRecovery * 0.016);
        }
        
        // 攻擊和技能
        if (this.targetEnemy && this.targetEnemy.hp > 0) {
            const dist = Math.hypot(
                this.pos[0] - this.targetEnemy.pos[0],
                this.pos[1] - this.targetEnemy.pos[1]
            );
            const attackRange = UNIT_ATTACK_RANGES[this.type];
            
            // 嘗試釋放技能
            if (this.skill && this.skillReady && dist < this.skill.range) {
                this.activateSkill(this.targetEnemy, units, gameWindow);
                return 0;
            }
            
            // 普通攻擊
            if (dist < attackRange) {
                const multiplier = getMultiplier(this.type, this.targetEnemy.type);
                let damage = this.atk * multiplier;
                
                // 應用暴擊率（黃忠專精）
                if (this.critRate && Math.random() < this.critRate) {
                    damage *= 1.5;
                }
                
                // 應用玩家方效果
                if (this.team === 0 && gameWindow) {
                    // 暴擊判定
                    if (gameWindow.critChance && Math.random() < gameWindow.critChance) {
                        damage *= 1.5;
                    }
                    // 吸血
                    if (gameWindow.lifestealRate && gameWindow.lifestealRate > 0 && gameWindow.playerCastle) {
                        const healAmount = damage * gameWindow.lifestealRate;
                        gameWindow.playerCastle.hp = Math.min(
                            gameWindow.playerCastle.maxHp,
                            gameWindow.playerCastle.hp + healAmount
                        );
                    }
                }
                
                // 應用目標方傷害減免
                if (this.targetEnemy.team === 0 && gameWindow && gameWindow.damageReduction) {
                    damage *= (1 - gameWindow.damageReduction);
                }
                
                this.targetEnemy.hp -= damage;
                
                // 顯示類型優勢反饋
                if (gameWindow) {
                    if (multiplier > 1.0) {
                        gameWindow.damageTexts.push([this.targetEnemy.pos.slice(), "⭐克制!", 60]);
                    } else if (multiplier < 1.0) {
                        gameWindow.damageTexts.push([this.targetEnemy.pos.slice(), "✗劣勢", 60]);
                    }
                }
                
                return Math.floor(damage);
            }
        }
        
        // 攻城邏輯：當周圍沒有可攻擊的敵人時，優先攻擊城堡
        if (castles && castles.length > 0) {
            const attackRange = UNIT_ATTACK_RANGES[this.type];
            // 檢查是否有敵人在攻擊範圍內
            let hasEnemyInRange = false;
            for (const enemy of units) {
                if (enemy.team !== this.team && enemy.hp > 0) {
                    if (Math.hypot(this.pos[0] - enemy.pos[0], this.pos[1] - enemy.pos[1]) < attackRange) {
                        hasEnemyInRange = true;
                        break;
                    }
                }
            }
            
            // 沒有敵人在範圍內，攻擊敵方城堡
            if (!hasEnemyInRange) {
                const enemyCastle = this.team === 0 ? castles[1] : castles[0];
                if (enemyCastle && Math.hypot(this.pos[0] - enemyCastle.pos[0], this.pos[1] - enemyCastle.pos[1]) < attackRange) {
                    const damage = Math.floor(this.siegeAtk || this.atk);
                    enemyCastle.hp -= damage;
                    
                    if (gameWindow) {
                        gameWindow.damageTexts.push([enemyCastle.pos.slice(), damage, 30]);
                        gameWindow.particles.push(new Particle(enemyCastle.pos[0], enemyCastle.pos[1], COLORS.RED, 0.8, 0, -30));
                    }
                    
                    return damage;
                }
            }
        }
        
        return 0;
    }

    // 激活技能
    activateSkill(target, units, gameWindow) {
        if (!this.skill) return;
        
        const skill = this.skill;
        let damage = this.atk * skill.damage_mult * getMultiplier(this.type, target.type);
        
        // 應用技能傷害加成（黃月英專精）
        if (this.skillDamageMult) {
            damage *= this.skillDamageMult;
        }
        
        const effect = skill.effect;
        
        if (effect === "pierce") { // 槍兵：貫穿突刺
            target.hp -= damage;
            // 眩暈效果 (25%概率，持續1秒)
            if (Math.random() < 0.25) {
                target.stunned = true;
                target.speedRecoverTime = 1.0;
                if (gameWindow) {
                    gameWindow.damageTexts.push([target.pos.slice(), "眩暈!", 60]);
                }
            }
            if (gameWindow) {
                gameWindow.damageTexts.push([target.pos.slice(), Math.floor(damage), 30]);
                gameWindow.particles.push(new Particle(target.pos[0], target.pos[1], COLORS.YELLOW, 1.0, 0, -40));
            }
        } else if (effect === "charge") { // 騎兵：衝鋒突擊
            target.hp -= damage;
            // 減速目標50% (持續2秒)
            target.slowFactor = 0.5;
            target.speedRecoverTime = 2.0;
            // 自身恢復25% HP
            this.hp = Math.min(this.maxHp, this.hp + this.maxHp * 0.25);
            if (gameWindow) {
                gameWindow.damageTexts.push([target.pos.slice(), Math.floor(damage), 30]);
                gameWindow.particles.push(new Particle(target.pos[0], target.pos[1], COLORS.WHITE, 1.0, 0, -40));
            }
        } else if (effect === "volley") { // 弓兵：連射覆蓋
            // 命中範圍內的多個敵人
            const arrowCount = skill.arrow_count || 3;
            const nearbyEnemies = units.filter(u =>
                u.team !== this.team && u.hp > 0 &&
                Math.hypot(u.pos[0] - target.pos[0], u.pos[1] - target.pos[1]) < (skill.range || 100)
            );
            
            nearbyEnemies.slice(0, arrowCount).forEach(enemy => {
                const arrowDamage = damage * 0.8;
                enemy.hp -= arrowDamage;
                // 減速效果 (40%減速，持續1.5秒)
                enemy.slowFactor = 0.6;
                enemy.speedRecoverTime = 1.5;
                if (gameWindow) {
                    gameWindow.damageTexts.push([enemy.pos.slice(), Math.floor(arrowDamage), 30]);
                    gameWindow.particles.push(new Particle(enemy.pos[0], enemy.pos[1], COLORS.CYAN, 1.0, 0, -40));
                }
            });
        }
        
        // 啟動技能冷卻
        const cooldown = skill.cooldown * (this.skillCooldownMult || 1);
        this.skillCooldown = cooldown;
        this.skillReady = false;
    }

    // 受到傷害
    takeDamage(damage) {
        this.hp = Math.max(0, this.hp - damage);
    }

    // 繪製單位
    draw(canvas) {
        const color = this.team === 0 ? COLORS.BLUE : COLORS.RED;
        
        // 畫單位
        canvas.create_oval(
            this.pos[0] - 25, this.pos[1] - 25,
            this.pos[0] + 25, this.pos[1] + 25,
            { fill: color, outline: COLORS.WHITE, width: 2 }
        );
        
        // 兵種圖標
        const unitIcons = { 0: "🔱", 1: "🐎", 2: "🏹" };
        const icon = unitIcons[this.type] || "⚔";
        canvas.create_text(
            this.pos[0], this.pos[1],
            { text: icon, fill: COLORS.WHITE, font: ["Arial", 16] }
        );
        
        // 血條背景
        canvas.create_rectangle(
            this.pos[0] - 25, this.pos[1] - 40,
            this.pos[0] + 25, this.pos[1] - 32,
            { fill: COLORS.RED, outline: COLORS.WHITE }
        );
        
        // 血條
        const hpWidth = 50 * (this.hp / this.maxHp);
        canvas.create_rectangle(
            this.pos[0] - 25, this.pos[1] - 40,
            this.pos[0] - 25 + hpWidth, this.pos[1] - 32,
            { fill: COLORS.GREEN, outline: COLORS.GREEN }
        );
        
        // 名稱
        canvas.create_text(
            this.pos[0], this.pos[1] + 40,
            { text: this.name, fill: COLORS.WHITE, font: ["Arial", 9] }
        );
        
        // 狀態指示器
        let statusText = "";
        let statusColor = COLORS.WHITE;
        
        if (this.stunned) {
            statusText = "💫眩暈";
            statusColor = COLORS.YELLOW;
        } else if (this.slowFactor < 1.0) {
            statusText = `⬇減速${Math.floor((1 - this.slowFactor) * 100)}%`;
            statusColor = COLORS.CYAN;
        }
        
        if (statusText) {
            canvas.create_text(
                this.pos[0], this.pos[1] + 52,
                { text: statusText, fill: statusColor, font: ["Arial", 8] }
            );
        }
        
        // 技能冷卻指示
        if (this.skill && !this.skillReady) {
            const cooldownPct = this.skillCooldown / this.skill.cooldown;
            const cooldownWidth = 50 * (1 - cooldownPct);
            
            canvas.create_rectangle(
                this.pos[0] - 25, this.pos[1] - 28,
                this.pos[0] + 25, this.pos[1] - 24,
                { fill: "#333", outline: "white", width: 1 }
            );
            canvas.create_rectangle(
                this.pos[0] - 25, this.pos[1] - 28,
                this.pos[0] - 25 + cooldownWidth, this.pos[1] - 24,
                { fill: "#FF9900", outline: "" }
            );
        } else if (this.skill && this.skillReady) {
            canvas.create_rectangle(
                this.pos[0] - 25, this.pos[1] - 28,
                this.pos[0] + 25, this.pos[1] - 24,
                { fill: "#00FF00", outline: "#00FF00", width: 1 }
            );
        }
        
        // 選中框
        if (this.selected) {
            canvas.create_oval(
                this.pos[0] - 30, this.pos[1] - 30,
                this.pos[0] + 30, this.pos[1] + 30,
                { outline: COLORS.YELLOW, width: 3 }
            );
        }
    }
}

// === Castle 類 (城堡) ===
class Castle {
    constructor(x, y, team, isBoss = false) {
        this.pos = [x, y];
        this.team = team;
        this.hp = 500;
        this.maxHp = 500;
        this.isBoss = isBoss;
        this.bossPhase = 1;
        
        if (isBoss) {
            this.hp = 1500;
            this.maxHp = 1500;
        }
    }

    // 受到傷害
    takeDamage(damage) {
        this.hp = Math.max(0, this.hp - damage);
    }

    // 繪製城堡
    draw(canvas) {
        const color = this.isBoss ? COLORS.PURPLE : (this.team === 0 ? COLORS.GREEN : COLORS.RED);
        const icon = this.isBoss ? "👑" : "🏰";
        
        // 城堡主體
        canvas.create_rectangle(
            this.pos[0] - 60, this.pos[1] - 40,
            this.pos[0] + 60, this.pos[1] + 40,
            { fill: color, outline: COLORS.DARK_GOLD, width: 3 }
        );
        
        // 城堡圖標
        canvas.create_text(
            this.pos[0], this.pos[1],
            { text: icon, fill: COLORS.WHITE, font: ["Arial", 24] }
        );
        
        // 血條背景
        canvas.create_rectangle(
            this.pos[0] - 60, this.pos[1] - 50,
            this.pos[0] + 60, this.pos[1] - 42,
            { fill: COLORS.GRAY, outline: COLORS.WHITE, width: 2 }
        );
        
        // 血條
        const hpWidth = 120 * (this.hp / this.maxHp);
        const hpColor = this.hp > this.maxHp * 0.5 ? COLORS.GREEN :
                       this.hp > this.maxHp * 0.2 ? COLORS.YELLOW : COLORS.RED;
        canvas.create_rectangle(
            this.pos[0] - 60, this.pos[1] - 50,
            this.pos[0] - 60 + hpWidth, this.pos[1] - 42,
            { fill: hpColor }
        );
        
        // HP 文字
        canvas.create_text(
            this.pos[0], this.pos[1] - 52,
            { text: `${Math.floor(this.hp)}/${Math.floor(this.maxHp)}`, fill: COLORS.WHITE, font: ["Arial", 10] }
        );
    }
}

// === Particle 類 (粒子效果) ===
class Particle {
    constructor(x, y, color, life = 1.0, vx = 0, vy = 0) {
        this.x = x;
        this.y = y;
        this.color = color;
        this.life = life;
        this.maxLife = life;
        this.vx = vx;
        this.vy = vy;
    }

    // 更新粒子
    update(dt) {
        this.x += this.vx * dt;
        this.y += this.vy * dt;
        this.life -= dt;
    }

    // 繪製粒子
    draw(canvas) {
        const alpha = this.life / this.maxLife;
        canvas.create_oval(
            this.x - 3, this.y - 3,
            this.x + 3, this.y + 3,
            { fill: this.color, outline: this.color }
        );
    }
}
