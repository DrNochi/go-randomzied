from dlgo.boards.normal import FrozenGoString, ZobristBoard, NormalGameState
from dlgo.boards.zobrist import HASH_CODE
from dlgo.gotypes import Player, Point

neighbor_tables = {}
corner_tables = {}


def get_adjacency_tables(rows, cols):
    key = (rows, cols)
    if key in neighbor_tables and key in corner_tables:
        return neighbor_tables[key], corner_tables[key]

    neighbor_table = {}
    corner_table = {}

    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            point = Point(r, c)

            neighbors = point.neighbors()
            on_board_neighbors = [n for n in neighbors
                                  if (1 <= n.row <= rows and
                                      1 <= n.col <= cols)]
            neighbor_table[point] = on_board_neighbors

            corners = point.corners()
            on_board_corners = [c for c in corners
                                if (1 <= c.row <= rows and
                                    1 <= c.col <= cols)]
            corner_table[point] = on_board_corners

    neighbor_tables[key] = neighbor_table
    corner_tables[key] = corner_table

    return neighbor_table, corner_table


class FastBoard(ZobristBoard):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)

        self._neighbor_table, self._corner_table = get_adjacency_tables(
            rows, cols)

    def place_stone(self, player, point):
        assert self.is_on_board(point)
        assert self[point] is None

        adj_own_strings = []
        adj_opponent_strings = []
        liberties = []

        for neighbor in self._neighbor_table[point]:
            adj_string = self[neighbor]

            if adj_string is None:
                liberties.append(neighbor)
            elif adj_string.owner == player:
                if adj_string not in adj_own_strings:
                    adj_own_strings.append(adj_string)
            else:
                if adj_string not in adj_opponent_strings:
                    adj_opponent_strings.append(adj_string)

        string = FrozenGoString(player, [point], liberties)

        for own_string in adj_own_strings:
            string = string.merged_with(own_string)

        for own_point in string.stones:
            self[own_point] = string

        self._hash ^= HASH_CODE[point, player]

        for opponent_string in adj_opponent_strings:
            replacement = opponent_string.without_liberty(point)
            if replacement.num_liberties:
                self._replace_string(opponent_string.without_liberty(point))
            else:
                self._capture_string(opponent_string)

    def _capture_string(self, string):
        for point in string.stones:
            for neighbor in self._neighbor_table[point]:
                adj_string = self[neighbor]
                if adj_string is not None and adj_string is not string:
                    self._replace_string(adj_string.with_liberty(point))

            self[point] = None
            self._hash ^= HASH_CODE[point, string.owner]

    def is_suicide(self, player, point):
        own_strings = []
        for neighbor in self._neighbor_table[point]:
            adj_string = self[neighbor]

            if adj_string is None:
                return False
            elif adj_string.owner == player:
                own_strings.append(adj_string)
            else:
                if adj_string.num_liberties == 1:
                    return False

        return True if all(neighbor.num_liberties == 1 for neighbor in own_strings) else False

    def will_capture(self, player, point):
        for neighbor in self._neighbor_table[point]:
            adj_string = self[neighbor]
            if adj_string is not None and adj_string.owner != player and adj_string.num_liberties == 1:
                return True
        return False


class FastGameState(NormalGameState):
    @staticmethod
    def new_game(board_size, komi):
        return FastGameState(FastBoard(board_size, board_size), Player.black, None, None, komi)

    def is_suicide(self, player, move):
        return self.board.is_suicide(player, move.point) if move.is_play else False

    def is_ko(self, player, move):
        return super().is_ko(player, move) if self.board.will_capture(player, move.point) else False
