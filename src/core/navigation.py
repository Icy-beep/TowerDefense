import math
from src.entities.coordinate import Coordinate


class Node:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.g = self.h = self.f = 0
        self.parent = None

    def __eq__(self, other):
        if not isinstance(other, Node): return False
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        return self.f < other.f

    def __hash__(self):
        return hash((self.x, self.y))


class NavigationGrid:
    def __init__(self, width, height, cell_size=32):
        self.width, self.height, self.cell_size = width, height, cell_size
        self.cols = math.ceil(width / cell_size)
        self.rows = math.ceil(height / cell_size)
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def get_node(self, x, y):
        col, row = int(x / self.cell_size), int(y / self.cell_size)
        return Node(col, row) if 0 <= row < self.rows and 0 <= col < self.cols else None

    def get_world_pos(self, node):
        return Coordinate(node.x * self.cell_size + self.cell_size / 2,
                          node.y * self.cell_size + self.cell_size / 2)

    def set_blocked(self, x, y, blocked=True):
        col, row = int(x / self.cell_size), int(y / self.cell_size)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row][col] = 1 if blocked else 0

    def is_walkable(self, node):
        return 0 <= node.y < self.rows and 0 <= node.x < self.cols and self.grid[node.y][node.x] == 0

    def find_path(self, start_pos, end_pos):
        start, end = self.get_node(start_pos.x, start_pos.y), self.get_node(end_pos.x, end_pos.y)
        if not start or not end:
            return []
        if start == end:
            return [self.get_world_pos(start)]

        open_set = {start}
        closed_set = set()
        nodes = {}

        start.g = 0
        start.h = math.hypot(start.x - end.x, start.y - end.y)
        start.f = start.h

        while open_set:
            current = min(open_set, key=lambda n: n.f)
            open_set.remove(current)
            closed_set.add(current)

            if current == end:
                path = []
                curr = current
                while curr:
                    path.append(self.get_world_pos(curr))
                    curr = curr.parent
                return path[::-1]

            for dx, dy in [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]:
                nx, ny = current.x + dx, current.y + dy
                if not (0 <= ny < self.rows and 0 <= nx < self.cols):
                    continue

                neighbor_pos = (nx, ny)
                if neighbor_pos in nodes:
                    neighbor = nodes[neighbor_pos]
                else:
                    neighbor = Node(nx, ny)
                    nodes[neighbor_pos] = neighbor

                if neighbor != end and not self.is_walkable(neighbor):
                    continue

                if neighbor in closed_set:
                    continue

                move_cost = 1.414 if dx != 0 and dy != 0 else 1.0
                tentative_g = current.g + move_cost

                if neighbor not in open_set or tentative_g < neighbor.g:
                    neighbor.parent = current
                    neighbor.g = tentative_g
                    neighbor.h = math.hypot(neighbor.x - end.x, neighbor.y - end.y)
                    neighbor.f = neighbor.g + neighbor.h
                    open_set.add(neighbor)

        return []