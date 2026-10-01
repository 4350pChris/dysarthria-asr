type QueuedRecording = {
  id?: number
  audio: Blob
}

const DATABASE_NAME = 'speech-recording-uploads'
const STORE_NAME = 'recordings'

let isUploading = false

export async function enqueueRecording(audio: Blob) {
  await withStore('readwrite', store => store.add({ audio }))
}

export async function uploadPendingRecordings() {
  if (isUploading || typeof window === 'undefined') return

  isUploading = true
  try {
    const recordings = await withStore<QueuedRecording[]>(
      'readonly',
      store => store.getAll()
    )

    for (const recording of recordings) {
      const id = recording.id
      if (id === undefined) continue

      const form = new FormData()
      form.append('audio', recording.audio, 'recording.webm')

      try {
        const response = await fetch('/api/transcribe', {
          method: 'POST',
          body: form
        })
        if (response.ok || (response.status >= 400 && response.status < 500)) {
          await withStore('readwrite', store => store.delete(id))
        }
      } catch {
        break
      }
    }
  } catch (error) {
    console.error('Could not process the offline recording queue.', error)
  } finally {
    isUploading = false
  }
}

function openDatabase() {
  return new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, 1)

    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME, {
        keyPath: 'id',
        autoIncrement: true
      })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function withStore<Result>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<Result>
) {
  return openDatabase().then(database => new Promise<Result>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, mode)
    const request = operation(transaction.objectStore(STORE_NAME))
    let result: Result | undefined

    request.onsuccess = () => {
      result = request.result
    }
    request.onerror = () => reject(request.error)
    transaction.oncomplete = () => {
      database.close()
      resolve(result as Result)
    }
    transaction.onabort = () => {
      database.close()
      reject(transaction.error)
    }
  }))
}
