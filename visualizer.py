import argparse
import pickle
import socket

import numpy as np
import pygame

GEOMETRY_ATTRIBUTES = 'room goal agent orientation objects'.split()
ROOM, GOAL, AGENT, ORIENTATION, OBJECTS = GEOMETRY_ATTRIBUTES
BUFFSIZE = 2 ** 14


class Visualizer:
    def __init__(self):
        self.screen_size = 1000
        self.screen = pygame.display.set_mode((self.screen_size,
                                               self.screen_size), )

        self.BACKGROUND_COLOR = (0, 0, 0)
        self.ROOM_COLOR = (80, 80, 80)
        self.AGENT_COLOR = (0, 255, 0)
        self.GOAL_COLOR = (255, 0, 0)

        self.screen_tlx = None
        self.screen_tly = None
        self.screen_brx = None
        self.screen_bry = None

    def normalize(self, x, y):
        if None in (
        self.screen_tlx, self.screen_tly, self.screen_brx, self.screen_bry):
            return x, y
        view_x = (x - self.screen_tlx) / (self.screen_brx - self.screen_tlx)
        view_y = (y - self.screen_tly) / (self.screen_bry - self.screen_tly)
        screen_x = int(self.screen_size * view_x)
        screen_y = int(self.screen_size * view_y)
        return screen_x, screen_y

    def draw_rect(self, dimensions, color):
        tl, br = dimensions
        tl_x, tl_y = self.normalize(*tl)
        br_x, br_y = self.normalize(*br)
        pygame.draw.rect(self.screen, color, (tl_x, tl_y, br_x - tl_x,
                                              br_y - tl_y))

    def draw_agent(self, pos, dir, color):
        x, y = self.normalize(*pos)
        dir_x, dir_y = dir * 100
        # for some reason, the x-axis is reversed
        pygame.draw.line(self.screen, color, (x, y), (x - dir_x, y + dir_y), 2)
        pygame.draw.circle(self.screen, color, (x, y), 5)

    def draw_goal(self, coord, color):
        x, y = self.normalize(*coord)
        pygame.draw.circle(self.screen, color, (x, y), 5)

    def draw(self, room_rect, agent_pos, agent_dir, goal_coords, objects):
        rect = [x + np.sign(x) for x in room_rect]
        (self.screen_tlx, self.screen_bry), (
        self.screen_tly, self.screen_brx) = rect
        self.screen.fill(self.BACKGROUND_COLOR)
        self.draw_rect(room_rect, self.ROOM_COLOR)
        for pos, size in objects:
            upper_left = pos + size
            lower_right = pos - size
            self.draw_rect((upper_left, lower_right), self.BACKGROUND_COLOR)
        self.draw_goal(goal_coords, self.GOAL_COLOR)
        self.draw_agent(agent_pos, agent_dir, self.AGENT_COLOR)

    def ping_forever(self, host, port):
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(b'', (host, port))
            msg = s.recv(BUFFSIZE)
            try:
                geoms = pickle.loads(msg)
            except pickle.UnpicklingError:
                print('failed to unpickle')
                continue
            self.draw(geoms[ROOM], geoms[AGENT], geoms[ORIENTATION],
                      geoms[GOAL], geoms[OBJECTS])
            pygame.display.update()


def run(host, port):
    visualizer = Visualizer()
    pygame.init()
    visualizer.ping_forever(host, port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('host', type=str, help='host')
    parser.add_argument('port', type=int, help='port')
    args = parser.parse_args()

    run(args.host, args.port)
