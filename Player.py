from multiprocessing.connection import wait
import os
import sys
import curses
import sysv_ipc
from multiprocessing.managers import BaseManager

from Game import Shm

T = ["airplane", "car", "train", "bike", "shoes"]
Transports = range(len(T))

Cambiecolo = """
   _________    __  _______  ____________________  __    ____
  / ____/   |  /  |/  / __ )/  _/ ____/ ____/ __ \/ /   / __ \\
 / /   / /| | / /|_/ / __  |/ // __/ / /   / / / / /   / / / /
/ /___/ ___ |/ /  / / /_/ // // /___/ /___/ /_/ / /___/ /_/ /
\____/_/  |_/_/  /_/_____/___/_____/\____/\____/_____/\____/
""".split("\n")

class Box():
    def __init__(self, screen, h, w, y, x):
        self.screen = screen
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.box = self.screen.derwin(self.h, self.w, self.y, self.x)
        self.box.border()

    def addstr(self, y, x, s):
        self.box.addstr(y, x, s)

    def refresh(self):
        self.box.refresh()

    def clear(self):
        self.box.clear()
        self.box.border()

    def is_in_box(self, y, x):
        return self.y <= y <= self.y + self.h and self.x <= x <= self.x + self.w


class Player():
    # ipc
    manager: BaseManager
    exchanges: sysv_ipc.MessageQueue
    shm: Shm

    # self
    i: int
    hand: list[int] = []
    offer: int = None  # contains transport type. when annoucing an offer, send hand.count(offer)

    # display
    transport_boxes = []
    offer_boxes = []

    # exchange state
    exchanging_with: int = None
    waiting_for_accept: int = None

    def __init__(self, stdsrc):
        self.screen = stdsrc
        self.exchanges = sysv_ipc.MessageQueue(666)

        BaseManager.register("shm")
        self.manager = BaseManager(address=("127.0.0.1", 6666), authkey=b"cambiecolo")
        self.manager.connect()

        self.shm = self.manager.shm()

        (self.hand, self.i) = self.shm.get_hand(os.getpid())
        if self.hand is None:
            print("Game already started")
            sys.exit(0)

    def init_display(self):
        self.screen.keypad(1)

        for t in Transports:
            b = Box(self.screen, 5, 10, 1, 10*(len(Transports) - t - 1))
            self.transport_boxes.append(b)

        nb_players = self.shm.get_nb_players()

        for i in range(nb_players):
            b = Box(self.screen, 4, 16, 13, 16*i)
            b.addstr(1, 1, "Player " + str(i))
            self.offer_boxes.append(b)

    def display_state(self, offers):
        self.screen.clear()
        if self.exchanging_with is not None:
            self.screen.addstr(0, 0, "Choose a transport to exchange with player {}".format(self.exchanging_with))
        else:
            self.screen.addstr(0, 0, "Choose a transport to offer...")
            self.screen.addstr(12, 0, "...or choose an offer to accept")
        self.screen.refresh()

        for t in range(len(self.transport_boxes)):
            b = self.transport_boxes[t]
            b.clear()
            nb = self.hand.count(t)
            if nb > 0:
                b.addstr(1, 1, T[t])
                b.addstr(2, 1, str(nb))
                if self.offer == t:
                    b.addstr(3, 1, "OFFERING")
            b.refresh()

        for l in range(len(Cambiecolo)):
            self.screen.addstr(l + 5, 0, Cambiecolo[l])

        for i in range(len(offers)):
            nb_cards = offers[i]
            b = self.offer_boxes[i]
            b.clear()
            if self.exchanging_with is None:
                b.addstr(1, 1, "Player " + str(i) + (" (you)" if i == self.i else ""))
                if nb_cards > 0:
                    b.addstr(2, 1, "offers {} cards".format(nb_cards))
            b.refresh()

    def start(self):
        print("Waiting for game to start...")
        self.shm.wait_for_start()
        curses.beep()
        self.init_display()

        while True:
            self.check_queue()
            offers = self.shm.get_offers()
            self.display_state(offers)

            event = self.screen.getch()
            if event == curses.KEY_MOUSE:
                _, mx, my, _, _ = curses.getmouse()

                for t in range(len(self.transport_boxes)):
                    b = self.transport_boxes[t]
                    if b.is_in_box(my, mx):
                        if self.exchanging_with is None:
                            self.announce_offer(t)
                        else:
                            self.ask_exchange(offers, t)
                        break

                for i in range(len(self.offer_boxes)):
                    b = self.offer_boxes[i]
                    if b.is_in_box(my, mx):
                        if i != self.i and offers[i] != 0:
                            if self.exchanging_with == i:
                                self.exchanging_with = None
                            else:
                                self.exchanging_with = i
                        break

    def stop(self):
        self.manager.close()

    def announce_offer(self, choice):
        if choice == self.offer:
            self.reset_offer()
        elif choice in self.hand:
            self.offer = choice
            self.shm.offer(self.i, self.hand.count(choice))

    def ask_exchange(self, offers, transport: int):
        # if exchange is possible, offer it
        nb_cards = offers[self.exchanging_with]
        if 0 < nb_cards <= self.hand.count(transport):
            # Init exchange : ("hey", my_i, nb_cards, card_type)
            message = "h,{},{},{}".format(self.i, nb_cards, transport).encode()
            self.exchanges.send(message, type=self.exchanging_with+1)
            self.waiting_for_accept = transport
            self.exchanging_with = None

    def swap_cards(self, nb_cards, t_rem, t_add):
        for _ in range(nb_cards):
            self.hand.remove(t_rem)
        self.hand += [t_add] * nb_cards
        self.hand.sort()

        if len(set(self.hand)) == 1:
            self.shm.win(self.i)

    def reset_offer(self):
        self.offer = None
        self.shm.offer(self.i, 0)

    def check_queue(self):
        try:
            msg, _ = self.exchanges.receive(block=False, type=self.i+1)
        except:
            return

        message = msg.decode().split(',')
        if message[0] == "h":  # Handle init exchange
            player, nb_cards, transport = int(message[1]), int(message[2]), int(message[3])
            if self.offer is not None and self.hand.count(self.offer) == nb_cards:
                # send cards to other player ("a", self.i, nb_cards, card_type = self.offer)
                accept = "a,{},{},{}".format(self.i, nb_cards, self.offer).encode()
                self.exchanges.send(accept, type=player+1)

                self.swap_cards(nb_cards, self.offer, transport)

                self.reset_offer()
            else:
                # refuse exchange = send nack
                nack = "n,{},{},{}".format(self.i, nb_cards, transport).encode()
                self.exchanges.send(nack, type=player+1)

        elif message[0] == "a":  # Handle accept exchange
            if self.waiting_for_accept is None:
                raise Exception("Received an accept message while not waiting for one")

            player, nb_cards, transport = int(message[1]), int(message[2]), int(message[3])

            self.swap_cards(nb_cards, self.waiting_for_accept, transport)

            self.waiting_for_accept = None

        elif message[0] == "n":  # Handle refuse exchange
            if self.waiting_for_accept is None:
                raise Exception("Received a refuse message while not waiting for one")

            self.waiting_for_accept = None


def main(stdscr):
    p = Player(stdscr)
    curses.curs_set(0)
    curses.mousemask(1)
    p.start()
    p.stop()


if __name__ == "__main__":
    curses.wrapper(main)
