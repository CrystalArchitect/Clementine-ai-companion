<script>
  /**
   * What they hold about you, and the ability to take any of it back.
   *
   * This is the first surface in this window that can destroy something. The
   * server's `forget` is immediate and permanent — there is no undo, no bin,
   * no second chance — so the work here is mostly about not deleting the
   * wrong thing.
   *
   * The hazard is specific and was measured, not guessed. Note and reflection
   * handles are positions in a list: n1, n2, n3. Deleting n2 renumbers
   * everything after it, so a list fetched a moment ago can already describe
   * a different memory than the server does. Confirm against a stale list and
   * the person permanently loses a memory they never chose. (Facts are keyed
   * by name and do not move; only notes and reflections renumber.)
   *
   * Three guards, none of which needed a new endpoint:
   *
   *   1. The confirmation names the memory in full, so the person is agreeing
   *      to specific words rather than to a row position.
   *   2. Immediately before deleting, the list is re-read and the handle is
   *      checked to still mean the same words. This closes the window to the
   *      length of one request instead of however long the panel sat open.
   *   3. After deleting, the server says what it removed. That is compared
   *      against what was agreed to, and any disagreement is reported loudly
   *      rather than swallowed.
   *
   * Guard 3 cannot prevent a wrong deletion, only surface one. That is worth
   * saying plainly: told what went, a person can put it back by hand, and
   * told nothing they cannot. The durable fix is stable identifiers on the
   * server, which is a change to the memory format and not this component's
   * to make.
   */
  import Drawer from './Drawer.svelte';

  let { open = false, onClose = () => {} } = $props();

  let facts = $state([]);
  let notes = $state([]);
  let reflections = $state([]);
  let loading = $state(false);
  let failed = $state(false);
  let pending = $state(null); // the memory awaiting confirmation
  let working = $state(false);
  let warning = $state('');
  let said = $state('');

  const total = $derived(facts.length + notes.length + reflections.length);

  async function read() {
    const res = await fetch('/api/memories');
    if (!res.ok) throw new Error('unreachable');
    return await res.json();
  }

  async function load() {
    loading = true;
    failed = false;
    try {
      const data = await read();
      facts = data.facts ?? [];
      notes = data.notes ?? [];
      reflections = data.reflections ?? [];
    } catch {
      failed = true;
    }
    loading = false;
  }

  $effect(() => {
    if (open) load();
  });

  /**
   * Does `handle` still mean these exact words on the server?
   *
   * Facts are identified by their handle, which is the key itself and stable.
   * Notes and reflections are identified by their text, because their handle
   * is only a row number and is precisely the thing that cannot be trusted.
   */
  function stillMeans(fresh, item) {
    const group = fresh[item.kind === 'fact' ? 'facts'
      : item.kind === 'note' ? 'notes' : 'reflections'] ?? [];
    const found = group.find((m) => m.handle === item.handle);
    if (!found) return false;
    return item.kind === 'fact' ? found.handle === item.handle
      : found.text === item.text;
  }

  /** The server reports what it removed; check it is what was agreed. */
  function removedWhatWasAgreed(forgotten, item) {
    const said = String(forgotten || '');
    return item.kind === 'fact'
      ? said.includes(item.handle)
      : said.includes(item.text);
  }

  function ask(kind, memory) {
    warning = '';
    said = '';
    pending = { kind, handle: memory.handle, text: memory.text };
  }

  async function forget() {
    const item = pending;
    pending = null;
    if (!item) return;
    working = true;
    warning = '';
    said = '';

    try {
      // Guard 2 — re-read and re-check before destroying anything.
      const fresh = await read();
      if (!stillMeans(fresh, item)) {
        warning =
          'That memory shifted position before it could be forgotten, so ' +
          'nothing was deleted. The list below has been refreshed — check ' +
          'it and try again.';
        await load();
        working = false;
        return;
      }

      const res = await fetch('/api/forget', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handle: item.handle })
      });
      const data = await res.json();

      if (!data.ok) {
        warning = 'Nothing matched that handle, so nothing was forgotten.';
      } else if (!removedWhatWasAgreed(data.forgotten, item)) {
        // Guard 3 — the wrong thing went. Say exactly what, because a person
        // told what they lost can write it back, and one told nothing cannot.
        warning =
          `You agreed to forget “${item.text}”, but the server removed ` +
          `${data.forgotten} instead. This should not happen. If that was ` +
          `not what you meant to lose, add it again now, while you can still ` +
          `read it here.`;
      } else {
        said = `Forgotten: ${data.forgotten}`;
      }
    } catch {
      warning = 'Could not reach them, so nothing was forgotten.';
    }

    await load();
    working = false;
  }
</script>

<Drawer
  {open}
  {onClose}
  title="What they remember"
  status={loading ? 'reading…' : failed ? 'unavailable' : `${total} in all`}
  note="Their memory is a folder on this machine. Forgetting is immediate
        and cannot be undone.">
  {#if warning}
    <p class="warning" role="alert">{warning}</p>
  {/if}
  {#if said}
    <p class="said" role="status">{said}</p>
  {/if}

  {#if failed}
        <p class="empty">
          Their memory could not be read. Is <code>server.py</code> still
          running?
        </p>
      {:else if !loading && total === 0}
        <p class="empty">
          They hold nothing about you yet. What you tell them to remember
          will appear here, and you can take any of it back.
        </p>
  {:else}
    {#each [['Told to them', 'fact', facts], ['Noticed', 'note', notes], ['Concluded on their own', 'reflection', reflections]] as [label, kind, items] (kind)}
      {#if items.length}
        <h3>{label}</h3>
        <ul>
          {#each items as memory (memory.handle + memory.text)}
            <li>
              <div class="text">
                {memory.text}
                {#if memory.tags?.length}
                  <span class="tags">
                    {#each memory.tags as tag (tag)}<em>#{tag}</em>{/each}
                  </span>
                {/if}
              </div>
              <button
                class="forget"
                disabled={working}
                onclick={() => ask(kind, memory)}
                aria-label={`Forget: ${memory.text}`}>forget</button>
            </li>
          {/each}
        </ul>
      {/if}
    {/each}
  {/if}
</Drawer>

{#if pending}
  <div class="scrim confirming"></div>
  <div class="confirm" role="alertdialog" aria-modal="true"
       aria-labelledby="confirm-title">
    <b id="confirm-title">Forget this permanently?</b>
    <blockquote>{pending.text}</blockquote>
    <p>This cannot be undone. There is no copy and no bin to recover it from.</p>
    <div class="actions">
      <button class="cancel" onclick={() => (pending = null)}>Keep it</button>
      <button class="destroy" onclick={forget}>Forget it</button>
    </div>
  </div>
{/if}

<style>
  /* The panel shell — scrim, header, scrolling body, footer — lives in
     Drawer.svelte. What remains here is only what is particular to showing
     memories and to destroying one. */
  .scrim.confirming {
    position: fixed;
    inset: 0;
    z-index: 40;
    background: rgba(0, 0, 4, 0.75);
  }
  h3 {
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    margin: 18px 0 8px;
  }
  ul {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  li {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    background: rgba(233, 235, 244, 0.04);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 9px 11px;
  }
  .text {
    font-size: 0.85rem;
    line-height: 1.45;
    text-wrap: pretty;
  }
  .tags {
    display: block;
    margin-top: 4px;
  }
  .tags em {
    font-style: normal;
    font-family: var(--mono);
    font-size: 0.68rem;
    color: var(--purple);
    margin-right: 6px;
  }
  .forget {
    flex: none;
    background: transparent;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--muted);
    font-size: 0.72rem;
    padding: 3px 10px;
    cursor: pointer;
  }
  .forget:hover:not(:disabled) {
    color: #fca5a5;
    border-color: rgba(252, 165, 165, 0.4);
  }
  .forget:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .empty {
    color: var(--muted);
    font-size: 0.83rem;
    line-height: 1.6;
    padding: 22px 0;
    text-wrap: pretty;
  }
  .warning,
  .said {
    /* No horizontal margin: these used to sit outside the scrolling body and
       needed to match its inset by hand. They are inside it now, and 18px of
       their own would sit on top of the 18px it already provides. */
    margin: 12px 0 0;
    padding: 9px 11px;
    border-radius: 8px;
    font-size: 0.8rem;
    line-height: 1.5;
    text-wrap: pretty;
  }
  .warning {
    color: #fca5a5;
    background: rgba(252, 165, 165, 0.08);
    border: 1px solid rgba(252, 165, 165, 0.3);
  }
  .said {
    color: var(--green);
    background: rgba(52, 211, 153, 0.08);
    border: 1px solid rgba(52, 211, 153, 0.25);
  }

  .confirm {
    position: fixed;
    z-index: 50;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(400px, calc(100vw - 32px));
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 18px;
  }
  .confirm b {
    color: var(--ink);
  }
  blockquote {
    margin: 11px 0;
    padding: 9px 12px;
    border-left: 2px solid var(--purple);
    background: rgba(233, 235, 244, 0.04);
    font-size: 0.86rem;
    line-height: 1.5;
    text-wrap: pretty;
  }
  .confirm p {
    color: var(--muted);
    font-size: 0.8rem;
    line-height: 1.5;
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 9px;
    margin-top: 16px;
  }
  .actions button {
    border-radius: 999px;
    padding: 7px 15px;
    font-size: 0.82rem;
    cursor: pointer;
    border: 1px solid var(--line);
  }
  .cancel {
    background: transparent;
    color: var(--ink);
  }
  .destroy {
    background: rgba(252, 165, 165, 0.12);
    border-color: rgba(252, 165, 165, 0.45);
    color: #fca5a5;
  }

</style>
