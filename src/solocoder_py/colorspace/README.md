# 颜色空间转换器 (Colorspace Converter) 模块

## 模块功能

本模块实现了一个纯数值计算的颜色空间转换器，支持常见颜色表示之间的相互转换，以及颜色相关的实用功能，包括：

- **四种颜色空间互转**：支持 RGB（0-255 整数或 0-1 浮点）、HSL、HSV、HEX 四种颜色表示之间的双向转换
- **色域裁剪 (Gamut Clipping)**：自动将超出合法范围的通道值裁剪到最近边界，避免异常
- **Alpha 合成**：支持两个带 Alpha 透明度的 RGB 颜色按 over 操作进行合成
- **WCAG 对比度计算**：计算两色之间的相对亮度和对比度比值，判定是否符合 WCAG 2.0 AA/AAA 级无障碍标准

---

## 核心类职责

### 数据类 (Data Classes)

所有颜色类均使用 `@dataclass(frozen=True)` 定义，不可变且可哈希。构造时自动进行范围裁剪。

| 类 | 字段 | 说明 |
|----|------|------|
| `RGB` | `r, g, b, alpha=1.0` | RGB 颜色，通道值范围 0-255（浮点存储），Alpha 0-1 |
| `HSL` | `h, s, l, alpha=1.0` | HSL 颜色：色相 0-360°，饱和度/亮度 0-100% |
| `HSV` | `h, s, v, alpha=1.0` | HSV 颜色：色相 0-360°，饱和度/明度 0-100% |
| `HEX` | `value` | HEX 字符串，统一规范化为 `#rrggbb` 或 `#rrggbbaa` 小写格式 |

**每个颜色类均提供 `to_rgb()`、`to_hsl()`、`to_hsv()`、`to_hex()` 方法**实现跨空间转换。

### 辅助类与枚举

| 类 | 说明 |
|----|------|
| `WCAGLevel` | 枚举：`AA` / `AAA` |
| `WCAGTextSize` | 枚举：`NORMAL` / `LARGE` |
| `ContrastResult` | 对比度结果数据类，包含 `ratio` 和各 WCAG 级别判定布尔值 |

### 异常类层次

```
ColorSpaceError
├── InvalidRGBError       RGB 值非法
├── InvalidHexError       HEX 字符串格式非法
├── InvalidHSLError       HSL 值非法
├── InvalidHSVError       HSV 值非法
└── InvalidAlphaError     Alpha 值非法
```

---

## 四种颜色空间的数学定义与转换公式

### 1. RGB (Red-Green-Blue)

**定义**：加法混色模型，每个通道值域 `[0, 255]`（整数）或 `[0, 1]`（浮点归一化）。

本模块内部存储使用浮点 0-255，提供以下接口：
- `RGB(r, g, b, alpha=1.0)`：直接使用 0-255 构造
- `RGB.from_float(r, g, b, alpha=1.0)`：使用 0-1 浮点构造
- `.r_float / .g_float / .b_float` 属性：获取归一化 0-1 浮点值
- `.to_int()`：返回 `(r, g, b)` 整数元组

---

### 2. RGB ↔ HSL 转换

#### HSL 定义
- **H (Hue 色相)**：`[0, 360)`，色环上的角度（红=0°，绿=120°，蓝=240°）
- **S (Saturation 饱和度)**：`[0, 100]`，0% 为灰色，100% 为最鲜艳
- **L (Lightness 亮度)**：`[0, 100]`，0% 纯黑，50% 原色，100% 纯白

#### RGB → HSL 公式

首先归一化：`r', g', b' = r/255, g/255, b/255`

```
C_max = max(r', g', b')
C_min = min(r', g', b')
Δ = C_max - C_min

L = (C_max + C_min) / 2

若 Δ = 0（灰度）：
    H = 0
    S = 0
否则：
    S = Δ / (1 - |2L - 1|)

    H = 60° × ⎧ ((g' - b') / Δ) mod 6   若 C_max = r'
             ⎨ ((b' - r') / Δ) + 2     若 C_max = g'
             ⎩ ((r' - g') / Δ) + 4     若 C_max = b'

最终 H ∈ [0, 360), S ∈ [0, 100], L ∈ [0, 100]
```

#### HSL → RGB 公式

首先归一化：`h' = h/360, s' = s/100, l' = l/100`

```
若 s' = 0（灰度）：
    r' = g' = b' = l'
否则：
    q = l' × (1 + s')         若 l' < 0.5
        l' + s' - l' × s'     若 l' ≥ 0.5
    p = 2 × l' - q

    r' = hue_to_rgb(p, q, h' + 1/3)
    g' = hue_to_rgb(p, q, h')
    b' = hue_to_rgb(p, q, h' - 1/3)

其中 hue_to_rgb(p, q, t)：
    先将 t 归一化到 [0, 1)
    ⎧ p + (q - p) × 6t              若 t < 1/6
    ⎨ q                             若 1/6 ≤ t < 1/2
    ⎩ p + (q - p) × (2/3 - t) × 6   若 1/2 ≤ t < 2/3
    ⎪ p                             否则

最终 r = r' × 255, g = g' × 255, b = b' × 255
```

---

### 3. RGB ↔ HSV 转换

#### HSV 定义
- **H (Hue 色相)**：`[0, 360)`，与 HSL 相同
- **S (Saturation 饱和度)**：`[0, 100]`，0% 为灰色，100% 为最鲜艳
- **V (Value 明度)**：`[0, 100]`，0% 纯黑，100% 为原色（白色需 S=0 时 V=100）

> **HSL vs HSV 区别**：HSL 中 L=100 一定是白色；HSV 中 V=100 不一定是白色（还需 S=0）。

#### RGB → HSV 公式

归一化同上：

```
C_max = max(r', g', b')
C_min = min(r', g', b')
Δ = C_max - C_min

V = C_max

若 Δ = 0（灰度）：
    H = 0
    S = 0
否则：
    S = Δ / C_max    (C_max ≠ 0)
    H 的计算与 RGB→HSL 完全相同
```

#### HSV → RGB 公式

归一化：`h' = h/360, s' = s/100, v' = v/100`

```
若 s' = 0（灰度）：
    r' = g' = b' = v'
否则：
    h_i = ⌊h' × 6⌋ mod 6   （色相扇区 0-5）
    f = h' × 6 - h_i       （扇区内的分数位置）
    p = v' × (1 - s')
    q = v' × (1 - s' × f)
    t = v' × (1 - s' × (1 - f))

    根据 h_i 选择：
    h_i=0: (v', t, p)   h_i=1: (q, v', p)   h_i=2: (p, v', t)
    h_i=3: (p, q, v')   h_i=4: (t, p, v')   h_i=5: (v', p, q)
```

---

### 4. HSL ↔ HSV 转换

HSL 与 HSV 之间的直接转换较为繁琐，本模块采用**通过 RGB 中转**的方式：
- HSL → RGB → HSV
- HSV → RGB → HSL

由于所有转换均为纯数学计算，中间转换的精度损失由裁剪机制保证结果合法。

---

### 5. RGB ↔ HEX 转换

#### HEX 格式

支持以下四种格式，解析后统一规范化为小写：
- `#RGB`（3 位简写，展开为 `#RRGGBB`，如 `#f00` → `#ff0000`）
- `#RGBA`（4 位简写，展开为 `#RRGGBBAA`）
- `#RRGGBB`（6 位标准格式）
- `#RRGGBBAA`（8 位带 Alpha，AA ∈ `[00, ff]` → Alpha ∈ `[0, 1]`）

#### RGB → HEX 公式

```
R_int = round(clamp(r, 0, 255))
G_int = round(clamp(g, 0, 255))
B_int = round(clamp(b, 0, 255))

若 alpha < 1：
    A_int = round(alpha × 255)
    HEX = "#{:02x}{:02x}{:02x}{:02x}".format(R, G, B, A)
否则：
    HEX = "#{:02x}{:02x}{:02x}".format(R, G, B)
```

#### HEX → RGB 公式

```
R = int(hex_str[1:3], 16)
G = int(hex_str[3:5], 16)
B = int(hex_str[5:7], 16)
若长度 9（含 Alpha）：
    A = int(hex_str[7:9], 16) / 255
否则：
    A = 1.0
```

---

## 色域裁剪 (Gamut Clipping) 规则

当构造颜色对象或转换过程中通道值超出合法范围时，**自动裁剪到最近边界**，而不抛出异常：

| 颜色空间 | 通道 | 合法范围 | 裁剪规则 |
|----------|------|----------|----------|
| RGB | r, g, b | `[0, 255]` | `<0 → 0`, `>255 → 255` |
| RGB/HSL/HSV | alpha | `[0, 1]` | `<0 → 0`, `>1 → 1` |
| HSL/HSV | h (色相) | `[0, 360)` | **模 360 归一化**（负角度加 360），如 `h=-30 → 330`, `h=400 → 40` |
| HSL/HSV | s (饱和度) | `[0, 100]` | `<0 → 0`, `>100 → 100` |
| HSL | l (亮度) | `[0, 100]` | `<0 → 0`, `>100 → 100` |
| HSV | v (明度) | `[0, 100]` | `<0 → 0`, `>100 → 100` |

NaN 值统一裁剪到下界（0）。

---

## Alpha 合成 (Alpha Compositing) 公式

实现 Porter-Duff **"over"** 合成操作：前景色 (foreground) 叠加到背景色 (background) 上。

### 标准 over 公式

设前景色 `F = (Fr, Fg, Fb, Fa)`，背景色 `B = (Br, Bg, Bb, Ba)`，所有通道已归一化至 `[0, 1]`：

```
输出 Alpha:
    Ao = Fa + Ba × (1 - Fa)

若 Ao = 0（两者全透明）：
    输出 RGB = (0, 0, 0)
否则：
    Ro = (Fr × Fa + Br × Ba × (1 - Fa)) / Ao
    Go = (Fg × Fa + Bg × Ba × (1 - Fa)) / Ao
    Bo = (Fb × Fa + Bb × Ba × (1 - Fa)) / Ao
```

### 特殊场景验证

- **不透明前景 (Fa=1)**：`Ao=1`, `Ro=Fr`，背景被完全覆盖
- **完全透明前景 (Fa=0)**：`Ao=Ba`, `Ro=Br`，背景原样输出
- **半透明白叠加到黑**（`F=(1,1,1,0.5)`, `B=(0,0,0,1)`）：
  - `Ao = 0.5 + 1 × 0.5 = 1`
  - `Ro = (1 × 0.5 + 0) / 1 = 0.5` → 输出中灰色 (128, 128, 128)

---

## WCAG 对比度计算规则

### 1. 相对亮度 (Relative Luminance)

WCAG 2.0 定义的 sRGB 相对亮度，用于衡量颜色对人眼的明暗感知：

对每个通道先做 **sRGB → 线性 RGB** 转换：

```
对于 sRGB 通道值 C_srgb ∈ [0, 1]（即 R/255, G/255, B/255）：

C_linear = C_srgb / 12.92                          若 C_srgb ≤ 0.04045
           ((C_srgb + 0.055) / 1.055) ^ 2.4        若 C_srgb > 0.04045
```

相对亮度：

```
L = 0.2126 × R_linear + 0.7152 × G_linear + 0.0722 × B_linear
```

> 绿色贡献最大（71.52%），其次是红色（21.26%），蓝色最小（7.22%），符合人眼对不同色光的敏感度。

### 2. 对比度比值 (Contrast Ratio)

```
L1 = 较亮色的相对亮度
L2 = 较暗色的相对亮度

对比度 = (L1 + 0.05) / (L2 + 0.05)
```

+0.05 是为了避免除零（纯黑 L=0）。

对比度范围：`[1, 21]`
- **1:1**：两色相同（如白底白字）
- **21:1**：最大对比度（纯黑 #000 vs 纯白 #fff）

### 3. WCAG 2.0 对比度标准

| 级别 | 正常文本 (≤18pt) | 大文本 (>18pt 或 >14pt 粗体) |
|------|-------------------|------------------------------|
| AA (最低) | ≥ 4.5 : 1 | ≥ 3.0 : 1 |
| AAA (最高) | ≥ 7.0 : 1 | ≥ 4.5 : 1 |

---

## 使用示例

### 基本颜色空间转换

```python
from solocoder_py.colorspace import RGB, HSL, HSV, HEX

# RGB 转其他空间
red = RGB(255, 0, 0)
print(red.to_hsl())   # HSL(h=0.0, s=100.0, l=50.0, alpha=1.0)
print(red.to_hsv())   # HSV(h=0.0, s=100.0, v=100.0, alpha=1.0)
print(red.to_hex())   # HEX(value='#ff0000')

# HEX 转 RGB
hex_blue = HEX("#0000ff")
rgb = hex_blue.to_rgb()
print(rgb.r, rgb.g, rgb.b)  # 0 0 255

# HSL 简写 HEX
hsl_purple = HSL(270, 100, 50)
print(hsl_purple.to_hex().value)  # '#7f00ff' 或类似

# 使用浮点 RGB
gray = RGB.from_float(0.5, 0.5, 0.5)
print(gray.to_int())  # (128, 128, 128)
```

### 自动裁剪与归一化

```python
# RGB 通道越界自动裁剪
color = RGB(300, -10, 256)
print(color.r, color.g, color.b)  # 255.0 0.0 255.0

# 色相自动归一化
hsl = HSL(-30, 150, 50)  # 色相负数、饱和度超标
print(hsl.h, hsl.s, hsl.l)  # 330.0 100.0 50.0

# HEX 3 位简写自动展开
print(HEX("#f00").value)   # '#ff0000'
print(HEX("#ABC").value)   # '#aabbcc'

# HEX 大小写不敏感
print(HEX("#FF00FF").value)  # '#ff00ff'
```

### Alpha 合成

```python
from solocoder_py.colorspace import RGB, alpha_composite

# 半透明白色叠加到黑色（标准测试场景）
fg = RGB(255, 255, 255, alpha=0.5)
bg = RGB(0, 0, 0, alpha=1.0)
result = alpha_composite(fg, bg)
print(result.to_int())      # (128, 128, 128) ≈ 中灰

# 不透明前景完全覆盖背景
fg_opaque = RGB(255, 0, 0, alpha=1.0)
bg_green = RGB(0, 255, 0, alpha=1.0)
result = alpha_composite(fg_opaque, bg_green)
print(result.to_int())      # (255, 0, 0)
```

### WCAG 对比度计算

```python
from solocoder_py.colorspace import (
    RGB, check_contrast, contrast_ratio,
    relative_luminance, meets_aa, meets_aaa,
    WCAGLevel, WCAGTextSize,
)

black = RGB(0, 0, 0)
white = RGB(255, 255, 255)

# 计算对比度比值
print(contrast_ratio(black, white))    # 21.0  (最大对比度)
print(contrast_ratio(white, white))    # 1.0   (最小对比度)

# 计算相对亮度
print(relative_luminance(white))       # 1.0
print(relative_luminance(black))       # 0.0

# 便捷判定函数
print(meets_aa(black, white))          # True  (21:1 ≥ 4.5:1)
print(meets_aaa(black, white))         # True  (21:1 ≥ 7:1)
print(meets_aa(white, white))          # False (1:1 < 4.5:1)

# 完整对比度报告
result = check_contrast(black, white)
print(result.ratio)                    # 21.0
print(result.aa_normal)                # True
print(result.aaa_normal)               # True
print(result.passes)
# {'AA_normal': True, 'AA_large': True, 'AAA_normal': True, 'AAA_large': True}

# 使用枚举判定
print(result.meets(WCAGLevel.AA, WCAGTextSize.NORMAL))   # True
```
