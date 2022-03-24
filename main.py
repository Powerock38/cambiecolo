

import multiprocessing as mp
from Game import Game

from Player import Player

if __name__ == "main":
  try:
    nb_players = int(input("How many players? "))
  except ValueError:
    print("Please enter a number")
    exit()
  
  players = []
  for i in range(nb_players):
    players.append(Player(i))

  game = Game()