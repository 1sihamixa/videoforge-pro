"""Create an avatar video from existing audio + avatar image"""
import sys
import os
sys.path.insert(0, 'C:/autosystem')
os.chdir('C:/autosystem')

from video_generator import TalkingHeadGenerator

# Use avatar image and existing TTS audio
image_path = 'avatar_images/passive_income_ideas/0.jpg.png'
audio_path = 'test_tts2.mp3'
output_path = 'output/avatar_video.mp4'

print("Creating avatar video...")
print("Image:", image_path)
print("Audio:", audio_path)

gen = TalkingHeadGenerator(
    image_path=image_path,
    audio_path=audio_path,
    output_path=output_path,
    fps=25,
    resolution=(1080, 1920)  # Vertical video
)

gen.generate()
print("Done! Output:", output_path)

import os
size = os.path.getsize(output_path)
print("Size: {:.1f} MB".format(size / 1024 / 1024))
