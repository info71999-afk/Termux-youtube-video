# ==============================================================================
# ARAKAN 24/7 BACKGROUND WAKE-LOCK & INSTANT TELEGRAM RENDER DAEMON
# ==============================================================================

TELEGRAM_BOT_TOKEN = "8809267828:AAGteEuxvC2-AKZB9X6-13c8WT4u3VqhmMU"  
TELEGRAM_CHAT_ID   = "8821661107"          

import os
import sys
import subprocess
import time
import requests

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
C = "\033[96m"
W = "\033[0m"

def acquire_wakelock():
    """ Keeps Termux/Android awake so the renderer never sleeps or pauses in background """
    print(f"{C}[*] acquiring Android wakelock to prevent sleep mode...{W}")
    try:
        subprocess.run(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{G}[+] wakelock active. background execution secured 24/7.{W}")
    except Exception as e:
        print(f"{Y}[!] note: termux-api not installed. run 'pkg install termux-api' if background sleep occurs.{W}")

def check_dependencies():
    try:
        import yt_dlp
        import deep_translator
    except ImportError:
        print(f"{Y}[*] installing required modules...{W}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "deep-translator", "requests", "ffmpeg"])

def translate_vtt_to_myanmar(vtt_path):
    from deep_translator import GoogleTranslator
    if not os.path.exists(vtt_path):
        return None

    with open(vtt_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.split('\n')
    translated_lines = []
    batch = []
    translator = GoogleTranslator(source='en', target='my')

    for line in lines:
        if '-->' in line or line.strip().isdigit() or not line.strip() or line.startswith('WEBVTT') or 'NOTE' in line:
            if batch:
                try:
                    text_to_translate = " \n ".join(batch)
                    res = translator.translate(text_to_translate)
                    if res:
                        translated_lines.extend(res.split(' \n '))
                    else:
                        translated_lines.extend(batch)
                except:
                    translated_lines.extend(batch)
                batch = []
            translated_lines.append(line)
        else:
            batch.append(line.strip())

    if batch:
        try:
            text_to_translate = " \n ".join(batch)
            res = translator.translate(text_to_translate)
            if res:
                translated_lines.extend(res.split(' \n '))
            else:
                translated_lines.extend(batch)
        except:
            translated_lines.extend(batch)

    translated_content = "\n".join(translated_lines)
    my_vtt_path = vtt_path.replace('.en.', '.my.')
    with open(my_vtt_path, 'w', encoding='utf-8') as f:
        f.write(translated_content)
    return my_vtt_path

def process_and_send(url):
    import yt_dlp
    output_dir = "/sdcard/Download" if os.path.exists("/sdcard/Download") else "."
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'noplaylist': True,
    }

    print(f"\n{C}[*] processing incoming task -> {url}{W}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            video_file = base + ".mp4"

        target_vtt = None
        for ext in ['.en.vtt', '.en.srt']:
            if os.path.exists(base + ext):
                target_vtt = base + ext
                break

        final_output = video_file
        if target_vtt:
            my_vtt = translate_vtt_to_myanmar(target_vtt)
            if my_vtt and os.path.exists(my_vtt):
                print(f"{G}[+] rendering Myanmar subtitles into video...{W}")
                rendered_file = base + "_arakan_sub.mp4"
                cmd = ['ffmpeg', '-y', '-i', video_file, '-vf', f"subtitles={my_vtt}", '-c:v', 'libx264', '-crf', '20', '-c:a', 'copy', rendered_file]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(rendered_file):
                    final_output = rendered_file

        # Dispatch straight to Telegram
        if TELEGRAM_BOT_TOKEN and "YOUR_BOTFATHER" not in TELEGRAM_BOT_TOKEN:
            print(f"{C}[*] uploading rendered file to Telegram...{W}")
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            with open(final_output, 'rb') as f:
                requests.post(tg_url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': '🔥 Arakan 24/7 Rendered Video (Myanmar Subs)'}, files={'document': f})
            print(f"{G}[+] successfully dispatched to Telegram!{W}")

    except Exception as e:
        print(f"{R}[-] task error: {e}{W}")

def telegram_listener_daemon():
    """ Polls Telegram continuously 24/7 so whenever you send a YouTube link to your bot, it auto-downloads, renders, and sends back. """
    if not TELEGRAM_BOT_TOKEN or "YOUR_BOTFATHER" in TELEGRAM_BOT_TOKEN:
        print(f"{R}[-] Telegram token missing. Running in interactive terminal mode instead.{W}")
        return

    print(f"{G}[+] 24/7 Telegram Daemon active! Send any YouTube link directly to your bot on Telegram.{W}")
    offset = 0
    while True:
        try:
            res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30", timeout=35)
            if res.status_code == 200:
                data = res.json()
                for result in data.get('result', []):
                    offset = result['update_id'] + 1
                    message = result.get('message', {})
                    text = message.get('text', '').strip()
                    chat_id = str(message.get('chat', {}).get('id', ''))
                    
                    if text.startswith('http') and ('youtube.com' in text or 'youtu.be' in text):
                        print(f"{C}[*] received link from telegram: {text}{W}")
                        process_and_send(text)
        except Exception as e:
            time.sleep(5)
        time.sleep(1)

def main():
    check_dependencies()
    acquire_wakelock()
    
    # Check if running in background daemon mode or manual prompt
    if len(sys.argv) > 1:
        process_and_send(sys.argv[1])
    else:
        # Start 24/7 Telegram listener daemon
        telegram_listener_daemon()

if __name__ == "__main__":
    main()