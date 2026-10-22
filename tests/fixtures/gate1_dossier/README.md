# Synthetic Gate 1 dossier fixtures

Every JSON file here is authored fiction. No device, AP, firmware, driver or
vendor evidence was acquired. Source locators point into `source.json` and its
SHA-256 pins the synthetic bytes, not their truth. These files never qualify a
capture path or authorize an experiment.

| File | Expected validator result |
|---|---|
| `complete-synthetic.json` | Exit 0, `synthetic_consistency_only`; actual budget terms remain unknown and all qualification/authorization flags remain false |
| `incomplete-synthetic.json` | Exit 2; missing firmware, unknown Q05 pairing contract and call timeout; G1 measurements remain unknown |
| `adversarial-synthetic.json` | Exit 2; observation arrives after immediate cutoff and two host timeouts remain unresolved operations |
| `source.json` | Hash-pinned synthetic assertions and records, not a standalone dossier |
| `policy.json` | Hash-pinned synthetic policy description, not an executable collector or a qualified timing policy |

The three collector artifact references deliberately share the fictional source
file. They exercise reference binding only; no collector source/build/configuration
or hardware qualification is supplied. Every pinned source uses LF newlines so
Git normalization cannot change its SHA-256 between Windows and Linux checkouts.

See the [contract and runnable commands](../../../docs/clock-models/gate1-reopening/machine-readable-dossier.md).
Do not turn these examples into retained evidence by changing their labels.
