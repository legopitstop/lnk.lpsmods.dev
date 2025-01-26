from bs4 import BeautifulSoup
from functools import partial
import multiprocessing
import shutil
import json
import os
import requests
import chevron
import logging

try:
    import dotenv  # python-dotenv

    dotenv.load_dotenv()
except ImportError:
    ...


# Scrape URL for metadata
def get_meta(url) -> dict:
    meta = {}
    res = requests.get(url)
    if res.status_code != 200:
        return {}
    soup = BeautifulSoup(res.text, features="html.parser")
    metas = soup.find_all("meta")
    for m in metas:
        if m.get("name") == "description":
            meta["description"] = m.get("content")
    title = soup.find("title")
    meta["title"] = title.text
    return meta


def get_mods(game_id, author_id):
    # https://console.curseforge.com/#/api-keys
    r = requests.get(
        "https://api.curseforge.com/v1/mods/search",
        params={"gameId": game_id, "authorId": author_id},
        headers={"Accept": "application/json", "x-api-key": os.getenv("CURSE_KEY")},
    )
    if r.status_code != 200:
        logging.warning('Failed to get Curseforge mods: %s %s', r.status_code, r.text)
        exit(1)
        return []
    return r.json()["data"]


def create(template, name, url):
    meta = get_meta(url)
    title = str(meta.get("title", "Redirecting...")).strip()
    desc = str(meta.get("description", "")).strip()
    print("-", name + ".html")
    with open(f"dist/{ name }.html", "w", encoding="utf-8") as html:
        content = chevron.render(template, {"title": title, "desc": desc, "url": url})
        soup = BeautifulSoup(content, "html.parser")
        html.write(
            soup.prettify().replace("\n ", "").replace("\n", "").replace("  ", "")
        )


def main():
    # Delete dist
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    # Copy source folder to dist
    shutil.copytree("src", "dist")

    # Load template
    with open("template.html") as fd:
        template = fd.read()

    # Load redirects
    with open("redirects.json") as fd:
        data = json.load(fd)

    # Curseforge redirects
    # TODO: Fetch all when count < total
    if "curseforge" in data:
        author_id = data["curseforge"]
        for project in get_mods(432, author_id):
            data["redirects"][str(project["id"])] = project["links"]["websiteUrl"]
        for project in get_mods(78022, author_id):
            data["redirects"][str(project["id"])] = project["links"]["websiteUrl"]

    # Modrinth redirects
    if "modrinth" in data:
        author = data["modrinth"]
        r = requests.get(f"https://api.modrinth.com/v2/user/{author}/projects")
        if r.status_code == 200:
            for project in r.json():
                project_type = project["project_type"]
                slug = project["slug"]
                data["redirects"][str(project["id"])] = (
                    f"https://modrinth.com/{ project_type }/{ slug }"
                )
        else:
            logging.warning("Failed to get Modrinth mods: %s %s", r.status_code, r.text)
            exit(1)

    # Split names
    redirects = {}
    for names, target in data["redirects"].items():
        for name in names.split(","):
            redirects[str(name)] = str(target)

    # Create copy of redirects for dist
    with open("dist/redirects.json", "w") as re:
        lst = []
        for name, target in redirects.items():
            lst.append({'name': name, 'target': target})
        re.write(json.dumps(lst, indent=4))

    with multiprocessing.Pool() as p:
        p.starmap(partial(create, template), redirects.items())


if __name__ == "__main__":
    main()
