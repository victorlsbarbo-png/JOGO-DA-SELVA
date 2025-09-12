# Plataforma em PgZero - Jogo de plataforma com física, colisões e áudio
# Controles: setas para mover, Espaco para pular, Mouse para menu
# Resolucao: 960x540

import math
import random
from pygame import Rect
from pgzero.builtins import Actor

# Configuracoes do jogo
TITLE = "PLATAFORMA NA SELVA"
WIDTH = 960
HEIGHT = 540

# Estados
SCENE_MENU = "menu"
SCENE_GAME = "game"

# Configuracoes de audio
music_enabled = True
sfx_enabled = True
game_scene = SCENE_MENU
game_time = 0.0
music_started = False

# Cores
COLOR_BG = (30, 144, 255)
COLOR_PLATFORM = (90, 200, 120)
COLOR_PLAYER = (240, 200, 80)
COLOR_ENEMY = (230, 80, 100)
COLOR_UI = (230, 230, 230)
COLOR_UI_ACCENT = (160, 220, 255)

# Fisica
GRAVITY = 1800.0
MOVE_SPEED = 260.0
JUMP_SPEED = 640.0
MAX_FALL = 1200.0
STOMP_BOUNCE = -JUMP_SPEED * 0.6
STOMP_TOLERANCE = 20
PLAYER_SPAWN_POS = (60, HEIGHT - 100)
INVINCIBILITY_DURATION = 0.3
ENEMY_DEATH_DURATION = 0.25

# Imagem de fundo
background = Actor("background")
background.topleft = (0, 0)

# Botao do menu
class Button:
    def __init__(self, text, rect):
        self.text = text
        self.rect = Rect(rect)
        self.hover = False

    def draw(self):
        fill = COLOR_UI_ACCENT if self.hover else COLOR_UI
        screen.draw.filled_rect(self.rect, fill)
        screen.draw.rect(self.rect, COLOR_BG)
        screen.draw.text(self.text, center=self.rect.center, fontsize=28, color=COLOR_BG)

    def update_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)

    def clicked(self, pos):
        return self.rect.collidepoint(pos)

# Animações (estrutura para sprites)
class AnimationPlayer:
    def __init__(self, frames_idle=None, frames_run=None, frames_jump=None, frame_duration=0.1):
        self.frames_idle = frames_idle or []
        self.frames_run = frames_run or []
        self.frames_jump = frames_jump or []
        self.timer = 0.0
        self.index = 0
        self.current_animation = self.frames_idle
        self.frame_duration = frame_duration

    def select_animation(self, is_on_ground, is_moving, vel_y):
        """Seleciona a animação correta com base no estado do jogador."""
        new_animation = None
        if is_on_ground:
            # No chão: alternar entre correr e parado.
            new_animation = self.frames_run if is_moving else self.frames_idle
        else:
            # No ar: usar animação de pulo apenas ao subir.
            if vel_y < 0:
                new_animation = self.frames_jump
        
        # Troca a animação apenas se a nova for diferente da atual.
        if new_animation and self.current_animation != new_animation:
            self.current_animation = new_animation
            self.index = 0
            self.timer = 0.0

    def update(self, dt):
        if not self.current_animation:
            return
        self.timer += dt
        # Garante que a animação avance no ritmo correto
        while self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.index = (self.index + 1) % len(self.current_animation)

    def get_frame_name(self):
        if not self.current_animation:
            return None
        return self.current_animation[self.index]

# Entidade base
class Entity:
    def __init__(self, x, y, w, h):
        self.rect = Rect(x, y, w, h)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.facing = 1

    def apply_gravity(self, dt):
        self.vel_y = min(self.vel_y + GRAVITY * dt, MAX_FALL)

    def move_and_collide(self, platforms, dt):
        # Movimento horizontal
        self.rect.x += int(self.vel_x * dt)
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_x > 0:
                    self.rect.right = p.rect.left
                elif self.vel_x < 0:
                    self.rect.left = p.rect.right
                self.vel_x = 0.0

        # Movimento vertical
        self.rect.y += int(self.vel_y * dt)
        self.on_ground = False # Assume que está no ar
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_y > 0: # Caindo sobre a plataforma
                    self.rect.bottom = p.rect.top
                    self.on_ground = True
                    self.vel_y = 0.0
                elif self.vel_y < 0: # Batendo a cabeça na plataforma
                    self.rect.top = p.rect.bottom
                    self.vel_y = 0.0

# Player
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 54)
        self.lives = 3
        self.jump_buffer_timer = 0.0  # Adiciona um buffer para o pulo
        self.invincibility_timer = 0.0
        self.can_double_jump = False
        self.anim = AnimationPlayer(
            frames_idle=["player_idle_1", "player_idle_2"],
            frames_run=["player_run_1", "player_run_2"],
            frames_jump=["player_jump_1"],
            frame_duration=0.25
        )
        self.actor = Actor("player_idle_1") # Define a imagem inicial
        # Ajusta o tamanho do actor para corresponder ao da caixa de colisão
        self.actor.width = 40
        self.actor.height = 54

    def reset_state(self):
        """Reseta a posição e velocidade do jogador ao morrer ou reiniciar."""
        self.rect.topleft = PLAYER_SPAWN_POS
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = True
        self.invincibility_timer = INVINCIBILITY_DURATION

    def handle_input(self, keyboard):
        move = 0
        if keyboard.left:
            move -= 1
        if keyboard.right:
            move += 1
        self.vel_x = move * MOVE_SPEED
        if move != 0:
            self.facing = 1 if move > 0 else -1

    def try_jump(self):
        # Com o buffer, esta função apenas registra a intenção de pular.
        # A lógica real do pulo acontece no método update().
        self.jump_buffer_timer = 0.15  # Buffer de 0.15 segundos

    def update(self, platforms, keyboard, dt):
        # Decrementa o timer do buffer de pulo a cada quadro
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt

        if self.invincibility_timer > 0:
            self.invincibility_timer -= dt

        self.handle_input(keyboard)
        self.apply_gravity(dt)
        self.move_and_collide(platforms, dt)

        # Lógica de pulo 
        # Pulo normal 
        if self.jump_buffer_timer > 0 and self.on_ground:
            self.vel_y = -JUMP_SPEED
            self.can_double_jump = True
            play_sfx_safe("jump")
            self.jump_buffer_timer = 0.0  
        # Pulo duplo
        elif self.jump_buffer_timer > 0 and self.can_double_jump:
            self.vel_y = -JUMP_SPEED * 0.9
            self.can_double_jump = False
            play_sfx_safe("jump")
            self.jump_buffer_timer = 0.0  

        # Atualiza a animação
        is_moving = self.vel_x != 0
        self.anim.select_animation(self.on_ground, is_moving, self.vel_y)
        self.anim.update(dt)

    def process_enemy_collisions(self, enemies):
        """Verifica e processa colisões com inimigos, retornando o estado do jogo."""
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect) and not enemy.is_dead:
                # Pisão no inimigo
                is_stomping = self.vel_y > 0 and self.rect.bottom - enemy.rect.top < STOMP_TOLERANCE
                if is_stomping:
                    play_sfx_safe("hit_enemy")
                    self.vel_y = STOMP_BOUNCE
                    enemy.stomp()
            
                elif self.invincibility_timer <= 0:
                    play_sfx_safe("player_hurt")
                    self.lives -= 1
                    self.invincibility_timer = INVINCIBILITY_DURATION
                    return "reset_level" if self.lives > 0 else "game_over"
        return "none"
 
    def draw(self):
        frame_name = self.anim.get_frame_name()
        if frame_name:
            # Atualiza a imagem e a posição do personagem
            self.actor.image = frame_name
            self.actor.midbottom = self.rect.midbottom

            # MELHORIA: Vira o sprite se o jogador estiver virado para a esquerda
            self.actor.flip_x = self.facing == -1
            self.actor.draw()

        else:
            # Se não houver sprites, desenha o placeholder
            screen.draw.filled_rect(self.rect, COLOR_PLAYER)

# Inimigo
class Enemy(Entity):
    def __init__(self, x, y, patrol_left, patrol_right, speed=120.0):
        super().__init__(x, y, 14, 14)
        self.patrol_left = patrol_left
        self.patrol_right = patrol_right
        self.speed = speed
        self.vel_x = speed
        self.is_dead = False
        self.death_timer = 0.0
        self.anim = AnimationPlayer(frames_run=["bee_a", "bee_b"], frame_duration=0.2)
        self.anim.current_animation = self.anim.frames_run # Força a animação de "correr" desde o início
        self.actor = Actor("bee_a") # Cria o inimigo uma única vez
        self.actor.width = 14
        self.actor.height = 14

    def stomp(self):
        """Marca o inimigo como morto e inicia o timer de desaparecimento."""
        if not self.is_dead:
            self.is_dead = True
            self.death_timer = ENEMY_DEATH_DURATION

    def update(self, platforms, dt):
        if self.is_dead:
            self.death_timer -= dt # Apenas o timer é atualizado
            return
            
        # Patrulha
        if self.rect.x <= self.patrol_left:
            self.vel_x = abs(self.speed)
            self.facing = 1
        elif self.rect.x + self.rect.w >= self.patrol_right:
            self.vel_x = -abs(self.speed)
            self.facing = -1

        # Movimento horizontal (sem física de gravidade/colisão com plataformas)
        self.rect.x += int(self.vel_x * dt)
        self.anim.update(dt)

    def draw(self):
        if self.is_dead:
            # Quando o inimigo morre, não reaparece
            return


        frame_name = self.anim.get_frame_name()
        if frame_name:
            # Atualiza a imagem e a posição 
            self.actor.image = frame_name
            self.actor.center = self.rect.center

            # MELHORIA: Vira o sprite do inimigo de acordo com a direção
            self.actor.flip_x = self.facing == -1
            self.actor.draw()

        else:
            screen.draw.filled_rect(self.rect, COLOR_ENEMY)

# Plataforma
class Platform:
    def __init__(self, x, y, w, h):
        self.rect = Rect(x, y, w, h)

    def draw(self):
        screen.draw.filled_rect(self.rect, COLOR_PLATFORM)

# Variáveis globais do jogo
player = None
platforms = []
enemies = []

# UI
buttons = [
    Button("Come\u00e7ar", (WIDTH // 2 - 120, 190, 240, 48)),
    Button("M\u00fasica: ON", (WIDTH // 2 - 120, 250, 240, 48)),
    Button("Sons: ON", (WIDTH // 2 - 120, 310, 240, 48)),
    Button("Sair", (WIDTH // 2 - 120, 370, 240, 48)),
]

game_buttons = [
    Button("Sair", (WIDTH - 120, 10, 100, 35)),
    Button("Reiniciar", (WIDTH - 120, 50, 100, 35)),
]

def play_sfx_safe(name):
    global sfx_enabled
    if not sfx_enabled:
        return
    try:
        getattr(sounds, name).play()
    except Exception as e:
        

# Funcao para resetar os inimigos
def reset_enemies():
    global enemies
    enemies = [
        Enemy(120, HEIGHT - 184, 80, 260, 70),
        Enemy(360, HEIGHT - 274, 340, 480, 90),
        Enemy(620, HEIGHT - 364, 600, 800, 80),
        Enemy(780, HEIGHT - 164, 760, 900, 85),
    ]

# Funcoes do jogo
def start_game():
    global game_scene, player, platforms, enemies, game_time
    platforms = [
        Platform(0, HEIGHT - 40, WIDTH, 40),
        Platform(80, HEIGHT - 140, 180, 18),
        Platform(340, HEIGHT - 230, 160, 18),
        Platform(600, HEIGHT - 320, 200, 18),
        Platform(760, HEIGHT - 120, 140, 18),
    ]
    player = Player(PLAYER_SPAWN_POS[0], PLAYER_SPAWN_POS[1])
    reset_enemies()
    game_scene = SCENE_GAME
    game_time = 0.0

def back_to_menu():
    global game_scene
    game_scene = SCENE_MENU

# Hooks do PgZero
def on_key_down(key):
    if game_scene == SCENE_GAME and key == keys.SPACE:
        player.try_jump()

def on_mouse_move(pos):
    if game_scene == SCENE_MENU:
        for b in buttons:
            b.update_hover(pos)
    elif game_scene == SCENE_GAME:
        for b in game_buttons:
            b.update_hover(pos)

def on_mouse_down(pos):
    global music_enabled, sfx_enabled
    if game_scene == SCENE_MENU:
        if buttons[0].clicked(pos):
            start_game()
        elif buttons[1].clicked(pos):
            music_enabled = not music_enabled
            buttons[1].text = f"M\u00fasica: {'ON' if music_enabled else 'OFF'}"
            if music_enabled:
                try:
                    # Toca a música em loop do arquivo music
                    music.play("music")
                except Exception as e:
                    
            else:
                music.stop()
        elif buttons[2].clicked(pos):
            sfx_enabled = not sfx_enabled
            buttons[2].text = f"Sons: {'ON' if sfx_enabled else 'OFF'}"
        elif buttons[3].clicked(pos):
            raise SystemExit
    elif game_scene == SCENE_GAME:
        if game_buttons[0].clicked(pos):
            back_to_menu()
        elif game_buttons[1].clicked(pos):
            start_game()

def update(dt):
    global game_time, music_started

    # --- LÓGICA DA MÚSICA DE FUNDO ---
    # Garante que a música comece a tocar uma vez no início do jogo.
    # O controle de ligar/desligar é feito no menu.
    if not music_started:
        if music_enabled:
            try:
                music.play("music")
            except Exception as e:
        music_started = True

    game_time += dt
    if game_scene == SCENE_MENU:
        return

    # Atualizar entidades
    player.update(platforms, keyboard, dt)
    for e in enemies:
        e.update(platforms, dt)

    # --- LÓGICA DE COLISÃO E ESTADO DO JOGO ---
    # 1. Colisão com inimigos
    collision_result = player.process_enemy_collisions(enemies)

    # 2. Verificação de queda do mapa (se não houve outra colisão)
    if player.rect.top > HEIGHT + 100 and collision_result == "none" and player.invincibility_timer <= 0:
        play_sfx_safe("player_hurt")
        player.lives -= 1
        collision_result = "reset_level" if player.lives > 0 else "game_over"

    # 3. Reação ao resultado das colisões ou quedas
    if collision_result == "reset_level":
        reset_enemies()
        player.reset_state()
        game_time = 0.0
    elif collision_result == "game_over":
        back_to_menu()

    # Remove inimigos cujo timer de morte já expirou
    enemies[:] = [e for e in enemies if not (e.is_dead and e.death_timer <= 0)]

def draw():
    background.draw()

    if game_scene == SCENE_MENU:
        screen.draw.text(TITLE, center=(WIDTH // 2, 110), fontsize=48, color=COLOR_UI_ACCENT)
        for b in buttons:
            b.draw()
        screen.draw.text("Setas para mover, Espaço para pular", center=(WIDTH // 2, HEIGHT - 40), fontsize=24, color=COLOR_UI_ACCENT)
        return

    # Desenhar jogo
    for p in platforms:
        p.draw()
    for e in enemies:
        e.draw()
    player.draw()

    # UI do jogo
    screen.draw.text("Esc para Menu", topright=(WIDTH - 14, 90), fontsize=22, color=COLOR_UI_ACCENT)
    screen.draw.text(f"Inimigos: {len(enemies)}", topleft=(10, 10), fontsize=22, color=COLOR_UI_ACCENT)
    screen.draw.text(f"Vidas: {player.lives}", topleft=(10, 34), fontsize=22, color=COLOR_UI_ACCENT)
    
    for b in game_buttons:
        b.draw()

def on_key_up(key):
    if key == keys.ESCAPE:
        back_to_menu()