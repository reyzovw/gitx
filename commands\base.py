from core.repository import Repository
import os
import hashlib
import json
from pathlib import Path

def init(repository: Repository, e=None):
    repository.init()

def add(repository: Repository, kwargs):
    files = kwargs.get('files', [])
    repository.add(files)

def commit(repository: Repository, kwargs):
    message = kwargs.get('message', '')
    repository.commit(message)

def branch(repository: Repository, kwargs):
    new_name = kwargs.get('new_name')
    repository.rename_branch(new_name)

def remote(repository: Repository, kwargs):
    action = kwargs.get('action')
    name = kwargs.get('name')
    url = kwargs.get('url')
    repository.remote(action, name, url)

def push(repository: Repository, kwargs):
    remote = kwargs.get('remote')
    branch = kwargs.get('branch')
    set_upstream = kwargs.get('set_upstream', False)
    repository.push(remote, branch, set_upstream)

def auth(repository: Repository, kwargs):
    token = kwargs.get('token')
    repository.auth(token)

