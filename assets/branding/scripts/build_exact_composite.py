import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# 1. Load Image 2 (source of A Y A and background)
img2_path = "/Users/contabilidad/.gemini/antigravity-ide/brain/fa5fa454-ce6d-4e6f-9a30-77dc642032c3/.user_uploaded/media_1793225948907.png"
base_img = Image.open(img2_path).convert("RGBA")
W, H = base_img.size
base_arr = np.array(base_img)

# Detect background color around J and L to cleanly mask out old J and old L
# Background sample around (x=10, y=10) or (x=500, y=10)
bg_color = tuple(base_arr[10, 500])
print("Background sample at (500, 10):", bg_color)

# The bounding boxes from our previous detection:
# Letter 0 (old J): x=[54, 173]
# Letter 1 (A): x=[234, 419]
# Letter 2 (Y): x=[438, 607]
# Letter 3 (A): x=[626, 812]
# Letter 4 (old L): x=[870, 977]

# Let's create a clean canvas with the exact background of Image 2
# We can sample the vertical background gradient of Image 2 at x=200 (between letters)
col_slice = base_arr[:, 200, :].copy() # shape (H, 4)
clean_bg = np.tile(col_slice[:, np.newaxis, :], (1, W, 1))
clean_bg_img = Image.fromarray(clean_bg.astype(np.uint8), "RGBA")

# Extract only A Y A from Image 2:
# The region from x=210 to x=840 contains A Y A with their subtle illumination/glow
# Let's paste the A Y A region onto clean_bg_img
aya_crop = base_img.crop((210, 0, 840, H))
clean_bg_img.paste(aya_crop, (210, 0), aya_crop)

# Now let's draw the custom J and mirrored Ⴑ with matching style
# Let's inspect the white color and glow in A Y A:
# A Y A white letters have RGB close to (255, 255, 255) with soft anti-aliased edges
# Let's create an oversized mask (4x super-sampling) for J and Ⴑ, then resize with Lanczos for ultra-crisp edges

scale = 4
mask_w, mask_h = W * scale, H * scale
mask = Image.new("L", (mask_w, mask_h), 0)
draw = ImageDraw.Draw(mask)

# Baseline in original: y = 163. Cap height: y = 35. Total H = 128.
# Target centers:
# In Image 2, old J was at x=[54, 173], center = 113.5
# old L was at x=[870, 977], center = 923.5
# Distance from center of Y (522.5):
# Left: 522.5 - 113.5 = 409
# Right: 923.5 - 522.5 = 401
# Perfect symmetrical position: center ± 405 px!
center_y = 522.5
j_left_center = center_y - 405  # ~117.5
j_right_center = center_y + 405 # ~927.5

y_top = 35.0
y_bot = 163.0
char_h = y_bot - y_top # 128

# Custom J parameters (scaled to 128px height):
# In SVG: H=80, capitel_w=64, capitel_h=10, stem_w=18, hook_r=22
# Scale factor = 128 / 80 = 1.6
s = char_h / 80.0
cap_w = 64.0 * s    # ~102.4
cap_h = 10.0 * s    # ~16.0
stem_w = 18.0 * s   # ~28.8
stem_right_rel = 0.0 # alignment reference
# Let's define the path for J relative to its right edge of stem (x=0, y=0 at top-right):
# Capitel goes from -cap_w to 0 at y in [0, cap_h]
# Stem goes from -stem_w to 0 at y in [0, 85*s]
# Hook curves left from -stem_w down to y_bot, over to -cap_w, and up

def draw_custom_j(drawer, cx, is_mirrored=False):
    # cx is the center of the letter
    # letter width is cap_w (~102.4)
    # left edge = cx - cap_w/2, right edge = cx + cap_w/2
    x0 = cx - cap_w / 2.0
    x1 = cx + cap_w / 2.0
    
    # We will draw on a high-res sub-canvas then paste
    sub_w = int(cap_w + 30) * scale
    sub_h = int(char_h + 30) * scale
    sub_img = Image.new("L", (sub_w, sub_h), 0)
    sub_draw = ImageDraw.Draw(sub_img)
    
    # Coordinates in sub_img:
    margin = 15.0 * scale
    top = margin
    bot = top + char_h * scale
    ch = cap_h * scale
    sw = stem_w * scale
    cw = cap_w * scale
    
    # Standard J (hook to left, capitel on top):
    # Top bar:
    bx0 = margin
    bx1 = margin + cw
    by0 = top
    by1 = top + ch
    sub_draw.rounded_rectangle([bx0, by0, bx1, by1], radius=3*scale, fill=255)
    
    # Stem:
    sx0 = bx1 - sw
    sx1 = bx1
    sy0 = top
    sy1 = top + (char_h - 32.0 * s) * scale
    sub_draw.rectangle([sx0, sy0, sx1, sy1], fill=255)
    
    # Hook (arc + inner cutout):
    # Outer bottom bounding box for arc:
    arc_x0 = margin
    arc_x1 = bx1
    arc_y0 = bot - 64.0 * s * scale
    arc_y1 = bot
    sub_draw.pieslice([arc_x0, arc_y0, arc_x1, arc_y1], 0, 180, fill=255)
    
    # Vertical connector left
    sub_draw.rectangle([margin, arc_y0 + 32.0*s*scale - 20*scale, margin + sw, arc_y0 + 32.0*s*scale], fill=255)
    
    # Inner cutout of the hook:
    in_x0 = margin + sw
    in_x1 = sx0
    in_y0 = arc_y0 + sw
    in_y1 = bot - sw
    sub_draw.pieslice([in_x0, in_y0, in_x1, in_y1], 0, 180, fill=0)
    
    # If mirrored, flip horizontally
    if is_mirrored:
        sub_img = sub_img.transpose(Image.FLIP_LEFT_RIGHT)
        
    return sub_img, int(cx * scale - sub_w / 2), int(y_top * scale - margin)

# Draw left J
sub_j_left, px_l, py_l = draw_custom_j(draw, j_left_center, is_mirrored=False)
mask.paste(sub_j_left, (px_l, py_l), sub_j_left)

# Draw right J (mirrored)
sub_j_right, px_r, py_r = draw_custom_j(draw, j_right_center, is_mirrored=True)
mask.paste(sub_j_right, (px_r, py_r), sub_j_right)

# Downscale mask with high quality anti-aliasing
mask_final = mask.resize((W, H), Image.LANCZOS)

# Create pure white letter layer with matching soft glow
white_layer = Image.new("RGBA", (W, H), (255, 255, 255, 255))
# Composite J and Ⴑ onto clean_bg_img
clean_bg_img.paste(white_layer, (0, 0), mask_final)

# Save result
output_composite = "/Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth/assets/branding/jayaj_exact_hybrid_wordmark.png"
clean_bg_img.save(output_composite, "PNG")
print("Saved exact composite to:", output_composite)
