import os, pygame, sys
from multiprocessing import Pool
from pygame.locals import *

# Configuration
FPS = 30
MAX_LETTERS = 20
FONT_SIZE = 150
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Initialization
pygame.init()
pygame.display.set_caption('MASH!')

DISPLAYSURF = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
FPSCLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont(pygame.font.get_default_font(), FONT_SIZE)
ALLOWED_PUNCTUATION = [K_SPACE, K_PERIOD, K_RETURN]
ALLOWED_WORDS = []
with open('words.txt', 'r') as f:
    ALLOWED_WORDS = set(map(lambda x: x.strip().upper(), list(f)))
POOL = Pool(processes=1)

# State
LETTERS = ['M','A','S','H','!',' ',' ',' ',' ',' ']
WORDS = []

def speak(word):
    os.system('echo {} | festival --tts'.format(word))

def recognizeWord():
    word_letters = []
    word = ''
    for l in LETTERS:
        if l == ' ' or l == '.':
            word = ''.join(word_letters)
            word_letters = []
        else:
            word_letters.append(l)
    if word in ALLOWED_WORDS:
        WORDS.append(word)
        POOL.apply_async(speak, [word])

def handleKeyDown(key):
    global LETTERS
    if (key >= K_a and key <= K_z) or key in ALLOWED_PUNCTUATION:
        if key == K_RETURN:
            # Return clears the input buffer
            LETTERS.append(' ')
            recognizeWord()
            LETTERS = []
        elif key == K_SPACE:
            # Only one space in a row
            if len(LETTERS) > 0 and LETTERS[len(LETTERS)-1] != chr(K_SPACE):
                LETTERS.append(chr(key))
                recognizeWord()
        else:
            # Everything else appends capitalized
            LETTERS.append(chr(key).capitalize())
        if len(LETTERS) > MAX_LETTERS:
            LETTERS = LETTERS[1:]

def handleEvents():
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == KEYDOWN:
            key = event.key
            handleKeyDown(key)

def refreshScreen():
    DISPLAYSURF.fill([0,0,0])
    l = FONT.render(''.join(LETTERS), 0, [255,255,255])
    w = l.get_width()
    DISPLAYSURF.blit(l, [SCREEN_WIDTH - w - 25, SCREEN_HEIGHT - 110])
    word_offset = SCREEN_HEIGHT - 250
    for w in reversed(WORDS):
        if word_offset < -100:
            continue
        words = FONT.render(w, 0, [255,255,255])
        DISPLAYSURF.blit(words, [0,word_offset])
        word_offset -= 100
    pygame.display.flip()

while True: # main game loop
    handleEvents()
    refreshScreen()
    FPSCLOCK.tick(FPS)
