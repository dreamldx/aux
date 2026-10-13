LVGL := lvgl
SRCS := $(shell find $(LVGL)/src -name '*.c') csrc/shim.c
OBJS := $(patsubst %.c,build/%.o,$(SRCS))
CFLAGS := -O2 -fPIC -MMD -DLV_CONF_INCLUDE_SIMPLE \
          -I$(LVGL) -Icsrc $(shell pkg-config --cflags libdrm freetype2)

build/liblvgl_aux.so: $(OBJS)
	$(CC) -shared -o $@ $^ $(shell pkg-config --libs libdrm freetype2) -lm

build/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf build/lvgl build/csrc build/liblvgl_aux.so
-include $(OBJS:.o=.d)
