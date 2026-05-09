#!/usr/bin/env node
// phdtake — thin installer CLI for phdtaketaketake.
//
// All real logic lives in ../lib/installer.js. This shim exists to be
// the stable bin entry registered in package.json; tests import the
// library directly without going through this entry.

import { run } from '../lib/installer.js';

run(process.argv.slice(2)).then(
  (code) => process.exit(code),
  (err) => {
    console.error(err && err.stack ? err.stack : String(err));
    process.exit(1);
  },
);
