"""
1. open pyproject.toml, increase the version number.
2. poetry build.
3. poetry publish
"""
import toml
from loguru import logger

with open("pyproject.toml",'r')as f :
    data = toml.load(f)
    v = data["tool"]["poetry"]["version"]
    major,minor,version = v.split(".")
    version = str(int(version) + 1)
    data["tool"]["poetry"]["version"] = ".".join([major,minor,version])
    logger.info(f"now pinject version is :{(major,minor,version)}")
with open("pyproject.toml","w") as f:
    toml.dump(data,f)

poetry build
poetry publish