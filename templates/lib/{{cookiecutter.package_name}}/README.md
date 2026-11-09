# {{cookiecutter.package_name}}

[![lint](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/libs/{{cookiecutter.package_name}}/badges/lint.json)](https://alexxios.github.io/python-course-project/reports/libs/{{cookiecutter.package_name}}/)
[![tests](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/libs/{{cookiecutter.package_name}}/badges/tests.json)](https://alexxios.github.io/python-course-project/reports/libs/{{cookiecutter.package_name}}/)
[![coverage](https://img.shields.io/endpoint?url=https%3A//alexxios.github.io/python-course-project/reports/libs/{{cookiecutter.package_name}}/badges/coverage.json)](https://alexxios.github.io/python-course-project/reports/libs/{{cookiecutter.package_name}}/)

{{cookiecutter.description}}

Run `just check libs/{{cookiecutter.package_name}}` from the workspace root.
Manage runtime versions with `uv add <dependency>` from the repository root.
List dependency names and required extras without version bounds in this
library's `pyproject.toml`; the root manifest and shared lockfile control versions.
