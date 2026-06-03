from PIL import Image, ImageDraw, ImageFont

# Create professional KBMC logo matching the official design
width, height = 200, 200
image = Image.new('RGB', (width, height), color='#C41E3A')
draw = ImageDraw.Draw(image)

try:
    font_large = ImageFont.truetype("C:\\Windows\\Fonts\\segoeui.ttf", 48)
    font_small = ImageFont.truetype("C:\\Windows\\Fonts\\segoeui.ttf", 10)
except:
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Draw "KBMC" in large white text - centered
try:
    text = "KBMC"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2 - 20
    
    draw.text((x, y), text, font=font_large, fill='white')
except Exception as e:
    print(f"Error drawing text: {e}")

# Save the logo
logo_path = "c:\\Users\\techstaff1\\Downloads\\kbmc_logo.png"
image.save(logo_path)
print(f"Logo created: {logo_path}")
