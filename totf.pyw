from math import sqrt
from textwrap import wrap
from random import choice
import shelve
import tcod


# ######################################################################
# Global Game Settings
# ######################################################################
# Windows Controls
fullscreen = False
screen_width = 60  # characters wide
screen_height = 40  # characters tall
limit_fps = 20  # 20 frames-per-second maximum
level_screen_width = 40
character_screen_width = 30
#Map
##################################
map_width = 60
map_height = 33
room_max_size = 8
room_min_size = 6
max_rooms = 40

# BSP map:
depth = 10
min_size = 5
full_rooms = False

inventory_width = 40

#Field of view
###############################
fov_algo = 0
fov_light_walls = True
torch_radius = 8
# GUI
#######################################################################
bar_width = 17
panel_height = 7
panel_y = screen_height - panel_height

# Player mods
#######################################################################

level_up_base = 150
level_up_factor = 250

# Messages:
#######################################################################
msg_x = bar_width + 2
msg_width = screen_width - bar_width - 2
msg_height = panel_height - 1

def message(new_msg, color=tcod.white):
    new_msg_lines = wrap(new_msg, msg_width)
    for line in new_msg_lines:
        if len(game_msgs) == msg_height:
            del game_msgs[0]
        game_msgs.append((line, color))


# Game state
########################################################################################
game_state = 'playing'
player_action = None

# Classes
##############################################################################################
# Basic tile classes:
#################################################################################################
class Tile:
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked
        self.explored = False

        block_sight = blocked if block_sight is None else None
        self.block_sight = block_sight

class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) // 2
        center_y = (self.y1 + self.y2) // 2
        return (center_x, center_y)

    def intersect(self, other):
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1)

# Spellbook functions:
##############################################################################################################
def cast_firebite_spell():
    firebite_damage = 25
    firebite_range = 1
    firebite_cost = 0.5
    monster = closest_monster(firebite_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    else:
        if player.fighter.mp >= firebite_cost:
            message(f"{player.name} casts Firebite on {monster.name}! (Dam: {firebite_damage-monster.fighter.res})", tcod.yellow)
            monster.fighter.take_damage(firebite_damage - monster.fighter.base_res)
            player.fighter.mp -= firebite_cost

        else:
            message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
            return 'cancelled'

def cast_heal_spell():
    heal_spell_amount = 30
    heal_spell_cost = 1
    if player.fighter.mp >= heal_spell_cost:
        if player.fighter.hp == player.fighter.max_hp:
            message(f"{player.name} is already at full health!", tcod.green)
            return 'cancelled'
        message(f"{player.name} casts Healing!", tcod.light_violet)
        player.fighter.heal(heal_spell_amount)
        player.fighter.mp -= heal_spell_cost
    else:
        message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
        return 'cancelled'

def cast_great_heal_spell():
    heal_spell_amount = 65
    heal_spell_cost = 1
    if player.fighter.mp >= heal_spell_cost:
        if player.fighter.hp == player.fighter.max_hp:
            message(f"{player.name} is already at full health!", tcod.green)
            return 'cancelled'
        message(f"{player.name} casts Greater Healing!", tcod.light_violet)
        player.fighter.heal(heal_spell_amount)
        player.fighter.mp -= heal_spell_cost
    else:
        message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
        return 'cancelled'

def cast_lightning_storm_spell():
    lightning_storm_range = 3
    lightning_storm_damage = 60
    lightning_storm_cost = 3
    monster = closest_monster(lightning_storm_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    elif player.fighter.mp >= lightning_storm_cost and monster:
        for obj in objects:
            if tcod.map_is_in_fov(fov_map, obj.x, obj.y) and obj.fighter and obj != player:
                obj.fighter.take_damage(lightning_storm_damage - obj.fighter.base_res)
        message(f"{player.name} calls down Lightning Bolts to strike everything in sight!", tcod.light_blue)
        player.fighter.mp -= lightning_storm_cost
    else:
        message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
        return 'cancelled'

def cast_soul_rend_spell():
    rend_range = 5
    rend_cost = 0.50
    rend_effect = 20
    monster = closest_monster(rend_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    else:
        if player.fighter.mp >= rend_cost:
            monster.fighter.base_res -= rend_effect
            message(f"{monster.name} is struck by Soul Rend! {monster.name} lost {rend_effect} RES!", tcod.blue)
            player.fighter.mp -= rend_cost

        else:
            message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
            return 'cancelled'

def cast_mana_burn_spell():
    mb_range = 5
    mb_cost = 1
    mb_effect = 2
    monster = closest_monster(mb_range)
    if monster is None:
        message('No enemy in sight for that spell!.', tcod.red)
        return 'cancelled'
    else:
        if player.fighter.mp >= mb_cost:
            monster.fighter.base_max_mp -= mb_effect
            monster.fighter.mp -= mb_effect
            message(f"{monster.name} mana slowly burns away! {monster.name} lost {mb_effect} MP!", tcod.blue)
            player.fighter.mp -= mb_cost

        else:
            message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
            return 'cancelled'

def cast_ice_spike_spell():
    ice_spike_range = 4
    ice_spike_damage = 50
    ice_spike_cost = 1
    monster = closest_monster(ice_spike_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    else:
        if player.fighter.mp >= ice_spike_cost:
            message(f"{player.name} casts Ice Spike on {monster.name}! (Dam: {ice_spike_damage-monster.fighter.res})", tcod.yellow)
            monster.fighter.take_damage(ice_spike_damage - monster.fighter.base_res)
            player.fighter.mp -= ice_spike_cost

        else:
            message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
            return 'cancelled'

def cast_shocking_grasp_spell():
    shock_damage = 80
    shock_range = 2
    shock_cost = 1
    monster = closest_monster(shock_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    else:
        if player.fighter.mp >= shock_cost:
            message(f"{player.name} casts Shocking Grasp on {monster.name}! (Dam: {shock_damage-monster.fighter.res})", tcod.light_blue)
            monster.fighter.take_damage(shock_damage - monster.fighter.base_res)
            player.fighter.mp -= shock_cost

        else:
            message(f"{player.name} doesn't have enough MP to cast that spell!", tcod.red)
            return 'cancelled'

def sacrifice():
    hp_cost = 30
    mp_cost = 0.1
    reju_amount = 3.1

    if player.fighter.mp < mp_cost or player.fighter.hp <= hp_cost:
        message(f"{player.name} doesn't have enough MP or HP to use this item!", tcod.red)
        return 'cancelled'
    else:
        message(f"{player.name} offers own blood in exchange for more power!", tcod.azure)
        player.fighter.take_damage(hp_cost)
        player.fighter.mp -= mp_cost
        player.fighter.rejuvenate(reju_amount)

# Basic Object class for representing map objects:
######################################################################################################
class Object:
    def __init__(self, x, y, char, name, color, blocks=False, always_visible=False, fighter=None, ai=None, item=None, equipment=None):
        self.name = name
        self.blocks = blocks
        self.always_visible = always_visible
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.fighter = fighter
        self.equipment = equipment

        if self.fighter:
            self.fighter.owner = self

        self.ai = ai
        if self.ai:
            self.ai.owner = self
        self.item = item
        if self.item:
            self.item.owner = self

        if self.equipment:
            self.equipment.owner = self
            self.item = Item()
            self.item.owner = self


    def move(self, dx, dy):
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_astar(self, target):
        #Create a FOV map that has the dimensions of the map
        fov = tcod.map_new(map_width, map_height)

        #Scan the current map each turn and set all the walls as unwalkable
        for y1 in range(map_height):
            for x1 in range(map_width):
                tcod.map_set_properties(fov, x1, y1, not map[x1][y1].block_sight, not map[x1][y1].blocked)

        #Scan all the objects to see if there are objects that must be navigated around
        for obj in objects:
            if obj.blocks and obj != self and obj != target:
                tcod.map_set_properties(fov, obj.x, obj.y, True, False)

        # Allocate the AI path:
        my_path = tcod.path_new_using_map(fov, 1.41)

        #Compute the path between self's coordinates and the target's coordinates
        tcod.path_compute(my_path, self.x, self.y, target.x, target.y)

        #Check if the path exists, and in this case, also the path is shorter than 25 tiles
        if not tcod.path_is_empty(my_path) and tcod.path_size(my_path) < 25:
            #Find the next coordinates in the computed full path
            x, y = tcod.path_walk(my_path, True)
            if x or y:
                self.x = x
                self.y = y

        else:
            #Keep the old move function as a backup so that if there are no paths (for example another monster blocks a corridor)
            #it will still try to move towards the player (closer to the corridor opening)
            self.move_toward(target.x, target.y)

        tcod.path_delete(my_path)

    def move_toward(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = sqrt(dx ** 2 + dy ** 2)

        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return sqrt(dx ** 2 + dy ** 2)

    def distance(self, x, y):
        return sqrt((x - self.x) ** 2 + (y - self.y) ** 2)


    def send_to_back(self):
        global objects, monster
        objects.remove(self)
        objects.insert(0, self)

    def draw(self):
        if (tcod.map_is_in_fov(fov_map, self.x, self.y) or (self.always_visible and map[self.x][self.y].explored)):
            tcod.console_set_default_foreground(con, self.color)
            tcod.console_put_char(con, self.x, self.y, self.char, tcod.BKGND_NONE)

    def clear(self):
        if tcod.map_is_in_fov(fov_map, self.x, self.y):
            tcod.console_put_char_ex(con, self.x, self.y, '.', tcod.white, tcod.gray)

    def drink_fountain_life(self, fountain_of_life):
        heal_amount = 10

        if player.distance_to(fountain_of_life) > 1:
            return 'cancelled'

        elif player.distance_to(fountain_of_life) <= 1:
            player.fighter.heal(heal_amount)
            message(f"The Fountain's blessing heals {player.name}'s wounds!", tcod.green)


# Class for general items, such as potons and scrolls:
##########################################################################################################
class Item:
    def __init__(self, use_function=None, use_book_function=None):
        self.use_function = use_function
        self.use_book_function = use_book_function

    def pick_up(self):
        if len(inventory) >= 26:
            message(f"{player.name}'s inventory is full, cannot pick up {self.owner.name}.", tcod.red)
        else:
            inventory.append(self.owner)
            objects.remove(self.owner)
            message(f"{player.name} picks up {self.owner.name}!", tcod.green)

        equipment = self.owner.equipment
        if equipment and get_equipped_in_slot(equipment.slot) is None:
            equipment.equip()

    def use(self):
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return
        if self.use_function is None:
            message(f"The {self.owner.name} cannot be used.", tcod.red)
        else:
            if self.use_function() != 'cancelled':
                inventory.remove(self.owner) #destroy item after use

    def use_spellbook(self):
        if self.owner.equipment:
            self.owner.equipment.toggle_equip()
            return
        if self.use_book_function is None:
            message(f"The {self.owner.name} cannot be used.", tcod.red)
        else:
            if self.use_book_function() != 'cancelled':
                player.fighter.use_book_function

    def drop(self):
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message(f"{player.name} drops a {self.owner.name}.", tcod.yellow)
        if self.owner.equipment:
            self.owner.equipment.dequip()


# Equipment class, for weapons, armor and artifacts:
#########################################################################################################
class Equipment:
    def __init__(self, slot, power_bonus=0, defense_bonus=0, res_bonus=0, max_hp_bonus=0, max_mp_bonus=0):
        self.slot = slot
        self.is_equipped = False
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.res_bonus = res_bonus
        self.max_hp_bonus = max_hp_bonus
        self.max_mp_bonus = max_mp_bonus

    def toggle_equip(self):
        if self.is_equipped:
            self.dequip()
        else:
            self.equip()

    def equip(self):
        old_equipment = get_equipped_in_slot(self.slot)
        if old_equipment is not None:
            old_equipment.dequip()

        self.is_equipped = True
        message(f"Equipped {self.owner.name} on {self.slot}.", tcod.light_green)

    def dequip(self):
        if not self.is_equipped: return
        self.is_equipped = False
        message(f"Dequipped {self.owner.name} from {self.slot}.", tcod.light_yellow)


def get_all_equipped(obj):  # list of equipped items
    if obj == player:
        equipped_list = []
        for item in inventory:
            if item.equipment and item.equipment.is_equipped:
                equipped_list.append(item.equipment)
        return equipped_list
    else:
        return []

# This is the player class, add player properties here
############################################################################################################
class Player:
    def __init__(self, hp, defense, res, power, xp, mp, souls, death_function=None, use_book_function=None):
        self.base_max_hp = hp
        self.hp = hp
        self.base_defense = defense
        self.base_res = res
        self.base_power = power
        self.xp = xp
        self.mp = mp
        self.base_max_mp = mp
        self.souls = souls
        self.death_function = death_function
        self.use_book_function = use_book_function

    @property
    def power(self):
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        return self.base_power + bonus

    @property
    def defense(self):
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus

    @property
    def res(self):
        bonus = sum(equipment.res_bonus for equipment in get_all_equipped(self.owner))
        return self.base_res + bonus


    @property
    def max_hp(self):
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus

    @property
    def max_mp(self):
        bonus = sum(equipment.max_mp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_mp + bonus

    def attack(self, target):
        damage = self.power - target.fighter.defense

        if damage > 0:
            message(f"{self.owner.name} attacks {target.name} for {damage} HP.")
            target.fighter.take_damage(damage)
        else:
            message(f"{self.owner.name} attacks {target.name} but it has no effect!")

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
                if self.owner != player:
                    player.fighter.xp += self.xp

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def rejuvenate(self, amount):
        self.mp += amount
        if self.mp > self.max_mp:
            self.mp = self.max_mp


# World Object classes:
##############################################################################################
class FountainLifeAI:
    def take_turn(self):
        fountain_of_life = self.owner
        fountain_of_life.drink_fountain_life(fountain_of_life)

# Functions for merchants:
##############################################################################################
def buy_wares():
    healingpotion_tile = 262
    manapotion_tile = 282
    chain_mail_tile = 276
    mage_robes_tile = 283
    bone_tile = 287

    message(f"{player.name} stops by merchant Lau to buy some wares.", tcod.yellow)
    hp_cost = 5
    mp_cost = 15
    cm_cost = 50
    mr_cost = 45
    ba_cost = 120
    x = player.x
    y = player.y
    choice = None
    fail_msgtext = f"{player.name} either doesn't have enough souls, or {player.name}'s inventory is full!"
    while choice == None:
        choice = menu('Give me your Dark Souls!\n',
            [f"Healing Potion, {hp_cost} souls",
            f"Mana Potion, {mp_cost} souls",
            f"Chain Mail, {cm_cost} souls",
            f"Mage Robes, {mr_cost} souls",
            f"Bone Armor, {ba_cost} souls",
            f"Nothing, thank you"], level_screen_width)

    if choice == 0:
        if player.fighter.souls >= hp_cost and len(inventory) <= 25:
            item_component = Item(use_function=cast_heal)
            item = Object(x, y, healingpotion_tile, 'Healing Potion', tcod.white, item=item_component)
            player.fighter.souls -= hp_cost
            inventory.append(item)
            message(f"{player.name} bought a Healing Potion for {hp_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 1:
        if player.fighter.souls >= mp_cost and len(inventory) <= 25:
            item_component = Item(use_function=cast_rejuvenate)
            item = Object(x, y, manapotion_tile, 'Mana Potion', tcod.white, item=item_component)
            inventory.append(item)
            player.fighter.souls -= mp_cost
            message(f"{player.name} bought a Mana Potion for {mp_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 2:
        if player.fighter.souls >= cm_cost and len(inventory) <= 25:
            equipment_component = Equipment(slot='body', defense_bonus=2)
            item = Object(x, y, chain_mail_tile, 'Chain Mail', tcod.white, equipment=equipment_component)
            inventory.append(item)
            player.fighter.souls -= cm_cost
            message(f"{player.name} bought Chain Mail for {cm_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 3:
        if player.fighter.souls >= mr_cost and len(inventory) <= 25:
            equipment_component = Equipment(slot='body', max_mp_bonus=3)
            item = Object(x, y, mage_robes_tile, 'Mage Robes', tcod.white, equipment=equipment_component)
            inventory.append(item)
            player.fighter.souls -= mr_cost
            message(f"{player.name} bought Mage Robes for {mr_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 4:
        if player.fighter.souls >= ba_cost and len(inventory) <= 25:
            equipment_component = Equipment(slot='body', max_mp_bonus=2, defense_bonus=3, res_bonus=8)
            item = Object(x, y, bone_tile, 'Bone Armor', tcod.white, equipment=equipment_component)
            inventory.append(item)
            player.fighter.souls -= ba_cost
            message(f"{player.name} bought Bone Armor for {ba_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 5:
        return 'cancelled'

def buy_goods():
    healingpotion_tile = 262
    manapotion_tile = 282
    helmet_tile = 274
    kushan_scythe_tile = 301
    ring_tile = 302

    message(f"{player.name} stops by merchant Hei to buy some goods.", tcod.yellow)
    hp_cost = 10
    mp_cost = 20
    ks_cost = 220
    kh_cost = 80
    rs_cost = 150
    mr_cost = 150

    x = player.x
    y = player.y
    choice = None
    fail_msgtext = f"{player.name} either doesn't have enough souls, or {player.name}'s inventory is full!"
    while choice == None:
        choice = menu(f"I have everything you need, {player.name}!\n",
            [f"Greater Healing Potion, {hp_cost} souls",
            f"Greater Mana Potion, {mp_cost} souls",
            f"Kushan Scythe, {ks_cost} souls",
            f"Kushan Helmet, {kh_cost} souls",
            f"Ring of Strength, {rs_cost} souls",
            f"Mentor's Ring, {mr_cost} souls",
            f"Nothing, thank you"], level_screen_width)

    if choice == 0:
        if player.fighter.souls >= hp_cost and len(inventory) <= 25:
            item_component = Item(use_function=cast_great_heal)
            item = Object(x, y, healingpotion_tile, 'Greater Healing Potion', tcod.white, item=item_component)
            player.fighter.souls -= hp_cost
            inventory.append(item)
            message(f"{player.name} bought a Greater Healing Potion for {hp_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 1:
        if player.fighter.souls >= mp_cost and len(inventory) <= 25:
            item_component = Item(use_function=cast_great_rejuvenate)
            item = Object(x, y, manapotion_tile, 'Greater Mana Potion', tcod.white, item=item_component)
            inventory.append(item)
            player.fighter.souls -= mp_cost
            message(f"{player.name} bought a Greater Mana Potion for {mp_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 2:
        if player.fighter.souls >= ks_cost and len(inventory) <= 25:
            equipment_component = Equipment(slot='main hand', power_bonus=12, defense_bonus=-2)
            item = Object(x, y, kushan_scythe_tile, 'Kushan Scythe', tcod.white, equipment=equipment_component)
            inventory.append(item)
            player.fighter.souls -= ks_cost
            message(f"{player.name} bought Kushan Scythe for {ks_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 3:
        if player.fighter.souls >= kh_cost and len(inventory) <= 25:
            equipment_component = Equipment(slot='head', defense_bonus=2)
            item = Object(x, y, helmet_tile, 'Kushan Helmet', tcod.white, equipment=equipment_component)
            inventory.append(item)
            player.fighter.souls -= kh_cost
            message(f"{player.name} bought Kushan Helmet for {kh_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 4:
        if player.fighter.souls >= rs_cost and len(inventory) <= 25:
            equipment_component = Equipment(slot='right finger', defense_bonus=1, power_bonus=2)
            item = Object(x, y, ring_tile, 'Ring of Strength', tcod.white, equipment=equipment_component)
            inventory.append(item)
            player.fighter.souls -= rs_cost
            message(f"{player.name} bought Ring of Strength for {rs_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 5:
        if player.fighter.souls >= mr_cost and len(inventory) <= 25:
            equipment_component = Equipment(slot='left finger', max_mp_bonus=4)
            item = Object(x, y, ring_tile, "Mentor's Ring", tcod.white, equipment=equipment_component)
            inventory.append(item)
            player.fighter.souls -= mr_cost
            message(f"{player.name} bought Mentor's Ring for {mr_cost} souls.", tcod.green)
        else:
            msgbox(fail_msgtext)

    elif choice == 6:
        return 'cancelled'


# Fighter classes:
###############################################################################################
class Enemy:
    def __init__(self, hp, mp, defense, res, power, xp, souls, death_function=None):
        self.base_max_hp = hp
        self.hp = hp
        self.mp = mp
        self.base_max_mp = mp
        self.base_defense = defense
        self.base_res = res
        self.base_power = power
        self.xp = xp
        self.souls = souls
        self.death_function = death_function

    @property
    def power(self):
        bonus = sum(equipment.power_bonus for equipment in get_all_equipped(self.owner))
        return self.base_power + bonus

    @property
    def defense(self):
        bonus = sum(equipment.defense_bonus for equipment in get_all_equipped(self.owner))
        return self.base_defense + bonus

    @property
    def res(self):
        bonus = sum(equipment.res_bonus for equipment in get_all_equipped(self.owner))
        return self.base_res + bonus

    @property
    def max_hp(self):
        bonus = sum(equipment.max_hp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_hp + bonus

    @property
    def max_mp(self):
        bonus = sum(equipment.max_mp_bonus for equipment in get_all_equipped(self.owner))
        return self.base_max_mp + bonus


    def attack(self, target):
        damage = self.power - target.fighter.defense

        if damage > 0:
            message(f"{self.owner.name} attacks {target.name} for {damage} HP.")
            target.fighter.take_damage(damage)
        else:
            message(f"{self.owner.name} attacks {target.name} but it has no effect!")

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage
            if self.hp <= 0:
                function = self.death_function
                if function is not None:
                    function(self.owner)
                if self.owner != player:
                    player.fighter.xp += self.xp
                    player.fighter.souls += self.souls

    def heal(self, amount):
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def shoot_bow(self, monster):
        bow_damage = monster.fighter.power
        bow_range = 3
        player = closest_player(bow_range)
        if player is None:
            return 'cancelled'
        else:
            if monster.distance_to(player) <= bow_range:
                message(f"{monster.name} shoots arrows at {player.name} for {bow_damage - player.fighter.defense} damage!", tcod.blue)
                player.fighter.take_damage(bow_damage - player.fighter.defense)
            else:
                return 'cancelled'
    
    def disease_cloud(self, monster):
        dis_damage = 1
        dis_range = 2
        target = closest_player(dis_range)
        if target is None:
            return 'cancelled'
        else:
            if target.fighter.res < 10:
                message(f"{monster.name} emmits a cloud of disease, almost choking you! (DAM: {dis_damage})", tcod.dark_yellow)
                target.fighter.take_damage(dis_damage)
            else:
                return 'cancelled'


    def gargoyle_stone_skin(self, monster):
        spell_cost = 1
        def_bonus = 1
        if monster.fighter.mp >= spell_cost and monster.fighter.hp <= 20:
            message("Gargoyle hardens it's skin!", tcod.blue)
            monster.fighter.base_defense += def_bonus
            monster.fighter.mp -= spell_cost
        else:
            return 'cancelled'

    def gargoyle_stone_hide(self, monster):
        spell_cost = 1
        def_bonus = 2
        if monster.fighter.mp >= spell_cost and monster.fighter.hp <= 40:
            message("Gargoyle hardens it's skin!", tcod.blue)
            monster.fighter.base_defense += def_bonus
            monster.fighter.mp -= spell_cost
        else:
            return 'cancelled'

    def lance_crit_swing(self, monster):
        mp_cost = 1
        swing_range = 1
        player = closest_player(swing_range)
        swing_damage = monster.fighter.power * 1.5
        if player is None:
            return 'cancelled'
        else:
            if monster.fighter.mp >= mp_cost and monster.distance_to(player) <= swing_range:
                message(f"{monster.name} thrusts his lance with great might!", tcod.blue)
                player.fighter.take_damage(swing_damage - player.fighter.defense)
                monster.fighter.mp -= mp_cost

            else:
                return 'cancelled'
                
    def scorching_aura(self, monster):
        aura_damage = 5
        aura_range = 1
        aura_cost = 1
        player = closest_player(aura_range)
        if player is None:
            return 'cancelled'
        else:
            if player.fighter.res < 25 and monster.fighter.mp >= aura_cost and monster.distance_to(player) <= aura_range:
                message(f"Flames lick {player.name}'s skin.", tcod.red)
                player.fighter.take_damage(aura_damage)
                monster.fighter.mp -= 1

            else:
                return 'cancelled'

    def judgement_call(self, monster): # powerfull buff spell, maybe add a handicap
        spell_damage = 55
        spell_effect1 = 3
        spell_effect2 = 30
        spell_range = 3
        spell_cost = 2
        player = closest_player(spell_range)
        if player is None:
            return 'cancelled'
        else:
            if monster.fighter.mp >= spell_cost and monster.distance_to(player) <= spell_range:
                message(f"{monster.name} invokes Judgement Call spell!", tcod.azure)
                player.fighter.take_damage(spell_damage - player.fighter.res)
                monster.fighter.base_max_hp += spell_effect2
                monster.fighter.hp += spell_effect2
                monster.fighter.base_power += spell_effect1
                monster.fighter.mp -= spell_cost

            else:
                return 'cancelled'

    def cast_lightning_forgotten(self, forgotten):
        lightning_spell_damage = 55
        lightning_spell_range = 3
        lightning_spell_cost = 2
        player = closest_player(lightning_spell_range)
        if player is None:
            return 'cancelled'
        else:
            if forgotten.fighter.mp >= lightning_spell_cost and forgotten.distance_to(player) <= lightning_spell_range:
                message(f"{forgotten.name} calls Lightning Strike on {player.name}!", tcod.blue)
                player.fighter.take_damage(lightning_spell_damage - player.fighter.res)
                forgotten.fighter.mp -= lightning_spell_cost

            else:
                return 'cancelled'

    def call_crushing_tide(self, monster):
        spell_damage = 80
        spell_range = 3
        spell_cost = 1
        tide_drain = 1
        player = closest_player(spell_range)
        if player is None:
            return 'cancelled'
        else:
            if monster.fighter.mp >= spell_cost and monster.distance_to(player) <= spell_range:
                message(f"{monster.name} casts Crushing Tide on {player.name}!", tcod.crimson)
                player.fighter.take_damage(spell_damage - player.fighter.res)
                player.fighter.mp -= tide_drain
                monster.fighter.mp -= spell_cost

            else:
                return 'cancelled'

    def blessing_of_old_sea(self, monster):
        spell_effect1 = 3
        spell_effect2 = 55
        spell_cost = 2
        if monster.fighter.mp >= spell_cost:
            if monster.fighter.hp > 100:
                return 'cancelled'
            elif monster.fighter.hp <= 100 and monster.fighter.mp >= spell_cost:
                message(f"{monster.name} casts Blessing of Old Sea Gods!", tcod.blue)
                monster.fighter.heal(spell_effect2)
                monster.fighter.base_power += spell_effect1
                monster.fighter.mp -= spell_cost

        else:
            return 'cancelled'

    def mummy_heal(self, monster):
        healing_amount = 25
        healing_cost = 1
        if monster.fighter.mp >= healing_cost:
            if monster.fighter.hp > 40:
                return 'cancelled'
            elif monster.fighter.hp <= 40 and monster.fighter.mp >= healing_cost:
                message(f"{monster.name} heals itself for {healing_amount} HP", tcod.darker_blue)
                monster.fighter.heal(healing_amount)
                monster.fighter.mp -= healing_cost

        else:
            return 'cancelled'

    def anubite_curse(self, monster):
        curse_effect = 1
        curse_cost = 2
        curse_range = 3
        player = closest_player(curse_range)
        if player is None:
            return 'cancelled'
        else:
            if monster.fighter.mp >= curse_cost and player.fighter.res < 30 and monster.distance_to(player) <= curse_range:
                message(f"{monster.name} curses {player.name}'s' armor!", tcod.crimson)
                player.fighter.base_defense -= curse_effect # if player has less than 30 res, reduce his defense
                monster.fighter.mp -= curse_cost
            else:
                return 'cancelled'

    def anubite_heal(self, monster):
        healing_cost = 1
        healing_amount = 40
        if monster.fighter.mp >= healing_cost:
            if monster.fighter.hp > 40:
                return 'cancelled'
            elif monster.fighter.hp <= 40 and monster.fighter.mp >= healing_cost:
                message(f"{monster.name} heals itself for {healing_amount} HP!" , tcod.darker_blue)
                monster.fighter.heal(healing_amount)
                monster.fighter.mp -= healing_cost

        else:
            return 'cancelled'
            
    def cast_firebite_sm(self, monster):
        firebite_damage = 15
        firebite_range = 1
        firebite_cost = 1
        player = closest_player(firebite_range)
        if player is None:
            return 'cancelled'

        else:
            if monster.fighter.mp >= firebite_cost and monster.distance_to(player) <= firebite_range:
                message(f"{monster.name} casts Firebite on {player.name}!", tcod.blue)
                player.fighter.take_damage(firebite_damage - player.fighter.res)
                monster.fighter.mp -= firebite_cost

            else:
                if monster.distance_to(player) >= 2:
                    monster.move_astar(player)

    def cast_fireball_tp(self, priest):
        fireball_damage = 35
        fireball_range = 3
        fireball_cost = 1
        player = closest_player(fireball_range)
        if player is None:
            return 'cancelled'
        else:
            if priest.fighter.mp >= fireball_cost and priest.distance_to(player) <= fireball_range:
                message(f"{priest.name} casts Fireball at {player.name}!", tcod.blue)
                player.fighter.take_damage(fireball_damage - player.fighter.res)
                priest.fighter.mp -= fireball_cost

            else:
                return 'cancelled'

    def dark_ritual(self, priest):
        ritual_cost = 1
        ritual_range = 4
        ritual_effect = 2
        target = closest_monster(ritual_range)
        if target is None:
            return 'cancelled'
        else:
            if priest.fighter.mp >= ritual_cost and target.fighter.hp >= 0 and target != priest: # target an ally, not self
                message(f"{priest.name} casts Dark Ritual on {target.name}!", tcod.crimson)
                target.fighter.base_power += ritual_effect
                priest.fighter.mp -= ritual_cost

            else:
                return 'cancelled'

    def clare_fatal_swing(self, clare): # fatal swing that ignores defense and does critical damage
        swing_damage = clare.fighter.power * 2
        swing_range = 2
        swing_cost = 1
        player = closest_player(swing_range)
        if player is None:
            return 'cancelled'
        else:
            if clare.fighter.mp >= swing_cost and clare.distance_to(player) == swing_range:
                message(f"{clare.name} swings her massive Claymore at {player.name} with monstrous strenght!", tcod.blue)
                player.fighter.take_damage(swing_damage - player.fighter.res)
                clare.fighter.mp -= swing_cost

            elif clare.distance_to(player) >= 3:
                clare.move_astar(player)

    def use_healing_clare(self, clare):
        healing_amount = 30
        healing_cost = 1
        if clare.fighter.mp >= healing_cost:
            if clare.fighter.hp > 30:
                return 'cancelled'
            elif clare.fighter.hp <= 30 and clare.fighter.mp >= healing_cost:
                message('Clare heals some of the damage using her demonic powers!', tcod.darker_blue)
                clare.fighter.heal(healing_amount)
                clare.fighter.mp -= healing_cost

        else:
            return 'cancelled'

    def nausea(self, monster):
        drain_res = 1
        damage = 40
        eff_range = 1
        cost = 1
        target = closest_player(eff_range)
        if target is None:
            return 'cancelled'
        else:
            if target.fighter.res <= 30 and monster.distance_to(target) <= eff_range and monster.fighter.mp >= cost:
                target.fighter.base_res -= drain_res
                target.fighter.take_damage(damage - target.fighter.res)
                monster.fighter.mp -= cost
                message(f"{monster.name}'s attack makes you feel sick. (-{drain_res} RES, DAM: {damage-target.fighter.res})", tcod.yellow)
            else:
                return 'cancelled'
    
    def venom_sting(self, monster):
        cost = 1
        sting_range = 2
        target = closest_player(sting_range)
        sting_damage = target.fighter.base_res // 3
        if target is None:
            return 'cancelled'
        else:
            if monster.distance_to(target) <= sting_range and monster.fighter.mp >= cost:
                message(f"{monster.name} gives you a painful sting. (DAM: {sting_damage})", tcod.azure)
                target.fighter.take_damage(sting_damage)
                monster.fighter.mp -= cost
            else:
                return 'cancelled'


    def cast_flame_phoenix(self,ashara):
        phoenix_damage = 75
        phoenix_range = 3
        phoenix_cost = 1
        player = closest_player(phoenix_range)
        if player is None:
            return 'cancelled'
        else:
            if ashara.fighter.mp >= phoenix_cost and ashara.distance_to(player) <= phoenix_range:
                message(f"{ashara.name} casts Flame Phoenix at {player.name}!", tcod.blue)
                player.fighter.take_damage(phoenix_damage - player.fighter.res)
                ashara.fighter.mp -= phoenix_cost

            else:
                return 'cancelled'

    def power_of_twilight(self,ashara):
        ritual_cost = 2
        ritual_range = 4
        ritual_effect1 = 4
        ritual_effect2 = 25
        target = closest_monster(ritual_range)
        if target is None:
            return 'cancelled'
        else:
            if ashara.fighter.mp >= ritual_cost and target.fighter.hp >= 0 and target != ashara: # target an ally, not self
                message(f"{ashara.name} casts Power of Twilight on {target.name}!", tcod.crimson)
                target.fighter.base_power += ritual_effect1
                target.fighter.base_max_hp += ritual_effect2
                target.fighter.heal(ritual_effect2)
                ashara.fighter.mp -= ritual_cost

            else:
                return 'cancelled'

    def cast_holy_restoration(self,ashara):
        healing_amount = 60
        healing_cost = 1
        heal_range = 3
        monster = closest_monster(heal_range)
        if ashara.fighter.mp >= healing_cost:
            if ashara.fighter.hp > 100 or monster is None:
                return 'cancelled'
            elif ashara.fighter.hp <= 100 or monster.fighter.hp <= 90 and ashara.fighter.mp >= healing_cost:
                message('Ashara casts Holy Restoration!', tcod.darker_blue)
                ashara.fighter.heal(healing_amount)
                monster.fighter.heal(healing_amount)
                ashara.fighter.mp -= healing_cost

    def cast_weaken(self,ashara):
        effect = 2
        cost = 2
        weaken_range = 5
        player = closest_player(weaken_range)
        if player is None:
            return 'cancelled'
        else:
            if ashara.fighter.mp >= cost and player.fighter.res < 40 and ashara.distance_to(player) <= weaken_range:
                message(f"{ashara.name} casts Weaken on {player.name}!", tcod.crimson)
                player.fighter.base_defense -= effect
                player.fighter.base_power -= effect
                ashara.fighter.mp -= cost
            else:
                return 'cancelled'

class SkeletalArcherAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 4:
                monster.move_astar(player)
            elif monster.distance_to(player) <= 3:
                monster.fighter.shoot_bow(monster)


class BasicMonster:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            elif player.fighter.hp >= 0:
                monster.fighter.attack(player)

class GhoulAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            if player.fighter.hp >= 0 and monster.distance_to(player) <= 1:
                monster.fighter.attack(player)
                monster.fighter.disease_cloud(monster)

class ClareAI:
    def take_turn(self):
        clare = self.owner
        if tcod.map_is_in_fov(fov_map, clare.x, clare.y):
            if clare.distance_to(player) >= 3:
                clare.move_astar(player)
            if player.fighter.hp >= 80:
                clare.fighter.clare_fatal_swing(clare)  # use special ability
            if clare.fighter.hp <= 30:
                clare.fighter.use_healing_clare(clare) # heal Clare
            if player.fighter.hp >= 0 and clare.distance_to(player) <= 1:
                clare.fighter.attack(player)


class SMageMonsterAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            elif player.fighter.hp >= 0:
                monster.fighter.cast_firebite_sm(monster)

class TwilightPriestAI:
    def take_turn(self):
        priest = self.owner
        if tcod.map_is_in_fov(fov_map, priest.x, priest.y):
            if priest.distance_to(player) >= 4:
                priest.move_astar(player)
            elif player.fighter.hp >= 0 and priest.distance_to(player) <= 1:
                priest.fighter.attack(player)
            if player.fighter.hp >= 70:
                priest.fighter.cast_fireball_tp(priest)
            if priest.fighter.mp >= 3:
                priest.fighter.dark_ritual(priest)

class PrincessAsharaAI:
    def take_turn(self):
        ashara = self.owner
        help_range = 5
        monster = closest_monster(help_range)
        dice = choice([0, 1])
        if tcod.map_is_in_fov(fov_map, ashara.x, ashara.y):
            if ashara.distance_to(player) >= 4:
                ashara.move_astar(player)
            elif player.fighter.hp >= 0 and ashara.distance_to(player) <= 1:
                ashara.fighter.attack(player)
                if dice == 1:
                    message("You don't belong here, mortal!", tcod.orange)
                else:
                    message("You will die here, ignorant fool!", tcod.orange)

            if player.fighter.hp > 80 and ashara.distance_to(player) <= 3:
                ashara.fighter.cast_flame_phoenix(ashara)
            if ashara.fighter.mp >= 6 and ashara.distance_to(player) <= help_range:
                ashara.fighter.power_of_twilight(ashara)
            if ashara.fighter.hp <= 100 and ashara.fighter.mp >= 2:
                ashara.fighter.cast_holy_restoration(ashara)
            if ashara.fighter.mp >= 8 and ashara.distance_to(player) <= 5:
                ashara.fighter.cast_weaken(ashara)

class AnubiteAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 4:
                monster.move_astar(player)
            if monster.distance_to(player) <= 3:
                monster.fighter.anubite_curse(monster)
            if monster.fighter.hp <= 40:
                monster.fighter.anubite_heal(monster)
            if player.fighter.hp >= 0 and monster.distance_to(player) <= 1:
                monster.fighter.attack(player)

class BigBeetleAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 3:
                monster.move_astar(player)
            if monster.distance_to(player) == 2:
                monster.fighter.venom_sting(monster)
            if monster.distance_to(player) <= 1 and player.fighter.hp >= 0:
                monster.fighter.nausea(monster)
                monster.fighter.attack(player)

class RoyalGuardAI:
    def take_turn(self):
        monster = self.owner
        dice = choice([0, 1])
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            if monster.distance_to(player) <= 3 and player.fighter.hp > 80:
                monster.fighter.call_crushing_tide(monster)
            if monster.fighter.hp <= 100:
                monster.fighter.blessing_of_old_sea(monster)
            if player.fighter.hp >= 0 and monster.distance_to(player) <= 1:
                monster.fighter.attack(player)
                if dice == 1:
                    message("For Princess Ashara!", tcod.azure)
                else:
                    message("Be crushed by the Old Sea's tide!", tcod.azure)

class ForgottenAI:
    def take_turn(self):
        forgotten = self.owner
        if tcod.map_is_in_fov(fov_map, forgotten.x, forgotten.y):
            if forgotten.distance_to(player) >= 2:
                forgotten.move_astar(player)
            if player.fighter.hp >= 70:
                forgotten.fighter.cast_lightning_forgotten(forgotten)
            if player.fighter.hp >= 0 and forgotten.distance_to(player) <= 1:
                forgotten.fighter.attack(player)

class ForgottenMummyAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            elif monster.fighter.hp <= 40:
                monster.fighter.mummy_heal(monster)
                monster.fighter.attack(player)
            elif player.fighter.hp >= 0 and monster.distance_to(player) <= 1:
                monster.fighter.attack(player)


class ScorchedDemonAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            elif player.fighter.hp >= 0:
                monster.fighter.scorching_aura(monster)
                monster.fighter.attack(player)

class AmarathLordAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            if player.fighter.hp > 0 and monster.distance_to(player) <= 3:
                monster.fighter.judgement_call(monster)
            if player.fighter.hp >= 0 and monster.distance_to(player) == 1:
                monster.fighter.attack(player)


class GargoyleAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            elif monster.fighter.hp <= 20:
                monster.fighter.gargoyle_stone_skin(monster)
                monster.fighter.attack(player)
            elif player.fighter.hp >= 0:
                monster.fighter.attack(player)

class GargoyleLancerAI:
    def take_turn(self):
        monster = self.owner
        if tcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_astar(player)
            if player.fighter.hp >= 75:
                monster.fighter.lance_crit_swing(monster)
            if monster.fighter.hp <= 40:
                monster.fighter.gargoyle_stone_hide(monster)
                monster.fighter.attack(player)
            elif player.fighter.hp >= 0 and player.distance_to(monster) <= 1:
                monster.fighter.attack(player)


class ConfusedMonster:
    confuse_num_turns = 10
    def __init__(self, old_ai, num_turns=confuse_num_turns):
        self.old_ai = old_ai
        self.num_turns = num_turns
    def take_turn(self):
        if self.num_turns > 0:
            self.owner.move(tcod.random_get_int(0, -1, 1), tcod.random_get_int(0, -1, 1))
            self.num_turns -= 1
        else:
            self.owner.ai = self.old_ai
            message('The ' + self.owner.name + ' is no longer confused!', tcod.red)

def is_blocked(x, y):
    if map[x][y].blocked:
        return True
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
    return False

def closest_monster(max_range):
    closest_enemy = None
    closest_dist = max_range + 1

    for object in objects:
        if object.fighter and not object == player and tcod.map_is_in_fov(fov_map, object.x, object.y):
            dist = player.distance_to(object)
            if dist < closest_dist:
                closest_enemy = object
                closest_dist = dist
    return closest_enemy

def closest_player(max_range):
    closest_enemy = None
    closest_dist = max_range + 1

    for object in objects:
        if object.fighter and object == player and tcod.map_is_in_fov(fov_map, object.x, object.y):
            dist = player.distance_to(object)
            if dist < closest_dist:
                closest_enemy = object
                closest_dist = dist
    return closest_enemy

# Functions for creating rooms and tunnels:
##########################################################################################################

def create_room(room):
    global map
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
    global map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

# Spells and effects:
################################################################################################

def cast_heal():
    heal_amount = 40
    if player.fighter.hp == player.fighter.max_hp:
        message(f"{player.name} is already at full health!", tcod.green)
        return 'cancelled'
    message(f"{player.name}'s wounds start to heal!", tcod.light_violet)
    player.fighter.heal(heal_amount)

def cast_great_heal():
    heal_amount = 75
    if player.fighter.hp == player.fighter.max_hp:
        message(f"{player.name} is already at full health!", tcod.green)
        return 'cancelled'
    message(f"{player.name}'s wounds start to heal!", tcod.light_violet)
    player.fighter.heal(heal_amount)

def cast_full_heal():
    heal_amount = 500
    if player.fighter.hp == player.fighter.max_hp:
        message(f"{player.name} is already at full health!", tcod.green)
        return 'cancelled'
    message(f"{player.name} is fully healed!", tcod.light_violet)
    player.fighter.heal(heal_amount)

def cast_rejuvenate():
    reju_amount = 3
    if player.fighter.mp == player.fighter.max_mp:
        message(f"{player.name} is already at full mana!", tcod.green)
        return 'cancelled'
    message(f"{player.name}'s mana is restoring!", tcod.azure)
    player.fighter.rejuvenate(reju_amount)

def cast_great_rejuvenate():
    reju_amount = 5
    if player.fighter.mp == player.fighter.max_mp:
        message(f"{player.name} is already at full mana!", tcod.green)
        return 'cancelled'
    message(f"{player.name}'s mana is restoring!", tcod.azure)
    player.fighter.rejuvenate(reju_amount)

def raise_power():
    effect = 2
    message(f"{player.name} reads the Tome of Might and gains {effect} Attack Power!", tcod.green)
    player.fighter.base_power += effect

def raise_agility():
    effect = 2
    message(f"{player.name} reads the Tome of Agility and gains {effect} Defense!", tcod.green)
    player.fighter.base_defense += effect

def raise_magic():
    effect = 2
    message(f"{player.name} reads the Tome of Magic and gains {effect} Mana!", tcod.green)
    player.fighter.base_max_mp += effect

def cast_lightning():
    lightning_range = 5
    lightning_damage = 50
    monster = closest_monster(lightning_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    message(f"Lightning Bolt strikes {monster.name}! (Dam: {lightning_damage - monster.fighter.base_res})", tcod.light_blue)
    monster.fighter.take_damage(lightning_damage - monster.fighter.base_res)


def cast_hand_of_marduk():
    spell_range = 5
    spell_damage = 120
    monster = closest_monster(spell_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    message(f"The hand of Marduk smites {monster.name}! (Dam: {spell_damage - monster.fighter.base_res})", tcod.light_blue)
    monster.fighter.take_damage(spell_damage - monster.fighter.base_res)

def cast_fireball():
    fireball_range = 3
    fireball_damage = 65
    monster = closest_monster(fireball_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    message(f"Fireball burns {monster.name}! (Dam: {fireball_damage - monster.fighter.base_res})", tcod.light_blue)
    monster.fighter.take_damage(fireball_damage - monster.fighter.base_res)

def cast_hellfire():
    hell_range = 4
    damage = 100
    target = closest_monster(hell_range)
    if target is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    message(f"Hellish fire rains down on {target.name}! (Dam: {damage - target.fighter.base_res})", tcod.light_blue)
    target.fighter.take_damage(damage - target.fighter.base_res)

def frost_bolt():
    frost_bolt_range = 5
    frost_bolt_damage = 80
    monster = closest_monster(frost_bolt_range)
    if monster is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    message(f"Frost Bolt chills {monster.name}! (Dam: {frost_bolt_damage - monster.fighter.base_res})", tcod.light_blue)
    monster.fighter.take_damage(frost_bolt_damage - monster.fighter.base_res)

def cast_weaken():
    w_range = 4
    effect1 = 5
    effect2 = 8
    target = closest_monster(w_range)
    if target is None:
        message('No enemy in sight for that spell!', tcod.red)
        return 'cancelled'
    message(f"The {target.name} is severely weakened! (Effect: -{effect2} DAM, -{effect1} DEF)", tcod.azure)
    target.fighter.base_defense -= effect1
    target.fighter.base_power -= effect2

def cast_confuse():
    confuse_range = 8
    monster = closest_monster(confuse_range)
    if monster is None:
        message('No monster to confuse!')
        return 'cancelled'
    old_ai = monster.ai
    monster.ai = ConfusedMonster(old_ai)
    monster.ai.owner = monster
    message(f"{monster.name} is confused!", tcod.light_blue)

# Functions for targeting and ranged combat:
#####################################################################################################

def target_tile(max_range=None):
    global key, mouse
    while True:
        tcod.console_flush()
        tcod.sys_check_for_event(tcod.EVENT_KEY_PRESS|tcod.EVENT_MOUSE, key, mouse)
        render_all()

        (x, y) = (mouse.cx, mouse.cy)
        if (mouse.lbutton_pressed and tcod.map_is_in_fov(fov_map, x, y) and (max_range is None or player.distance(x, y) <= max_range)):
            return (x, y)
        if mouse.rbutton_pressed or key.vk == tcod.KEY_ESCAPE:
            return (None, None)


def target_monster(max_range=None):
    while True:
        (x, y) = target_tile(max_range)
        if x is None:
            return None

        for obj in objects:
            if obj.x == x and obj.y == y and obj.fighter and obj != player:
                return obj

# Functions for making maps:
##############################################################################################
def make_bsp_map():
    global map, objects, stairs, bsp_rooms

    scroll_tile = 261
    fountain_of_life_tile = 288
    merchant_tile = 281
    book_tile = 273
    garg_lance_tile = 292
    stairsdown_tile = 265
    twilight_priest_tile = 293
    scorched_demon_tile = 295
    amarath_tile = 296
    boots_tile = 303
    royal_guard_tile = 304
    twilight_princess_tile = 305
    ashara_dagger_tile = 299
    kushan_armor_tile = 300

    objects = [player]

    map = [[Tile(True) for y in range(map_height)] for x in range(map_width)]

    # Empty list for bsp rooms:
    bsp_rooms = []

    # New root node:
    bsp = tcod.bsp_new_with_size(0, 0, map_width, map_height)

    tcod.bsp_split_recursive(bsp, 0, depth, min_size+1, min_size+1, 1.5, 1.5)

    # Create rooms:
    tcod.bsp_traverse_inverted_level_order(bsp, traverse_node)

    # Random room for stairs, princess Ashara, her guard and the merchant:
    stairs_location = choice(bsp_rooms)
    bsp_rooms.remove(stairs_location)
    stairs = Object(stairs_location[0], stairs_location[1], stairsdown_tile, 'Stairs', tcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back()

    if dungeon_level == 11 or dungeon_level == 13 or dungeon_level == 15 or dungeon_level == 17 or dungeon_level == 19:
        merchant_hei = Object(20, 20, merchant_tile, 'Merchant Hei', tcod.white, blocks=True, always_visible=True)
        objects.append(merchant_hei)

    if dungeon_level == 20:
        ashara_component = Enemy(hp=200, mp=8, defense=4, res=40, power=25, xp=1000, souls=10, death_function=monster_death)
        ashara_ai = PrincessAsharaAI()
        ashara = Object(stairs_location[0]+1, stairs_location[1]+1, twilight_princess_tile, 'Ashara', tcod.white, blocks=True, fighter=ashara_component, ai=ashara_ai)

        fighter_component = Enemy(hp=255, mp=4, defense=5, res=35, power=35, xp=800, souls=6, death_function=monster_death)
        ai_component = RoyalGuardAI()
        royal = Object(stairs_location[0]-1, stairs_location[1]-1, royal_guard_tile, 'Royal Guard', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
        objects.append(ashara)
        objects.append(royal)


    # Random room for player:
    player_room = choice(bsp_rooms)
    bsp_rooms.remove(player_room)
    player.x = player_room[0]
    player.y = player_room[1]

    # Random room for the fountain, Royal Guard and Tomes:
    fountain_room = choice(bsp_rooms)
    bsp_rooms.remove(fountain_room)
    fountain_life_ai = FountainLifeAI()
    fountain_of_life = Object(fountain_room[0], fountain_room[1], fountain_of_life_tile, 'Fountain of Life', tcod.white, blocks=False, ai=fountain_life_ai, always_visible=True)

    if dungeon_level == 16:
        tome_effect = Item(use_function=raise_power)
        tome = Object(fountain_room[0]+1, fountain_room[1]+1, book_tile, 'Tome of Might', tcod.white, blocks=False, item=tome_effect)
        objects.append(tome)

    elif dungeon_level == 18:
        tome_effect = Item(use_function=raise_agility)
        tome = Object(fountain_room[0]+1, fountain_room[1]+1, book_tile, 'Tome of Agility', tcod.white, blocks=False, item=tome_effect)
        scroll_effect = Item(use_function=cast_full_heal)
        scroll = Object(fountain_room[0]-1, fountain_room[1]-1, scroll_tile, "Healer's Scroll", tcod.white, blocks=False, item=scroll_effect)
        objects.append(tome)
        objects.append(scroll)

    elif dungeon_level == 19:
        tome_effect = Item(use_function=raise_magic)
        tome = Object(fountain_room[0]+1, fountain_room[1]+1, book_tile, "Tome of Magic", tcod.white, blocks=False, item=tome_effect)
        scroll_effect = Item(use_function=cast_full_heal)
        scroll = Object(fountain_room[0]-1, fountain_room[1]-1, scroll_tile, "Healer's Scroll", tcod.white, blocks=False, item=scroll_effect)

        royal_component = Enemy(hp=255, mp=4, defense=5, res=35, power=35, xp=800, souls=6, death_function=monster_death)
        royal_ai_component = RoyalGuardAI()
        royal_guard = Object(stairs_location[0]-1, stairs_location[1]-1, royal_guard_tile, "Royal Guard", tcod.white, blocks=True, fighter=royal_component, ai=royal_ai_component)
        objects.append(tome)
        objects.append(scroll)
        objects.append(royal_guard)


    # Room for the Ashara dagger:
    dagger_room = choice(bsp_rooms)
    if dungeon_level == 12:
        bsp_rooms.remove(dagger_room)
        dagger_component = Equipment(slot='main hand', power_bonus=9)
        dagger = Object(dagger_room[0], dagger_room[1], ashara_dagger_tile, "Ashara's Dagger", tcod.white, equipment=dagger_component)
        objects.append(dagger)

    # Room for the Kushan armor:
    kushan_room = choice(bsp_rooms)
    if dungeon_level == 11:
        bsp_rooms.remove(kushan_room)
        kushan_component = Equipment(slot='body', defense_bonus=7, max_hp_bonus=20)
        kushan_armor = Object(kushan_room[0], kushan_room[1], kushan_armor_tile, 'Kushan Armor', tcod.white, equipment=kushan_component)
        objects.append(kushan_armor)

    # Room for the Boots of Koel Tolas:
    bokt_room = choice(bsp_rooms)
    if dungeon_level == 14:
        bsp_rooms.remove(bokt_room)
        bokt_component = Equipment(slot='legs', defense_bonus=2, power_bonus=1, max_mp_bonus=2)
        bokt = Object(bokt_room[0], bokt_room[1], boots_tile, 'Boots of Koel Tolas', tcod.white, equipment=bokt_component)
        objects.append(bokt)

    # Room for the Healing book:
    great_hb_room = choice(bsp_rooms)
    if dungeon_level == 13:
        bsp_rooms.remove(great_hb_room)
        heal_component = Item(use_book_function=cast_great_heal_spell)
        heal_book = Object(great_hb_room[0], great_hb_room[1], book_tile, 'Great Healing Spellbook', tcod.white, item=heal_component)
        objects.append(heal_book)

   # Room for the Mana Burn book:
    mb_book_room = choice(bsp_rooms)
    if dungeon_level == 15:
        bsp_rooms.remove(mb_book_room)
        mb_component = Item(use_book_function=cast_mana_burn_spell)
        mb_book = Object(mb_book_room[0], mb_book_room[1], book_tile, 'Mana Burn Spellbook', tcod.white, item=mb_component)
        objects.append(mb_book)

    # Room for the Soul Rend book:
    soul_rend_room = choice(bsp_rooms)
    if dungeon_level == 14:
        bsp_rooms.remove(soul_rend_room)
        sr_component = Item(use_book_function=cast_soul_rend_spell)
        sr_book = Object(soul_rend_room[0], soul_rend_room[1], book_tile, 'Soul Rending Spellbook', tcod.white, item=sr_component)
        objects.append(sr_book)

    # Room for the Shocking Grasp book:
    shock_room = choice(bsp_rooms)
    if dungeon_level == 12:
        bsp_rooms.remove(shock_room)
        shock_component = Item(use_book_function=cast_shocking_grasp_spell)
        shock_book = Object(shock_room[0], shock_room[1], book_tile, 'Shocking Grasp Spellbook', tcod.white, item=shock_component)
        objects.append(shock_book)

    # Random room for the Priest and his ally:
    priest_room = choice(bsp_rooms)
    bsp_rooms.remove(priest_room)
    priest_component = Enemy(hp=90, mp=4, defense=2, res=25, power=18, xp=350, souls=3, death_function=monster_death)
    priest_ai = TwilightPriestAI()
    priest = Object(priest_room[0], priest_room[1], twilight_priest_tile, 'Twilight Priest', tcod.white, blocks=True, fighter=priest_component, ai=priest_ai)
    objects.append(priest)

    if dungeon_level == 11 or dungeon_level == 12 or dungeon_level == 13:
        fighter_component = Enemy(hp=120, mp=2, defense=3, res=12, power=20, xp=320, souls=3, death_function=monster_death)
        ai_component = GargoyleLancerAI()
        monster = Object(priest_room[0]+1, priest_room[1]+1, garg_lance_tile, 'Gargoyle Lancer', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
        objects.append(monster)

    elif dungeon_level > 13 and dungeon_level <= 16:
        fighter_component = Enemy(hp=180, mp=5, defense=4, res=30, power=27, xp=480, souls=4, death_function=monster_death)
        ai_component = ScorchedDemonAI()
        monster = Object(priest_room[0]+1, priest_room[1]+1, scorched_demon_tile, 'Scorched Demon', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
        objects.append(monster)

    elif dungeon_level > 16:
        fighter_component = Enemy(hp=220, mp=0, defense=4, res=15, power=30, xp=520, souls=4, death_function=monster_death)
        ai_component = BasicMonster()
        monster = Object(priest_room[0]+1, priest_room[1]+1, amarath_tile, 'Amarath', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)
        objects.append(monster)

    # Add other monsters and items:
    for room in bsp_rooms:
        new_room = Rect(room[0], room[1], 2, 2)
        place_objects(new_room)

    initialize_fov()

    if dungeon_level >= 11:
        objects.append(fountain_of_life)


def traverse_node(node, dat):
    global map, bsp_rooms

    # Create rooms:
    if tcod.bsp_is_leaf(node):
        minx = node.x + 1
        maxx = node.x + node.w -1
        miny = node.y + 1
        maxy = node.y + node.h - 1

        if maxx == map_width - 1:
            maxx -= 1
        if maxy == map_height - 1:
            maxy -= 1

        if full_rooms == False:
            minx = tcod.random_get_int(None, minx, maxx - min_size + 1)
            miny = tcod.random_get_int(None, miny, maxy - min_size + 1)
            maxx = tcod.random_get_int(None, minx + min_size - 2, maxx)
            maxy = tcod.random_get_int(None, miny + min_size - 2, maxy)

        node.x = minx
        node.y = miny
        node.w = maxx-minx + 1
        node.h = maxy-miny + 1

        # Dig room:
        for x in range(minx, maxx + 1):
            for y in range(miny, maxy + 1):
                map[x][y].blocked = False
                map[x][y].block_sight = False

        bsp_rooms.append(((minx + maxx) // 2, (miny + maxy) // 2))

    else:
        # Create corridors:
        left = tcod.bsp_left(node)
        right = tcod.bsp_right(node)
        node.x = min(left.x, right.x)
        node.y = min(left.y, right.y)
        node.w = max(left.x + left.w, right.x + right.w) - node.x
        node.h = max(left.y + left.h, right.y + right.h) - node.y
        if node.horizontal:
            if left.x + left.w - 1 < right.x or right.x + right.w - 1 < left.x:
                x1 = tcod.random_get_int(None, left.x, left.x + left.w - 1)
                x2 = tcod.random_get_int(None, right.x, right.x + right.w - 1)
                y = tcod.random_get_int(None, left.y + left.h, right.y)
                vline_up(map, x1, y - 1)
                hline(map, x1, y, x2)
                vline_down(map, x2, y + 1)

            else:
                minx = max(left.x, right.x)
                maxx = min(left.x + left.w - 1, right.x + right.w -1)
                x = tcod.random_get_int(None, minx, maxx)

                # catch out of bounds attempts:
                while x > map_width - 1:
                    x -= 1

                vline_down(map, x, right.y)
                vline_up(map, x, right.y - 1)

        else:
            if left.y + left.h - 1 < right.y or right.y + right.h - 1 < left.y:
                y1 = tcod.random_get_int(None, left.y, left.y + left.h - 1)
                y2 = tcod.random_get_int(None, right.y, right.y + right.h - 1)
                x = tcod.random_get_int(None, left.x + left.w, right.x)
                hline_left(map, x - 1, y1)
                vline(map, x, y1, y2)
                hline_right(map, x + 1, y2)
            else:
                miny = max(left.y, right.y)
                maxy = min(left.y + left.h - 1, right.y + right.h - 1)
                y = tcod.random_get_int(None, miny, maxy)

                # Catch out of bounds attempts:
                while y > map_height - 1:
                    y -= 1

                hline_left(map, right.x - 1, y)
                hline_right(map, right.x, y)

    return True

def vline(map, x, y1, y2):
    if y1 > y2:
        y1,y2 = y2,y1

    for y in range(y1, y2 + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def vline_up(map, x, y):
    while y >= 0 and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        y -= 1

def vline_down(map, x, y):
    while y < map_height and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        y += 1

def hline(map, x1, y, x2):
    if x1 > x2:
        x1,x2 = x2,x1

    for x in range(x1, x2 + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def hline_left(map, x, y):
    while x >= 0 and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        x -= 1

def hline_right(map, x, y):
    while x < map_width and map[x][y].blocked == True:
        map[x][y].blocked = False
        map[x][y].block_sight = False
        x += 1

# Def standard map:
def make_map():
    global map, objects, stairs

    sword_tile = 263
    buckler_tile = 264
    fountain_of_life_tile = 288
    book_tile = 273
    merchant_tile = 281
    forgotten_tile = 272
    clare_tile = 285
    stairsdown_tile = 265
    helmet_tile = 274
    star_shield_tile = 275
    chain_mail_tile = 276
    chain_gauntlets_tile = 277
    plate_mail_tile = 278
    morning_star_tile = 279
    boots_tile = 303

    objects = [player]

    map = [
        [Tile(True) for y in range(map_height)]
        for x in range(map_width)
    ]
    # create rooms:
    rooms = []
    num_rooms = 0


    for r in range(max_rooms):
        w = tcod.random_get_int(0, room_min_size, room_max_size)
        h = tcod.random_get_int(0, room_min_size, room_max_size)
        x = tcod.random_get_int(0, 0, map_width - w - 1)
        y = tcod.random_get_int(0, 0, map_height - h - 1)


        new_room = Rect(x, y, w, h)

        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break
        if not failed:
            create_room(new_room)
            (new_x, new_y) = new_room.center()
        if num_rooms == 0:
            player.x = new_x
            player.y = new_y

        else:
            (prev_x, prev_y) = rooms[num_rooms - 1].center()
            if tcod.random_get_int(0, 0, 1) == 1:
                create_h_tunnel(prev_x, new_x, prev_y)
                create_v_tunnel(prev_y, new_y, new_x)
            else:
                create_v_tunnel(prev_y, new_y, prev_x)
                create_h_tunnel(prev_x, new_x, new_y)

        place_objects(new_room)
        rooms.append(new_room)
        num_rooms += 1

    book_x = player.x
    book_y = player.y

    fountain_x = map_width // 2
    fountain_y = map_height // 2 -1

    stairs = Object(new_x, new_y, stairsdown_tile, 'Stairs', tcod.white, always_visible=True)
    objects.append(stairs)
    stairs.send_to_back() # draw stairs below the monsters

    # NPCs:
    merchant_lau = Object(15, 15, merchant_tile, "Merchant Lau", tcod.white, blocks=True, always_visible=True) # define merchant
    
    # Equipment:
    sword_component = Equipment(slot='main hand', power_bonus=3)
    sword = Object(book_x+1, book_y+1, sword_tile, 'Sword', tcod.white, equipment=sword_component)

    buckler_component = Equipment(slot='off hand', defense_bonus=1)
    buckler = Object(book_x+1, book_y+1, buckler_tile, 'Buckler', tcod.white, equipment=buckler_component)

    helmet_component = Equipment(slot='head', defense_bonus=1)
    helmet = Object(new_x+1, new_y+1, helmet_tile, 'Helmet', tcod.white, equipment=helmet_component)

    sshield_component = Equipment(slot='off hand', res_bonus=5)
    sshield = Object(book_x+1, book_y+1, star_shield_tile, 'Star Shield', tcod.white, equipment=sshield_component)

    chainm_component = Equipment(slot='body', defense_bonus=2)
    chainm = Object(book_x+1, book_y+1, chain_mail_tile, 'Chain Mail', tcod.white, equipment=chainm_component)

    chaing_component = Equipment(slot='hands', defense_bonus=1)
    chaing = Object(new_x+1, new_y+1, chain_gauntlets_tile, 'Chain Gauntlets', tcod.white, equipment=chaing_component)

    platem_component = Equipment(slot='body', defense_bonus=4)
    platem = Object(book_x+1, book_y+1, plate_mail_tile, 'Plate Mail', tcod.white, equipment=platem_component)

    plateb_component = Equipment(slot='legs', defense_bonus=1)
    plateb = Object(book_x+1, book_y+1, boots_tile, 'Plate Boots', tcod.white, equipment=plateb_component)

    morning_component = Equipment(slot='main hand', power_bonus=5)
    morning_star = Object(book_x+1, book_y+1, morning_star_tile, 'Morning Star', tcod.white, equipment=morning_component)

    # Books:
    firebite_component = Item(use_book_function=cast_firebite_spell)
    firebite_book = Object(book_x+2, book_y+2, book_tile, 'Firebite Spellbook', tcod.white, item=firebite_component)

    heal_component = Item(use_book_function=cast_heal_spell)
    heal_book = Object(book_x+2, book_y+2, book_tile, 'Healing Spellbook', tcod.white, item=heal_component)

    ice_spike_component = Item(use_book_function=cast_ice_spike_spell)
    ice_spike_book = Object(book_x+2, book_y+2, book_tile, 'Ice Spike Spellbook', tcod.white, item=ice_spike_component)

    storm_component = Item(use_book_function=cast_lightning_storm_spell)
    storm_book = Object(book_x+2, book_y+2, book_tile, 'Lightning Storm Spellbook', tcod.white, item=storm_component)

    # Fountains:
    fountain_life_ai = FountainLifeAI()
    fountain_of_life = Object(fountain_x, fountain_y, fountain_of_life_tile, 'Fountain of Life', tcod.white, blocks=False, ai=fountain_life_ai, always_visible=True)

    #Booss monsters:

    clare_fighter = Enemy(hp=150, defense=4, res=8, power=20, xp=450, mp=3, souls=4, death_function=monster_death)
    clare_ai = ClareAI()
    clare = Object(new_x+2, new_y+1, clare_tile, "Clare", tcod.white, fighter=clare_fighter, ai=clare_ai)

    forgotten_component = Enemy(hp=200, mp=2, defense=4, res=10, power=24, xp=500, souls=4, death_function=monster_death)
    forgotten_ai = ForgottenAI()
    forgotten = Object(new_x+2, new_y+1, forgotten_tile, 'Forgotten', tcod.white, blocks=True, fighter=forgotten_component, ai=forgotten_ai)


    # Place defined objects inside the dungeon:
    if dungeon_level == 2 or dungeon_level == 4 or dungeon_level == 6 or dungeon_level == 8:
        objects.append(merchant_lau)

    if dungeon_level == 1:
        objects.append(firebite_book)
    
    elif dungeon_level == 3:
        objects.append(sword)

    elif dungeon_level == 4:
        objects.append(heal_book)
        objects.append(buckler)
        objects.append(helmet)

    elif dungeon_level == 5:
        objects.append(ice_spike_book)
        objects.append(sshield)
        
    elif dungeon_level == 6:
        objects.append(chainm)
        objects.append(chaing)

    elif dungeon_level == 7:
        objects.append(storm_book)
        objects.append(fountain_of_life)
    
    elif dungeon_level == 8:
        objects.append(plateb)

    elif dungeon_level == 9:
        objects.append(clare)
        objects.append(fountain_of_life)
        objects.append(platem)

    elif dungeon_level == 10:
        objects.append(morning_star)
        objects.append(forgotten)
        objects.append(fountain_of_life)

# Functions for randomizing things in place_objects():
###################################################################################################################

def random_choice_index(chances):
    dice = tcod.random_get_int(0, 1, sum(chances))

    running_sum = 0
    choice = 0
    for w in chances:
        running_sum += w
        if dice <= running_sum:
            return choice
        choice += 1

def random_choice(chances_dict):
    chances = list(chances_dict.values())
    strings = list(chances_dict.keys())

    return strings[random_choice_index(chances)]

def from_dungeon_level(table):
    for (value, level) in reversed(table):
        if dungeon_level >= level:
            return value
    return 0

def get_equipped_in_slot(slot):
    for obj in inventory:
        if obj.equipment and obj.equipment.slot == slot and obj.equipment.is_equipped:
            return obj.equipment
    return None

# Place your monsters, items and other objects here:
################################################################################################################

def place_objects(room):
    skelly_tile = 259
    skelly_warr_tile = 260
    scroll_tile = 261
    healingpotion_tile = 262
    garg_tile = 267
    garg_lance_tile = 292
    wraith_tile = 268
    skelly_mage_tile = 269
    flayed_one_tile = 270
    ghoul_tile = 271
    skelly_archer_tile = 289
    frg_mummy_tile = 294
    scorched_demon_tile = 295
    amarath_tile = 296
    amarath_lord_tile = 297
    anubite_tile = 298
    big_beetle_tile = 307

    #choose random number of monsters
    max_monsters = from_dungeon_level([[2, 1], [3, 4]])
    monster_chances = {}

    monster_chances['skeleton'] = from_dungeon_level([[35, 1], [25, 3], [0, 5]])
    monster_chances['skeletal warrior'] = from_dungeon_level([[15, 2], [16, 4], [0, 6]])
    monster_chances['gargoyle'] = from_dungeon_level([[10, 4], [12, 5], [14, 8], [0, 11]])
    monster_chances['gargoyle lancer'] = from_dungeon_level([[8, 11], [10, 13], [8, 15], [0, 16]])
    monster_chances['forgotten mummy'] = from_dungeon_level([[8, 11], [9, 13], [7, 14], [6, 16], [0, 18]])
    monster_chances['scorched demon'] = from_dungeon_level([[7, 13], [8, 14], [9, 17]])
    monster_chances['flayed one'] = from_dungeon_level([[8, 7], [10, 8], [8, 11], [0, 12]])
    monster_chances['skeletal archer'] = from_dungeon_level([[6, 5], [8, 6], [9, 7], [0, 11]])
    monster_chances['skeletal marksman'] = from_dungeon_level([[8, 11], [9, 13], [7, 14], [0, 16]])
    monster_chances['amarath'] = from_dungeon_level([[7, 14], [8, 16], [9, 18]])
    monster_chances['amarath lord'] = from_dungeon_level([[5, 16], [7, 18]])
    monster_chances['anubite'] = from_dungeon_level([[5, 17], [6, 19]])
    monster_chances['wraith'] = from_dungeon_level([[8, 3], [12, 6], [0, 8]])
    monster_chances['skeletal fire mage'] = from_dungeon_level([[8, 5], [10, 8], [0, 11]])
    monster_chances['ghoul'] = from_dungeon_level([[6, 6], [8, 7], [10, 8], [0, 11]])
    monster_chances['big beetle'] = from_dungeon_level([[5, 14], [6, 15], [7, 16]])


    max_items = from_dungeon_level([[1, 1], [2, 2], [3, 4]])
    item_chances = {}

    item_chances['heal'] = from_dungeon_level([[15, 1], [12, 5], [10, 8], [8, 10], [0, 11]])
    item_chances['great heal'] = from_dungeon_level([[6, 11], [5, 15]])
    item_chances['lightning'] = from_dungeon_level([[6, 3], [8, 5], [5, 8], [0, 11]])
    item_chances['fireball'] = from_dungeon_level([[6, 4], [7, 6], [6, 8], [0, 12]])
    item_chances['frost bolt'] = from_dungeon_level([[5, 8], [3, 12]])
    item_chances['weaken'] = from_dungeon_level([[4, 12], [3,16]])
    item_chances['hellfire'] = from_dungeon_level([[4, 14], [3, 18]])
    item_chances['marduk hand'] = from_dungeon_level([[4, 16], [3,18]])
    item_chances['confuse'] = from_dungeon_level([[5, 2], [6, 4], [0, 5]])


    num_monsters = tcod.random_get_int(0, 0, max_monsters)
    for i in range(num_monsters):
    #choose random spot for this monster
        x = tcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = tcod.random_get_int(0, room.y1 + 1, room.y2 - 1)
        if not is_blocked(x, y):
            choice = random_choice(monster_chances)
            if choice == 'skeleton':
                fighter_component = Enemy(hp=22, mp=0, defense=0, res=0, power=3, xp=40, souls=1, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, skelly_tile, 'Skeleton', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'skeletal warrior':
                fighter_component = Enemy(hp=44, mp=0, defense=1, res=0, power=5, xp=110, souls=1, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, skelly_warr_tile, 'Skeletal Warrior', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'skeletal fire mage':
                fighter_component = Enemy(hp=25, mp=2, defense=0, res=5, power=1, xp=180, souls=2, death_function=monster_death)
                ai_component = SMageMonsterAI()
                monster = Object(x, y, skelly_mage_tile, 'Skeletal Fire Mage', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'skeletal archer':
                fighter_component = Enemy(hp=35, mp=0, defense=0, res=0, power=10, xp=200, souls=2, death_function=monster_death)
                ai_component = SkeletalArcherAI()
                monster = Object(x, y, skelly_archer_tile, 'Skeletal Archer', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'skeletal marksman':
                fighter_component = Enemy(hp=65, mp=0, defense=1, res=5, power=19, xp=300, souls=3, death_function=monster_death)
                ai_component = SkeletalArcherAI()
                monster = Object(x, y, skelly_archer_tile, 'Skeletal Marksman', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'gargoyle lancer':
                fighter_component = Enemy(hp=120, mp=2, defense=3, res=12, power=20, xp=320, souls=3, death_function=monster_death)
                ai_component = GargoyleLancerAI()
                monster = Object(x, y, garg_lance_tile, 'Gargoyle Lancer', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'gargoyle':
                fighter_component = Enemy(hp=44, mp=1, defense=2, res=8, power=10, xp=200, souls=2, death_function=monster_death)
                ai_component = GargoyleAI()
                monster = Object(x, y, garg_tile, 'Gargoyle', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'wraith':
                fighter_component = Enemy(hp=55, mp=0, defense=0, res=5, power=8, xp=160, souls=2, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, wraith_tile, 'Wraith', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'ghoul':
                fighter_component = Enemy(hp=75, mp=0, defense=1, res=0, power=14, xp=240, souls=3, death_function=monster_death)
                ai_component = GhoulAI()
                monster = Object(x, y, ghoul_tile, 'Ghoul', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'flayed one':
                fighter_component = Enemy(hp=105, mp=0, defense=3, res=5, power=16, xp=300, souls=3, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, flayed_one_tile, 'Flayed One', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'forgotten mummy':
                fighter_component = Enemy(hp=155, mp=1, defense=3, res=20, power=24, xp=400, souls=4, death_function=monster_death)
                ai_component = ForgottenMummyAI()
                monster = Object(x, y, frg_mummy_tile, 'Forgotten Mummy', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'scorched demon':
                fighter_component = Enemy(hp=180, mp=5, defense=4, res=30, power=27, xp=480, souls=4, death_function=monster_death)
                ai_component = ScorchedDemonAI()
                monster = Object(x, y, scorched_demon_tile, 'Scorched Demon', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'amarath':
                fighter_component = Enemy(hp=220, mp=0, defense=4, res=15, power=30, xp=520, souls=4, death_function=monster_death)
                ai_component = BasicMonster()
                monster = Object(x, y, amarath_tile, 'Amarath', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'amarath lord':
                fighter_component = Enemy(hp=240, mp=2, defense=5, res=25, power=32, xp=650, souls=5, death_function=monster_death)
                ai_component = AmarathLordAI()
                monster = Object(x, y, amarath_lord_tile, 'Amarath Lord', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'anubite':
                fighter_component = Enemy(hp=160, mp=3, defense=3, res=40, power=25, xp=650, souls=5, death_function=monster_death)
                ai_component = AnubiteAI()
                monster = Object(x, y, anubite_tile, 'Anubite', tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            elif choice == 'big beetle':
                fighter_component = Enemy(hp=200, mp=2, defense=5, res=20, power=28, xp=580, souls=3, death_function=monster_death)
                ai_component = BigBeetleAI()
                monster = Object(x, y, big_beetle_tile, "Big Beetle", tcod.white, blocks=True, fighter=fighter_component, ai=ai_component)

            objects.append(monster)


    num_items = tcod.random_get_int(0, 0, max_items)

    for i in range(num_items):
        x = tcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = tcod.random_get_int(0, room.y1 + 1, room.y2 - 1)
        if not is_blocked(x, y):
            choice = random_choice(item_chances)
            if choice == 'heal':
                item_component = Item(use_function=cast_heal)
                item = Object(x, y, healingpotion_tile, 'Healing Potion', tcod.white, item=item_component)

            elif choice == 'great heal':
                item_component = Item(use_function=cast_great_heal)
                item = Object(x, y, healingpotion_tile, 'Greater Healing Potion', tcod.white, item=item_component)

            elif choice == 'lightning':
                item_component = Item(use_function=cast_lightning)
                item = Object(x, y, scroll_tile, 'Scroll of Lightning', tcod.white, item=item_component)

            elif choice == 'fireball':
                item_component = Item(use_function=cast_fireball)
                item = Object(x, y, scroll_tile, 'Scroll of Fireball', tcod.white, item=item_component)

            elif choice == 'frost bolt':
                item_component = Item(use_function=frost_bolt)
                item = Object(x, y, scroll_tile, 'Scroll of Frost Bolt', tcod.white, item=item_component)

            elif choice == 'marduk hand':
                item_component = Item(use_function=cast_hand_of_marduk)
                item = Object(x, y, scroll_tile, "Marduk's Scroll", tcod.white, item=item_component)

            elif choice == 'weaken':
                item_component = Item(use_function=cast_weaken)
                item = Object(x, y, scroll_tile, "Scroll of Weaken", tcod.white, item=item_component)

            elif choice == 'hellfire':
                item_component = Item(use_function=cast_hellfire)
                item = Object(x, y, scroll_tile, "Scroll of Hellfire", tcod.white, item=item_component)

            elif choice == 'confuse':
                item_component = Item(use_function=cast_confuse)
                item = Object(x, y, scroll_tile, 'Scroll of Confusion', tcod.white, item=item_component)

            objects.append(item)
            item.send_to_back()


# Function to render everything to the screen:
################################################################################################################

def render_all():
    global fov_map, fov_recompute
    global key, mouse
    wall_tile = 256
    floor_tile = 257
    pir_floor_tile = 290
    pir_wall_tile = 291

    level_up_xp = level_up_base + player.level * level_up_factor
    if fov_recompute:
        fov_recompute = False
        tcod.map_compute_fov(fov_map, player.x, player.y, torch_radius, fov_light_walls, fov_algo)

        for y in range(map_height):
            for x in range(map_width):
                if dungeon_level <= 10:
                    visible = tcod.map_is_in_fov(fov_map, x, y)
                    wall = map[x][y].block_sight
                    if not visible:
                        if map[x][y].explored:
                            if wall:
                                tcod.console_put_char_ex(con, x, y, wall_tile, tcod.grey, tcod.black) # tile if wall not explored
                            else:
                                tcod.console_put_char_ex(con, x, y, floor_tile, tcod.grey, tcod.black) # tile if ground
                    else:
                        if wall:
                            tcod.console_put_char_ex(con, x, y, wall_tile, tcod.white, tcod.black) #explored
                        else:
                            tcod.console_put_char_ex(con, x, y, floor_tile, tcod.white, tcod.black) #bkgnd explored
                        map[x][y].explored = True

                else:
                    visible = tcod.map_is_in_fov(fov_map, x, y)
                    wall = map[x][y].block_sight
                    if not visible:
                        if map[x][y].explored:
                            if wall:
                                tcod.console_put_char_ex(con, x, y, pir_wall_tile, tcod.grey, tcod.black) #not already explored
                            else:
                                tcod.console_put_char_ex(con, x, y, pir_floor_tile, tcod.grey, tcod.black) #bkgnd not explored
                    else:
                        if wall:
                            tcod.console_put_char_ex(con, x, y, pir_wall_tile, tcod.white, tcod.black) #explored
                        else:
                            tcod.console_put_char_ex(con, x, y, pir_floor_tile, tcod.white, tcod.black) #bkgnd explored
                        map[x][y].explored = True

    for object in objects: # draw various objects on the screen
        if object != player:
            object.draw()
        player.draw()

    tcod.console_blit(con, 0, 0, map_width, map_height, 0, 0, 0)
    tcod.console_set_default_background(panel, tcod.black)
    tcod.console_clear(panel)
    y = 1
    for (line, color) in game_msgs:
        tcod.console_set_default_foreground(panel, color)
        tcod.console_print_ex(panel, msg_x, y, tcod.BKGND_NONE, tcod.LEFT, line)
        y += 1


    if player.fighter.hp <= (player.fighter.max_hp/2) and player.fighter.hp > (player.fighter.max_hp/3):
        render_bar(1, 1, bar_width, 'HP', player.fighter.hp, player.fighter.max_hp, tcod.orange, tcod.black)
    elif player.fighter.hp <= (player.fighter.max_hp/3):
        render_bar(1, 1, bar_width, 'HP', player.fighter.hp, player.fighter.max_hp, tcod.red, tcod.black)
    render_bar(1, 1, bar_width, 'HP', player.fighter.hp, player.fighter.max_hp, tcod.darker_green, tcod.black)
    render_bar(1, 2, bar_width, 'MP', player.fighter.mp, player.fighter.max_mp, tcod.blue, tcod.black)
    render_bar(1, 3, bar_width, 'XP', player.fighter.xp, level_up_xp, tcod.violet, tcod.black)
    tcod.console_print_ex(panel, 1, 4, tcod.BKGND_NONE, tcod.LEFT, f"Dungeon level {dungeon_level}")
    tcod.console_set_default_foreground(panel, tcod.light_gray)
    tcod.console_print_ex(panel, 1, 0, tcod.BKGND_NONE, tcod.LEFT, get_names_under_mouse())
    tcod.console_blit(panel, 0, 0, screen_width, screen_height, 0, 0, panel_y)

def player_move_or_attack(dx, dy):
    global fov_recompute
    x = player.x + dx
    y = player.y + dy

    target = None
    for object in objects:
        if object.fighter and object.x == x and object.y == y:
            target = object
            break
    if target is not None:
        player.fighter.attack(target)
        fov_recompute = True
    else:
        player.move(dx, dy)
        fov_recompute = True

# Function for menu generation:
################################################################################################################
def menu(header, options, width):

    if len(options) > 26:
        raise ValueError('Cannot have more than 26 options.')
    header_height = tcod.console_get_height_rect(con, 0, 0, width, screen_height, header)
    if header == '':
        header_height = 0
    height = len(options) + header_height
    window = tcod.console_new(width, height)
    tcod.console_set_default_foreground(window, tcod.white)
    tcod.console_print_rect_ex(window, 0, 0, width, height, tcod.BKGND_NONE, tcod.LEFT, header)

    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = f"({chr(letter_index)}) {option_text}"
        tcod.console_print_ex(window, 0, y, tcod.BKGND_NONE, tcod.LEFT, text)
        y += 1
        letter_index += 1
    x = screen_width // 2 - width // 2
    y = screen_height // 2 - height // 2
    tcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)
    tcod.console_flush()
    key = tcod.console_wait_for_keypress(True)

    index = key.c - ord('a')
    if index >= 0 and index < len(options): return index
    return None

def inventory_menu(header):

    if len(inventory) == 0:
        options = ['Inventory is empty.']
    else:
        options = []
        for item in inventory:
            text = item.name
            if item.equipment and item.equipment.is_equipped:
                text = f"{text} (on {item.equipment.slot})"
            options.append(text)

    index = menu(header, options, inventory_width)
    if index is None or len(inventory) == 0: return None
    return inventory[index].item



# User Input
# ##########################################################################################

def handle_keys():
    global key
    global player_x, player_y
    global fov_recompute

    if key.vk == tcod.KEY_ENTER and key.lalt:
# Alt+Enter: toggle fullscreen
        tcod.console_set_fullscreen(not tcod.console_is_fullscreen())

    elif key.vk == tcod.KEY_ESCAPE:
        return 'exit'  # exit game

    # movement keys
    key_char = chr(key.c)

    if game_state == 'playing':
        if key.vk == tcod.KEY_UP or key_char == 'k':
            player_move_or_attack(0, -1)
            fov_recompute = True

        elif key.vk == tcod.KEY_DOWN or key_char == 'j':
            player_move_or_attack(0, 1)
            fov_recompute = True

        elif key.vk == tcod.KEY_LEFT or key_char == 'h':
            player_move_or_attack(-1, 0)
            fov_recompute = True

        elif key.vk == tcod.KEY_RIGHT or key_char == 'l':
            player_move_or_attack(1, 0)
            fov_recompute = True

        # diagonal keys (vim keys)
        elif key_char == 'z': # I use QERTZ keyboard, change this to 'y' if QWERTY
            player_move_or_attack(-1, -1)
            fov_recompute = True
        elif key_char == 'u':
            player_move_or_attack(1, -1)
            fov_recompute = True
        elif key_char == 'b':
            player_move_or_attack(-1, 1)
            fov_recompute = True
        elif key_char == 'n':
            player_move_or_attack(1, 1)
            fov_recompute = True

        elif key_char == 'q':
            for object in objects:
                if object.x == player.x and object.y == player.y and object.item:
                    object.item.pick_up()
                    break
            fov_recompute = True

        elif key_char == 'w':
            chosen_item = inventory_menu("Press the key next to an item to use it, or any other to cancel.\n")
            if chosen_item is not None:
                chosen_item.use()

        elif key_char == 'e':
            chosen_item = inventory_menu("Press the key next to an item to drop it, or any other to cancel.\n")
            if chosen_item is not None:
                chosen_item.drop()

        elif key_char == 'r':
            chosen_item = inventory_menu('Press the key next to the Spellbook to use it, or any other to cancel.\n')
            if chosen_item is not None:
                chosen_item.use_spellbook()
            fov_recompute = True

        else:
            if key_char == 's':
                if stairs.x == player.x and stairs.y == player.y:
                    next_level()
                elif dungeon_level < 11:
                    merchant_tile = 281
                    merchant_lau = Object(15, 15, merchant_tile, "Merchant Lau", tcod.white, blocks=True, always_visible=True) # define merchant

                    if merchant_lau.distance_to(player) <= 2:
                        buy_wares()
                else:
                    merchant_tile = 281
                    merchant_hei = Object(20, 20, merchant_tile, "Merchant Hei", tcod.white, blocks=True, always_visible=True)
                    if merchant_hei.distance_to(player) <= 2:
                        buy_goods()

            elif key_char == 'c':
                level_up_xp = level_up_base + player.level * level_up_factor
                msgbox(f"Character Information\n\nLevel: {player.level} \nExperience: {player.fighter.xp}"
                f" Souls: {player.fighter.souls} \nExperience to level up: {level_up_xp} \n\nMaximum HP:"
                f" {player.fighter.max_hp} Maximum MP: {player.fighter.max_mp} \nAttack: {player.fighter.power}"
                f" \nDefense: {player.fighter.defense} Resistance: {player.fighter.res}", character_screen_width)
            
            elif key_char == "i":
                msgbox("Controls:\n\nArrows,vim keys: movement\nq: pick up item\nw: open inventory\ne: drop items\nr: use spellbooks\n"
                        "s: use stairs, buy from merchant\nc: character info\nALT + Enter: toggle fullscreen\nEscape: main menu")


            return 'didnt-take-turn'


def get_names_under_mouse():
    global mouse
    (x, y) = (mouse.cx, mouse.cy)

    names = [obj.name for obj in objects
        if obj.x == x and obj.y == y and tcod.map_is_in_fov(fov_map, obj.x, obj.y)]
    names = ', '.join(names)
    return names

def player_death(player):
    global game_state
    message(f"{player.name} died!", tcod.red)
    game_state = 'dead'


def check_level_up():
    level_up_xp = level_up_base + player.level * level_up_factor
    if player.fighter.xp >= level_up_xp:
        player.level += 1
        player.fighter.xp -= level_up_xp
        message(f"Honing skills in battle give {player.name} more strength! {player.name} has reached level {player.level}!", tcod.yellow)
        choice = None
        while choice == None:
            choice = menu('Level up! Choose a stat to raise:\n',
                ['Constitution (+20 HP)',
                'Strength (+2 attack power)',
                'Dexterity (+1 defense)',
                'Resistance (+5 resistance)',
                'Mana (+2 mana points)'], level_screen_width)

        if choice == 0:
            player.fighter.base_max_hp += 20
            player.fighter.hp += 20
            player.fighter.heal(500)
            player.fighter.rejuvenate(100)
        elif choice == 1:
            player.fighter.base_power += 2
            player.fighter.heal(500)
            player.fighter.rejuvenate(100)
        elif choice == 2:
            player.fighter.base_defense += 1
            player.fighter.heal(500)
            player.fighter.rejuvenate(100)
        elif choice == 3:
            player.fighter.base_res += 5
            player.fighter.heal(500)
            player.fighter.rejuvenate(100)
        elif choice == 4:
            player.fighter.base_max_mp += 2
            player.fighter.mp += 2
            player.fighter.heal(500)
            player.fighter.rejuvenate(100)


def monster_death(monster):
    claymore_tile = 284
    frg_amulet_tile = 286
    red_dagger_tile = 306
    death_tile = 280

    if monster.name == "Clare":
        claymore_component = Equipment(slot='main hand', power_bonus=6, defense_bonus=-1)
        claymore = Object(monster.x, monster.y, claymore_tile, "Clare's Claymore", tcod.white, blocks=False, equipment=claymore_component)
        objects.append(claymore)

    elif monster.name == "Forgotten":
        frg_amulet_effects = Equipment(slot='neck', defense_bonus=2, res_bonus=5, power_bonus=2)
        frg_amulet = Object(monster.x, monster.y, frg_amulet_tile, 'Forgotten Amulet', tcod.white, blocks=False, equipment=frg_amulet_effects)
        objects.append(frg_amulet)

    elif monster.name == "Royal Guard" and dungeon_level == 19:
        red_dagger_effects = Item(use_book_function=sacrifice)
        red_dagger = Object(monster.x, monster.y, red_dagger_tile, 'Sangre Eterna', tcod.white, blocks=False, item=red_dagger_effects)
        objects.append(red_dagger)

    message(f"{monster.name} is dead! {player.name} gains {monster.fighter.xp} XP and {monster.fighter.souls} souls.", tcod.orange)
    monster.char = death_tile
    monster.color = tcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = f"Remains of {monster.name}"
    monster.send_to_back()

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    bar_width = int(float(value) / maximum * total_width)

    tcod.console_set_default_background(panel, back_color)
    tcod.console_rect(panel, x, y, total_width, 1, False, tcod.BKGND_SCREEN)

    tcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        tcod.console_rect(panel, x, y, bar_width, 1, False, tcod.BKGND_SCREEN)
    tcod.console_set_default_foreground(panel, tcod.white)
    stats =  f"{name}: {value}/{maximum}"
    tcod.console_print_ex(panel, int(x + total_width / 2), y, tcod.BKGND_NONE, tcod.CENTER, stats)

# Functions for saving and loading a game:
#############################################################################################################

def load_customfont():
    #The index of the first custom tile in the file
    a = 256

    #The "y" is the row index, here we load the sixth row in the font file. Increase the "6" to load any new rows from the file
    for y in range(5,7):
        tcod.console_map_ascii_codes_to_font(a, 32, 0, y)
        a += 32

def save_game():
    file = shelve.open('savegame', 'n')
    file['map'] = map
    file['objects'] = objects
    file['player_index'] = objects.index(player)
    file['inventory'] = inventory
    file['game_msgs'] = game_msgs
    file['game_state'] = game_state
    file['stairs_index'] = objects.index(stairs)
    file['dungeon_level'] = dungeon_level
    file.close()

def load_game():
    global map, objects, player, inventory, game_msgs, game_state, stairs, dungeon_level
    file = shelve.open('savegame', 'r')
    map = file['map']
    objects = file['objects']
    player = objects[file['player_index']]
    inventory = file['inventory']
    game_msgs = file['game_msgs']
    game_state = file['game_state']
    stairs = objects[file['stairs_index']]
    dungeon_level = file['dungeon_level']
    file.close()

    initialize_fov()

# Main functions for starting and playing a game:
##########################################################################################################################

def next_level():
    global dungeon_level
    message(f"{player.name} takes a rare chance to rest and recover stamina.", tcod.light_violet)
    player.fighter.heal(player.fighter.max_hp / 2) # heal the player
    player.fighter.rejuvenate(player.fighter.max_mp)

    message(f"After a moment of peace, {player.name} descends deeper into the dungeon.", tcod.red)
    dungeon_level += 1
    make_map()
    initialize_fov()

    if dungeon_level > 10:
        make_bsp_map()


def msgbox(text, width=50):
    menu(text, [], width)

def new_game():
    global player, inventory, game_msgs, game_state, dungeon_level

    dagger_tile = 266
    player_tile = 258

    fighter_component = Player(hp=100, defense=0, res=0, power=4, xp=0, mp=2, souls=0, death_function=player_death)
    player = Object(0, 0, player_tile, 'Reziel', tcod.white, blocks=True, fighter=fighter_component)
    dungeon_level = 1
    player.level = 1
    # Generate map
################################################
    make_map()

    initialize_fov()

    game_state = 'playing'
    inventory = []
    game_msgs = []
    message(f"Help {player.name} fight through and escape from the Tombs of the Forgotten!", tcod.light_blue)

    equipment_component = Equipment(slot='main hand', power_bonus=2)
    obj = Object(0, 0, dagger_tile, 'Dagger', tcod.white, equipment=equipment_component)
    inventory.append(obj)
    equipment_component.equip()
    obj.always_visible = True

def initialize_fov():
    global fov_recompute, fov_map
    fov_recompute = True
    fov_map = tcod.map_new(map_width, map_height)
    for y in range(map_height):
        for x in range(map_width):
            tcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

    tcod.console_clear(con)


def play_game():
    global key, mouse
    player_action = None

    mouse = tcod.Mouse()
    key = tcod.Key()

# Main loop
########################################################################################################
    while not tcod.console_is_window_closed():
        tcod.sys_check_for_event(tcod.EVENT_KEY_PRESS|tcod.EVENT_MOUSE, key, mouse)

        load_customfont()

        render_all()

        tcod.console_flush()
        check_level_up()
        for object in objects:
            object.clear()

        player_action = handle_keys()
        if player_action == 'exit':
            save_game()
            break

        if game_state == 'playing' and player_action != 'didnt-take-turn':
            for object in objects:
                if object.ai:
                    object.ai.take_turn()

        if dungeon_level == 21:
            msgbox(f"\nCongratulations! {player.name} escaped the tombs and survived the Forgotten!\n", 30) # win message
            print(f'Congratulations! {player.name} escaped the tombs and survived the Forgotten!') # print to the console if player doesn't see win msg
            break


def main_menu():
    img = tcod.image_load('background.png')

    while not tcod.console_is_window_closed():
        tcod.image_blit_2x(img, 0, 0, 0)

        choice = menu('', ['Play a new game', 'Continue last game', 'Quit'], 24)
        if choice == 0:
            new_game()
            play_game()
        if choice == 1:
            try:
                load_game()
            except:
                msgbox('\n No saved game to load.\n', 24)
                continue
            play_game()
        elif choice == 2:
            break

# Setup Font
font_filename = 'Tiles.png'
tcod.console_set_custom_font(font_filename, tcod.FONT_TYPE_GREYSCALE | tcod.FONT_LAYOUT_TCOD, 32, 10)

# Initialize screen
title = 'Tombs of the Forgotten'
tcod.console_init_root(screen_width, screen_height, title, False)
con = tcod.console_new(map_width, map_height)

# Set FPS
tcod.sys_set_fps(limit_fps)
panel = tcod.console_new(screen_width, panel_height)

main_menu()
