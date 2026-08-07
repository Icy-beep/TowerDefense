import heapq
import itertools
import math

from src.core.coordinate import Coordinate


class Node:
    """Клетка навигационной сетки для поиска пути."""

    def __init__(self, x, y):
        """Создаёт узел с координатами клетки."""
        self.x, self.y = x, y
        self.g = self.h = self.f = 0
        self.parent = None

    def __eq__(self, other):
        """Сравнивает узлы по координатам."""
        if not isinstance(other, Node): return False
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        """Сравнивает узлы по стоимости f для очереди с приоритетом."""
        return self.f < other.f

    def __hash__(self):
        """Хэш узла по координатам."""
        return hash((self.x, self.y))


class NavigationGrid:
    """Сетка клеток карты для поиска пути алгоритмом A*."""

    def __init__(self, width, height, cell_size=32):
        """Создаёт пустую проходимую сетку заданного размера."""
        self.width, self.height, self.cell_size = width, height, cell_size
        self.cols = math.ceil(width / cell_size)
        self.rows = math.ceil(height / cell_size)
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def get_node(self, x, y):
        """Возвращает узел сетки для мировых координат."""
        col, row = int(x / self.cell_size), int(y / self.cell_size)
        return Node(col, row) if 0 <= row < self.rows and 0 <= col < self.cols else None

    def get_world_pos(self, node):
        """Возвращает мировые координаты центра клетки узла."""
        return Coordinate(node.x * self.cell_size + self.cell_size / 2,
                          node.y * self.cell_size + self.cell_size / 2)

    def set_blocked(self, x, y, blocked=True):
        """Помечает клетку в мировых координатах как проходимую или нет."""
        col, row = int(x / self.cell_size), int(y / self.cell_size)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row][col] = 1 if blocked else 0

    def is_walkable(self, node):
        """Проверяет, проходима ли клетка."""
        return 0 <= node.y < self.rows and 0 <= node.x < self.cols and self.grid[node.y][node.x] == 0

    HEURISTIC_WEIGHT = 1.3

    # 400 казался разумным лимитом, пока не выяснилось, что даже один манёвр вокруг одной
    # башни с avoid_danger=True (жёсткий запрет всего её радиуса) регулярно требует больше
    # 400 узлов A* и возвращает "пути нет" даже когда честный объезд существует - враг тогда
    # решает, что застрял, и уходит в fallback (например, к спавну/краю карты) без нужды.
    # 1500 с запасом хватает на объезд нескольких башен и не даёт заметно просесть худший
    # случай (полностью недостижимая база) - его стоимость упирается в размер карты, а не
    # в этот лимит.
    MAX_EXPANSIONS = 1500

    def find_path(self, start_pos, end_pos, extra_blocked: set[tuple[int, int]] | None = None,
                  extra_cost: dict[tuple[int, int], float] | None = None):
        """Ищет путь между двумя точками алгоритмом A*."""
        extra_blocked = extra_blocked or set()
        extra_cost = extra_cost or {}
        start, end = self.get_node(start_pos.x, start_pos.y), self.get_node(end_pos.x, end_pos.y)
        if not start or not end:
            return []
        if start == end:
            return [self.get_world_pos(start)]

        end_key = (end.x, end.y)
        start_key = (start.x, start.y)

        nodes = {start_key: start}
        closed_set = set()
        best_g = {start_key: 0.0}

        start.g = 0.0
        start.h = math.hypot(start.x - end.x, start.y - end.y) * self.HEURISTIC_WEIGHT
        start.f = start.h
        start.parent = None

        counter = itertools.count()
        open_heap = [(start.f, next(counter), start)]
        expansions = 0

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            current_key = (current.x, current.y)
            if current_key in closed_set:
                continue
            closed_set.add(current_key)

            expansions += 1
            if expansions > self.MAX_EXPANSIONS:
                return []

            if current_key == end_key:
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

                neighbor_key = (nx, ny)
                if neighbor_key in nodes:
                    neighbor = nodes[neighbor_key]
                else:
                    neighbor = Node(nx, ny)
                    nodes[neighbor_key] = neighbor

                if neighbor_key != end_key and (not self.is_walkable(neighbor) or neighbor_key in extra_blocked):
                    continue

                if neighbor_key in closed_set:
                    continue

                move_cost = 1.414 if dx != 0 and dy != 0 else 1.0
                move_cost += extra_cost.get(neighbor_key, 0.0)
                tentative_g = current.g + move_cost

                if tentative_g < best_g.get(neighbor_key, math.inf):
                    best_g[neighbor_key] = tentative_g
                    neighbor.parent = current
                    neighbor.g = tentative_g
                    neighbor.h = math.hypot(neighbor.x - end.x, neighbor.y - end.y) * self.HEURISTIC_WEIGHT
                    neighbor.f = neighbor.g + neighbor.h
                    heapq.heappush(open_heap, (neighbor.f, next(counter), neighbor))

        return []