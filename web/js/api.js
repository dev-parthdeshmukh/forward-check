// Run a check and hand each progress event to onEvent as it arrives.
// Resolves when the stream ends; the last event is {type: "result"} or {type: "error"}.
export async function streamCheck({ text, url, file, replyLanguage }, onEvent) {
  const body = new FormData();
  if (text) body.append("text", text);
  if (url) body.append("url", url);
  if (file) body.append("file", file, file.name || "upload");
  if (replyLanguage && replyLanguage !== "auto") body.append("reply_language", replyLanguage);

  const response = await fetch("check/stream", { method: "POST", body });
  if (!response.ok || !response.body) {
    let message = `HTTP ${response.status}`;
    try {
      message = (await response.json()).detail || message;
    } catch { /* not JSON; keep the status */ }
    throw new Error(message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;
  const handle = (line) => {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === "result" || event.type === "error") finished = true;
    if (event.type !== "ping") onEvent(event);
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      handle(buffer.slice(0, newline));
      buffer = buffer.slice(newline + 1);
    }
  }
  handle(buffer);
  if (!finished) throw new Error("The connection closed before the check finished.");
}

export async function fetchSpeech(text, languageCode) {
  const response = await fetch("tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, language_code: languageCode }),
  });
  if (!response.ok) throw new Error(`Speech failed: HTTP ${response.status}`);
  return response.blob();
}

export async function fetchMeta() {
  const response = await fetch("meta");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
