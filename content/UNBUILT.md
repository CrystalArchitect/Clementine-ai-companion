# Unbuilt

*A register of what is described, promised, or implied here but does not
exist. Opened 10 August 2026.*

`ARCHITECTURE.md` opens by saying it is "a design overview, not a description
of currently deployed software." That sentence is honest, and it is also the
only place the distance between the design and the build is acknowledged.
Nowhere does the repository say *which* parts are the unbuilt ones.

This file is that list. It exists because the same rule that governs the maps
governs the product: a dreamed line may be drawn, but it may not be drawn in
the same ink as a surveyed one. A gap nobody has written down is a gap that
gets described as a feature by accident.

Entries are removed when the thing is built, not when it is planned.

---

## 1. The interface a person opens reaches almost none of the companion

**Status: unbuilt. Measured 10 August 2026 against `master`.**

The server declares **17 routes**. Setting aside the three that describe the
service rather than provide it (`/api`, `/api/openapi.json`, and the static
asset handler), **14 are functional. The webapp calls 4.**

| Reachable from the interface | Reachable only over HTTP |
|---|---|
| `POST /api/chat/stream` | `GET /api/memories` |
| `GET /api/status` | `POST /api/teach` |
| `GET /api/health` | `POST /api/forget` |
| `GET /api/audit` *(count and intactness only)* | `POST /api/reflect` |
| | `GET /api/export` |
| | `POST /api/import` |
| | `GET /api/profile` |
| | `POST /api/profile` |
| | `POST /api/profile/meta` |
| | `POST /api/profile/delete` |

### Why this is not a missing settings panel

That is how it was first described, including by the person writing this
note, and the description was wrong. Counting the routes changed the finding.

What is unreachable is not preference and decoration. It is most of what the
word *sovereign* is doing in this project:

- **A person cannot see what the companion remembers about them.**
  `/api/memories` has no interface. The memory is on their own disk, in their
  own file, and the program they open will not show it to them.
- **A person cannot delete a memory.** `/api/forget` has no interface. The
  right to be forgotten by your own companion is currently exercised through
  a terminal or a `curl` command.
- **A person cannot take their memory with them.** `/api/export` and
  `/api/import` have no interface. Portability that requires a developer is
  not portability; it is a promise with an audience test attached.
- **A person cannot read the consent log.** The interface calls
  `/api/audit?limit=1` and reports two things: how many entries exist and
  whether the hash chain verifies. So it says *"nothing has been tampered
  with"* while showing none of what it is vouching for. That is the weakest
  form of the claim — trust restored by assertion, which is the thing the log
  was built to replace.
- **Neither party can set pronouns.** The law names two who may decide, the
  human and the companion. `/api/profile/meta` now serves both (August 2026),
  and no interface calls it.

Name, avatar, description and model are also unreachable. Those genuinely are
settings, and they are the least of it.

### The shape of the problem

The API is not the gap. Every capability above exists, is described in
`api_surface.py`, is checked against Flask's route table in both directions,
and is covered by tests. Someone building this surface should need to invent
no new endpoints, and should be suspicious of any urge to.

The gap is that the audit of *reachability* was never run. Each endpoint was
built and tested; nothing asked whether a person who does not use a terminal
could get to it. Tests answer "does this work when called." Nothing answered
"can anyone call it."

### Not decided here

Whether this should be built, and in what order. This note records the gap
and its size; it does not argue for a solution, and the sequencing is a
product decision rather than a technical one.

One observation for whoever takes it: the memory and consent items
(`memories`, `forget`, `export`, `audit`) are a different class from the
profile items. The first group is the project's central claim made operable.
The second group is a preferences screen.

---

## 2. `ARCHITECTURE.md` is largely design, and does not say which parts

**Status: acknowledged, unenumerated.**

The document declares its own status in its opening line, which is more than
most such documents do. But a reader cannot tell from it which described
components run today and which are intended. `SOVEREIGNTY.md` was filed
partly to have one document whose claims are all currently true; the
complement — marking the design document's unbuilt sections — has not been
done.

This entry is deliberately thin. Enumerating it properly is an audit, and
nobody has run one. Recording that it has not been run is the honest state.
