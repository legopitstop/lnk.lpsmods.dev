from bs4 import BeautifulSoup
import json
import os
import glob
import requests
import chevron


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


os.makedirs("dist", exist_ok=True)

for file in glob.glob("dist/*"):
    os.remove(file)

with open("template.html") as fd:
    template = fd.read()

with open("redirects.json") as fd:
    data = json.load(fd)
    with open("dist/redirects.json", "w") as re:
        re.write(json.dumps(data))

    for names, url in data.items():
        meta = get_meta(url)
        title = str(meta.get("title", "Redirecting...")).strip()
        desc = str(meta.get("description", "")).strip()
        for name in names.split(","):
            print("-", name + ".html")
            with open(f"dist/{ name }.html", "w", encoding="utf-8") as html:
                content = chevron.render(
                    template, {"title": title, "desc": desc, "url": url}
                )
                soup = BeautifulSoup(content, "html.parser")
                html.write(
                    soup.prettify()
                    .replace("\n ", "")
                    .replace("\n", "")
                    .replace("  ", "")
                )
