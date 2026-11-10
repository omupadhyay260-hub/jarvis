"""
JARVIS v2 - Rotating 3D globe + time-based greeting (Windows, Hindi + English)

Install (CMD mein ek baar):
    pip install SpeechRecognition pyaudio pyttsx3 pyautogui pyperclip pywhatkit AppOpener requests

Gemini API key (free): https://aistudio.google.com/apikey  ->  neeche paste karo
Run:  python jarvis.py
(Globe ke liye tkinter chahiye, wo Python ke saath already aata hai.)
"""

import datetime
import math
import os
import random
import re
import time
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser

import pyautogui
import pyperclip
import pyttsx3
import requests
import speech_recognition as sr

# ---------------- SETTINGS ----------------
GEMINI_API_KEY = "YAHAN_APNI_KEY_PASTE_KARO"
try:   # jarvis.exe/jarvis.py ke saath wali 'gemini_key.txt' file se key padhta hai
    _p = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "gemini_key.txt")
    GEMINI_API_KEY = open(_p, encoding="utf-8").read().strip() or GEMINI_API_KEY
except OSError:
    pass
GEMINI_MODEL = "gemini-2.0-flash"
WAKE_WORD = "jarvis"
LANG = "hi-IN"            # English ke liye "en-IN"
USER_NAME = "Sir"         # apna naam likh sakte ho

# ---------------- SHARED STATE (globe isse chalta hai) ----------------
state = {"mode": "idle", "text": "Say 'Jarvis'"}   # idle / listening / speaking

recognizer = sr.Recognizer()


# ---------------- GREETING ----------------
def time_greeting():
    h = datetime.datetime.now().hour
    if 5 <= h < 12:
        wish = "Good morning"
    elif 12 <= h < 17:
        wish = "Good afternoon"
    elif 17 <= h < 21:
        wish = "Good evening"
    else:
        wish = "Good night"
    return f"{wish} {USER_NAME}! Main Jarvis hoon. Bataiye, kya kaam hai?"


# ---------------- VOICE ----------------
def speak(text):
    print("Jarvis:", text)
    state["mode"], state["text"] = "speaking", text[:60]
    engine = pyttsx3.init()          # har baar naya engine = Windows par hang nahi hota
    engine.setProperty("rate", 175)
    engine.say(text)
    engine.runAndWait()
    state["mode"], state["text"] = "idle", "Say 'Jarvis'"


def listen(timeout=6, phrase_limit=10):
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            text = recognizer.recognize_google(audio, language=LANG)
            print("Aap:", text)
            return text.lower()
        except Exception:
            return ""


def ask_ai(question):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
    body = {"contents": [{"parts": [{"text":
            "Tum Jarvis ho, ek helpful assistant. Hinglish mein chhota jawab do "
            "(2-3 vaakya, bina markdown). Sawal: " + question}]}]}
    try:
        r = requests.post(url, json=body, timeout=30)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "Maaf kijiye, AI se jawab nahi mil paya. API key check karein."


# ---------------- ACTIONS ----------------
def type_text(text):
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")


def dictation_mode():
    speak("Likhna shuru. Band karne ke liye bolo: likhna band karo.")
    while True:
        state["mode"], state["text"] = "listening", "Typing mode..."
        text = listen(timeout=10, phrase_limit=15)
        if not text:
            continue
        if "likhna band" in text or "stop typing" in text:
            speak("Likhna band kar diya.")
            return
        if "new line" in text or "nayi line" in text:
            pyautogui.press("enter")
            continue
        type_text(text + " ")


def open_app(name):
    from AppOpener import open as app_open
    try:
        app_open(name, match_closest=True, output=False)
        speak(f"{name} khol diya.")
    except Exception:
        speak(f"{name} nahi mila.")


def install_app(name):
    speak(f"{name} install karun? Haan ya na bolo.")
    state["mode"] = "listening"
    answer = listen()
    if any(w in answer for w in ["haan", "han", "yes", "kar do"]):
        speak(f"{name} install ho raha hai, thoda wait karo.")
        try:
            result = subprocess.run(
                ["winget", "install", "--accept-package-agreements",
                 "--accept-source-agreements", name], capture_output=True, text=True)
            ok = result.returncode == 0
        except FileNotFoundError:        # Windows 10 par winget na ho to
            ok = False
        if ok:
            speak(f"{name} install ho gaya.")
        else:
            speak("Seedha install nahi ho paya. Google par download page khol raha hoon.")
            webbrowser.open(f"https://www.google.com/search?q=download+{name}")
    else:
        speak("Theek hai, cancel.")


SITES = {
    "chrome": "https://www.google.com", "google": "https://www.google.com",
    "youtube": "https://www.youtube.com", "whatsapp": "https://web.whatsapp.com",
    "gmail": "https://mail.google.com", "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com", "maps": "https://maps.google.com",
    "chatgpt": "https://chatgpt.com", "github": "https://github.com",
}
last_site = {"name": None}


def run_step(cmd):
    """Ek chhota kaam. Jaise: 'open youtube' ya 'type masoom sharma song'."""
    if any(w in cmd for w in ["exit", "band ho ja", "alvida", "bye"]):
        speak("Alvida!")
        os._exit(0)

    if "likhna shuru" in cmd or "start typing" in cmd:
        dictation_mode()

    # --- type <text> : jahan bhi cursor/search box ho wahan likhta hai ---
    elif cmd.startswith("type ") or cmd.startswith("likho "):
        text = cmd.split(" ", 1)[1].strip()
        if last_site["name"] == "youtube":
            pyautogui.press("/")             # YouTube ka search box select
            time.sleep(0.5)
            type_text(text)
            pyautogui.press("enter")
            speak(f"YouTube par {text} search kiya.")
        elif last_site["name"] in ("google", "chrome"):
            type_text(text)                  # Google khulte hi search box ready hota hai
            pyautogui.press("enter")
            speak(f"{text} search kiya.")
        else:
            type_text(text)
            speak("Likh diya.")

    # --- open <name> ---
    elif cmd.startswith("open ") or "kholo" in cmd or "khol do" in cmd:
        name = (cmd.replace("open", "").replace("kholo", "")
                   .replace("khol do", "").strip())
        key = next((k for k in SITES if k in name), None)
        if key:
            webbrowser.open(SITES[key])
            last_site["name"] = key
            speak(f"{key} khol diya.")
            time.sleep(4)                    # page load hone do
        else:
            last_site["name"] = None
            open_app(name)
            time.sleep(2)

    elif cmd.startswith("play ") or "chalao" in cmd:
        import pywhatkit
        song = cmd.replace("youtube par", "").replace("chalao", "").replace("play", "").strip()
        speak(f"{song} chala raha hoon.")
        pywhatkit.playonyt(song)
    elif "search" in cmd:
        q = cmd.replace("google par", "").replace("search karo", "").replace("search", "").strip()
        webbrowser.open(f"https://www.google.com/search?q={q}")
        speak(f"{q} search kar diya.")
    elif "install" in cmd or "download" in cmd:
        name = (cmd.replace("install karo", "").replace("install", "")
                   .replace("download karo", "").replace("download", "").strip())
        install_app(name)
    elif "time" in cmd or "samay" in cmd or "baje" in cmd:
        speak(datetime.datetime.now().strftime("Abhi %I:%M %p ho raha hai."))
    elif "screenshot" in cmd:
        pyautogui.screenshot().save("screenshot.png")
        speak("Screenshot le liya.")
    elif "volume badhao" in cmd or "volume up" in cmd:
        for _ in range(5):
            pyautogui.press("volumeup")
    elif "volume kam" in cmd or "volume down" in cmd:
        for _ in range(5):
            pyautogui.press("volumedown")
    elif "mute" in cmd:
        pyautogui.press("volumemute")
    else:
        speak(ask_ai(cmd))


def handle(cmd):
    """'open chrome and open youtube and type masoom sharma song' jaise lambe order bhi chalte hain."""
    last_site["name"] = None
    steps = [x.strip() for x in re.split(r"\b(?:and then|and|aur phir|aur|phir|fir|then)\b", cmd) if x.strip()]
    for step in steps:
        run_step(step)


def voice_loop():
    speak(time_greeting())
    while True:
        heard = listen(timeout=5, phrase_limit=8)
        if WAKE_WORD in heard:
            cmd = heard.replace(WAKE_WORD, "").strip()
            if not cmd:
                speak(time_greeting())          # sirf "Jarvis" bola -> time wali wish
                state["mode"], state["text"] = "listening", "Listening..."
                cmd = listen()
            if cmd:
                handle(cmd)


# ---------------- 3D ROTATING GLOBE ----------------
W, H = 520, 640
CX, CY, R = W // 2, 270, 170
BG = "#02060d"


def build_globe():
    """Latitude + longitude lines + random 'city light' dots, sab 3D points."""
    lines = []
    seg = 28
    for lat in range(-75, 90, 15):                       # latitude circles
        la = math.radians(lat)
        pts = [(math.cos(la) * math.cos(2 * math.pi * i / seg),
                math.sin(la),
                math.cos(la) * math.sin(2 * math.pi * i / seg)) for i in range(seg + 1)]
        lines.append(pts)
    for lon in range(0, 180, 20):                        # longitude half-circles
        lo = math.radians(lon)
        pts = []
        for i in range(seg + 1):
            la = -math.pi / 2 + math.pi * i / seg
            pts.append((math.cos(la) * math.cos(lo), math.sin(la), math.cos(la) * math.sin(lo)))
        lines.append(pts)
        pts2 = [(-x, y, -z) for x, y, z in pts]          # doosri taraf ka half
        lines.append(pts2)
    dots = []
    for _ in range(90):
        la = math.asin(random.uniform(-0.9, 0.9))
        lo = random.uniform(0, 2 * math.pi)
        dots.append((math.cos(la) * math.cos(lo), math.sin(la), math.cos(la) * math.sin(lo)))
    return lines, dots


LINES, DOTS = build_globe()
angle = 0.0
pulse = 0.0
ring_angle = 0.0
TILT = math.radians(22)


def project(p, a, scale):
    x, y, z = p
    xr = x * math.cos(a) + z * math.sin(a)               # Y-axis rotation
    zr = -x * math.sin(a) + z * math.cos(a)
    yt = y * math.cos(TILT) - zr * math.sin(TILT)        # thoda tilt
    zt = y * math.sin(TILT) + zr * math.cos(TILT)
    return CX + xr * R * scale, CY - yt * R * scale, zt


def shade(z, base):
    """Peeche ki lines dim, aage ki bright."""
    k = 0.25 + 0.75 * (z + 1) / 2
    r, g, b = base
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))


def draw(canvas):
    global angle, pulse, ring_angle
    mode = state["mode"]
    speed = {"idle": 0.012, "listening": 0.03, "speaking": 0.05}[mode]
    base = {"idle": (0, 190, 255), "listening": (0, 255, 170), "speaking": (255, 190, 40)}[mode]
    angle += speed
    ring_angle += speed * 2
    pulse += 0.25 if mode == "speaking" else 0.08
    scale = 1.0 + (0.035 * math.sin(pulse) if mode != "idle" else 0.012 * math.sin(pulse))

    canvas.delete("all")

    # glow circles
    for i, rad in enumerate((R + 38, R + 24, R + 10)):
        rr = rad * scale
        canvas.create_oval(CX - rr, CY - rr, CX + rr, CY + rr,
                           outline=shade(-0.4 + i * 0.3, base), width=1)

    # rotating outer arc ring
    ro = (R + 55) * scale
    for k in range(6):
        canvas.create_arc(CX - ro, CY - ro, CX + ro, CY + ro,
                          start=math.degrees(ring_angle) + k * 60, extent=35,
                          style="arc", outline=shade(0.8, base), width=3)

    # globe lines
    for pts in LINES:
        prev = None
        for p in pts:
            cur = project(p, angle, scale)
            if prev:
                zavg = (prev[2] + cur[2]) / 2
                canvas.create_line(prev[0], prev[1], cur[0], cur[1],
                                   fill=shade(zavg, base), width=2 if zavg > 0 else 1)
            prev = cur

    # glowing dots on front side
    for p in DOTS:
        x, y, z = project(p, angle, scale)
        if z > 0:
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#ffffff", outline="")

    # texts
    canvas.create_text(CX, 520, text="J.A.R.V.I.S", fill=shade(1, base),
                       font=("Consolas", 30, "bold"))
    canvas.create_text(CX, 560, text=mode.upper(), fill=shade(0.6, base),
                       font=("Consolas", 12))
    canvas.create_text(CX, 595, text=state["text"], fill="#9fb4c7",
                       font=("Segoe UI", 11), width=W - 60)

    canvas.after(33, draw, canvas)


def main():
    root = tk.Tk()
    root.title("JARVIS")
    root.geometry(f"{W}x{H}")
    root.configure(bg=BG)
    root.resizable(False, False)
    canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
    canvas.pack()
    threading.Thread(target=voice_loop, daemon=True).start()
    draw(canvas)
    root.mainloop()
    os._exit(0)


if __name__ == "__main__":
    main()
