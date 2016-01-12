import os, pygame, sys, yaml
from multiprocessing import Pool
from os.path import expanduser
from pygame.locals import *


class Configuration:
    def __init__(self):
        self.fps = 30
        self.max_letters = 20
        self.font_size = 150
        self.screen_width = 800
        self.screen_height = 600
        self.allowed_punctuation = [K_SPACE, K_PERIOD, K_RETURN]
        self.cursor_blink_rate_sec = 1
        try:
            with open (expanduser('~/.mash')) as f:
                custom_config = yaml.safe_load(f)
                self.__dict__.update(custom_config)
        except IOError:
            pass


class Time:

    def __init__(self, config):
        self.config = config
        self.fps_clock = pygame.time.Clock()

    def tick(self):
        self.fps_clock.tick(self.config.fps)


class Display:

    def __init__(self, config):
        self.config = config
        self.surface = pygame.display.set_mode((config.screen_width, config.screen_height))
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), config.font_size)

    def refresh(self, state):
        self.surface.fill([0,0,0])
        # Compute cursor
        cursor = self.font.render('_', 0, [255,255,255])
        cursor_width = cursor.get_width()
        cursor_point = [self.config.screen_width - cursor_width - 25, self.config.screen_height - 110]
        cursor_on = state.frames / (self.config.fps / 2) % 2 == 0
        # Compute letters
        l = self.font.render(''.join(state.letters), 0, [255,255,255])
        w = l.get_width()
        # Adjust cursor to remove left-side whitespace
        left_whitespace = cursor_point[0] - w
        if left_whitespace > 0:
            cursor_point[0] -= left_whitespace
        # Draw cursor
        if cursor_on:
            self.surface.blit(cursor, cursor_point)
        # Draw letters
        self.surface.blit(l, [cursor_point[0] - w, cursor_point[1]])
        # Words
        word_offset = self.config.screen_height - 250
        for w in reversed(state.words):
            if word_offset < -100:
                continue
            words = self.font.render(w, 0, [255,255,255])
            self.surface.blit(words, [0,word_offset])
            word_offset -= 100
        pygame.display.flip()


class Speech:

    def __init__(self, config):
        self.config = config
        self.pool = Pool(processes=1)

    def say(self, word):
        self.pool.apply_async(speak, [word])


class Words:

    def __init__(self, config):
        self.config = config
        with open('words.txt', 'r') as f:
            self.known_words = set(map(lambda x: x.strip().upper(), list(f)))

    def recognize(self, state):
        word_letters = []
        word = ''
        for l in state.letters:
            if l == ' ' or l == '.':
                word = ''.join(word_letters)
                word_letters = []
            else:
                word_letters.append(l)
        if word in self.known_words:
            return word


class State:

    def __init__(self, config):
        self.config = config
        self.letters = []
        self.words = ["OKAY", "MASH"]
        self.frames = 0


class Game:

    def __init__(self):
        pygame.init()
        pygame.display.set_caption('MASH!')
        self.config = Configuration()
        self.time = Time(self.config)
        self.display = Display(self.config)
        self.speech = Speech(self.config)
        self.words = Words(self.config)
        self.state = State(self.config)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                key = event.key
                self.handle_key_down(key)

    def handle_key_down(self, key):
        if key == K_BACKSPACE:
            if len(self.state.letters) > 0:
                self.state.letters = self.state.letters[:-1]
        elif (key >= K_a and key <= K_z) or key in self.config.allowed_punctuation:
            letters = self.state.letters
            if key == K_RETURN:
                # Return clears the input buffer
                letters.append(' ')
                word = self.words.recognize(self.state)
                if word:
                    self.state.words.append(word)
                    self.speech.say(word)
                self.state.letters = letters = []
            elif key == K_SPACE:
                # Only one space in a row
                if len(letters) > 0 and letters[len(letters)-1] != chr(K_SPACE):
                    letters.append(chr(key))
                    word = self.words.recognize(self.state)
                    if word:
                        self.state.words.append(word)
                        self.speech.say(word)
            else:
                # Everything else appends capitalized
                letters.append(chr(key).capitalize())
            if len(letters) > self.config.max_letters:
                self.state.letters = letters = letters[1:]

    def run(self):
        while True:
            self.handle_events()
            self.state.frames += 1
            self.display.refresh(self.state)
            self.time.tick()


def speak(word):
    os.system('echo {} | festival --tts'.format(word))


if __name__ == '__main__':
    Game().run()
