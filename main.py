import arcade
import math
import os
import random

#region CONSTANTS
# Game window
SCREEN_WIDTH = 1152
SCREEN_HEIGHT = 576
SCREEN_TITLE = "Mephistophelia"

# Entity scaling
TILE_SCALING = 0.5
CHARACTER_SCALING = TILE_SCALING * 2
SPRITE_PIXEL_SIZE = 128
TILE_PIXEL_SIZE = SPRITE_PIXEL_SIZE * TILE_SCALING

# Physics engine
PLAYER_MOVEMENT_SPEED = 10
GRAVITY = 1.5
PLAYER_JUMP_SPEED = 25
PLAYER_DASH_SPEED = 25
PLAYER_DASH_DURATION = 0.1
PLAYER_DASH_COOLDOWN = 2

# Player sprite facing direction
PLAYER_RIGHT_FACING = 0
PLAYER_LEFT_FACING = 1

# Map
MAP_NAME = "./test_map3.json"
MAP_LAYER_GOAL = "Goal"
MAP_LAYER_FOREGROUND = "Foreground"
# MAP_LAYER_MOVING_PLATFORMS = "Moving Platforms"
MAP_LAYER_PLATFORMS = "Platforms"
MAP_LAYER_PLAYER = "Player"
MAP_LAYER_BACKGROUND = "Background"
MAP_LAYER_DEATHGROUND = "Deathground"

# Agent
AGENT_REWARD_DEATH = -1000
AGENT_REWARD_GOAL = 1000
AGENT_REWARD_STEP = -1
AGENT_ACTIONS = [
    'LEFT', 'RIGHT',
    'JUMP', 'JUMP_LEFT', 'JUMP_RIGHT',
    'DASH', 'DASH_LEFT', 'DASH_RIGHT', 'DASH_UP'
]
#endregion CONSTANTS

#region GAME
# Player class
class Player(arcade.Sprite):

    def __init__(self):
        super().__init__()

        # Set player to face right at start
        self.character_face_direction = PLAYER_RIGHT_FACING

        # Used for flipping between image sequences
        self.cur_texture = 0
        self.scale = CHARACTER_SCALING

        # Player texture path (from arcade examples)
        player_path = "./assets/player"

        # Load textures for idle standing
        self.idle_texture_pair = self.load_texture_pair(f"{player_path}_idle.png")
        self.jump_texture_pair = self.load_texture_pair(f"{player_path}_jump.png")
        self.fall_texture_pair = self.load_texture_pair(f"{player_path}_fall.png")

        # Load textures for walking
        self.walk_textures = []
        for i in range(8):
            texture = self.load_texture_pair(f"{player_path}_walk{i}.png")
            self.walk_textures.append(texture)

        # Set player initial texture
        self.texture = self.idle_texture_pair[0]

        # Set player hit box
        self.hit_box = self.texture.hit_box_points

    def load_texture_pair(self, filename):
        return [
            arcade.load_texture(filename),
            arcade.load_texture(filename, flipped_horizontally=True),
        ]

    def update_animation(self, delta_time: float = 1 / 60):
        # Animation direction
        if self.change_x < 0 and self.character_face_direction == PLAYER_RIGHT_FACING:
            self.character_face_direction = PLAYER_LEFT_FACING
        elif self.change_x > 0 and self.character_face_direction == PLAYER_LEFT_FACING:
            self.character_face_direction = PLAYER_RIGHT_FACING

        # Jumping animation
        if self.change_y > 0:
            self.texture = self.jump_texture_pair[self.character_face_direction]
            return
        elif self.change_y < 0:
            self.texture = self.fall_texture_pair[self.character_face_direction]
            return

        # Idle animation
        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Walking animation
        self.cur_texture += 1
        if self.cur_texture > 7:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture][
            self.character_face_direction
        ]

# Game class
class Game(arcade.Window):

    def __init__(self):
        # Set game window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Set origin path
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)

        # State machine
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        # self.down_pressed = False
        self.space_pressed = False
        self.dashing = False
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_direction = (0, 0)

        # Tilemap Object
        self.tile_map = None

        # Game Scene Object
        self.scene = None

        # Player Object
        self.player = None
        self.player_start_x = 0
        self.player_start_y = 0

        # Physics engine Object
        self.physics_engine = None

        # Camera Object
        self.camera = None
        self.gui_camera = None

        # Map bounds
        self.map_x_bound = 0
        self.map_y_bound = 0

        # AI agent
        self.agent = None
        self.agent_reward = 0

    def setup(self):
        # Set camera
        self.camera = arcade.Camera(self.width, self.height)
        self.gui_camera = arcade.Camera(self.width, self.height)

        # Map name
        map_name = MAP_NAME

        # Set map layers options
        map_layer_options = {
            MAP_LAYER_PLATFORMS: {
                "use_spatial_hash": True,
            },
            # LAYER_NAME_MOVING_PLATFORMS: {
            #     "use_spatial_hash": False,
            # },
            MAP_LAYER_DEATHGROUND: {
                "use_spatial_hash": True,
            },
        }

        # Load the map
        self.tile_map = arcade.load_tilemap(map_name, TILE_SCALING, map_layer_options)
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        # Load the player layer
        self.scene.add_sprite_list_after(MAP_LAYER_PLAYER, MAP_LAYER_FOREGROUND)

        # Set the player at start position
        self.player = Player()
        self.player_start_x = int(self.tile_map.get_tilemap_layer("Player").properties["start_x"]) * TILE_PIXEL_SIZE
        self.player_start_y = int(self.tile_map.get_tilemap_layer("Player").properties["start_y"]) * TILE_PIXEL_SIZE
        self.player.center_x = self.player_start_x
        self.player.center_y = self.player_start_y
        self.scene.add_sprite(MAP_LAYER_PLAYER, self.player)

        # Locate edges of the map
        self.map_x_bound = int(self.tile_map.width * TILE_PIXEL_SIZE)
        self.map_y_bound = int(self.tile_map.height * TILE_PIXEL_SIZE)

        # Set the background color
        if self.tile_map.background_color:
            arcade.set_background_color(self.tile_map.background_color)

        # Set the 'physics engine'
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player,
            # platforms=self.scene[LAYER_NAME_MOVING_PLATFORMS],
            gravity_constant=GRAVITY,
            walls=self.scene[MAP_LAYER_PLATFORMS]
        )

        # Set the AI agent
        self.agent = Agent(self.player_start_x, self.player_start_y, self.map_x_bound, self.map_y_bound)

    def on_draw(self):
        self.clear()
        self.camera.use()
        self.scene.draw()
        self.gui_camera.use()

        arcade.draw_text(
            f'State: {self.agent.state} Score: {self.agent.score}',
            12,
            self.height - 12,
            arcade.color.WHITE,
            font_size=18,
            anchor_x="left",
            anchor_y="top",
        )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.UP or key == arcade.key.Z:
            self.up_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.Q:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True
        elif key == arcade.key.SPACE:
            self.space_pressed = True
        elif key == arcade.key.R:
            self.reset_player_position()
            self.agent.reset(self.player_start_x, self.player_start_y)

        self.on_key_change()

    def on_key_release(self, key, modifiers):
        if key == arcade.key.UP or key == arcade.key.Z:
            self.up_pressed = False
        # elif key == arcade.key.DOWN or key == arcade.key.S:
            # self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.Q:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False
        elif key == arcade.key.SPACE:
            self.space_pressed = False

        self.on_key_change()

    def on_key_change(self):
        self.process_movement()
        self.process_jump()
        self.process_dash()

    def can_jump(self):
        return self.up_pressed and self.physics_engine.can_jump() #and not self.down_pressed
    
    def can_dash(self):
        return self.space_pressed \
            and self.dash_timer == 0 \
            and self.dash_cooldown == 0

    def process_movement(self):
        if self.right_pressed and not self.left_pressed:
            self.player.change_x = PLAYER_MOVEMENT_SPEED
        elif self.left_pressed and not self.right_pressed:
            self.player.change_x = -PLAYER_MOVEMENT_SPEED
        else:
            self.player.change_x = 0

    def process_jump(self):
        if self.can_jump():
            self.player.change_y = PLAYER_JUMP_SPEED

    def process_dash(self):
        if self.can_dash():
            self.dash_timer = PLAYER_DASH_DURATION
            self.dash_direction = (
                int(self.right_pressed) - int(self.left_pressed),
                int(self.up_pressed),
            )

    def on_update(self, delta_time):
        self.physics_engine.update()
        # self.update_agent()
        self.update_animations(delta_time)
        self.update_camera()
        self.update_dash(delta_time)
        self.check_collision_with_goal()
        self.check_collision_with_warps()
        self.check_out_of_bounds()
        self.check_collision_with_deathground()

    def update_agent(self):
        ai_input = self.agent.best_action()

        self.left_pressed = ai_input[0]
        self.right_pressed = ai_input[1]
        self.up_pressed = ai_input[2]
        self.space_pressed = ai_input[3]
        self.on_key_change()

        self.agent_reward += AGENT_REWARD_STEP

        self.agent.update(
            AGENT_ACTIONS[0],
            tuple[int(self.player.center_x), int(self.player.center_y)],
            self.agent_reward,
        )

        self.agent_reward = 0

    def update_animations(self, delta_time):
        self.scene.update_animation(
            delta_time, [MAP_LAYER_BACKGROUND, MAP_LAYER_PLAYER]
        )

    def update_camera(self):
            screen_center_x = 0
            screen_center_y = self.player.center_y - (
                self.camera.viewport_height / 2
            )

            if screen_center_x < 0:
                screen_center_x = 0
            if screen_center_y < 0:
                screen_center_y = 0

            player_centered = screen_center_x, screen_center_y

            self.camera.move_to(player_centered, 0.2)

    def update_dash(self, delta_time):
        if self.dash_timer > 0:
            self.dash_timer -= delta_time

            dash_length = math.sqrt(self.dash_direction[0] ** 2 + self.dash_direction[1] ** 2)
            if dash_length > 0:
                self.dash_direction = (
                    self.dash_direction[0] / dash_length,
                    self.dash_direction[1] / dash_length,
                )
            
            self.player.change_x = self.dash_direction[0] * PLAYER_DASH_SPEED
            self.player.change_y = self.dash_direction[1] * PLAYER_DASH_SPEED

            self.dashing = True
        else:
            if self.dashing:
                self.player.change_x = PLAYER_MOVEMENT_SPEED * self.dash_direction[0]
                self.player.change_y = PLAYER_MOVEMENT_SPEED * self.dash_direction[1]
                self.dashing = False
                self.dash_cooldown = PLAYER_DASH_COOLDOWN

            if self.dash_cooldown > 0:
                self.dash_cooldown = max(0, self.dash_cooldown - delta_time)
            
            self.dash_timer = 0
            self.dash_direction = (0, 0)

    def check_out_of_bounds(self):
        if self.player.center_y < -100:
            self.agent_reward += AGENT_REWARD_DEATH
            self.reset_player_position()

    def check_collision_with_deathground(self):
        if arcade.check_for_collision_with_list(
            self.player, self.scene[MAP_LAYER_DEATHGROUND]
        ):
            self.agent_reward += AGENT_REWARD_DEATH
            self.reset_player_position()

    def check_collision_with_warps(self):
        map_left_warp = -self.player.width + TILE_PIXEL_SIZE
        map_right_warp = self.map_x_bound + self.player.width - TILE_PIXEL_SIZE
        if self.player.center_x > map_right_warp:
            self.player.center_x = map_left_warp
        if self.player.center_x < map_left_warp:
            self.player.center_x = map_right_warp

    def check_collision_with_goal(self):
        if arcade.check_for_collision_with_list(
            self.player, self.scene[MAP_LAYER_GOAL]
        ):
            self.agent_reward += AGENT_REWARD_GOAL
            arcade.exit()

    def reset_player_position(self):
        self.player.change_x = 0
        self.player.change_y = 0
        self.player.center_x = self.player_start_x
        self.player.center_y = self.player_start_y
#endregion GAME

#region AI
class Agent:

    def __init__(self, x=0, y=0, x_bound=0, y_bound=0, learning_rate=0.5, discount_factor=0.5):
        self.start_x = x
        self.start_y = y
        self.state = x, y
        self.score = 0
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        
        self.qtable = {}
        for state in self.get_all_states(x_bound, y_bound):
            self.qtable[state] = {}
            for action in self.get_all_actions():
                self.qtable[state][action] = 0.0

        print(self.qtable[self.state])

    def get_all_states(self, x_bound: int, y_bound: int):
        return [
            (x, y) for x in range(0, x_bound + 1)
            for y in range(0, y_bound + 1)
        ]

    def get_all_actions(self):
        return AGENT_ACTIONS

    def best_action(self):
        return self.random_action()
        # return max(range(len(self.qtable[self.state])), key=lambda i: self.qtable[self.state][i])
    
    def random_action(self):
        return [
            random.choice([True, False]) for _ in range(len(AGENT_ACTIONS))
        ]
    
    def update(self, action: str, new_state, reward: int):
        self.score += reward
        # self.qtable[self.state][action] += reward
        # maxQ = max(self.qtable[new_state].values())
        # delta = self.learning_rate * (reward + self.discount_factor * maxQ - self.qtable[self.state][action])
        # self.qtable[self.state][action] += delta
        self.state = new_state
    
    def reset(self):
        self.state = self.start_x, self.start_y
        self.score = 0
#endregion AI

# Main function
def main():
    window = Game()
    window.setup()
    arcade.run()

if __name__ == "__main__":
    main()
