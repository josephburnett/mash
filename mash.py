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
        self.cursor_blink_rate_sec = 1
        self.custom_words = []
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
        # History
        word_offset = self.config.screen_height - 250
        for w in reversed(state.history):
            if word_offset < -100:
                continue
            history = self.font.render(w, 0, [255,255,255])
            self.surface.blit(history, [0,word_offset])
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
        self.known_words.update(set(map(lambda x: x.strip().upper(), config.custom_words)))

    def recognize(self, letters):
        word = self.last_proto_word(letters)
        if word is None or word == '':
            return None
        if word in self.known_words:
            return word

    def last_proto_word(self, letters):
        if len(letters) == 0:
            return nil
        if letters[len(letters)-1] == ' ':
            letters = letters[:-1]
        if ' ' in letters:
            last_space = len(letters) - letters[::-1].index(' ') - 1
            return ''.join(letters[last_space+1:])
        return ''.join(letters)


def enum(**enums):
    return type('Enum', (), enums)

InputState = enum(EMPTY=1, MASHING=2, MASHING_SPACE=3, TYPING=4, TYPING_SPACE=5)


class State:

    def __init__(self, config):
        self.config = config
        self.letters = []
        self.words = []
        self.history = ["OKAY", "MASH"]
        self.frames = 0
        self.input_state = InputState.EMPTY
        self.input_state_stack = []

    def transition(self, state):
        self.input_state_stack.append(self.input_state)
        self.input_state = state

    def pop(self):
        self.input_state = self.input_state_stack[len(self.input_state_stack)-1]
        self.input_state_stack = self.input_state_stack[:-1]


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
        state = self.state

        if (key >= K_a and key <= K_z):
            state.letters.append(chr(key).capitalize())
            # Transition ([K_a-K_z] *) => (TYPING)
            if self.words.recognize(state.letters):
                state.transition(InputState.TYPING)
            # Transition ([K_a-K_z] *) => (MASHING)
            else:
                state.transition(InputState.MASHING)

        if key == K_SPACE:
            if state.input_state in [InputState.TYPING_SPACE, InputState.MASHING_SPACE]:
                pass
            # Transition (K_SPACE TYPING) => (TYPING_SPACE)
            elif state.input_state == InputState.TYPING:
                state.letters.append(' ')
                word = self.words.recognize(state.letters)
                self.speech.say(word)
                state.words.append(word)
                state.transition(InputState.TYPING_SPACE)
            # Transition (K_SPACE MASHING) => (MASHING_SPACE)
            elif state.input_state == InputState.MASHING:
                state.letters.append(' ')
                state.transition(InputState.MASHING_SPACE)

        if key == K_BACKSPACE:
            if state.input_state == InputState.EMPTY:
                pass
            # Transition (K_BACKSPACE *) => (prev)
            else:
                if state.input_state == InputState.TYPING_SPACE:
                    state.words = state.words[:-1]
                state.letters = state.letters[:-1]
                state.pop()

        if key == K_RETURN:
            # Transition: (K_RETURN MASHING|MASHING_SPACE) => (EMPTY)
            if state.input_state in [InputState.MASHING, InputState.MASHING_SPACE]:
                state.letters = []
                state.words = []
                state.transition(InputState.EMPTY)
            # Transition: (K_RETURN TYPING|TYPING_SPACE) => (EMPTY)
            else:
                if state.input_state == InputState.TYPING:
                    word = self.words.recognize(state.letters)
                    self.speech.say(word)
                    state.words.append(word)
                state.history.append(' '.join(state.words))
                state.letters = []
                state.words = []
                state.transition(InputState.EMPTY)

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
