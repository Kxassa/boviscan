import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const dir = dirname(fileURLToPath(import.meta.url));
const pt = JSON.parse(readFileSync(join(dir, "locales/pt-BR.json"), "utf8"));

test("pt-BR is the ship catalog and has core keys", () => {
  assert.equal(pt["app.title"], "BoviScan");
  assert.ok(pt["live.disclaimer"]);
  assert.ok(pt["lang.note"].includes("português") || pt["lang.note"].includes("Brasil"));
});
