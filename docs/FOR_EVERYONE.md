# DUP Protocol in plain language

**For:** a first-time reader, a recruiter, or anyone who is not a fund officer or an auditor.  
**Not:** a diligence pack and not an audit report.  
**Author:** Uladzimir Dabranski (D.U.P.) · DUP Labs · DUP Protocol.  
**Code:** [github.com/Gruver87/dup-protocol](https://github.com/Gruver87/dup-protocol)  
**Русский:** [FOR_EVERYONE_RU.md](FOR_EVERYONE_RU.md)

---

## One paragraph

This repository is a program that runs a small private network of nodes and keeps one shared ledger. Python orchestrates the node. Rust does the hot path: cryptography, storage, and execution. You can start it on your own machine and open a local explorer. It is not an exchange, not a “buy the coin” app, and not a public network that strangers already use.

The folder used to be called Absolute Blockchain Ultimate Hybrid. The GitHub name is `dup-protocol`.

## Fair to say

- The author built a hybrid blockchain node: Python on the outside, Rust on the inside.
- GitHub runs automated tests. A three-node local network exists.
- Amounts are integers (satoshi), not floating-point money.
- The bridge to other networks is off.
- The license is MIT. The code can be read. Authorship stays with the author.

## Not fair to say

- “The coin is listed” or “this is a public mainnet.” It is not.
- “A security firm has finished an audit.” It has not. The external checklist is 6 of 8. A pen-test and a third-party PDF are still open.
- “The two GitHub repos are the same proof.” They are not. The experimental repo is a sandbox. Its green runs are not proof for this repo.
- “The Belarus trademark is registered.” Only a filing checklist exists.

## Two repositories

| | This repo | The other repo |
|---|---|---|
| URL | [dup-protocol](https://github.com/Gruver87/dup-protocol) | [dup-protocol-experimental](https://github.com/Gruver87/dup-protocol-experimental) |
| Role | The line shown to an auditor | A sandbox where ideas are tried first |
| How to read it | Proof lives here | Do not copy green checks from there into this repo |

## What a running node shows

| Address | What it is |
|---|---|
| http://localhost:8080 | A normal browser page. The explorer. |
| http://localhost:8545 | Not a page. Programs post requests here. A browser shows an error. The prod profile also requires a key. |
| ws://localhost:8766 | A program channel, not a browser tab. |

A solo node on port 8080 is not the three-node public-style mesh. That mesh is a separate Docker bring-up.

## Shape of the system

1. Outside: the explorer, ordinary HTTP, and a program channel.
2. Python decides which piece of work goes where.
3. Rust does cryptography, state roots, and storage.
4. Nodes talk to each other. The working-tip mesh uses rust-libp2p. The frozen tag `v1.3.1339-tip-v2-industrial` is the older TCP+TLS picture.
5. Bridge, Ethereum-style NFT market, oracles, and sharding stay off on the prod profile. Lab code exists. The prod switches stay off.

Long-Range (a defense against a very old history swap) is lab code. The prod switch is off. BLS is not implemented.

## What has actually been checked

- GitHub tests and image build.
- A local Max self-check: one node on this computer plus a short isolated peer check. That is not a day-long network run.
- A long mesh run on 15–17 October 2026 (about 48 hours, no hard failures) is packed at `docs/evidence/runs/pin-libp2p-strict-48h`. That proves that build stayed up. It does not launch a public network. Git was dirty when that run started. No new release tag was cut for it.

## Recruiter: ten-minute read

1. [README](../README.md). Green badges mean tests passed, not “the network is open to the world.”
2. This file, for the boundaries.
3. [LICENSE](../LICENSE) (MIT) and [CITATION.cff](../CITATION.cff).
4. `consensus`, `network`, `crypto`, `storage`, `native/abs_native` are the core. `api` is the outside door. `docs/adr` is optional “why we chose this.”
5. `tests/` and `.github/workflows` are how the project checks itself.

Fair on a CV: “hybrid Python + Rust L1 node, private mesh, evidence packs in the repo, external audit not finished.”  
Not fair: “launched mainnet,” “passed an audit,” “listed a coin.”

Next, if you need depth: [FAQ](FAQ.md), [ONE_PAGER](ONE_PAGER.md), [EVIDENCE_MATRIX](EVIDENCE_MATRIX.md).
