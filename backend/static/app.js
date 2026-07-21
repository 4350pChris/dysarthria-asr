let recorder;
let chunks = [];
let lastResult;
let source = "browser_recording";
let phrases = [];

const recordButton = document.querySelector("#record");
const stopButton = document.querySelector("#stop");
const speakButton = document.querySelector("#speak");
const saveButton = document.querySelector("#save");
const upload = document.querySelector("#upload");
const phrase = document.querySelector("#phrase");
const expected = document.querySelector("#expected");
const raw = document.querySelector("#raw");
const suggestionsSection = document.querySelector("#suggestionsSection");
const suggestions = document.querySelector("#suggestions");
const corrected = document.querySelector("#corrected");
const notes = document.querySelector("#notes");
const understandable = document.querySelector("#understandable");
const status = document.querySelector("#status");
const speechAttempts = document.querySelector("#speechAttempts");
const total = document.querySelector("#total");
const understandableRate = document.querySelector("#understandableRate");
const exactRate = document.querySelector("#exactRate");
const fuzzyRate = document.querySelector("#fuzzyRate");
const worstPhrases = document.querySelector("#worstPhrases");

function setStatus(message) {
  status.textContent = message;
}

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

function clearAttempt() {
  lastResult = undefined;
  upload.value = "";
  raw.value = "";
  suggestions.replaceChildren();
  suggestionsSection.hidden = true;
  notes.value = "";
  understandable.checked = false;
  saveButton.disabled = true;
  speakButton.disabled = true;
  setStatus("");
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
  const topSuggestion = lastResult.suggestions?.[0] || {};
  form.append("audio_id", lastResult.audio_id);
  form.append("source", source);
  form.append("phrase_id", phrase.selectedOptions[0]?.dataset.id || "");
  form.append("expected_text", expected.value);
  form.append("raw_transcript", raw.value);
  form.append("corrected_text", corrected.value);
  form.append("suggested_phrase_id", topSuggestion.phrase_id || "");
  form.append("suggested_text", topSuggestion.text || "");
  form.append("suggestion_score", topSuggestion.score || "");
  form.append("was_understandable", understandable.checked ? "true" : "false");
  form.append("notes", notes.value);

  const response = await fetch("/api/speech-attempts", { method: "POST", body: form });
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
  expected.value = phrase.value;
  corrected.value = phrase.value;
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
      corrected.value = phrase.value;
    } else if (lastResult.suggestions?.[0]?.score >= 0.8) {
      selectPhrase(lastResult.suggestions[0].phrase_id, lastResult.suggestions[0].text);
    } else {
      corrected.value = lastResult.raw_transcript;
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

function selectPhrase(id, text) {
  phrase.value = text;
  phrase.selectedIndex = phrases.findIndex((item) => item.id === id) + 1;
  expected.value = text;
  corrected.value = text;
}

function renderSuggestions(items) {
  suggestionsSection.hidden = items.length === 0;
  suggestions.replaceChildren(
    ...items.map((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "suggestion";
      button.textContent = `${item.phrase_id} ${Math.round(item.score * 100)}% - ${item.text}`;
      button.addEventListener("click", () => selectPhrase(item.phrase_id, item.text));
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
  const response = await fetch("/api/speech-attempts");
  if (!response.ok) return;
  const rows = await response.json();
  speechAttempts.replaceChildren(
    ...rows.map((row) => {
      const tr = document.createElement("tr");
      for (const value of [
        row.phrase_id || "",
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

async function loadAnalysis() {
  const response = await fetch("/api/analysis");
  if (!response.ok) return;
  const analysis = await response.json();
  total.textContent = analysis.total;
  understandableRate.textContent = percent(analysis.understandable_rate);
  exactRate.textContent = percent(analysis.exact_match_rate);
  fuzzyRate.textContent = percent(analysis.fuzzy_top_1_rate);
  worstPhrases.replaceChildren(
    ...analysis.worst_phrases.map((row) => {
      const tr = document.createElement("tr");
      for (const value of [
        row.phrase_id,
        row.expected_text,
        row.failures,
        row.attempts,
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
loadSpeechAttempts();
loadAnalysis();
