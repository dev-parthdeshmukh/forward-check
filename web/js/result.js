// The two things the checker says back: a live progress card, then the result card.
import { fetchSpeech } from "./api.js";
import { h, icon, domainOf, safeHref } from "./dom.js";
import { t, formatDate, formatTime, localDay, VERDICTS } from "./i18n.js";

const VERDICT_STYLE = {
  VERIFIED: { cls: "v-true", icon: "check" },
  FALSE: { cls: "v-false", icon: "x" },
  OUTDATED: { cls: "v-old", icon: "clock" },
  PARTLY_SUPPORTED: { cls: "v-partly", icon: "half" },
  UNVERIFIABLE: { cls: "v-unknown", icon: "help" },
};
const TIER_ICON = { official: "shield", fact_checker: "search", news: "page", other: "link" };
const STANCE_ICON = { refutes: "x", supports: "check", context: "info" };
// Longer messages (articles, PDFs) are not echoed back whole; their claims are quoted one by one instead.
const MAX_ECHO_CHARS = 1500;
const SPEECH_CHARS = 1400;

export function verdictStyle(verdict) {
  return VERDICT_STYLE[verdict] || VERDICT_STYLE.UNVERIFIABLE;
}

export function verdictChip(verdict, lang) {
  const style = verdictStyle(verdict);
  return h("span", { class: `chip ${style.cls}` }, icon(style.icon, 14), t(lang, `v_${verdict}`));
}

function formatElapsed(ms) {
  const total = Math.floor(ms / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/* ---------- progress ---------- */

function stepRow(label) {
  const mark = h("span", { class: "p-mark" });
  const text = h("span", { class: "p-label" }, label);
  const el = h("li", { class: "p-step is-pending" }, mark, text);
  return {
    el,
    set(state, newLabel) {
      el.className = `p-step is-${state}`;
      mark.replaceChildren(state === "done" ? icon("check", 14) : "");
      if (newLabel) text.textContent = newLabel;
    },
  };
}

// A card that follows one check: feed it the stream's events, then swap it for the result.
export function createProgress(lang, kind) {
  const read = stepRow(t(lang, `st_${kind}`));
  const find = stepRow(t(lang, "findClaims"));
  const verify = stepRow(t(lang, "checking"));
  const claimList = h("div", { class: "p-claims", hidden: true });
  const hint = h("span", {}, t(lang, "usuallyTakes"));
  const clock = h("span", { class: "p-clock" }, "0:00");
  const el = h("div", { class: "card progress", role: "status" },
    h("ol", { class: "p-steps" }, read.el, find.el, verify.el),
    claimList,
    h("div", { class: "p-foot" }, hint, clock));

  const started = Date.now();
  const ticker = setInterval(() => { clock.textContent = formatElapsed(Date.now() - started); }, 1000);
  const rows = new Map();
  read.set("active");

  function showClaims(claims) {
    rows.clear();
    claimList.replaceChildren();
    claims.forEach((claim, index) => {
      const step = h("div", { class: "p-claim-step" }, icon("search", 14), h("span", {}, t(lang, "starting")));
      const state = h("span", { class: "p-claim-state" }, h("span", { class: "spinner" }));
      const row = h("div", { class: "p-claim" },
        h("span", { class: "num" }, index + 1),
        h("div", { class: "p-claim-body" }, h("div", { class: "p-claim-text" }, claim.original_span || claim.text), step),
        state);
      rows.set(claim.id, { row, step, state });
      claimList.append(row);
    });
    claimList.hidden = claims.length === 0;
  }

  return {
    el,
    handle(event) {
      if (event.type === "status") {
        kind = event.stage;
        read.set("active", t(lang, `st_${kind}`));
        find.set("pending", t(lang, "findClaims"));
        verify.set("pending");
        claimList.hidden = true;
      } else if (event.type === "claims") {
        lang = event.reply_language_code || lang;
        // From here on the card speaks the language the answer will be in.
        hint.textContent = t(lang, "usuallyTakes");
        read.set("done", t(lang, `st_${kind}`));
        find.set("done", t(lang, "claimsFound", event.claims.length));
        verify.set(event.claims.length ? "active" : "done", t(lang, "checking"));
        showClaims(event.claims);
      } else if (event.type === "step") {
        const entry = rows.get(event.claim_id);
        if (!entry) return;
        const searching = event.action === "search";
        const label = searching ? t(lang, "searching", event.detail) : t(lang, "readingSite", domainOf(event.detail));
        entry.step.replaceChildren(icon(searching ? "search" : "page", 14), h("span", {}, label));
        entry.step.classList.remove("swap");
        void entry.step.offsetWidth;  // restart the fade so each new lookup is noticed
        entry.step.classList.add("swap");
      } else if (event.type === "claim_done") {
        const entry = rows.get(event.claim.claim.id);
        if (!entry) return;
        entry.row.classList.add("is-done");
        entry.step.remove();
        entry.state.replaceChildren(verdictChip(event.claim.verdict, lang));
      }
    },
    stop() {
      clearInterval(ticker);
    },
  };
}

/* ---------- result pieces ---------- */

function callout(kind, title, text) {
  if (!text) return null;
  return h("div", { class: `callout callout-${kind}` },
    h("div", { class: "callout-title" }, icon(kind === "wrong" ? "x" : "check", 16), title),
    h("p", {}, text));
}

function confidenceMeter(level, lang) {
  const filled = { low: 1, medium: 2, high: 3 }[level] || 1;
  return h("div", { class: "conf", title: t(lang, `conf_${level}`) },
    h("span", { class: "conf-bars", "aria-hidden": "true" },
      [1, 2, 3].map((n) => h("i", { class: n <= filled ? "on" : "" }))),
    h("span", { class: "conf-text" }, t(lang, `conf_${level}`)));
}

function timeline(item, lang) {
  if (item.verdict !== "OUTDATED" || !(item.true_as_of || item.changed_on)) return null;
  const node = (cls, label, date) => h("div", { class: `tl-node ${cls}` },
    h("span", { class: "tl-dot" }), h("div", { class: "tl-label" }, label), h("div", { class: "tl-date" }, date));
  return h("div", { class: "timeline" },
    item.true_as_of ? node("was", t(lang, "tl_was"), formatDate(item.true_as_of, lang)) : null,
    item.changed_on ? node("changed", t(lang, "tl_changed"), formatDate(item.changed_on, lang)) : null,
    node("today", t(lang, "tl_today"), formatDate(localDay(), lang)));
}

function evidenceCard(ev, lang) {
  const href = safeHref(ev.url);
  const tier = TIER_ICON[ev.tier] ? ev.tier : "other";
  return h("div", { class: `ev stance-${ev.stance}` },
    h("div", { class: "ev-head" },
      h("span", { class: `tier tier-${tier}` }, icon(TIER_ICON[tier], 13), t(lang, `tier_${tier}`)),
      h("span", { class: "ev-name" }, ev.source_name || ev.domain),
      ev.published_date ? h("span", { class: "ev-date" }, formatDate(ev.published_date, lang)) : null),
    ev.quote ? h("blockquote", {}, ev.quote) : null,
    h("div", { class: "ev-foot" },
      h("span", { class: "stance" }, icon(STANCE_ICON[ev.stance] || "info", 14),
        ev.independent === false ? t(lang, "samePage") : t(lang, `stance_${ev.stance}`)),
      href
        ? h("a", { class: "ev-link", href, target: "_blank", rel: "noopener noreferrer" }, ev.domain || domainOf(href), icon("external", 13))
        : h("span", { class: "ev-link" }, ev.domain)));
}

function howChecked(item, lang) {
  const searches = item.steps.filter((s) => s.action === "search");
  const pages = item.steps.filter((s) => s.action === "fetch");
  if (!item.steps.length && !item.validation_notes.length) return null;
  return h("div", { class: "how" },
    h("div", { class: "how-title" }, t(lang, "howChecked")),
    item.steps.length
      ? h("div", { class: "how-stats dotsep" },
          h("span", {}, t(lang, "searchCount", searches.length)), h("span", {}, t(lang, "pageCount", pages.length)))
      : null,
    h("ul", { class: "how-steps" },
      item.steps.map((s) => h("li", {}, icon(s.action === "search" ? "search" : "page", 13),
        h("span", {}, s.action === "search" ? s.detail : domainOf(s.detail))))),
    item.validation_notes.length
      ? h("ul", { class: "how-notes" }, item.validation_notes.map((note) => h("li", {}, note)))
      : null);
}

function proofBlock(item, lang) {
  return h("div", { class: "proof-body" },
    item.evidence.length
      ? item.evidence.map((ev) => evidenceCard(ev, lang))
      : h("p", { class: "muted" }, t(lang, "noProof")),
    howChecked(item, lang));
}

// The explanation, what is wrong / true, the timeline: everything about one claim except its proof.
function claimDetail(item, lang) {
  return [
    item.explanation ? h("p", { class: "explain" }, item.explanation) : null,
    item.downgraded_from
      ? h("p", { class: "withdrawn" }, icon("shield", 15), t(lang, "withdrawn", t(lang, `v_${item.downgraded_from}`)))
      : null,
    timeline(item, lang),
    callout("wrong", t(lang, "whatWrong"), item.what_is_wrong),
    callout("true", t(lang, "whatTrue"), item.correct_information),
  ];
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// The message with each checked passage tinted in its verdict's colour and numbered.
function highlighted(text, claims) {
  const marks = [];
  claims.forEach((item, index) => {
    const span = (item.claim.original_span || "").trim();
    if (!span) return;
    let at = text.indexOf(span);
    let length = span.length;
    if (at < 0) {
      // The model may have changed spacing or line breaks when copying the passage.
      const match = new RegExp(span.split(/\s+/).map(escapeRegExp).join("\\s+")).exec(text);
      if (match) [at, length] = [match.index, match[0].length];
    }
    if (at >= 0) marks.push({ at, end: at + length, index, verdict: item.verdict });
  });
  marks.sort((a, b) => a.at - b.at);

  const out = h("p", { class: "echo-text" });
  let cursor = 0;
  for (const mark of marks) {
    if (mark.at < cursor) continue;  // overlaps an earlier passage
    out.append(text.slice(cursor, mark.at));
    out.append(h("mark", { class: `hl ${verdictStyle(mark.verdict).cls}` },
      claims.length > 1 ? h("sup", {}, mark.index + 1) : null, text.slice(mark.at, mark.end)));
    cursor = mark.end;
  }
  out.append(text.slice(cursor));
  return out;
}

function echoBlock(result, lang) {
  const text = result.input_text || "";
  const heard = result.source_kind === "audio";
  const seen = result.source_kind === "image" || (result.source_kind === "pdf" && text.length <= MAX_ECHO_CHARS);
  const multi = result.claims.length > 1;
  if (!text || text.length > MAX_ECHO_CHARS || result.source_kind === "url") return null;
  if (!multi && !heard && !seen) return null;  // a typed single claim is already on screen in the user's bubble
  const title = heard ? t(lang, "readAudio") : seen ? t(lang, "readImage") : t(lang, "checkedMessage");
  return h("div", { class: "echo" }, h("div", { class: "section-title" }, title), highlighted(text, result.claims));
}

function warnings(result, lang) {
  if (!result.risk_flags.length) return null;
  return h("div", { class: "warn" },
    h("div", { class: "warn-title" }, icon("alert", 16), t(lang, "warning")),
    h("ul", {}, result.risk_flags.map((flag) => h("li", {}, flag.message))));
}

/* ---------- reading the answer aloud, copying it ---------- */

function spokenText(result, lang) {
  const parts = [`${t(lang, `v_${result.overall_verdict}`)}.`];
  for (const item of result.claims) {
    if (result.claims.length > 1) parts.push(`${t(lang, `v_${item.verdict}`)}.`);
    parts.push(item.explanation, item.correct_information);
  }
  if (!result.claims.length) parts.push(result.summary);
  let text = "";
  for (const part of parts.filter(Boolean)) {
    if (text.length + part.length + 1 > SPEECH_CHARS) break;
    text += (text ? " " : "") + part;
  }
  return text;
}

export function plainText(result, lang) {
  const lines = [`*${t(lang, `v_${result.overall_verdict}`)}* · Forward Check`];
  for (const item of result.claims) {
    lines.push("");
    if (result.claims.length > 1) lines.push(`*${t(lang, `v_${item.verdict}`)}*: “${item.claim.original_span || item.claim.text}”`);
    if (item.explanation) lines.push(item.explanation);
    if (item.what_is_wrong) lines.push(`✗ ${item.what_is_wrong}`);
    if (item.correct_information) lines.push(`✓ ${item.correct_information}`);
    for (const ev of item.evidence.slice(0, 3)) lines.push(`– ${ev.source_name}: ${ev.url}`);
  }
  if (!result.claims.length) lines.push("", result.summary);
  return lines.join("\n");
}

let playing = null;  // { audio, reset } for the one reply being read aloud

function stopSpeech() {
  if (!playing) return;
  playing.audio.pause();
  playing.reset();
  playing = null;
}

function listenButton(result, lang) {
  const label = h("span", {}, t(lang, "listen"));
  const button = h("button", { class: "act", type: "button" }, icon("volume", 16), label);
  const reset = () => {
    button.classList.remove("is-on", "is-busy");
    button.replaceChildren(icon("volume", 16), label);
    label.textContent = t(lang, "listen");
  };
  button.addEventListener("click", async () => {
    if (button.classList.contains("is-on") || button.classList.contains("is-busy")) return stopSpeech();
    stopSpeech();
    button.classList.add("is-busy");
    const audio = new Audio();
    playing = { audio, reset };
    try {
      audio.src = URL.createObjectURL(await fetchSpeech(spokenText(result, lang), lang));
      if (playing?.audio !== audio) return;  // stopped, or another reply started, while loading
      audio.addEventListener("ended", stopSpeech);
      await audio.play();
      button.classList.replace("is-busy", "is-on");
      button.replaceChildren(icon("stop", 16), label);
      label.textContent = t(lang, "stop");
    } catch {
      if (playing?.audio === audio) stopSpeech();
    }
  });
  return button;
}

function copyButton(result, lang) {
  const label = h("span", {}, t(lang, "copy"));
  const button = h("button", { class: "act", type: "button" }, icon("copy", 16), label);
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(plainText(result, lang));
    } catch {
      return;  // clipboard blocked (insecure page or denied permission); leave the label alone
    }
    label.textContent = t(lang, "copied");
    setTimeout(() => { label.textContent = t(lang, "copy"); }, 1600);
  });
  return button;
}

/* ---------- the result card ---------- */

function verdictBand(result, lang) {
  const style = verdictStyle(result.overall_verdict);
  const single = result.claims.length === 1 ? result.claims[0] : null;
  const counts = VERDICTS
    .map((verdict) => [verdict, result.claims.filter((c) => c.verdict === verdict).length])
    .filter(([, n]) => n > 0);
  return h("header", { class: "verdict" },
    h("span", { class: "verdict-icon" }, icon(style.icon, 26)),
    h("div", { class: "verdict-text" },
      h("div", { class: "verdict-label" }, t(lang, `v_${result.overall_verdict}`)),
      lang !== "en" ? h("div", { class: "verdict-en" }, t("en", `v_${result.overall_verdict}`)) : null),
    single ? confidenceMeter(single.confidence, lang) : null,
    result.claims.length > 1
      ? h("div", { class: "verdict-counts" }, counts.map(([verdict, n]) =>
          h("span", { class: `count ${verdictStyle(verdict).cls}` }, h("b", {}, n), t(lang, `v_${verdict}`))))
      : null);
}

function singleBody(result, lang) {
  const item = result.claims[0];
  const summary = h("summary", { class: "proof-toggle" }, h("span", {}, t(lang, "showProof", item.evidence.length)), icon("chevron", 18));
  const proof = h("details", { class: "proof" }, summary, proofBlock(item, lang));
  proof.addEventListener("toggle", () => {
    summary.firstChild.textContent = proof.open ? t(lang, "hideProof") : t(lang, "showProof", item.evidence.length);
  });
  return [echoBlock(result, lang), claimDetail(item, lang), warnings(result, lang), proof];
}

function multiBody(result, lang) {
  const echo = echoBlock(result, lang);
  const rows = result.claims.map((item, index) => {
    const style = verdictStyle(item.verdict);
    return h("details", { class: `claim ${style.cls}` },
      h("summary", {},
        h("span", { class: "num" }, index + 1),
        h("div", { class: "claim-head" },
          verdictChip(item.verdict, lang),
          h("div", { class: "claim-line" }, item.what_is_wrong || item.explanation || item.claim.text)),
        icon("chevron", 18)),
      h("div", { class: "claim-body" },
        // Without the echoed message above, quote the passage here so the reader knows what was checked.
        echo ? null : h("blockquote", { class: "claim-quote" }, item.claim.original_span || item.claim.text),
        claimDetail(item, lang),
        h("div", { class: "section-title" }, t(lang, "sources", item.evidence.length)),
        proofBlock(item, lang)));
  });
  return [
    echo,
    h("div", { class: "section-title" }, t(lang, "claimsChecked")),
    h("div", { class: "claims" }, rows),
    warnings(result, lang),
  ];
}

// actions.onShare(result, lang) opens the share card.
export function createResultCard(result, actions) {
  const lang = result.reply_language_code || "en";
  const style = verdictStyle(result.overall_verdict);
  const hasClaims = result.claims.length > 0;
  const checkedAt = result.checked_at ? new Date(result.checked_at) : new Date();
  const fellBack = result.notes.some((note) => note.includes(" failed: "));
  const inputNotes = result.notes.filter((note) => !note.includes(" failed: ") && note !== "No checkable claims found.");

  const body = !hasClaims
    ? [h("p", { class: "explain" }, result.summary)]
    : result.claims.length === 1 ? singleBody(result, lang) : multiBody(result, lang);

  return h("article", { class: `card result ${hasClaims ? style.cls : "v-unknown"} ${hasClaims ? "" : "no-claims"}`, lang },
    hasClaims
      ? verdictBand(result, lang)
      : h("header", { class: "verdict" },
          h("span", { class: "verdict-icon" }, icon("info", 26)),
          h("div", { class: "verdict-text" }, h("div", { class: "verdict-label" }, t(lang, "noClaimsTitle")))),
    h("div", { class: "result-body" },
      body,
      result.claims.some((item) => item.claim.topic === "health") ? h("p", { class: "fineprint" }, t(lang, "health")) : null,
      inputNotes.map((note) => h("p", { class: "fineprint" }, note)),
      fellBack ? h("p", { class: "fineprint" }, t(lang, "fallback")) : null),
    h("footer", { class: "actions" },
      hasClaims ? listenButton(result, lang) : null,
      hasClaims ? h("button", { class: "act", type: "button", onclick: () => actions.onShare(result, lang) }, icon("share", 16), h("span", {}, t(lang, "share"))) : null,
      hasClaims ? copyButton(result, lang) : null,
      h("span", { class: "act-meta dotsep" },
        result.cached
          ? h("span", { class: "cached" }, icon("bolt", 13), t(lang, "cached", result.times_checked))
          : h("span", {}, t(lang, "seconds", Math.round(result.seconds))),
        h("span", {}, formatTime(checkedAt, lang)))));
}

export function createErrorCard(message, lang, onRetry) {
  return h("div", { class: "card error-card", role: "alert" },
    h("div", { class: "error-title" }, icon("alert", 18), t(lang, "error")),
    message ? h("p", { class: "muted" }, message) : null,
    onRetry ? h("button", { class: "btn btn-ghost", type: "button", onclick: onRetry }, icon("refresh", 16), t(lang, "retry")) : null);
}
