<script setup lang="ts">
import type { AudioSource, LabelItem, LabelStatus } from "~/types/speech";

type ItemsResponse = {
  items: LabelItem[];
  counts: Record<LabelStatus | "total", number>;
};

const sourceOptions = [
  { label: "Alle Quellen", value: "all" },
  { label: "App-Aufnahmen", value: "app_recording" },
  { label: "WhatsApp", value: "whatsapp_upload" },
];
const statusOptions = [
  { label: "Entwürfe", value: "draft" },
  { label: "Gelabelt", value: "labeled" },
  { label: "Übersprungen", value: "skipped" },
  { label: "Alle", value: "all" },
];

const audio = ref<HTMLAudioElement>();
const files = ref<File[] | null>(null);
const currentIndex = ref(0);
const targetSender = ref("");
const sourceFilter = ref<AudioSource | "all">("all");
const statusFilter = ref<LabelStatus | "all">("draft");
const unsureOnly = ref(false);
const transcript = ref("");
const notes = ref("");
const unsure = ref(false);
const isBusy = ref(false);
const isSaving = ref(false);

const emptyCounts: Record<LabelStatus | "total", number> = {
  draft: 0,
  labeled: 0,
  skipped: 0,
  total: 0,
};

const itemsQuery = computed(() => ({
  ...(sourceFilter.value !== "all" ? { source: sourceFilter.value } : {}),
  ...(statusFilter.value !== "all" ? { status: statusFilter.value } : {}),
  ...(unsureOnly.value ? { unsure: true } : {}),
}));

const {
  data: itemsData,
  error: itemsError,
  refresh: refreshItems,
} = await useFetch<ItemsResponse>("/api/labeling/items", {
  query: itemsQuery,
  default: () => ({ items: [], counts: emptyCounts }),
});

const items = computed(() => itemsData.value.items);
const counts = computed(() => itemsData.value.counts);
const current = computed(() => items.value[currentIndex.value]);
const audioUrl = computed(() =>
  current.value ? `/api/labeling/audio/${current.value.audio_id}` : "",
);

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeydown);
});

watch(
  current,
  (item) => {
    transcript.value = item?.transcript || item?.asr_text || "";
    notes.value = item?.notes || "";
    unsure.value = Boolean(item?.unsure);
  },
  { immediate: true },
);

watch([sourceFilter, statusFilter, unsureOnly], () => {
  currentIndex.value = 0;
});

watch(items, (nextItems) => {
  if (currentIndex.value >= nextItems.length) currentIndex.value = 0;
});

async function importFiles() {
  if (!files.value?.length || isBusy.value) return;
  isBusy.value = true;
  const form = new FormData();
  files.value.forEach((file) => form.append("files", file));
  form.append("target_sender", targetSender.value.trim());
  try {
    const response = await $fetch<ItemsResponse & { imported: number }>(
      "/api/labeling/import",
      { method: "POST", body: form },
    );
    files.value = null;
    await refreshItems();
  } catch {
  } finally {
    isBusy.value = false;
  }
}

async function save(nextStatus: LabelStatus) {
  if (!current.value || isSaving.value) return;
  isSaving.value = true;
  const form = new FormData();
  form.append("transcript", transcript.value.trim());
  form.append("status", nextStatus);
  form.append("unsure", String(unsure.value));
  form.append("notes", notes.value.trim());
  try {
    await $fetch(`/api/labeling/items/${current.value.audio_id}`, {
      method: "PATCH",
      body: form,
    });
    await refreshItems();
    if (currentIndex.value < items.value.length - 1) currentIndex.value += 1;
    else currentIndex.value = 0;
  } finally {
    isSaving.value = false;
  }
}

function moveCurrent(delta: number) {
  if (!items.value.length) return;
  currentIndex.value =
    (currentIndex.value + delta + items.value.length) % items.value.length;
}

function handleKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement;
  const isTyping = ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
    event.preventDefault();
    void save("labeled");
  } else if (event.key === "Escape") {
    unsure.value = !unsure.value;
  } else if (event.code === "Space" && !isTyping && audio.value) {
    event.preventDefault();
    if (audio.value.paused) void audio.value.play();
    else audio.value.pause();
  }
}
</script>

<template>
  <UMain class="min-h-dvh bg-default px-4 py-5 text-highlighted">
    <UContainer class="max-w-3xl space-y-5">
      <div class="flex items-center justify-between gap-3">
        <UButton
          class="min-h-12 font-extrabold"
          color="neutral"
          icon="i-lucide-arrow-left"
          size="lg"
          to="/"
          variant="ghost"
        >
          Zurück
        </UButton>
        <UButton
          class="min-h-12 font-extrabold"
          color="primary"
          icon="i-lucide-download"
          size="lg"
          to="/api/labeling/export.csv"
        >
          CSV
        </UButton>
      </div>

      <header>
        <p class="text-sm font-semibold text-muted">Audio-Labels</p>
        <h1 class="mt-1 text-3xl font-bold tracking-normal">
          Aufnahmen prüfen
        </h1>
      </header>

      <section class="space-y-3">
        <UFileUpload
          v-model="files"
          accept="audio/*,.zip,application/zip"
          class="min-h-48"
          description="WhatsApp-Export-ZIP oder einzelne Audiodateien"
          label="ZIP oder Audios hier ablegen"
          layout="list"
          multiple
          position="inside"
          size="lg"
        />
        <UFormField label="Name der sprechenden Person im WhatsApp-Chat">
          <UInput
            v-model="targetSender"
            class="w-full"
            placeholder="Leer lassen, um alle Audios zu importieren"
            size="lg"
          />
        </UFormField>
        <UButton
          block
          class="min-h-14 justify-center font-extrabold"
          color="primary"
          icon="i-lucide-upload"
          size="lg"
          :loading="isBusy"
          @click="importFiles"
        >
          WhatsApp-Audios importieren
        </UButton>
      </section>

      <section class="grid gap-3 sm:grid-cols-3">
        <UFormField label="Quelle">
          <USelect
            v-model="sourceFilter"
            class="w-full"
            :items="sourceOptions"
            size="lg"
          />
        </UFormField>
        <UFormField label="Status">
          <USelect
            v-model="statusFilter"
            class="w-full"
            :items="statusOptions"
            size="lg"
          />
        </UFormField>
        <UCheckbox
          v-model="unsureOnly"
          class="min-h-16 items-center"
          label="Nur unsichere"
          size="lg"
        />
      </section>

      <p class="text-sm font-semibold text-muted">
        {{ counts.draft }} offen · {{ counts.labeled }} gelabelt ·
        {{ counts.skipped }} übersprungen
      </p>

      <section v-if="current" class="space-y-4">
        <div
          class="flex flex-wrap items-center gap-2 text-sm font-semibold text-muted"
        >
          <span class="rounded-md bg-muted px-2 py-1">{{
            current.source
          }}</span>
          <span>{{ current.original_filename || current.audio_file }}</span>
        </div>

        <audio ref="audio" class="w-full" controls :src="audioUrl" />

        <div>
          <p class="text-sm font-semibold text-muted">ASR-Entwurf</p>
          <p
            class="mt-1 min-h-12 rounded-lg border border-default bg-muted p-3 text-lg"
          >
            {{ current.asr_text || "Kein ASR-Entwurf." }}
          </p>
        </div>

        <UFormField label="Korrigierte Transkription">
          <LazyUTextarea
            v-model="transcript"
            class="w-full"
            autofocus
            autoresize
            size="xl"
            :rows="5"
          />
        </UFormField>

        <UCheckbox v-model="unsure" label="Unsicher" />

        <UFormField label="Notizen">
          <LazyUTextarea
            v-model="notes"
            class="w-full"
            autoresize
            size="lg"
            :rows="3"
          />
        </UFormField>

        <div class="grid gap-3 grid-cols-3">
          <UButton
            block
            class="font-extrabold"
            color="neutral"
            icon="i-lucide-chevron-left"
            size="lg"
            variant="ghost"
            :disabled="items.length < 2"
            @click="moveCurrent(-1)"
          >
            Zurück
          </UButton>
          <p
            class="flex items-center justify-center text-sm font-semibold text-muted"
          >
            {{ currentIndex + 1 }} / {{ items.length }}
          </p>
          <UButton
            block
            class="font-extrabold"
            color="neutral"
            icon="i-lucide-chevron-right"
            size="lg"
            variant="ghost"
            :disabled="items.length < 2"
            @click="moveCurrent(1)"
          >
            Weiter
          </UButton>
        </div>

        <div class="grid gap-3 sm:grid-cols-3">
          <UButton
            block
            class="min-h-14 justify-center font-extrabold"
            color="neutral"
            icon="i-lucide-skip-forward"
            size="lg"
            variant="subtle"
            :loading="isSaving"
            @click="save('skipped')"
          >
            Skip
          </UButton>
          <UButton
            block
            class="min-h-14 justify-center font-extrabold"
            color="neutral"
            icon="i-lucide-save"
            size="lg"
            variant="outline"
            :loading="isSaving"
            @click="save('draft')"
          >
            Entwurf
          </UButton>
          <UButton
            block
            class="min-h-14 justify-center font-extrabold"
            color="primary"
            icon="i-lucide-check"
            size="lg"
            :loading="isSaving"
            @click="save('labeled')"
          >
            Gelabelt + weiter
          </UButton>
        </div>
      </section>

      <p
        v-else
        class="rounded-lg border border-default p-5 text-center text-lg font-semibold text-muted"
      >
        Keine Aufnahme in dieser Ansicht.
      </p>
    </UContainer>
  </UMain>
</template>
