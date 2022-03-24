import sys
import multiprocessing.shared_memory as shm

TransportsStr = ["airplane", "car", "train", "bike", "shoes"]
Transports = range(len(TransportsStr))


class Player:
    offers: shm.SharedMemory
    hand: list[int] = []
    offer: int = None
    # offer contains transport type
    # when annoucing an offer, send hand.count(offer)

    def __init__(self, i):
        self.i = i
        self.offers = shm.SharedMemory(name="cambiecolo")

    def stop(self):
        self.offers.close()


if __name__ == "__main__":
    p = Player(int(sys.argv[1]))
    print(p.exchanges)
    p.stop()