AIOSDR is a software radio suite designed to turn a standard RTL-SDR dongle into an AI-augmented surveillance and tracking station. It bridges the gap between raw radio signals and digital intelligence by combining digital signal processing (DSP) with modern machine learning.


1. The Hardware Interface Layer
At its base, the program uses the pyrtlsdr library to communicate with the RTL-SDR USB hardware.

Tuning: The script sends commands to the R820T2 tuner chip to oscillate at specific frequencies (e.g., 101.1 MHz for FM or 162.4 MHz for NOAA).

I/Q Sampling: It captures raw "In-phase" and "Quadrature" samples. These are complex numbers representing the phase and amplitude of the radio wave.


2. The Multi-Mode Processing Logic
The program operates in two distinct modes depending on the band you select:

Voice/Analog Mode (FM, VHF, NOAA)
When a signal hit is detected, the program temporarily releases control of the hardware and initiates a Subprocess Pipe. It calls rtl_fm to demodulate the signal into audible speech. This audio is simultaneously:

Streamed to your speakers via aplay (Live Audio).

Recorded and converted via ffmpeg into a .wav file for the AI to read.

Digital Mode (AIRCRAFT/ADS-B)
In this mode, the program stops scanning and becomes a TCP Client. It expects an external "Server" (dump1090) to be decoding the 1090MHz pulses from airplanes.

It connects to a local network socket (Port 30003).

It parses the "BaseStation" format—a comma-separated string containing the flight ID, altitude, and speed.

The Map feature leverages the web server built into dump1090 to visualize this data on a browser-based radar.

3. The Artificial Intelligence Layer
This is the "Pro" feature of the app. Once a voice transmission is captured as a .wav file, the program hands it off to OpenAI's Whisper (Tiny Model).

Model Loading: The "Tiny" model is used because it is optimized for speed on CPUs like the one in your Surface Book.

Transcription: The AI analyzes the spectral features of the audio (using those mel_filters.npz files) and converts the radio chatter into text.

Threading: This happens in the "background" (a separate thread) so that the scanner can keep looking for new signals while the AI is still "thinking" about the last one.

4. The User Interface (GUI)
The UI is built using Tkinter, the standard Python interface toolkit. It acts as the "Command Center," coordinating the various threads:

The Main Loop: Keeps the window responsive.

The Scanner Thread: Runs the heavy math for signal detection.


Summary of Capabilities
Automated Monitoring: Watches "known" frequencies and only alerts you when there is activity.

Intelligence Logging: Creates a permanent text record of both technical data (signal hits) and human data (what was actually said).

Visual Radar: Integrates local radio data with a web-based mapping interface for situational awareness
