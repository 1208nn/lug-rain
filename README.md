# LUG 终端雨

摆在 LUG 摊位上的 **60 秒命令打字街机**。命令从终端上方落下来，在它砸到提示符之前敲完并按 `Enter` 执行掉。

适合路人轮流玩：待机时自动运行，按任意键开始；结束后输入 3 个字母进本地排行榜，超时自动回到待机。

```text
  LUG//ARCADE  COMMAND RAIN // LINUX USER GROUP // TAB TO COMPLETE      SYS.ONLINE
         ┌─ LUG 终端雨 ────────────────────────────────────────────────────┐
         │  ██╗   ██╗ ██╗   ██╗  ██████╗  COMMAND                          │
         │  ██║   ██║ ██║   ██║ ██╔════╝  RAIN                             │
         │  ██║   ██║ ██║   ██║ ██║  ███╗                                  │
         │  ██║   ██║ ██║   ██║ ██║   ██║ 终端雨                           │
         │  ╚██████╔╝ ╚██████╔╝ ╚██████╔╝ LUG 摊位游戏                     │
         │  输入命令，Tab 补全，Enter 执行。                                │
         │  别让它落到提示符；连击越高倍率越高。60 秒，3 条命。             │
         │  排行榜                                                          │
         │    1. ABC                                                   2600 │
         │    2. XYZ                                                   1200 │
         │                    按任意键开始                                  │
         └─────────────────────────────────────────────────────────────────┘
 lug@booth:~$ _
```

## 运行

需要 [uv](https://docs.astral.sh/uv/)。`mise.toml` 只负责提供 `uv`。

```bash
cd lug-rain
./lug
```

也可以用：

```bash
mise exec -- uv run python main.py
```

终端至少 **80 x 24**，推荐全屏 + 真彩（`COLORTERM=truecolor`）。窗口太小时会提示，放大后自动继续。

## 玩法

1. 屏幕里会落下 Linux 命令，最下面那条用亮色高亮。
2. 像 shell 一样输入命令：`Tab` 补全，`Enter` 执行。
3. 命令落到最下面的红线还没执行，扣一条命。
4. 60 秒结束或 3 条命用完，本局结束。

- 大小写敏感，和真实 shell 一致；大小写不对时按 `Tab` 会修正已输入部分。
- `Tab` 按单词补全，例如 `curl -` + `Tab` → `curl -I`。
- 键入错误会断连击，但不会扣命；`Backspace` 可以删。
- 连击每 5 次提升一级倍率，最高 5 倍。
- 目标命令下面会显示中文说明，没玩过 Linux 的人也能照着敲。

## 键位

| 键 | 作用 |
| --- | --- |
| 任意键 | 待机页开始游戏 |
| 字母 / 数字 / 符号 | 输入命令 |
| Tab | 按 shell 习惯补全当前单词 |
| Enter | 执行命令；结算页确认 3 个字母 |
| Backspace | 删除一个字符 |
| Esc | 游戏中放弃，回到待机 |
| Ctrl-C | 退出 |

## 摊位模式

- 待机页会自动运行：命令照常下落，自动玩家会逐字敲掉，路人能直接看懂怎么玩。
- 结算页停留 25 秒、排行榜停留 12 秒，之后自动回待机。
- 排行榜存在本地：

```text
~/.local/share/lug-rain/scores.json
```

也可以用 `LUG_RAIN_SCORES` 指定路径。清空榜单：

```bash
./lug --reset-scores
```

## 计分

- 难度 1 / 2 / 3 的基础分是 10 / 20 / 30。
- 连击倍率 `1 + combo // 5`，最高 5 倍。
- 越早击碎，速度奖励越高。
- 一条命没掉打完 60 秒，额外 `PERFECT +200`。
- 评级：S ≥ 2600，A ≥ 1800，B ≥ 1100，C ≥ 500，其余 D。

## 命令池

三个难度会随着时间逐步解锁：

- 入门：`ls`、`cd`、`pwd`、`cat`、`grep`、`git`、`ssh`、`tar`……
- 进阶：`ls -l`、`git add`、`chmod +x`、`tar -xf`、`docker ps`……
- 硬核：`git commit -m`、`systemctl status`、`journalctl -xe`、`rsync -av`……

每条命令都带一句中文说明，既是大字报也是小型命令手册。

## 技术

- Python 3.13 + `uv`，零第三方依赖。
- 真彩 ANSI 画布，按行 diff 输出；30 FPS。
- 不使用图片协议：摊位环境只需要一个能显示真彩字符的终端，最稳。
- 数据只有本地排行榜 JSON，不联网。

## 项目结构

```text
lug           启动脚本
main.py       状态机、布局、主循环
game.py       掉落、shell 式输入、连击、生命、待机模式
commands.py   命令池与中文说明
fx.py         背景雨、粒子、飘字
canvas.py     真彩画布、宽字符、按行输出
term.py       raw 输入、替换屏幕、终端尺寸
scores.py     本地排行榜
```

## 开发

```bash
mise exec -- uv run python -m py_compile main.py game.py commands.py fx.py canvas.py term.py scores.py
```

固定随机种子：

```bash
./lug --seed 7
```

不依赖终端跑一局模拟：

```bash
mise exec -- uv run python - <<'PY'
from game import Game

g = Game("play", seed=7)
for step in range(30 * 65):
    g.update(1 / 30, 100, 14)
    if step % 4 == 0 and g.state == "playing":
        t = g.target
        if t:
            if g.typed == t.text:
                g.key("enter")
            elif t.text.startswith(g.typed):
                g.key(t.text[len(g.typed)])
    if g.state == "over":
        break
print(g.score, g.rank, g.kills, g.misses, g.max_combo)
PY
```
