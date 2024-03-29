import click
import coverpy
import os
import pyglet as pg
import random
import requests
import subprocess
import sys
import youtube_dl
from decimal import Decimal
from time import time
from collections import deque

# Constantes
############

CONTROL_WINDOW_FONT = "Droid Sans Mono"
DISPLAY_WINDOW_FONT = "Kenyan Coffee"

STEP_IDLE = 0
STEP_PLAYING = 1
STEP_ANSWERING = 2

RETRY_MODE_STRICT = 0
RETRY_MODE_ALTERNATING = 1
RETRY_MODE_TIMER = 2

CONTROL_WINDOW_WIDTH = 500
CONTROL_WINDOW_HEIGHT = 900
CONTROL_WINDOW_PADDING = 20
TIMER_OUTLINE_WIDTH = CONTROL_WINDOW_WIDTH - 2*CONTROL_WINDOW_PADDING
TIMER_OUTLINE_HEIGHT = 30
TIMER_GAP_WIDTH = TIMER_OUTLINE_WIDTH - 2
TIMER_GAP_HEIGHT = TIMER_OUTLINE_HEIGHT - 2
TIMER_BAR_WIDTH = TIMER_GAP_WIDTH - 2
TIMER_BAR_HEIGHT = TIMER_GAP_HEIGHT - 2
DISPLAY_WINDOW_WIDTH = 1200
DISPLAY_WINDOW_HEIGHT = 900

BUZZER_FX = "buzzer2.wav"
SUCCESS_FX = "success4.wav"
NEUTRAL_IMAGE = "thinking2.png"
BACKGROUND_IMAGE = "background1.png"
BUZZER_IMAGE = "emergency2.png"
NOCOVER_IMAGE = "nocover.jpg"

DEFAULT_FADEOUT_FACTOR = 0.8
DEFAULT_ANSWER_TIMER_DURATION = 3
DEFAULT_RETRY_MODE = RETRY_MODE_STRICT
DEFAULT_RETRY_TIMER_DURATION = 5

NUMBER_KEYS = (pg.window.key._1, pg.window.key._2, pg.window.key._3, pg.window.key._4, pg.window.key._5,
               pg.window.key._6, pg.window.key._7, pg.window.key._8, pg.window.key._9)

COLOR_RED = "#F04E23"
COLOR_GREEN = "#A2D45E"
COLOR_BLUE = "#00A19B"
COLOR_YELLOW = "#F3BD48"
COLOR_PURPLE = "#5B315E"
COLOR_WHITE = "#FFFFFF"

ASSETS_DIR = "assets" # pyglet ne supporte pas les chemins absolus
COVERS_DIR = "covers"
TRACKS_DIR = "tracks"
FX_DIR = os.path.join(ASSETS_DIR, "fx")
GIFS_DIR = os.path.join(ASSETS_DIR, "gifs")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # utile pour créer des liens symboliques

MAX_PLAYLIST_ENTRIES = 23
PLAYLIST_BUFFER_LINES = 4

# Fonctions utilitaires

def download_audio(track=None, video_id=None):
    output_file = os.path.join(TRACKS_DIR, f"{track}.mp3")

    if not video_id:
        query = f"ytsearch:{track}"
    else:
        query = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {"outtmpl": r"temp_audio.%(ext)s",
                "quiet": True,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320"
                }]}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([query])

    print("Son téléchargé.")

    subprocess.run(["sox", 
                    "temp_audio.mp3",
                    output_file,
                    "silence",
                    "1",
                    "0.1",
                    "0.1%"])

    print("Silences supprimés.")

    os.remove("temp_audio.mp3")

def download_cover(track):
    temp_cover_file = "temp_cover.jpg"

    cp = coverpy.CoverPy()
    try:
        cover = cp.get_cover(track)
        cover_url = cover.artwork(800)
        response = requests.get(cover_url)
        if response.status_code == 200:
            with open(temp_cover_file, "wb") as f:
                f.write(response.content)

        os.rename(temp_cover_file, os.path.join(COVERS_DIR, f"{track}.jpg"))
        print("Couverture téléchargée.")
    except coverpy.exceptions.NoResultsException:
        os.symlink(os.path.join(BASE_DIR, IMAGES_DIR, NOCOVER_IMAGE), os.path.join(COVERS_DIR, f"{track}.jpg"))
        print("Couverture introuvable, lien symbolique créé vers couverture générique.")

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

        self.playlist_label = pg.text.HTMLLabel("Playlist",
                                            anchor_x="left",
                                            anchor_y="top",
                                            x=CONTROL_WINDOW_PADDING,
                                            y=CONTROL_WINDOW_HEIGHT-2*CONTROL_WINDOW_PADDING-TIMER_OUTLINE_HEIGHT,
                                            multiline=True,
                                            width=9999)

        self.info_label = pg.text.HTMLLabel("Info",
                                         anchor_x="left",
                                         anchor_y="bottom",
                                         x=CONTROL_WINDOW_PADDING,
                                         y=CONTROL_WINDOW_PADDING,
                                         multiline=True,
                                         width=9999)

        self.timer_outline = pg.shapes.Rectangle(CONTROL_WINDOW_PADDING,
                                                 CONTROL_WINDOW_HEIGHT-TIMER_OUTLINE_HEIGHT-CONTROL_WINDOW_PADDING,
                                                 TIMER_OUTLINE_WIDTH,
                                                 TIMER_OUTLINE_HEIGHT,
                                                 color=(255, 255, 255))
        self.timer_gap = pg.shapes.Rectangle(CONTROL_WINDOW_PADDING+1,
                                                CONTROL_WINDOW_HEIGHT-TIMER_OUTLINE_HEIGHT-CONTROL_WINDOW_PADDING+1,
                                                TIMER_GAP_WIDTH,
                                                TIMER_GAP_HEIGHT,
                                                color=(0, 0, 0))
        self.timer_bar = pg.shapes.Rectangle(CONTROL_WINDOW_PADDING+2,
                                             CONTROL_WINDOW_HEIGHT-TIMER_OUTLINE_HEIGHT-CONTROL_WINDOW_PADDING+2,
                                             TIMER_BAR_WIDTH,
                                             TIMER_BAR_HEIGHT,
                                             color=(255, 255, 255))
        self.success_fx = pg.media.load(os.path.join(FX_DIR, SUCCESS_FX), streaming=False)

    def on_draw(self):
        self.clear()

        playlist_label_string = ""

        bottom_track = MAX_PLAYLIST_ENTRIES-1+state.playlist_scroll
        top_track = state.playlist_scroll
        scroll = state.playlist_scroll
        if state.track_number > bottom_track - PLAYLIST_BUFFER_LINES and scroll < len(state.tracks) - MAX_PLAYLIST_ENTRIES:
            state.playlist_scroll += 1
        if state.track_number < top_track + PLAYLIST_BUFFER_LINES and scroll > 0:
            state.playlist_scroll -= 1

        for i in range(MAX_PLAYLIST_ENTRIES):
            try:
                track = state.tracks[i + state.playlist_scroll]
            except IndexError:
                break

            if track == state.selected_track:
                if state.player:
                    color = COLOR_GREEN
                else:
                    color = COLOR_YELLOW
            else:
                color = COLOR_WHITE

            if track.artist_revealed and track.artist_found_by:
                mark_artist = str(track.artist_found_by.number)
            elif track.artist_revealed:
                mark_artist = "-"
            else:
                mark_artist = " "
            if track.title_revealed and track.title_found_by:
                mark_title = str(track.title_found_by.number)
            elif track.title_revealed:
                mark_title = "-"
            else:
                mark_title = " "
            line = f"{track.artist} - {track.title}"
            if len(line) > 39:
                if track != state.selected_track:
                    line = line[:38]+"\u2026"
                else:
                    line = "\u2026"+line[-38:]
            line = f"[{mark_artist}][{mark_title}] {line}"
            line = f"<font color='{color}'>{line}</font>"
            playlist_label_string += f"{line}<br>"

        self.playlist_label.text = f"<font face='{CONTROL_WINDOW_FONT}'>{playlist_label_string}</font>"

        info_label_string = ""

        info_label_string += f"{state.selected_track.artist}\n"
        info_label_string += f"{state.selected_track.title}\n"
        info_label_string += "\n"

        max_name_length = max(len(f"{team.name} ({team.number})") for team in state.teams)
        for team in state.teams:
            if team.can_buzz:
                color = COLOR_WHITE
            else:
                color = COLOR_RED
            name_length = len(f"{team.name} ({team.number})")
            info_label_string += f"<font color='{color}'>{team.name} ({team.number}){' '*(max_name_length-name_length)} : {team.score}</font><br>"

        info_label_string += "<br>"

        info_label_string += f"Piste : {state.track_number+1}/{len(state.tracks)}<br>"
        info_label_string += f"Pitch : {state.pitch}<br>"
        if state.player:
            elapsed_seconds = int(state.player.time)
            elapsed_minsec = f"{(elapsed_seconds // 60):02}:{(elapsed_seconds % 60):02}"
            total_seconds = int(state.selected_track.media.duration)
            total_minsec = f"{(total_seconds // 60):02}:{(total_seconds % 60):02}"
            info_label_string += f"Position : {elapsed_minsec:} / {total_minsec}<br>"
        else:
            info_label_string += "Position : - / -<br>"

        if state.gifs:
            info_label_string += f"GIF : {state.gifs[0]['name']} ({'visible' if state.gif_visible else 'caché'})<br>"
        else:
            info_label_string += "GIF : aucun<br>"

        info_label_string += (f"<font color='{COLOR_YELLOW}'>Prêt</font>",
                              f"<font color='{COLOR_GREEN}'>Lecture</font>",
                              f"<font color='{COLOR_RED}'>Réponse</font>")[state.step]
        
        if state.step == STEP_ANSWERING:
            info_label_string += f" ({state.last_team_to_buzz.name})"
            # aucun rapport avec le label d'infos :
            if not state.timer_running: # pour éviter que le schedule_interval crée plusieurs intervalles.
                                        # Note : pas possible de se baser sur timer, car il est réduit dans
                                        # le callback, or le callback n'est pas appelé à t=0, mais à t=0.01,
                                        # donc dans l'intervalle on_draw() peut s'exécuter plusieurs fois.
                state.timer_running = True
                pg.clock.schedule_interval(state.reduce_answer_timer, 0.01)

        self.info_label.text = f"<pre><font color='{COLOR_WHITE}' face='{CONTROL_WINDOW_FONT}'>{info_label_string}</font></pre>"

        self.timer_bar.width = state.timer * TIMER_BAR_WIDTH

        if state.selected_track.title_revealed and state.selected_track.artist_revealed and state.step == STEP_ANSWERING:
            state.step = STEP_PLAYING
            state.toggle_pause()

        self.playlist_label.draw()
        self.info_label.draw()
        self.timer_outline.draw()
        self.timer_gap.draw()
        self.timer_bar.draw()

    def on_activate(self):
        self.dispatch_event("on_draw")

    def on_expose(self):
        self.dispatch_event("on_draw")

    def on_key_press(self, symbol, modifiers):
        if symbol == pg.window.key.ENTER:
            if not state.player:
                state.step = STEP_PLAYING
                state.player = state.selected_track.media.play()
                state.player.pitch = float(state.pitch)
                if modifiers & pg.window.key.MOD_CTRL: # ctrl appuyé : seek au hasard dans la piste
                    random_point = random.uniform(0.2, 0.8) # ni trop au début, ni trop à la fin
                    random_second = state.selected_track.media.duration * random_point
                    state.player.seek(random_second)

            elif state.step == STEP_PLAYING:
                state.reset_track()
            elif state.step == STEP_ANSWERING:
                state.step = STEP_PLAYING
                state.toggle_pause()
                if state.retry_mode == RETRY_MODE_TIMER:
                    pg.clock.schedule_once(state.restore_buzzer, state.retry_timer_duration, team=state.last_team_to_buzz)
                state.reset_answer_timer()
        elif symbol == pg.window.key.R:
            state.selected_track.artist_revealed = True
            state.selected_track.title_revealed = True
            state.display_window.dispatch_event("on_draw")
        elif symbol == pg.window.key.T and state.step == STEP_ANSWERING and not state.selected_track.title_revealed:
            state.last_team_to_buzz.score += 1
            state.selected_track.title_revealed = True
            state.selected_track.title_found_by = state.last_team_to_buzz
            self.success_fx.play()
        elif symbol == pg.window.key.A and state.step == STEP_ANSWERING and not state.selected_track.artist_revealed:
            state.last_team_to_buzz.score += 1
            state.selected_track.artist_revealed = True
            state.selected_track.artist_found_by = state.last_team_to_buzz
            self.success_fx.play()
        elif symbol == pg.window.key.L:
            state.leaderboard_visible = not state.leaderboard_visible
            state.display_window.dispatch_event("on_draw")
        elif symbol == pg.window.key.S:
            output = ""
            for team in state.teams:
                output += f"{team.name}:{team.button_id}:{team.score}\n"
            filename = f"teams_{int(time())}.txt"
            with open(filename, "w") as f:
                f.write(output)
        elif symbol == pg.window.key.G:
            if modifiers & pg.window.key.MOD_CTRL:
                state.shift_selected_gif(1)
            elif modifiers & pg.window.key.MOD_ALT:
                state.gif_visible = not state.gif_visible
            else:
                state.shift_selected_gif(-1)

        elif symbol in NUMBER_KEYS:
            number = NUMBER_KEYS.index(symbol) + 1
            try:
                team = state.get_team_by_number(number)
                if modifiers & pg.window.key.MOD_CTRL:
                    team.score -= 1
                else:
                    team.score += 1
            except StopIteration:
                pass

    def on_text(self, text):
        if text == ".":
            state.pitch += Decimal("0.1")
            if state.player:
                state.player.pitch = float(state.pitch)
        elif text == ",":
            if state.pitch <= 0.1:
                return
            state.pitch -= Decimal("0.1")
            if state.player:
                state.player.pitch = float(state.pitch)

    def on_text_motion(self, motion):
        if motion == pg.window.key.MOTION_UP and not state.player:
            state.shift_selected_track(-1)
        elif motion == pg.window.key.MOTION_DOWN and not state.player:
            state.shift_selected_track(1)
        elif motion == pg.window.key.MOTION_RIGHT and state.player:
            state.player.seek(state.player.time + 1)
        elif motion == pg.window.key.MOTION_LEFT and state.player:
            state.player.seek(state.player.time - 1)

    def on_close(self):
        sys.exit()

class DisplayWindow(pg.window.Window):
    def __init__(self):
        super(DisplayWindow, self).__init__(DISPLAY_WINDOW_WIDTH,
                                            DISPLAY_WINDOW_HEIGHT,
                                            resizable=True,
                                            caption="Blind - Afficheur")
        self.set_location(50,50)

        self.neutral_image = pg.image.load(os.path.join(IMAGES_DIR, NEUTRAL_IMAGE)).get_texture()
        self.background_image = pg.image.load(os.path.join(IMAGES_DIR, BACKGROUND_IMAGE)).get_texture()
        self.buzzer_image = pg.image.load(os.path.join(IMAGES_DIR, BUZZER_IMAGE)).get_texture()

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

        self.answering_team_label = pg.text.Label("",
                                                  font_name=DISPLAY_WINDOW_FONT,
                                                  font_size=0,
                                                  x=0,
                                                  y=0,
                                                  multiline=True,
                                                  width=100,
                                                  align="center",
                                                  anchor_x="center",
                                                  anchor_y="center",
                                                  color=(255,255,255,255))


    def on_draw(self):
        self.clear()
        self.background_image.blit(0,0,1)

        track = state.selected_track

        if state.step == STEP_ANSWERING:
            self.cover_image = self.buzzer_image
        elif track.artist_revealed and track.title_revealed:
            self.cover_image = track.cover
        else:
            self.cover_image = self.neutral_image

        self.cover_image.width = self.height*0.7
        self.cover_image.height = self.cover_image.width
        self.cover_image.anchor_x = self.cover_image.width//2
        self.cover_image.anchor_y = self.cover_image.height//2
        self.cover_image.x = self.width//2 # placé dans `image` artificiellement, utile pour dessiner la barre de timer
        self.cover_image.y = self.height*0.6

        if track.artist_revealed:
            self.current_artist_label.text = track.artist
            self.current_artist_label.color = (0,0,0,255)
        else:
            self.current_artist_label.text = "Artiste ?"
            self.current_artist_label.color = (100,100,100,255)

        if track.title_revealed:
            self.current_title_label.text = track.title
            self.current_title_label.color = (0,0,0,255)
        else:
            self.current_title_label.text = "Titre ?"
            self.current_title_label.color = (100,100,100,255)

        if track.artist_found_by:
            self.artist_found_by_label.text = track.artist_found_by.name
        else:
            self.artist_found_by_label.text = ""

        if track.title_found_by:
            self.title_found_by_label.text = track.title_found_by.name
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

        self.timer_bar.x = self.cover_image.x - self.cover_image.width//2 - self.width*0.05
        self.timer_bar.y = self.cover_image.y - self.cover_image.height//2
        self.timer_bar.width = self.cover_image.width + (2*self.width*0.05)
        self.timer_bar.height = state.timer * self.cover_image.height
        self.timer_bar.draw()

        self.cover_image.blit(self.cover_image.x, self.cover_image.y, 1) # blit tardif, pour qu'il ait lieu par dessus
                                                                         # la barre de timer

        if state.step == STEP_ANSWERING:
            self.answering_team_label.text = state.last_team_to_buzz.name
        else:
            self.answering_team_label.text = ""
        self.answering_team_label.draw()
        
        if state.leaderboard_visible:
            scores_string = ""
            for team in state.teams:
                scores_string += f"{team.name} : {str(team.score)}\n"
            scores_string = scores_string.strip()
            self.leaderboard_label.text = scores_string

            self.background_image.blit(0,0,1)
            self.leaderboard_label.draw()

        if state.gifs and state.gif_visible:
            state.gifs[0]["sprite"].scale *= ((self.width/3) / state.gifs[0]["sprite"].width)
            state.gifs[0]["sprite"].y = 0
            state.gifs[0]["sprite"].x = self.width - state.gifs[0]["sprite"].width - self.width//20
            state.gifs[0]["sprite"].draw()

    def on_resize(self, width, height):
        self.background_image.width, self.background_image.height = width, height

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

        self.answering_team_label.x = width*0.5
        self.answering_team_label.y = height*0.8
        self.answering_team_label.font_size = height//8
        self.answering_team_label.width = width*0.5

        super(DisplayWindow, self).on_resize(width, height) # https://stackoverflow.com/a/23276270/602339

    def on_activate(self):
        self.dispatch_event("on_draw")

    def on_expose(self):
        self.dispatch_event("on_draw")

    def on_key_press(self, symbol, modifiers): # empêche Esc de fermer la fenêtre
        pass

    def on_close(self):
        sys.exit()

# Classes de jeu
################

class State:
    def __init__(self):
        self.step = STEP_IDLE
        self._joystick = None
        self._teams = []
        self.tracks = []
        self.track_number = 0
        self.player = None
        self.timer = 1
        self.timer_running = False
        self.pitch = Decimal("1")
        self.leaderboard_visible = False
        self.last_team_to_buzz = None
        self.gifs = None
        self.gif_visible = False
        self.playlist_scroll = 0

        self.answer_timer_duration = None
        self.retry_mode = None
        self.retry_timer_duration = None
        self.pause_during_answers = None
        self.fadeout_factor = None

    @property
    def joystick(self):
        if not self._joystick:
            joysticks = pg.input.get_joysticks()
            if not joysticks:
                print("Aucun joystick connecté")
                sys.exit()
            self._joystick = joysticks[0]
            self._joystick.open()
        return self._joystick

    @property
    def teams(self):
        return sorted(self._teams, key=lambda x: (-x.score, x.name))

    @property
    def selected_track(self):
        return self.tracks[self.track_number]
    
    def add_team(self, team):
        team.number = len(self._teams) + 1
        self._teams.append(team)

    def get_team_by_button_id(self, button_id):
        try:
            team = next(team for team in self._teams if team.button_id == button_id)
        except StopIteration:
            team = None
        return team

    def get_team_by_number(self, number):
        try:
            team = next(team for team in self._teams if team.number == number)
        except StopIteration:
            team = None
        return team

    def shift_selected_track(self, offset=1):
        requested_track_number = self.track_number + offset
        if 0 <= requested_track_number < len(self.tracks):
            self.track_number += offset
            self.display_window.dispatch_event("on_draw")

    def shift_selected_gif(self, offset=1):
        if not self.gifs:
            return
        self.gifs.rotate(offset)

    def toggle_pause(self):
        if self.pause_during_answers:
            if self.player.playing:
                self.player.pause()
            else:
                self.player.play()
        else:
            if self.player.volume == 1:
                self.player.volume = 0.1
            else:
                self.player.volume = 1

    def make_quieter(self, dt):
        if self.player.volume > 0.01:
            self.player.volume *= self.fadeout_factor
            return

        self.player.pause()
        self.player = None
        self.step = STEP_IDLE
        pg.clock.unschedule(self.make_quieter)
        for team in self.teams:
            team.can_buzz = True
        self.reset_answer_timer()

    def reduce_answer_timer(self, dt):
        unit = dt / self.answer_timer_duration

        if self.timer > unit:
            self.timer -= unit
            return

        self.timer = 0

        pg.clock.unschedule(self.reduce_answer_timer)

    def restore_buzzer(self, dt, team):
        team.can_buzz = True

    def reset_answer_timer(self):
        self.timer = 1
        self.timer_running = False
        pg.clock.unschedule(self.reduce_answer_timer)

    def reset_track(self):
        pg.clock.schedule_interval(self.make_quieter, 0.1)

class Team:
    def __init__(self, name="NAME", score=0, button_id=0):
        self.name = name
        self.score = score
        self.can_buzz = True
        self.button_id = button_id

class Track:
    def __init__(self, artist="ARTIST", title="TITLE", media=None, cover=None):
        self.artist = artist
        self.title = title
        self.media = media
        self.cover = cover
        self.artist_revealed = False
        self.title_revealed = False
        self.artist_found_by = None
        self.title_found_by = None

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
        lines = f.read().splitlines()

    for line in lines:
        line = line.strip()
        if "=" in line:
            track, video_id = line.split("=")
        else:
            track = line
            video_id = None

        print(f"Démarre '{track}' ({video_id if video_id else 'pas de video_id'})...")

        if not os.path.isfile(os.path.join(TRACKS_DIR, f"{track}.mp3")):
            download_audio(track=track, video_id=video_id)
        else:
            print(f"Le fichier audio existe déjà, ignore.")

        if not os.path.isfile(os.path.join(COVERS_DIR, f"{track}.jpg")):
            download_cover(track)
        else:
            print(f"La pochette existe déjà, ignore.")

@cli.command()
def check():
    """Discover what button triggers what code, visually."""
    button_check_window = ButtonCheckWindow()

    @state.joystick.event
    def on_joybutton_press(joystick, button):
        # ici : convertir évent. le code reçu
        try:
            button_check_window.button_labels[button].color = (255, 0, 0, 255)
        except IndexError:
            pass
        button_check_window.dispatch_event("on_draw")

    @state.joystick.event
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

    state.answer_timer_duration = answer_timer_duration
    state.retry_mode = ("strict", "alternating", "timer").index(retry_mode)
    state.retry_timer_duration = retry_timer_duration
    state.pause_during_answers = pause_during_answers
    state.fadeout_factor = fadeout_factor

    _ = state.joystick # Simple accès au joystick, pour l'initialiser et échouer s'il est absent 

    with open(teams_file, "r") as f:
        lines = f.read().splitlines()

    for line in lines:
        line = line.strip()
        fields = line.split(":")
        name, button_id = fields[0], int(fields[1])
        if len(fields) == 3:
            score = int(fields[2])
        else:
            score = 0
        state.add_team(Team(name=name, score=score, button_id=button_id))

    with open(playlist_file, "r") as f:
        lines = f.read().splitlines()

    for idx, line in enumerate(lines):
        line = line.strip()
        if "=" in line:
            line = line.split("=")[0]
        artist, title = line.split(" - ")
        if "/" in artist:
            artist = artist.split("/")[-1]
        media = pg.media.load(os.path.join(TRACKS_DIR, f"{line}.mp3"), streaming=False)
        cover = pg.image.load(os.path.join(COVERS_DIR, f"{line}.jpg")).get_texture()
        track = Track(artist, title, media, cover)
        state.tracks.append(track)
        print(f"Piste {str(idx+1)}/{len(lines)} chargée ({line})")

    buzzer_fx = pg.media.load(os.path.join(FX_DIR, BUZZER_FX), streaming=False)

    gifs = []
    gif_files = sorted(os.listdir(GIFS_DIR))
    for idx, gif_file in enumerate(gif_files):
        gif_name = gif_file[:-4]
        gif_sprite = pg.sprite.Sprite(img=pg.resource.animation(os.path.join(GIFS_DIR, gif_file)))
        gifs.append({"name":gif_name, "sprite":gif_sprite})
        print(f"GIF {str(idx+1)}/{len(gif_files)} chargé ({gif_name})")
    state.gifs = deque(gifs)

    if state.tracks:
        state.tracks[0].media.play().pause() # pour éviter un lag à la 1re piste

    state.display_window = DisplayWindow()
    state.control_window = ControlWindow()

    @state.joystick.event
    def on_joybutton_press(joystick, button_id):
        if state.selected_track.artist_revealed and state.selected_track.title_revealed:
            return

        if state.step == STEP_PLAYING:
            if not (team_trying_to_buzz := state.get_team_by_button_id(button_id)):
                return
            if team_trying_to_buzz.can_buzz:
                state.last_team_to_buzz = team_trying_to_buzz
            else:
                return
            buzzer_fx.play()
            state.step = STEP_ANSWERING
            state.toggle_pause()
            if state.retry_mode == RETRY_MODE_ALTERNATING:
                for team in state.teams:
                    team.can_buzz = True
            state.last_team_to_buzz.can_buzz = False
    
    pg.app.run()

# Exécution principale
######################

if __name__ == "__main__":
    state = State()
    cli()