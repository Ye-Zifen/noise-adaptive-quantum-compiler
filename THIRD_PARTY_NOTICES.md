# Third-Party Notices

This release package depends on third-party open-source Python packages declared in `pyproject.toml`.

Direct runtime dependencies:

| Package | Purpose | License |
|---|---|---|
| Cirq | Circuit representation, routing, and simulation utilities | Apache-2.0 |
| NetworkX | Coupling graph and path utilities | BSD-3-Clause |
| NumPy | Numeric arrays and probability handling | BSD-3-Clause |
| Pydantic | JSON schema-style validation models | MIT |
| Stim | Clifford circuit sampling for Track B | Apache-2.0 |
| stimcirq | Cirq/Stim interoperability | Apache-2.0 |

Development/test dependency:

| Package | Purpose | License |
|---|---|---|
| pytest | Local regression tests | MIT |

Before redistributing a modified package, regenerate dependency notices from the exact lockfile or environment used for that release, including transitive dependencies if they are bundled.
