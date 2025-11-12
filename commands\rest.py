from pathlib import Path
import requests
import tempfile
import zipfile
import os


def clone(repository, repository_url: str = ""):
    repository_url = repository_url['repository_url']

    if not repository_url.startswith(('https://github.com/', 'git@github.com:')):
        raise ValueError("Only GitHub URLs are supported")

    if repository_url.startswith('https://github.com/'):
        parts = repository_url.replace('https://github.com/', '').split('/')
    else:
        parts = repository_url.replace('git@github.com:', '').replace('.git', '').split('/')

    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL format")

    user, repo = parts[0], parts[1].replace('.git', '')
    zip_url = f"https://api.github.com/repos/{user}/{repo}/zipball/main"

    print(f"Cloning {repository.path}/{user}/{repo}...")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        tmp_path = tmp_file.name

    try:
        response = requests.get(zip_url, stream=True)
        response.raise_for_status()

        with open(tmp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            members = zip_ref.namelist()
            if not members:
                raise ValueError("Empty repository")

            root_dir = members[0]

            target_path = Path(f"./{user}/{repo}")
            target_path.mkdir(parents=True, exist_ok=True)

            for member in members:
                if member != root_dir:
                    relative_path = member[len(root_dir):]
                    if relative_path:
                        full_path = target_path / relative_path

                        if member.endswith('/'):
                            full_path.mkdir(parents=True, exist_ok=True)
                        else:
                            with zip_ref.open(member) as source, open(full_path, 'wb') as target:
                                target.write(source.read())

        print(f"Repository cloned successfully")

    except requests.RequestException as e:
        raise Exception(f"Failed to download repository: {e}")
    except zipfile.BadZipFile:
        raise Exception("Invalid ZIP file downloaded")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
