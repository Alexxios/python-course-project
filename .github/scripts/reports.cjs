const fs = require('node:fs');
const path = require('node:path');

const CONTENT_BRANCH = 'pages-reports';
const COMMENT_MARKER = '<!-- allure-report-summary -->';

async function selectPublication({ github, context, core }) {
  const run = context.payload.workflow_run;
  const repository = context.payload.repository;
  const repo = context.repo;
  const skip = (reason) => {
    core.info(reason);
    return { publish: false };
  };
  if (run.conclusion === 'cancelled' || run.head_repository.full_name !== repository.full_name) {
    return skip('Cancelled and fork runs retain artifacts without publication.');
  }

  let pr;
  if (run.event === 'pull_request' && run.name === 'Pull request checks') {
    const candidates = await github.paginate(github.rest.pulls.list, {
      ...repo, state: 'open', head: `${repo.owner}:${run.head_branch}`, per_page: 100,
    });
    pr = candidates.find((candidate) => candidate.head.sha === run.head_sha &&
      candidate.head.repo?.full_name === repository.full_name);
    if (!pr) return skip('The PR is closed, from a fork, or has a newer head commit.');
  } else if (['push', 'workflow_dispatch'].includes(run.event) &&
      run.name === 'Default branch checks and Pages deployment' &&
      run.head_branch === repository.default_branch) {
    const { data: branch } = await github.rest.repos.getBranch({ ...repo, branch: repository.default_branch });
    if (branch.commit.sha !== run.head_sha) return skip('A newer default-branch commit supersedes this run.');
  } else {
    return skip('Only default-branch checks and same-repository PR checks are published.');
  }

  const hasArtifact = async (runId, name) => {
    const artifacts = await github.paginate(github.rest.actions.listWorkflowRunArtifacts, {
      ...repo, run_id: runId, per_page: 100,
    });
    return artifacts.some((artifact) => artifact.name === name && !artifact.expired);
  };
  const artifact = pr ? 'check-reports' : 'default-site';
  if (!await hasArtifact(run.id, artifact)) return skip(`No retained ${artifact} artifact is available.`);

  let storedSite = true;
  try {
    await github.rest.git.getRef({ ...repo, ref: `heads/${CONTENT_BRANCH}` });
  } catch (error) {
    if (error.status !== 404) throw error;
    storedSite = false;
  }
  let bootstrapRun = '';
  if (pr && !storedSite) {
    const { data } = await github.rest.actions.listWorkflowRuns({
      ...repo, workflow_id: 'ci.yml', branch: repository.default_branch,
      status: 'completed', per_page: 30,
    });
    for (const candidate of data.workflow_runs) {
      if (await hasArtifact(candidate.id, 'default-site')) {
        bootstrapRun = candidate.id;
        break;
      }
    }
    if (!bootstrapRun) return skip('Waiting for a default-branch default-site artifact to preserve the main site.');
  }

  const publication = {
    runId: run.id, attempt: run.run_attempt, sha: run.head_sha, runUrl: run.html_url,
    prNumber: pr?.number ?? null, baseBranch: pr?.base.ref ?? repository.default_branch,
  };
  return {
    publish: true, artifact, 'stored-site': storedSite, 'bootstrap-run': bootstrapRun,
    'pr-number': pr?.number ?? '', publication: JSON.stringify(publication),
  };
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function loadReports(directory) {
  const matrix = readJson(path.join(directory, 'allure-matrix.json'));
  const seen = new Set();
  if (!matrix.include?.length) throw new Error('Missing Allure matrix members.');
  return matrix.include.map(({ path: scope }) => {
    if (!/^(integration|(?:services|libs)\/[a-zA-Z0-9][a-zA-Z0-9_.-]*)$/.test(scope) || seen.has(scope)) {
      throw new Error(`Invalid or duplicate report scope: ${scope}`);
    }
    seen.add(scope);
    const directoryForScope = path.join(directory, scope);
    if (!fs.existsSync(path.join(directoryForScope, 'allure/index.html'))) {
      throw new Error(`Missing HTML report for ${scope}`);
    }
    return {
      scope,
      summary: readJson(path.join(directoryForScope, 'allure/summary.json')),
      hasHistory: readJson(path.join(directoryForScope, 'allure-history-available.json')) === true,
    };
  });
}

function previewPath(publication) {
  for (const field of ['prNumber', 'runId', 'attempt']) {
    if (!Number.isSafeInteger(publication[field]) || publication[field] < 1) {
      throw new Error(`Invalid publication ${field}`);
    }
  }
  return `pull-requests/${publication.prNumber}/${publication.runId}-${publication.attempt}`;
}

function assertStaticTree(directory) {
  // Downloaded reports are data. Never copy Git metadata or follow links into the checkout.
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.name.toLowerCase() === '.git' || entry.isSymbolicLink()) {
      throw new Error(`Unsafe report entry: ${path.join(directory, entry.name)}`);
    }
    if (entry.isDirectory()) assertStaticTree(path.join(directory, entry.name));
    else if (!entry.isFile()) throw new Error(`Non-file report entry: ${entry.name}`);
  }
}

function assembleSite(publication, root = process.cwd()) {
  const incoming = path.join(root, 'incoming');
  const published = path.join(root, 'published');
  assertStaticTree(incoming);
  if (publication.prNumber) {
    loadReports(incoming); // Fail before deploying an incomplete report set.
    if (!fs.existsSync(path.join(published, 'index.html'))) {
      const bootstrap = path.join(root, 'bootstrap');
      assertStaticTree(bootstrap);
      if (!fs.existsSync(path.join(bootstrap, 'index.html'))) throw new Error('Missing default-branch site.');
      fs.cpSync(bootstrap, published, { recursive: true });
    }
    const destination = path.join(published, previewPath(publication));
    fs.rmSync(destination, { recursive: true, force: true });
    fs.cpSync(incoming, destination, { recursive: true });
  } else {
    if (!fs.existsSync(path.join(incoming, 'index.html'))) throw new Error('Missing default-branch index.');
    if (fs.existsSync(path.join(incoming, 'pull-requests'))) throw new Error('Default site contains PR snapshots.');
    for (const name of fs.readdirSync(published)) {
      if (!['.git', 'pull-requests'].includes(name)) {
        fs.rmSync(path.join(published, name), { recursive: true, force: true });
      }
    }
    fs.cpSync(incoming, published, { recursive: true });
  }
  fs.writeFileSync(path.join(published, '.nojekyll'), '');
}

function count(value) {
  if (value === undefined) return 0;
  if (!Number.isSafeInteger(value) || value < 0) throw new Error(`Invalid test count: ${value}`);
  return value;
}

function renderSummary(reports, publication, pagesUrl) {
  const base = new URL(pagesUrl);
  if (base.protocol !== 'https:') throw new Error('Expected an HTTPS Pages URL.');
  const prefix = `${base.href.replace(/\/$/, '')}/${previewPath(publication)}`;
  const lines = [
    COMMENT_MARKER, `<!-- allure-run:${publication.runId}:${publication.attempt} -->`,
    '### Allure report summary', '',
    `[Workflow run](${publication.runUrl}) · commit \`${publication.sha.slice(0, 7)}\``, '',
    '| Matrix member | Duration | Stats | New | Flaky | Retry | Report |',
    '| --- | --- | --- | --- | --- | --- | --- |',
  ];
  let missingHistory = false;
  for (const { scope, summary, hasHistory } of reports) {
    const href = `${prefix}/${scope.split('/').map(encodeURIComponent).join('/')}/allure/`;
    const stats = ['passed', 'failed', 'broken', 'skipped', 'unknown']
      .filter((status) => count(summary.stats[status]) > 0)
      .map((status) => `${count(summary.stats[status])} ${status}`).join('<br>') || 'No tests';
    const duration = Number(summary.duration);
    if (!Number.isFinite(duration) || duration < 0) throw new Error(`Invalid duration for ${scope}`);
    const formattedDuration = duration < 1000 ? `${Math.round(duration)}ms` : `${Math.round(duration / 1000)}s`;
    const flag = (name, query) => {
      const value = count(summary[name]?.length);
      return value ? `[${value}](${href}?${query})` : '0';
    };
    const baselineKnown = hasHistory || count(summary.stats.total) === 0;
    missingHistory ||= !baselineKnown;
    const newTests = baselineKnown ? flag('newTests', 'transition=new') : '—';
    lines.push(`| \`${scope}\` | ${formattedDuration} | ${stats} | ${newTests} | ${flag('flakyTests', 'flaky=true')} | ${flag('retryTests', 'retry=true')} | [Open report](${href}) |`);
  }
  lines.push('', `New tests are compared with the latest available history from \`${publication.baseBranch.replaceAll('`', '')}\`.`);
  if (missingHistory) lines.push('— means no baseline history is available for that member; its tests are not counted as new.');
  return `${lines.join('\n')}\n`;
}

async function postSummary({ github, context, core, publication, pagesUrl, directory = 'incoming' }) {
  const { data: pr } = await github.rest.pulls.get({ ...context.repo, pull_number: publication.prNumber });
  if (pr.state !== 'open' || pr.head.sha !== publication.sha) {
    core.info('The PR changed during publication; its summary will not be replaced.');
    return;
  }
  const comments = await github.paginate(github.rest.issues.listComments, {
    ...context.repo, issue_number: publication.prNumber, per_page: 100,
  });
  const existing = comments.find((comment) => comment.user.login === 'github-actions[bot]' &&
    comment.body?.includes(COMMENT_MARKER));
  const previous = existing?.body.match(/<!-- allure-run:(\d+):(\d+) -->/);
  if (previous && (Number(previous[1]) > publication.runId ||
      (Number(previous[1]) === publication.runId && Number(previous[2]) > publication.attempt))) {
    core.info('A newer run already owns the PR summary.');
    return;
  }
  const body = renderSummary(loadReports(directory), publication, pagesUrl);
  if (existing) {
    await github.rest.issues.updateComment({ ...context.repo, comment_id: existing.id, body });
  } else {
    await github.rest.issues.createComment({ ...context.repo, issue_number: publication.prNumber, body });
  }
}

module.exports = { selectPublication, loadReports, previewPath, assembleSite, renderSummary, postSummary };
if (require.main === module) assembleSite(JSON.parse(process.env.PUBLICATION));
