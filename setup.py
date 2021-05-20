from setuptools import find_packages, setup

# Old versions of setuptools do not provide `find_namespace_packages`
# see https://github.com/pulp/pulp-cli/issues/248
# packages = find_namespace_packages(include=["pulpcore.cli.*"]) + ["pytest_pulp_cli"]
plugins = find_packages(where="pulpcore/cli")
packages = [f"pulpcore.cli.{plugin}" for plugin in plugins] + ["pulp_cli", "pytest_pulp_cli"]
plugins.remove("common")
plugin_entry_points = [plugin, f"pulpcore.cli.{plugin}" for plugin in plugins]

long_description = ""
with open("README.md") as readme:
    for line in readme:
        if line == "## Contributing\n":
            break
        long_description += line


setup(
    name="pulp-cli",
    description="Command line interface to talk to pulpcore's REST API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pulp/pulp-cli",
    version="0.10.0.dev",
    packages=packages,
    package_data={package: ["py.typed"] for package in plugin_packages},
    python_requires=">=3.6",
    install_requires=[
        "click~=8.0.1",
        "packaging",
        "PyYAML~=5.4.1",
        "requests~=2.25.1",
        "toml==0.10.2",
    ],
    extras_require={
        "pygments": ["pygments"],
        "shell": ["click-shell~=2.1"],
    },
    entry_points={
        "console_scripts": ["pulp=pulp_cli:main"],
        "pulp_cli.plugins": [f"{name}={module}" for name, module in plugin_entry_points],
    },
    license="GPLv2+",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Software Distribution",
        "Typing :: Typed",
    ],
)
