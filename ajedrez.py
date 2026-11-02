# 用 ANSI 24 位真彩色在终端绘制国际象棋棋盘与棋子。
#
# 数据模型：棋盘是 8x8 的二维数组 board[row][col]，每格是一个 Piece 枚举成员。
# Piece 共 13 种状态：空 + 白方 6 种 + 黑方 6 种；每个成员自带字形和所属方，
# 棋盘上只存枚举值，字形/颜色不再散落在渲染代码里。
# 坐标约定：row 0 是第 8 横线（黑方底线），col 0 是 a 线，row 7 是第 1 横线。
#
# 显示用横向棋盘：把标准棋盘逆时针转 90° 画出来，黑方两列在左、白方两列在右。
# 棋子同样用横向棋符（旋转 90° 的版本）：黑棋 U+1FA0F..U+1FA14（rotate 90°，
# 朝右）、白棋 U+1FA33..U+1FA38（rotate 270°，朝左），与棋盘转向一致。
#
# 配色：棋盘格用背景色，白格 #ffffff、黑格 #000000；棋子用前景色叠在格子上。
# 颜色统一用 0xRRGGBB 整数表示，由 fg()/bg() 转成 ANSI 真彩色序列，换色只需改整数：
# int 自带取值范围，不用解析字符串，也没有 # 可省、#rgb 简写、大小写的歧义。
# 棋子刻意不用纯白/纯黑，而是 #e0e0e0 / #202020：纯色棋子会和同色格子背景
# 融为一体（白棋在 #ffffff 格、黑棋在 #000000 格上就看不见了）。
#
# 作者: ToyosatomiminoMiko  2026-11-02

from enum import Enum

# 调色板：颜色用 0xRRGGBB 整数，渲染时由 fg()/bg() 转成 ANSI 转义序列。
WHITE_SQUARE_BG = 0xFFFFFF  # 白格背景
BLACK_SQUARE_BG = 0x000000  # 黑格背景
WHITE_PIECE_FG = 0xE0E0E0   # 白棋前景
BLACK_PIECE_FG = 0x202020   # 黑棋前景
RESET = "\x1b[0m"

BOARD_SIZE = 8


def _rgb(color: int) -> tuple[int, int, int]:
    """把 0xRRGGBB 整数拆成 (r, g, b)，越界直接抛 ValueError。"""
    if not 0 <= color <= 0xFFFFFF:
        raise ValueError(f"颜色必须是 0x000000..0xFFFFFF 的整数，收到：{color!r}")
    return (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF


def fg(color: int) -> str:
    """返回 24 位真彩色前景色 ANSI 序列，颜色用 0xRRGGBB 整数，如 fg(0xE0E0E0)。"""
    r, g, b = _rgb(color)
    return f"\x1b[38;2;{r};{g};{b}m"


def bg(color: int) -> str:
    """返回 24 位真彩色背景色 ANSI 序列，颜色用 0xRRGGBB 整数，如 bg(0xFFFFFF)。"""
    r, g, b = _rgb(color)
    return f"\x1b[48;2;{r};{g};{b}m"


class Piece(Enum):
    """棋盘格子的 13 种状态：空 + 白方 6 种 + 黑方 6 种。

    value 是 (字形, 是否白方)：EMPTY 两项都是 None；其余成员的字形是横向棋符，
    "是否白方" 用来挑前景色。
    """

    EMPTY = (None, None)
    WHITE_KING = ("🨳", True)
    WHITE_QUEEN = ("🨴", True)
    WHITE_ROOK = ("🨵", True)
    WHITE_BISHOP = ("🨶", True)
    WHITE_KNIGHT = ("🨷", True)
    WHITE_PAWN = ("🨸", True)
    BLACK_KING = ("🨏", False)
    BLACK_QUEEN = ("🨐", False)
    BLACK_ROOK = ("🨑", False)
    BLACK_BISHOP = ("🨒", False)
    BLACK_KNIGHT = ("🨓", False)
    BLACK_PAWN = ("🨔", False)

    def __init__(self, glyph: str | None, is_white: bool | None) -> None:
        # Enum 会把 value 元组拆开传给 __init__，这里存成成员属性
        self.glyph = glyph
        self.is_white = is_white


# 标准开局：上面两行黑棋，下面两行白棋，中间四行空。
# 存的是标准棋盘坐标（row 0 = 第 8 横线），绘制时再转成横向视图。
# 每行按 a..h 排列，即 [车, 马, 象, 后, 王, 象, 马, 车]。
INITIAL_BOARD = [
    [Piece.BLACK_ROOK, Piece.BLACK_KNIGHT, Piece.BLACK_BISHOP, Piece.BLACK_QUEEN,
     Piece.BLACK_KING, Piece.BLACK_BISHOP, Piece.BLACK_KNIGHT, Piece.BLACK_ROOK],
    [Piece.BLACK_PAWN] * BOARD_SIZE,
    [Piece.EMPTY] * BOARD_SIZE,
    [Piece.EMPTY] * BOARD_SIZE,
    [Piece.EMPTY] * BOARD_SIZE,
    [Piece.EMPTY] * BOARD_SIZE,
    [Piece.WHITE_PAWN] * BOARD_SIZE,
    [Piece.WHITE_ROOK, Piece.WHITE_KNIGHT, Piece.WHITE_BISHOP, Piece.WHITE_QUEEN,
     Piece.WHITE_KING, Piece.WHITE_BISHOP, Piece.WHITE_KNIGHT, Piece.WHITE_ROOK],
]


def clean() -> None:
    """清屏（3J 连滚动缓冲一起清），每次重绘棋盘前调用。"""
    print("\x1b[3J\x1b[2J\x1b[H", end="")


def new_board() -> list[list[Piece]]:
    """返回初始局面的副本：逐行复制，避免后续走子时改动到共享的行。"""
    return [row[:] for row in INITIAL_BOARD]


def draw_board(board: list[list[Piece]]) -> None:
    """绘制横向棋盘：标准棋盘逆时针转 90°，黑方两列在左、白方两列在右。"""
    # 全盘只有 4 种颜色组合，先转成 ANSI 序列，避免 64 格重复转换
    white_bg = bg(WHITE_SQUARE_BG)
    black_bg = bg(BLACK_SQUARE_BG)
    white_fg = fg(WHITE_PIECE_FG)
    black_fg = fg(BLACK_PIECE_FG)
    for view_row in range(BOARD_SIZE):
        cells = []
        for view_col in range(BOARD_SIZE):
            # 视图是标准棋盘逆时针转 90° 后的结果：
            #   屏幕第 view_col 列 = 棋盘第 view_col 行（第 8 → 第 1 横线，左侧是黑方）；
            #   屏幕第 view_row 行 = 棋盘第 7 - view_row 列（h 线在上、a 线在下）。
            board_row = view_col
            board_col = BOARD_SIZE - 1 - view_row
            piece = board[board_row][board_col]
            # 国际象棋棋盘 a8 是白格：按棋盘坐标判断，行号 + 列号为偶数时是白格
            is_white_square = (board_row + board_col) % 2 == 0
            background = white_bg if is_white_square else black_bg
            if piece is Piece.EMPTY:
                cells.append(background + "  ")
            else:
                foreground = white_fg if piece.is_white else black_fg
                # 棋子后补一个空格，保持每格 2 列宽，棋盘才是正方形
                cells.append(background + foreground + piece.glyph + " ")
        # 每行结束重置一次，避免背景色/前景色泄漏到终端下一行
        print("".join(cells) + RESET)


def main() -> None:
    clean()
    draw_board(new_board())


if __name__ == "__main__":
    main()
