import pygame, sys
from pygame.locals import *

# Configuration
FPS = 30
MAX_LETTERS = 12
FONT_SIZE = 150
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Initialization
pygame.init()
pygame.display.set_caption('MASH!')

DISPLAYSURF = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
FPSCLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont(pygame.font.get_default_font(), FONT_SIZE)
ALLOWED_PUNCTUATION = [K_SPACE, K_PERIOD]

# State
LETTERS = ['M','A','S','H','!',' ',' ',' ',' ',' ']
WORDS = []

def handleKeyDown(key):
    global LETTERS
    if (key >= K_a and key <= K_z) or key in ALLOWED_PUNCTUATION:
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
    DISPLAYSURF.blit(l, [SCREEN_WIDTH - w - 25, 200])
    pygame.display.flip()

while True: # main game loop
    handleEvents()
    refreshScreen()
    FPSCLOCK.tick(FPS)
