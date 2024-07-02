# Requirements:
# packaging==24.1
# tomlkit==0.12.5
# requests_cache==1.2.1

from packaging.version import Version
from packaging.requirements import Requirement
from packaging.specifiers import Specifier, SpecifierSet
from packaging.utils import canonicalize_name
import tomlkit
import requests_cache


class Config:
    def __init__(self):
        self.warehouse = "https://pypi.org"
        self.packages = {
            canonicalize_name("pulp-glue"): {"strategy": "ignore"},
            canonicalize_name("importlib_metadata"): {"strategy": "semver"},
            canonicalize_name("click"): {"strategy": "semver"},
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
        print(requirement)
        name = requirement.name
        canonical_name = canonicalize_name(name, validate=True)
        specifier = requirement.specifier
        strategy = self.config.strategy(name)
        allow_prereleases = specifier.prereleases

        if strategy == "ignore":
            print(f"Skipping {name}")
            return

        response = self.session.get(f"{self.config.warehouse}/pypi/{canonical_name}/json")

        releases = response.json()["releases"]
        available_versions = sorted(
            (
                version
                for version in (Version(key) for key in releases.keys())
                if allow_prereleases or not version.is_prerelease
            )
        )

        latest_version = available_versions[-1]
        # installable_versions = list(specifier.filter(available_versions))
        if latest_version not in specifier:
            if strategy == "warn":
                print(f"Package {name} latest version {latest_version} is not in {specifier}.")
            elif strategy == "semver":
                upper_bound = None
                rest = []
                for spec in specifier:
                    if spec.operator in {"<", "<=", "=="}:
                        if upper_bound is not None:
                            if Version(spec.version) > Version(upper_bound.version):
                                rest.append(upper_bound)
                                upper_bound = spec
                            else:
                                rest.append(spec)
                        else:
                            upper_bound = spec
                    else:
                        rest.append(spec)
                print(upper_bound, rest)
                if latest_version < Version(upper_bound.version):
                    print(
                        "Dependency on {requirement} cannot be updated to include latest version {latest_version}."
                    )
                else:
                    if upper_bound.operator == "==":
                        upper_bound = Specifier(f"=={latest_version}")
                    elif upper_bound.operator == "<=":
                        upper_bound = Specifier(f"<={latest_version}")
                    elif upper_bound.operator == "<":
                        dots = len([c for c in upper_bound.version if c == "."])
                        if dots == 0:
                            new_version = f"{latest_version.major + 1}"
                        elif dots == 1:
                            new_version = f"{latest_version.major}.{latest_version.minor + 1}"
                        elif dots == 2:
                            new_version = f"{latest_version.major}.{latest_version.minor}.{latest_version.patch + 1}"
                        else:
                            return
                        upper_bound = Specifier(f"<{new_version}")
                    requirement.specifier = SpecifierSet(",".join(map(str, [upper_bound] + rest)))
                    print(requirement)

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
