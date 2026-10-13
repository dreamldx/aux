# aux

用 LVGL (v9.2) + DRM/KMS + Python 在 HDMI 副屏上显示黑客帝国数字雨。
目标平台:Raspberry Pi 4,Debian 13,无桌面环境。

## 依赖

```
sudo apt install -y build-essential cmake libdrm-dev libfreetype-dev fonts-noto-cjk
```

## 构建与运行

```
git clone --recurse-submodules https://github.com/dreamldx/aux
cd aux
make -j4                       # 生成 build/liblvgl_aux.so
python3 -m matrix.rain         # Ctrl+C 退出
```

用户需在 `video` 组里才能打开 `/dev/dri/card1`。

## 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--card` | `/dev/dri/card1` | DRM 设备 |
| `--fps` | 30 | 帧率 |
| `--size` | 48 | 基准字号 (px) |
| `--size-range` | 15 | 每列字号在 `size ± range` 内随机 |
| `--gap` | 2 | 列间额外间距 (px) |
| `--font` | Noto Sans CJK | 含半角片假名的 TTF/TTC |
| `--seconds` | 0 | 运行 N 秒后退出,0 为一直运行 |

## 结构

- `csrc/lv_conf.h`:LVGL 配置(DRM 驱动、32 位色、FreeType)
- `csrc/shim.c`:C 薄层,初始化 DRM 显示,用 FreeType 渲染字形并直接画进全屏 `lv_canvas`
- `matrix/lv.py`:ctypes 绑定
- `matrix/rain.py`:数字雨逻辑
