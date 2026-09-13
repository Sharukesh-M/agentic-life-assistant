"""
Fixture generator for JARVIX Voice Subsystem Tests.
Generates deterministic test WAV audio files and reference transcripts.
"""

import os
import wave
import struct
import math

def generate_test_wav(filepath: str, duration: float = 2.0, sample_rate: int = 16000, freq: float = 440.0):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    n_samples = int(sample_rate * duration)
    with wave.open(filepath, "wb") as f:
        f.setnchannels(1)       # Mono
        f.setsampwidth(2)      # 16-bit PCM
        f.setframerate(sample_rate)
        for i in range(n_samples):
            # Generate 440 Hz sine wave tone
            val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            f.writeframes(struct.pack("<h", val))

def generate_all_fixtures():
    fixtures_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Valid test input WAV
    valid_wav = os.path.join(fixtures_dir, "test_input.wav")
    generate_test_wav(valid_wav, duration=2.0)
    
    # Text transcript for test_input.wav
    with open(os.path.join(fixtures_dir, "test_input.wav.txt"), "w", encoding="utf-8") as f:
        f.write("Hello JARVIX, what can you help me with?")
        
    # 2. Planning test input WAV
    planning_wav = os.path.join(fixtures_dir, "test_planning.wav")
    generate_test_wav(planning_wav, duration=2.0, freq=523.25)
    with open(os.path.join(fixtures_dir, "test_planning.wav.txt"), "w", encoding="utf-8") as f:
        f.write("Create a 7-day Python learning plan.")
        
    # 3. High impact safety test input WAV
    safety_wav = os.path.join(fixtures_dir, "test_safety.wav")
    generate_test_wav(safety_wav, duration=2.0, freq=659.25)
    with open(os.path.join(fixtures_dir, "test_safety.wav.txt"), "w", encoding="utf-8") as f:
        f.write("Create a calendar meeting for tomorrow at 4.")
        
    # 4. Empty WAV (0 bytes)
    empty_wav = os.path.join(fixtures_dir, "empty_input.wav")
    with open(empty_wav, "wb") as f:
        pass
        
    print(f"[JARVIX Voice Fixtures] Generated test audio fixtures in {fixtures_dir}")

if __name__ == "__main__":
    generate_all_fixtures()
