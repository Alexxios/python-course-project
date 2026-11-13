const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test } = require('node:test');
const { selectPublication, loadReports, assembleSite, renderSummary, postSummary } = require('./reports.cjs');

const publication = {
  prNumber: 11, runId: 123, attempt: 2, sha: 'abc123456',
  runUrl: 'https://github.com/owner/repo/actions/runs/123', baseBranch: 'main',
};
const pagesUrl = 'https://owner.github.io/repo/';

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'report-publishing-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

function write(root, file, content) {
  const target = path.join(root, file);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, typeof content === 'string' ? content : JSON.stringify(content));
}

function reportsFixture(root) {
  const scopes = ['services/app', 'libs/new', 'integration'];
  write(root, 'allure-matrix.json', { include: scopes.map((scope) => ({ path: scope })) });
  for (const [index, scope] of scopes.entries()) {
    write(root, `${scope}/allure/index.html`, `<h1>${scope}</h1>`);
    write(root, `${scope}/allure/summary.json`, {
      name: scope, stats: { total: index === 2 ? 0 : 3, passed: index === 2 ? 0 : 2, failed: index === 2 ? 0 : 1 },
      duration: 52000, newTests: index === 2 ? [] : ['new'], flakyTests: [], retryTests: [],
    });
    write(root, `${scope}/allure-history-available.json`, index === 0);
    write(root, `${scope}/summary.json`, { unrelated: true });
  }
  return loadReports(root);
}

test('renders every matrix member, including empty scopes, with exact-run report URLs', (t) => {
  const reports = reportsFixture(fixture(t));
  const body = renderSummary(reports, publication, pagesUrl);
  assert.equal(body.split('\n').filter((line) => line.startsWith('| `')).length, 3);
  assert.match(body, /\| `integration` \| 52s \| No tests \| 0 \|/);
  assert.match(body, /\| `services\/app` \| 52s \| 2 passed<br>1 failed \| \[1\]/);
  assert.match(body, /\| `libs\/new` \| 52s \| 2 passed<br>1 failed \| — \|/);
  assert.ok(body.includes('https://owner.github.io/repo/pull-requests/11/123-2/services/app/allure/'));
  assert.ok(body.includes('?transition=new'));
  assert.ok(!body.includes('All tests'));
});

test('does not deploy partial or unsafe report sets', (t) => {
  const root = fixture(t);
  reportsFixture(root);
  write(root, 'allure-matrix.json', { include: [{ path: '../escape' }] });
  assert.throws(() => loadReports(root), /Invalid.*scope/);
  reportsFixture(root);
  fs.rmSync(path.join(root, 'integration/allure/index.html'));
  assert.throws(() => loadReports(root), /Missing HTML report/);
});

test('PR publication preserves the main site and earlier snapshots', (t) => {
  const root = fixture(t);
  reportsFixture(path.join(root, 'incoming'));
  write(root, 'published/index.html', 'main');
  write(root, 'published/.git', 'worktree metadata');
  write(root, 'published/pull-requests/10/100-1/index.html', 'earlier PR');
  assembleSite(publication, root);
  assert.equal(fs.readFileSync(path.join(root, 'published/index.html'), 'utf8'), 'main');
  assert.equal(fs.readFileSync(path.join(root, 'published/.git'), 'utf8'), 'worktree metadata');
  assert.ok(fs.existsSync(path.join(root, 'published/pull-requests/10/100-1/index.html')));
  assert.ok(fs.existsSync(path.join(root, 'published/pull-requests/11/123-2/services/app/allure/index.html')));
});

test('default publication removes obsolete main files while preserving PR snapshots', (t) => {
  const root = fixture(t);
  write(root, 'incoming/index.html', 'updated main');
  write(root, 'published/index.html', 'old main');
  write(root, 'published/obsolete.html', 'removed page');
  write(root, 'published/.git', 'worktree metadata');
  write(root, 'published/pull-requests/11/123-2/index.html', 'PR');
  assembleSite({ ...publication, prNumber: null }, root);
  assert.equal(fs.readFileSync(path.join(root, 'published/index.html'), 'utf8'), 'updated main');
  assert.ok(!fs.existsSync(path.join(root, 'published/obsolete.html')));
  assert.ok(fs.existsSync(path.join(root, 'published/pull-requests/11/123-2/index.html')));
  assert.ok(fs.existsSync(path.join(root, 'published/.git')));
});

test('first PR publication bootstraps the main site; report links and Git metadata are rejected', (t) => {
  const root = fixture(t);
  reportsFixture(path.join(root, 'incoming'));
  write(root, 'published/.git', 'worktree metadata');
  write(root, 'bootstrap/index.html', 'main');
  assembleSite(publication, root);
  assert.equal(fs.readFileSync(path.join(root, 'published/index.html'), 'utf8'), 'main');
  fs.symlinkSync(path.join(root, 'bootstrap'), path.join(root, 'incoming/link'));
  assert.throws(() => assembleSite(publication, root), /Unsafe report entry/);
  fs.unlinkSync(path.join(root, 'incoming/link'));
  write(root, 'incoming/.git/config', 'untrusted metadata');
  assert.throws(() => assembleSite(publication, root), /Unsafe report entry/);
});

function githubFixture() {
  const pr = { number: 11, state: 'open', head: { sha: publication.sha, repo: { full_name: 'owner/repo' } }, base: { ref: 'main' } };
  const context = {
    repo: { owner: 'owner', repo: 'repo' },
    payload: {
      repository: { full_name: 'owner/repo', default_branch: 'main' },
      workflow_run: {
        id: 123, run_attempt: 2, head_sha: publication.sha, html_url: publication.runUrl,
        head_branch: 'DEV-9', event: 'pull_request', name: 'Pull request checks',
        conclusion: 'failure', head_repository: { full_name: 'owner/repo' },
      },
    },
  };
  const comments = [];
  const writes = [];
  const github = {
    rest: {
      pulls: { list: 'pulls.list', get: async () => ({ data: pr }) },
      actions: { listWorkflowRunArtifacts: 'artifacts.list', listWorkflowRuns: async () => ({ data: { workflow_runs: [{ id: 99 }] } }) },
      git: { getRef: async () => ({}) },
      repos: { getBranch: async () => ({ data: { commit: { sha: publication.sha } } }) },
      issues: {
        listComments: 'comments.list',
        createComment: async (comment) => writes.push({ kind: 'create', ...comment }),
        updateComment: async (comment) => writes.push({ kind: 'update', ...comment }),
      },
    },
    paginate: async (method) => {
      if (method === 'pulls.list') return [pr];
      if (method === 'artifacts.list') return [{ name: 'check-reports' }, { name: 'default-site' }];
      if (method === 'comments.list') return comments;
      throw new Error(`Unexpected API method: ${method}`);
    },
  };
  return { github, context, core: { info() {} }, pr, comments, writes };
}

test('failed checks with retained reports publish; cancelled, fork, and stale PR runs do not', async () => {
  const mock = githubFixture();
  const selected = await selectPublication(mock);
  assert.equal(selected.publish, true);
  assert.deepEqual(JSON.parse(selected.publication), publication);
  mock.pr.head.sha = 'newer';
  assert.equal((await selectPublication(mock)).publish, false);
  mock.pr.head.sha = publication.sha;
  mock.context.payload.workflow_run.conclusion = 'cancelled';
  assert.equal((await selectPublication(mock)).publish, false);
  mock.context.payload.workflow_run.conclusion = 'success';
  mock.pr.head.repo.full_name = 'fork/repo';
  assert.equal((await selectPublication(mock)).publish, false);
});

test('initial PR publication selects a retained default site for bootstrap', async () => {
  const mock = githubFixture();
  mock.github.rest.git.getRef = async () => { throw Object.assign(new Error('missing'), { status: 404 }); };
  const selected = await selectPublication(mock);
  assert.equal(selected['stored-site'], false);
  assert.equal(selected['bootstrap-run'], 99);
});

test('only the current default-branch run publishes the main site', async () => {
  const mock = githubFixture();
  Object.assign(mock.context.payload.workflow_run, {
    event: 'push', head_branch: 'main', name: 'Default branch checks and Pages deployment',
  });
  const selected = await selectPublication(mock);
  assert.equal(selected.artifact, 'default-site');
  assert.equal(selected['pr-number'], '');
  assert.equal(JSON.parse(selected.publication).prNumber, null);
  mock.github.rest.repos.getBranch = async () => ({ data: { commit: { sha: 'newer' } } });
  assert.equal((await selectPublication(mock)).publish, false);
});

test('missing artifacts and an absent bootstrap site skip publication', async () => {
  const mock = githubFixture();
  const paginate = mock.github.paginate;
  mock.github.paginate = async (method, options) => method === 'artifacts.list' ? [] : paginate(method, options);
  assert.equal((await selectPublication(mock)).publish, false);
  mock.github.paginate = async (method, options) => method === 'artifacts.list'
    ? [{ name: 'check-reports' }] : paginate(method, options);
  mock.github.rest.git.getRef = async () => { throw Object.assign(new Error('missing'), { status: 404 }); };
  assert.equal((await selectPublication(mock)).publish, false);
});

test('updates the existing Allure bot comment only after publication, skipping stale runs', async (t) => {
  const directory = fixture(t);
  reportsFixture(directory);
  const mock = githubFixture();
  mock.comments.push({ id: 7, user: { login: 'github-actions[bot]' }, body: '<!-- allure-report-summary --> old aggregate' });
  await postSummary({ ...mock, publication, pagesUrl, directory });
  assert.equal(mock.writes[0].kind, 'update');
  assert.equal(mock.writes[0].comment_id, 7);
  assert.ok(mock.writes[0].body.includes('/pull-requests/11/123-2/'));
  mock.comments[0].body = '<!-- allure-report-summary -->\n<!-- allure-run:124:1 -->';
  await postSummary({ ...mock, publication, pagesUrl, directory });
  assert.equal(mock.writes.length, 1);
  mock.pr.head.sha = 'newer';
  await postSummary({ ...mock, publication, pagesUrl, directory });
  assert.equal(mock.writes.length, 1);
});
