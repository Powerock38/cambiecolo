import sys
import sysv_ipc
from multiprocessing.managers import BaseManager

from Game import Shm

TransportsStr = ["airplane", "car", "train", "bike", "shoes"]
Transports = range(len(TransportsStr))


class Player():
    manager: BaseManager
    exchanges: sysv_ipc.MessageQueue
    shm: Shm

    hand: list[int] = []
    offer: int = None
    # offer contains transport type
    # when annoucing an offer, send hand.count(offer)

    def __init__(self, i):
        self.i = i

        self.exchanges = sysv_ipc.MessageQueue(666)

        BaseManager.register("shm")
        self.manager = BaseManager(address=("127.0.0.1", 6666), authkey=b"cambiecolo")
        self.manager.connect()

        self.shm = self.manager.shm()

        print(self.exchanges)
        print(self.manager)

    def start(self):
        # Start player

        while True:
            pass

    def stop(self):
        self.manager.close()

    def exchange(self):
        # Wait for exchange (polling, signals maybe?)
        try:
            msg = self.exchanges.receive(block=False)
        except:
            return

        # someone offers something (i, nb_cards, card_type)
        # if i can accept, accept:
        # add cards to hand
        # send cards to other player (i, nb_cards, card_type)

        # if i can't accept, send nack (i)


if __name__ == "__main__":
    p = Player(int(sys.argv[1]))
    p.start()
    p.stop()
