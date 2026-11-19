"""背景雨、粒子、飘字。"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from canvas import BG, Canvas, Color, mix, scale

RAIN_CHARS = "01#><$[]{}()/\\|=+-abcdefghijklmnopqrstuvwxyz"
RAIN_COLORS = ((40, 130, 140), (70, 80, 170), (120, 70, 150), (40, 150, 110))


class Rain:
    def __init__(self, w: int, h: int, seed: int | None = None):
        self.rng = random.Random(seed)
        self.w = self.h = 0
        self.cols: list[dict] = []
        self.resize(w, h)

    def resize(self, w: int, h: int) -> None:
        if (w, h) == (self.w, self.h):
            return
        self.w, self.h = w, h
        self.cols = []
        step = 5
        for x in range(1, max(2, w - 1), step):
            self.cols.append(self._new_col(x, top=True))

    def _new_col(self, x: int, top: bool = False) -> dict:
        length = self.rng.randint(2, 6)
        return {
            "x": x,
            "y": self.rng.uniform(-self.h, 0) if top else -length,
            "len": length,
            "speed": self.rng.uniform(3.0, 10.0),
            "color": self.rng.choice(RAIN_COLORS),
            "chars": [self.rng.choice(RAIN_CHARS) for _ in range(length)],
        }

    def update(self, dt: float) -> None:
        for c in self.cols:
            c["y"] += c["speed"] * dt
            if c["y"] - c["len"] > self.h:
                fresh = self._new_col(c["x"])
                c.update(fresh)

    def draw(self, c: Canvas, x: int, y: int, w: int, h: int, dim: float = 0.42) -> None:
        for col in self.cols:
            cx = x + col["x"]
            if not (x <= cx < x + w):
                continue
            color = scale(col["color"], dim)
            for i, ch in enumerate(col["chars"]):
                cy = y + int(col["y"]) - i
                if y <= cy < y + h:
                    c.put(cx, cy, ch, color, BG)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    ch: str
    color: Color


@dataclass
class Float:
    x: float
    y: float
    text: str
    color: Color
    life: float
    max_life: float


class Effects:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.particles: list[Particle] = []
        self.floats: list[Float] = []

    def burst(self, x: float, y: float, color: Color, n: int = 12) -> None:
        chars = "*+·.✦"
        for _ in range(n):
            ang = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(4, 18)
            self.particles.append(Particle(
                x, y,
                math.cos(ang) * speed,
                math.sin(ang) * speed - 4,
                self.rng.uniform(0.35, 0.8),
                0.8,
                self.rng.choice(chars),
                color,
            ))

    def float(self, x: float, y: float, text: str, color: Color) -> None:
        self.floats.append(Float(x, y, text, color, 0.9, 0.9))

    def update(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 26 * dt
            alive.append(p)
        self.particles = alive
        floats = []
        for f in self.floats:
            f.life -= dt
            if f.life > 0:
                f.y -= 3.5 * dt
                floats.append(f)
        self.floats = floats

    def draw(self, c: Canvas, x0: int, y0: int, w: int, h: int) -> None:
        for p in self.particles:
            if p.life <= 0:
                continue
            a = p.life / p.max_life
            color = mix(BG, p.color, a)
            px, py = x0 + int(p.x), y0 + int(p.y)
            if x0 <= px < x0 + w and y0 <= py < y0 + h:
                c.put(px, py, p.ch, color, BG)
        for f in self.floats:
            if f.life <= 0:
                continue
            a = f.life / f.max_life
            color = mix(BG, f.color, a)
            px, py = x0 + int(f.x), y0 + int(f.y)
            if x0 <= px < x0 + w and y0 <= py < y0 + h:
                c.put(px, py, f.text, color, BG, bold=True)
