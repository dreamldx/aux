"""Minimal ctypes binding for the LVGL shared library built by the Makefile."""
import ctypes
import os

_LIB = os.path.join(os.path.dirname(__file__), "..", "build", "liblvgl_aux.so")
_lib = ctypes.CDLL(os.path.abspath(_LIB))

_p = ctypes.c_void_p
_i32 = ctypes.c_int32

_lib.aux_init.argtypes = [ctypes.c_char_p, ctypes.POINTER(_i32), ctypes.POINTER(_i32)]
_lib.aux_init.restype = _p
_lib.aux_style_bg.argtypes = [_p, ctypes.c_uint32]
_lib.aux_canvas.argtypes = [_p, _i32, _i32]
_lib.aux_canvas.restype = _p
_lib.aux_glyphs_init.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int,
                                 ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int]
_lib.aux_draw.argtypes = [_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
_lib.lv_timer_handler.restype = ctypes.c_uint32


def init(card="/dev/dri/card1"):
    """Open the DRM display. Returns (screen, width, height)."""
    w, h = _i32(), _i32()
    screen = _lib.aux_init(card.encode(), ctypes.byref(w), ctypes.byref(h))
    if not screen:
        raise RuntimeError(f"cannot open DRM display on {card}")
    return screen, w.value, h.value


def set_bg(obj, rgb):
    _lib.aux_style_bg(obj, rgb)


def canvas(parent, w, h):
    return _lib.aux_canvas(parent, w, h)


def load_glyphs(ttf, size_min, size_max, chars, cell_w):
    """Render `chars` with FreeType at every size in [size_min, size_max]."""
    cps = (ctypes.c_uint32 * len(chars))(*[ord(c) for c in chars])
    n = _lib.aux_glyphs_init(ttf.encode(), size_min, size_max, cps, len(chars), cell_w)
    if n <= 0:
        raise RuntimeError(f"could not load glyphs from {ttf} (code {n}: -2 open font, -4 too many sizes, 0 no glyphs)")
    return n


def set_palette(colors, head):
    arr = (ctypes.c_uint32 * len(colors))(*colors)
    _lib.aux_set_palette(arr, len(colors), head)


def draw(cv, glyph, shade, col_size, cols):
    _lib.aux_draw(cv, bytes(glyph), bytes(shade), bytes(col_size), cols)


def timer_handler():
    """Run LVGL timers/rendering. Returns the suggested sleep time in ms."""
    return _lib.lv_timer_handler()


def deinit():
    _lib.lv_deinit()
