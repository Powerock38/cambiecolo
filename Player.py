from multiprocessing.connection import wait
import os
import sys
import curses
import sysv_ipc
from multiprocessing.managers import BaseManager

from Game import Shm

T = ["airplane", "car", "train", "bike", "shoes"]
Transports = range(len(T))

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
    offer: int = None # contains transport type. when annoucing an offer, send hand.count(offer)

    # display
    transport_boxes = []
    offer_boxes = []
    offering_to: int = None
    waiting_for_accept = False

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
            b = Box(self.screen, 5, 10, 2, 1 + 10*t)
            self.transport_boxes.append(b)

        nb_players = self.shm.get_nb_players()
        
        for i in range(nb_players):
            b = Box(self.screen, 4, 16, 10, 1 + 16*i)
            b.addstr(1, 1, "Player " + str(i))
            self.offer_boxes.append(b)

    def display_state(self):
        self.screen.clear()
        if self.offering_to is not None:
            self.screen.addstr(1, 1, "Choose a transport to offer to player {}".format(self.offering_to))

        for t in range(len(self.transport_boxes)):
            b = self.transport_boxes[t]
            b.clear()
            b.addstr(1, 1, T[t])
            b.addstr(2, 1, str(self.hand.count(t)))
            if self.offer == t:
                b.addstr(3, 1, "OFFERING")
            b.refresh()

        offers = self.shm.get_offers()

        for i in range(len(offers)):
            nb_cards = offers[i]
            b = self.offer_boxes[i]
            b.clear()
            b.addstr(1, 1, "Player " + str(i))
            b.addstr(2, 1, "offers {} cards".format(nb_cards))
            b.refresh()

    def start(self):
        # Start player

        print("Waiting for game to start...")
        self.shm.wait_for_start()

        self.init_display()

        while True:
            self.check_queue()
            self.display_state()

            event = self.screen.getch()
            if event == curses.KEY_MOUSE:
                _, mx, my, _, _ = curses.getmouse()
            
            for t in range(len(self.transport_boxes)):
                b = self.transport_boxes[t]
                if b.is_in_box(my, mx):
                    if self.offering_to is None:
                        self.announce_offer(t)
                    else:
                        self.try_exchange(t, self.offering_to)
                        self.offering_to = None

            for i in range(len(self.offer_boxes)):
                b = self.offer_boxes[i]
                if b.is_in_box(my, mx):
                    self.offering_to = i

    def stop(self):
        self.manager.close()

    def look(self):
        print()
        offers = self.shm.get_offers()
        if len(offers) == 0:
            print("No offers")
            return

        for i in range(len(offers)):
            if offers[i] is not None:
                if i == self.i:
                    s = "You offer"
                else:
                    s = "Player {} offers".format(i)
                print("{} {} cards".format(s, offers[i]))

    def announce_offer(self, choice):
        if choice in self.hand:
            self.offer = choice
            self.shm.offer(self.i, self.hand.count(choice))

    def try_exchange(self, transport: int, player: int):
        # if exchange is possible, offer it
        offers = self.shm.get_offers()
        nb_cards = offers[player]
        if 0 < nb_cards <= self.hand.count(transport):
            # Init exchange : ("hey", my_i, nb_cards, card_type)
            message = "h,{},{},{}".format(self.i, nb_cards, transport).encode()
            self.exchanges.send(message, type=player+1)
            self.waiting_for_accept = True

    def check_queue(self):
        try:
            msg, _ = self.exchanges.receive(block=False, type=self.i+1)
        except:
            return

        message = msg.decode().split(',')
        if message[0] == "h": # Handle init exchange
            player, nb_cards, transport = int(message[1]), int(message[2]), int(message[3])
            if self.offer is not None and self.hand.count(self.offer) == nb_cards:
                # send cards to other player ("a", self.i, nb_cards, card_type = self.offer)
                accept = "a,{},{},{}".format(self.i, nb_cards, self.offer).encode()
                self.exchanges.send(accept, type=player+1)
                # delete my cards
                for _ in range(nb_cards):
                    self.hand.remove(transport)

                # add cards to my hand
                self.hand.extend([transport] * nb_cards)
            else:
                # refuse exchange = send nack
                nack = "n,{},{},{}".format(self.i, nb_cards, transport).encode()
                self.exchanges.send(nack, type=player+1)

        
        elif message[0] == "a": # Handle accept exchange
            if not self.waiting_for_accept:
                raise Exception("Received an accept message while not waiting for one")
            
            player, nb_cards, transport = int(message[1]), int(message[2]), int(message[3])
            # delete my cards
            for _ in range(nb_cards):
                self.hand.remove(transport)
            
            # add cards to my hand
            self.hand.extend([transport] * nb_cards)
            
            self.waiting_for_accept = False
        
        elif message[0] == "n": # Handle refuse exchange
            if not self.waiting_for_accept:
                raise Exception("Received a refuse message while not waiting for one")

            self.waiting_for_accept = False


def main(stdscr):
    p = Player(stdscr)
    curses.curs_set(0)
    curses.mousemask(1)
    # curses.noecho()
    # curses.cbreak()
    p.start()
    p.stop()

if __name__ == "__main__":
    curses.wrapper(main)

    # stop
    # curses.nocbreak()
    # curses.echo()
    # curses.endwin()
