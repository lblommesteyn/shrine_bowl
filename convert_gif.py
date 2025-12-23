from PIL import Image
import os

gif_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\viz_play_anim.gif"
output_path = r"C:\Users\16476\OneDrive\Desktop\ss_sbc\viz_play_anim_static.png"

try:
    with Image.open(gif_path) as im:
        im.seek(0)
        im.save(output_path)
    print(f"Saved static image to {output_path}")
except Exception as e:
    print(f"Error: {e}")
