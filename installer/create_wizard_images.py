"""
Tạo ảnh BMP cho Inno Setup wizard (WizardStyle=modern):
- wizard_banner.bmp  : 164x314 — banner trái (kích thước chuẩn IS7)
- wizard_icon.bmp    : 55x55  — icon nhỏ góc trên phải
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.dirname(os.path.abspath(__file__))
BG_PATH = os.path.join(os.path.dirname(OUT), "images", "background.png")


def make_banner():
    """164x314 — dark gradient với text Dyno All In One"""
    w, h = 164, 314
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    # Gradient nền: #0d1b3e → #1a1a2e → #2a0a14
    for y in range(h):
        t = y / h
        if t < 0.5:
            r = int(13 + (26 - 13) * (t / 0.5))
            g = int(27 + (26 - 27) * (t / 0.5))
            b = int(62 + (46 - 62) * (t / 0.5))
        else:
            t2 = (t - 0.5) / 0.5
            r = int(26 + (42 - 26) * t2)
            g = int(26 + (10 - 26) * t2)
            b = int(46 + (20 - 46) * t2)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Overlay background.png nếu có
    if os.path.isfile(BG_PATH):
        try:
            bg = Image.open(BG_PATH).convert("RGB")
            bg = bg.resize((w, h), Image.LANCZOS)
            # Blend: 30% background, 70% gradient
            img = Image.blend(img, bg, alpha=0.30)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    # Grid overlay nhẹ
    for x in range(0, w, 40):
        draw.line([(x, 0), (x, h)], fill=(30, 42, 74, 40))
    for y in range(0, h, 40):
        draw.line([(0, y), (w, y)], fill=(30, 42, 74, 40))

    # Accent line đỏ bên trái
    draw.rectangle([(0, 0), (3, h)], fill=(233, 69, 96))

    # Text
    try:
        font_big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
        font_med = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 11)
        font_small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 9)
    except Exception:
        font_big = font_med = font_small = ImageFont.load_default()

    draw.text((12, 60), "DYNO", font=font_big, fill=(233, 69, 96))
    draw.text((12, 88), "ALL IN ONE", font=font_big, fill=(255, 255, 255))
    draw.text((12, 124), "Phần mềm quản lý", font=font_med, fill=(136, 153, 187))
    draw.text((12, 140), "dyno xe", font=font_med, fill=(136, 153, 187))
    draw.text((12, 162), "Phiên bản 1.0", font=font_small, fill=(100, 120, 160))

    # Đường kẻ ngang
    draw.line([(12, 180), (140, 180)], fill=(233, 69, 96), width=1)

    draw.text((12, 240), "© 2026 Khoa Lê", font=font_small, fill=(80, 100, 140))
    draw.text((12, 254), "dynoaio.vercel.app", font=font_small, fill=(80, 100, 140))

    img.save(os.path.join(OUT, "wizard_banner.bmp"), "BMP")
    print("✓ wizard_banner.bmp (164x314) created")


def make_icon():
    """55x55 — icon nhỏ"""
    w, h = 55, 55
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        t = y / h
        r = int(13 + (42 - 13) * t)
        g = int(27 + (10 - 27) * t)
        b = int(62 + (20 - 62) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    draw.ellipse([(4, 4), (51, 51)], outline=(233, 69, 96), width=2)

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
    except Exception:
        font = ImageFont.load_default()
    draw.text((16, 12), "D", font=font, fill=(233, 69, 96))

    img.save(os.path.join(OUT, "wizard_icon.bmp"), "BMP")
    print("✓ wizard_icon.bmp (55x55) created")


if __name__ == "__main__":
    try:
        make_banner()
        make_icon()
        print("\nDone! Chạy installer.iss bằng Inno Setup Compiler.")
    except ImportError:
        print("Cần cài Pillow: pip install pillow")
