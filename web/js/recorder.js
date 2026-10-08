// Voice-note recording. Browsers record in different formats (WebM, Ogg, MP4), so the recording is
// converted to 16 kHz mono WAV before upload: one format the transcriber is sure to accept, and small.

const TARGET_RATE = 16000;

function wavFile(samples) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const ascii = (offset, text) => [...text].forEach((ch, i) => view.setUint8(offset + i, ch.charCodeAt(0)));
  ascii(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);            // PCM
  view.setUint16(22, 1, true);            // mono
  view.setUint32(24, TARGET_RATE, true);
  view.setUint32(28, TARGET_RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  ascii(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new File([buffer], "voice-note.wav", { type: "audio/wav" });
}

async function toWav(blob) {
  const context = new AudioContext();
  try {
    const decoded = await context.decodeAudioData(await blob.arrayBuffer());
    const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * TARGET_RATE), TARGET_RATE);
    const source = offline.createBufferSource();
    source.buffer = decoded;
    source.connect(offline.destination);
    source.start();
    return wavFile((await offline.startRendering()).getChannelData(0));
  } finally {
    context.close();
  }
}

// Starts recording. onLevel(0..1) is called many times a second with the input loudness.
// Returns { stop(): Promise<File>, cancel() }.
export async function startRecording(onLevel) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mime = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((m) => MediaRecorder.isTypeSupported(m));
  const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const chunks = [];
  recorder.addEventListener("dataavailable", (event) => { if (event.data.size) chunks.push(event.data); });

  const context = new AudioContext();
  const analyser = context.createAnalyser();
  analyser.fftSize = 256;
  context.createMediaStreamSource(stream).connect(analyser);
  const data = new Uint8Array(analyser.fftSize);
  let frame = 0;
  const meter = () => {
    analyser.getByteTimeDomainData(data);
    let peak = 0;
    for (const value of data) peak = Math.max(peak, Math.abs(value - 128) / 128);
    onLevel(peak);
    frame = requestAnimationFrame(meter);
  };
  meter();
  recorder.start();

  const release = () => {
    cancelAnimationFrame(frame);
    stream.getTracks().forEach((track) => track.stop());
    context.close();
  };

  return {
    stop() {
      return new Promise((resolve, reject) => {
        recorder.addEventListener("stop", async () => {
          release();
          const blob = new Blob(chunks, { type: recorder.mimeType });
          try {
            resolve(await toWav(blob));
          } catch {
            // Could not decode our own recording; send it as recorded and let the server try.
            const ext = recorder.mimeType.includes("ogg") ? "ogg" : recorder.mimeType.includes("mp4") ? "m4a" : "webm";
            if (blob.size) resolve(new File([blob], `voice-note.${ext}`, { type: recorder.mimeType }));
            else reject(new Error("Nothing was recorded."));
          }
        }, { once: true });
        recorder.stop();
      });
    },
    cancel() {
      recorder.addEventListener("stop", release, { once: true });
      recorder.stop();
    },
  };
}
