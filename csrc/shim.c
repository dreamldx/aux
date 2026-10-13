#include <time.h>
#include <stdint.h>
#include "lvgl.h"

static uint32_t tick_cb(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000u + ts.tv_nsec / 1000000u);
}

/* Returns the screen object, or NULL if the DRM display could not be opened. */
lv_obj_t * aux_init(const char * card, int32_t * w, int32_t * h)
{
    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t * disp = lv_linux_drm_create();
    if(disp == NULL) return NULL;
    lv_linux_drm_set_file(disp, card, -1);
    *w = lv_display_get_horizontal_resolution(disp);
    *h = lv_display_get_vertical_resolution(disp);
    return lv_screen_active();
}

const lv_font_t * aux_font_unscii16(void) { return &lv_font_unscii_16; }

/* Style helpers taking plain integers, so Python never passes lv_color_t by value. */
void aux_style_bg(lv_obj_t * obj, uint32_t hex)
{
    lv_obj_set_style_bg_color(obj, lv_color_hex(hex), 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
}


#include <stdlib.h>
#include <string.h>

#define MAX_GLYPHS 160
#define MAX_SIZES 32
#define MAX_SHADES 64

static uint32_t * canvas_px;
static int32_t canvas_w, canvas_h;
static uint8_t * glyph_a8[MAX_SIZES][MAX_GLYPHS];   /* [size][glyph]: cell_w x size coverage */
static int size_px[MAX_SIZES];                      /* font size == cell height of size k */
static int size_count, glyph_count;
static int cell_w;
static uint32_t shade_rgb[MAX_SHADES];
static uint32_t head_rgb = 0xE8FFF0;

/* Full-screen canvas drawn directly by aux_draw(). */
lv_obj_t * aux_canvas(lv_obj_t * parent, int32_t w, int32_t h)
{
    canvas_w = w;
    canvas_h = h;
    canvas_px = calloc((size_t)w * h, sizeof(uint32_t));
    lv_obj_t * c = lv_canvas_create(parent);
    lv_canvas_set_buffer(c, canvas_px, w, h, LV_COLOR_FORMAT_XRGB8888);
    lv_obj_set_pos(c, 0, 0);
    return c;
}

/* Render every code point at every size in [size_min, size_max] with FreeType, each into
 * a cw x size coverage cell. Returns the glyph count per size, or a negative error code. */
int aux_glyphs_init(const char * ttf, int size_min, int size_max, const uint32_t * cps, int n, int cw)
{
    if(size_max - size_min + 1 > MAX_SIZES) return -4;
    cell_w = cw;
    size_count = 0;
    for(int size = size_min; size <= size_max; size++) {
        lv_font_t * font = lv_freetype_font_create(ttf, LV_FREETYPE_FONT_RENDER_MODE_BITMAP, size,
                                                   LV_FREETYPE_FONT_STYLE_NORMAL);
        if(font == NULL) return -2;                 /* font file / face open failed */
        int k = size_count++;
        size_px[k] = size;
        int count = 0;
        for(int i = 0; i < n && count < MAX_GLYPHS; i++) {
            lv_font_glyph_dsc_t g;
            if(!lv_font_get_glyph_dsc(font, &g, cps[i], 0)) continue;
            if(g.box_w == 0 || g.box_h == 0) continue;
            /* FreeType ignores the draw_buf argument and returns its own cached lv_draw_buf_t */
            const lv_draw_buf_t * buf = lv_font_get_glyph_bitmap(&g, NULL);
            if(buf == NULL) continue;
            uint8_t * cell = calloc((size_t)cw * size, 1);
            /* centre the advance box horizontally; sit glyphs on a common baseline */
            int x0 = (cw - (int)g.adv_w) / 2 + g.ofs_x;
            int y0 = (int)(size * 0.86f) - g.ofs_y - g.box_h;
            for(int y = 0; y < g.box_h; y++) {
                int dy = y0 + y;
                if(dy < 0 || dy >= size) continue;
                const uint8_t * src = (const uint8_t *)buf->data + (size_t)y * buf->header.stride;
                for(int x = 0; x < g.box_w; x++) {
                    int dx = x0 + x;
                    if(dx >= 0 && dx < cw) cell[dy * cw + dx] = src[x];
                }
            }
            lv_font_glyph_release_draw_data(&g);
            glyph_a8[k][count++] = cell;
        }
        glyph_count = count;
    }
    return glyph_count;
}

void aux_set_palette(const uint32_t * rgb, int n, uint32_t head)
{
    if(n > MAX_SHADES) n = MAX_SHADES;
    memcpy(shade_rgb, rgb, n * sizeof(uint32_t));
    head_rgb = head;
}

/* glyph/shade are cols x stride row-major (column c, row r at r * cols + c).
 * shade: 0 = empty, 1..n = palette entry, 255 = head.
 * col_size[c] picks the size index of column c, which also sets its row count. */
void aux_draw(lv_obj_t * canvas, const uint8_t * glyph, const uint8_t * shade,
              const uint8_t * col_size, int cols)
{
    memset(canvas_px, 0, (size_t)canvas_w * canvas_h * sizeof(uint32_t));
    for(int c = 0; c < cols; c++) {
        int k = col_size[c];
        int ch = size_px[k];
        int rows = canvas_h / ch;
        for(int r = 0; r < rows; r++) {
            uint8_t s = shade[r * cols + c];
            if(s == 0) continue;
            uint32_t rgb = (s == 255) ? head_rgb : shade_rgb[s - 1];
            uint32_t cr = (rgb >> 16) & 0xFF, cg = (rgb >> 8) & 0xFF, cb = rgb & 0xFF;
            const uint8_t * a8 = glyph_a8[k][glyph[r * cols + c] % glyph_count];
            uint32_t * dst = canvas_px + (size_t)(r * ch) * canvas_w + c * cell_w;
            for(int y = 0; y < ch; y++, dst += canvas_w) {
                for(int x = 0; x < cell_w; x++) {
                    uint32_t a = a8[y * cell_w + x];
                    if(a) dst[x] = ((cr * a / 255) << 16) | ((cg * a / 255) << 8) | (cb * a / 255);
                }
            }
        }
    }
    lv_obj_invalidate(canvas);
}

/* Coverage cell of glyph i at size index k (cell_w x size bytes), for tests. */
const uint8_t * aux_glyph_ptr(int k, int i)
{
    return (k >= 0 && k < size_count && i >= 0 && i < glyph_count) ? glyph_a8[k][i] : NULL;
}
