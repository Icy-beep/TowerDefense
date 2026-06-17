import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


def main():

    from src.core.game_session import GameSession
    session = GameSession()

    from src.ui.game_view import GameView
    game_view = GameView(session)

    game_view.run()


if __name__ == "__main__":
    main()