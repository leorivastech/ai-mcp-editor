/**
 * Cross-language determinism contract: the JS compiler port must produce
 * byte-identical output to the Python compiler for every golden fixture.
 * Run: node widget/test/golden.test.js
 */
"use strict";

const fs = require("fs");
const path = require("path");

const compiler = require("../src/compiler.js");

const goldenDir = path.join(__dirname, "..", "..", "core", "tests", "golden");
const cases = fs
  .readdirSync(goldenDir)
  .filter((f) => f.endsWith(".json"))
  .sort();

if (cases.length === 0) {
  console.error("No golden fixtures found — did core/tests/golden move?");
  process.exit(1);
}

let failures = 0;
for (const file of cases) {
  const preset = JSON.parse(fs.readFileSync(path.join(goldenDir, file), "utf8"));
  const expected = fs.readFileSync(
    path.join(goldenDir, file.replace(/\.json$/, ".txt")),
    "utf8"
  );
  const actual = compiler.compile(preset);
  if (actual === expected) {
    console.log(`  ok ${file}`);
  } else {
    failures++;
    console.error(`FAIL ${file}`);
    const a = actual.split("\n");
    const e = expected.split("\n");
    for (let i = 0; i < Math.max(a.length, e.length); i++) {
      if (a[i] !== e[i]) {
        console.error(`  line ${i + 1}:`);
        console.error(`    expected: ${JSON.stringify(e[i])}`);
        console.error(`    actual:   ${JSON.stringify(a[i])}`);
      }
    }
  }
}

if (failures) {
  console.error(`\n${failures} golden case(s) diverged — JS port != Python compiler`);
  process.exit(1);
}
console.log(`\nAll ${cases.length} golden cases match the Python compiler.`);
