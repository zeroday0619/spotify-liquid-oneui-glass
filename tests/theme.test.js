import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFile, readdir } from 'node:fs/promises';
import { installLightModeLock } from '../theme/light-mode.js';

const theme = new URL('../theme/', import.meta.url);

test('light mode recovers after a native theme change and stops observing on disposal', () => {
  const originalObserver = globalThis.MutationObserver;
  let callback;
  let disconnected = false;
  let writes = 0;
  globalThis.MutationObserver = class {
    constructor(fn) { callback = fn; }
    observe(root, options) {
      assert.deepEqual(options.attributeFilter, ['class', 'data-lg-mode']);
    }
    disconnect() { disconnected = true; }
  };
  try {
    const classes = new Set(['encore-dark-theme', 'unrelated-class']);
    const root = {
      dataset: { lgMode: 'dark' },
      classList: {
        contains: value => classes.has(value),
        add: value => { classes.add(value); writes++; },
        remove: value => { classes.delete(value); writes++; },
      },
    };
    const dispose = installLightModeLock(root);
    assert.equal(root.dataset.lgMode, 'light');
    assert(classes.has('encore-light-theme'));
    assert(!classes.has('encore-dark-theme'));
    classes.delete('encore-light-theme');
    classes.add('encore-dark-theme');
    root.dataset.lgMode = 'dark';
    callback();
    assert.equal(root.dataset.lgMode, 'light');
    assert(classes.has('encore-light-theme'));
    assert(!classes.has('encore-dark-theme'));
    assert(classes.has('unrelated-class'));
    const settledWrites = writes;
    callback();
    assert.equal(writes, settledWrites);
    dispose();
    assert(disconnected);
  } finally {
    globalThis.MutationObserver = originalObserver;
  }
});

test('module entry points and referenced local styles are included in the distribution', async () => {
  const files = new Set(await readdir(theme));
  const metadata = JSON.parse(await readFile(new URL('metadata.json', theme), 'utf8'));
  assert.equal(metadata.name, 'liquid-glass-local');
  for (const entry of Object.values(metadata.entries)) assert(files.has(entry), entry);
  for (const name of files) {
    if (!/\.(js|css)$/.test(name)) continue;
    const source = await readFile(new URL(name, theme), 'utf8');
    assert(!source.includes('/Users/'), `${name} contains a machine-specific path`);
    for (const match of source.matchAll(/["'](?:\/modules\/liquid-glass-local\/|\.\/)?([a-z][a-z0-9-]*\.(?:css|js))["']/g)) {
      assert(files.has(match[1]), `${name} references missing ${match[1]}`);
    }
  }
});
