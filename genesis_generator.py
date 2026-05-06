#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════╗
║  GENESIS — Psychoacoustic Engineering Suite                ║
╠════════════════════════════════════════════════════════════╣
║  44100 Hz | FLAC PCM-24 | Stereo                          ║
║  Author: franklin-sys | https://franklin-sys.vercel.app/  ║
╚════════════════════════════════════════════════════════════╝

USAGE:
  python genesis_generator.py                      # GENESIS (default)
  python genesis_generator.py --profile WALK       # 30 min, motion
  python genesis_generator.py --profile SLEEP      # 90 min, OBE windows
  python genesis_generator.py --profile HEALER     # 75 min, deep delta
  python genesis_generator.py --profile ORACLE     # 60 min, clairvoyance
  python genesis_generator.py --profile WARRIOR    # 50 min, activation
  python genesis_generator.py --map                # session map only, no render
  python genesis_generator.py --all                # render all profiles

REQUIRES:
  pip install numpy scipy soundfile

LAYER STACK per block (active flags shown in --map output):
  Binaural       phase-accurate dual-octave pair + 1/f carrier/beat jitter
  Isochronic     hard-gated AM — stronger cortical evoked response
  CFC            theta→gamma phase-amplitude coupling (real hippocampal PAC)
  ASSR-80Hz      brainstem + inferior colliculus entrainment, independent of 40Hz
  ITD rotation   inter-aural phase sweep — vestibular / spatial circuits
  Infra-mod      ultra-slow AM (0.025–0.10 Hz) — ANS + respiratory sync
  SR noise       stochastic-resonance optimal: 15% of signal RMS
  Lorenz chaos   deterministic chaos beat modulation — forces sustained response
  HRTF approx   pinna reflection + head shadow — partial sound externalization
  Phi layer      φ=1.618 ratio 3rd binaural — minimal cognitive friction
  Phase lock     infra envelope drives beat frequency (breath = master clock)
  Schumann stack all 5 Earth resonances (7.83+14.3+20.8+27.3+33.8 Hz) simultaneous
  Pattern breaks 20s neutral resets between major blocks — anti-lock
  Equal-power XF √taper crossfades — zero loudness dip at transitions
"""

import os
import sys
import argparse
import textwrap

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

AUTHOR = 'franklin-sys'
URL    = 'https://franklin-sys.vercel.app/'

ALL_PROFILES = ['GENESIS', 'WALK', 'SLEEP', 'HEALER', 'ORACLE', 'WARRIOR']

PROTOCOL = {
    'GENESIS': [
        "Проводные наушники обязательно (BT разрушает ITD-фазу)",
        "Громкость: 20–28% — плотный микс, тише = лучше",
        "Не засыпать первые 5 мин (gamma ignition активен)",
        "Не чаще 1 раза в 2 дня",
        "10 мин тишины без экранов после — интеграция",
    ],
    'WALK': [
        "Проводные наушники (HRTF+ITD требует фазовой точности)",
        "Можно слушать в движении — специально под прогулку",
        "Громкость: 25–35%",
        "Не садиться за руль",
    ],
    'SLEEP': [
        "Лежать, глаза закрыты с первой секунды",
        "Засыпать можно — архитектура учитывает это",
        "Окна осознания: ~40, 65, 88 мин — не пугаться резкого возврата",
        "Проводные наушники или подушка-динамик",
    ],
    'HEALER': [
        "Можно полностью засыпать",
        "528 Hz — мягкий тембр, не требует усилий",
        "Громкость: 15–25%",
        "Идеально: ночной цикл или дневной сон",
    ],
    'ORACLE': [
        "Лежать, глаза закрыты",
        "Не пытаться 'видеть' — позволить образам приходить самим",
        "Громкость: 20–28%",
        "Chaos-блок (~22 мин) — самый интенсивный, не двигаться",
    ],
    'WARRIOR': [
        "Можно сидеть или стоять",
        "Громкость: 25–35%",
        "Не использовать для сна — выраженная активация",
        "Хорошо перед важной задачей / тренировкой",
    ],
}


def main():
    parser = argparse.ArgumentParser(
        description='GENESIS — Psychoacoustic Engineering Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Profiles:
          GENESIS   full-spectrum flagship: ignition→void→integration (63 min)
          WALK      alpha/theta expansion in motion, operator mode (30 min)
          SLEEP     deep delta + 3x OBE-window cycles (90 min)
          HEALER    delta restoration, 528 Hz, phi-geometry (75 min)
          ORACLE    Schumann/theta, clairvoyance corridor (60 min)
          WARRIOR   beta/gamma peak activation, chaos+HRTF (50 min)
        """)
    )
    parser.add_argument('--profile', default='GENESIS',
                        choices=ALL_PROFILES,
                        help='Session profile (default: GENESIS)')
    parser.add_argument('--map', action='store_true',
                        help='Print session map only, no render')
    parser.add_argument('--all', action='store_true',
                        help='Render all profiles sequentially')
    args = parser.parse_args()

    # Deferred import — only after args parsed (faster --help)
    from psychoacoustic.profiles  import build_profile
    from psychoacoustic.renderer  import render_session, export_map

    targets = ALL_PROFILES if args.all else [args.profile.upper()]

    for profile in targets:
        blocks    = build_profile(profile)
        total_s   = sum(b.dur_s for b in blocks)
        out_flac  = os.path.join(OUT_DIR, f"GENESIS_{profile}_{int(total_s//60)}min.flac")
        out_map   = out_flac.replace('.flac', '_MAP.txt')

        export_map(blocks, profile, out_map)

        if args.map and not args.all:
            print(open(out_map, encoding='utf-8').read())
            return

        print("═" * 64)
        print(f"  GENESIS — {profile}")
        print(f"  SR: 44100 Hz | FLAC PCM-24 | Stereo")
        render_session(blocks, out_flac,
                       author=AUTHOR, url=URL,
                       fade_s=8.0, break_min_dur=600.0)
        print()
        print("  PROTOCOL:")
        for line in PROTOCOL.get(profile, []):
            print(f"  — {line}")
        print("═" * 64)
        print()


if __name__ == '__main__':
    main()
