import click
import coverpy
import os
import pyglet as pg
import random
import re
import requests
import subprocess
import sys
import youtube_dl
from decimal import Decimal

# Constantes
############

CONTROL_WINDOW_FONT = "monospace"
DISPLAY_WINDOW_FONT = "Kenyan Coffee"
CONTROL_WINDOW_FONT_SIZE = 18
DISPLAY_WINDOW_FONT_SIZE = 80

STEP_IDLE = 0
STEP_PLAYING = 1
STEP_ANSWERING = 2
STEP_REVEALED = 3

RETRY_MODE_STRICT = 0
RETRY_MODE_ALTERNATING = 1
RETRY_MODE_TIMER = 2

CONTROL_WINDOW_WIDTH = 800
CONTROL_WINDOW_HEIGHT = 600
CONTROL_WINDOW_PADDING = 20
TRACKS_CENTER = CONTROL_WINDOW_HEIGHT - 100
TIMER_BAR_WIDTH = 200
TIMER_BAR_HEIGHT = 20
DISPLAY_WINDOW_WIDTH = 1200
DISPLAY_WINDOW_HEIGHT = 900

BUZZER_FX = "buzzer2.wav"
SUCCESS_FX = "success4.wav"
NEUTRAL_IMAGE = "thinking2.png"
BACKGROUND_IMAGE = "background1.png"

DEFAULT_FADEOUT_FACTOR = 0.8
DEFAULT_ANSWER_TIMER_DURATION = 3
DEFAULT_RETRY_MODE = RETRY_MODE_STRICT
DEFAULT_RETRY_TIMER_DURATION = 5

NUMBER_KEYS = (pg.window.key._1, pg.window.key._2, pg.window.key._3, pg.window.key._4, pg.window.key._5,
              pg.window.key._6, pg.window.key._7, pg.window.key._8, pg.window.key._9)

# Callbacks
###########

def make_quieter(dt):
    global player
    global artist_revealed
    global title_revealed
    global artist_found_by
    global title_found_by
    global step

    if player.volume > 0.01:
        player.volume *= chosen_fadeout_factor
        return

    player.pause()
    player = None
    step = STEP_IDLE
    pg.clock.unschedule(make_quieter)
    for team in teams:
        teams[team].can_buzz = True
    artist_revealed = False
    title_revealed = False
    artist_found_by = None
    title_found_by = None
    reset_answer_timer()

def reduce_answer_timer(dt):
    global timer

    unit = dt / chosen_answer_timer_duration

    if timer > unit:
        timer -= unit
        return

    timer = 0

    pg.clock.unschedule(reduce_answer_timer)

def restore_buzzer(dt, team):
    print(f"{team.name} peut de nouveau buzzer")
    team.can_buzz = True

# Fonctions utilitaires
#######################

def open_joystick():
    global joystick
    joysticks = pg.input.get_joysticks()
    if not joysticks:
        print("Aucun joystick connecté")
        sys.exit()
    joystick = joysticks[0]
    joystick.open()

def reset_answer_timer():
    global timer
    global timer_running
    timer = 1
    timer_running = False
    pg.clock.unschedule(reduce_answer_timer)

def reset_turn():
    pg.clock.schedule_interval(make_quieter, 0.1)

def download_audio(track): 
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

    subprocess.run(["sox", 
                    "temp_audio.mp3",
                    os.path.join("tracks", f"{track}.mp3"),
                    "silence",
                    "1",
                    "0.1",
                    "1%"])

    os.remove("temp_audio.mp3")

def download_cover(track):
    temp_cover_file = "temp_cover.jpg"

    cp = coverpy.CoverPy()
    cover = cp.get_cover(track)
    cover_url = cover.artwork(800)

    response = requests.get(cover_url)
    if response.status_code == 200:
        with open(temp_cover_file, "wb") as f:
            f.write(response.content)

    os.rename(temp_cover_file, os.path.join("covers", f"{track}.jpg"))

# Classes de fenêtres
#####################

class ButtonCheckWindow(pg.window.Window):
    def __init__(self):
        super(ButtonCheckWindow, self).__init__(400, 100, caption="Blind - Test des boutons")

        self.button_labels = []
        for i in range(10):
            self.button_labels.append(pg.text.Label(str(i),
                                                    font_name=CONTROL_WINDOW_FONT,
                                                    font_size=36,
                                                    x=i*30,
                                                    y=self.height//2,
                                                    anchor_x="left",
                                                    anchor_y="center"))

    def on_draw(self):
        self.clear()
        for button_label in self.button_labels:
            button_label.draw()

class ControlWindow(pg.window.Window):
    def __init__(self):
        super(ControlWindow, self).__init__(CONTROL_WINDOW_WIDTH,
                                            CONTROL_WINDOW_HEIGHT,
                                            caption="Blind - Contrôleur")

        self.previous_artist_label = pg.text.Label("Artiste",
                                                   font_name=CONTROL_WINDOW_FONT,
                                                   font_size=CONTROL_WINDOW_FONT_SIZE,
                                                   x=self.width//2,
                                                   y=TRACKS_CENTER+55,
                                                   anchor_x="center",
                                                   anchor_y="center",
                                                   color=(100, 100, 100, 255))
        self.previous_title_label = pg.text.Label("Titre",
                                                  font_name=CONTROL_WINDOW_FONT,
                                                  font_size=CONTROL_WINDOW_FONT_SIZE,
                                                  x=self.width//2,
                                                  y=TRACKS_CENTER+35,
                                                  anchor_x="center",
                                                  anchor_y="center",
                                                  color=(100, 100, 100, 255))
        self.current_artist_label = pg.text.Label("Artiste",
                                                  font_name=CONTROL_WINDOW_FONT,
                                                  font_size=CONTROL_WINDOW_FONT_SIZE,
                                                  x=self.width//2,
                                                  y=TRACKS_CENTER+10,
                                                  anchor_x="center",
                                                  anchor_y="center")
        self.current_title_label = pg.text.Label("Titre",
                                                 font_name=CONTROL_WINDOW_FONT,
                                                 font_size=CONTROL_WINDOW_FONT_SIZE,
                                                 x=self.width//2,
                                                 y=TRACKS_CENTER-10,
                                                 anchor_x="center",
                                                 anchor_y="center")
        self.next_artist_label = pg.text.Label("Artiste",
                                               font_name=CONTROL_WINDOW_FONT,
                                               font_size=CONTROL_WINDOW_FONT_SIZE,
                                               x=self.width//2,
                                               y=TRACKS_CENTER-35,
                                               anchor_x="center",
                                               anchor_y="center",
                                               color=(100, 100, 100, 255))
        self.next_title_label = pg.text.Label("Titre",
                                              font_name=CONTROL_WINDOW_FONT,
                                              font_size=CONTROL_WINDOW_FONT_SIZE,
                                              x=self.width//2,
                                              y=TRACKS_CENTER-55,
                                              anchor_x="center",
                                              anchor_y="center",
                                              color=(100, 100, 100, 255))
        self.track_number_label = pg.text.Label("Numéro",
                                                font_name=CONTROL_WINDOW_FONT,
                                                font_size=CONTROL_WINDOW_FONT_SIZE,
                                                x=CONTROL_WINDOW_PADDING,
                                                y=CONTROL_WINDOW_HEIGHT-CONTROL_WINDOW_PADDING,
                                                anchor_x="left",
                                                anchor_y="top")
        self.pitch_label = pg.text.Label("Pitch",
                                         font_name=CONTROL_WINDOW_FONT,
                                         font_size=CONTROL_WINDOW_FONT_SIZE,
                                         x=CONTROL_WINDOW_PADDING,
                                         y=CONTROL_WINDOW_HEIGHT-CONTROL_WINDOW_PADDING-50,
                                         anchor_x="left",
                                         anchor_y="top")
        self.seek_label = pg.text.Label("Seek",
                                        font_name=CONTROL_WINDOW_FONT,
                                        font_size=CONTROL_WINDOW_FONT_SIZE,
                                        x=CONTROL_WINDOW_PADDING,
                                        y=CONTROL_WINDOW_HEIGHT-CONTROL_WINDOW_PADDING-100,
                                        anchor_x="left",
                                        anchor_y="top")
        self.step_label = pg.text.Label("Etape",
                                        font_name=CONTROL_WINDOW_FONT,
                                        font_size=CONTROL_WINDOW_FONT_SIZE,
                                        x=CONTROL_WINDOW_PADDING,
                                        y=CONTROL_WINDOW_PADDING,
                                        anchor_x="left",
                                        anchor_y="bottom")
        self.scores_label = pg.text.Label("Scores",
                                          font_name=CONTROL_WINDOW_FONT,
                                          font_size=CONTROL_WINDOW_FONT_SIZE,
                                          multiline=True,
                                          width=CONTROL_WINDOW_WIDTH-(2*CONTROL_WINDOW_PADDING),
                                          align="right",
                                          x=CONTROL_WINDOW_WIDTH-CONTROL_WINDOW_PADDING,
                                          y=CONTROL_WINDOW_PADDING,
                                          anchor_x="right",
                                          anchor_y="bottom") 

        self.timer_outline = pg.shapes.Rectangle(CONTROL_WINDOW_WIDTH-TIMER_BAR_WIDTH-CONTROL_WINDOW_PADDING-4,
                                                 CONTROL_WINDOW_HEIGHT-TIMER_BAR_HEIGHT-CONTROL_WINDOW_PADDING-4,
                                                 TIMER_BAR_WIDTH+4,
                                                 TIMER_BAR_HEIGHT+4,
                                                 color=(255, 255, 255))
        self.timer_inside = pg.shapes.Rectangle(CONTROL_WINDOW_WIDTH-TIMER_BAR_WIDTH-CONTROL_WINDOW_PADDING-3,
                                                CONTROL_WINDOW_HEIGHT-TIMER_BAR_HEIGHT-CONTROL_WINDOW_PADDING-3,
                                                TIMER_BAR_WIDTH+2,
                                                TIMER_BAR_HEIGHT+2,
                                                color=(0, 0, 0))
        self.timer_bar = pg.shapes.Rectangle(CONTROL_WINDOW_WIDTH-TIMER_BAR_WIDTH-CONTROL_WINDOW_PADDING-2,
                                             CONTROL_WINDOW_HEIGHT-TIMER_BAR_HEIGHT-CONTROL_WINDOW_PADDING-2,
                                             TIMER_BAR_WIDTH,
                                             TIMER_BAR_HEIGHT,
                                             color=(255, 255, 255))

    def on_draw(self):
        global step
        global player
        global timer_running

        self.clear()

        if track_number > 0:
            self.previous_artist_label.text = tracks[track_number-1].artist
            self.previous_title_label.text = tracks[track_number-1].title
        else:
            self.previous_artist_label.text = "---"
            self.previous_title_label.text = "---"            

        self.current_artist_label.text = tracks[track_number].artist
        self.current_title_label.text = tracks[track_number].title

        if track_number < len(tracks)-1:
            self.next_artist_label.text = tracks[track_number+1].artist
            self.next_title_label.text = tracks[track_number+1].title
        else:
            self.next_artist_label.text = "---"
            self.next_title_label.text = "---"

        self.track_number_label.text = f"{track_number+1}/{len(tracks)}"
        self.pitch_label.text = f"Pitch : {pitch}"
        if player:
            elapsed_seconds = int(player.time)
            elapsed_minsec = f"{(elapsed_seconds // 60):02}:{(elapsed_seconds % 60):02}"
            total_seconds = int(tracks[track_number].media.duration)
            total_minsec = f"{(total_seconds // 60):02}:{(total_seconds % 60):02}"
            self.seek_label.text = f"{elapsed_minsec:} / {total_minsec}"
        else:
            self.seek_label.text = "- / -"

        self.step_label.text = ("Prêt", "Lecture", "Réponse", "Révélation")[step]
        
        if step == STEP_ANSWERING:
            self.step_label.text += f" ({last_team_to_buzz.name})"
            if not timer_running:
                timer_running = True
                pg.clock.schedule_interval(reduce_answer_timer, 0.01)

        self.timer_bar.width = timer * TIMER_BAR_WIDTH

        if artist_revealed:
            self.current_artist_label.color = (0, 255, 0, 255)
        else:
            self.current_artist_label.color = (255, 255, 255, 255)
        
        if title_revealed:
            self.current_title_label.color = (0, 255, 0, 255)
        else:
            self.current_title_label.color = (255, 255, 255, 255)

        if title_revealed and artist_revealed and step == STEP_ANSWERING: # Dernier test : nécessaire pour n'exécuter
                                                                          # qu'une fois
            step = STEP_REVEALED
            if chosen_pause_during_answers:
                player.play()
            else:
                player.volume = 1
            # pg.clock.unschedule(reduce_answer_timer) # Décommenter pour mettre le timer en pause lorsque tout trouvé

        scores_string = ""
        for team in sorted(teams.values(), key=lambda x:x.score, reverse=True):
            scores_string += f"{team.name} ({team.number}) : {str(team.score).rjust(3)}\n"
        scores_string = scores_string.strip()
        self.scores_label.text = scores_string

        self.previous_artist_label.draw()
        self.previous_title_label.draw()
        self.current_artist_label.draw()
        self.current_title_label.draw()
        self.next_artist_label.draw()
        self.next_title_label.draw()
        self.track_number_label.draw()
        self.pitch_label.draw()
        self.seek_label.draw()
        self.step_label.draw()
        self.scores_label.draw()
        self.timer_outline.draw()
        self.timer_inside.draw()
        self.timer_bar.draw()

    def on_activate(self):
        self.dispatch_event("on_draw")

    def on_expose(self):
        self.dispatch_event("on_draw")

    def on_key_press(self, symbol, modifiers):
        global step
        global track_number
        global player
        global artist_revealed
        global title_revealed
        global artist_found_by
        global title_found_by
        global pitch
        global leaderboard_visible

        if symbol == pg.window.key.ENTER:
            if step == STEP_IDLE:
                step = STEP_PLAYING
                player = tracks[track_number].media.play()
                player.pitch = float(pitch)
                if modifiers == 2: # ctrl appuyé : seek au hasard dans la piste
                    random_point = random.uniform(0.2, 0.8) # ni trop au début, ni trop à la fin
                    random_second = tracks[track_number].media.duration * random_point
                    player.seek(random_second)

            elif step == STEP_PLAYING:
                if modifiers == 2: # ctrl appuyé : repasse en mode idle, sans révéler
                    reset_turn()
                else: # sinon : révèle
                    step = STEP_REVEALED
                    artist_revealed = True
                    title_revealed = True
            elif step == STEP_ANSWERING:
                step = STEP_PLAYING
                if chosen_pause_during_answers:
                    player.play()
                else:
                    player.volume = 1
                if chosen_retry_mode == RETRY_MODE_TIMER:
                    pg.clock.schedule_once(restore_buzzer, chosen_retry_timer_duration, team=last_team_to_buzz)
                reset_answer_timer()
            elif step == STEP_REVEALED:
                reset_turn()

        elif symbol == pg.window.key.T and step == STEP_ANSWERING and not title_revealed:
            last_team_to_buzz.score += 1
            title_revealed = True
            title_found_by = last_team_to_buzz
            success_fx.play()
        elif symbol == pg.window.key.A and step == STEP_ANSWERING and not artist_revealed:
            last_team_to_buzz.score += 1
            artist_revealed = True
            artist_found_by = last_team_to_buzz
            success_fx.play()
        elif symbol == pg.window.key.L:
            leaderboard_visible = not leaderboard_visible
            display_window.dispatch_event("on_draw")
        elif symbol in NUMBER_KEYS:
            number = NUMBER_KEYS.index(symbol) + 1
            try:
                team = next(team for team in teams.values() if team.number == number)
                if modifiers == 2:
                    team.score -= 1
                else:
                    team.score += 1
            except StopIteration:
                pass

    def on_text(self, text):
        global pitch
        if text == ".":
            pitch += Decimal("0.1")
            if player:
                player.pitch = float(pitch)
        elif text == ",":
            if pitch <= 0.1:
                return
            pitch -= Decimal("0.1")
            if player:
                player.pitch = float(pitch)

    def on_text_motion(self, motion):
        global track_number
        if motion == pg.window.key.MOTION_UP and step == STEP_IDLE and track_number > 0:
            track_number -= 1
        elif motion == pg.window.key.MOTION_DOWN and step == STEP_IDLE and track_number < len(tracks)-1:
            track_number += 1
        elif motion == pg.window.key.MOTION_RIGHT and player:
            player.seek(player.time + 1)
        elif motion == pg.window.key.MOTION_LEFT and player:
            player.seek(player.time - 1)

class DisplayWindow(pg.window.Window):
    def __init__(self):
        super(DisplayWindow, self).__init__(DISPLAY_WINDOW_WIDTH,
                                            DISPLAY_WINDOW_HEIGHT,
                                            resizable=True,
                                            caption="Blind - Afficheur")
        self.set_location(50,50)
        self.background = background_image
        self.current_artist_label = pg.text.Label("Artiste",
                                                  font_name=DISPLAY_WINDOW_FONT,
                                                  font_size=0,
                                                  x=0,
                                                  y=0,
                                                  anchor_x="left",
                                                  anchor_y="bottom",
                                                  color=(0,0,0,255))
        self.current_title_label = pg.text.Label("Titre",
                                                 font_name=DISPLAY_WINDOW_FONT,
                                                 font_size=0,
                                                 x=0,
                                                 y=0,
                                                 anchor_x="left",
                                                 anchor_y="bottom",
                                                 color=(0,0,0,255))
        self.artist_found_by_label = pg.text.Label("",
                                                   font_name=DISPLAY_WINDOW_FONT,
                                                   font_size=0,
                                                   x=0,
                                                   y=0,
                                                   anchor_x="left",
                                                   anchor_y="bottom",
                                                   color=(0,100,0,255))
        self.title_found_by_label = pg.text.Label("",
                                                  font_name=DISPLAY_WINDOW_FONT,
                                                  font_size=0,
                                                  x=0,
                                                  y=0,
                                                  anchor_x="left",
                                                  anchor_y="bottom",
                                                  color=(0,100,0,255))
        self.timer_bar = pg.shapes.Rectangle(0, 0, 0, 0, color=(0,0,0))

        self.leaderboard_label = pg.text.Label("Leaderboard",
                                               font_name=DISPLAY_WINDOW_FONT,
                                               font_size=0,
                                               x=0,
                                               y=0,
                                               multiline=True,
                                               width=100,
                                               align="center",
                                               anchor_x="center",
                                               anchor_y="center",
                                               color=(0,0,0,255))

    def on_draw(self):
        self.clear()
        #self.background.draw()
        self.background.blit(0,0,1)

        if step == STEP_REVEALED:
            image = tracks[track_number].cover
        else:
            image = neutral_image
        image.width = self.height*0.7
        image.height = image.width
        image.anchor_x = image.width//2
        image.anchor_y = image.height//2
        image.x = self.width//2 # placé dans `image` artificiellement, utile pour dessiner la barre de timer
        image.y = self.height*0.6

        if artist_revealed:
            self.current_artist_label.text = tracks[track_number].artist
            self.current_artist_label.color = (0,0,0,255)
        else:
            self.current_artist_label.text = "Artiste ?"
            self.current_artist_label.color = (100,100,100,255)

        if title_revealed:
            self.current_title_label.text = tracks[track_number].title
            self.current_title_label.color = (0,0,0,255)
        else:
            self.current_title_label.text = "Titre ?"
            self.current_title_label.color = (100,100,100,255)

        if artist_found_by:
            self.artist_found_by_label.text = artist_found_by.name
        else:
            self.artist_found_by_label.text = ""

        if title_found_by:
            self.title_found_by_label.text = title_found_by.name
        else:
            self.title_found_by_label.text = ""

        self.current_artist_label.draw()
        self.current_title_label.draw()

        self.artist_found_by_label.x = (self.current_artist_label.x +
                                        self.current_artist_label.content_width +
                                        self.width*0.02)
        self.title_found_by_label.x = (self.current_title_label.x +
                                       self.current_title_label.content_width +
                                       self.width*0.02)
        self.artist_found_by_label.y = self.current_artist_label.y + self.height*0.02
        self.title_found_by_label.y = self.current_title_label.y + self.height*0.02
        self.artist_found_by_label.draw()
        self.title_found_by_label.draw()

        self.timer_bar.x = image.x - image.width//2 - self.width*0.05
        self.timer_bar.y = image.y - image.height//2
        self.timer_bar.width = image.width + (2*self.width*0.05)
        self.timer_bar.height = timer * image.height
        self.timer_bar.draw()

        image.blit(image.x, image.y, 1) # blit tardif, pour qu'il ait lieu par dessus la barre de timer

        if leaderboard_visible:
            # rect = pg.shapes.Rectangle(0, 0, self.width, self.height, color=(255,0,0))
            # rect.draw()
            scores_string = ""
            for team in sorted(teams.values(), key=lambda x:x.score, reverse=True):
                scores_string += f"{team.name} : {str(team.score)}\n"
            scores_string = scores_string.strip()
            self.leaderboard_label.text = scores_string

            self.background.blit(0,0,1)
            self.leaderboard_label.draw()

    def on_resize(self, width, height):
        self.background.width, self.background.height = width, height

        self.current_artist_label.x = width*0.02
        self.current_title_label.x = width*0.02
        self.current_artist_label.y = height*0.12
        self.current_title_label.y = height*0.02
        self.current_artist_label.font_size = height//15
        self.current_title_label.font_size = height//15
        
        self.artist_found_by_label.font_size = height//30
        self.title_found_by_label.font_size = height//30

        self.leaderboard_label.x = width*0.5
        self.leaderboard_label.y = height*0.5
        self.leaderboard_label.font_size = height//15
        self.leaderboard_label.width = width*0.8

        super(DisplayWindow, self).on_resize(width, height) # https://stackoverflow.com/a/23276270/602339

    def on_activate(self):
        self.dispatch_event("on_draw")

    def on_expose(self):
        self.dispatch_event("on_draw")

    def on_key_press(self, symbol, modifiers): # empêche Esc de fermer la fenêtre
        pass

# Classes de jeu
################

class Team:
    def __init__(self, name="NAME", score=0, number=0):
        self.name = name
        self.score = score
        self.can_buzz = True
        self.number = number

class Track:
    def __init__(self, artist="ARTIST", title="TITLE", media=None, cover=None):
        self.artist = artist
        self.title = title
        self.media = media
        self.cover = cover

# Sous-commandes, options et paramètres
#######################################

@click.group()
def cli():
    pass

@cli.command()
@click.option("--playlist-file", type=click.Path(exists=True), default="playlist.txt", help="Playlist file.")
def download(playlist_file):
    """Download songs and cover pictures."""
    with open(playlist_file, "r") as f:
        tracks = f.read().splitlines()

    for track in tracks:

        print(f"Démarre '{track}'...")

        if not os.path.isfile(os.path.join("tracks", f"{track}.mp3")):
            download_audio(track)
        else:
            print(f"Le fichier audio existe déjà, ignore.")

        if not os.path.isfile(os.path.join("covers", f"{track}.jpg")):
            download_cover(track)
        else:
            print(f"La pochette existe déjà, ignore.")

@cli.command()
def check():
    """Discover what button triggers what code, visually."""
    global joystick
    open_joystick()
    button_check_window = ButtonCheckWindow()

    @joystick.event
    def on_joybutton_press(joystick, button):
        # ici : convertir évent. le code reçu
        try:
            button_check_window.button_labels[button].color = (255, 0, 0, 255)
        except IndexError:
            pass
        button_check_window.dispatch_event("on_draw")

    @joystick.event
    def on_joybutton_release(joystick, button):
        # ici : convertir évent. le code reçu
        try:
            button_check_window.button_labels[button].color = (255, 255, 255, 255)
        except IndexError:
            pass
        button_check_window.dispatch_event("on_draw")

    pg.app.run()

@cli.command()
@click.option("--playlist-file",
              type=click.Path(exists=True),
              default="playlist.txt",
              help="Playlist file.")
@click.option("--teams-file",
              type=click.Path(exists=True),
              default="teams.txt",
              help="Teams file.")
@click.option("--answer-timer-duration",
              type=int,
              default=DEFAULT_ANSWER_TIMER_DURATION,
              help="How fast a player must answer after buzzing (in seconds).")
@click.option("--retry-mode",
              type=click.Choice(["strict", "alternating", "timer"]),
              default=("strict", "alternating", "timer")[DEFAULT_RETRY_MODE],
              help="Strict: a player can buzz once per track. Alternating: a player can buzz multiple times, "
                   "but not in a row. Timer: a player can buzz again, a few seconds after the track was resumed.")
@click.option("--retry-timer-duration",
              type=int,
              default=DEFAULT_RETRY_TIMER_DURATION,
              help="If --retry-mode is timer, the number of seconds to wait to buzz again.")
@click.option("--pause-during-answers",
              is_flag=True,
              help="Pause tracks when someone is answering. Without this flag, the volume is lowered instead.")
@click.option("--fadeout-factor",
              type=float,
              default=DEFAULT_FADEOUT_FACTOR,
              help="Between 0 and 1, higher = longer fadeout, 0 = no fadeout.")
def play(playlist_file,
         teams_file,
         answer_timer_duration,
         retry_mode,
         retry_timer_duration,
         pause_during_answers,
         fadeout_factor):
    """Play the game."""
    global joystick
    global teams 
    global tracks
    global step
    global track_number
    global player
    global artist_revealed
    global title_revealed
    global artist_found_by
    global title_found_by
    global timer
    global timer_running
    global neutral_image
    global background_image
    global success_fx
    global chosen_answer_timer_duration
    global chosen_retry_mode
    global chosen_retry_timer_duration
    global chosen_pause_during_answers
    global chosen_fadeout_factor
    global pitch
    global leaderboard_visible
    global display_window
    
    step = STEP_IDLE
    track_number = 0
    player = None
    artist_revealed = False
    title_revealed = False
    artist_found_by = None
    title_found_by = None
    timer = 1 # va de 1 à 0
    timer_running = False
    chosen_answer_timer_duration = answer_timer_duration
    chosen_retry_mode = ("strict", "alternating", "timer").index(retry_mode)
    chosen_retry_timer_duration = retry_timer_duration
    chosen_pause_during_answers = pause_during_answers
    chosen_fadeout_factor = fadeout_factor
    pitch = Decimal("1")
    leaderboard_visible = False

    open_joystick()
    teams = {}
    with open(teams_file, "r") as f:
        lines = f.read().splitlines()

    for line in lines:
        fields = line.split(":")
        team_name, team_id = fields[0], int(fields[1])
        if len(fields) == 3:
            team_score = int(fields[2])
        else:
            team_score = 0
        teams[team_id] = Team(name=team_name, score=team_score, number=len(teams)+1)

    with open(playlist_file, "r") as f:
        lines = f.read().splitlines()

    tracks = []

    for idx, line in enumerate(lines):
        track_artist, track_title = line.split(" - ")
        track_media = pg.media.load(os.path.join("tracks", f"{line}.mp3"), streaming=False)
        track_cover = pg.image.load(os.path.join("covers", f"{line}.jpg")).get_texture()
        track = Track(track_artist, track_title, track_media, track_cover)
        tracks.append(track)
        print(f"[{str(idx+1).rjust(len(str(len(lines))))}/{len(lines)}] {track_artist} - {track_title}")

    buzzer_fx = pg.media.load(os.path.join("assets", "fx", BUZZER_FX), streaming=False)
    success_fx = pg.media.load(os.path.join("assets", "fx", SUCCESS_FX), streaming=False)

    neutral_image = pg.image.load(os.path.join("assets", "images", NEUTRAL_IMAGE)).get_texture()
    background_image = pg.image.load(os.path.join("assets", "images", BACKGROUND_IMAGE)).get_texture()

    tracks[0].media.play().pause() # pour éviter un lag à la 1re piste

    control_window = ControlWindow()
    display_window = DisplayWindow()

    @joystick.event
    def on_joybutton_press(joystick, button):
        global step
        global last_team_to_buzz

        if step == STEP_PLAYING:
            try:
                team_trying_to_buzz = teams[button]
            except KeyError:
                return
            if team_trying_to_buzz.can_buzz:
                last_team_to_buzz = team_trying_to_buzz
            else:
                return
            buzzer_fx.play()
            step = STEP_ANSWERING
            if chosen_pause_during_answers:
                player.pause()
            else:
                player.volume = 0.1
            if chosen_retry_mode == RETRY_MODE_ALTERNATING:
                for team in teams:
                    teams[team].can_buzz = True
            last_team_to_buzz.can_buzz = False
    
    pg.app.run()

# Exécution principale
######################

if __name__ == "__main__":
    cli()