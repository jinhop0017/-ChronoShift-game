"""
Load a map stored in csv format, as exported by the program 'Tiled.'
"""
import arcade
import math
import random
import time

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# How many pixels to keep as a minimum margin between the character
# and the edge of the screen.
VIEWPORT_MARGIN = 300
D_MARGIN = 300

TILE_SIZE = 32
MAP_HEIGHT = 18

# Physics
MOVEMENT_SPEED = 8
JUMP_SPEED = 15
GRAVITY = 0.2

# Player health
HEALTH = 100


def get_map(filename):
    """
    This function loads an array based on a map stored as a list of
    numbers separated by commas.
    """

    # Open the file
    map_file = open(filename)

    # Create an empty list of rows that will hold our map
    map_array = []

    # Read in a line from the file
    for line in map_file:

        # Strip the whitespace, and \n at the end
        line = line.strip()

        # This creates a list by splitting line everywhere there is a comma.
        map_row = line.split(",")

        # The list currently has all the numbers stored as text, and we want it
        # as a number. (e.g. We want 1 not "1"). So loop through and convert
        # to an integer.
        for index, item in enumerate(map_row):
            map_row[index] = int(item)

        # Now that we've completed processing the row, add it to our map array.
        map_array.append(map_row)

    # Done, return the map.
    return map_array


class Enemy(arcade.Sprite):
    """ Class for the enemy and their sprite """
    
    def __init__(self, image_file, scale, turret_type, bullet_list, target):
        super().__init__(image_file, scale)
        
        # Get the turret texture in order to use it as a bullet texture
        self.image_file = image_file
        
        # chang the values of turret stats depending on the turret type
        if turret_type == "normal":
            self.health = 2
            self.time_between_firing = 3
            self.bullet_speed = 6.5
            self.bullet_size = 1
            self.bullet_damage = 1
            
        if turret_type == "sniper":
            self.health = 1
            self.time_between_firing = 6
            self.bullet_speed = 30
            self.bullet_size = 0.65
            self.bullet_damage = 2
            
        if turret_type == "destroyer":
            self.health = 4
            self.time_between_firing = 4
            self.bullet_speed = 5.2
            self.bullet_size = 1
            self.bullet_damage = 3
            
        if turret_type == "machine gun":
            self.health = 1
            self.time_between_firing = 0.3
            self.bullet_speed = 8.45
            self.bullet_size = 0.7
            self.bullet_damage = 1
            
        # How long has it been since we last fired?
        if self.time_between_firing >= 1:
            self.time_since_last_firing = random.randrange(0, self.time_between_firing - 1) + random.randrange(1, 10)/10
        else:
            self.time_since_last_firing = 0
            
        # Make the bullet list
        self.bullet_list = bullet_list
    
        # Set the bullet timer
        self.bullet_timer = 0
        
        # Set the target
        self.target = target
        
    def on_update(self, delta_time: float = 1/60):
        self.time_since_last_firing += delta_time
        
        # If we are past the firing time, then fire
        if self.time_since_last_firing >= self.time_between_firing:

            # Reset timer
            self.time_since_last_firing = 0

            # Spawn the bullet
            bullet = arcade.Sprite(self.image_file, self.bullet_size)       
            
            # Set the bullet damage
            bullet.damage = self.bullet_damage
            
            # Set the bullet spawn position
            bullet.center_x = self.center_x
            bullet.center_y = self.center_y
            
            # Calculate where the bullet would fire by using a little trig
            y_diff = bullet.center_y - self.target.center_y
            x_diff = bullet.center_x - self.target.center_x
            distance = math.sqrt(x_diff**2 + y_diff**2)
            
            # Fire the bullet with the consistant speed such that
            # as long as the bullet is from the same turret type
            # their bullet speed will be the same no matter where
            # it is firing
            bullet.change_y = (-y_diff/distance) * self.bullet_speed
            bullet.change_x = (-x_diff/distance) * self.bullet_speed
            self.bullet_list.append(bullet)


class MyGame(arcade.Window):
    """ Main application class. """

    def __init__(self):
        """ Initializer """
        
        # Call the parent class
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Sprite lists
        self.player_list = None
        self.wall_list = None
        self.mimic_list = None
        self.enemy_list = None
        self.bullet_list = None
        self.next_level_list = None
        self.kill_barrier_list = None
        self.player_bullet_list = None
        self.cutscene_list = None
        
        # Set up the player
        self.player_sprite = arcade.AnimatedTimeSprite()
        self.player_sprite.textures = []
        
        # Set up the mimic
        self.mimic_sprite = arcade.AnimatedTimeSprite()
        self.mimic_sprite.textures = []           
        
        # Cordinates
        self.player_cordinates_x = []
        self.player_cordinates_y = []

        # Direction of the player
        self.player_direction = None
        
        # Player Health
        self.player_health = None
        
        # If player is alive or not
        self.player_death = None        
        
        # Loading the sounds
        self.time_stop_sound = arcade.load_sound("data/sound effects/player/time stop.ogg")
        self.time_slow_sound = arcade.load_sound("data/sound effects/player/time slow.ogg")
        self.shoot_sound = arcade.load_sound("data/sound effects/player/shoot.ogg")
        self.kill_sound = arcade.load_sound("data/sound effects/player/kill.ogg")
        self.respawn_sound = arcade.load_sound("data/sound effects/player/respawn.ogg")
        self.background_sound = arcade.load_sound("data/sound effects/environment/background.ogg")
        self.hit_sound = arcade.load_sound("data/sound effects/player/hit.ogg")
        
        # Scores
        self.score = 0
        self.saved_score = 0
        
        # This is for switiching positions with mimic
        self.recall = False

        # Physics engine
        self.physics_engine = None

        # Used for scrolling map 
        self.view_left = 0
        self.view_bottom = 0
        
        # Set the time meter
        self.time_meter = None   
        
        # Which level the player is at
        self.level = 0
        
        # What kind of cutscene the game is at
        self.cutscene_count = 0
        
        # Play the background music
        arcade.play_sound(self.background_sound, 0.06)
        
        # Type of ending player got
        self.ending = None
        
        # A switch for endings to properly work
        self.switch = None
        
    def setup(self, level):
        """ Set up the game and initialize the variables. """
        
        # This is so I can reset the player score to where it was
        # before entering the level when the player dies
        self.score = self.saved_score
        
        # Cordinates
        self.player_cordinates_x = []
        self.player_cordinates_y = []        
        
        # Used for slowing down time
        self.time_count = 0
        self.time_slow = 0
        
        # Mimic start timer 
        self.mimic_timer = 0        
        
        # sprite lists
        self.player_list = arcade.SpriteList()
        self.mimic_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()  
        self.wall_list = arcade.SpriteList()
        self.kill_barrier_list = arcade.SpriteList()
        self.next_level_list = arcade.SpriteList()
        self.player_bullet_list = arcade.SpriteList()
        self.cutscene_list = arcade.SpriteList()
        
        # Load player texture
        for i in range(4):
            self.player_sprite.textures.append(arcade.load_texture("data/sprites/player/player_sprite.png", x=i*32, y=0, width = 32, height = 32))        
        
        # player health
        self.player_health = HEALTH
        
        # player death state:
        self.player_death = False
        
        # player direction:
        self.player_direction = "+"
        
        # Load mimic texture
        self.mimic_sprite.textures.append(arcade.load_texture("data/sprites/player/player_sprite.png", x=32, y=0, width = 32, height = 32))        
        
        # Time meter
        self.time_meter = 100
        
        # Get a 2D array made of numbers based on which level the player is at
        if self.level == 0:
            map_array = get_map("data/levels/csv version/screen0.csv")
            
            # Level 0 is a cutscene stage so if it is level 0 then add a cutscene sprite
            cutscene = arcade.Sprite("data/sprites/cutscenes/cutscene 0.png")
            
        if self.level == 1:
            map_array = get_map("data/levels/csv version/screen1.csv")
        if self.level == 2:
            map_array = get_map("data/levels/csv version/screen2.csv")
        if self.level == 3:
            map_array = get_map("data/levels/csv version/screen3.csv")
        if self.level == 4:
            map_array = get_map("data/levels/csv version/screen4.csv")
        if self.level == 5:
            map_array = get_map("data/levels/csv version/screen5.csv")
        if self.level == 6:
            map_array = get_map("data/levels/csv version/screen6.csv")
        
        # Now that we've got the map, loop through and create the sprites
        for row_index in range(len(map_array)):
            for column_index in range(len(map_array[row_index])):
                item = map_array[row_index][column_index]

                # For this map, the numbers represent:
                # 0  = groud
                # 1  = platform
                # 2  = standard turret
                # 3  = sniper turret
                # 4  = machine gun turret
                # 5  = destroyer turret
                if item == 0:
                    self.wall_sprite = arcade.Sprite("data/sprites/stage/ground.png")
                elif item == 1:
                    self.wall_sprite = arcade.Sprite("data/sprites/stage/block.png")

                # Calculate where the sprite goes                
                if item == 0 or item == 1:
                    self.wall_sprite.center_x = column_index * TILE_SIZE + 16
                    self.wall_sprite.center_y = (MAP_HEIGHT - row_index) * TILE_SIZE + 16

                    # Add the sprite
                    self.wall_list.append(self.wall_sprite)
                
                # Place the turrets
                if item >= 2 and item <= 5:
                    if item == 2:
                        turret = Enemy("data/sprites/enemies/standard turret.png", 1, "normal", self.bullet_list, self.player_sprite)
                    elif item == 3:
                        turret = Enemy("data/sprites/enemies/sniper turret.png", 1, "sniper", self.bullet_list, self.player_sprite)
                    elif item == 4:
                        turret = Enemy("data/sprites/enemies/machine gun turret.png", 1, "machine gun", self.bullet_list, self.player_sprite)
                    elif item == 5:
                        turret = Enemy("data/sprites/enemies/destroyer turret.png", 1, "destroyer", self.bullet_list, self.player_sprite)
                    
                    # Calculate where the sprite goes
                    turret.center_x = column_index * TILE_SIZE + 16
                    turret.center_y = (MAP_HEIGHT - row_index) * TILE_SIZE + 16
                    self.enemy_list.append(turret)
                
                # Sprites for kill barriers and respawn points as well as goals for each level
                if item == 6:
                    self.kill_barrier_sprite = arcade.Sprite("data/sprites/stage/kill barrier.png")
                    self.kill_barrier_sprite.center_x = column_index * TILE_SIZE + 16
                    self.kill_barrier_sprite.center_y = (MAP_HEIGHT - row_index) * TILE_SIZE + 16                    
                    self.kill_barrier_list.append(self.kill_barrier_sprite)
                if item == 7:
                    self.next_level_sprite = arcade.Sprite("data/sprites/stage/next level.png")
                    self.next_level_sprite.center_x = column_index * TILE_SIZE + 16
                    self.next_level_sprite.center_y = (MAP_HEIGHT - row_index) * TILE_SIZE + 16                    
                    self.next_level_list.append(self.next_level_sprite)
                if item == 8:
                    self.spawn_point = arcade.Sprite("data/sprites/stage/spawn.png")
                    self.spawn_point.center_x = column_index * TILE_SIZE + 16
                    self.spawn_point.center_y = (MAP_HEIGHT - row_index) * TILE_SIZE + 16
        
        # Add both the player and the mimic in the spritelist
        self.player_sprite.center_x = self.spawn_point.center_x
        self.player_sprite.center_y = self.spawn_point.center_y
        self.player_list.append(self.player_sprite)
        self.mimic_list.append(self.mimic_sprite)
        
        # Also spawn cutscene at the location of the player if its at stage 0
        if self.level == 0:
            cutscene.center_x = self.player_sprite.center_x + 100
            cutscene.center_y = self.player_sprite.center_y
            self.cutscene_list.append(cutscene)
        
        # Create out platformer physics engine with gravity
        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite,
                                                             self.wall_list,
                                                             gravity_constant=GRAVITY)

        # Set the background color
        arcade.set_background_color(arcade.color.BLACK)

        # Set the view port boundaries
        # These numbers set where we have 'scrolled' to.
        self.view_left = 0
        self.view_bottom = 0
        
        # A switch for endings to properly work
        self.switch = False        

    def on_draw(self):
        """ Render the screen. """
        
        # This command has to happen before we start drawing
        arcade.start_render()

        # Draw all the sprites.
        self.wall_list.draw()
        self.player_list.draw()
        self.enemy_list.draw()
        self.mimic_list.draw()
        self.bullet_list.draw()
        self.next_level_list.draw()
        self.kill_barrier_list.draw()
        
        # If there is anything in the bullet list
        # then draw
        if len(self.player_bullet_list):
            self.player_bullet_list.draw()
        
        # Draw the hud
        arcade.draw_text("Health: " + str(self.player_health), self.player_sprite.center_x - 160, self.player_sprite.center_y + 100, arcade.color.GREEN)
        arcade.draw_text("Score: " + str(self.score), self.player_sprite.center_x + 100, self.player_sprite.center_y + 100, arcade.color.GREEN)
        arcade.draw_text("Chronos: " + str(round(self.time_meter)), self.player_sprite.center_x + 100, self.player_sprite.center_y + 80, arcade.color.GREEN)
        arcade.draw_text("Q: Rewind Time", self.player_sprite.center_x - 165, self.player_sprite.center_y - 60, arcade.color.GREEN)        
        
        # Depending on which ability the player unlocked, display a different text according to it
        if self.score >= 1000 and self.score < 3300:
            arcade.draw_text("Shift: Slow Time", self.player_sprite.center_x - 165, self.player_sprite.center_y - 80, arcade.color.GREEN)
        if self.score >= 3300:
            arcade.draw_text("Shift: Impowered Slow Time", self.player_sprite.center_x - 165, self.player_sprite.center_y - 80, arcade.color.GREEN)
        if self.score >= 1800 and self.score < 4300:
            arcade.draw_text("Space: Stop Time", self.player_sprite.center_x - 165, self.player_sprite.center_y - 100, arcade.color.GREEN)
        if self.score >= 4300:
            arcade.draw_text("Space: Impowered Stop Time", self.player_sprite.center_x - 165, self.player_sprite.center_y - 100, arcade.color.GREEN)
        
        # Give player the notification for unlocking abilities
        if self.score == 1000:
            arcade.draw_text("! Unlocked slow time !", self.player_sprite.center_x - 65, self.player_sprite.center_y + 50, arcade.color.RED)
        if self.score == 1800:
            arcade.draw_text("! Unlocked stop time !", self.player_sprite.center_x - 65, self.player_sprite.center_y + 50, arcade.color.RED)
        if self.score == 3300:
            arcade.draw_text("! Unlocked IMPROVED slow time !", self.player_sprite.center_x - 65, self.player_sprite.center_y + 50, arcade.color.RED)
        if self.score == 4300:
            arcade.draw_text("! Unlocked IMPROVED stop time !", self.player_sprite.center_x - 65, self.player_sprite.center_y + 50, arcade.color.RED)
        
        # If the level is 0 which is a cutscene level the draw the cutscene
        if self.level == 0:
            self.cutscene_list.draw()
    
    def on_key_press(self, key, modifiers):
        """ Called whenever the key is pressed. """
        
        if key == arcade.key.W and self.level != 0:
            # This line below is new. It checks to make sure there is a platform underneath
            # the player. Because you can't jump if there isn't ground beneath your feet.
            if self.physics_engine.can_jump():
                self.player_sprite.change_y = JUMP_SPEED
        
        elif key == arcade.key.A:
            # Clear out the list            
            self.player_sprite.textures = []
            
            # Add new animation
            for i in range(4):
                self.player_sprite.textures.append(arcade.load_texture("data/sprites/player/player_sprite.png", x=i*32, y=64, width = 32, height = 32))
            
            # Change the direction
            self.player_sprite.change_x = -MOVEMENT_SPEED
            self.player_direction = "-"
            
        elif key == arcade.key.D:
            # Clear out the list
            self.player_sprite.textures = []
            
            # Add new animation
            for i in range(4):
                self.player_sprite.textures.append(arcade.load_texture("data/sprites/player/player_sprite.png", x=i*32, y=96, width = 32, height = 32))
            
            # Change the direction
            self.player_sprite.change_x = MOVEMENT_SPEED
            self.player_direction = "+"            
        
        # Slow down the time by 3 times when the player reaches certian score and has enough time meter
        elif key == arcade.key.LSHIFT and self.score >= 1000 and self.time_meter > 10:
            self.time_slow = 3
            arcade.play_sound(self.time_slow_sound, 0.2)
        
        # Slow down the time by 1000000 times so it appears that time has stopped
        # when the player reaches certian score and has enough time meter
        elif key == arcade.key.SPACE and self.score >= 1800 and self.time_meter > 10:
            self.time_slow = 100000000000
            arcade.play_sound(self.time_stop_sound, 0.4)
        
        elif key == arcade.key.Q:
            self.recall = True
        
        elif key == arcade.key.ESCAPE:
            arcade.stop_sound(self.background_sound)

    def on_key_release(self, key, modifiers):
        """ Called when the user lets go of a key. """
    
        if key == arcade.key.D:
            # Clear the texture lists and replace it with a stand still image
            self.player_sprite.textures = []
            self.player_sprite.textures.append(arcade.load_texture("data/sprites/player/player_sprite.png", x=0, y=96, width = 32, height = 32))
            
            # Change direction
            self.player_sprite.change_x = 0
        
        elif key == arcade.key.A:
            # Clear the texture lists and replace it with a stand still image
            self.player_sprite.textures = []
            self.player_sprite.textures.append(arcade.load_texture("data/sprites/player/player_sprite.png", x=0, y=64, width = 32, height = 32))
            
            # Change direction
            self.player_sprite.change_x = 0
        
        elif key == arcade.key.LSHIFT:
            self.time_slow = 0
            
        elif key == arcade.key.SPACE:
            self.time_slow = 0
    
    # For shooting
    def on_mouse_press(self, x, y, button, modifiers):
        """ Called whenever mouse button is pressed """
        
        # Make bullet a sprite and set their location
        bullet = arcade.Sprite("data/sprites/enemies/standard turret.png", 1)
        bullet.center_x = self.player_sprite.center_x
        bullet.center_y = self.player_sprite.center_y
        arcade.play_sound(self.shoot_sound, 0.1)
        
        # Set the bullet movespeed depending on the direction
        bullet.movespeed = 0
        if self.player_direction == "+":
            bullet.movespeed = 10
        if self.player_direction == "-":
            bullet.movespeed = -10
        
        # Add the bullet to the list
        self.player_bullet_list.append(bullet)
        
        # So the cutscene events only trigger at level 0 which is made for cutscenes
        if self.level == 0:
        
            # So nothing gets removed from the empty cutscene list in the beggining
            if self.cutscene_count > 0:
                self.cutscene_list.pop(0)
            
            # Add to the cutscene count
            self.cutscene_count += 1
            
            # If the the game shows us the ending scenes then close the window
            # on the next click
            if self.cutscene_count == 13 or self.cutscene_count == 15:
                    arcade.close_window()            
            
            # Set which cutscene to play based on the ending
            if self.ending == "good" and self.switch == False:
                self.cutscene_count = 13
                self.switch = True
            if self.ending == "bad" and self.switch == False:
                self.cutscene_count = 11
                self.switch = True
            
            print(str(self.cutscene_count))
            
            # Instead of writing the code 14 times for 14 different cutscenes
            # I made it so the directory just changes depending on which cutscene I am on
            sprite_directory = "data/sprites/cutscenes/cutscene " + str(self.cutscene_count) + ".png"
            cutscene = arcade.Sprite(sprite_directory)
            
            # Setting the location for the cutscene
            cutscene.center_x = self.player_sprite.center_x + 70
            cutscene.center_y = self.player_sprite.center_y
            
            # Adding the cutscene to the list
            self.cutscene_list.append(cutscene)
            
            # This is for the 11 cutscenes at the very start of the game
            # but if I didn't add the ending code then it brings us to
            # the beggining of the game when completed level 6
            if self.cutscene_count == 11 and self.ending != "bad":
                self.level += 1
                self.setup(self.level)


    def update(self, delta_time):
        """ Movement and game logic """
        
        # Drain the time bar
        if self.time_slow >= 2:
            self.time_meter -= 0.5
        
        # Charge the time bar but dont charge it once it goes over 100
        elif self.time_slow < 2 and self.time_meter <= 100:
            self.time_meter += 0.3
        if self.time_meter > 100:
            self.time_meter = 100
        
        # If time meter reaches 0 then stop slowing down time
        if self.time_meter <= 0:
            self.time_slow = 1
            self.time_meter = 0
        
        # Setting it so if the time count doesn't match the time slow number
        # then you don't update the physics engine. If time count is bigger then
        # time slow time count resets to 0
        # (ex: physics will run every 3 updates if time slow was 3)
        # !!!THIS IS THE NEW UPDATE FOR EVERYTHING THAT IS AFFECTED BY TIME ELEMENTS!!!
        if self.time_count >= self.time_slow:
            
            # Checking if a bullet hit the wall
            for wall in self.wall_list:
                ground_hit_list = arcade.check_for_collision_with_list(wall, self.bullet_list)
                
                # Removing bullets that did hit the wall
                for bullet in ground_hit_list:
                    bullet.remove_from_sprite_lists()
            
            # Move the bullet
            for bullet in self.player_bullet_list:
                bullet.center_x += bullet.movespeed
            
            # Finding out which bullet hit the player
            player_hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.bullet_list)
            
            # Remove the bullet that hit the player and also subtract player's health by 30
            for bullet in player_hit_list:
                self.player_health -= bullet.damage
                arcade.play_sound(self.hit_sound)
                bullet.remove_from_sprite_lists()
            
            # Kill the player if their health is below 0 and play a sound effect
            if self.player_health <= 0:
                self.player_death = True
            
            # Find out if the player hit the turret
            for bullet in self.player_bullet_list:
                bullet_hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_list)
                
                # go through the hit list
                for turret in bullet_hit_list:
                    turret.health -= 1
                    bullet.remove_from_sprite_lists()
            
            # Kill the turret and add 100 in the score
            for turret in self.enemy_list:
                if turret.health <= 0:
                    arcade.play_sound(self.kill_sound, 0.1)
                    turret.remove_from_sprite_lists()
                    self.score += 100
            
            # Update the animation
            self.player_list.update_animation()
            
            # Call update on all sprites
            self.wall_list.update()
            self.player_list.update()
            self.enemy_list.on_update(delta_time)        
            self.bullet_list.update()
            
            # Updating the physics engine
            self.physics_engine.update()
            
            # Set the player coordinates
            self.player_cordinates_x.append(self.player_sprite.center_x)
            self.player_cordinates_y.append(self.player_sprite.center_y)
            
            # Counting to 3 seconds with the in game time
            # meaning that if you slow time then the 3 seconds
            # will also slow down
            if self.mimic_timer <= 3:
                self.mimic_timer += delta_time
                if self.recall == True:
                    self.recall = False
            
            # This is a code for mimic copying our position whil
            # our character can swap the position with the mimic
            else:
                # The mimic copies the players position in a delayed way
                # by copying a list of player's coordinates that is delayed
                self.mimic_sprite.center_x = self.player_cordinates_x[0]
                self.mimic_sprite.center_y = self.player_cordinates_y[0]
                
                # Make sure to remove whatever the mimic copied so it doesn't
                # copy the exact same move
                self.player_cordinates_x.pop(0)
                self.player_cordinates_y.pop(0)
                
                # If rewinding back in time is aviable, then swap positions with mimic
                # and turn the cooldown timer on
                if self.recall == True:
                    self.mimic_timer = 0
                    self.player_sprite.center_x = self.player_cordinates_x[0]
                    self.player_sprite.center_y = self.player_cordinates_y[0]
                    self.player_cordinates_y.clear()
                    self.player_cordinates_x.clear()
                    
                    # Disabling to rewind back time until it goes off cooldown
                    self.recall = False
            
            # Update the mimic animation
            self.mimic_list.update_animation()
            self.mimic_list.update()
            
            # Set time count to 0 when the number reaches time slow to reset
            # the variable
            self.time_count = 0
        
        # If time count isn't as big as time slow then add 1 to time count every update
        else:
            self.player_list.update_animation()
            self.time_count += 1
        
            # If player collected more then 3300 score then don't slow the player down
            # on time slow
            if self.score >= 3300 and self.time_slow < 10:
                self.player_list.update()
                self.physics_engine.update()
            
            # If player collected more then 4300 score then don't stop the player
            # on time stop
            if self.score >= 4300 and self.time_slow > 10:
                self.player_list.update()
                self.physics_engine.update()
        
        # --- Manage Scrolling ---
    
        # Keep track of if we changed the boundary. We don't want to call the
        # set_viewport command if we didn't change the view port.
        changed = False

        # Scroll left
        left_bndry = self.view_left + VIEWPORT_MARGIN
        if self.player_sprite.left < left_bndry:
            self.view_left -= left_bndry - self.player_sprite.left
            changed = True

        # Scroll right
        right_bndry = self.view_left + SCREEN_WIDTH - D_MARGIN
        if self.player_sprite.right > right_bndry:
            self.view_left += self.player_sprite.right - right_bndry
            changed = True

        # Scroll up
        top_bndry = self.view_bottom + SCREEN_HEIGHT - VIEWPORT_MARGIN
        if self.player_sprite.top > top_bndry:
            self.view_bottom += self.player_sprite.top - top_bndry
            changed = True

        # Scroll down
        bottom_bndry = self.view_bottom + VIEWPORT_MARGIN
        if self.player_sprite.bottom < bottom_bndry:
            self.view_bottom -= bottom_bndry - self.player_sprite.bottom
            changed = True

        # If we need to scroll, go ahead and do it.
        if changed:
            arcade.set_viewport(self.view_left,
                                SCREEN_WIDTH + self.view_left,
                                self.view_bottom,
                                SCREEN_HEIGHT + self.view_bottom)
        
        # If player hit the kill barrier
        player_kill_list = arcade.check_for_collision_with_list(self.player_sprite, self.kill_barrier_list)
        if len(player_kill_list):
            self.player_death = True
            player_kill_list.clear()
        
        # If player died
        if self.player_death == True:
            self.player_death = False
            arcade.play_sound(self.respawn_sound, 0.1)
            self.setup(self.level)
        
        # Code for going to next level:
        if self.level != 6 and self.level != 0 and arcade.check_for_collision(self.player_sprite, self.next_level_sprite) == True:
            
            # Save the player's current score
            self.saved_score = self.score
            
            # Proceed the character to next level
            self.level += 1
            self.setup(self.level)
        
        # If player is in level 6 then proceed the ending
        if self.level == 6 and arcade.check_for_collision(self.player_sprite, self.next_level_sprite) == True:
            
            # determine which type of ending it is
            if self.score < 9500:
                self.ending = "bad"
            else:
                self.ending = "good"
            
            self.level = 0
            self.setup(self.level)

def main():
    window = MyGame()
    window.setup(window.level)
    arcade.run()


if __name__ == "__main__":
    main()