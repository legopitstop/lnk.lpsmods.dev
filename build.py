from bs4 import BeautifulSoup
from functools import partial
from requests import Session
from requests_cache import CachedSession
from typing import Optional, Dict, Any
from pydantic import BaseModel
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, urljoin
import multiprocessing
import shutil
import json
import os
import chevron
import logging

try:
    import dotenv  # python-dotenv

    dotenv.load_dotenv()
except ImportError:
    ...

session = Session()
cached = CachedSession(".cache/http_cache.sqlite3")


class Meta(BaseModel):
    url: str
    title: Optional[str] = "Redirecting..."
    description: Optional[str] = None
    image: Optional[str] = None

def is_rel_url(url: str) -> bool:
    parsed = urlparse(url)
    return not parsed.scheme and not parsed.netloc

def add_query_params(url: str, new_params: Dict[str, Any]):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query.update(new_params)
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def get_meta(url: str, id: str) -> Meta:
    """
    Scrape URL for metadata

    :param url: The URL to scrape
    :type url: str
    :param id: The name of redirect id
    :type id: str
    :return: The resulting metadata
    :rtype: dict
    """
    url = add_query_params(url, {"ref": "lpsmods.dev"})
    meta = {"url": url, "id": id}
    res = cached.get(
        url,
        headers={
            "User-Agent": "python-requests/2.31.0",
        },
    )
    if res.status_code != 200:
        return Meta(url=url)
    soup = BeautifulSoup(res.text, features="html.parser")
    metas = soup.find_all("meta")
    for m in metas:
        if m.get("name") == "description":
            meta["description"] = m.get("content")
        if m.get("property") == "og:image":
            image_url = m.get("content")
            if is_rel_url(image_url):
                parsed = urlparse(url)
                meta["image"] =  urljoin(parsed.netloc, image_url)
            else:
                meta["image"] = image_url
    title = soup.find("title")
    if title:
        meta["title"] = title.text
    return Meta.model_validate(meta)


def search_curse_mods(game_id, author_id, index):
    # https://console.curseforge.com/#/api-keys
    r = session.get(
        "https://api.curseforge.com/v1/mods/search",
        params={"gameId": game_id, "authorId": author_id, "index": index},
        headers={
            "User-Agent": "python-requests/2.31.0",
            "Accept": "application/json",
            "x-api-key": os.getenv("CURSE_KEY"),
        },
    )
    if r.status_code != 200:
        logging.warning("Failed to get Curseforge mods: %s %s", r.status_code, r.text)
        exit(1)
        return None
    return r.json()


def get_curse_mods(game_id, author_id):
    index = 0
    mods = []
    while True:
        data = search_curse_mods(game_id, author_id, index)
        mods.extend(data["data"])
        if len(data["data"]) < 50:
            break
        index += 50

    return mods


def get_rinth_mods(user_slug):
    r = session.get(f"https://api.modrinth.com/v2/user/{user_slug}/projects")
    if r.status_code != 200:
        logging.warning("Failed to get Modrinth mods: %s %s", r.status_code, r.text)
        exit(1)
        return None
    return r.json()


def create(template, name, url):
    meta = get_meta(url, name)
    print("-", name + ".html")
    fp = f"dist/{ name }.html"
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as html:
        content = chevron.render(template, meta.model_dump())
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
    with open("src/template.html") as fd:
        template = fd.read()

    # Load redirects
    with open("redirects.json") as fd:
        data = json.load(fd)

    # Curseforge redirects
    # TODO: Fetch all when count < total
    if "curseforge" in data:
        author_id = data["curseforge"]
        for project in get_curse_mods(432, author_id):
            data["redirects"][str(project["id"])] = project["links"]["websiteUrl"]

        for project in get_curse_mods(78022, author_id):
            data["redirects"][str(project["id"])] = project["links"]["websiteUrl"]

    # Modrinth redirects
    if "modrinth" in data:
        for project in get_rinth_mods(data["modrinth"]):
            slug = str(project["slug"])
            data["redirects"][
                slug
            ] = f"https://modrinth.com/{ project['project_type'] }/{ slug }"

    # Split names
    redirects = {}
    for names, target in data["redirects"].items():
        for name in names.split(","):
            redirects[str(name)] = str(target)

    # Create copy of redirects for dist
    with open("dist/redirects.json", "w") as re:
        lst = []
        for name, target in redirects.items():
            lst.append({"name": name, "target": target})
        re.write(json.dumps(lst, separators=(",", ":")))

    with multiprocessing.Pool() as p:
        p.starmap(partial(create, template), redirects.items())


if __name__ == "__main__":
    main()
