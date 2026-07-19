let recorder;
let chunks = [];
let lastResult;
let source = "browser_recording";

const recordButton = document.querySelector("#record");
const stopButton = document.querySelector("#stop");
const speakButton = document.querySelector("#speak");
const saveButton = document.querySelector("#save");
const upload = document.querySelector("#upload");
const phrase = document.querySelector("#phrase");
const expected = document.querySelector("#expected");
const raw = document.querySelector("#raw");
const corrected = document.querySelector("#corrected");
const notes = document.querySelector("#notes");
const understandable = document.querySelector("#understandable");
const status = document.querySelector("#status");
const corrections = document.querySelector("#corrections");

function setStatus(message) {
  status.textContent = message;
}

recordButton.addEventListener("click", async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  source = "browser_recording";
  recorder = new MediaRecorder(stream);
  recorder.ondataavailable = (event) => chunks.push(event.data);
  recorder.onstop = async () => {
    stream.getTracks().forEach((track) => track.stop());
    await transcribe(new Blob(chunks, { type: recorder.mimeType }));
  };
  recorder.start();
  recordButton.disabled = true;
  stopButton.disabled = false;
  saveButton.disabled = true;
  speakButton.disabled = true;
  setStatus("Aufnahme läuft...");
});

stopButton.addEventListener("click", () => {
  stopButton.disabled = true;
  recorder.stop();
  setStatus("Erkennung läuft...");
});

upload.addEventListener("change", async () => {
  const file = upload.files[0];
  if (!file) return;
  source = "uploaded_audio";
  recordButton.disabled = true;
  stopButton.disabled = true;
  saveButton.disabled = true;
  speakButton.disabled = true;
  setStatus("Upload wird erkannt...");
  await transcribe(file, file.name);
});

speakButton.addEventListener("click", () => {
  const text = corrected.value.trim() || raw.value.trim();
  if (!text) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "de-DE";
  speechSynthesis.speak(utterance);
});

saveButton.addEventListener("click", async () => {
  const form = new FormData();
  form.append("audio_id", lastResult.audio_id);
  form.append("audio_path", lastResult.audio_path);
  form.append("source", source);
  form.append("expected_text", expected.value);
  form.append("raw_transcript", raw.value);
  form.append("corrected_text", corrected.value);
  form.append("was_understandable", understandable.checked ? "true" : "false");
  form.append("notes", notes.value);

  const response = await fetch("/api/corrections", { method: "POST", body: form });
  if (!response.ok) {
    setStatus("Korrektur konnte nicht gespeichert werden.");
    return;
  }
  setStatus("Gespeichert.");
  await loadCorrections();
});

phrase.addEventListener("change", () => {
  expected.value = phrase.value;
  if (!corrected.value.trim()) corrected.value = phrase.value;
});

async function transcribe(blob, filename = "recording.webm") {
  const form = new FormData();
  form.append("audio", blob, filename);

  try {
    const response = await fetch("/api/transcribe", { method: "POST", body: form });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Transcription failed.");
    }
    lastResult = await response.json();
    raw.value = lastResult.raw_transcript;
    corrected.value = lastResult.raw_transcript;
    saveButton.disabled = false;
    speakButton.disabled = false;
    setStatus(`Audio gespeichert als ${lastResult.audio_path}`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    recordButton.disabled = false;
  }
}

async function loadPhrases() {
  const response = await fetch("/api/phrases");
  if (!response.ok) return;
  const phrases = await response.json();
  for (const item of phrases) {
    const option = document.createElement("option");
    option.value = item.text || "";
    option.textContent = item.category ? `${item.category}: ${item.text}` : item.text;
    phrase.append(option);
  }
}

async function loadCorrections() {
  const response = await fetch("/api/corrections");
  if (!response.ok) return;
  const rows = await response.json();
  corrections.replaceChildren(
    ...rows.map((row) => {
      const tr = document.createElement("tr");
      for (const value of [
        row.expected_text || "",
        row.raw_transcript || "",
        row.corrected_text || "",
        row.was_understandable ? "ja" : "nein",
      ]) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      }
      return tr;
    }),
  );
}

loadPhrases();
loadCorrections();
