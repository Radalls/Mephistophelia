import arcade
import matplotlib.pyplot as plt

from src.constants import AGENT_LEARNING_MODES, PLAY_MODES, VIEW_MODES
from src.environment import Environment

def main():
    player_path     = '../assets/sprites/player/player'
    map_path        = '../assets/maps/json/map_5-2.json'
    save_path       = '../agent.qtable'
    play_mode       = PLAY_MODES[1]
    view_mode       = VIEW_MODES[1]
    learning_mode   = AGENT_LEARNING_MODES[1]
    learning_rate   = 0.1
    discount_factor = 0.9

    env = Environment()
    env.setup(
        player_path, map_path, save_path,
        play_mode, view_mode, learning_mode,
        learning_rate, discount_factor,
    )
    arcade.run()

    if env.is_agent_play():
        plt.plot(env.agent.history)
        plt.show()

if __name__ == "__main__":
    main()
