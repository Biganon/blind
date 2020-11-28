import os
import pyglet as pg
import sys

FONT1 = "monospace"
STEP_IDLE = 0
STEP_PLAYING = 1
STEP_ANSWERING = 2
STEP_REVEALED = 3
TRACKS_CENTER = 500
TEAMS_CENTER = 200
FADEOUT = True
FADEOUT_INTERVAL = 0.1

def make_quieter(dt, fadeout=True):
    global player
    global answering_team    
    global artist_found
    global title_found
    global step

    if player.volume > 0.01 and fadeout:
        player.volume *= 0.5
        return

    player.pause()
    player = None
    step = STEP_IDLE
    pg.clock.unschedule(make_quieter)
    for team in teams:
        teams[team].can_buzz = True
    answering_team = None
    artist_found = False
    title_found = False

def reset(fadeout=True):
    pg.clock.schedule_interval(make_quieter, FADEOUT_INTERVAL, fadeout=fadeout)

class ButtonCheckWindow(pg.window.Window):
    def __init__(self):
        super(ButtonCheckWindow, self).__init__(400, 100, caption="Blind - Test des boutons")

        self.button_labels = []
        for i in range(10):
            self.button_labels.append(pg.text.Label(str(i), font_name=FONT1, font_size=36, x=i*30, y=self.height//2, anchor_x="left", anchor_y="center"))

    def on_draw(self):
        self.clear()
        for button_label in self.button_labels:
            button_label.draw()

class ControlWindow(pg.window.Window):
    def __init__(self):
        super(ControlWindow, self).__init__(800, 600, caption="Blind - Contrôleur")

        self.previous_artist_label = pg.text.Label("Artiste", font_name=FONT1, font_size=18, x=self.width//2, y=TRACKS_CENTER+50, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.previous_title_label = pg.text.Label("Titre", font_name=FONT1, font_size=18, x=self.width//2, y=TRACKS_CENTER+30, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.current_artist_label = pg.text.Label("Artiste", font_name=FONT1, font_size=18, x=self.width//2, y=TRACKS_CENTER+10, anchor_x="center", anchor_y="center")
        self.current_title_label = pg.text.Label("Titre", font_name=FONT1, font_size=18, x=self.width//2, y=TRACKS_CENTER-10, anchor_x="center", anchor_y="center")
        self.next_artist_label = pg.text.Label("Artiste", font_name=FONT1, font_size=18, x=self.width//2, y=TRACKS_CENTER-30, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.next_title_label = pg.text.Label("Titre", font_name=FONT1, font_size=18, x=self.width//2, y=TRACKS_CENTER-50, anchor_x="center", anchor_y="center", color=(100, 100, 100, 255))
        self.track_number_label = pg.text.Label("#/#", font_name=FONT1, font_size=18, x=20, y=TRACKS_CENTER, anchor_x="left", anchor_y="center")
        self.step_label = pg.text.Label("Etape", font_name=FONT1, font_size=18, x=20, y=20, anchor_x="left", anchor_y="bottom")
        self.scores_label = pg.text.Label("Scores", font_name=FONT1, font_size=18, multiline=True, width=760, align="right", x=780, y=20, anchor_x="right", anchor_y="bottom") 

    def on_draw(self):
        global step
        global player

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

        if artist_found:
            self.current_artist_label.color = (0, 255, 0, 255)
        else:
            self.current_artist_label.color = (255, 255, 255, 255)
        
        if title_found:
            self.current_title_label.color = (0, 255, 0, 255)
        else:
            self.current_title_label.color = (255, 255, 255, 255)

        if title_found and artist_found:
            step = STEP_REVEALED
            player.volume = 1
            # player.play()

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

    def on_key_press(self, symbol, modifiers):
        global step
        global track_number
        global player
        global artist_found
        global title_found

        if symbol == pg.window.key.ENTER:
            if step == STEP_IDLE:
                step = STEP_PLAYING
                player = tracks[track_number].media.play()
            elif step == STEP_PLAYING: # abandon, les équipes n'ont pas tout trouvé
                reset(fadeout=FADEOUT)
            elif step == STEP_ANSWERING:
                step = STEP_PLAYING
                player.volume = 1
                # player.play()
            elif step == STEP_REVEALED:
                reset(fadeout=FADEOUT)

        elif symbol == pg.window.key.UP and step == STEP_IDLE and track_number > 0:
            track_number -= 1
        elif symbol == pg.window.key.DOWN and step == STEP_IDLE and track_number < len(tracks)-1:
            track_number += 1
        elif symbol == pg.window.key.T and step == STEP_ANSWERING and not title_found:
            answering_team.score += 1
            title_found = True
        elif symbol == pg.window.key.A and step == STEP_ANSWERING and not artist_found:
            answering_team.score += 1
            artist_found = True

class Team:
    def __init__(self, name="NAME"):
        self.name = name
        self.score = 0
        self.can_buzz = True

class Track:
    def __init__(self, artist="ARTIST", title="TITLE", media=None):
        self.artist = artist
        self.title = title
        self.media = media

if __name__ == "__main__":

    teams = {}
    tracks = []
    step = STEP_IDLE
    track_number = 0
    player = None
    answering_team = None
    artist_found = False
    title_found = False

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
            track_artist, track_title, track_file = line.split("_")
            track_media = pg.media.load(os.path.join("tracks", track_file), streaming=False)
            track = Track(track_artist, track_title, track_media)
            tracks.append(track)
            print(f"[{str(idx+1).rjust(len(str(len(lines))))}/{len(lines)}] {track_artist} - {track_title} ({track_file})")

        dummy_player = tracks[0].media.play()
        dummy_player.pause()
        del dummy_player

        control_window = ControlWindow()

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
                answering_team.can_buzz = False
                step = STEP_ANSWERING
                player.volume = 0.1
                # player.pause()

            # control_window.dispatch_event("on_draw")

    else:
        sys.exit()

    pg.app.run()