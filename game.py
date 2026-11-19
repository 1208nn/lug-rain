"""游戏逻辑：掉落命令、打字、连击、生命和演示模式。"""

from __future__ import annotations

import random
from dataclasses import dataclass

from canvas import twidth
from commands import BY_TIER
from fx import Effects

ROUND_TIME = 60.0
MAX_ACTIVE = 6
MAX_DEMO = 7
TIER_BASE = {1: 10, 2: 20, 3: 30}


@dataclass
class Falling:
    text: str
    desc: str
    tier: int
    x: int
    y: float
    speed: float


def rank_for(score: int) -> str:
    if score >= 2600:
        return "S"
    if score >= 1800:
        return "A"
    if score >= 1100:
        return "B"
    if score >= 500:
        return "C"
    return "D"


class Game:
    def __init__(self, mode: str = "play", seed: int | None = None):
        self.mode = mode
        self.state = "playing"
        self.rng = random.Random(seed)
        self.commands: list[Falling] = []
        self.typed = ""
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.kills = 0
        self.misses = 0
        self.lives = 3
        self.elapsed = 0.0
        self.time_left = ROUND_TIME
        self.perfect = False
        self.rank = "D"
        self.flash = 0.0
        self.wrong_flash = 0.0
        self.shake = 0.0
        self.spawn_timer = 0.35
        self.auto_timer = 0.25
        self.fx = Effects(seed)
        # 演示模式一开始就有内容
        if mode == "demo":
            for _ in range(4):
                self._spawn(140, force=True)

    # ---------- 查询 ----------

    def _lowest(self) -> Falling | None:
        return max(self.commands, key=lambda c: c.y, default=None)

    def matches(self) -> list[Falling]:
        if not self.typed:
            return list(self.commands)
        return [c for c in self.commands if c.text.startswith(self.typed)]

    @property
    def target(self) -> Falling | None:
        if not self.typed:
            return self._lowest()
        exact = [c for c in self.commands if c.text == self.typed]
        rows = exact or [c for c in self.commands if c.text.startswith(self.typed)]
        return max(rows, key=lambda c: c.y, default=None)

    @property
    def progress(self) -> float:
        return max(0.0, min(1.0, self.elapsed / ROUND_TIME))

    # ---------- 更新 ----------

    def update(self, dt: float, w: int, h: int) -> None:
        dt = min(dt, 0.25)
        self.flash = max(0.0, self.flash - dt)
        self.wrong_flash = max(0.0, self.wrong_flash - dt)
        self.shake = max(0.0, self.shake - dt)
        self.fx.update(dt)

        if self.state != "playing":
            return

        self.elapsed += dt
        if self.mode == "play":
            self.time_left = max(0.0, ROUND_TIME - self.elapsed)
            if self.elapsed >= ROUND_TIME:
                self._finish()
                return

        if w <= 0 or h <= 0:
            return

        # 命令下落
        for c in self.commands:
            c.y += c.speed * dt
            if c.x + twidth(c.text) >= w:
                c.x = max(0, w - twidth(c.text) - 1)

        missed = [c for c in self.commands if c.y >= h - 0.5]
        for c in missed:
            self._miss(c)

        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn(w)
            self.spawn_timer = self._spawn_interval()

        if self.mode == "demo":
            self._auto_type(dt)

    def _spawn_interval(self) -> float:
        if self.mode == "demo":
            e = min(self.elapsed, 30.0)
            return max(0.60, 0.95 - e * 0.010)
        return max(0.78, 2.05 - self.elapsed * 0.020)

    def _spawn(self, w: int, force: bool = False) -> None:
        cap = MAX_DEMO if self.mode == "demo" else MAX_ACTIVE
        if not force and len(self.commands) >= cap:
            return
        if w < 20:
            return

        tiers = [1]
        weights = [1.0]
        if self.elapsed > 6:
            tiers.append(2)
            weights.append(0.75)
        if self.elapsed > 22:
            tiers.append(3)
            weights.append(0.45)
        tier = self.rng.choices(tiers, weights=weights, k=1)[0]
        active = {c.text for c in self.commands}
        pool = [item for item in BY_TIER[tier] if item[0] not in active]
        if not pool:
            pool = [item for item in BY_TIER[1] if item[0] not in active]
        if not pool:
            return
        text, tier, desc = self.rng.choice(pool)

        lanes = max(2, min(4, w // 22))
        lane_w = w / lanes
        free = []
        for lane in range(lanes):
            x0 = lane * lane_w
            if not any(x0 <= c.x < x0 + lane_w and c.y < 5 for c in self.commands):
                free.append(lane)
        if not free:
            return
        lane = self.rng.choice(free)
        max_x = max(0, int(lane * lane_w + lane_w) - twidth(text) - 1)
        min_x = int(lane * lane_w) + 1
        x = max(0, min(w - twidth(text) - 1, self.rng.randint(min_x, max(min_x, max_x))))
        speed = 1.35 + self.elapsed * 0.028 + self.rng.uniform(-0.05, 0.25)
        if self.mode == "demo":
            speed = 1.35 + min(self.elapsed, 30.0) * 0.024
        self.commands.append(Falling(text, desc, tier, x, -1.0, min(3.8, speed)))

    # ---------- 输入 ----------

    def key(self, key: str) -> None:
        if self.state != "playing" or self.mode != "play":
            return
        if key in ("esc", "ctrl-c"):
            return
        if key == "backspace":
            self.typed = self.typed[:-1]
            return
        if key == "tab":
            self.complete()
            return
        if key == "enter":
            exact = [c for c in self.commands if c.text == self.typed]
            if exact:
                self._destroy(max(exact, key=lambda c: c.y))
            elif self.typed:
                self._wrong()
            return
        if len(key) != 1 or not key.isprintable():
            return

        self.typed += key
        if not any(c.text.startswith(self.typed) for c in self.commands):
            self._wrong()

    def complete(self) -> None:
        """像 shell 一样按单词补全；大小写不对时用不区分大小写的候选兜底。"""
        if not self.typed or not self.commands:
            return
        matches = [c for c in self.commands if c.text.startswith(self.typed)]
        if not matches:
            # 大小写不对也允许 Tab 修正；这是补全，不是放宽手动输入
            fixed = [c for c in self.commands
                     if c.text.lower().startswith(self.typed.lower())]
            if not fixed:
                self._wrong()
                return
            # 只修正已输入部分的字母大小写，不帮忙补后面的内容
            target = max(fixed, key=lambda c: c.y)
            n = len(self.typed)
            if len(target.text) >= n:
                self.typed = target.text[:n]
            return

        parts = self.typed.split(" ")
        idx = len(parts) - 1
        cur = parts[-1]
        words = []
        for c in matches:
            cw = c.text.split(" ")
            if idx < len(cw):
                words.append(cw[idx])
        if not words:
            return

        lcp = words[0]
        for w in words[1:]:
            while lcp and not w.startswith(lcp):
                lcp = lcp[:-1]
        if len(lcp) <= len(cur):
            # 唯一候选且当前词已经完整：像 shell 一样补一个空格
            if len(matches) == 1 and cur == words[0]:
                cw = matches[0].text.split(" ")
                if idx < len(cw) - 1:
                    self.typed += " "
            return

        parts[-1] = lcp
        self.typed = " ".join(parts)
        if all(w == lcp for w in words) and len(matches) == 1:
            cw = matches[0].text.split(" ")
            if idx < len(cw) - 1:
                self.typed += " "

    def _wrong(self) -> None:
        self.combo = 0
        self.shake = 0.24
        self.wrong_flash = 0.16

    def _destroy(self, c: Falling) -> None:
        if c not in self.commands:
            return
        self.commands.remove(c)
        if self.mode == "play":
            mult = min(5, 1 + self.combo // 5)
            gain = (TIER_BASE[c.tier] + int(max(0.0, 6 - c.y / 2))) * mult
            self.score += gain
            self.kills += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.fx.float(c.x + twidth(c.text) / 2, c.y, f"+{gain}", (255, 226, 140))
        else:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
        self.fx.burst(c.x + twidth(c.text) / 2, c.y + 0.5, (255, 198, 96), 14)
        self.typed = ""

    def _miss(self, c: Falling) -> None:
        if self.state != "playing" or c not in self.commands:
            return
        self.commands.remove(c)
        self.typed = ""
        self.fx.burst(c.x + twidth(c.text) / 2, c.y, (255, 86, 98), 10)
        if self.mode == "play":
            self.lives -= 1
            self.misses += 1
            self.combo = 0
            self.flash = 0.40
            self.fx.float(c.x, c.y, "-1", (255, 120, 120))
            if self.lives <= 0:
                self._finish()
        else:
            self.combo = 0

    def _auto_type(self, dt: float) -> None:
        self.auto_timer -= dt
        if self.auto_timer > 0:
            return
        target = self.target
        if target is None:
            self.auto_timer = 0.3
            return
        if not target.text.startswith(self.typed):
            self.typed = ""
            return
        self.typed += target.text[len(self.typed)]
        if self.typed == target.text:
            self._destroy(target)
            self.auto_timer = self.rng.uniform(0.28, 0.55)
        else:
            self.auto_timer = self.rng.uniform(0.075, 0.14)

    # ---------- 结算 ----------

    def _finish(self) -> None:
        if self.state != "playing":
            return
        self.state = "over"
        self.time_left = 0.0
        if self.lives == 3 and self.score > 0:
            self.perfect = True
            self.score += 200
        self.rank = rank_for(self.score)
