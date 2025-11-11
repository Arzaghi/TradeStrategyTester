import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_git_commit_hash():
    return os.getenv("COMMIT_HASH", "local version running")
