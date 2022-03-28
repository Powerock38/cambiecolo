from multiprocessing import Event, Lock
from multiprocessing.managers import BaseManager
import os
import random
import signal
import sys
import sysv_ipc

T = ["airplane", "car", "train", "bike", "shoes"]
Transports = range(len(T))

class Shm():
    hands_start: list[list[int]] = []
    offers: list[int] = []
    playersPID: list[int] = []
    lock = Lock()
    start_game = Event()
    stop_game = Event()
    winner: int = None

    def __init__(self) -> None:
        pass

    def win(self, i: int):
        with self.lock:
            self.winner = i
            self.stop_game.set()

    def wait_for_start(self):
        self.start_game.wait()

    def wait_for_stop(self):
        self.stop_game.wait()

    def get_hand(self, pid) -> tuple[list[int], int]:
        with self.lock:
            if len(self.hands_start) == 0:
                return (None, None)

            self.offers.append(0)
            self.playersPID.append(pid)
            i = len(self.offers) - 1
            hand = self.hands_start.pop()
            hand.sort()

            # launch game if all players are ready
            if len(self.hands_start) == 0:
                self.start_game.set()

            return (hand, i)

    def get_nb_players(self) -> int:
        with self.lock:
            return len(self.playersPID)

    def get_winner(self) -> int:
        with self.lock:
            return self.winner

    def get_offers(self) -> list[int]:
        with self.lock:
            return self.offers

    def get_playersPID(self) -> list[int]:
        with self.lock:
            return self.playersPID

    def offer(self, i: int, nb_cards: int):
        with self.lock:
            self.offers[i] = nb_cards


class Game():
    manager: BaseManager
    ishm: Shm = Shm()
    shm: Shm
    exchanges: sysv_ipc.MessageQueue
    nb_players: int

    def __init__(self, nb_players: int):
        self.nb_players = nb_players

        # clean old IPC mq
        try:
            mq = sysv_ipc.MessageQueue(666)
            mq.remove()
            print("old messagequeue removed")
        except:
            pass

        self.exchanges = sysv_ipc.MessageQueue(666, sysv_ipc.IPC_CREX)
        
        BaseManager.register("shm", lambda: self.ishm)

        self.manager = BaseManager(address=("127.0.0.1", 6666), authkey=b"cambiecolo")

        # Hands generation
        possible_transports = list(Transports)[-nb_players:]
        print("Possible transports:", possible_transports)
        cards = possible_transports * 5
        print("Cards pool         :", cards)
        random.shuffle(cards)
        print("Cards pool shuffled:", cards)
        self.ishm.hands_start = [cards[i:i + 5] for i in range(0, len(cards), 5)]
        print("Cards:", self.ishm.hands_start)

    def stop(self):
        print("Stopping game")
        self.manager.shutdown()
        self.exchanges.remove()

    def start(self):
        # Start game
        self.manager.start()
        self.manager.connect()
        self.shm = self.manager.shm()

        print("Waiting for all {} players to get ready...".format(self.nb_players))
        
        self.shm.wait_for_start()

        print("Game started")
        print("PIDs:", self.shm.get_playersPID())

        self.shm.wait_for_stop()

        print("Game finished")
        print("\n!!! Player {} (pid {}) won !!!\n".format(self.shm.get_winner(), self.shm.get_playersPID()[self.shm.get_winner()]))
        print("PIDs:", self.shm.get_playersPID())

        for pid in self.shm.get_playersPID():
            try:
                print("Killed pid {}".format(pid))
                os.kill(pid, signal.SIGINT)
            except:
                print("Can't kill pid {}".format(pid))

if __name__ == "__main__":
    try:
        n = int(sys.argv[1])
        if not 2 <= n <= 5:
            raise ValueError
    except:
        print("Usage: {} <nb_players [2;5]>".format(sys.argv[0]))
        exit()

    g = Game(n)
    g.start()
    g.stop()