#!/usr/bin/env python3
"""LUG 终端雨 —— 摊位上的命令打字街机。"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time

import scores
from canvas import (
    AMBER, BG, DIM, FAINT, GREEN, INK, PANEL, PINK, PURPLE,
    RED, TEAL, WHITE, Canvas, mix, scale, twidth,
)
from fx import Rain
from game import Game, ROUND_TIME
from term import Terminal

MIN_W, MIN_H = 80, 24
FPS = 30
FIELD_Y = 3

TIER_COLOR = {1: TEAL, 2: AMBER, 3: PINK}

LUG_LOGO = (
    "██╗   ██╗ ██╗   ██╗  ██████╗",
    "██║   ██║ ██║   ██║ ██╔════╝",
    "██║   ██║ ██║   ██║ ██║  ███╗",
    "██║   ██║ ██║   ██║ ██║   ██║",
    "╚██████╔╝ ╚██████╔╝ ╚██████╔╝",
)
LOGO_COLORS = (AMBER, AMBER, TEAL, TEAL, PURPLE)

RANK_GLYPH = {
    "S": ("█████", "█    ", "█████", "    █", "█████"),
    "A": (" ███ ", "█   █", "█████", "█   █", "█   █"),
    "B": ("████ ", "█   █", "████ ", "█   █", "████ "),
    "C": (" ████", "█    ", "█    ", "█    ", " ████"),
    "D": ("████ ", "█   █", "█   █", "█   █", "████ "),
}
DIGITS = {
    "1": ("   ██", "  ███", "   ██", "   ██", "   ██"),
    "2": (" ████", "█   █", "   ██", "  ██ ", "█████"),
    "3": ("█████", "    █", " ████", "    █", "█████"),
}


def multiplier(game: Game) -> int:
    return min(5, 1 + game.combo // 5)


def draw_logo(c: Canvas, x: int, y: int) -> int:
    for i, line in enumerate(LUG_LOGO):
        c.put(x, y + i, line, LOGO_COLORS[i], PANEL, bold=True)
    return twidth(LUG_LOGO[0])


def draw_rank(c: Canvas, x: int, y: int, rank: str, color) -> None:
    for i, line in enumerate(RANK_GLYPH.get(rank, RANK_GLYPH["D"])):
        c.put(x, y + i, line, color, PANEL, bold=True)


def draw_header(c: Canvas, game: Game, w: int, now: float) -> None:
    c.put(0, 0, " LUG 终端雨 ", BG, AMBER, bold=True)
    label, value = "SCORE", f"{game.score:06d}"
    x = (w - (twidth(label) + 1 + twidth(value))) // 2
    c.put(x, 0, label, FAINT, BG, bold=True)
    c.put(x + twidth(label) + 1, 0, value, INK, BG, bold=True)

    hearts = "♥" * max(0, game.lives) + "♡" * max(0, 3 - game.lives)
    c.right(w - 1, 0, hearts, PINK, BG, bold=True)

    ratio = max(0.0, game.time_left / ROUND_TIME)
    color = RED if game.time_left <= 10 else AMBER if game.time_left <= 25 else TEAL
    if game.time_left <= 10 and int(now * 4) % 2 == 0:
        color = WHITE
    c.put(2, 1, "TIME", FAINT, BG, bold=True)
    c.bar(7, 1, max(8, min(28, w // 3)), ratio, fg=color)
    c.put(8 + max(8, min(28, w // 3)), 1, f"{int(math.ceil(game.time_left)):02d}s", color, BG, bold=True)

    mult = multiplier(game)
    combo = f"COMBO {game.combo:02d}  x{mult}"
    c.right(w - 1, 1, combo, AMBER if mult > 1 else DIM, BG, bold=True)


def draw_commands(c: Canvas, game: Game, ox: int, oy: int, w: int, h: int,
                  now: float, dim: float = 1.0) -> None:
    target = game.target
    for cmd in sorted(game.commands, key=lambda c: c.y):
        y = oy + int(cmd.y)
        if y < oy or y >= oy + h - 1:
            continue
        color = TIER_COLOR[cmd.tier]
        if dim < 1.0:
            color = mix(BG, color, dim)
        text = cmd.text
        tw = twidth(text)
        x = ox + max(0, min(cmd.x, w - tw - 2))
        if cmd is target:
            c.put(x - 1, y, "▐", BG, color)
            typed = game.typed if cmd is game.locked else ""
            if typed and text.startswith(typed):
                c.put(x, y, typed, WHITE, color, bold=True)
                c.put(x + twidth(typed), y, text[len(typed):], BG, color, bold=True)
            else:
                c.put(x, y, text, BG, color, bold=True)
            c.put(x + tw, y, "▌", BG, color)
            if int(now * 4) % 2 == 0:
                c.put(x - 2, y, "▸", color, BG, bold=True)
        else:
            bg = mix(BG, color, 0.14)
            c.put(x - 1, y, "▏", scale(color, 0.7), bg)
            c.put(x, y, text, color, bg)
            c.put(x + tw, y, "▕", scale(color, 0.7), bg)


def draw_field(c: Canvas, game: Game, rain: Rain, ox: int, oy: int, w: int, h: int,
               now: float, dim: float = 1.0) -> None:
    c.fill(ox, oy, w, h, " ", INK, BG)
    rain.draw(c, ox, oy, w, h, 0.30 * dim)
    draw_commands(c, game, ox, oy, w, h, now, dim)
    game.fx.draw(c, ox, oy, w, h)
    c.hline(ox, oy + h - 1, w, "┄", scale(RED, 0.35), BG)


def draw_prompt(c: Canvas, game: Game, w: int, h: int, now: float) -> None:
    py = h - 7
    c.fill(0, py, w, 7, " ", INK, PANEL)
    c.hline(0, py, w, "─", FAINT, PANEL)

    shake = 0
    if game.shake > 0:
        shake = 1 if int(game.shake * 40) % 2 == 0 else 0
    prompt_bg = mix(PANEL, RED, 0.22) if game.wrong_flash > 0 else PANEL
    c.fill(0, py + 1, w, 1, " ", INK, prompt_bg)
    c.put(1 + shake, py + 1, "lug@booth", GREEN, prompt_bg, bold=True)
    c.put(11 + shake, py + 1, ":~$", TEAL, prompt_bg, bold=True)
    x = 16 + shake
    typed = game.typed
    c.put(x, py + 1, typed, WHITE, prompt_bg, bold=True)
    if int(now * 3) % 2 == 0:
        c.put(x + twidth(typed), py + 1, "█", AMBER, prompt_bg, bold=True)

    target = game.target
    if target:
        color = TIER_COLOR[target.tier]
        c.put(2, py + 2, "目标", FAINT, PANEL)
        c.put(7, py + 2, target.text, color, PANEL, bold=True)
        dx = 9 + twidth(target.text)
        c.put(dx, py + 2, "·", FAINT, PANEL)
        c.put(dx + 2, py + 2, target.desc, DIM, PANEL)
        if game.typed and target.text.startswith(game.typed):
            c.right(w - 2, py + 2, f"{len(game.typed)}/{twidth(target.text)}", FAINT, PANEL)
    else:
        c.put(2, py + 2, "等一条命令落下来…", FAINT, PANEL)

    mult = multiplier(game)
    c.put(2, py + 3, "连击", FAINT, PANEL)
    c.put(7, py + 3, f"{game.combo:02d}", AMBER if game.combo else DIM, PANEL, bold=True)
    c.put(11, py + 3, "倍率", FAINT, PANEL)
    c.put(16, py + 3, f"x{mult}", PINK if mult > 1 else DIM, PANEL, bold=True)
    c.put(22, py + 3, "击碎", FAINT, PANEL)
    c.put(27, py + 3, f"{game.kills:02d}", INK, PANEL)
    c.put(33, py + 3, "失误", FAINT, PANEL)
    c.put(38, py + 3, f"{game.misses:02d}", RED if game.misses else DIM, PANEL)
    c.put(45, py + 3, "目标数", FAINT, PANEL)
    c.put(52, py + 3, f"{len(game.commands)}", DIM, PANEL)

    c.put(2, py + 5, "输入高亮命令", TEAL, PANEL, bold=True)
    c.put(15, py + 5, "·", FAINT, PANEL)
    c.put(17, py + 5, "Backspace 删除", FAINT, PANEL)
    c.put(33, py + 5, "·", FAINT, PANEL)
    c.put(35, py + 5, "Esc 放弃", FAINT, PANEL)
    c.right(w - 2, py + 5, "Ctrl-C 退出", FAINT, PANEL)

    c.put(2, py + 6, "LUG 终端雨", AMBER, PANEL, bold=True)
    c.put(14, py + 6, "在命令落到提示符之前，把它敲碎。", FAINT, PANEL)
    c.right(w - 2, py + 6, "60 秒 · 连击越高分数越高", FAINT, PANEL)


def draw_play(c: Canvas, game: Game, rain: Rain, w: int, h: int, now: float,
              countdown: float) -> None:
    c.fill(0, 0, w, h, " ", INK, BG)
    draw_header(c, game, w, now)
    c.hline(0, 2, w, "─", FAINT, BG)
    c.put(2, 2, "命令雨", DIM, BG)
    c.right(w - 2, 2, "INPUT", FAINT, BG)
    field_h = h - 7 - FIELD_Y
    draw_field(c, game, rain, 0, FIELD_Y, w, field_h, now)
    draw_prompt(c, game, w, h, now)

    if countdown > 0:
        n = max(1, int(math.ceil(countdown)))
        label = str(n)
        x = (w - 10) // 2
        y = FIELD_Y + field_h // 2 - 3
        for i, line in enumerate(DIGITS.get(label, ())):
            c.put(x, y + i, line * 2, AMBER, BG, bold=True)
        c.center(y + 6, "准备", AMBER, BG, bold=True)
        c.center(y + 8, "输入高亮命令", FAINT, BG)


def draw_attract(c: Canvas, game: Game, rain: Rain, board: list[dict],
                 w: int, h: int, now: float) -> None:
    c.fill(0, 0, w, h, " ", INK, BG)
    rain.draw(c, 0, 0, w, h, 0.60)
    draw_commands(c, game, 0, 0, w, h - 1, now, 0.55)

    pw = min(82, w - 10)
    ph = min(21, h - 3)
    px = (w - pw) // 2
    py = max(1, (h - ph) // 2)
    c.box(px, py, pw, ph, AMBER, PANEL, "LUG 终端雨", AMBER)
    c.put(px + pw - 6, py, "DEMO", PINK, PANEL, bold=True)

    logo_w = draw_logo(c, px + 3, py + 2)
    tx = px + 5 + logo_w
    if tx + 24 < px + pw:
        c.put(tx, py + 2, "COMMAND", DIM, PANEL, bold=True)
        c.put(tx, py + 3, "RAIN", DIM, PANEL, bold=True)
        c.put(tx, py + 5, "终端雨", PINK, PANEL, bold=True)
        c.put(tx, py + 6, "LUG 摆摊小游戏", FAINT, PANEL)

    c.put(px + 3, py + 8, "输入高亮命令，在它落到提示符之前击碎。", INK, PANEL)
    c.put(px + 3, py + 9, "连击越高倍率越高；60 秒，3 条命。", DIM, PANEL)
    c.put(px + 3, py + 10, "Backspace 删除 · Esc 放弃 · Ctrl-C 退出", FAINT, PANEL)

    ly = py + 12
    c.put(px + 3, ly, "排行榜", AMBER, PANEL, bold=True)
    c.hline(px + 9, ly, max(0, pw - 12), "─", FAINT, PANEL)
    if board:
        for i, row in enumerate(board[:4]):
            name = str(row.get("name", "???"))[:3]
            score = int(row.get("score", 0))
            color = AMBER if i == 0 else INK if i < 3 else DIM
            c.put(px + 4, ly + 1 + i, f"{i + 1:>2}.", FAINT, PANEL)
            c.put(px + 8, ly + 1 + i, name, color, PANEL, bold=True)
            c.right(px + pw - 4, ly + 1 + i, f"{score:>6}", color, PANEL)
    else:
        c.put(px + 4, ly + 1, "还没有记录 · 来打第一条", FAINT, PANEL)

    label = "按任意键开始"
    c.put(px + (pw - twidth(label)) // 2, py + ph - 2, label, FAINT, PANEL, bold=True)
    if int(now * 2) % 2 == 0:
        c.put(px + (pw - twidth(label)) // 2, py + ph - 2, label, WHITE, PANEL, bold=True)
    c.right(w - 2, h - 1, "Ctrl-C 退出", FAINT, BG)


def draw_over(c: Canvas, game: Game, rain: Rain, board: list[dict], w: int, h: int,
              now: float, initials: str, can_save: bool, saved_name: str) -> None:
    c.fill(0, 0, w, h, " ", INK, BG)
    rain.draw(c, 0, 0, w, h, 0.35)

    pw = min(76, w - 10)
    ph = min(21, h - 4)
    px = (w - pw) // 2
    py = max(1, (h - ph) // 2)
    c.box(px, py, pw, ph, PINK if game.lives <= 0 else AMBER, PANEL, "SYSTEM REPORT", PINK)
    title = "连接中断" if game.lives <= 0 else "时间到"
    c.put(px + 3, py + 1, title, PINK if game.lives <= 0 else AMBER, PANEL, bold=True)
    c.put(px + 3 + twidth(title) + 2, py + 1, "终端雨结束", DIM, PANEL)

    c.put(px + 4, py + 2, "RANK", FAINT, PANEL)
    draw_rank(c, px + 4, py + 3, game.rank, AMBER if game.rank in ("S", "A") else INK)
    c.put(px + 13, py + 3, "SCORE", FAINT, PANEL)
    c.put(px + 13, py + 4, f"{game.score:06d}", WHITE, PANEL, bold=True)
    c.put(px + 13, py + 6, f"击碎 {game.kills} · 最高连击 {game.max_combo} · 失误 {game.misses}", DIM, PANEL)
    if game.perfect:
        c.put(px + 13, py + 7, "PERFECT +200", AMBER, PANEL, bold=True)

    ly = py + 9
    c.put(px + 3, ly, "排行榜", AMBER, PANEL, bold=True)
    c.hline(px + 9, ly, pw - 12, "─", FAINT, PANEL)
    if board:
        for i, row in enumerate(board[:5]):
            name = str(row.get("name", "???"))[:3]
            value = int(row.get("score", 0))
            hot = name == saved_name and value == game.score
            color = AMBER if hot else INK if i < 3 else DIM
            bg = mix(PANEL, AMBER, 0.18) if hot else PANEL
            c.put(px + 4, ly + 1 + i, f"{i + 1:>2}.", FAINT, bg)
            c.put(px + 8, ly + 1 + i, name, color, bg, bold=True)
            c.right(px + pw - 4, ly + 1 + i, f"{value:>6}", color, bg)
    else:
        c.put(px + 4, ly + 1, "还没有记录", FAINT, PANEL)

    if can_save:
        c.put(px + 3, py + ph - 4, "留下名字", DIM, PANEL)
        shown = initials.ljust(3, "_")
        c.put(px + 13, py + ph - 4, " ".join(shown), WHITE, PANEL, bold=True)
        if int(now * 3) % 2 == 0:
            c.put(px + 13 + twidth(initials) * 2, py + ph - 4, "█", AMBER, PANEL, bold=True)
        c.put(px + 3, py + ph - 3, "A-Z 0-9 · Enter 确认 · Backspace 删除", FAINT, PANEL)
    else:
        c.put(px + 3, py + ph - 4, "未进入排行榜", DIM, PANEL)
        c.put(px + 3, py + ph - 3, "按任意键回到待机", DIM, PANEL)
    c.right(w - 2, h - 1, "Ctrl-C 退出", FAINT, BG)


def draw_board(c: Canvas, board: list[dict], w: int, h: int, now: float,
               saved_name: str, saved_score: int) -> None:
    c.fill(0, 0, w, h, " ", INK, BG)
    pw = min(70, w - 10)
    ph = min(20, h - 4)
    px = (w - pw) // 2
    py = (h - ph) // 2
    c.box(px, py, pw, ph, AMBER, PANEL, "LUG 排行榜", AMBER)
    for i, row in enumerate(board[:8]):
        name = str(row.get("name", "???"))[:3]
        value = int(row.get("score", 0))
        combo = int(row.get("combo", 0))
        hot = name == saved_name and value == saved_score
        color = AMBER if hot else INK if i < 3 else DIM
        bg = mix(PANEL, AMBER, 0.18) if hot else PANEL
        c.put(px + 4, py + 2 + i, f"{i + 1:>2}.", FAINT, bg)
        c.put(px + 8, py + 2 + i, name, color, bg, bold=True)
        c.put(px + 13, py + 2 + i, f"最高连击 {combo}", FAINT, bg)
        c.right(px + pw - 4, py + 2 + i, f"{value:>6}", color, bg)
    c.put(px + (pw - 20) // 2, py + ph - 2, "按任意键回到待机", WHITE, PANEL, bold=True)
    c.right(w - 2, h - 1, "Ctrl-C 退出", FAINT, BG)


def draw_too_small(c: Canvas, w: int, h: int) -> None:
    c.fill(0, 0, w, h, " ", INK, BG)
    c.center(max(0, h // 2 - 2), "终端太小了", AMBER, BG, bold=True)
    c.center(max(0, h // 2), f"至少需要 {MIN_W} x {MIN_H}", DIM, BG)
    c.center(max(0, h // 2 + 1), f"当前 {w} x {h}", FAINT, BG)
    c.center(max(0, h // 2 + 3), "放大窗口后自动继续", FAINT, BG)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="lug-rain", description="LUG 终端雨 —— 摊位上的命令打字街机")
    p.add_argument("--seed", type=int, default=None, help="固定随机种子（调试用）")
    p.add_argument("--reset-scores", action="store_true", help="清空本地排行榜后退出")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.reset_scores:
        print(f"已清空 {scores.reset()}")
        return 0

    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    rng = random.Random(seed)
    try:
        term = Terminal()
    except Exception as e:
        print(f"启动失败：{e}", file=sys.stderr)
        return 1

    board = scores.load()
    state = "attract"
    game = Game("demo", seed=seed)
    rain = Rain(100, 30, seed)
    countdown = 0.0
    initials = ""
    can_save = False
    saved_name = ""
    saved_score = 0
    over_timer = 0.0
    board_timer = 0.0
    prev_rows = None
    last_size = None
    last = time.monotonic()
    running = True

    with term:
        try:
            while running:
                frame_start = time.monotonic()
                now = frame_start
                dt = min(0.25, frame_start - last)
                last = frame_start
                w, h = term.size()
                if (w, h) != last_size:
                    last_size = (w, h)
                    rain.resize(w, h)
                    prev_rows = None
                    term.clear()

                keys = term.read_keys(0.0)
                if not keys:
                    keys = term.read_keys(0.002)

                if w < MIN_W or h < MIN_H:
                    frame = Canvas(w, h)
                    draw_too_small(frame, w, h)
                    text, prev_rows = frame.render(prev_rows)
                    term.write(text)
                    term.flush()
                    for key in keys:
                        if key == "ctrl-c":
                            running = False
                    time.sleep(1 / FPS)
                    last = time.monotonic()
                    continue

                if state == "attract":
                    game.update(dt, w, max(1, h - 1))
                    for key in keys:
                        if key == "ctrl-c":
                            running = False
                            break
                        game = Game("play", seed=rng.randrange(1_000_000))
                        state = "playing"
                        countdown = 3.0
                        initials = ""
                        can_save = False
                        saved_name = ""
                        saved_score = 0
                        over_timer = 0.0
                        prev_rows = None
                        term.clear()
                        break

                elif state == "playing":
                    if countdown > 0:
                        countdown = max(0.0, countdown - dt)
                    else:
                        game.update(dt, w, max(1, h - 7 - FIELD_Y))
                    for key in keys:
                        if key == "ctrl-c":
                            running = False
                            break
                        if key == "esc":
                            state = "attract"
                            game = Game("demo", seed=rng.randrange(1_000_000))
                            prev_rows = None
                            term.clear()
                            break
                        if countdown <= 0:
                            game.key(key)
                    if game.state == "over":
                        state = "over"
                        over_timer = 0.0
                        initials = ""
                        can_save = scores.qualifies(game.score)
                        saved_name = ""
                        saved_score = game.score
                        prev_rows = None

                elif state == "over":
                    over_timer += dt
                    for key in keys:
                        if key == "ctrl-c":
                            running = False
                            break
                        if key == "esc":
                            state = "attract"
                            game = Game("demo", seed=rng.randrange(1_000_000))
                            prev_rows = None
                            term.clear()
                            break
                        if not can_save:
                            state = "attract"
                            game = Game("demo", seed=rng.randrange(1_000_000))
                            prev_rows = None
                            term.clear()
                            break
                        if key == "backspace":
                            initials = initials[:-1]
                        elif key == "enter":
                            name = (initials or "YOU").upper()[:3]
                            board = scores.save(name, game.score, game.max_combo)
                            saved_name = name
                            saved_score = game.score
                            state = "board"
                            board_timer = 0.0
                            prev_rows = None
                            term.clear()
                            break
                        elif len(key) == 1 and key.isalnum() and len(initials) < 3:
                            initials += key.upper()
                    if over_timer > 25 and state == "over":
                        state = "attract"
                        game = Game("demo", seed=rng.randrange(1_000_000))
                        prev_rows = None
                        term.clear()

                else:  # board
                    board_timer += dt
                    for key in keys:
                        if key == "ctrl-c":
                            running = False
                            break
                        state = "attract"
                        game = Game("demo", seed=rng.randrange(1_000_000))
                        prev_rows = None
                        term.clear()
                        break
                    if board_timer > 12 and state == "board":
                        state = "attract"
                        game = Game("demo", seed=rng.randrange(1_000_000))
                        prev_rows = None
                        term.clear()

                if not running:
                    break

                frame = Canvas(w, h)
                if state == "attract":
                    draw_attract(frame, game, rain, board, w, h, now)
                elif state == "playing":
                    draw_play(frame, game, rain, w, h, now, countdown)
                elif state == "over":
                    draw_over(frame, game, rain, board, w, h, now, initials,
                              can_save, saved_name)
                else:
                    draw_board(frame, board, w, h, now, saved_name, saved_score)

                text, prev_rows = frame.render(prev_rows)
                term.write(text)
                term.flush()

                spent = time.monotonic() - frame_start
                if spent < 1 / FPS:
                    time.sleep(1 / FPS - spent)
        except KeyboardInterrupt:
            pass

    print("收摊了。下次再玩。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
