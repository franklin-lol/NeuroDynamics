#!/usr/bin/env python3
"""
GENESIS — Psychoacoustic Engineering Suite
Author: franklin-sys | https://franklin-sys.vercel.app/
pip install numpy scipy soundfile
"""

import os, sys, re, time, threading

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTHOR  = 'franklin-sys'
URL     = 'https://franklin-sys.vercel.app/'

# ── Windows: enable ANSI + arrow keys
if sys.platform == 'win32':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), 7)
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# ══════════════════════════════════════════
#  ANSI
# ══════════════════════════════════════════

ESC   = '\033['
RESET = '\033[0m'

def C(r,g,b,bg=False): return f'\033[{"48" if bg else "38"};2;{r};{g};{b}m'
def BOLD():   return '\033[1m'
def DIM():    return '\033[2m'
def CLEAR():  return '\033[2J\033[H'
def HIDE():   return '\033[?25l'
def SHOW():   return '\033[?25h'
def MOVE(r,c):return f'\033[{r};{c}H'
def CLRL():   return '\033[2K'

# Palette
GOLD   = C(255,200, 50)
CYAN   = C( 80,220,255)
TEAL   = C( 50,190,160)
GREY   = C(140,140,160)
WHITE  = C(230,230,245)
DIM_W  = C(100,100,115)
PURPLE = C(160,100,255)
RED    = C(255, 80, 80)
GREEN  = C( 80,220,120)
BG_SEL = C( 25, 35, 55, bg=True)
BG_DIM = C( 12, 15, 22, bg=True)

# ── ANSI strip regex — один экземпляр на модуль (не импортировать re в каждой функции)
_ANSI_RE = re.compile(r'\033\[[^m]*m')


# ══════════════════════════════════════════
#  KEY READER (cross-platform)
#  FIX: Unix ESC без продолжения больше не блокирует:
#       select() с timeout 50 мс проверяет наличие следующего байта.
# ══════════════════════════════════════════

def _getch():
    if sys.platform == 'win32':
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):
            ch2 = msvcrt.getwch()
            return {'H': 'UP', 'P': 'DOWN', 'M': 'RIGHT', 'K': 'LEFT'}.get(ch2, '')
        return ch
    else:
        import tty, termios, select as _select
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                # Проверяем следующий байт с timeout 50 мс
                if _select.select([sys.stdin], [], [], 0.05)[0]:
                    ch2 = sys.stdin.read(1)
                    if _select.select([sys.stdin], [], [], 0.05)[0]:
                        ch3 = sys.stdin.read(1)
                        return {'A': 'UP', 'B': 'DOWN',
                                'C': 'RIGHT', 'D': 'LEFT'}.get(ch3, 'ESC')
                return 'ESC'
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ══════════════════════════════════════════
#  PROFILE DEFINITIONS
# ══════════════════════════════════════════

PROFILES = [
    {
        'key':   'GENESIS',
        'title': 'GENESIS',
        'time':  '63 мин',
        'glyph': '◈',
        'color': GOLD,
        'short': 'Полный спектр — флагманская сессия',
        'desc': [
            'Gamma ignition → Schumann → Theta → Void → Integration',
            'Все слои активны: HRTF · CFC · Lorenz · ASSR-80 · Phi',
            'Carrier cascade: 200→432→528→639→432→200 Hz',
        ],
        'protocol': [
            'Проводные наушники — BT разрушает ITD-фазу',
            'Громкость 20–28%  ·  не засыпать первые 5 мин',
            'Не чаще 1 раза в 2 дня  ·  10 мин тишины после',
        ],
    },
    {
        'key':   'WALK',
        'title': 'ПРОГУЛКА',
        'time':  '30 мин',
        'glyph': '◉',
        'color': TEAL,
        'short': 'Расширенное восприятие в движении',
        'desc': [
            'Alpha→Theta (12→7.5 Hz) · оператор-режим без транса',
            'HRTF + ITD-ротация → широкополосное пространство',
            'Gamma-якорь держит ясность всю сессию',
        ],
        'protocol': [
            'Проводные наушники — можно в движении',
            'Громкость 25–35%  ·  не садиться за руль',
        ],
    },
    {
        'key':   'SLEEP',
        'title': 'СОН / ВЫХОД',
        'time':  '90 мин',
        'glyph': '◌',
        'color': PURPLE,
        'short': 'Глубокий сон + 3 окна осознания (OBE)',
        'desc': [
            'Descent → Deep delta → 3× gamma-spike trigger cycles',
            'Окна осознания: ~40, 65, 88 мин — OBE-архитектура',
            'HRTF + Lorenz chaos в триггерных блоках',
        ],
        'protocol': [
            'Лечь, глаза закрыты с первой секунды',
            'Засыпать можно — сессия это учитывает',
            'Резкий возврат в окнах — норма, не пугаться',
        ],
    },
    {
        'key':   'HEALER',
        'title': 'ИСЦЕЛЕНИЕ',
        'time':  '75 мин',
        'glyph': '◎',
        'color': GREEN,
        'short': 'Глубокая дельта · восстановление · 528 Hz',
        'desc': [
            '528 Hz Solfeggio MI carrier на всей сессии',
            'Phi (φ=1.618) geometry layers · delta 1.5 Hz hold',
            'Двойной void-блок · максимальный CFC strength',
        ],
        'protocol': [
            'Можно полностью засыпать',
            'Громкость 15–25%  ·  идеально для ночного цикла',
        ],
    },
    {
        'key':   'ORACLE',
        'title': 'ОРАКУЛ',
        'time':  '60 мин',
        'glyph': '◐',
        'color': CYAN,
        'short': 'Ясновидение · Шуман · тета-коридор',
        'desc': [
            '432 Hz · все 5 резонансов Шумана одновременно',
            'Lorenz chaos в theta-2 → деактивация DMN',
            'Phase lock: дыхание = master clock всей сессии',
        ],
        'protocol': [
            'Лечь, глаза закрыты · не пытаться "видеть"',
            'Громкость 20–28%  ·  chaos-блок ~22 мин — не двигаться',
        ],
    },
    {
        'key':   'WARRIOR',
        'title': 'ВОИН',
        'time':  '50 мин',
        'glyph': '◆',
        'color': RED,
        'short': 'Beta/Gamma пик · полная активация',
        'desc': [
            'Gamma (30–40 Hz) dominant · ASSR-80 на максимуме',
            'HRTF + ITD + Lorenz chaos с первого блока',
            'Минимальная дельта · фокус на beta-lock финале',
        ],
        'protocol': [
            'Можно сидеть или стоять · не для сна',
            'Громкость 25–35%  ·  хорошо перед тренировкой/задачей',
        ],
    },
]


# ══════════════════════════════════════════
#  LAYOUT HELPERS
# ══════════════════════════════════════════

W = 72   # total width

def hr(char='─', col=DIM_W):
    return f'{col}{char * W}{RESET}'

def center(text, width=W):
    pad = max(0, (width - len(_ANSI_RE.sub('', text))) // 2)
    return ' ' * pad + text

def pad_right(text, width):
    return text + ' ' * max(0, width - len(_ANSI_RE.sub('', text)))


# ══════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════

LOGO = f"""
{GOLD}{BOLD()}  ██████╗ ███████╗███╗  ██╗███████╗███████╗██╗███████╗{RESET}
{GOLD}{BOLD()}  ██╔════╝██╔════╝████╗ ██║██╔════╝██╔════╝██║██╔════╝{RESET}
{GOLD}{BOLD()}  ██║ ███╗█████╗  ██╔██╗██║█████╗  ███████╗██║███████╗{RESET}
{GOLD}{BOLD()}  ██║  ██║██╔══╝  ██║╚████║██╔══╝  ╚════██║██║╚════██║{RESET}
{GOLD}{BOLD()}  ██████╔╝███████╗██║ ╚███║███████╗███████║██║███████║{RESET}
{GOLD}{BOLD()}  ╚═════╝ ╚══════╝╚═╝  ╚══╝╚══════╝╚══════╝╚═╝╚══════╝{RESET}"""

def draw_header():
    print(LOGO)
    print(center(f'{DIM_W}Psychoacoustic Engineering Suite  ·  {AUTHOR}{RESET}'))
    print(center(f'{DIM_W}{URL}{RESET}'))
    print()
    print(hr())
    print()


def draw_menu(sel: int, show_detail: bool = False):
    sys.stdout.write(CLEAR() + HIDE())
    draw_header()

    print(f'{GREY}  Выбери профиль сессии:{RESET}')
    print(f'{DIM_W}  ↑ ↓  навигация    Enter  запуск    M  карта    Q  выход{RESET}')
    print()

    for i, p in enumerate(PROFILES):
        active = (i == sel)
        bg     = BG_SEL if active else BG_DIM
        col    = p['color']
        arrow  = f'{col}▶{RESET}' if active else ' '
        glyph  = f'{col}{BOLD()}{p["glyph"]}{RESET}'
        title  = f'{col}{BOLD()}{p["title"]:<13}{RESET}'
        t      = f'{DIM_W}{p["time"]:<8}{RESET}'
        short  = f'{WHITE}{p["short"]}{RESET}' if active else f'{GREY}{p["short"]}{RESET}'

        line = f'  {arrow} {glyph}  {title} {t}  {short}'
        line += ' ' * max(0, W - len(_ANSI_RE.sub('', line)) + 2)
        print(f'{bg}{line}{RESET}')

        if active and show_detail:
            print()
            for d in p['desc']:
                print(f'    {TEAL}·{RESET} {DIM_W}{d}{RESET}')
            print()

    print()

    if show_detail:
        p = PROFILES[sel]
        print(hr('·'))
        print(f'  {DIM_W}Протокол:{RESET}')
        for line in p['protocol']:
            print(f'  {GOLD}→{RESET} {GREY}{line}{RESET}')
        print()

    sys.stdout.flush()


def draw_confirm(profile: dict) -> bool:
    sys.stdout.write(CLEAR() + HIDE())
    draw_header()

    col = profile['color']
    print(center(f'{col}{BOLD()}{profile["glyph"]}  {profile["title"]}  {profile["glyph"]}{RESET}'))
    print(center(f'{WHITE}{profile["short"]}{RESET}'))
    print()
    print(hr())
    print()
    print(f'  {GREY}Длительность:{RESET} {WHITE}{profile["time"]}{RESET}')
    print()
    print(f'  {GREY}Описание:{RESET}')
    for d in profile['desc']:
        print(f'    {TEAL}·{RESET} {DIM_W}{d}{RESET}')
    print()
    print(f'  {GREY}Протокол:{RESET}')
    for line in profile['protocol']:
        print(f'    {GOLD}→{RESET} {GREY}{line}{RESET}')
    print()
    print(hr())
    print()
    print(f'  {WHITE}Начать рендер?  {GREEN}{BOLD()}[Enter] Да{RESET}  {RED}[Esc/Q] Назад{RESET}')
    print()
    sys.stdout.flush()

    while True:
        k = _getch()
        if k in ('\r', '\n'):        return True
        if k in ('q', 'Q', '\x1b', 'ESC'): return False


# ══════════════════════════════════════════
#  PROGRESS RENDERER
#  FIX: _render_patched() удалён.
#       Вместо дублирования render_session() используется
#       progress_cb — callback передаётся в renderer.render_session().
# ══════════════════════════════════════════

_spin = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
_tick = [0]


def render_with_ui(profile: dict):
    from psychoacoustic.profiles import build_profile
    from psychoacoustic.renderer import render_session, export_map

    blocks   = build_profile(profile['key'])
    total_s  = sum(b.dur_s for b in blocks)
    out_flac = os.path.join(OUT_DIR, f"GENESIS_{profile['key']}_{int(total_s//60)}min.flac")
    out_map  = out_flac.replace('.flac', '_MAP.txt')
    col      = profile['color']
    bar_w    = 40

    BREAK_AFTER  = {i for i, b in enumerate(blocks) if b.dur_s >= 600}
    BREAK_AFTER.add(0)
    total_core   = sum(b.dur_s for b in blocks)
    total_breaks = len(BREAK_AFTER) * 20
    total_render = total_core + total_breaks

    sys.stdout.write(CLEAR() + SHOW())
    draw_header()

    print(center(f'{col}{BOLD()}{profile["glyph"]}  {profile["title"]}  ·  {profile["time"]}{RESET}'))
    print()
    print(hr())
    print()
    export_map(blocks, profile['key'], out_map)

    print(f'  {GREY}Блоков:{RESET} {WHITE}{len(blocks)}{RESET}   '
          f'{GREY}Длительность:{RESET} {WHITE}{total_render/60:.1f} мин{RESET}')
    print(f'  {GREY}Файл:{RESET}  {DIM_W}{os.path.basename(out_flac)}{RESET}')
    print()

    # ── Progress callback — вызывается из render_session перед каждым блоком
    def _progress(idx: int, label: str, pct: float, elapsed: float):
        filled  = int(pct / 100 * bar_w)
        bar     = (f'{col}{"█" * filled}{RESET}'
                   f'{DIM_W}{"░" * (bar_w - filled)}{RESET}')
        eta_str = ''
        if pct > 3:
            eta     = elapsed / pct * (100 - pct)
            eta_str = f'  {DIM_W}ETA {int(eta//60):02d}:{int(eta%60):02d}{RESET}'
        sys.stdout.write(
            f'\r  [{bar}] {col}{pct:4.0f}%{RESET}'
            f'  {WHITE}{label[:32]:<32}{RESET}{eta_str}   '
        )
        sys.stdout.flush()

    t_render_start = time.time()

    render_session(
        blocks, out_flac,
        author=AUTHOR, url=URL,
        progress_cb=_progress,
    )

    elapsed = time.time() - t_render_start
    size_mb = os.path.getsize(out_flac) / 1024 / 1024

    bar_full = f'{col}{"█" * bar_w}{RESET}'
    sys.stdout.write(f'\r  [{bar_full}] {col}100%{RESET}' + ' ' * 50 + '\n')
    sys.stdout.flush()

    print()
    print(hr())
    print()
    print(f'  {GREEN}{BOLD()}✓  Готово{RESET}')
    print()
    print(f'  {GREY}Файл:{RESET}    {WHITE}{out_flac}{RESET}')
    print(f'  {GREY}Размер:{RESET}  {WHITE}{size_mb:.1f} MB{RESET}   '
          f'{GREY}Время рендера:{RESET} {WHITE}{int(elapsed//60):02d}:{int(elapsed%60):02d}{RESET}')
    print()
    print(f'  {GREY}Карта сессии:{RESET}  {DIM_W}{out_map}{RESET}')
    print()
    print(hr())
    print()
    print(f'  {GREY}Протокол:{RESET}')
    for line in profile['protocol']:
        print(f'  {GOLD}→{RESET} {GREY}{line}{RESET}')
    print()
    print(f'  {DIM_W}Нажми любую клавишу...{RESET}')
    sys.stdout.flush()
    _getch()


def show_map(profile: dict):
    from psychoacoustic.profiles import build_profile
    from psychoacoustic.renderer import export_map

    blocks   = build_profile(profile['key'])
    total_s  = sum(b.dur_s for b in blocks)
    tmp_path = os.path.join(OUT_DIR,
                 f"GENESIS_{profile['key']}_{int(total_s//60)}min_MAP.txt")
    export_map(blocks, profile['key'], tmp_path)

    sys.stdout.write(CLEAR() + SHOW())
    draw_header()
    print(f'{GOLD}  Карта: {profile["title"]}{RESET}')
    print()
    with open(tmp_path, encoding='utf-8') as f:
        for line in f:
            print(f'  {DIM_W}{line.rstrip()}{RESET}')
    print()
    print(f'  {DIM_W}Нажми любую клавишу...{RESET}')
    sys.stdout.flush()
    _getch()


# ══════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════

def main():
    sel         = 0
    show_detail = False

    while True:
        draw_menu(sel, show_detail)
        k = _getch()

        if k == 'UP':
            sel = (sel - 1) % len(PROFILES)
            show_detail = False

        elif k == 'DOWN':
            sel = (sel + 1) % len(PROFILES)
            show_detail = False

        elif k in ('\r', '\n'):
            if draw_confirm(PROFILES[sel]):
                try:
                    render_with_ui(PROFILES[sel])
                except KeyboardInterrupt:
                    sys.stdout.write(SHOW())
                    sys.stdout.write(CLEAR())
                    print(f'\n  {RED}Прервано.{RESET}\n')
                    sys.exit(0)
            show_detail = False

        elif k in ('m', 'M'):
            show_map(PROFILES[sel])
            show_detail = False

        elif k in (' ',):
            show_detail = not show_detail

        elif k in ('q', 'Q', '\x03'):
            sys.stdout.write(SHOW() + CLEAR())
            print(f'\n  {GOLD}GENESIS{RESET} {GREY}— до следующей сессии.{RESET}\n')
            sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write(SHOW())
        print()
        sys.exit(0)
