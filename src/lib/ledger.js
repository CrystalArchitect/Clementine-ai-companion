/**
 * The Journey Ledger — creative footprints that predate this project.
 *
 * These entries are on the **Science belt**: each one is a claim about work that
 * actually happened and can be checked against the world. That is exactly why
 * `verified` exists. An entry is only allowed to render as evidence — with an
 * embed or an outbound link — once the CrystalArchitect has confirmed the URL
 * points at the right recording. Until then it renders as an unverified note,
 * plainly labelled.
 *
 * Adding a confirmed link:
 *   1. Open the public share URL of the recording.
 *   2. For YouTube, copy the eleven-character id out of the URL
 *      (`https://youtu.be/<ID>` or `https://www.youtube.com/watch?v=<ID>`)
 *      and set `youtubeId`.
 *   3. Set `url` to the canonical public page for the recording.
 *   4. Flip `verified` to `true`. Nothing renders as evidence until you do.
 *
 * The embed is deliberately click-to-load and points at youtube-nocookie.com:
 * no third party is contacted, and no cookie is set, until a reader asks for
 * the video. A page about sovereignty should not leak its readers on load.
 */

/**
 * @typedef {Object} LedgerEntry
 * @property {string} id            Stable slug, used as the anchor.
 * @property {string} title         What the thing is.
 * @property {string} era           Rough period. Say "circa" when it is circa.
 * @property {string} place         Where it happened.
 * @property {string} platform      Where it was published.
 * @property {string} colour        CSS custom property driving the node dot.
 * @property {string|null} url      Canonical public page, or null while pending.
 * @property {string|null} youtubeId  YouTube id for the embed, or null.
 * @property {boolean} verified     Has the URL been confirmed to be the right recording?
 * @property {string} body          Two or three sentences. What it was, and what it fed.
 */

/** @type {LedgerEntry[]} */
export const entries = [
  {
    id: 'ingleburn-use-somebody',
    title: '"Use Somebody" — live, Ingleburn',
    era: 'Circa the Sydney years',
    place: 'Ingleburn, South-Western Sydney',
    platform: 'YouTube',
    colour: 'var(--pink)',
    url: null,
    youtubeId: null,
    verified: false,
    body: `A live vocal and acoustic performance in South-Western Sydney, uploaded to a
      YouTube account that is no longer under my control. Working a room by ear — reading
      how a held note lands, where a phrase wants to breathe — is the same instinct that
      later went into rhythm and pacing in the Codex. The performance is real; the link is
      not yet confirmed, and it stays marked that way until it is.`
  },
  {
    id: 'tiktok-fragments',
    title: 'Short-form fragments',
    era: 'Pre-TerAustralis',
    place: 'Regional and metropolitan Australia',
    platform: 'TikTok',
    colour: 'var(--blue)',
    url: null,
    youtubeId: null,
    verified: false,
    body: `Early experiments in vocal dynamics and short-form storytelling, published to
      accounts I can no longer sign in to. They are listed here as checkpoints rather than
      as work I am pointing at — no specific clip is being claimed, because no specific
      clip has been confirmed.`
  },
  {
    id: 'western-australia',
    title: 'Heavy industry, Western Australia',
    era: 'Before Sydney',
    place: 'Western Australia',
    platform: 'Not published',
    colour: 'var(--gold)',
    url: null,
    youtubeId: null,
    verified: false,
    body: `Time spent around industrial-scale operations, where a plan meets tonnage,
      weather and distance, and the plan is the thing that gives. Nothing was recorded and
      nothing is linked. It is on this page because it is where the project's stubbornness
      about local-first systems and long supply lines actually comes from.`
  }
];

/**
 * Entries whose links have been confirmed. Only these are shown as evidence.
 * @returns {LedgerEntry[]}
 */
export function verifiedEntries() {
  return entries.filter((entry) => entry.verified);
}

/**
 * Entries still awaiting a confirmed link.
 * @returns {LedgerEntry[]}
 */
export function pendingEntries() {
  return entries.filter((entry) => !entry.verified);
}
