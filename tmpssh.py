#!/usr/bin/env python

# Runs an SSH server that supports shell and SFTP access for the current user.
# No root privileges required.

# Requires sshd in PATH, but no Python dependencies.

import os
import sys
import pwd
import shutil
import subprocess
import tempfile
import requests
import hashlib
from pathlib import Path
from argparse import ArgumentParser

GITHUB_KEYS_ENDPOINT = "https://github.com/{username}.keys"

if 'XDG_STATE_HOME' in os.environ:
    STATE_DIR = Path(os.environ['XDG_STATE_HOME'])
else:
    STATE_DIR = Path.home() / '.local/state'
STATE_DIR = STATE_DIR / 'tmpssh'

def create_parser():
    parser = ArgumentParser(usage="Grants temporary SSH access as the current user")
    parser.add_argument("-f", "--file", action="append", help="authorized_keys file")
    parser.add_argument("--url", action="append", help="authorized_keys file from the web")
    parser.add_argument("--github", action="append", help="Grant access to a Github user")
    parser.add_argument("-p", "--port", default=2222, help="Port to listen on")
    parser.add_argument("-q", "--quiet", action='store_true')
    return parser

def do_get(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def ensure_cache_dir() -> Path:
    cache_dir = STATE_DIR / 'pubkeys'
    cache_dir.mkdir(mode=0o700, exist_ok=True, parents=True)
    return cache_dir

def get_and_save_url(file: Path, url: str):
    content = do_get(url)
    with file.open('w') as fp:
        fp.write(content)


def make_authorized_keys(parsed_args) -> Path:
    sources = list(parsed_args.file or [])

    urls = list(parsed_args.url or [])
    for github_user in parsed_args.github or []:
        urls.append(GITHUB_KEYS_ENDPOINT.format(username=github_user))

    if urls:
        cache_dir = ensure_cache_dir()
        prev_mask = os.umask(0o022)
        for url in urls:
            cache_file_name = hashlib.sha3_256(url.encode()).hexdigest()
            cache_file_path = cache_dir / cache_file_name
            if not cache_file_path.exists():
                get_and_save_url(cache_file_path, url)
            sources.append(cache_file_path)        
        os.umask(prev_mask)
    
    n_sources = len(sources)
    if n_sources == 0:
        authorized_keys = Path.home() / '.ssh/authorized_keys'
        if authorized_keys.exists():
            return authorized_keys
        else:
            parsed_args.parser.error("No key sources given, and ~/.ssh/authorized_keys does not exist.")
    elif n_sources == 1:
        return sources[0]
    else:
        return merge_files(sources)
    
def generate_sshd_config(authorized_keys: Path, user: str):
    return f"""
AuthorizedKeysFile	{str(authorized_keys)}
AllowUsers	{user}
PubkeyAuthentication	yes
PasswordAuthentication	no
PermitRootLogin	no
"""
    
def merge_files(files: list[Path]) -> Path:
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmpfile:
        for file in files:
            tmpfile.write(file.read_bytes())
        return Path(tmpfile.name)

def ensure_host_key() -> Path:
    host_key = STATE_DIR / 'host_ed25519_key'
    STATE_DIR.mkdir(mode=0o700, exist_ok=True, parents=True)
    if not host_key.exists():
        subprocess.run(['ssh-keygen', '-q', '-N', '', '-t', 'ed25519', '-f', str(host_key)]).check_returncode()
    return host_key

def get_username():
    return pwd.getpwuid(os.getuid())[0]

def main():
    parser = create_parser()
    parsed_args = parser.parse_args()
    parsed_args.parser = parser

    authorized_keys_path = make_authorized_keys(parsed_args)
    sshd_config = generate_sshd_config(authorized_keys_path, get_username())
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as sshd_config_file:
        sshd_config_file.write(sshd_config)
    host_key = ensure_host_key()
    sshd = shutil.which("sshd")
    argv = [sshd, '-Dp', str(parsed_args.port), '-f', sshd_config_file.name, '-h', str(host_key)]
    if not parsed_args.quiet:
        argv.append('-e')
        print(argv)
        print(sshd_config)
    os.execv(sshd, argv)
        
if __name__ == '__main__':
    main()
