import os
import sys
import sysv_ipc
from multiprocessing.managers import BaseManager

from Game import Shm

T = ["airplane", "car", "train", "bike", "shoes"]
Transports = range(len(T))


class Player():
    manager: BaseManager
    exchanges: sysv_ipc.MessageQueue
    shm: Shm

    i: int
    hand: list[int] = []
    offer: int = None
    # offer contains transport type
    # when annoucing an offer, send hand.count(offer)

    def __init__(self):
        self.exchanges = sysv_ipc.MessageQueue(666)

        BaseManager.register("shm")
        self.manager = BaseManager(address=("127.0.0.1", 6666), authkey=b"cambiecolo")
        self.manager.connect()

        self.shm = self.manager.shm()

        (self.hand, self.i) = self.shm.get_hand(os.getpid())
        if self.hand is None:
            print("Game already started")
            sys.exit(0)

    def display(self):
        print("Player {}".format(self.i))
        print("Hand:", " ".join([T[c] + " (" + str(c) + ") " for c in self.hand]))
        print("Currnet offer: {}".format(self.offer))

    def input_int(self, s) -> int:
        a = input(s + " > ")
        try:
            return int(a)
        except ValueError:
            print("Not an integer")
            return self.input_int(s)

    def start(self):
        # Start player

        print("Waiting for game to start...")
        self.shm.wait_for_start()

        while True:
            self.display()

            choice = self.input_int("Choose a transport id to offer " + str(set(self.hand)))
            #Todo

            self.check_queue()
            pass

    def stop(self):
        self.manager.close()

    def try_announce(self):
        # announce offer
        # if offer is possible, announce it

        self.shm.offer(self.i, self.hand.count(self.offer))

    def try_exchange(self):
        # Check hand for exchange
        # if exchange is possible, offer it
        pass

    def check_queue(self):
        # Wait for exchange (polling, signals maybe?)
        try:
            msg = self.exchanges.receive(block=False)
        except:
            return

        # someone offers something ("hey", their_i, nb_cards, card_type)
        # if i can accept, accept:
        # add cards to hand
        # send cards to other player (self.i, nb_cards, card_type)

        # if i can't accept, send nack ("nope", self.i)


if __name__ == "__main__":
    p = Player()
    p.start()
    p.stop()
