import json
import os
import hashlib
import re
import time

import requests
from pathlib import Path
import base64

class Repository:
    def __init__(self, path: str):
        self.path = path
        self.vcs_dir = os.path.join(path, ".gitx")
        self.__config_path = f"{self.vcs_dir}/config.json"
        self.__index_path = f"{self.vcs_dir}/index.json"
        self.__head_path = f"{self.vcs_dir}/HEAD"
        self.__auth_path = f"{self.vcs_dir}/auth.json"

    def __register_user(self):
        if not os.path.exists(self.__config_path):
            with open(self.__config_path, "w") as file:
                json.dump({"author": None, "remotes": {}}, file, indent=4)

    def __get_config(self):
        with open(self.__config_path, "r") as file:
            return json.load(file)

    def __save_config(self, config):
        with open(self.__config_path, "w") as file:
            json.dump(config, file, indent=4)

    def __get_auth(self):
        if os.path.exists(self.__auth_path):
            with open(self.__auth_path, "r") as file:
                return json.load(file)
        return {"token": None}

    def __get_ignore_patterns(self):
        ignore_file = os.path.join(self.path, ".gitxignore")
        patterns = []

        if os.path.exists(ignore_file):
            with open(ignore_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)

        patterns.extend(['.gitx/', '__pycache__/', '*.pyc', '.git'])
        return patterns

    def __should_ignore(self, filepath, patterns):
        relative_path = str(filepath.relative_to(self.path))

        for pattern in patterns:
            regex_pattern = pattern.replace('.', '\\.').replace('*', '.*').replace('?', '.')
            if re.match(regex_pattern, relative_path) or regex_pattern in relative_path:
                return True
            # Проверяем совпадение с путем
            if pattern in relative_path:
                return True

        return False

    def __save_auth(self, auth):
        with open(self.__auth_path, "w") as file:
            json.dump(auth, file, indent=4)

    def __get_index(self):
        if os.path.exists(self.__index_path):
            with open(self.__index_path, "r") as file:
                return json.load(file)
        return {}

    def __save_index(self, index):
        with open(self.__index_path, "w") as file:
            json.dump(index, file, indent=4)

    def __get_head(self):
        if os.path.exists(self.__head_path):
            with open(self.__head_path, "r") as file:
                return file.read().strip()
        return "refs/heads/main"

    def __hash_file(self, filepath):
        with open(filepath, 'rb') as f:
            return hashlib.sha1(f.read()).hexdigest()

    def __get_github_headers(self):
        auth = self.__get_auth()
        token = auth.get("token")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        return headers

    def __github_api_request(self, method, url, data=None):
        headers = self.__get_github_headers()
        response = requests.request(method, url, headers=headers, json=data)

        if response.status_code in [200, 201]:
            return response.json() if response.content else None
        else:
            # Пробрасываем ошибку для обработки в основном методе
            error_msg = response.json().get('message', f"HTTP {response.status_code}")
            raise Exception(error_msg)

    def init(self) -> bool:
        try:
            os.makedirs(self.vcs_dir, exist_ok=True)
            os.makedirs(os.path.join(self.vcs_dir, "objects"))
            os.makedirs(os.path.join(self.vcs_dir, "refs", "heads"))

            self.__register_user()

            with open(self.__head_path, "w") as file:
                file.write("refs/heads/main")

            print(f"Initialized empty gitx repository")
            return True
        except FileExistsError:
            print("Repository already exists")
            return False

    def add(self, files):
        index = self.__get_index()
        ignore_patterns = self.__get_ignore_patterns()

        # Если добавляется .gitxignore, добавляем его в первую очередь
        if '.gitxignore' in files or '.gitxignore' in [f for pattern in files for f in Path(self.path).glob(pattern)]:
            gitxignore_path = Path(self.path) / ".gitxignore"
            if gitxignore_path.exists():
                self.__add_single_file(gitxignore_path, index, ignore_patterns)

        for pattern in files:
            # Рекурсивно ищем файлы включая подпапки
            for filepath in Path(self.path).rglob(pattern):
                if filepath.is_file():
                    # Пропускаем .gitxignore так как уже добавили выше
                    if filepath.name == ".gitxignore":
                        continue

                    self.__add_single_file(filepath, index, ignore_patterns)

        self.__save_index(index)

    def __add_single_file(self, filepath, index, ignore_patterns):
        """Добавляет один файл в индекс с проверкой игнорирования"""
        try:
            # Проверяем не в ignore ли файл
            if self.__should_ignore(filepath, ignore_patterns):
                return

            # Читаем файл как текст
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Получаем относительный путь
            relative_path = str(filepath.relative_to(self.path))

            file_hash = hashlib.sha1(content.encode('utf-8')).hexdigest()
            index[relative_path] = {
                "hash": file_hash,
                "timestamp": os.path.getmtime(filepath),
                "content": content
            }
            print(f"Added {relative_path}")

        except UnicodeDecodeError:
            # Если файл бинарный, читаем как bytes
            with open(filepath, 'rb') as f:
                content = f.read()

            relative_path = str(filepath.relative_to(self.path))
            file_hash = hashlib.sha1(content).hexdigest()
            index[relative_path] = {
                "hash": file_hash,
                "timestamp": os.path.getmtime(filepath),
                "content": base64.b64encode(content).decode('utf-8'),
                "binary": True
            }
            print(f"Added binary file {relative_path}")

        except Exception as e:
            print(f"Error adding {filepath}: {e}")

    def commit(self, message):
        index = self.__get_index()
        head = self.__get_head()

        commit_data = {
            "tree": {},
            "parent": None,
            "author": "Unknown",
            "message": message,
            "timestamp": int(time.time())
        }

        for filepath, fileinfo in index.items():
            commit_data["tree"][filepath] = {
                "hash": fileinfo["hash"],
                "content": fileinfo["content"],
                "binary": fileinfo.get("binary", False)  # сохраняем флаг бинарности
            }

            # Сохраняем объект файла
            obj_path = os.path.join(self.vcs_dir, "objects", fileinfo["hash"])
            if not os.path.exists(obj_path):
                if fileinfo.get("binary"):
                    # Для бинарных файлов сохраняем как есть
                    with open(obj_path, 'wb') as f:
                        f.write(base64.b64decode(fileinfo["content"]))
                else:
                    # Для текстовых файлов сохраняем как текст
                    with open(obj_path, 'w', encoding='utf-8') as f:
                        f.write(fileinfo["content"])

        commit_hash = hashlib.sha1(json.dumps(commit_data, sort_keys=True).encode()).hexdigest()
        commit_path = os.path.join(self.vcs_dir, "objects", commit_hash)
        with open(commit_path, 'w', encoding='utf-8') as file:
            json.dump(commit_data, file, indent=2, ensure_ascii=False)

        branch_path = os.path.join(self.vcs_dir, head.replace('refs/heads/', ''))
        with open(branch_path, 'w') as file:
            file.write(commit_hash)

        print(f"Committed {commit_hash[:8]} {message}")

    def rename_branch(self, new_name):
        if new_name:
            with open(self.__head_path, "w") as file:
                file.write(f"refs/heads/{new_name}")
            print(f"Renamed branch to {new_name}")

    def remote(self, action, name, url):
        config = self.__get_config()
        if action == "add":
            if "remotes" not in config:
                config["remotes"] = {}
            config["remotes"][name] = url
            self.__save_config(config)
            print(f"Added remote {name} = {url}")

    def auth(self, token):
        auth_data = {"token": token}
        self.__save_auth(auth_data)
        print("GitHub token saved")

    def push(self, remote_name, branch, set_upstream):
        config = self.__get_config()
        if "remotes" not in config or remote_name not in config["remotes"]:
            print(f"Remote {remote_name} not found")
            return

        remote_url = config["remotes"][remote_name]
        if not remote_url.startswith("https://github.com/"):
            print("Only GitHub remotes supported")
            return

        parts = remote_url.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            print("Invalid remote URL")
            return

        owner, repo = parts[0], parts[1].replace(".git", "")
        branch_ref = self.__get_head().replace("refs/heads/", "")

        print(f"Pushing to {remote_url}...")

        try:
            branch_file = os.path.join(self.vcs_dir, branch_ref)
            if not os.path.exists(branch_file):
                print("No commits to push")
                return

            with open(branch_file, "r") as f:
                commit_hash = f.read().strip()

            commit_path = os.path.join(self.vcs_dir, "objects", commit_hash)
            if not os.path.exists(commit_path):
                print(f"Commit {commit_hash} not found")
                return

            with open(commit_path, "r", encoding='utf-8') as f:
                commit_data = json.load(f)

            auth = self.__get_auth()
            if not auth.get("token"):
                print("GitHub token not set. Use: gitx auth <token>")
                return

            print(f"Pushing commit {commit_hash[:8]} to {owner}/{repo} on branch {branch}")

            base_url = f"https://api.github.com/repos/{owner}/{repo}"

            tree_data = self.__build_tree_data(commit_data["tree"])

            if not tree_data:
                print("No files to push")
                return

            self.__push_to_empty_repo(base_url, tree_data, commit_data["message"], branch)

        except Exception as e:
            print(f"Push failed: {e}")

    def __build_tree_data(self, commit_tree):
        tree_data = []

        for filepath, file_info in commit_tree.items():
            is_binary = file_info.get("binary", False)
            content = file_info["content"]

            if is_binary:
                encoded_content = content
            else:
                encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

            tree_data.append({
                "path": filepath,
                "mode": "100644",
                "type": "blob",
                "content": encoded_content
            })
            file_type = "binary" if is_binary else "text"
            print(f"Preparing {filepath} ({file_type})")

        return tree_data

    def __push_to_empty_repo(self, base_url, tree_data, message, branch):
        try:
            tree_response = requests.post(
                f"{base_url}/git/trees",
                headers=self.__get_github_headers(),
                json={"tree": tree_data}
            )

            if tree_response.status_code not in [200, 201]:
                raise Exception(f"Failed to create tree: {tree_response.text}")

            tree_sha = tree_response.json()["sha"]

            commit_response = requests.post(
                f"{base_url}/git/commits",
                headers=self.__get_github_headers(),
                json={
                    "message": message,
                    "tree": tree_sha,
                    "parents": []
                }
            )

            if commit_response.status_code not in [200, 201]:
                raise Exception(f"Failed to create commit: {commit_response.text}")

            commit_sha = commit_response.json()["sha"]

            ref_response = requests.post(
                f"{base_url}/git/refs",
                headers=self.__get_github_headers(),
                json={"ref": f"refs/heads/{branch}", "sha": commit_sha}
            )

            if ref_response.status_code not in [200, 201]:
                raise Exception(f"Failed to create branch: {ref_response.text}")

            print(f"Push completed successfully: {commit_sha[:8]}")

        except Exception as e:
            if "empty" in str(e).lower() or "409" in str(e):
                self.__push_via_contents_api_with_dirs(base_url, tree_data, message, branch)
            else:
                raise e

    def __push_via_contents_api_with_dirs(self, base_url, tree_data, message, branch):
        created_dirs = set()

        for file_data in tree_data:
            filepath = file_data["path"]
            dir_path = os.path.dirname(filepath)

            if dir_path and dir_path not in created_dirs:
                parts = dir_path.split('/')
                current_path = ""
                for part in parts:
                    current_path = os.path.join(current_path, part).replace('\\', '/')
                    if current_path and current_path not in created_dirs:
                        created_dirs.add(current_path)

            try:
                response = requests.put(
                    f"{base_url}/contents/{filepath}",
                    headers=self.__get_github_headers(),
                    json={
                        "message": message,
                        "content": file_data["content"],
                        "branch": branch
                    }
                )

                if response.status_code in [200, 201]:
                    print(f"Created {filepath}")
                else:
                    print(f"Failed to create {filepath}: {response.text}")

            except Exception as e:
                print(f"Error creating {filepath}: {e}")


