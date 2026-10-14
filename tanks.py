#!/usr/bin/env python3
# grid tanks
# a little tank game that runs in your terminal
#
# run it:   python3 tanks.py
# on windows you need this first:   pip install windows-curses

import curses
import os
import random
import time
from collections import deque

# esc is really slow in curses by default, this fixes it
os.environ.setdefault("ESCDELAY", "25")


# ------------------------------------------------------------
# settings (mess with these if you want)
# ------------------------------------------------------------

TANK_DELAY = 0.12      # seconds between tank moves
FAST_DELAY = 0.07      # same thing but with the speed powerup
BULLET_DELAY = 0.05    # seconds between bullet moves
MAX_BULLETS = 2        # bullets you can have flying at once
MAX_BOUNCES = 4        # bullets die after this many bounces
WIN_SCORE = 5          # first to this wins
ROUND_PAUSE = 2.0      # seconds between rounds
POWERUP_EVERY = 7.0    # a new powerup shows up this often
POWERUP_STAYS = 12.0   # how long a powerup sits there before it goes away
POWERUP_LASTS = 8.0    # how long triple shot and speed last
FPS = 30

MIN_W = 60  # the game needs at least this big of a terminal
MIN_H = 20


# ------------------------------------------------------------
# maps
# # = wall, . = floor, 1 = blue start, 2 = red start
# every map has to be 21 wide and 13 tall
# ------------------------------------------------------------

MAPS = [
    ("pillars", [
        "#####################",
        "#1..................#",
        "#...................#",
        "#...##.........##...#",
        "#...##....#....##...#",
        "#.........#.........#",
        "#....###.....###....#",
        "#.........#.........#",
        "#...##....#....##...#",
        "#...##.........##...#",
        "#...................#",
        "#..................2#",
        "#####################",
    ]),
    ("rails", [
        "#####################",
        "#1..................#",
        "#...................#",
        "#...#############...#",
        "#...................#",
        "#.........#.........#",
        "#.......#####.......#",
        "#.........#.........#",
        "#...................#",
        "#...#############...#",
        "#...................#",
        "#..................2#",
        "#####################",
    ]),
    ("split", [
        "#####################",
        "#1........#.........#",
        "#.........#.........#",
        "#..###....#....###..#",
        "#.........#.........#",
        "#...................#",
        "#....#.........#....#",
        "#...................#",
        "#.........#.........#",
        "#..###....#....###..#",
        "#.........#.........#",
        "#.........#........2#",
        "#####################",
    ]),
    ("rooms", [
        "#####################",
        "#1........#.........#",
        "#.........#.........#",
        "#.........#.........#",
        "#...................#",
        "#.........#.........#",
        "#####.#########.#####",
        "#.........#.........#",
        "#...................#",
        "#.........#.........#",
        "#.........#.........#",
        "#.........#........2#",
        "#####################",
    ]),
    ("diamond", [
        "#####################",
        "#1..................#",
        "#...................#",
        "#........#.#........#",
        "#.......#...#.......#",
        "#......#.....#......#",
        "#.....#.......#.....#",
        "#......#.....#......#",
        "#.......#...#.......#",
        "#........#.#........#",
        "#...................#",
        "#..................2#",
        "#####################",
    ]),
]

ROWS = len(MAPS[0][1])
COLS = len(MAPS[0][1][0])


# ------------------------------------------------------------
# directions and keys
# ------------------------------------------------------------

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
UL, UR, DL, DR = (-1, -1), (1, -1), (-1, 1), (1, 1)

# all 8 directions going clockwise from up
DIRS = [UP, UR, RIGHT, DR, DOWN, DL, LEFT, UL]

# blue: wasd to move, q e z c for diagonals, space to shoot
BLUE_KEYS = {
    "w": UP, "s": DOWN, "a": LEFT, "d": RIGHT,
    "q": UL, "e": UR, "z": DL, "c": DR,
}
# red: ijkl to move, u o m . for diagonals, enter to shoot
# (arrow keys work for red too but they cant do diagonals)
RED_KEYS = {
    "i": UP, "k": DOWN, "j": LEFT, "l": RIGHT,
    "u": UL, "o": UR, "m": DL, ".": DR,
}
ARROWS = {
    curses.KEY_UP: UP, curses.KEY_DOWN: DOWN,
    curses.KEY_LEFT: LEFT, curses.KEY_RIGHT: RIGHT,
}
ENTER = (10, 13, curses.KEY_ENTER)
ESC = 27

# how the cpu plays at each level:
# name, seconds between decisions, chance it shoots when lined up,
# how many bounces it plans shots around, chance it dodges, chance it wanders
CPU_LEVELS = [
    ("easy", 0.45, 0.35, 0, 0.2, 0.4),
    ("normal", 0.26, 0.7, 1, 0.6, 0.15),
    ("hard", 0.14, 0.95, 3, 0.95, 0.0),
]

# letter, name, what it does
POWERUPS = [
    ("S", "shield", "blocks one hit"),
    ("3", "triple", "shoots 3 bullets at once"),
    (">", "speed", "drive way faster"),
]

# color pair numbers (set up in setup_colors)
BLUE = 1
RED = 2
WHITE = 3

TITLE_ART = [
    " ###  ####  ### ####      #####  ###  #   # #   #  ####",
    "#     #   #  #  #   #       #   #   # ##  # #  #  #",
    "# ##  ####   #  #   #       #   ##### # # # ###    ###",
    "#   # #  #   #  #   #       #   #   # #  ## #  #      #",
    " ###  #   # ### ####        #   #   # #   # #   # ####",
]


# ------------------------------------------------------------
# game objects
# ------------------------------------------------------------

class Tank:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.score = 0
        self.cpu = False

    def spawn(self, x, y, facing):
        self.x = x
        self.y = y
        self.dx = facing   # face toward the middle
        self.dy = 0
        self.alive = True
        self.shield = False
        self.triple_until = 0
        self.fast_until = 0
        self.want = None      # the direction it's trying to move
        self.next_move = 0
        self.next_think = 0   # cpu only
        self.killed_by = None
        self.bank_shot = False


class Bullet:
    def __init__(self, x, y, dx, dy, owner):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.owner = owner
        self.bounces = 0
        self.age = 0       # how many cells it moved. cant hit its owner at 0
        self.dead = False


class Game:
    def __init__(self):
        self.screen = "title"  # title, howto, playing, roundover, paused, matchover
        self.paused_from = "playing"  # where to go back to after pausing
        self.menu = 0
        self.cpu_level = 1
        self.mode = "2p"       # "2p" or "cpu"
        self.tanks = [Tank("BLUE", BLUE), Tank("RED", RED)]
        self.t = 0.0           # game clock, stops while paused
        self.map_num = -1
        self.map_name = ""
        self.grid = MAPS[0][1]
        self.bullets = []
        self.powerups = []     # each one is [x, y, letter, time it disappears]
        self.booms = []        # explosions: [x, y, start time, color]
        self.bullet_clock = 0.0
        self.next_powerup = 0.0
        self.round_over_at = 0.0
        self.message = ""
        self.winner = None


# ------------------------------------------------------------
# starting matches and rounds
# ------------------------------------------------------------

def start_match(g, mode):
    g.mode = mode
    blue, red = g.tanks
    red.cpu = mode == "cpu"
    red.name = "CPU" if mode == "cpu" else "RED"
    for tank in g.tanks:
        tank.score = 0
    g.map_num = -1
    g.winner = None
    start_round(g)


def start_round(g):
    # random map but not the same one twice in a row
    num = g.map_num
    while num == g.map_num:
        num = random.randrange(len(MAPS))
    g.map_num = num
    g.map_name, g.grid = MAPS[num]

    g.bullets = []
    g.powerups = []
    g.booms = []
    g.bullet_clock = 0.0
    g.next_powerup = g.t + POWERUP_EVERY / 2

    for y, row in enumerate(g.grid):
        for x, ch in enumerate(row):
            if ch == "1":
                g.tanks[0].spawn(x, y, 1)
            if ch == "2":
                g.tanks[1].spawn(x, y, -1)

    g.screen = "playing"


# ------------------------------------------------------------
# little helpers
# ------------------------------------------------------------

def wall(g, x, y):
    if x < 0 or y < 0 or x >= COLS or y >= ROWS:
        return True
    return g.grid[y][x] == "#"


def tank_at(g, x, y):
    for tank in g.tanks:
        if tank.alive and tank.x == x and tank.y == y:
            return tank
    return None


def powerup_at(g, x, y):
    for p in g.powerups:
        if p[0] == x and p[1] == y:
            return p
    return None


def dist(x1, y1, x2, y2):
    # diagonal steps count as 1
    return max(abs(x1 - x2), abs(y1 - y2))


def other(g, tank):
    if tank is g.tanks[0]:
        return g.tanks[1]
    return g.tanks[0]


def can_move(g, x, y, dx, dy):
    if wall(g, x + dx, y + dy):
        return False
    if tank_at(g, x + dx, y + dy):
        return False
    # cant squeeze diagonally between two walls
    if dx != 0 and dy != 0:
        if wall(g, x + dx, y) or wall(g, x, y + dy):
            return False
    return True


# ------------------------------------------------------------
# tanks
# ------------------------------------------------------------

def press_move(tank, d):
    # turn right away so you can aim, then actually move on the next step
    tank.dx, tank.dy = d
    tank.want = d


def update_tanks(g):
    for tank in g.tanks:
        if not tank.alive or tank.want is None or g.t < tank.next_move:
            continue

        tank.dx, tank.dy = tank.want
        tank.want = None
        if g.t < tank.fast_until:
            tank.next_move = g.t + FAST_DELAY
        else:
            tank.next_move = g.t + TANK_DELAY

        if can_move(g, tank.x, tank.y, tank.dx, tank.dy):
            tank.x += tank.dx
            tank.y += tank.dy
            p = powerup_at(g, tank.x, tank.y)
            if p:
                grab_powerup(g, tank, p)


def hit(g, tank, shooter, bank):
    if not tank.alive:
        return
    if tank.shield:
        tank.shield = False  # shield saves you once
        return
    tank.alive = False
    tank.killed_by = shooter
    tank.bank_shot = bank
    g.booms.append([tank.x, tank.y, g.t, tank.color])


# ------------------------------------------------------------
# bullets
# ------------------------------------------------------------

def fire(g, tank):
    if not tank.alive:
        return
    mine = [b for b in g.bullets if b.owner is tank]
    if len(mine) >= MAX_BULLETS:
        return

    if g.t < tank.triple_until:
        # straight ahead plus one to each side
        i = DIRS.index((tank.dx, tank.dy))
        shots = [DIRS[(i - 1) % 8], DIRS[i], DIRS[(i + 1) % 8]]
    else:
        shots = [(tank.dx, tank.dy)]

    for dx, dy in shots:
        g.bullets.append(Bullet(tank.x, tank.y, dx, dy, tank))


def step_bullet(g, b):
    # moves a bullet one step, bouncing it off walls
    nx = b.x + b.dx
    ny = b.y + b.dy

    if b.dx != 0 and b.dy != 0:
        # diagonal. figure out which side it hit
        hit_x = wall(g, b.x + b.dx, b.y)
        hit_y = wall(g, b.x, b.y + b.dy)
        if hit_x or hit_y or wall(g, nx, ny):
            if hit_x:
                b.dx = -b.dx
            if hit_y:
                b.dy = -b.dy
            if not hit_x and not hit_y:
                # hit the exact corner, go straight back
                b.dx = -b.dx
                b.dy = -b.dy
            b.bounces += 1
            return
    elif wall(g, nx, ny):
        b.dx = -b.dx
        b.dy = -b.dy
        b.bounces += 1
        return

    b.x = nx
    b.y = ny
    b.age += 1


def check_hits(g):
    for b in g.bullets:
        for tank in g.tanks:
            if b.dead or not tank.alive:
                continue
            if b.x == tank.x and b.y == tank.y:
                if tank is not b.owner or b.age > 0:
                    b.dead = True
                    hit(g, tank, b.owner, b.bounces > 0)
    g.bullets = [b for b in g.bullets if not b.dead and b.bounces <= MAX_BOUNCES]


# ------------------------------------------------------------
# powerups
# ------------------------------------------------------------

def update_powerups(g):
    g.powerups = [p for p in g.powerups if g.t < p[3]]

    if g.t < g.next_powerup:
        return
    g.next_powerup = g.t + POWERUP_EVERY
    if len(g.powerups) >= 2:
        return

    # find open spots that arent right next to a tank
    spots = []
    for y in range(ROWS):
        for x in range(COLS):
            if wall(g, x, y) or tank_at(g, x, y) or powerup_at(g, x, y):
                continue
            close = False
            for tank in g.tanks:
                if tank.alive and dist(x, y, tank.x, tank.y) < 3:
                    close = True
            if not close:
                spots.append((x, y))
    if not spots:
        return

    x, y = random.choice(spots)
    letter = random.choice(POWERUPS)[0]
    g.powerups.append([x, y, letter, g.t + POWERUP_STAYS])


def grab_powerup(g, tank, p):
    g.powerups.remove(p)
    if p[2] == "S":
        tank.shield = True
    elif p[2] == "3":
        tank.triple_until = g.t + POWERUP_LASTS
    elif p[2] == ">":
        tank.fast_until = g.t + POWERUP_LASTS


# ------------------------------------------------------------
# cpu player
# every so often it decides what to do:
# dodge bullets > shoot if it can hit > go get stuff / chase you
# ------------------------------------------------------------

def update_cpu(g):
    for tank in g.tanks:
        if not tank.cpu or not tank.alive or g.t < tank.next_think:
            continue
        name, think, fire_chance, bounces, dodge, wander = CPU_LEVELS[g.cpu_level]
        tank.next_think = g.t + think
        cpu_think(g, tank, fire_chance, bounces, dodge, wander)


def cpu_think(g, tank, fire_chance, bounces, dodge, wander):
    enemy = other(g, tank)
    tank.want = None

    # dodge
    if random.random() < dodge:
        d = find_dodge(g, tank)
        if d:
            tank.want = d
            return

    if not enemy.alive:
        return

    # shoot
    shot = find_shot(g, tank, enemy, bounces)
    if shot:
        if shot == (tank.dx, tank.dy):
            if random.random() < fire_chance:
                fire(g, tank)
        else:
            tank.dx, tank.dy = shot  # aim now, shoot next time
        return

    # wander around randomly sometimes
    if random.random() < wander:
        d = random.choice(DIRS)
        if can_move(g, tank.x, tank.y, d[0], d[1]):
            tank.want = d
        return

    # go for a powerup if its closer than the enemy, otherwise go for the enemy
    goal = (enemy.x, enemy.y)
    for p in g.powerups:
        if dist(tank.x, tank.y, p[0], p[1]) < dist(tank.x, tank.y, goal[0], goal[1]):
            goal = (p[0], p[1])
    tank.want = path_step(g, tank, goal)


def trace_shot(g, tank, dx, dy, target, max_bounces):
    # pretend to shoot and follow the bullet. returns steps until it hits, or None
    ghost = Bullet(tank.x, tank.y, dx, dy, tank)
    for step in range(1, 41):
        step_bullet(g, ghost)
        if ghost.bounces > max_bounces:
            return None
        if ghost.x == target.x and ghost.y == target.y:
            return step
        if ghost.age > 0 and ghost.x == tank.x and ghost.y == tank.y:
            return None  # would shoot itself
    return None


def find_shot(g, tank, target, max_bounces):
    best = None
    best_steps = 999
    for dx, dy in DIRS:
        steps = trace_shot(g, tank, dx, dy, target, max_bounces)
        if steps is not None and steps < best_steps:
            best = (dx, dy)
            best_steps = steps
    return best


def find_dodge(g, tank):
    # every cell a bullet is about to go through
    danger = set()
    for b in g.bullets:
        ghost = Bullet(b.x, b.y, b.dx, b.dy, b.owner)
        ghost.bounces = b.bounces
        for i in range(8):
            step_bullet(g, ghost)
            if ghost.bounces > MAX_BOUNCES:
                break
            danger.add((ghost.x, ghost.y))

    if (tank.x, tank.y) not in danger:
        return None

    safe = []
    for d in DIRS:
        if can_move(g, tank.x, tank.y, d[0], d[1]):
            if (tank.x + d[0], tank.y + d[1]) not in danger:
                safe.append(d)
    if not safe:
        return None
    return random.choice(safe)


def path_step(g, tank, goal):
    # breadth first search to the goal, returns the first step to take
    start = (tank.x, tank.y)
    came_from = {start: None}
    queue = deque([start])

    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            break
        for dx, dy in DIRS:
            nxt = (x + dx, y + dy)
            if nxt in came_from or wall(g, nxt[0], nxt[1]):
                continue
            if dx != 0 and dy != 0 and (wall(g, x + dx, y) or wall(g, x, y + dy)):
                continue
            came_from[nxt] = (x, y)
            queue.append(nxt)

    if goal not in came_from or goal == start:
        return None

    # walk back from the goal to the cell right next to us
    cell = goal
    while came_from[cell] != start:
        cell = came_from[cell]
    return (cell[0] - tank.x, cell[1] - tank.y)


# ------------------------------------------------------------
# rounds ending
# ------------------------------------------------------------

def check_round_end(g):
    dead = [tank for tank in g.tanks if not tank.alive]
    if not dead:
        return

    alive = [tank for tank in g.tanks if tank.alive]
    if not alive:
        g.message = "double ko, nobody scores"
    else:
        win = alive[0]
        lose = dead[0]
        win.score += 1
        if lose.killed_by is lose:
            g.message = lose.name + " shot themselves lol"
        elif lose.bank_shot:
            g.message = "BANK SHOT!! " + win.name + " scores"
        else:
            g.message = win.name + " scores"

    g.screen = "roundover"
    g.round_over_at = g.t


def update(g, dt):
    if g.screen == "roundover":
        g.t += dt
        g.booms = [b for b in g.booms if g.t - b[2] < 0.6]
        if g.t - g.round_over_at >= ROUND_PAUSE:
            for tank in g.tanks:
                if tank.score >= WIN_SCORE:
                    g.winner = tank
                    g.screen = "matchover"
                    return
            start_round(g)
        return

    if g.screen != "playing":
        return

    g.t += dt
    update_cpu(g)
    update_tanks(g)
    check_hits(g)

    g.bullet_clock += dt
    while g.bullet_clock >= BULLET_DELAY:
        g.bullet_clock -= BULLET_DELAY
        for b in g.bullets:
            step_bullet(g, b)
        check_hits(g)

    update_powerups(g)
    g.booms = [b for b in g.booms if g.t - b[2] < 0.6]
    check_round_end(g)


# ------------------------------------------------------------
# keys
# ------------------------------------------------------------

def key_char(k):
    if 0 <= k < 256:
        return chr(k).lower()
    return ""


def handle_key(g, k):
    # returns "quit" when the game should close
    ch = key_char(k)

    if g.screen == "title":
        if k in (curses.KEY_UP,) or ch == "w":
            g.menu = (g.menu - 1) % 5
        elif k in (curses.KEY_DOWN,) or ch == "s":
            g.menu = (g.menu + 1) % 5
        elif g.menu == 2 and (k in (curses.KEY_LEFT,) or ch == "a"):
            g.cpu_level = (g.cpu_level - 1) % len(CPU_LEVELS)
        elif g.menu == 2 and (k in (curses.KEY_RIGHT,) or ch == "d"):
            g.cpu_level = (g.cpu_level + 1) % len(CPU_LEVELS)
        elif k in ENTER or ch == " ":
            if g.menu == 0:
                start_match(g, "2p")
            elif g.menu == 1:
                start_match(g, "cpu")
            elif g.menu == 2:
                g.cpu_level = (g.cpu_level + 1) % len(CPU_LEVELS)
            elif g.menu == 3:
                g.screen = "howto"
            elif g.menu == 4:
                return "quit"
        return None

    if g.screen == "howto":
        if k in ENTER or k == ESC or ch == " ":
            g.screen = "title"
        return None

    if g.screen == "paused":
        if ch == "p":
            g.screen = g.paused_from
        elif ch == "t":
            g.screen = "title"
        return None

    if g.screen == "matchover":
        if ch == "r":
            start_match(g, g.mode)
        elif k in ENTER:
            g.screen = "title"
        return None

    # playing or roundover from here
    # (esc doesnt pause on purpose, some terminals send esc when you hit arrows)
    if ch == "p":
        g.paused_from = g.screen
        g.screen = "paused"
        return None
    if g.screen != "playing":
        return None

    blue, red = g.tanks
    # in cpu mode you can play blue with either side of the keyboard
    right_side = blue if g.mode == "cpu" else red

    if ch in BLUE_KEYS:
        press_move(blue, BLUE_KEYS[ch])
    elif ch in RED_KEYS:
        press_move(right_side, RED_KEYS[ch])
    elif k in ARROWS:
        press_move(right_side, ARROWS[k])
    elif ch == " ":
        fire(g, blue)
    elif k in ENTER:
        fire(g, right_side)
    return None


# ------------------------------------------------------------
# drawing
# every cell is 2 characters wide so the map isnt squished
# ------------------------------------------------------------

def setup_colors():
    if not curses.has_colors():
        return
    curses.start_color()
    curses.init_pair(BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(RED, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(WHITE, curses.COLOR_WHITE, curses.COLOR_BLACK)


def put(scr, y, x, text, color=WHITE):
    # writing to the very bottom right corner makes curses throw an error,
    # so just ignore anything that doesnt fit
    try:
        scr.addstr(y, x, text, curses.color_pair(color) | curses.A_BOLD)
    except curses.error:
        pass


def put_center(scr, y, text, color=WHITE):
    h, w = scr.getmaxyx()
    put(scr, y, max(0, (w - len(text)) // 2), text, color)


def put_box(scr, lines):
    # draws text in an ascii box in the middle of the screen
    h, w = scr.getmaxyx()
    width = max(len(line) for line in lines) + 4
    top = h // 2 - len(lines) // 2 - 1
    left = (w - width - 2) // 2
    put(scr, top, left, "+" + "-" * width + "+")
    for i, line in enumerate(lines):
        put(scr, top + 1 + i, left, "|" + line.center(width) + "|")
    put(scr, top + 1 + len(lines), left, "+" + "-" * width + "+")


def draw_title(scr, g):
    for i, line in enumerate(TITLE_ART):
        put_center(scr, 2 + i, line.ljust(len(TITLE_ART[0])))

    # two little tanks shooting at each other
    left = (scr.getmaxyx()[1] - 22) // 2
    put(scr, 8, left, "@-   *", BLUE)
    put(scr, 8, left + 16, "*   -@", RED)

    level = CPU_LEVELS[g.cpu_level][0]
    items = ["2 players", "vs cpu", "cpu level: < " + level + " >", "how to play", "quit"]
    for i, item in enumerate(items):
        if i == g.menu:
            put_center(scr, 11 + i, "> " + item + " <")
        else:
            put_center(scr, 11 + i, item)

    put_center(scr, 18, "w/s or arrows to pick, enter to go")


def draw_howto(scr, g):
    lines = [
        "HOW TO PLAY",
        "",
        "shoot the other tank. bullets bounce off walls.",
        "your own bullets can hit you too, so be careful",
        "first to " + str(WIN_SCORE) + " wins",
        "",
        "BLUE   w a s d = move   q e z c = diagonals   space = shoot",
        "RED    i j k l = move   u o m . = diagonals   enter = shoot",
        "       (arrow keys work for red too)",
        "",
        "pressing a direction turns you AND moves you",
        "p pauses, ctrl+c quits whenever",
        "",
        "powerups:",
    ]
    for letter, name, info in POWERUPS:
        lines.append("  [" + letter + "] " + name.ljust(8) + info)

    for i, line in enumerate(lines):
        put(scr, 1 + i, 2, line)
    put(scr, 2 + len(lines), 2, "press enter to go back")


def barrel_char(dx, dy):
    if dy == 0:
        return "-"
    if dx == 0:
        return "|"
    if dx == dy:
        return "\\"
    return "/"


def draw_game(scr, g):
    h, w = scr.getmaxyx()
    ox = (w - COLS * 2) // 2   # left edge of the map
    oy = 2                     # top edge of the map
    blue, red = g.tanks

    # top bar
    put(scr, 0, ox, "[ " + blue.name + ": " + str(blue.score) + " ]", BLUE)
    right = "[ " + red.name + ": " + str(red.score) + " ]"
    put(scr, 0, ox + COLS * 2 - 1 - len(right), right, RED)
    put_center(scr, oy + ROWS + 1, "map: " + g.map_name + "   first to " + str(WIN_SCORE))

    # walls
    for y in range(ROWS):
        for x in range(COLS):
            if wall(g, x, y):
                put(scr, oy + y, ox + x * 2, "#")

    # powerups (they blink when theyre about to go away)
    for p in g.powerups:
        if p[3] - g.t < 3 and int(g.t * 6) % 2 == 0:
            continue
        put(scr, oy + p[1], ox + p[0] * 2, p[2])

    # barrels
    taken = set((b.x, b.y) for b in g.bullets)
    taken |= set((p[0], p[1]) for p in g.powerups)
    for tank in g.tanks:
        if not tank.alive:
            continue
        sx = ox + tank.x * 2
        sy = oy + tank.y
        if tank.dx == 0:
            # straight up or down: the barrel goes in the next cell
            cx, cy = tank.x, tank.y + tank.dy
            if not wall(g, cx, cy) and not tank_at(g, cx, cy) and (cx, cy) not in taken:
                put(scr, sy + tank.dy, sx, "|", tank.color)
        elif tank.dy == 0 or not (wall(g, tank.x, tank.y + tank.dy) or wall(g, tank.x + tank.dx, tank.y + tank.dy)):
            # sideways or diagonal: the barrel goes in the gap between cells
            # (skipped if it would end up drawn on a wall)
            put(scr, sy + tank.dy, sx + tank.dx, barrel_char(tank.dx, tank.dy), tank.color)

    # bullets
    for b in g.bullets:
        put(scr, oy + b.y, ox + b.x * 2, "*", b.owner.color)

    # tank bodies (white if they have a shield)
    for tank in g.tanks:
        if tank.alive:
            color = WHITE if tank.shield else tank.color
            put(scr, oy + tank.y, ox + tank.x * 2, "@", color)

    # explosions
    for bx, by, start, color in g.booms:
        age = g.t - start
        if age < 0.2:
            put(scr, oy + by, ox + bx * 2, "X", color)
        else:
            for dx, dy in DIRS:
                if not wall(g, bx + dx, by + dy):
                    put(scr, oy + by + dy, ox + (bx + dx) * 2, "*", color)

    # bottom bar shows powerups you have
    put(scr, oy + ROWS, ox, powerup_text(g, blue), BLUE)
    txt = powerup_text(g, red)
    put(scr, oy + ROWS, ox + COLS * 2 - 1 - len(txt), txt, RED)

    if g.screen == "roundover":
        put_box(scr, [g.message, blue.name + " " + str(blue.score) + " - " + str(red.score) + " " + red.name])


def powerup_text(g, tank):
    stuff = []
    if tank.shield:
        stuff.append("shield")
    if g.t < tank.triple_until:
        stuff.append("triple " + str(int(tank.triple_until - g.t) + 1))
    if g.t < tank.fast_until:
        stuff.append("speed " + str(int(tank.fast_until - g.t) + 1))
    return " ".join(stuff)


def draw_matchover(scr, g):
    blue, red = g.tanks
    put_box(scr, [
        g.winner.name + " WINS!!",
        "",
        blue.name + " " + str(blue.score) + " - " + str(red.score) + " " + red.name,
        "",
        "r = rematch   enter = menu",
    ])


def draw(scr, g):
    scr.erase()
    h, w = scr.getmaxyx()
    if w < MIN_W or h < MIN_H:
        put(scr, 0, 0, "make your terminal bigger")
        put(scr, 1, 0, "(needs " + str(MIN_W) + "x" + str(MIN_H) + ")")
        scr.refresh()
        return

    if g.screen == "title":
        draw_title(scr, g)
    elif g.screen == "howto":
        draw_howto(scr, g)
    elif g.screen == "matchover":
        draw_matchover(scr, g)
    elif g.screen == "paused":
        put_box(scr, ["PAUSED", "", "p = keep playing", "t = quit to menu"])
    else:
        draw_game(scr, g)
    scr.refresh()


# ------------------------------------------------------------
# main loop
# ------------------------------------------------------------

def main(scr):
    curses.curs_set(0)
    scr.nodelay(True)
    scr.keypad(True)
    setup_colors()
    scr.bkgd(" ", curses.color_pair(WHITE))

    g = Game()
    last = time.time()
    while True:
        while True:
            k = scr.getch()
            if k == -1:
                break
            if handle_key(g, k) == "quit":
                return

        now = time.time()
        dt = min(now - last, 0.1)  # so the game doesnt jump if it lags
        last = now
        update(g, dt)
        draw(scr, g)
        time.sleep(1 / FPS)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass  # ctrl+c just quits
