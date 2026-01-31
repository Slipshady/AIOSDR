#!/usr/bin/env python3
import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
import numpy as np
from rtlsdr import RtlSdr
import time
import os
import subprocess
import whisper
import socket
import webbrowser
from datetime import datetime

class UltimateSDRScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Surface SDR Pro: Manual Control & Radar")
        self.root.geometry("1200x950")
        self.root.configure(bg="#121212")
        self.is_scanning = False
        self.audio_enabled = tk.BooleanVar(value=True)
        self.transcribe_enabled = tk.BooleanVar(value=True)
        self.current_band = "ALL"
        self.setup_ui()
        self.log_message("System: Initializing AI Model (Tiny)...")
        try:
        
            self.model = whisper.load_model("tiny", device="cpu")
            self.log_message("System: AI Model Ready.")
        except Exception as e:
            self.log_message(f"AI ERROR: {e}")

    def setup_ui(self):
        header_frame = tk.Frame(self.root, bg="#121212")
        header_frame.pack(side="top", fill="x", padx=20, pady=10)
        
        tk.Button(header_frame, text="🌐 VIEW FLIGHT MAP", font=("Arial", 10, "bold"),
                  bg="#8e44ad", fg="white", width=22, relief="flat",
                  command=lambda: webbrowser.open("http://localhost:8080")).pack(side="right")

        sidebar = tk.Frame(self.root, bg="#1f1f1f", width=200)
        sidebar.pack(side="left", fill="y")
        
        tk.Label(sidebar, text="RADIO BANDS", font=("Arial", 12, "bold"), bg="#1f1f1f", fg="gray").pack(pady=20)
        
        bands = ["ALL", "FM", "VHF", "UHF", "FRS/GMRS", "NOAA", "AIRCRAFT"]
        for b in bands:
            tk.Button(sidebar, text=b, font=("Arial", 10, "bold"), bg="#2d2d2d", fg="white",
                      activebackground="#444444", relief="flat", height=2, 
                      command=lambda opt=b: self.set_band(opt)).pack(fill="x", padx=10, pady=5)

        tk.Button(sidebar, text="SAVE LOG", font=("Arial", 10, "bold"), bg="#3498db", fg="white",
                  relief="flat", command=self.save_log_to_file).pack(side="bottom", fill="x", padx=10, pady=20)

        main_area = tk.Frame(self.root, bg="#121212")
        main_area.pack(side="right", expand=True, fill="both")

        self.freq_display = tk.Label(main_area, text="IDLE", font=("Courier", 72, "bold"), 
                                     bg="black", fg="#00FF00", pady=20)
        self.freq_display.pack(pady=10, fill="x")

        ctrl_frame = tk.Frame(main_area, bg="#121212")
        ctrl_frame.pack(pady=5)
        tk.Checkbutton(ctrl_frame, text="Live Audio", variable=self.audio_enabled, 
                       bg="#121212", fg="white", selectcolor="black").pack(side="left", padx=20)
        tk.Checkbutton(ctrl_frame, text="Transcribe", variable=self.transcribe_enabled, 
                       bg="#121212", fg="white", selectcolor="black").pack(side="left", padx=20)

        self.threshold_slider = tk.Scale(main_area, from_=-60, to=0, orient="horizontal", 
                                         length=600, label="Squelch Sensitivity (dB)", 
                                         bg="#121212", fg="white", highlightthickness=0)
        self.threshold_slider.set(-32)
        self.threshold_slider.pack(pady=10)

        self.delay_slider = tk.Scale(main_area, from_=2, to=30, orient="horizontal", 
                                     length=600, label="Scanner Delay (Seconds)", 
                                     bg="#121212", fg="white", highlightthickness=0)
        self.delay_slider.set(6)
        self.delay_slider.pack(pady=10)

        self.btn_toggle = tk.Button(main_area, text="START MONITOR", font=("Arial", 16, "bold"), 
                                    bg="#27ae60", fg="white", command=self.toggle_scan, 
                                    height=2, width=30, relief="flat")
        self.btn_toggle.pack(pady=15)

        self.log_area = scrolledtext.ScrolledText(main_area, height=20, bg="#0a0a0a", 
                                                  fg="#00FF00", font=("Courier", 10))
        self.log_area.pack(padx=20, pady=10, fill="both", expand=True)

    def log_message(self, msg):
        """Timestamped console output"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_area.see(tk.END)

    def set_band(self, band):
        """Switches scanning mode"""
        self.current_band = band
        self.log_message(f"System: Switched to {band}")

    def save_log_to_file(self):
        """Exports log area to text file"""
        file_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if file_path:
            with open(file_path, "w") as f:
                f.write(self.log_area.get("1.0", tk.END))
            self.log_message(f"System: Log saved successfully.")

    def transcribe_audio(self, filename, freq_mhz):
        """Threads Whisper AI to process recorded hits"""
        if not hasattr(self, 'model'): return
        try:
            result = self.model.transcribe(filename, fp16=False)
            text = result['text'].strip()
            if text and len(text) > 3:
                self.log_message(f"AI ({freq_mhz}MHz): {text}")
        except Exception as e:
            self.log_message(f"AI Transcription Error: {e}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)

    def adsb_listener(self):
        """Full manual link to dump1090 --net data socket"""
        self.log_message("System: Attempting to link to manual dump1090 stream...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(("127.0.0.1", 30003))
            self.log_message("System: Aircraft Data Link ONLINE.")
            
            while self.current_band == "AIRCRAFT" and self.is_scanning:
                try:
                    raw_data = sock.recv(4096).decode('utf-8', errors='ignore')
                    for line in raw_data.split('\n'):
                        parts = line.split(',')
                        if len(parts) > 12:
                            call = parts[10].strip()
                            if call:
                                alt = parts[11].strip() or "---"
                                spd = parts[12].strip() or "---"
                                self.log_message(f"RADAR: {call} | ALT: {alt}ft | SPD: {spd}kt")
                except socket.timeout:
                    continue
                except Exception:
                    break
            sock.close()
        except Exception:
            self.log_message("ERROR: No decoder found. Did you run 'dump1090 --net' in a terminal?")

    def toggle_scan(self):
        """Starts/Stops the primary scanner thread"""
        if not self.is_scanning:
            self.is_scanning = True
            self.btn_toggle.config(text="STOP MONITOR", bg="#c0392b")
            threading.Thread(target=self.scanner_loop, daemon=True).start()
        else:
            self.is_scanning = False
            self.btn_toggle.config(text="START MONITOR", bg="#27ae60")

    def scanner_loop(self):
        """Full verbose scanner logic"""
        sdr = None
        
        frs_list = [462.5625, 462.5875, 462.6125, 462.6375, 462.6625, 462.6875, 462.7125]
        noaa_list = [162.400, 162.425, 162.450, 162.475, 162.500, 162.525, 162.550]
        vhf_list = list(np.arange(144.0, 148.0, 0.5))
        fm_list = list(np.arange(88.1, 107.9, 2.0))

        while self.is_scanning:
            if self.current_band == "AIRCRAFT":
                if sdr: 
                    sdr.close()
                    sdr = None
                self.freq_display.config(text="1090.00", fg="#3498db")
                self.adsb_listener() 
                continue

            try:
                if sdr is None:
                    sdr = RtlSdr()
                    sdr.sample_rate = 2.048e6 
                    sdr.gain = 'auto'

                if self.current_band == "NOAA": active_list = noaa_list
                elif self.current_band == "FM": active_list = fm_list
                elif self.current_band == "VHF": active_list = vhf_list
                elif self.current_band == "FRS/GMRS": active_list = frs_list
                else: active_list = [101.1, 162.4, 462.5625]

                for f_mhz in active_list:
                    if not self.is_scanning or self.current_band == "AIRCRAFT": 
                        break
                    
                    sdr.center_freq = f_mhz * 1e6
                    self.freq_display.config(text=f"{f_mhz:.4f}", fg="#00FF00")
                    self.root.update()
                    
                    time.sleep(0.1)
                    samples = sdr.read_samples(1024 * 32)
                    power = 10 * np.log10(np.var(samples) + 1e-10)
                    
                    if power > self.threshold_slider.get():
                        self.log_message(f"SIGNAL HIT: {f_mhz:.4f} MHz")
                        self.freq_display.config(fg="#e74c3c")
                        
                        sdr.close()
                        sdr = None
                        time.sleep(1)
                        
                        dwell = int(self.delay_slider.get())
                        audio_file = f"capture_{int(f_mhz)}.wav"
                        
                        cmd = f"rtl_fm -f {int(f_mhz*1e6)} -M nfm -s 24k -g 42 -l 0 -t {dwell} | tee >(aplay -r 24000 -f S16_LE) | ffmpeg -y -f s16le -ar 24000 -ac 1 -i - -t {dwell+1} {audio_file}"
                        
                        subprocess.run(cmd, shell=True, executable='/bin/bash', stderr=subprocess.DEVNULL)
                        
                        if self.transcribe_enabled.get():
                            threading.Thread(target=self.transcribe_audio, args=(audio_file, f_mhz), daemon=True).start()
                        
                        time.sleep(1)
                        break 

            except Exception as e:
                self.log_message(f"Hardware/Driver Error: {e}")
                if sdr: sdr.close()
                sdr = None
                time.sleep(2)

        if sdr: sdr.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateSDRScanner(root)
    root.mainloop()
