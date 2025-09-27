from src.chess.game import Game
from src.chess.puzzle import Puzzle
from src.utils.console import Style

from typing import Generator, Union
import zstandard as zstd
import pandas as pd
import io

class Loader:

    def __init__(self, window=None, epochs_per_window=None, min_elo=None):
        """
        Initialize a loader.

        The parameters `window` and `epochs_per_window` are used to generate a window of data.
        It's used to train the model on groups of batches, and not on the whole dataset at once.

        If you don't use a loader for training, you can ignore these parameters.

        :param window: size of the window
        :type window: int
        :param epochs_per_window: number of epochs per window
        :type epochs_per_window: int
        :param min_elo: minimum ELO to filter games
        :type min_elo: int
        """

        self.generator = None
        self.path = None

        self.window = window
        self.epochs_per_window = epochs_per_window

        self.min_elo = min_elo or 0

    def load(self, path: str, dtype: type = Game, chunksize: int = 128) -> Generator:
        """
        Load a .csv.zst or .pgn.zst file.

        If you load a game from a PGN, all the moves will be loaded and pushed to the game.
        If you load a puzzle from a CSV, only the first move will be loaded. 

        :param path: path to the file
        :type path: str
        :param dtype: type of the data to load (Game or Puzzle)
        :type dtype: type
        :param chunksize: size of the chunks to load (only for CSV)
        :type chunksize: int
        :return: generator of data
        :rtype: Generator[list]
        """
        
        if dtype not in [Game, Puzzle]:
            raise Exception("Invalid dtype, must be Game or Puzzle")
        
        if path.endswith(".csv.zst"):
            self.generator = self._stream_csv_zst(path, dtype, chunksize)
        elif path.endswith(".pgn.zst"):
            self.generator = self._stream_pgn_zst(path, dtype, chunksize)
        else:
            raise Exception("Invalid file format, must be .csv.zst or .pgn.zst")
        
        self.path = path
        return self
    
    def get(self) -> list:
        """
        Return a generated window of data.

        :return: window of data
        :rtype: list
        """

        if self.generator is None:
            raise Exception("No generator loaded")
        
        window = []
        if self.window is None:
            print(Style("WARNING", "[loader] No window size specified, loading all data") + f"|_ from {self.path}")
            for data in self.generator:
                window.extend(data)
        
        else:
            for _ in range(self.window):
                if self.generator is None:
                    break
                window.extend(next(self.generator))

        return window
    
    def skip(self, n: int):
        """
        Skip n elements in the generator.

        :param n: number of elements to skip
        :type n: int
        """

        for _ in range(n):
            next(self.generator)
    
    def __or__(self, other: 'Loader') -> 'Loader':
        """
        Chain two loaders together.

        :param other: loader to chain
        :type other: Loader
        :return: chained loader
        :rtype: Loader
        """

        if self.generator is None:
            return other
        if other.generator is None:
            return self
        
        return LoaderSet([self, other])
    
    def __iter__(self):
        return self.generator

    def _stream_csv_zst(self, filepath, dtype, chunksize=128):
        """Stream a .csv.zst file in chunks."""
        
        with open(filepath, 'rb') as f:
            dctx = zstd.ZstdDecompressor()
            stream_reader = dctx.stream_reader(f)
            text_stream = io.TextIOWrapper(stream_reader, encoding='utf-8')

            for chunk in pd.read_csv(text_stream, chunksize=chunksize):
                data = [dtype().load(list(row[1].values)) for row in chunk.iterrows()]
                yield data

    def _stream_pgn_zst(self, filepath, dtype, chunksize=128):
        """Stream a .pgn.zst file, decompressing line by line."""
        
        skip = False

        with open(filepath, 'rb') as f:
            dctx = zstd.ZstdDecompressor()
            stream_reader = dctx.stream_reader(f)
            text_stream = io.TextIOWrapper(stream_reader, encoding='utf-8')

            buffer = ""
            games = []
            for line in text_stream:
                buffer += line
                if line.strip() == "":  # Empty line signals end of PGN game
                    if not skip: 
                        game = dtype().load(buffer, format="pgn")
                        games.append(game)
                    skip = False
                    buffer = ""  # Reset buffer for next game

                    if len(games) == chunksize:
                        yield games
                        games = []

                elif "Elo" in line and self.min_elo > 0:
                    if "?" in line:
                        skip = True
                        continue
                    
                    current_elo = line.split(" ")[-1]
                    current_elo = int(current_elo[1:-3])
                    if current_elo < self.min_elo: skip = True

            if buffer.strip():  # Handle last game if no trailing newline
                yield [dtype().load(buffer)]

    def skip(self, n: int):
        """
        Skip n elements in the generator.

        :param n: number of elements to skip
        :type n: int
        """

        for _ in range(n):
            next(self.generator)

    def need_update(self, epoch):
        return epoch == 0 or (self.epochs_per_window is not None and epoch % self.epochs_per_window == 0)
    
    def get_update(self, epoch):
        return self.get()

class LoaderSet:

    def __init__(self, loaders: list[Loader]):
        self.loaders = loaders
        self.layout = [[] for _ in loaders]
        self.window = min([l.window for l in loaders])

    def need_update(self, epoch, _idx=False):
        idx = [l.need_update(epoch) for l in self.loaders]
        if _idx:
            return idx
        return any(idx)
    
    def get_update(self, epoch):
        update_idx = self.need_update(epoch, True)

        result = []
        for idx, need in enumerate(update_idx):
            if need:
                self.layout[idx] = self.loaders[idx].get()
            
            result.extend(self.layout[idx])

        return result
            

    def get(self) -> list:
        """
        Return a generated window of data.

        :return: window of data
        :rtype: list
        """

        window = []
        for loader in self.loaders:
            window.extend(loader.get())
        
        return window
    
    def __or__(self, other: Union[Loader, 'LoaderSet']) -> 'LoaderSet':
        """
        Chain two loaders together.

        :param other: loader to chain
        :type other: Loader
        :return: chained loader
        :rtype: Loader
        """

        if isinstance(other, Loader):
            self.loaders.append(other)
            return self

        if isinstance(other, LoaderSet):
            self.loaders.extend(other.loaders)
            return self
        
        raise Exception("Cannot concat with type <" + str(type(other)) + ">")

