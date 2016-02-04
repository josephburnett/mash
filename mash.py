import os, pygame, sys, yaml
from multiprocessing import Pool
from os.path import expanduser
from pygame.locals import *


class Configuration:
    def __init__(self):
        # Configuration which can be overridden with a .mash file.
        self.background_color = [0,0,0]
        self.consonate_color = [77,255,136]
        self.cursor_blink_rate_sec = 1
        self.cursor_color = [255,255,255]
        self.custom_words = []
        self.font_size = 150
        self.fps = 30
        self.font_size = 150
        self.mash_color_dim_ratio = 0.35
        self.screen_width = 800
        self.screen_height = 600
        self.vowel_color = [229,128,255]
        self.vowels = ['A','E','I','O','U']
        try:
            with open (expanduser('~/.mash')) as f:
                custom_config = yaml.safe_load(f)
                self.__dict__.update(custom_config)
        except IOError:
            pass
        # Configuration which cannot be overridden.
        self.max_letters = 50

class Time:

    def __init__(self, config):
        self.config = config
        self.fps_clock = pygame.time.Clock()

    def tick(self, state):
        state.frames += 1
        previous_cursor_on = state.cursor_on
        state.cursor_on = state.frames / (self.config.fps / 2) % 2 == 0
        if previous_cursor_on != state.cursor_on:
            state.dirty = True
        self.fps_clock.tick(self.config.fps)


class Display:

    def __init__(self, config):
        self.config = config
        self.surface = pygame.display.set_mode((config.screen_width, config.screen_height))
        self.font = pygame.font.SysFont(pygame.font.get_default_font(), config.font_size)

    def refresh(self, state):
        if not state.dirty:
            return
        self.surface.fill(self.config.background_color)
        # Compute cursor
        cursor = self.font.render('_', 0, self.config.cursor_color)
        cursor_width = cursor.get_width()
        cursor_point = [self.config.screen_width - cursor_width - 25, self.config.screen_height - 110]
        # Compute letters
        format_flags = self.format_letters(state.letters, state.input_state_stack)
        rendered_letters, letters_width, _ = self.render_letters(state.letters, format_flags)
        # Adjust cursor to remove left-side whitespace
        left_whitespace = cursor_point[0] - letters_width
        if left_whitespace > 0:
            cursor_point[0] -= left_whitespace
        # Draw cursor
        if state.cursor_on:
            self.surface.blit(cursor, cursor_point)
        # Draw letters
        point = [cursor_point[0] - letters_width, cursor_point[1]]
        self.display_letters(rendered_letters, point)
        # History
        phrase_offset = self.config.screen_height - 250
        for phrase, input_state_stack in zip(reversed(state.history), reversed(state.history_state_stacks)):
            if phrase_offset < -100:
                continue
            format_flags = self.format_letters(phrase, input_state_stack)
            rendered_letters, _, _ = self.render_letters(phrase, format_flags)
            self.display_letters(rendered_letters, [0, phrase_offset])
            phrase_offset -= 100
        pygame.display.flip()
        state.dirty = False

    def render_letters(self, letters, format_flags):
        if letters is str:
            letters = list(letters)
        rendered_letters = []
        for l,f in zip(letters, format_flags):
            color = self.config.consonate_color
            if FormatFlag.VOWEL in f:
                color = self.config.vowel_color
            if FormatFlag.MASHED_WORD in f:
                ratio = self.config.mash_color_dim_ratio
                color = [int(color[0] * ratio), int(color[1] * ratio), int(color[2] * ratio)]
            if FormatFlag.VOWEL in f:
                rendered_letters.append(self.font.render(l, 0, color))
            else:
                rendered_letters.append(self.font.render(l, 0, color))
        total_width = 0
        max_height = 0
        for r in rendered_letters:
            total_width += r.get_width()
            if r.get_height() > max_height:
                max_height = r.get_height()
        return (rendered_letters, total_width, max_height)

    def display_letters(self, rendered_letters, point):
        offset = 0
        for letter in rendered_letters:
            self.surface.blit(letter, [point[0] + offset, point[1]])
            offset += letter.get_width()

    def format_letters(self, letters, input_state_stack):
        if letters is str:
            letters = list(letters)
        if len(letters) == 0:
            return []
        input_state_stack = input_state_stack[1:] # Drop the first EMPTY state.
        format_flags = []
        recognized_word = False
        first_letter = True
        for letter, input_state in zip(reversed(letters), reversed(input_state_stack)):
            if input_state == InputState.TYPING_SPACE:
                recognized_word = True
            elif input_state == InputState.MASHING_SPACE:
                recognized_word = False
            if first_letter and input_state_stack[len(input_state_stack)-1] == InputState.TYPING:
                recognized_word = True
                first_letter = False
            letter_format = []
            if not recognized_word:
                letter_format.append(FormatFlag.MASHED_WORD)
            if letter in self.config.vowels:
                letter_format.append(FormatFlag.VOWEL)
            else:
                letter_format.append(FormatFlag.CONSONATE)
            format_flags.append(letter_format)
        return reversed(format_flags)


class Speech:

    def __init__(self, config):
        self.config = config
        self.pool = Pool(processes=3)

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
FormatFlag = enum(VOWEL=1, CONSONATE=2, MASHED_WORD=3)


class State:

    def __init__(self, config):
        self.config = config
        self.letters = []
        self.words = []
        self.history = []
        self.history_state_stacks = []
        self.frames = 0
        self.input_state_stack = [InputState.EMPTY]
        self.dirty = True
        self.cursor_on = True

    def transition(self, state):
        self.dirty = True
        if state == InputState.EMPTY:
            self.input_state_stack = [state]
        else:
            self.input_state_stack.append(state)

    def pop(self):
        self.dirty = True
        self.input_state_stack = self.input_state_stack[:-1]

    def current_input_state(self):
        return self.input_state_stack[len(self.input_state_stack)-1]


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
            if state.current_input_state() in [InputState.TYPING_SPACE, InputState.MASHING_SPACE]:
                pass
            # Transition (K_SPACE TYPING) => (TYPING_SPACE)
            elif state.current_input_state() == InputState.TYPING:
                state.letters.append(' ')
                word = self.words.recognize(state.letters)
                self.speech.say(word)
                state.words.append(word)
                state.transition(InputState.TYPING_SPACE)
            # Transition (K_SPACE MASHING) => (MASHING_SPACE)
            elif state.current_input_state() == InputState.MASHING:
                state.letters.append(' ')
                state.transition(InputState.MASHING_SPACE)

        if key == K_BACKSPACE:
            if state.current_input_state() == InputState.EMPTY:
                pass
            # Transition (K_BACKSPACE *) => (prev)
            else:
                if state.current_input_state() == InputState.TYPING_SPACE:
                    state.words = state.words[:-1]
                state.letters = state.letters[:-1]
                state.pop()

        if key == K_RETURN:
            if state.current_input_state() == InputState.EMPTY:
                pass
            # Transition: (K_RETURN MASHING|MASHING_SPACE) => (EMPTY)
            elif state.current_input_state() in [InputState.MASHING, InputState.MASHING_SPACE]:
                state.letters = []
                state.words = []
                state.transition(InputState.EMPTY)
            # Transition: (K_RETURN TYPING|TYPING_SPACE) => (EMPTY)
            else:
                if state.current_input_state() == InputState.TYPING:
                    word = self.words.recognize(state.letters)
                    self.speech.say(word)
                    state.words.append(word)
                # Only accept into history if there are no mashed words.
                if not InputState.MASHING_SPACE in state.input_state_stack:
                    state.history.append(' '.join(state.words))
                    state.history_state_stacks.append(state.input_state_stack)
                state.letters = []
                state.words = []
                state.transition(InputState.EMPTY)


    def run(self):
        while True:
            self.handle_events()
            self.display.refresh(self.state)
            self.time.tick(self.state)


def speak(word):
    os.system('echo {} | espeak -ven+f3 -p80 -k20 -s120'.format(word.lower()))

if __name__ == '__main__':
    Game().run()
