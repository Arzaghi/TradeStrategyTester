import os

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_git_commit_hash():
    return os.getenv("COMMIT_HASH", "local version running")

class OutputBuffer:
    def __init__(self):
        self.lines = []

    def add(self, line: str):
        """Add a line to the buffer."""
        self.lines.append(line)

    def flush(self):
        """Print all lines and clear the buffer."""
        print("\n".join(self.lines))
        self.lines.clear()
