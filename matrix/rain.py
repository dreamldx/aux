"""Matrix digital rain rendered with LVGL over DRM/KMS."""
import argparse
import random
import signal
import time

from . import lv

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"   # face 0 = Japanese
SIZE = 48                  # base font size in px
SIZE_RANGE = 15            # each column draws at a random size in SIZE +/- SIZE_RANGE
# half-width katakana (U+FF66..U+FF9D) plus digits and a few symbols, as in the film
GLYPHS = "".join(chr(c) for c in range(0xFF66, 0xFF9E)) + "0123456789:.=*+<>|"
SHADES = 16          # trail brightness levels, 1 = just behind the head
HEAD = 255


def palette():
    out = []
    for i in range(SHADES):
        t = i / (SHADES - 1)
        out.append((int(20 * (1 - t)) << 16) | (int(255 - 215 * t) << 8) | int(65 * (1 - t)))
    return out


class Column:
    def __init__(self, rows, size_idx):
        self.rows = rows
        self.size_idx = size_idx
        self.glyphs = [random.randrange(len(GLYPHS)) for _ in range(rows)]
        self.reset(initial=True)

    def reset(self, initial=False):
        self.length = random.randint(max(4, self.rows // 3), self.rows)
        self.speed = random.uniform(0.08, 0.37)    # rows per frame
        self.head = (random.uniform(-self.rows, self.rows) if initial
                     else -random.uniform(0, self.rows * 0.6))

    def step(self):
        self.head += self.speed
        if self.head - self.length > self.rows:
            self.reset()
        for _ in range(2):                                # random glyph flicker
            self.glyphs[random.randrange(self.rows)] = random.randrange(len(GLYPHS))

    def shades(self):
        head = int(self.head)
        out = bytearray(self.rows)
        for r in range(max(0, head - self.length + 1), min(self.rows, head + 1)):
            d = head - r
            out[r] = HEAD if d == 0 else 1 + int((d - 1) / self.length * SHADES)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default="/dev/dri/card1")
    ap.add_argument("--font", default=FONT)
    ap.add_argument("--size", type=int, default=SIZE, help="base font size in px")
    ap.add_argument("--size-range", type=int, default=SIZE_RANGE, help="columns vary by +/- this many px")
    ap.add_argument("--gap", type=int, default=2, help="extra px between columns")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=float, default=0, help="exit after N seconds (0 = run forever)")
    args = ap.parse_args()

    running = [True]
    signal.signal(signal.SIGINT, lambda *_: running.__setitem__(0, False))
    signal.signal(signal.SIGTERM, lambda *_: running.__setitem__(0, False))

    screen, w, h = lv.init(args.card)
    print(f"display {w}x{h}")
    lv.set_bg(screen, 0x000000)
    lv.set_palette(palette(), 0xE8FFF0)
    cv = lv.canvas(screen, w, h)

    size_min, size_max = args.size - args.size_range, args.size + args.size_range
    cell_w = size_max // 2 + args.gap
    lv.load_glyphs(args.font, size_min, size_max, GLYPHS, cell_w)
    n_cols = w // cell_w
    col_size = bytes(random.randrange(size_max - size_min + 1) for _ in range(n_cols))
    cols = [Column(h // (size_min + k), k) for k in col_size]
    max_rows = h // size_min
    glyph = bytearray(n_cols * max_rows)
    shade = bytearray(n_cols * max_rows)

    frame_dt = 1.0 / args.fps
    t0 = next_frame = time.monotonic()
    frames = 0
    try:
        while running[0]:
            now = time.monotonic()
            if args.seconds and now - t0 >= args.seconds:
                break
            if now >= next_frame:
                for i, c in enumerate(cols):
                    c.step()
                    glyph[i:i + n_cols * c.rows:n_cols] = bytes(c.glyphs)
                    shade[i:i + n_cols * c.rows:n_cols] = c.shades()
                lv.draw(cv, glyph, shade, col_size, n_cols)
                frames += 1
                next_frame += frame_dt
                if next_frame < now:                      # fell behind; don't spiral
                    next_frame = now + frame_dt
            lv.timer_handler()
            time.sleep(0.002)
    finally:
        elapsed = time.monotonic() - t0
        print(f"{frames} frames in {elapsed:.1f}s = {frames / elapsed:.1f} fps")
        lv.deinit()


if __name__ == "__main__":
    main()
