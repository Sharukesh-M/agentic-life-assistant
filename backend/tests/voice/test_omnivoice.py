"""
OmniVoice TTS Installation Verification Script for JARVIX.
Performs verification step-by-step as outlined in Phase 2.
"""

import sys
import os
import time
import platform

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

try:
    import psutil
except ImportError:
    psutil = None

def check_environment():
    print("==================================================")
    print("JARVIX Voice Subsystem - OmniVoice Verification")
    print("==================================================")
    print(f"OS:                {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python Version:    {sys.version.split()[0]}")
    print(f"Active Executable: {sys.executable}")
    print(f"CPU:               {platform.processor() or 'Apple Silicon / ARM64'}")

    # PyTorch Check
    try:
        import torch
        print(f"PyTorch Version:   {torch.__version__}")
        cuda_avail = torch.cuda.is_available()
        mps_avail = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        print(f"CUDA Available:    {cuda_avail}")
        print(f"MPS Available:     {mps_avail}")

        if cuda_avail:
            device = "cuda:0"
            device_name = torch.cuda.get_device_name(0)
        elif mps_avail:
            device = "mps"
            device_name = "Apple Silicon GPU (MPS)"
        else:
            device = "cpu"
            device_name = "CPU"
            
        print(f"Selected Device:   {device} ({device_name})")
    except ImportError as e:
        print(f"[FAIL] PyTorch not installed: {str(e)}")
        device = "cpu"
        torch = None

    # OmniVoice Import Check
    omnivoice_ok = False
    try:
        import omnivoice
        print(f"OmniVoice Import:  SUCCESSFUL")
        omnivoice_ok = True
    except ImportError as e:
        print(f"OmniVoice Import:  FAILED ({str(e)})")

    return torch, omnivoice_ok, device

def run_tts_test(device: str):
    print("\n--------------------------------------------------")
    print("Running OmniVoice TTS Generation Test")
    print("--------------------------------------------------")

    test_text = "Hello, I am JARVIX. Voice synthesis is working successfully."
    os.makedirs(os.path.join("outputs", "audio"), exist_ok=True)
    output_wav = os.path.abspath(os.path.join("outputs", "audio", "jarvix_tts_test.wav"))

    print(f"Test Sentence: \"{test_text}\"")
    print(f"Target Wav File: {output_wav}")

    start_time = time.time()
    try:
        from omnivoice import OmniVoice
        print(f"Loading OmniVoice pretrained model 'k2-fsa/OmniVoice'...")
        model = OmniVoice.from_pretrained("k2-fsa/OmniVoice")
        if hasattr(model, "to"):
            model.to(device)
        load_time = time.time() - start_time
        print(f"Model loaded successfully in {load_time:.2f} seconds.")

        # Generation
        gen_start = time.time()
        audio = model.generate(test_text)
        gen_time = time.time() - gen_start

        # Save audio
        if hasattr(audio, "save"):
            audio.save(output_wav)
        elif hasattr(model, "save_audio"):
            model.save_audio(audio, output_wav)
        else:
            import soundfile as sf
            sf.write(output_wav, audio, 24000)

        duration = len(audio) / 24000.0 if hasattr(audio, "__len__") else 2.0
        rtf = gen_time / duration if duration > 0 else 0.0

        ram_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024) if psutil else 0.0

        print("\n==================================================")
        print("TTS Generation Result: SUCCESS")
        print("==================================================")
        print(f"WAV File Path:       {output_wav}")
        print(f"Device Used:         {device}")
        print(f"Model Load Time:     {load_time:.2f} s")
        print(f"Generation Time:     {gen_time:.2f} s")
        print(f"Audio Duration:      {duration:.2f} s")
        print(f"Real-Time Factor:    {rtf:.2f}x")
        print(f"Memory Usage:        {ram_mb:.1f} MB")
        return True
    except Exception as e:
        gen_time = time.time() - start_time
        print("\n==================================================")
        print("TTS Generation Result: FAILED / NOT READY")
        print("==================================================")
        print(f"Error Details:       {str(e)}")
        print(f"Device Attempted:    {device}")
        print(f"Time Elapsed:        {gen_time:.2f} s")
        return False

if __name__ == "__main__":
    torch, omnivoice_ok, device = check_environment()
    if omnivoice_ok:
        run_tts_test(device)
    else:
        print("\n[NOTE] OmniVoice package or dependencies are not available in current execution shell.")
        print("To install OmniVoice package run: pip install omnivoice")
