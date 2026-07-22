let recorder;
let chunks = [];
let lastResult;
let phrases = [];
let selectedCandidate;

const recordButton = document.querySelector("#record");
const stopButton = document.querySelector("#stop");
const speakButton = document.querySelector("#speak");
const saveButton = document.querySelector("#save");
const upload = document.querySelector("#upload");
const phrase = document.querySelector("#phrase");
const raw = document.querySelector("#raw");
const suggestionsSection = document.querySelector("#suggestionsSection");
const suggestions = document.querySelector("#suggestions");
const target = document.querySelector("#target");
const status = document.querySelector("#status");
const speechAttempts = document.querySelector("#speechAttempts");
const total = document.querySelector("#total");
const exactRate = document.querySelector("#exactRate");
const topRate = document.querySelector("#topRate");

function setStatus(message) {
  status.textContent = message;
}

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function clearAttempt() {
  lastResult = undefined;
  selectedCandidate = undefined;
  upload.value = "";
  raw.value = "";
  suggestions.replaceChildren();
  suggestionsSection.hidden = true;
  saveButton.disabled = true;
  speakButton.disabled = true;
  setStatus("");
}

recordButton.addEventListener("click", async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
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
  recordButton.disabled = true;
  stopButton.disabled = true;
  saveButton.disabled = true;
  speakButton.disabled = true;
  setStatus("Upload wird erkannt...");
  await transcribe(file, file.name);
});

speakButton.addEventListener("click", () => {
  const text = target.value.trim() || raw.value.trim();
  if (!text) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "de-DE";
  speechSynthesis.speak(utterance);
});

saveButton.addEventListener("click", async () => {
  const form = new FormData();
  form.append("transcript", target.value);
  form.append("status", "draft");
  form.append("unsure", "false");
  form.append("notes", "Provisional app selection.");

  const response = await fetch(`/api/labeling/items/${lastResult.audio_id}`, { method: "PATCH", body: form });
  if (!response.ok) {
    setStatus("Korrektur konnte nicht gespeichert werden.");
    return;
  }
  setStatus("Gespeichert.");
  await loadSpeechAttempts();
  await loadAnalysis();
});

phrase.addEventListener("change", () => {
  clearAttempt();
  selectedCandidate = phrase.selectedOptions[0]?.dataset.id
    ? { id: `phrase:${phrase.selectedOptions[0].dataset.id}`, source: "phrase", text: phrase.value, score: 1 }
    : undefined;
  target.value = phrase.value;
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
    renderSuggestions(lastResult.suggestions || []);
    if (phrase.value) {
      target.value = phrase.value;
    } else if (lastResult.suggestions?.[0]?.score >= 0.8) {
      selectCandidate(lastResult.suggestions[0]);
    } else {
      target.value = lastResult.raw_transcript;
    }
    saveButton.disabled = false;
    speakButton.disabled = false;
    setStatus(`Audio gespeichert als ${lastResult.audio_path}`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    recordButton.disabled = false;
  }
}

function selectCandidate(candidate) {
  selectedCandidate = candidate;
  target.value = candidate.text;
  if (candidate.source === "phrase") {
    const phraseId = Number(candidate.id.replace("phrase:", ""));
    phrase.selectedIndex = phrases.findIndex((item) => item.id === phraseId) + 1;
  }
}

function renderSuggestions(items) {
  suggestionsSection.hidden = items.length === 0;
  suggestions.replaceChildren(
    ...items.map((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "suggestion";
      button.textContent = `${Math.round(item.score * 100)}% - ${item.text}`;
      button.addEventListener("click", () => selectCandidate(item));
      return button;
    }),
  );
}

async function loadPhrases() {
  const response = await fetch("/api/phrases");
  if (!response.ok) return;
  phrases = await response.json();
  phrases.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.text || "";
    option.dataset.id = item.id;
    option.textContent = item.text;
    phrase.append(option);
  });
}

async function loadSpeechAttempts() {
  const response = await fetch("/api/labeling/items?limit=50");
  if (!response.ok) return;
  const body = await response.json();
  const rows = body.items || [];
  speechAttempts.replaceChildren(
    ...rows.map((row) => {
      const tr = document.createElement("tr");
      for (const value of [
        row.asr_text || "",
        row.transcript || "",
        row.status || "",
      ]) {
        const td = document.createElement("td");
        td.textContent = value;
        tr.append(td);
      }
      return tr;
    }),
  );
}

async function loadAnalysis() {
  const response = await fetch("/api/labeling/items?limit=1");
  if (!response.ok) return;
  const body = await response.json();
  total.textContent = body.counts.total;
  exactRate.textContent = body.counts.labeled;
  topRate.textContent = body.counts.draft;
}

loadPhrases();
loadSpeechAttempts();
loadAnalysis();
