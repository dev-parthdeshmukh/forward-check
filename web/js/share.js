// Draws the correction as a picture the user can send back to the group the forward came from.
import { t, formatDate, localDay } from "./i18n.js";

const W = 1080;
const H = 1350;
const PAD = 72;
const FONT = '"Anek Devanagari", "Nirmala UI", "Segoe UI", sans-serif';
const COLORS = {
  VERIFIED: { main: "#177a43", bg: "#e4f4ea", ink: "#0e5630" },
  FALSE: { main: "#c5302b", bg: "#fdebe8", ink: "#8c1d19" },
  OUTDATED: { main: "#6a41c9", bg: "#efe9fb", ink: "#47288f" },
  PARTLY_SUPPORTED: { main: "#b5600a", bg: "#fcefd9", ink: "#7b3f04" },
  UNVERIFIABLE: { main: "#586470", bg: "#eaeef1", ink: "#38434d" },
};

function wrap(ctx, text, maxWidth, maxLines) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const word of words) {
    const trial = line ? `${line} ${word}` : word;
    if (ctx.measureText(trial).width <= maxWidth || !line) {
      line = trial;
    } else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  if (lines.length <= maxLines) return lines;
  const kept = lines.slice(0, maxLines);
  let last = kept[maxLines - 1];
  while (last && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1);
  kept[maxLines - 1] = `${last.trimEnd()}…`;
  return kept;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

function glyph(ctx, verdict, cx, cy, size) {
  ctx.save();
  ctx.strokeStyle = "#fff";
  ctx.fillStyle = "#fff";
  ctx.lineWidth = size * 0.16;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  const u = size / 2;
  ctx.beginPath();
  if (verdict === "VERIFIED") {
    ctx.moveTo(cx - u * 0.75, cy + u * 0.05); ctx.lineTo(cx - u * 0.2, cy + u * 0.6); ctx.lineTo(cx + u * 0.8, cy - u * 0.55);
    ctx.stroke();
  } else if (verdict === "FALSE") {
    ctx.moveTo(cx - u * 0.6, cy - u * 0.6); ctx.lineTo(cx + u * 0.6, cy + u * 0.6);
    ctx.moveTo(cx + u * 0.6, cy - u * 0.6); ctx.lineTo(cx - u * 0.6, cy + u * 0.6);
    ctx.stroke();
  } else if (verdict === "OUTDATED") {
    ctx.arc(cx, cy, u * 0.85, 0, Math.PI * 2);
    ctx.moveTo(cx, cy - u * 0.45); ctx.lineTo(cx, cy); ctx.lineTo(cx + u * 0.35, cy + u * 0.22);
    ctx.stroke();
  } else if (verdict === "PARTLY_SUPPORTED") {
    ctx.arc(cx, cy, u * 0.85, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, u * 0.85, Math.PI / 2, Math.PI * 1.5);
    ctx.fill();
  } else {
    ctx.font = `800 ${size * 1.15}px ${FONT}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("?", cx, cy + size * 0.06);
  }
  ctx.restore();
}

function label(ctx, text, x, y) {
  ctx.fillStyle = "#677572";
  ctx.font = `700 26px ${FONT}`;
  ctx.fillText(text.toUpperCase(), x, y);
  return y + 46;
}

function paragraph(ctx, text, x, y, width, { size, weight = 500, color = "#14211f", maxLines, leading = 1.42 }) {
  ctx.fillStyle = color;
  ctx.font = `${weight} ${size}px ${FONT}`;
  for (const line of wrap(ctx, text, width, maxLines)) {
    ctx.fillText(line, x, y);
    y += size * leading;
  }
  return y;
}

export async function drawShareCard(canvas, result, lang) {
  await document.fonts.ready;
  const ctx = canvas.getContext("2d");
  const width = W - PAD * 2;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";

  ctx.fillStyle = "#f3eee4";
  ctx.fillRect(0, 0, W, H);

  // Brand bar
  ctx.fillStyle = "#0c3f40";
  ctx.fillRect(0, 0, W, 132);
  roundRect(ctx, PAD, 36, 60, 60, 16);
  ctx.fillStyle = "#125456";
  ctx.fill();
  ctx.lineWidth = 6;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#fff";
  ctx.beginPath();
  ctx.moveTo(PAD + 14, 68); ctx.lineTo(PAD + 24, 78); ctx.lineTo(PAD + 45, 54);
  ctx.stroke();
  ctx.strokeStyle = "#8ce5cb";
  ctx.beginPath();
  ctx.moveTo(PAD + 32, 54); ctx.lineTo(PAD + 45, 54); ctx.lineTo(PAD + 45, 67);
  ctx.stroke();
  ctx.fillStyle = "#fff";
  ctx.font = `700 40px ${FONT}`;
  ctx.fillText("Forward Check", PAD + 82, 80);
  ctx.textAlign = "right";
  ctx.fillStyle = "#b9e0da";
  ctx.font = `500 28px ${FONT}`;
  ctx.fillText(t(lang, "tagline"), W - PAD, 78);
  ctx.textAlign = "left";

  // A short answer would leave the bottom of the card empty, so the body is measured on a
  // scratch canvas first and then drawn centred between the brand bar and the footer.
  const bodyTop = 184;
  const footerTop = H - 150;
  const scratch = document.createElement("canvas").getContext("2d");
  const used = drawBody(scratch, result, lang, bodyTop, footerTop) - bodyTop;
  const slack = Math.max(0, footerTop - 40 - bodyTop - used);
  drawBody(ctx, result, lang, bodyTop + Math.min(slack / 2, 150), footerTop);

  // Footer
  ctx.fillStyle = "#e6dfd1";
  ctx.fillRect(PAD, footerTop, width, 2);
  const when = formatDate(localDay(result.checked_at ? new Date(result.checked_at) : new Date()), lang);
  ctx.fillStyle = "#677572";
  ctx.font = `500 28px ${FONT}`;
  ctx.fillText(t(lang, "sc_checked", when), PAD, footerTop + 64);
  ctx.textAlign = "right";
  ctx.fillStyle = "#0c3f40";
  ctx.font = `700 30px ${FONT}`;
  ctx.fillText(t(lang, "sc_footer"), W - PAD, footerTop + 64);
  ctx.textAlign = "left";
}

// The verdict, what was said, what is true and the sources. Returns the y where it ended.
function drawBody(ctx, result, lang, top, footerTop) {
  const verdict = result.overall_verdict;
  const color = COLORS[verdict] || COLORS.UNVERIFIABLE;
  const width = W - PAD * 2;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";

  let y = top;
  roundRect(ctx, PAD, y, width, 196, 36);
  ctx.fillStyle = color.bg;
  ctx.fill();
  ctx.beginPath();
  ctx.arc(PAD + 98, y + 98, 58, 0, Math.PI * 2);
  ctx.fillStyle = color.main;
  ctx.fill();
  glyph(ctx, verdict, PAD + 98, y + 98, 62);
  ctx.fillStyle = color.ink;
  const verdictText = t(lang, `v_${verdict}`);
  let size = 92;
  ctx.font = `800 ${size}px ${FONT}`;
  while (ctx.measureText(verdictText).width > width - 220 && size > 48) {
    size -= 4;
    ctx.font = `800 ${size}px ${FONT}`;
  }
  ctx.fillText(verdictText, PAD + 186, y + 98 + size * 0.34);
  y += 196 + 56;

  const single = result.claims.length === 1 ? result.claims[0] : null;

  if (single) {
    y = label(ctx, t(lang, "sc_said"), PAD, y);
    const quoteTop = y - 36;
    const quoteEnd = paragraph(ctx, `“${single.claim.original_span || single.claim.text}”`, PAD + 30, y, width - 30,
      { size: 36, weight: 400, color: "#3b4a47", maxLines: 4 });
    ctx.fillStyle = color.main;
    roundRect(ctx, PAD, quoteTop, 6, quoteEnd - quoteTop - 20, 3);
    ctx.fill();
    y = quoteEnd + 36;

    const truth = single.correct_information || single.explanation;
    const heading = single.correct_information ? t(lang, "whatTrue") : t(lang, `v_${verdict}`);
    y = label(ctx, heading, PAD, y);
    y = paragraph(ctx, truth, PAD, y, width, { size: 42, weight: 600, maxLines: 6 }) + 30;
  } else {
    // Up to three claims, two lines each, which leaves room for the sources underneath.
    for (const item of result.claims.slice(0, 3)) {
      const c = COLORS[item.verdict] || COLORS.UNVERIFIABLE;
      const chip = t(lang, `v_${item.verdict}`);
      ctx.font = `700 30px ${FONT}`;
      const chipWidth = ctx.measureText(chip).width + 44;
      roundRect(ctx, PAD, y - 38, chipWidth, 54, 27);
      ctx.fillStyle = c.bg;
      ctx.fill();
      ctx.fillStyle = c.ink;
      ctx.fillText(chip, PAD + 22, y);
      y += 58;
      const line = item.what_is_wrong || item.correct_information || item.explanation || item.claim.text;
      y = paragraph(ctx, line, PAD, y, width, { size: 36, weight: 500, maxLines: 2 }) + 30;
    }
  }

  // Sources, as far as there is room above the footer
  const seen = new Set();
  const names = [];
  for (const item of result.claims) {
    for (const ev of item.evidence) {
      if (ev.tier === "other" || seen.has(ev.source_name)) continue;
      seen.add(ev.source_name);
      names.push(ev.source_name);
    }
  }
  if (names.length && y + 100 < footerTop) {
    y = label(ctx, t(lang, "sc_sources"), PAD, y);
    const lines = Math.max(1, Math.min(2, Math.floor((footerTop - y) / 46)));
    y = paragraph(ctx, names.slice(0, 4).join(", "), PAD, y, width, { size: 32, weight: 500, color: "#3b4a47", maxLines: lines });
  }
  return y;
}

export function canvasFile(canvas) {
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(new File([blob], "forward-check.png", { type: "image/png" })), "image/png");
  });
}

export function canShareFiles(file) {
  return Boolean(navigator.canShare && navigator.canShare({ files: [file] }));
}
