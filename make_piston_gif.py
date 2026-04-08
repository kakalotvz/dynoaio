"""Generate images/loading.gif — two interlocking gears rotating."""
from PIL import Image, ImageDraw
import math, os

W, H = 160, 160
FRAMES = 36
BG_COLOR = (8, 8, 24)

C_GEAR1     = (180, 185, 200)   # large gear body
C_GEAR1_HI  = (210, 215, 228)   # highlight
C_GEAR2     = (140, 145, 165)   # small gear body
C_GEAR2_HI  = (170, 175, 190)
C_ACCENT    = (233, 69, 96)     # red accent (center hub)
C_ACCENT2   = (255, 120, 60)    # orange accent (small gear hub)
C_HOLE      = (8, 8, 24)        # center hole
C_OUTLINE   = (60, 65, 90)


def gear_polygon(cx, cy, r_outer, r_inner, n_teeth, angle_offset=0.0):
    """Return polygon points for a gear with n_teeth."""
    pts = []
    for i in range(n_teeth * 4):
        frac = i / (n_teeth * 4)
        angle = 2 * math.pi * frac + angle_offset
        # Alternate between outer (tooth tip) and inner (tooth root)
        if (i % 4) in (1, 2):
            r = r_outer
        else:
            r = r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def draw_gear(d: ImageDraw.Draw, cx, cy, r_outer, r_inner, n_teeth,
              angle, body_color, hi_color, hub_color, hub_r=8):
    pts = gear_polygon(cx, cy, r_outer, r_inner, n_teeth, angle)
    # Body
    d.polygon(pts, fill=body_color, outline=C_OUTLINE)
    # Simple highlight arc (top-left quadrant lighter)
    hi_pts = gear_polygon(cx, cy, r_outer - 2, r_inner + 2, n_teeth, angle)
    # Hub circle
    d.ellipse([cx - hub_r, cy - hub_r, cx + hub_r, cy + hub_r],
              fill=hub_color, outline=C_OUTLINE, width=1)
    # Center hole
    hole_r = hub_r - 4
    if hole_r > 1:
        d.ellipse([cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r],
                  fill=C_HOLE)
    # Spoke lines
    for s in range(3):
        sa = angle + s * (2 * math.pi / 3)
        x1 = cx + math.cos(sa) * (hub_r - 1)
        y1 = cy + math.sin(sa) * (hub_r - 1)
        x2 = cx + math.cos(sa) * (r_inner - 2)
        y2 = cy + math.sin(sa) * (r_inner - 2)
        d.line([(x1, y1), (x2, y2)], fill=C_OUTLINE, width=2)


def make_frame(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))  # fully transparent background
    d = ImageDraw.Draw(img)

    # No background panel — transparent

    # Large gear: center-left, 11 teeth
    R1_OUT, R1_IN = 46, 36
    N1 = 11
    cx1, cy1 = 62, 82
    angle1 = 2 * math.pi * t

    # Small gear: meshes with large gear, 7 teeth
    # Pitch radii ratio = N2/N1 → small gear rotates faster
    N2 = 7
    R2_OUT, R2_IN = 30, 22
    # Distance between centers = R1_pitch + R2_pitch (approx r_inner avg)
    pitch1 = (R1_OUT + R1_IN) / 2
    pitch2 = (R2_OUT + R2_IN) / 2
    dist = pitch1 + pitch2
    cx2 = int(cx1 + dist * math.cos(math.radians(-30)))
    cy2 = int(cy1 + dist * math.sin(math.radians(-30)))
    # Counter-rotate, speed ratio = N1/N2
    angle2 = -2 * math.pi * t * (N1 / N2) + math.pi / N2

    draw_gear(d, cx1, cy1, R1_OUT, R1_IN, N1, angle1,
              C_GEAR1, C_GEAR1_HI, C_ACCENT, hub_r=10)
    draw_gear(d, cx2, cy2, R2_OUT, R2_IN, N2, angle2,
              C_GEAR2, C_GEAR2_HI, C_ACCENT2, hub_r=7)

    return img


os.makedirs("images", exist_ok=True)
frames = [make_frame(i / FRAMES) for i in range(FRAMES)]

# Convert to palette mode with transparency for GIF
def to_gif_frame(img: Image.Image) -> Image.Image:
    # Convert RGBA to P (palette) with transparency
    return img.convert("RGBA").quantize(colors=255, method=Image.Quantize.FASTOCTREE)

gif_frames = [to_gif_frame(f) for f in frames]
gif_frames[0].save(
    "images/loading.gif",
    save_all=True,
    append_images=gif_frames[1:],
    loop=0,
    duration=40,
    disposal=2,
    transparency=0,
    optimize=False,
)
print(f"Created images/loading.gif  ({W}x{H}px, {FRAMES} frames, transparent bg)")
