# CI and GitHub Pages reports

## Checks

`checks.yml` is shared by default-branch and pull-request workflows. It discovers
`services/*/pyproject.toml` and `libs/*/pyproject.toml` for a dynamic job matrix,
including an independent `integration` job even when there are no members.
`fail-fast: false` lets healthy members finish when another fails collection.
A separate tooling job checks the generated README and builds documentation.

Pants owns the dependency graph and CI target selection. Each member scaffold
includes a `BUILD` file covering its Python sources, tests, and other files.
Pants infers first-party dependencies from Python imports. uv continues to own
package installation and its lockfile; Just runs the existing lint/test commands.
For runtime relationships that cannot be inferred from imports, add an explicit
dependency such as `libs/common:member` to the consumer's `python_sources` target
in its `BUILD` file. Manifest declarations alone do not create Pants graph edges.

PR discovery runs `pants --changed-since=<merge-base> --changed-dependents=transitive list`
and converts its target addresses into unique member paths with `jq`. Integration
always runs. Member metadata/assets are dependencies of that member's Python
targets; shared configuration, lockfiles, and tooling are dependencies of all
members. Deletions and renames run the full matrix because a removed import may
no longer have an owner in the current graph. Default-branch publication also
checks every member, keeping published reports and Allure history complete.

Install the [Pants launcher](https://www.pantsbuild.org/stable/docs/getting-started/installing-pants)
for local queries; `pants.toml` pins the engine version. CI installs it in discovery.
There is no generated dependency graph or dependency regeneration command:

```bash
pants dependencies --transitive services/api:member
pants dependents --transitive libs/common::
pants --changed-since=HEAD --changed-dependents=transitive list
```

See [Pants target selection](https://www.pantsbuild.org/stable/docs/using-pants/advanced-target-selection)
for native filters and changed-file options. PRs build Allure reports for selected
scopes only; unselected members have unavailable results in the combined artifact.

The same Just commands run locally and in CI:

```bash
just check services/api
just test libs/common
just lint integration
just check
just reports
```

Each member's pytest invocation runs from its directory, installs its declared
workspace/runtime dependencies and shared dev tools into `.venvs/<group>/<name>`,
and measures only its own `src/`. The shared uv lockfile still resolves the whole
workspace. Separate environments expose imports of unrelated workspace packages;
they do not prevent access to transitive or tooling dependencies.

Integration tests use a separate environment with all members installed. Their
coverage does not contribute to member badges. Empty integration suites are
allowed; empty member suites fail. Root scripts and integration tests are linted
under the integration scope, along with the shared root `conftest.py`. Members
run their own lint and formatting checks.

Native Ruff, pytest, coverage, and Allure outputs go directly to each scope's
report directory. `build_reports.py` only summarizes those outputs; it neither
runs checks nor partitions workspace-wide results. Missing results/tool errors
show unavailable, empty suites show no tests, and skipped suites show skipped.
Reports are published after failing checks when report generation succeeds;
the checks keep their failure status. Same-repository PRs also publish a snapshot
of their reports, while fork runs retain artifacts only.

## Pull request summaries

Both CI workflows call `publish-reports.yml` after reports are retained, including
after failed tests. It uses
[JamesIves/github-pages-deploy-action](https://github.com/JamesIves/github-pages-deploy-action)
to update the `gh-pages` branch. `pages.yml` then uses GitHub's checkout,
upload-artifact, and deploy Pages actions to publish it. PR reports live under
`/pr-preview/pr-<number>/<scope>/allure/`.
Each PR update replaces that PR's preview; main-site updates preserve previews.

After updating the preview branch, the official
[allure-framework/allure-action](https://github.com/allure-framework/allure-action)
posts or updates the summary with links to the hosted PR reports. The action
reads only Allure report folders, excluding the custom `summary.json` files from
`just reports`. It is pinned to `v0.9.0`, whose native table has one row per report,
including empty matrix members. Dependabot excludes `0.10+` because those releases
switch to an aggregate table. There is no custom comment renderer.

PR reports restore the latest available base-branch Allure history to identify
new tests. They never save PR history into the base-branch cache. Without any
baseline, Allure treats the run as the first run and marks its tests new.

Fork and Dependabot PRs retain artifacts but skip publishing because their
tokens are read-only. Only publishing jobs receive write permissions. The first
PR preview seeds `gh-pages` from a successful default-branch run's documentation
and report artifacts, preserving the existing website.

Keep Pages configured with **GitHub Actions** as its source. `pages.yml` runs
on the default branch after CI completes, preserving the existing main-only
`github-pages` environment policy. GitHub requires this `workflow_run` workflow
to be merged into the default branch before it runs. Preview links become live
when the ensuing Pages deployment finishes; the workflow also supports manual runs.
The downloadable `check-reports` artifact remains available as well.

## Browser failure videos

Integration, service, and library pytest configurations enable
`--video=retain-on-failure`. Tests using pytest-playwright's managed browser
fixtures record videos; passing-test recordings are discarded. Install the
browser before running UI tests, for example
`uv run --group dev python -m playwright install chromium`. Linux CI also needs
`playwright install --with-deps chromium` and the application under test running.
Tests that do not use a browser do not launch one.

Raw videos live under `reports/<scope>/playwright/<test>/`. The root `conftest.py`
attaches finalized WebM files to the corresponding failed Allure test, including
setup or teardown failures when a recording exists. Member pytest configurations
set `--confcutdir=../..` to load this shared hook while retaining their own test
and coverage settings. No per-test attachment code is needed.

Allure copies attachments into `reports/<scope>/allure-results/`; the existing
artifact and Allure report jobs retain them. `just test <scope>` clears that
scope's old videos and Allure results before running. Override recording when
needed with `PYTEST_ADDOPTS='--video=off' just test <scope>`. Contexts created
manually outside the pytest-playwright fixtures need their own recording setup.

This follows the [Allure pytest-playwright video guide](https://allurereport.org/docs/guides/pytest-playwright-video/),
with attachment after the teardown report so pytest-playwright has finished
retaining its artifacts. Attachment errors are logged without replacing the
test's original failure.

## Badge setup

GitHub Pages is configured with **GitHub Actions** as its source at
<https://alexxios.github.io/python-course-project/>. The README and scaffold
templates already use this URL for their badges and report links. The one-time
setup workflow and binding script were removed after configuration.

Default-branch CI builds the documentation and reports; the shared publisher
deploys them alongside PR snapshots. Badges become available after the first
successful deployment. No custom token or secret is required.

Future `just new-service` and `just new-lib` commands render direct links from
the bound templates without Git/network access or a saved URL configuration.
Running Cookiecutter directly on either member template works the same way.
The setup preserves member prose and updates only standalone Shields lint,
tests, and coverage badge lines. Normal codegen never rewrites member READMEs.

After a Pages/domain move, update the plain report URLs and URL-encoded Shields
endpoints in existing member READMEs, `templates/service/*/README.md`,
`templates/lib/*/README.md`, and `templates/readme/header.md.jinja`, then run
`just codegen`. Shields needs public access to the endpoint JSON.

## Published layout

```text
/
├── index.html                         MkDocs documentation
├── ci-reports/                        This guide
└── reports/
    ├── index.html                     Links and status for every scope
    ├── services/<name>/
    │   ├── index.html                 Only this service's check results
    │   ├── badges/{lint,tests,coverage}.json
    │   ├── coverage/                  Only its source, from its tests
    │   ├── allure/                    Its Allure report and trends
    │   ├── allure-results/            Native results and attachments
    │   ├── playwright/                Retained browser failure videos
    │   ├── history.jsonl              Published Allure history snapshot
    │   ├── junit.xml
    │   ├── coverage.xml, coverage.json
    │   ├── ruff.json, ruff-format.json
    │   ├── lint.exit, format.exit, test.exit
    │   └── summary.json
    ├── libs/<name>/                   Same layout for each library
    └── integration/                   Separate integration results
```

Pages deployment uses an Actions artifact built from the `gh-pages` branch.
The deployment action manages branch updates and preserves `/pr-preview/` when
replacing the default-branch site. Publishing jobs are serialized to avoid
overwriting concurrent updates. GitHub Pages keeps **GitHub Actions** as its
source; no separate branch-based Pages build is required.

Coverage pages exist only when data is available. Every badge opens its own
member's default-branch report, which links to its coverage and Allure pages.

## Allure history

The reporting job restores `.allure-history/` from a default-branch cache and
builds an Allure report for each scope using a separate `<scope>.jsonl` history
file. It then saves the histories using a unique run/attempt key. Failed test
runs still enter history. Default-branch workflows are serialized to avoid
competing history updates. Cache eviction starts new history.

PRs restore base-branch history and pass it to each scope's report generator,
without saving the resulting PR history cache. Each scope's artifact is uploaded
even if its checks fail; the reporting job collects them into `check-reports`
and, on the default branch, `default-site` for the shared publisher.
