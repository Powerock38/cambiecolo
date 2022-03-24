import multiprocessing as mp
import multiprocessing.shared_memory as shm
import sysv_ipc

"""
Cambiecolo is the environmentalist cousin of the Cambio card game. Its goal is presenting a hand of 5
cards of the same transport means. The player who succeeds is awarded the points of the transport they
put together. The game deals as many different types of transports as there are players. Possible transport
means are: airplane, car, train, bike and shoes. Each player receives 5 random cards, face down, e.g. if there
are 3 players, 15 cards of 3 transport means are distributed, 5 cards per transport. A bell is placed in the
middle of the players. As soon as cards are distributed, players start exchanging by announcing the
number of cards they offer, from 1 to 3 identical cards, without showing them. They exchange the same
number of cards with the first player to accept the offer. This continues until one of the players rings the
bell and presents a hand of 5 identical cards, scoring the points of the transport they have grouped.

Cambiecolo involves 2 types of processes:
• game: implements the game session, keeping track of current offers and the bell.
• player: interacts with the user 1, the game process and other player processes keeping track of
and displaying the hand and current offers. Interactions with the game process are carried out in a
separate thread.
Inter-process communication: Current offers are stored in a shared memory accessible to player
processes to update their own offer as well as to check current offers. Communication between player
processes takes place in a message queue requiring a carefully designed exchange protocol.
"""


class Game(mp.Process):
    offers: shm.SharedMemory
    exchanges: sysv_ipc.MessageQueue

    def __init__(self, nb_players: int):
        super().__init__()
        self.exchanges = sysv_ipc.MessageQueue(666, sysv_ipc.IPC_CREAT)
        self.offers = shm.SharedMemory(name="cambiecolo", create=True, size=nb_players)

    def stop(self):
        self.offers.unlink()

    def run(self):
        # Start game

        while True:
            pass


if __name__ == "__main__":
    g = Game(1)
    print(g.exchanges)
    g.stop()
