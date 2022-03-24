TransportsStr = ["airplane", "car", "train", "bike", "shoes"]
Transports = range(len(TransportsStr))


class Player:
    hand: list[int] = []
    offer: int = None
    # offer contains transport type
    # when annoucing an offer, send hand.count(offer)

    def __init__(self, i):
        self.i = i
