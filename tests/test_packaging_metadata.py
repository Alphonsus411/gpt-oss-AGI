import importlib
import pathlib
import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_distribution_name_and_package_discovery_metadata():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert metadata["project"]["name"] == "gpt-oss-agi"
    assert metadata["tool"]["setuptools"]["packages"]["find"]["include"] == [
        "gpt_oss*",
        "agicore_core*",
    ]


def test_public_import_packages_remain_importable():
    assert importlib.import_module("gpt_oss").__name__ == "gpt_oss"
    assert importlib.import_module("agicore_core").__name__ == "agicore_core"
