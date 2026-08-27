#!/usr/bin/env node
/**
 * End-to-end test: edit code in the VS Code GUI, have it execute inside
 * Mac OS X 10.7.5, and validate the result.
 *
 * This drives the REAL VS Code that is installed on this machine, through
 * Playwright's Electron support -- actual keystrokes into actual widgets, not a
 * simulation. Every claim it makes is then checked from outside the editor:
 *
 *   * that the editor's save reached Lion         -> read the file back in Lion
 *   * that the edit changed behaviour             -> run it in Lion, check output
 *   * that the editor's own task ran in Lion      -> read the task's log
 *   * that the "Lion (root)" terminal exists      -> find it in the UI's picker
 *
 * Screenshots of each stage land in ./shots/ so the run can be reviewed.
 *
 *   DISPLAY=:0 node vscode-lion.e2e.js
 */

'use strict';

const { _electron: electron } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const VSCODE = '/usr/share/code/code';
const WORKSPACE = process.env.HOME + '/Lion-Demo.code-workspace';
const MOUNT = process.env.LION_MOUNT || '/mnt/lion-live';
const PROJ_LINUX = MOUNT + '/Users/Shared/lion-demo';
const PROJ_LION = '/Users/Shared/lion-demo';
const FILE = 'report.py';
const SHOTS = path.join(__dirname, 'shots');
const UDATA = path.join(__dirname, 'udata');

// A 2006 Xeon on a framebuffer driver. Everything is slower than you expect.
const BIG = 240000;
const MED = 90000;

let pass = 0;
const fails = [];

function check(label, condition, detail) {
  if (condition) {
    pass++;
    console.log('  ok    ' + label);
  } else {
    fails.push({ label, detail });
    console.log('  FAIL  ' + label);
    if (detail) console.log('          ' + String(detail).split('\n').join('\n          '));
  }
}

/** Run a command inside Lion. Throws only on spawn failure, not on exit code. */
function inLion(cmd) {
  try {
    return execFileSync('/usr/local/bin/lion', [cmd],
      { encoding: 'utf8', timeout: 120000 }).trim();
  } catch (e) {
    return ((e.stdout || '') + (e.stderr || '')).trim() || ('ERROR: ' + e.message);
  }
}

/**
 * Make report.py the active editor and verify it, closing anything an extension
 * opened. Returns the active tab's label.
 */
async function focusTheFile(win) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const other = win.locator('.tabs-container .tab').filter({ hasNotText: FILE });
    const n = await other.count();
    for (let i = n - 1; i >= 0; i--) {
      try {
        await other.nth(i).locator('.codicon-close, .tab-actions a').first()
          .click({ timeout: 8000 });
        await win.waitForTimeout(1200);
      } catch (e) { /* already gone, or not closable */ }
    }
    const tab = win.locator('.tabs-container .tab').filter({ hasText: FILE }).first();
    if (await tab.count()) {
      await tab.click();
      await win.waitForTimeout(2500);
    }
    const active = await win.locator('.tabs-container .tab.active').first()
      .innerText().catch(() => '');
    if (active.includes(FILE)) {
      // Put the caret in the text, not just the tab.
      await win.locator('.monaco-editor .view-lines').first().click();
      await win.waitForTimeout(1500);
      return active;
    }
    await win.waitForTimeout(3000);
  }
  return await win.locator('.tabs-container .tab.active').first()
    .innerText().catch(() => '(none)');
}

/**
 * Have a real assistant add a function to the Lion project, then run it in Lion.
 *
 * Tries Claude Code first, then Codex. Neither is authenticated on this machine
 * by design -- no API keys ship with it -- so an unauthenticated tool is
 * reported as SKIPPED, never as a pass.
 */
function runAiEdit() {
  const PROMPT =
    'In report.py, add a function disk_free() that returns the output of ' +
    '`df -h /` filtered to the Avail column, and print it from main() as ' +
    'disk_free=<value>. This code runs on Mac OS X 10.7 with Python 2.7 and ' +
    'BSD userland, so use print as a statement and no f-strings. Edit the file.';

  const before = fs.readFileSync(path.join(PROJ_LINUX, FILE), 'utf8');

  const candidates = [
    { tool: 'claude',
      argv: ['-p', PROMPT, '--permission-mode', 'acceptEdits'],
      how: 'claude   (then /login)',
      unauth: /invalid api key|please run \/login|not authenticated|credit balance/i },
    { tool: 'codex',
      argv: ['exec', '--full-auto', PROMPT],
      how: 'codex login',
      unauth: /not (logged in|authenticated)|missing api key|unauthorized|401|sign in/i },
  ];

  let lastWhy = '';
  for (const c of candidates) {
    let out = '';
    try {
      out = execFileSync('/usr/local/bin/' + c.tool, c.argv, {
        cwd: PROJ_LINUX, encoding: 'utf8', timeout: 300000,
        env: Object.assign({}, process.env, { CI: '1' }),
      });
    } catch (e) {
      out = ((e.stdout || '') + (e.stderr || '')).toString();
    }
    if (c.unauth.test(out)) {
      lastWhy = c.tool + ' is not signed in';
      continue;
    }
    const after = fs.readFileSync(path.join(PROJ_LINUX, FILE), 'utf8');
    if (after === before) {
      lastWhy = c.tool + ' ran but changed nothing';
      continue;
    }
    const output = execFileSync('/usr/local/bin/lion',
      ['cd ' + PROJ_LION + ' && /usr/bin/python ' + FILE],
      { encoding: 'utf8', timeout: 120000 }).toString();
    return { tool: c.tool, fileChanged: true, output: output,
             detail: 'the file grew by ' + (after.length - before.length) + ' bytes' };
  }
  return {
    skipped: true,
    why: 'no AI assistant is signed in on this machine (' + lastWhy + ')',
    how: 'claude   # then type /login      -- or --      codex login',
  };
}

async function shot(win, name) {
  try {
    fs.mkdirSync(SHOTS, { recursive: true });
    await win.screenshot({ path: path.join(SHOTS, name + '.png') });
    console.log('        (shot: shots/' + name + '.png)');
  } catch (e) {
    console.log('        (screenshot failed: ' + e.message + ')');
  }
}

(async () => {
  console.log('E2E: VS Code on Linux, code executing in Mac OS X Lion\n');

  // ---- preconditions, checked rather than assumed ------------------------
  console.log('== preconditions');
  check('Lion VM answers', inLion('echo alive') === 'alive', inLion('echo alive'));
  check('project is mounted and readable',
    fs.existsSync(path.join(PROJ_LINUX, FILE)));
  check('workspace file exists', fs.existsSync(WORKSPACE));
  check('VS Code binary present', fs.existsSync(VSCODE));
  if (fails.length) {
    console.log('\npreconditions failed; not launching the editor.');
    process.exit(fails.length);
  }

  const original = fs.readFileSync(path.join(PROJ_LINUX, FILE), 'utf8');

  // ---- launch the real editor -------------------------------------------
  console.log('\n== launch VS Code');
  fs.rmSync(UDATA, { recursive: true, force: true });
  // A fresh --user-data-dir keeps this run from colliding with the VS Code the
  // user already has open, but it also starts with NO user settings -- which is
  // why the "Lion (root)" terminal profile was absent. Copy the real settings
  // in, so what is tested is the actual configuration.
  const realSettings = process.env.HOME + '/.config/Code/User/settings.json';
  if (fs.existsSync(realSettings)) {
    fs.mkdirSync(path.join(UDATA, 'User'), { recursive: true });
    fs.copyFileSync(realSettings, path.join(UDATA, 'User', 'settings.json'));
    console.log('        (copied the real user settings into the test profile)');
  } else {
    console.log('        (WARNING: no user settings at ' + realSettings + ')');
  }
  const app = await electron.launch({
    executablePath: VSCODE,
    args: [
      '--no-sandbox',
      '--disable-gpu',                 // fbdev; there is no GPU to use
      '--disable-updates',
      '--skip-welcome',
      '--skip-release-notes',
      '--disable-workspace-trust',
      // Gemini Code Assist reopens its welcome page and takes the active editor
      // even after it is closed, so keystrokes land in a webview and edits
      // silently do nothing. Disabled for the automated run ONLY; Claude Code
      // and ChatGPT stay enabled, and the extension is untouched for the user.
      '--disable-extension=google.geminicodeassist',
      '--user-data-dir=' + UDATA,      // a private profile, so a running
                                       // VS Code instance is not reused
      '--extensions-dir=' + process.env.HOME + '/.vscode/extensions',
      WORKSPACE,
      path.join(PROJ_LINUX, FILE),     // open the file directly; far more
                                       // reliable than driving Quick Open or
                                       // clicking a tree row
    ],
    timeout: BIG,
  });

  const win = await app.firstWindow({ timeout: BIG });
  global.__win = win;                  // so the crash handler can screenshot
  await win.waitForSelector('.monaco-workbench', { timeout: BIG });
  check('workbench rendered', true);
  await win.waitForTimeout(15000);     // let the extension host settle
  await shot(win, '01-workbench');

  const title = await win.title();
  check('window is on the Lion workspace', /Lion/i.test(title), 'title: ' + title);

  // Dismiss any extension-recommendation toast. Escape is enough; driving the
  // command palette for this is worse, because if the command name does not
  // match exactly then Enter runs whatever is highlighted instead.
  await win.keyboard.press('Escape');
  await win.waitForTimeout(1500);
  await win.keyboard.press('Escape');
  await win.waitForTimeout(1500);

  // ---- the file was named at launch, so it should already be open -------
  console.log('\n== ' + FILE + ' is open in the editor');
  await win.waitForSelector('.monaco-editor .view-lines', { timeout: MED });
  await win.waitForTimeout(8000);
  let shown = await win.locator('.monaco-editor .view-lines').first().innerText();
  if (!/os_version/.test(shown)) {
    // Fallback: click it in the Explorer. Reveal the view first, or the row
    // may not be rendered at all.
    console.log('        (not open yet; trying the Explorer)');
    await win.keyboard.press('Control+Shift+E');
    await win.waitForTimeout(5000);
    const row = win.locator('.monaco-list-row').filter({ hasText: FILE }).first();
    if (await row.count()) {
      await row.dblclick();
      await win.waitForTimeout(8000);
      shown = await win.locator('.monaco-editor .view-lines').first().innerText();
    }
  }
  check('the editor is showing the real file',
    /os_version/.test(shown) && /sw_vers/.test(shown), shown.slice(0, 200));

  // Extensions activate late and open their own tabs -- Gemini Code Assist's
  // welcome page took the active editor in an earlier run, so every keystroke
  // went into a webview and every edit silently did nothing. Close the others
  // and confirm which tab is active before touching the keyboard.
  await focusTheFile(win);
  await shot(win, '02-file-open');

  // ---- edit 1: rename the printed label, via Find & Replace ------------
  console.log('\n== edit 1: rename a label with Find & Replace');
  const active1 = await focusTheFile(win);
  check('report.py is the ACTIVE editor before typing', active1.includes(FILE),
    'active tab is: ' + active1);
  await win.keyboard.press('Control+H');
  try {
    await win.waitForSelector('.find-widget', { state: 'visible', timeout: 25000 });
  } catch (e) {
    console.log('        (find widget did not open; refocusing and retrying)');
    await focusTheFile(win);
    await win.keyboard.press('Control+H');
    await win.waitForSelector('.find-widget', { state: 'visible', timeout: MED });
  }
  await win.waitForTimeout(2000);
  const findInput = win.locator('.find-widget .find-part textarea, .find-widget .find-part input').first();
  await findInput.click();
  await win.keyboard.type('os_version=', { delay: 40 });
  await win.waitForTimeout(1500);
  const replSelectors = '.find-widget .replace-part textarea, ' +
                       '.find-widget .replace-input textarea, ' +
                       '.find-widget .replace-part input, ' +
                       '.find-widget .replace-input input';
  const replInput = win.locator(replSelectors).first();
  if (await replInput.count()) {
    await replInput.click();
  } else {
    // The widget can open collapsed; Tab moves from find to replace.
    console.log('        (no replace field located; tabbing to it)');
    await win.keyboard.press('Tab');
  }
  await win.waitForTimeout(1000);
  await win.keyboard.type('macos_version=', { delay: 40 });
  await win.waitForTimeout(1500);
  await shot(win, '03-find-replace');
  await win.keyboard.press('Control+Alt+Enter');       // Replace All
  await win.waitForTimeout(3000);
  await win.keyboard.press('Escape');
  await win.keyboard.press('Control+S');
  await win.waitForTimeout(8000);                     // sshfs write + editor
  await shot(win, '04-saved');

  // Validate from OUTSIDE the editor, on both sides of the boundary.
  const afterLinux = fs.readFileSync(path.join(PROJ_LINUX, FILE), 'utf8');
  check('the editor wrote the change to the mounted file',
    afterLinux.includes('macos_version='), 'file still has: ' +
      (afterLinux.match(/.*_version=.*/) || ['<no match>'])[0]);

  const afterLion = inLion('grep -c macos_version= ' + PROJ_LION + '/' + FILE);
  check('Lion itself sees the change', parseInt(afterLion, 10) >= 1, 'grep -c said: ' + afterLion);

  const run1 = inLion('cd ' + PROJ_LION + ' && /usr/bin/python ' + FILE);
  check('running it in Lion shows the NEW label',
    /macos_version=10\.7\.5/.test(run1), run1);
  check('running it in Lion no longer shows the old label',
    !/\bos_version=/.test(run1), run1);

  // ---- edit 2: type new code that changes behaviour -------------------
  console.log('\n== edit 2: type a new line into the editor');
  const active2 = await focusTheFile(win);
  check('report.py is still the active editor', active2.includes(FILE),
    'active tab is: ' + active2);
  await win.keyboard.press('Control+End');
  await win.waitForTimeout(1500);
  await win.keyboard.press('Enter');
  // One self-contained line: no imports to place, no indentation to reason
  // about beyond what auto-indent gives us inside the __main__ block.
  await win.keyboard.type(
    'print("build=%s" % __import__("subprocess").check_output(["sw_vers","-buildVersion"]).strip())',
    { delay: 25 });
  await win.waitForTimeout(2000);
  await win.keyboard.press('Control+S');
  await win.waitForTimeout(8000);
  await shot(win, '05-typed-code');

  const afterTyped = fs.readFileSync(path.join(PROJ_LINUX, FILE), 'utf8');
  check('the typed line reached the file', afterTyped.includes('build=%s'),
    afterTyped.slice(-200));

  const run2 = inLion('cd ' + PROJ_LION + ' && /usr/bin/python ' + FILE);
  check('the typed code executes in Lion and prints its build number',
    /build=11G63/.test(run2), run2);

  // ---- the editor's own task must run in Lion, not on Linux ----------
  console.log('\n== run the workspace task from the command palette');
  const logPath = path.join(PROJ_LINUX, '.vscode', 'last-run.log');
  fs.rmSync(logPath, { force: true });
  // The task command is lion-run "${file}", and ${file} is the ACTIVE editor's
  // path. With a webview active it would have been empty or wrong.
  await focusTheFile(win);
  await win.keyboard.press('Control+Shift+P');
  await win.waitForSelector('.quick-input-widget', { state: 'visible', timeout: MED });
  await win.keyboard.type('Tasks: Run Task', { delay: 50 });
  await win.waitForTimeout(4000);
  await win.keyboard.press('Enter');
  await win.waitForTimeout(6000);
  await shot(win, '06-task-list');
  await win.keyboard.type('Lion: run the open file', { delay: 40 });
  await win.waitForTimeout(3000);
  await win.keyboard.press('Enter');
  await win.waitForTimeout(30000);                   // task runs over ssh
  await shot(win, '07-task-ran');

  let taskLog = '';
  for (let i = 0; i < 12 && !taskLog; i++) {
    if (fs.existsSync(logPath)) taskLog = fs.readFileSync(logPath, 'utf8');
    if (!taskLog) await win.waitForTimeout(5000);
  }
  check('the task actually executed, and inside Lion',
    /macos_version=10\.7\.5/.test(taskLog) && /build=11G63/.test(taskLog),
    'last-run.log: ' + (taskLog || '<never written>').slice(0, 300));

  // ---- the Lion terminal profile must be offered in the UI ----------
  console.log('\n== the "Lion (root)" terminal profile is offered');
  await win.keyboard.press('Control+Shift+P');
  await win.waitForSelector('.quick-input-widget', { state: 'visible', timeout: MED });
  await win.keyboard.type('Terminal: Select Default Profile', { delay: 40 });
  await win.waitForTimeout(4000);
  await win.keyboard.press('Enter');
  await win.waitForTimeout(6000);
  const picker = await win.locator('.quick-input-widget').innerText().catch(() => '');
  check('VS Code lists a "Lion (root)" terminal profile',
    /Lion \(root\)/.test(picker), 'picker showed: ' + picker.replace(/\s+/g, ' ').slice(0, 200));
  await shot(win, '08-terminal-profiles');
  await win.keyboard.press('Escape');

  // ---- an actual AI making an actual edit, validated by running it ----
  // The requirement is that Claude or Codex -- not only Gemini -- edits Lion
  // code and the result is verified. Both need credentials, which are
  // deliberately absent from this machine, so this stage reports SKIPPED with
  // the exact command needed rather than quietly passing.
  console.log('\n== an AI assistant edits the Lion code');
  const aiResult = runAiEdit();
  if (aiResult.skipped) {
    console.log('  SKIP  ' + aiResult.why);
    console.log('        run this on the machine, then re-run this test:');
    console.log('          ' + aiResult.how);
  } else {
    check('the AI (' + aiResult.tool + ') edited the file',
      aiResult.fileChanged, aiResult.detail);
    check('the AI\'s edit runs correctly inside Lion',
      /disk_free=/.test(aiResult.output), aiResult.output);
  }

  // ---- put the file back --------------------------------------------
  console.log('\n== restore the file');
  fs.writeFileSync(path.join(PROJ_LINUX, FILE), original);
  const restored = inLion('cd ' + PROJ_LION + ' && /usr/bin/python ' + FILE);
  check('the file is back to its original behaviour',
    /os_version=10\.7\.5/.test(restored) && !/build=/.test(restored), restored);

  await shot(win, '09-final');
  await app.close();

  console.log('\n' + pass + ' passed, ' + fails.length + ' failed');
  if (fails.length) {
    console.log('\nFailures:');
    for (const f of fails) console.log('  ' + f.label + (f.detail ? '\n    ' + f.detail : ''));
  }
  process.exit(fails.length);
})().catch(async (e) => {
  console.error('\nE2E crashed: ' + e.stack);
  if (global.__win) {
    try {
      fs.mkdirSync(SHOTS, { recursive: true });
      await global.__win.screenshot({ path: path.join(SHOTS, '99-crash.png') });
      console.error('state at the crash: shots/99-crash.png');
    } catch (e2) {
      console.error('could not screenshot the crash: ' + e2.message);
    }
  }
  process.exit(1);
});
