import json
import os
import glob

os.makedirs("dist", exist_ok=True)

for file in glob.glob("dist/*"):
    os.remove(file)

with open("redirects.json") as fd:
    data = json.load(fd)
    with open("dist/redirects.json", "w") as re:
        re.write(json.dumps(data))

    for names, url in data.items():
        for name in names.split(","):
            with open(f"dist/{ name }.html", "w") as html:
                html.write(
                    f'<!DOCTYPE html><html lang="en-US"><head><title>Redirecting...</title><meta name="robots" content="noindex"><meta charset="utf-8"><meta name="robots" content="noindex"><link rel="canonical" href="{ url }" /><meta http-equiv="refresh" content="0;url={ url }" /><script>location="{ url }"</script></head><body> <h1>Redirecting&hellip;</h1><a href="{ url }">Click here if you are not redirected.</a></body></html>'
                )
