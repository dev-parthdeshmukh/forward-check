import { streamCheck, fetchMeta } from "./api.js";
import { h, icon, domainOf } from "./dom.js";
import { t, uiLang, applyStatic, formatTime, VERDICTS } from "./i18n.js";
import { startRecording } from "./recorder.js";
import { createProgress, createResultCard, createErrorCard, plainText, verdictStyle } from "./result.js";
import { drawShareCard, canvasFile, canShareFiles } from "./share.js";

const $ = (id) => document.getElementById(id);
const thread = $("thread");
const messages = $("messages");
const input = $("input");
const sendBtn = $("send");
const micBtn = $("mic");
const fileInput = $("file");
const attachmentTray = $("attachment");
const langSelect = $("lang");

const HISTORY_KEY = "fc.history";
const HISTORY_MAX = 12;
// Saved results keep only this much of a long article's text.
const HISTORY_TEXT_CHARS = 4000;
const LONG_BUBBLE_CHARS = 420;
const WAVE_BARS = 40;

const EXAMPLES = [
  {
    id: "scheme", kind: "text", language: "हिन्दी",
    text: "🔥 बड़ी खुशखबरी 🔥 प्रधानमंत्री फ्री लैपटॉप योजना 2026 के तहत सरकार सभी छात्रों को मुफ्त लैपटॉप दे रही है। 10वीं पास सभी छात्र आवेदन कर सकते हैं। अभी रजिस्टर करें: http://pm-laptop-yojana.xyz आखिरी तारीख कल है, जल्दी करें और सभी ग्रुप में भेजें 🙏",
  },
  {
    id: "note", kind: "text", language: "English",
    text: "URGENT!! RBI has withdrawn the 2000 rupee note. You can exchange your 2000 rupee notes at any bank branch till 30 September, so hurry up. After that the notes will not be legal tender and will become worthless paper.",
  },
  {
    id: "shot", kind: "image", language: "English", asset: "demo/forward-screenshot.png",
    preview: "BREAKING: NASA has confirmed that the Earth will go completely dark for 6 days…",
  },
  {
    id: "voice", kind: "audio", language: "हिन्दी", asset: "demo/voice-note-hi.mp3",
    preview: "रोज़ सुबह खाली पेट लहसुन खाने से डेंगू का बुखार पूरी तरह ठीक हो जाता है…",
  },
  {
    id: "marathi", kind: "text", language: "मराठी",
    text: "डॉक्टरांचा सल्ला: दर 15 मिनिटांनी गरम पाणी प्यायल्याने कोरोना विषाणू घशातच मरतो आणि फुफ्फुसांपर्यंत पोहोचत नाही. हा संदेश सर्वांना पाठवा.",
  },
];
const KIND_ICON = { text: "text", image: "image", audio: "mic", pdf: "page", url: "link" };

const store = {
  read(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? fallback;
    } catch {
      return fallback;  // storage blocked or holding something unreadable
    }
  },
  write(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch { /* storage full or blocked: the chat still works, it just is not remembered */ }
  },
};

let languageSetting = store.read("fc.lang", "auto");  // auto | en | hi | mr
let history = store.read(HISTORY_KEY, []);
let busy = false;
let attachment = null;
let recording = null;
let meta = null;

// The language of the page itself. "Auto" follows the browser; replies then follow each message.
function chromeLang() {
  return languageSetting === "auto" ? uiLang((navigator.language || "en").slice(0, 2)) : languageSetting;
}

/* ---------- small helpers ---------- */

function nearEnd() {
  return thread.scrollHeight - thread.scrollTop - thread.clientHeight < 180;
}

function scrollToEnd() {
  thread.scrollTop = thread.scrollHeight;
}

function addMessage(side, ...content) {
  const el = h("div", { class: `msg ${side}` }, ...content);
  messages.append(el);
  return el;
}

function toast(text) {
  document.querySelector(".toast")?.remove();
  const el = h("div", { class: "toast", role: "alert" }, text);
  document.querySelector(".chat").append(el);
  setTimeout(() => el.remove(), 5000);
}

function fileKind(file) {
  const name = (file.name || "").toLowerCase();
  if (file.type.startsWith("image/")) return "image";
  if (file.type.startsWith("audio/") || /\.(ogg|opus|mp3|wav|m4a|aac|flac|webm)$/.test(name)) return "audio";
  if (file.type === "application/pdf" || name.endsWith(".pdf")) return "pdf";
  return "text";
}

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatClock(seconds) {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function isLink(text) {
  return /^\s*https?:\/\/\S+\s*$/.test(text);
}

function modelName(id) {
  // "claude-opus-5-5" -> "Claude Opus 5.5"
  const words = [];
  const numbers = [];
  for (const part of id.split("-")) (/^[\d.]+$/.test(part) ? numbers : words).push(part);
  return [...words.map((w) => w[0].toUpperCase() + w.slice(1)), numbers.join(".")].filter(Boolean).join(" ");
}

/* ---------- user bubbles ---------- */

function fileChip(kind, name, detail) {
  return h("div", { class: "filechip" },
    h("span", { class: "filechip-icon" }, icon(KIND_ICON[kind] || "page", 20)),
    h("div", {}, h("div", { class: "filechip-name" }, name), detail ? h("div", { class: "filechip-meta" }, detail) : null));
}

function audioPlayer(src) {
  const audio = new Audio(src);
  const fill = h("i");
  const time = h("span", { class: "player-time" }, "0:00");
  const button = h("button", { class: "player-btn", type: "button", "aria-label": t(chromeLang(), "listen") }, icon("play", 18));
  const setIcon = (name) => button.replaceChildren(icon(name, 18));
  button.addEventListener("click", () => (audio.paused ? audio.play() : audio.pause()));
  audio.addEventListener("play", () => setIcon("pause"));
  audio.addEventListener("pause", () => setIcon("play"));
  audio.addEventListener("loadedmetadata", () => { if (isFinite(audio.duration)) time.textContent = formatClock(audio.duration); });
  audio.addEventListener("timeupdate", () => {
    if (isFinite(audio.duration)) fill.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
    time.textContent = formatClock(audio.currentTime);
  });
  audio.addEventListener("ended", () => { fill.style.width = "0"; });
  return h("div", { class: "player" }, button, h("div", { class: "player-bar" }, fill), time);
}

// entry: { kind, text?, name?, file? } — file is only there for a message sent in this session.
function userBubble(entry, when) {
  const lang = chromeLang();
  const time = h("span", { class: "bubble-time" }, formatTime(when, lang));
  if (entry.kind === "image" && entry.file) {
    return h("div", { class: "bubble media" }, h("img", { src: URL.createObjectURL(entry.file), alt: entry.name || "" }), time);
  }
  if (entry.kind === "audio" && entry.file) {
    return h("div", { class: "bubble" }, audioPlayer(URL.createObjectURL(entry.file)), time);
  }
  if (entry.kind !== "text" && entry.kind !== "url") {
    const detail = entry.file ? `${t(lang, `kind_${entry.kind}`)}, ${formatSize(entry.file.size)}` : t(lang, `kind_${entry.kind}`);
    return h("div", { class: "bubble" }, fileChip(entry.kind, entry.name || t(lang, `kind_${entry.kind}`), detail), time);
  }
  if (entry.kind === "url") {
    const url = entry.text.trim();
    return h("div", { class: "bubble" }, fileChip("url", domainOf(url), url), time);
  }
  const text = h("div", { class: "bubble-text" }, entry.text);
  const bubble = h("div", { class: "bubble" }, text, time);
  if (entry.text.length > LONG_BUBBLE_CHARS) {
    text.classList.add("is-clamped");
    const more = h("button", { class: "bubble-more", type: "button" }, t(lang, "more"));
    more.addEventListener("click", () => { text.classList.remove("is-clamped"); more.remove(); });
    time.before(more);
  }
  return bubble;
}

/* ---------- welcome and examples ---------- */

function renderWelcome() {
  document.querySelector(".welcome")?.remove();
  const lang = chromeLang();
  const kinds = ["text", "image", "audio", "pdf", "url"].map((kind) =>
    h("span", { class: "kind" }, icon(KIND_ICON[kind], 14), t(lang, `kind_${kind}`)));
  const cards = EXAMPLES.map((example) =>
    h("button", { class: "example", type: "button", onclick: () => runExample(example) },
      h("div", { class: "example-top" },
        h("span", { class: "example-icon" }, icon(KIND_ICON[example.kind], 17)),
        h("span", { class: "example-tag dotsep" }, h("span", {}, example.language), h("span", {}, t(lang, `kind_${example.kind}`)))),
      h("div", { class: "example-title" }, t(lang, `ex_${example.id}`)),
      h("div", { class: "example-preview" }, example.preview || example.text)));
  const welcome = h("div", { class: "welcome", lang },
    h("div", { class: "msg in" }, h("div", { class: "bubble" }, t(lang, "welcome1"))),
    h("div", { class: "msg in" }, h("div", { class: "bubble" }, t(lang, "welcome2"), h("div", { class: "kinds" }, kinds))),
    h("div", { class: "examples-title" }, t(lang, "tryExamples")),
    h("div", { class: "examples" }, cards));
  messages.prepend(welcome);
}

async function runExample(example) {
  if (busy) return;
  if (!example.asset) return submit({ text: example.text });
  try {
    const response = await fetch(example.asset);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    submit({ file: new File([blob], example.asset.split("/").pop(), { type: blob.type }) });
  } catch (err) {
    toast(`${t(chromeLang(), "error")} (${err.message})`);
  }
}

/* ---------- checking a message ---------- */

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
  micBtn.disabled = value;
  for (const button of document.querySelectorAll(".example")) button.disabled = value;
}

function remember(entry, result) {
  const saved = { ...result, input_text: (result.input_text || "").slice(0, HISTORY_TEXT_CHARS) };
  history.push({ kind: entry.kind, text: entry.text || "", name: entry.name || "", when: Date.now(), result: saved });
  history = history.slice(-HISTORY_MAX);
  store.write(HISTORY_KEY, history);
}

const cardActions = { onShare: openShare };

async function submit({ text, file }) {
  if (busy) return;
  const kind = file ? fileKind(file) : isLink(text) ? "url" : "text";
  const entry = { kind, text, file, name: file?.name };
  const lang = chromeLang();

  const sent = addMessage("out", userBubble(entry, new Date()));
  const progress = createProgress(lang, kind === "url" ? "link" : kind);
  const reply = addMessage("in", progress.el);
  scrollToEnd();
  setBusy(true);

  let outcome = null;
  try {
    await streamCheck({ text, file, replyLanguage: languageSetting }, (event) => {
      if (event.type === "result" || event.type === "error") {
        outcome = event;
        return;
      }
      const follow = nearEnd();
      progress.handle(event);
      if (follow) scrollToEnd();
    });
  } catch (err) {
    outcome = { type: "error", code: "network", message: err.message };
  }
  progress.stop();
  setBusy(false);

  if (outcome.type === "result") {
    const card = createResultCard(outcome.result, cardActions);
    card.classList.add("reveal");
    reply.replaceChildren(card);
    remember(entry, outcome.result);
    // Bring the verdict into view; a tall card would otherwise open scrolled to its bottom.
    reply.scrollIntoView({ block: "start", behavior: "smooth" });
  } else {
    const retry = () => {
      sent.remove();
      reply.remove();
      submit({ text, file });
    };
    reply.replaceChildren(createErrorCard(String(outcome.message || "").slice(0, 240), lang, retry));
    scrollToEnd();
  }
}

/* ---------- composer ---------- */

function refreshComposer() {
  const ready = Boolean(attachment) || input.value.trim().length > 0;
  sendBtn.hidden = !ready;
  micBtn.hidden = ready;
  input.disabled = Boolean(attachment);
}

function autosize() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
}

function setAttachment(file) {
  attachment = file;
  attachmentTray.replaceChildren();
  attachmentTray.hidden = !file;
  if (file) {
    const kind = fileKind(file);
    const lang = chromeLang();
    attachmentTray.append(
      kind === "image" ? h("img", { src: URL.createObjectURL(file), alt: "" }) : null,
      fileChip(kind, file.name, `${t(lang, `kind_${kind}`)}, ${formatSize(file.size)}`),
      h("button", { class: "icon-btn", type: "button", "aria-label": t(lang, "cancel"), onclick: () => setAttachment(null) }, icon("x", 18)));
    // The thumbnail already says "image"; the generic file icon beside it would be noise.
    if (kind === "image") attachmentTray.querySelector(".filechip-icon").hidden = true;
  }
  refreshComposer();
  if (file) sendBtn.focus();
}

function sendFromComposer() {
  if (busy) return;
  if (attachment) {
    const file = attachment;
    setAttachment(null);
    return submit({ file });
  }
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  autosize();
  refreshComposer();
  submit({ text });
}

function wireComposer() {
  $("attach").append(icon("clip", 20));
  micBtn.append(icon("mic", 22));
  sendBtn.append(icon("send", 20));
  $("record-cancel").append(icon("trash", 20));
  $("record-send").append(icon("send", 20));

  input.addEventListener("input", () => { autosize(); refreshComposer(); });
  input.addEventListener("keydown", (event) => {
    // Enter sends on a keyboard; on a touch screen it adds a line, as chat apps do.
    const desktop = window.matchMedia("(pointer: fine)").matches;
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing && desktop) {
      event.preventDefault();
      sendFromComposer();
    }
  });
  input.addEventListener("paste", (event) => {
    const file = [...(event.clipboardData?.files || [])][0];
    if (file) {
      event.preventDefault();
      setAttachment(file);
    }
  });
  sendBtn.addEventListener("click", sendFromComposer);
  $("attach").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setAttachment(fileInput.files[0]);
    fileInput.value = "";
  });

  const chat = document.querySelector(".chat");
  const dropHint = $("drop-hint");
  let dragDepth = 0;
  chat.addEventListener("dragenter", (event) => {
    if (![...(event.dataTransfer?.types || [])].includes("Files")) return;
    dragDepth += 1;
    dropHint.hidden = false;
  });
  chat.addEventListener("dragleave", () => {
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) dropHint.hidden = true;
  });
  chat.addEventListener("dragover", (event) => event.preventDefault());
  chat.addEventListener("drop", (event) => {
    event.preventDefault();
    dragDepth = 0;
    dropHint.hidden = true;
    const file = event.dataTransfer?.files?.[0];
    if (file) setAttachment(file);
  });
}

/* ---------- voice recording ---------- */

function wireRecorder() {
  const composeRow = $("compose-row");
  const recordRow = $("record-row");
  const wave = $("record-wave");
  const clock = $("record-time");
  let started = 0;
  let ticker = 0;

  const close = () => {
    clearInterval(ticker);
    recording = null;
    recordRow.hidden = true;
    composeRow.hidden = false;
    wave.replaceChildren();
  };

  micBtn.addEventListener("click", async () => {
    if (busy || recording) return;
    let lastBar = 0;
    try {
      recording = await startRecording((level) => {
        const now = performance.now();
        if (now - lastBar < 70) return;
        lastBar = now;
        wave.append(h("i", { style: { height: `${Math.round(3 + Math.min(1, level * 2.2) * 25)}px` } }));
        while (wave.children.length > WAVE_BARS) wave.firstChild.remove();
      });
    } catch {
      return toast(t(chromeLang(), "micDenied"));
    }
    started = Date.now();
    clock.textContent = "0:00";
    ticker = setInterval(() => { clock.textContent = formatClock((Date.now() - started) / 1000); }, 500);
    composeRow.hidden = true;
    recordRow.hidden = false;
    $("record-send").focus();
  });

  $("record-cancel").addEventListener("click", () => {
    recording?.cancel();
    close();
  });

  $("record-send").addEventListener("click", async () => {
    if (!recording) return;
    const active = recording;
    close();
    try {
      submit({ file: await active.stop() });
    } catch (err) {
      toast(`${t(chromeLang(), "error")} (${err.message})`);
    }
  });
}

/* ---------- share card ---------- */

async function openShare(result, lang) {
  const dialog = $("share-dialog");
  const canvas = $("share-canvas");
  applyStatic(lang, dialog);
  dialog.lang = uiLang(lang);
  $("share-download").replaceChildren(icon("download", 18), t(lang, "download"));
  $("share-send").replaceChildren(icon("share", 18), t(lang, "shareSend"));
  await drawShareCard(canvas, result, lang);
  const file = await canvasFile(canvas);

  $("share-send").hidden = !canShareFiles(file);
  $("share-send").onclick = async () => {
    try {
      await navigator.share({ files: [file], text: plainText(result, lang) });
    } catch { /* the user closed the share sheet */ }
  };
  $("share-download").onclick = () => {
    const link = h("a", { href: URL.createObjectURL(file), download: file.name });
    link.click();
    URL.revokeObjectURL(link.href);
  };
  dialog.showModal();
}

/* ---------- page chrome ---------- */

function renderMeta() {
  const lang = chromeLang();
  const stats = $("source-stats");
  stats.replaceChildren();
  $("powered").textContent = "";
  if (!meta) return;
  for (const tier of ["official", "fact_checker", "news"]) {
    stats.append(h("div", { class: "stat" }, h("b", {}, meta.sources[tier] ?? 0), h("span", {}, t(lang, `tiers_${tier}`))));
  }
  $("powered").textContent = t(lang, "poweredBy", modelName(meta.model));
}

function renderChrome() {
  const lang = chromeLang();
  applyStatic(lang);
  langSelect.options[0].textContent = t(lang, "langAuto");
  $("legend").replaceChildren(...VERDICTS.map((verdict) => {
    const style = verdictStyle(verdict);
    return h("li", {},
      h("span", { class: `legend-icon ${style.cls}` }, icon(style.icon, 15)),
      h("div", {}, h("strong", {}, t(lang, `v_${verdict}`)), h("p", {}, t(lang, `d_${verdict}`))));
  }));
  renderMeta();
  if (document.querySelector(".welcome")) renderWelcome();
}

function restoreHistory() {
  for (const item of history) {
    addMessage("out", userBubble(item, new Date(item.when)));
    addMessage("in", createResultCard(item.result, cardActions));
  }
}

function wireChrome() {
  $("lang-icon").append(icon("globe", 17));
  $("clear").append(icon("trash", 19));
  $("about-open").append(icon("info", 21));
  $("about-close").append(icon("x", 22));
  $("share-close").append(icon("x", 20));

  langSelect.value = languageSetting;
  langSelect.addEventListener("change", () => {
    languageSetting = langSelect.value;
    store.write("fc.lang", languageSetting);
    renderChrome();
  });
  $("clear").addEventListener("click", () => {
    if (busy) return;
    history = [];
    store.write(HISTORY_KEY, history);
    messages.replaceChildren();
    renderWelcome();
  });
  $("about-open").addEventListener("click", () => document.body.classList.add("about-on"));
  $("about-close").addEventListener("click", () => document.body.classList.remove("about-on"));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") document.body.classList.remove("about-on");
  });
  $("share-close").addEventListener("click", () => $("share-dialog").close());
  $("share-dialog").addEventListener("click", (event) => {
    if (event.target === $("share-dialog")) $("share-dialog").close();  // a click on the backdrop
  });
}

wireChrome();
wireComposer();
wireRecorder();
renderWelcome();
renderChrome();
restoreHistory();
refreshComposer();
scrollToEnd();
fetchMeta().then((data) => { meta = data; renderMeta(); }).catch(() => { /* the panel just shows no numbers */ });
