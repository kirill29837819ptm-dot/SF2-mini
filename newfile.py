import pygame, sys, time, json, os, math

# ================= INIT =================
pygame.init()
screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
clock = pygame.time.Clock()

# ================= COLORS =================
WHITE=(255,255,255)
BLACK=(0,0,0)
GRAY=(40,40,40)
RED=(200,60,60)
BLUE=(80,140,255)
YELLOW=(255,255,0)
BROWN=(139,69,19)

# ================= GROUND =================
GROUND_Y = int(HEIGHT * 0.78)
GROUND_HEIGHT = HEIGHT - GROUND_Y

def draw_ground():
    pygame.draw.rect(screen, BLACK, (0, GROUND_Y, WIDTH, GROUND_HEIGHT))

# ================= FONTS =================
font_big = pygame.font.SysFont("arial",54,True)
font_mid = pygame.font.SysFont("arial",32)
font_small = pygame.font.SysFont("arial",24)

# ================= ASSETS =================
def load_bg(path):
    try:
        img = pygame.image.load(path).convert()
        return pygame.transform.scale(img,(WIDTH,HEIGHT))
    except:
        return None

def load_icon(path,size):
    try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img,size)
    except:
        return None

BG_LOADING = load_bg("assets/backgrounds/loading.png")
BG_TRAIN = load_bg("assets/backgrounds/training.png")
BG_MAP   = load_bg("assets/backgrounds/map.png")
BG_FIGHT = load_bg("assets/backgrounds/fight.png")
BG_SURV  = load_bg("assets/backgrounds/survival.png")

ENEMY_ICON = load_icon("assets/icons/enemy_circle.png",(80,80))
SURV_AVATAR = load_icon("assets/avatars/survival_enemy.png",(64,64))

# ================= SAVE =================
SAVE_FILE="save.json"
def load_save():
    base={"coins":100,"weapon":"fists","owned":["fists"]}
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE,"r") as f:
                data=json.load(f)
            for k in base:
                if k not in data: data[k]=base[k]
            return data
        except:
            return base
    return base

save=load_save()
def save_game():
    with open(SAVE_FILE,"w") as f:
        json.dump(save,f)

# ================= WEAPONS =================
WEAPONS={
    "fists":{"name":"Кулаки","dmg":5,"price":0},
    "dagger":{"name":"Кинжал","dmg":8,"price":50},
    "sword":{"name":"Меч","dmg":12,"price":100},
}

# ================= UI =================
BTN_MENU = pygame.Rect(20,20,50,40)
BTN_LIGHT = pygame.Rect(WIDTH-220,HEIGHT-160,60,60)
BTN_HEAVY = pygame.Rect(WIDTH-140,HEIGHT-200,70,70)

MENU_MAP_BTN  = pygame.Rect(WIDTH//2-120,260,240,70)
MENU_SHOP_BTN = pygame.Rect(WIDTH//2-120,360,240,70)

MAP_ENEMY_BTN = pygame.Rect(WIDTH//2-40,HEIGHT//2-40,80,80)
MAP_SURV_BTN  = pygame.Rect(WIDTH//2+120,HEIGHT//2-40,80,80)

# ================= JOYSTICK =================
JOY_CENTER=(int(WIDTH*0.15),int(HEIGHT*0.8))
JOY_RADIUS=60
joy_active=False
joy_dx=0
joy_dy=0

# ================= ENTITIES =================
class Fighter:
    def __init__(self,x,color,ai=False):
        self.start_x=x
        self.x=x
        self.y=GROUND_Y-100
        self.vy=0
        self.hp=100
        self.max_hp=100
        self.color=color
        self.on_ground=True
        self.attack_cd=0
        self.attack_anim=0
        self.ai=ai
        self.ai_timer=0
        self.dir=1
        self.dmg_bonus=0

    def reset(self):
        self.x=self.start_x
        self.y=GROUND_Y-100
        self.vy=0
        self.hp=self.max_hp
        self.attack_cd=0
        self.ai_timer=0

    def face(self,target):
        self.dir = 1 if target.x>self.x else -1

    def attack(self):
        if self.attack_cd==0:
            self.attack_cd=30
            self.attack_anim=10
            return WEAPONS[save["weapon"]]["dmg"] + self.dmg_bonus
        return 0

    def jump(self):
        if self.on_ground:
            self.vy=-18
            self.on_ground=False

    def update(self,target=None):
        if not self.on_ground:
            self.vy+=1
            self.y+=self.vy
            if self.y>=GROUND_Y-100:
                self.y=GROUND_Y-100
                self.vy=0
                self.on_ground=True

        if self.attack_cd>0: self.attack_cd-=1
        if self.attack_anim>0: self.attack_anim-=1

        if self.ai and target and round_active:
            self.face(target)
            self.x+=self.dir*1.4
            self.ai_timer+=1
            if self.ai_timer>90 and abs(self.x-target.x)<80:
                self.ai_timer=0
                dmg=max(1,self.attack()-3)
                target.hp=max(0,target.hp-dmg)

class Bag:
    def __init__(self):
        self.x=WIDTH//2-20
        self.y=GROUND_Y-100
        self.swing=0
        self.hit_anim=0
    def hit(self):
        self.hit_anim=6
        self.swing += 20 if player.x<self.x else -20
    def update(self):
        self.swing*=0.9
        if self.hit_anim>0: self.hit_anim-=1

player=Fighter(WIDTH*0.25,WHITE)
enemy=Fighter(WIDTH*0.7,RED,ai=True)
bag=Bag()

# ================= STATES =================
LOADING="loading"
MENU="menu"
MAP="map"
TRAIN="train"
FIGHT="fight"
SURVIVAL="survival"
ROUND_INTRO="round_intro"
PREVIEW = "preview"
SHOP = "shop"

state = LOADING  # начальное состояние

preview_data = {}
shop_selected = 0
round_num=1
round_timer=0
round_active=False

SHOP_SECTIONS = ["Оружие","Нагрудник","Шлем","Сюрикены","Магия"]

# ================= DRAW =================
def draw_menu_btn():
    pygame.draw.rect(screen,WHITE, BTN_MENU,2)
    for i in range(3):
        pygame.draw.line(screen,WHITE,(30,30+i*10),(60,30+i*10),2)

def draw_joystick():
    pygame.draw.circle(screen,WHITE,JOY_CENTER,JOY_RADIUS,2)
    pygame.draw.circle(screen,BLUE,(JOY_CENTER[0]+int(joy_dx*30),JOY_CENTER[1]+int(joy_dy*30)),18)

def draw_buttons():
    pygame.draw.ellipse(screen,WHITE,BTN_LIGHT,2)
    pygame.draw.ellipse(screen,RED,BTN_HEAVY,2)
    screen.blit(font_small.render("A",True,WHITE),(BTN_LIGHT.x+22,BTN_LIGHT.y+18))
    screen.blit(font_small.render("B",True,WHITE),(BTN_HEAVY.x+25,BTN_HEAVY.y+20))

def draw_fighter(f):
    pygame.draw.rect(screen,f.color,(f.x,f.y,40,100))
    if f.attack_anim>0:
        pygame.draw.rect(screen,YELLOW,(f.x+f.dir*40,f.y+30,f.dir*30,20))

def get_difficulty(enemy):
    power = enemy.max_hp + enemy.dmg_bonus*5
    if power < 110: return "Легко"
    elif power < 130: return "Средне"
    elif power < 150: return "Сложно"
    else: return "Невозможно"

# ================= SCREENS =================
def screen_loading():
    if BG_LOADING: screen.blit(BG_LOADING,(0,0))
    else: screen.fill(BLACK)
    t = font_big.render("SF2 MINI", True, WHITE)
    screen.blit(t, (WIDTH - t.get_width() - 30, HEIGHT - t.get_height() - 30))

def screen_menu():
    screen.fill(GRAY)
    draw_menu_btn()
    pygame.draw.rect(screen,WHITE,MENU_MAP_BTN,2)
    screen.blit(font_mid.render("КАРТА",True,WHITE),(MENU_MAP_BTN.x+70,MENU_MAP_BTN.y+20))
    pygame.draw.rect(screen,WHITE,MENU_SHOP_BTN,2)
    screen.blit(font_mid.render("МАГАЗИН",True,WHITE),(MENU_SHOP_BTN.x+50,MENU_SHOP_BTN.y+20))

def screen_map():
    if BG_MAP: screen.blit(BG_MAP,(0,0))
    else: screen.fill(BLACK)
    draw_menu_btn()
    pygame.draw.circle(screen,RED,MAP_ENEMY_BTN.center,42,3)
    pygame.draw.circle(screen,BLUE,MAP_SURV_BTN.center,42,3)
    if ENEMY_ICON: screen.blit(ENEMY_ICON,MAP_ENEMY_BTN.topleft)
    if SURV_AVATAR: screen.blit(SURV_AVATAR,(MAP_SURV_BTN.x+8,MAP_SURV_BTN.y+8))
    screen.blit(font_small.render("БОЙ",True,WHITE),(MAP_ENEMY_BTN.x+20,MAP_ENEMY_BTN.bottom+8))
    screen.blit(font_small.render("ВЫЖИВАНИЕ",True,WHITE),(MAP_SURV_BTN.x-30,MAP_SURV_BTN.bottom+8))

def screen_preview():
    screen.fill(GRAY)
    draw_menu_btn()
    pygame.draw.rect(screen, BLACK, (WIDTH//2-200, HEIGHT//2-150, 400, 300))
    pygame.draw.rect(screen, WHITE, (WIDTH//2-200, HEIGHT//2-150, 400, 300), 3)
    screen.blit(font_big.render("Предпросмотр", True, WHITE), (WIDTH//2-130, HEIGHT//2-140))
    screen.blit(font_mid.render(f"Награда: {preview_data.get('coins',0)} монет", True, WHITE), (WIDTH//2-180, HEIGHT//2-80))
    screen.blit(font_mid.render(f"Сложность: {preview_data.get('difficulty','?')}", True, WHITE), (WIDTH//2-180, HEIGHT//2-40))
    btn_start = pygame.Rect(WIDTH//2-180, HEIGHT//2+60, 160, 50)
    btn_back  = pygame.Rect(WIDTH//2+20, HEIGHT//2+60, 160, 50)
    pygame.draw.rect(screen, BLUE, btn_start)
    pygame.draw.rect(screen, RED, btn_back)
    screen.blit(font_small.render("БИТВА", True, WHITE), (btn_start.x+40, btn_start.y+15))
    screen.blit(font_small.render("НАЗАД", True, WHITE), (btn_back.x+40, btn_back.y+15))
    return btn_start, btn_back

def screen_round_intro():
    overlay=pygame.Surface((WIDTH,HEIGHT))
    overlay.set_alpha(180)
    overlay.fill(BLACK)
    screen.blit(overlay,(0,0))
    t=font_big.render(f"РАУНД {round_num}",True,WHITE)
    screen.blit(t,(WIDTH//2-t.get_width()//2,HEIGHT//2-40))

def screen_train():
    if BG_TRAIN: screen.blit(BG_TRAIN,(0,0))
    else: screen.fill(GRAY)
    draw_ground()
    draw_menu_btn()
    pygame.draw.line(screen,BROWN,(bag.x+20,bag.y-60),(bag.x+20+bag.swing,bag.y),3)
    pygame.draw.rect(screen, RED if bag.hit_anim==0 else YELLOW, (bag.x + bag.swing, bag.y, 40, 100))
    draw_fighter(player)
    draw_joystick()
    draw_buttons()

def screen_fight():
    if state==SURVIVAL and BG_SURV:
        screen.blit(BG_SURV,(0,0))
    elif BG_FIGHT:
        screen.blit(BG_FIGHT,(0,0))
    else:
        screen.fill(GRAY)
    draw_ground()
    draw_menu_btn()
    pygame.draw.rect(screen,RED,(40,20,player.hp*2,12))
    pygame.draw.rect(screen,RED,(WIDTH-260,20,enemy.hp*2,12))
    draw_fighter(player)
    draw_fighter(enemy)
    draw_joystick()
    draw_buttons()

def screen_shop():
    screen.fill(GRAY)
    draw_menu_btn()
    # Разделы магазина
    for i, section in enumerate(SHOP_SECTIONS):
        rect = pygame.Rect(100 + i*150, 100, 140, 50)
        pygame.draw.rect(screen, WHITE if i==shop_selected else BLACK, rect, 2)
        screen.blit(font_small.render(section, True, WHITE), (rect.x+10, rect.y+15))
    # Простой показ оружия
    if SHOP_SECTIONS[shop_selected]=="Оружие":
        for i,(key,item) in enumerate(WEAPONS.items()):
            rect = pygame.Rect(100 + i*150, 200, 140, 50)
            pygame.draw.rect(screen, WHITE if key in save["owned"] else BLACK, rect, 2)
            screen.blit(font_small.render(f"{item['name']} ({item['price']}💰)", True, WHITE), (rect.x+5, rect.y+15))

# ================= MAIN LOOP =================
running=True
load_time=time.time()

while running:
    for e in pygame.event.get():
        if e.type==pygame.QUIT:
            save_game()
            pygame.quit()
            sys.exit()
        if e.type==pygame.MOUSEBUTTONDOWN:
            x,y=e.pos
            # Меню
            if BTN_MENU.collidepoint(x,y):
                state=MENU
            if state==MENU:
                if MENU_MAP_BTN.collidepoint(x,y):
                    state=MAP
                elif MENU_SHOP_BTN.collidepoint(x,y):
                    state=SHOP
            elif state==MAP:
                if MAP_ENEMY_BTN.collidepoint(x,y):
                    preview_data = {"coins": 20 + enemy.dmg_bonus*5, "difficulty": get_difficulty(enemy), "enemy": enemy}
                    state = PREVIEW
                elif MAP_SURV_BTN.collidepoint(x,y):
                    round_num=1
                    round_active=False
                    player.reset()
                    enemy.reset()
                    state=ROUND_INTRO
                    round_timer=time.time()
            elif state==PREVIEW:
                btn_start, btn_back = screen_preview()
                if btn_start.collidepoint(x,y):
                    preview_data["enemy"].reset()
                    player.reset()
                    round_active = True
                    state = FIGHT
                elif btn_back.collidepoint(x,y):
                    state = MAP
            elif state==SHOP:
                # Выбор раздела
                for i, section in enumerate(SHOP_SECTIONS):
                    rect = pygame.Rect(100 + i*150, 100, 140, 50)
                    if rect.collidepoint(x,y):
                        shop_selected = i
                # Покупка оружия
                if SHOP_SECTIONS[shop_selected]=="Оружие":
                    for i,(key,item) in enumerate(WEAPONS.items()):
                        rect = pygame.Rect(100 + i*150, 200, 140, 50)
                        if rect.collidepoint(x,y):
                            if key not in save["owned"] and save["coins"]>=item["price"]:
                                save["coins"]-=item["price"]
                                save["owned"].append(key)
                            elif key in save["owned"]:
                                save["weapon"]=key
            elif state in [TRAIN,FIGHT,SURVIVAL]:
                if BTN_LIGHT.collidepoint(x,y):
                    dmg=player.attack()
                    if state==TRAIN and abs(player.x-bag.x)<80:
                        bag.hit()
                    if abs(player.x-enemy.x)<80:
                        enemy.hp=max(0,enemy.hp-dmg)
            if (x-JOY_CENTER[0])**2+(y-JOY_CENTER[1])**2<JOY_RADIUS**2:
                joy_active=True
        if e.type==pygame.MOUSEBUTTONUP:
            joy_active=False
            joy_dx=joy_dy=0
        if e.type==pygame.MOUSEMOTION and joy_active:
            joy_dx=max(-1,min(1,(e.pos[0]-JOY_CENTER[0])/JOY_RADIUS))
            joy_dy=max(-1,min(1,(e.pos[1]-JOY_CENTER[1])/JOY_RADIUS))

    # ===== Логика игры =====
    if state in [TRAIN,FIGHT,SURVIVAL]:
        player.x += joy_dx*6
        player.x = max(0, min(WIDTH-40, player.x))
        if joy_dy < -0.6: player.jump()
        player.update(enemy)
        enemy.update(player)
        bag.update()
        if player.hp<=0:
            round_active=False
            save_game()
            state=MAP
            player.reset()
            enemy.reset()
        elif state==FIGHT and enemy.hp<=0:
            round_active=False
            save_game()
            state=MAP
            player.reset()
            enemy.reset()
        elif state==SURVIVAL and enemy.hp<=0:
            round_active=False
            round_num+=1
            save["coins"]+=20
            enemy.reset()
            enemy.dmg_bonus=round_num//2
            state=ROUND_INTRO
            round_timer=time.time()

    # ===== Отрисовка =====
    if state==ROUND_INTRO:
        screen_fight()
        screen_round_intro()
        if time.time()-round_timer>2:
            round_active=True
            state=SURVIVAL
    elif state==LOADING:
        screen_loading()
        if time.time()-load_time>2:
            state=TRAIN
    elif state==MENU:
        screen_menu()
    elif state==MAP:
        screen_map()
    elif state==PREVIEW:
        screen_preview()
    elif state==SHOP:
        screen_shop()
    elif state==TRAIN:
        screen_train()
    elif state in [FIGHT,SURVIVAL]:
        screen_fight()

    pygame.display.flip()
    clock.tick(60)