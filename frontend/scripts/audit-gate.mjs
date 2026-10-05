#!/usr/bin/env node
// CI security gate: `npm audit` over all dependencies (dev included), failing on
// high/critical advisories like `npm audit --audit-level=high`, except for the
// narrowly scoped exceptions below. An exception covers one advisory, one
// package, and only the dependency paths listed; the same advisory reached any
// other way still fails.
//
// Usage (from frontend/): node scripts/audit-gate.mjs
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const FAIL_LEVELS = new Set(["high", "critical"]);

export const EXCEPTIONS = [];

const advisoryId = (url = "") => url.match(/GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}/i)?.[0] ?? url;

/** Every chain of package names from the root to `target`, following the lockfile (dev included). */
export function dependencyPaths(lock, target) {
  const packages = lock.packages ?? {};
  // Node resolution: the nearest node_modules/<name> walking up from the parent's location.
  const resolve = (from, name) => {
    let dir = from;
    for (;;) {
      const loc = (dir ? `${dir}/` : "") + `node_modules/${name}`;
      if (packages[loc]) return loc;
      if (!dir) return null;
      const i = dir.lastIndexOf("/node_modules/");
      dir = i >= 0 ? dir.slice(0, i) : "";
    }
  };
  const deps = (loc) => {
    const p = packages[loc] ?? {};
    return Object.keys({ ...p.dependencies, ...p.optionalDependencies, ...(loc === "" ? p.devDependencies : {}) });
  };
  const paths = [];
  const walk = (loc, chain, seen) => {
    for (const name of deps(loc)) {
      const child = resolve(loc, name);
      if (!child || seen.has(child)) continue;
      const next = [...chain, name];
      if (name === target) paths.push(next);
      else walk(child, next, new Set(seen).add(child));
    }
  };
  walk("", [], new Set([""]));
  return paths;
}

/**
 * Decide the gate from `npm audit --json` output and the lockfile.
 * Returns { failures, allowed } (lists of human-readable lines).
 */
export function evaluateAudit(audit, lock, exceptions = EXCEPTIONS) {
  const advisories = new Map();
  for (const vuln of Object.values(audit.vulnerabilities ?? {})) {
    for (const via of vuln.via ?? []) {
      if (typeof via === "object") advisories.set(`${advisoryId(via.url)}|${via.name}`, via);
    }
  }
  const failures = [], allowed = [];
  for (const adv of advisories.values()) {
    if (!FAIL_LEVELS.has(adv.severity)) continue;
    const id = advisoryId(adv.url);
    const label = `${id} ${adv.severity} ${adv.name}: ${adv.title}`;
    const exception = exceptions.find((e) => e.id === id && e.package === adv.name);
    if (!exception) { failures.push(label); continue; }
    const paths = dependencyPaths(lock, adv.name).map((p) => p.join(">"));
    const stray = paths.filter((p) => !exception.paths.includes(p));
    if (paths.length === 0 || stray.length) failures.push(`${label} (reached outside the excepted paths: ${stray.join(", ") || "no path found"})`);
    else allowed.push(`${label} via ${paths.join(", ")}`);
  }
  return { failures, allowed };
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  let raw;
  try {
    raw = execFileSync("npm", ["audit", "--json"], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  } catch (err) {
    raw = err.stdout; // npm audit exits non-zero when it finds anything
  }
  const { failures, allowed } = evaluateAudit(JSON.parse(raw), JSON.parse(readFileSync("package-lock.json", "utf8")));
  for (const line of allowed) console.log(`allowed (exception): ${line}`);
  const today = new Date().toISOString().slice(0, 10);
  for (const e of EXCEPTIONS) if (today >= e.review) console.log(`::warning::exception ${e.id} is past its review date ${e.review}`);
  if (failures.length) {
    for (const line of failures) console.log(`::error::${line}`);
    console.log(`${failures.length} high/critical advisor${failures.length === 1 ? "y" : "ies"} not covered by an exception`);
    process.exit(1);
  }
  console.log("audit gate: no high/critical advisories outside the listed exceptions");
}
