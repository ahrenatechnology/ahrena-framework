---
id: layer-map
type: rule
clade: engineering
subclade: architecture
title: The declared layer map
statement: A project declares a layer map at .ahrena/layer-map.json that assigns every source folder to one layer; a folder the map leaves out is a finding.
enforcement: judgment
---

# The declared layer map

One condition. Every rule that asks which side of a boundary a module sits on, such as a domain that imports no mechanism, needs a partition of the source tree into layers. [`domain-model.md`](domain-model.md) supplies a default by folder name; this rule is the file a project writes when its layout is not that default, and the file the detectors that will ship read. The rule names the shape and the location of the file; the content is the project's.

## Conditions

1. **STR-4. The project has a layer map and it covers every folder under its source root.** The map is the JSON file `.ahrena/layer-map.json` at the repository root. It holds a `sourceRoot` string and a `layers` array; each entry has a `path` (a folder, relative to the repository root, without a glob) and a `layer`, one of `domain`, `use-case`, `edge` or `composition-root`. `edge` is any folder that talks to something outside the process: an API, a database, a queue, an integration. The state that is a finding is one of: the file is absent, a folder under `sourceRoot` that no entry's `path` contains, or two entries with different layers at the same path. Where entries nest, the deepest entry decides a folder's layer, so `src/orders` as `domain` and `src/orders/db` as `edge` is valid. Threshold: 0 uncovered folders. Detector: a script that lists the folders and checks them against the entries; the TypeScript detector is owned by the structure detectors issue #330, and until it ships the rule is read by a reviewer. A threshold of 0 is a definition, not a measurement.

## Where this stops

**It does not say which layers may depend on which.** The map is a partition and nothing more. The direction of dependency is stated by [`solid.md`](solid.md) condition 6 and by [`domain-model.md`](domain-model.md) condition 1, and a detector composes them with this file.

**It does not judge whether a folder is in the right layer.** A folder named `domain` that holds database code is mapped as `domain` and the rule is satisfied; the import conditions are what catch the mismatch.

**A project with only the default folder names still writes the file.** The convention in `domain-model.md` is the fallback for a reviewer reading a tree by eye, not a way to skip the file for a detector; a map that is inferred is a map that drifts unseen.

**Generated folders and fixtures may be left out in writing.** A path listed under an optional `ignored` array in the same file is not uncovered; the entry is the written reason, and it is itself reviewed.

**This rule declares judgment because no detector ships yet.** A rule that declared a hook before the script existed would fail the foundation gate; it moves to `hook` in the change that lands the detector.
