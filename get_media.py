import sys
import requests
import re
import youtube_dl
import os
# import musicbrainzngs as mb
import coverpy
import subprocess

# Audio
#######

def get_audio(track): 
    ydl_opts = {"outtmpl": r"temp_audio.%(ext)s",
                "quiet": True,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320"
                }]}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch:{track}"])

    subprocess.run(["sox", "temp_audio.mp3", os.path.join("tracks", f"{track}.mp3"), "silence", "1", "0.1", "1%"])
    os.remove("temp_audio.mp3")

# Pochette
##########

def get_cover(track):
    temp_cover_file = "temp_cover.jpg"

    # mb.set_useragent("Simon Junod - Cover images for blind tests", version=0.1)
    # works = mb.search_works(track)
    # work = works["work-list"][0]
    # performances = work["recording-relation-list"]
    # performance = performances[0]
    # recording = performance["recording"]
    # releases = mb.browse_releases(recording=recording["id"])
    # release = releases["release-list"][0]
    # cover_data = mb.get_image_front(release["id"])

    # with open(temp_cover_file, "wb") as f:
    #     f.write(cover_data)

    # os.rename(temp_cover_file, os.path.join("covers", f"{track}.jpg"))

    cp = coverpy.CoverPy()
    cover = cp.get_cover(track)
    cover_url = cover.artwork(800)

    response = requests.get(cover_url)
    if response.status_code == 200:
        with open(temp_cover_file, "wb") as f:
            f.write(response.content)

    os.rename(temp_cover_file, os.path.join("covers", f"{track}.jpg"))

if __name__ == "__main__":
    playlist = sys.argv[1]

    with open(playlist, "r") as f:
        tracks = f.read().splitlines()

    for track in tracks:

        print(f"Démarre '{track}'...")

        if not os.path.isfile(os.path.join("tracks", f"{track}.mp3")):
            get_audio(track)
        else:
            print(f"Le fichier audio existe déjà, ignore.")

        if not os.path.isfile(os.path.join("covers", f"{track}.jpg")):
            get_cover(track)
        else:
            print(f"La pochette existe déjà, ignore.")