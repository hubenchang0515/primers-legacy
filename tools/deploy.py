import os
import subprocess

def deploy(target:str):
    origin = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "init", "."], cwd=target)
    subprocess.run(["git", "remote", "add", "origin", origin], cwd=target)
    subprocess.run(["git", "checkout", "-b", "gh-pages"], cwd=target)
    subprocess.run(["git", "add", "*"], cwd=target)
    subprocess.run(["git", "commit", "-m", "\"Update gh-pages\""], cwd=target)
    subprocess.run(["git", "push", "-f", "origin", "gh-pages"], cwd=target)

if __name__ == '__main__':
    CURRENT_FILE = os.path.abspath(__file__)
    CURRENT_DIR =  os.path.dirname(CURRENT_FILE)
    DEPLOY_DIR = os.path.join(CURRENT_DIR, "..", "build", "primers-legacy")
    deploy(DEPLOY_DIR)