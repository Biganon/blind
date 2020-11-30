import os
import pyglet as pg
import sys

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

CONTROL_WINDOW_WIDTH = 800
CONTROL_WINDOW_HEIGHT = 600
CONTROL_WINDOW_PADDING = 20
TRACKS_CENTER = CONTROL_WINDOW_HEIGHT - 100
TIMER_BAR_WIDTH = 200
TIMER_BAR_HEIGHT = 20
DISPLAY_WINDOW_WIDTH = 1200
DISPLAY_WINDOW_HEIGHT = 900
DISPLAY_WINDOW_PADDING = 40
DISPLAY_WINDOW_BACKGROUND_COLOR = (255,255,255)

FADEOUT_FACTOR = 0.8
BUZZER_FX = "buzzer2.wav"
SUCCESS_FX = "success4.wav"
TIMER_DURATION = 3
NEUTRAL_IMAGE = "thinking2.png"
BACKGROUND_IMAGE = "background1.png"

# Callbacks
###########

def make_quieter(dt):
    global player
    global answering_team    
    global artist_revealed
    global title_revealed
    global artist_found_by
    global title_found_by
    global step

    if player.volume > 0.01:
        player.volume *= FADEOUT_FACTOR
        return

    player.pause()
    player = None
    step = STEP_IDLE
    pg.clock.unschedule(make_quieter)
    for team in teams:
        teams[team].can_buzz = True
    answering_team = None
    artist_revealed = False
    title_revealed = False
    artist_found_by = None
    title_found_by = None
    reset_timer()

def reduce_timer(dt):
    global timer

    unit = dt / TIMER_DURATION

    if timer > unit:
        timer -= unit
        return

    timer = 0
    pg.clock.unschedule(reduce_timer)

# Fonctions utilitaires
#######################

def reset_timer():
    global timer
    global timer_running
    timer = 1
    timer_running = False
    pg.clock.unschedule(reduce_timer)

def reset_turn():
    pg.clock.schedule_interval(make_quieter, 0.1)

# Classes de fenêtres
#####################

class ButtonCheckWindow(pg.window.Window):
    def __init__(self):
        super(ButtonCheckWindow, self).__init__(400, 100, caption="Blind - Test des boutons")

        self.button_labels = []
        for i in range(10):
            self.button_labels.append(pg.text.Label(str(i), font_name=CONTROL_WINDOW_FONT, font_size=36, x=i*30, y=self.height//2, anchor_x="left", anchor_y="center"))

    def on_draw(self):
        self.clear()
        for button_label in self.button_labels:
            button_label.draw()

class ControlWindow(pg.window.Window):
    def __init__(self):
        super(ControlWindow, self).__init__(CONTROL_WINDOW_WIDTH, CONTROL_WINDOW_HEIGHT, caption="Blind - Contrôleur")

        self.previous_artist_label = pg.text.Label("Artiste", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=self.width//2, y=TRACKS_CENTER+55, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.previous_title_label = pg.text.Label("Titre", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=self.width//2, y=TRACKS_CENTER+35, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.current_artist_label = pg.text.Label("Artiste", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=self.width//2, y=TRACKS_CENTER+10, anchor_x="center", anchor_y="center")
        self.current_title_label = pg.text.Label("Titre", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=self.width//2, y=TRACKS_CENTER-10, anchor_x="center", anchor_y="center")
        self.next_artist_label = pg.text.Label("Artiste", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=self.width//2, y=TRACKS_CENTER-35, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.next_title_label = pg.text.Label("Titre", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=self.width//2, y=TRACKS_CENTER-55, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.track_number_label = pg.text.Label("#/#", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=CONTROL_WINDOW_PADDING, y=CONTROL_WINDOW_HEIGHT-CONTROL_WINDOW_PADDING, anchor_x="left", anchor_y="top")
        self.step_label = pg.text.Label("Etape", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, x=CONTROL_WINDOW_PADDING, y=CONTROL_WINDOW_PADDING, anchor_x="left", anchor_y="bottom")
        self.scores_label = pg.text.Label("Scores", font_name=CONTROL_WINDOW_FONT, font_size=CONTROL_WINDOW_FONT_SIZE, multiline=True, width=CONTROL_WINDOW_WIDTH-(2*CONTROL_WINDOW_PADDING), align="right", x=CONTROL_WINDOW_WIDTH-CONTROL_WINDOW_PADDING, y=CONTROL_WINDOW_PADDING, anchor_x="right", anchor_y="bottom") 

        self.timer_outline = pg.shapes.Rectangle(CONTROL_WINDOW_WIDTH-TIMER_BAR_WIDTH-CONTROL_WINDOW_PADDING-4, CONTROL_WINDOW_HEIGHT-TIMER_BAR_HEIGHT-CONTROL_WINDOW_PADDING-4, TIMER_BAR_WIDTH+4, TIMER_BAR_HEIGHT+4, color=(255, 255, 255))
        self.timer_inside = pg.shapes.Rectangle(CONTROL_WINDOW_WIDTH-TIMER_BAR_WIDTH-CONTROL_WINDOW_PADDING-3, CONTROL_WINDOW_HEIGHT-TIMER_BAR_HEIGHT-CONTROL_WINDOW_PADDING-3, TIMER_BAR_WIDTH+2, TIMER_BAR_HEIGHT+2, color=(0, 0, 0))
        self.timer_bar = pg.shapes.Rectangle(CONTROL_WINDOW_WIDTH-TIMER_BAR_WIDTH-CONTROL_WINDOW_PADDING-2, CONTROL_WINDOW_HEIGHT-TIMER_BAR_HEIGHT-CONTROL_WINDOW_PADDING-2, TIMER_BAR_WIDTH, TIMER_BAR_HEIGHT, color=(255, 255, 255))

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

        self.step_label.text = ("Prêt", "Lecture", "Réponse", "Révélation")[step]
        
        if step == STEP_ANSWERING:
            self.step_label.text += f" ({answering_team.name})"
            if not timer_running:
                timer_running = True
                pg.clock.schedule_interval(reduce_timer, 0.01)

        self.timer_bar.width = timer * TIMER_BAR_WIDTH

        if artist_revealed:
            self.current_artist_label.color = (0, 255, 0, 255)
        else:
            self.current_artist_label.color = (255, 255, 255, 255)
        
        if title_revealed:
            self.current_title_label.color = (0, 255, 0, 255)
        else:
            self.current_title_label.color = (255, 255, 255, 255)

        if title_revealed and artist_revealed and step == STEP_ANSWERING: # Dernier test : nécessaire pour n'exécuter qu'une fois
            step = STEP_REVEALED
            player.volume = 1
            # pg.clock.unschedule(reduce_timer) # Décommenter pour mettre le timer en pause lorsque tout trouvé
            # player.play() # Alternative à la réduction du son

        scores_string = ""
        for team in teams:
            scores_string += f"{teams[team].name} : {str(teams[team].score).rjust(3)}\n"
        scores_string = scores_string.strip()
        self.scores_label.text = scores_string

        self.previous_artist_label.draw()
        self.previous_title_label.draw()
        self.current_artist_label.draw()
        self.current_title_label.draw()
        self.next_artist_label.draw()
        self.next_title_label.draw()
        self.track_number_label.draw()
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

        if symbol == pg.window.key.ENTER:
            if step == STEP_IDLE:
                step = STEP_PLAYING
                player = tracks[track_number].media.play()
            elif step == STEP_PLAYING:
                if modifiers == 1: # shift appuyé : repasse en mode idle, sans révéler
                    reset_turn()
                else: # sinon : révèle
                    step = STEP_REVEALED
                    artist_revealed = True
                    title_revealed = True
            elif step == STEP_ANSWERING:
                step = STEP_PLAYING
                player.volume = 1
                reset_timer()
                # player.play() # Alternative à la réduction du son
            elif step == STEP_REVEALED:
                reset_turn()

        elif symbol == pg.window.key.UP and step == STEP_IDLE and track_number > 0:
            track_number -= 1
        elif symbol == pg.window.key.DOWN and step == STEP_IDLE and track_number < len(tracks)-1:
            track_number += 1
        elif symbol == pg.window.key.T and step == STEP_ANSWERING and not title_revealed:
            answering_team.score += 1
            title_revealed = True
            title_found_by = answering_team
            success_fx.play()
        elif symbol == pg.window.key.A and step == STEP_ANSWERING and not artist_revealed:
            answering_team.score += 1
            artist_revealed = True
            artist_found_by = answering_team
            success_fx.play()

class DisplayWindow(pg.window.Window):
    def __init__(self):
        super(DisplayWindow, self).__init__(DISPLAY_WINDOW_WIDTH, DISPLAY_WINDOW_HEIGHT, resizable=True, caption="Blind - Afficheur")
        self.set_location(50,50)
        #self.background = pg.shapes.Rectangle(0, 0, 0, 0, color=DISPLAY_WINDOW_BACKGROUND_COLOR)
        self.background = background_image
        self.current_artist_label = pg.text.Label("Artiste", font_name=DISPLAY_WINDOW_FONT, font_size=0, x=0, y=0, anchor_x="left", anchor_y="bottom", color=(0,0,0,255))
        self.current_title_label = pg.text.Label("Titre", font_name=DISPLAY_WINDOW_FONT, font_size=0, x=0, y=0, anchor_x="left", anchor_y="bottom", color=(0,0,0,255))
        self.artist_found_by_label = pg.text.Label("", font_name=DISPLAY_WINDOW_FONT, font_size=0, x=0, y=0, anchor_x="left", anchor_y="bottom", color=(0,100,0,255))
        self.title_found_by_label = pg.text.Label("", font_name=DISPLAY_WINDOW_FONT, font_size=0, x=0, y=0, anchor_x="left", anchor_y="bottom", color=(0,100,0,255))
        self.timer_bar = pg.shapes.Rectangle(0, 0, 0, 0, color=(0,0,0))

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
        image.x = self.width//2 # placé dans `image` artificiellement, utile pour dessiner la barre de timer (L271)
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

        self.artist_found_by_label.x = self.current_artist_label.x + self.current_artist_label.content_width + self.width*0.02
        self.title_found_by_label.x = self.current_title_label.x + self.current_title_label.content_width + self.width*0.02
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
    def __init__(self, name="NAME"):
        self.name = name
        self.score = 0
        self.can_buzz = True

class Track:
    def __init__(self, artist="ARTIST", title="TITLE", media=None, cover=None):
        self.artist = artist
        self.title = title
        self.media = media
        self.cover = cover

# Exécution principale
######################

if __name__ == "__main__":

    teams = {}
    tracks = []
    step = STEP_IDLE
    track_number = 0
    player = None
    answering_team = None
    artist_revealed = False
    title_revealed = False
    artist_found_by = None
    title_found_by = None
    timer = 1 # va de 1 à 0
    timer_running = False

    try:
        action = sys.argv[1]
    except IndexError:
        print(f"Usage :\t{sys.argv[0]} TEAMS_FILE")
        print(f"\t{sys.argv[0]} check")
        sys.exit()

    joysticks = pg.input.get_joysticks()
    assert joysticks, "Aucun joystick connecté"
    joystick = joysticks[0]
    joystick.open()

    if action == "check":
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

    elif action == "play":
        teams_file = sys.argv[2]
        playlist_file = sys.argv[3]
        with open(teams_file, "r") as f:
            lines = f.read().splitlines()

        for line in lines:
            team_name, team_id = line.split("_")
            team_id = int(team_id) 
            teams[team_id] = Team(team_name)

        with open(playlist_file, "r") as f:
            lines = f.read().splitlines()

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
            global answering_team

            if step == STEP_PLAYING:
                try:
                    buzzing_team = teams[button]
                except KeyError:
                    return
                if buzzing_team.can_buzz:
                    answering_team = buzzing_team
                else:
                    return
                buzzer_fx.play()
                answering_team.can_buzz = False
                step = STEP_ANSWERING
                player.volume = 0.1
                # player.pause() # Alternative à la réduction du son

    else:
        sys.exit()

    pg.app.run()