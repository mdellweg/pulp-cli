# Requirements:
# packaging==24.1
# tomlkit==0.12.5
#  #requests==2.32.3
# requests_cache==1.2.1

from packaging.version import Version
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
import tomlkit
import requests_cache

# import requests


class Config:
    def __init__(self):
        self.warehouse = "https://pypi.org"
        self.packages = {
            "pulp-glue": {"strategy": "ignore"},
            "importlib_metadata": {"strategy": "semver"},
        }

    def strategy(self, name):
        try:
            return self.packages[name]["strategy"]
        except KeyError:
            return "warn"


class DependencyChecker:
    def __init__(self):
        super().__init__()
        self.config = Config()
        # TODO expire_after=datetime.timedelta(weeks=1)
        self.session = requests_cache.CachedSession("update_requirements")

    def check_dependency(self, dependency):
        requirement = Requirement(dependency)
        name = requirement.name
        specifier = requirement.specifier
        strategy = self.config.strategy(name)

        if strategy == "ignore":
            print(f"Skipping {name}")
            return

        # Sanitize before sending an http request.
        assert name.replace("-", "_").isidentifier()
        response = self.session.get(f"{self.config.warehouse}/pypi/{name}/json")

        releases = response.json()["releases"]
        versions = sorted(
            (
                version
                for version in (Version(key) for key in releases.keys())
                if not version.is_prerelease
            )
        )
        latest_version = versions[-1]
        if versions[-1] not in specifier:
            if strategy == "warn":
                print(f"Package {name} latest version {latest_version} is not in {specifier}.")
            elif strategy == "semver":
                # TODO
                pass

    def check_pyproject_toml(self):
        print("Looking at 'pyproject.toml':")
        with open("pyproject.toml", "r") as fp:
            pyproject_toml = tomlkit.load(fp)

        print("  Dependencies:")
        for dependency in pyproject_toml["project"]["dependencies"]:
            self.check_dependency(dependency)

        print("  Optional Dependencies:")
        for key, dependencies in pyproject_toml["project"]["optional-dependencies"].items():
            print(f"    '{key}':")
            for dependency in dependencies:
                self.check_dependency(dependency)


def main():
    checker = DependencyChecker()
    checker.check_pyproject_toml()


if __name__ == "__main__":
    main()
