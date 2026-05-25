<template>
  <div v-if="authChecking" class="h-screen overflow-hidden text-gray-900 font-sans bg-[url('/1.jpg')] bg-cover bg-center bg-no-repeat">
    <div class="h-full flex items-center justify-center bg-white/20 backdrop-blur-[2px] px-6">
      <div class="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-6 py-5 shadow-sm">
        <div class="h-1 bg-gray-200 rounded-full overflow-hidden">
          <div class="h-full w-2/3 bg-blue-600 rounded-full animate-pulse"></div>
        </div>
        <p class="mt-4 text-base text-gray-600">Проверяем сессию...</p>
      </div>
    </div>
  </div>

  <div v-else-if="!isAuthenticated" class="h-screen overflow-hidden text-gray-900 font-sans bg-[url('/1.jpg')] bg-cover bg-center bg-no-repeat">
    <div class="h-full flex items-center justify-center bg-white/20 backdrop-blur-[2px] px-6">
      <form
        class="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-6 py-6 shadow-sm"
        @submit.prevent="login"
      >
        <h1 class="text-2xl font-semibold tracking-tight">Вход</h1>
        <div class="mt-5 flex flex-col gap-4">
          <label class="flex flex-col gap-1 text-base font-medium text-gray-700">
            Логин
            <input
              v-model.trim="loginForm.username"
              autocomplete="username"
              class="rounded-lg border border-gray-200 px-3 py-2 text-base font-normal text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              type="text"
              required
            />
          </label>
          <label class="flex flex-col gap-1 text-base font-medium text-gray-700">
            Пароль
            <input
              v-model="loginForm.password"
              autocomplete="current-password"
              class="rounded-lg border border-gray-200 px-3 py-2 text-base font-normal text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              type="password"
              required
            />
          </label>
        </div>
        <div
          v-if="loginError"
          class="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-base text-red-700"
        >
          {{ loginError }}
        </div>
        <button
          :disabled="loginLoading || !loginForm.username || !loginForm.password"
          class="mt-5 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-base font-medium text-white transition-all hover:bg-blue-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
          type="submit"
        >
          {{ loginLoading ? 'Входим...' : 'Войти' }}
        </button>
      </form>
    </div>
  </div>

  <div v-else class="h-screen overflow-hidden text-gray-900 font-sans bg-[url('/1.jpg')] bg-cover bg-center bg-no-repeat">
    <div class="h-full overflow-y-auto bg-white/15 backdrop-blur-[2px]" style="scrollbar-width: none; -ms-overflow-style: none;">
      <div class="max-w-6xl mx-auto px-16 py-10">

        <!-- Header -->
        <div class="mb-8">
          <h1 class="text-2xl font-semibold tracking-tight">Проверка документов</h1>
          <p class="text-base text-gray-500 mt-1">
            Загрузите шаблон и документы для проверки структуры, содержания и форматирования
          </p>
          <div class="mt-3 flex flex-wrap items-center gap-3 text-base text-gray-600">
            <span class="rounded-lg border border-gray-200 bg-white px-3 py-1.5">{{ currentUser?.email }}</span>
            <button
              class="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-gray-700 transition-colors hover:bg-gray-50"
              @click="logout"
            >
              Выйти
            </button>
          </div>
        </div>

        <!-- Upload zones -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
          <!-- Шаблон — одиночный файл -->
          <DropZone
            label="Шаблон (эталон)"
            icon="📄"
            :file="files.template"
            @file-selected="onTemplateFileSelected"
            @file-removed="files.template = null"
          />

          <!-- Документы — множественная загрузка -->
          <MultiDropZone
            label="Документы для проверки"
            icon="📋"
            :files="files.documents"
            @files-added="onDocumentsAdded"
            @file-removed="removeDocument"
          />
        </div>

        <div v-if="templates.length || currentUser?.role === 'admin'" class="mb-5 flex flex-wrap items-center gap-3">
          <label v-if="templates.length" class="text-base text-gray-500">Готовый шаблон:</label>
          <select
            v-if="templates.length"
            v-model="selectedTemplate"
            class="text-base border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            @change="files.template = null"
          >
            <option value="">Не выбран</option>
            <option v-for="template in templates" :key="template.id" :value="template.id">
              {{ template.name }}
            </option>
          </select>
          <template v-if="currentUser?.role === 'admin'">
            <input
              class="hidden"
              ref="adminTemplateInput"
              accept=".docx"
              type="file"
              @change="onAdminTemplateFileSelected"
            />
            <button
              class="px-4 py-2 text-base font-medium rounded-lg border border-gray-200 bg-white text-gray-700 transition-colors hover:bg-gray-50"
              @click="adminTemplateInput?.click()"
            >
              {{ adminTemplateFile ? adminTemplateFile.name : 'Выбрать шаблон' }}
            </button>
            <button
              :disabled="!adminTemplateFile || adminTemplateUploadLoading"
              class="px-4 py-2 text-base font-medium rounded-lg border border-gray-200 bg-white text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-40"
              @click="uploadAdminTemplate"
            >
              {{ adminTemplateUploadLoading ? 'Загружаем...' : 'Загрузить шаблон' }}
            </button>
            <span v-if="adminTemplateUploadMessage" class="text-base text-gray-600">{{ adminTemplateUploadMessage }}</span>
          </template>
        </div>

        <!-- Controls -->
        <div class="flex flex-wrap items-center gap-3 mb-5">
          <div class="flex items-center gap-2">
            <label class="text-base text-gray-500">Модель:</label>
            <select
              v-model="model"
              class="text-base border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="option in models" :key="option.id" :value="option.id">
                {{ modelOptionLabel(option) }}
              </option>
            </select>
          </div>
          <button
            :disabled="!canRun || loading"
            @click="runCheck"
            class="px-5 py-2 text-base font-medium rounded-lg bg-blue-600 text-white transition-all
                  hover:bg-blue-700 active:scale-95
                  disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ loading ? 'Проверяем...' : 'Запустить проверку' }}
          </button>
        </div>

        <div v-if="currentUser?.role === 'admin'" class="mb-5 flex flex-wrap items-center gap-3">
          <input
            v-model.trim="adminResetUser"
            class="text-base border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Логин пользователя"
            type="text"
          />
          <button
            :disabled="adminResetLoading"
            class="px-4 py-2 text-base font-medium rounded-lg border border-gray-200 bg-white text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-40"
            @click="resetUsageLimits"
          >
            {{ adminResetLoading ? 'Сбрасываем...' : 'Сбросить лимиты' }}
          </button>
          <span v-if="adminResetMessage" class="text-base text-gray-600">{{ adminResetMessage }}</span>
        </div>

        <!-- Progress -->
        <div v-if="loading" class="mb-5">
          <div class="h-1 bg-gray-200 rounded-full overflow-hidden">
            <div
              class="h-full bg-blue-500 rounded-full transition-all duration-500"
              :style="{ width: overallProgress + '%' }"
            ></div>
          </div>
          <p class="text-lg text-gray-400 mt-1.5">{{ progressLabel }}</p>
        </div>

        <!-- Error alert -->
        <div
          v-if="globalError"
          class="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-base text-red-700"
        >
          {{ globalError }}
        </div>

        <!-- Results per file -->
        <template v-if="fileResults.length">
          <hr class="border-gray-100 my-6" />
          <h2 class="text-base font-semibold mb-3">Результаты проверки</h2>

          <div class="flex flex-col gap-3">
            <div
              v-for="fr in fileResults"
              :key="fr.fileName"
              class="border border-gray-200 rounded-xl overflow-hidden bg-white"
            >
              <!-- File accordion header -->
              <button
                @click="fr.open = !fr.open"
                class="w-full flex items-center justify-between px-5 py-4 text-base font-medium bg-gray-50 hover:bg-gray-100 transition-colors text-left"
              >
                <span class="flex items-center gap-3">
                  <!-- Status icon -->
                  <span v-if="fr.loading" class="text-xl animate-spin">⏳</span>
                  <span v-else-if="fr.error" class="text-xl">❌</span>
                  <span v-else-if="fr.result && fr.result.errors?.length === 0" class="text-xl">✅</span>
                  <span v-else class="text-xl">⚠️</span>

                  <span class="text-gray-800 break-all">{{ fr.fileName }}</span>

                  <!-- Error count badge -->
                  <span
                    v-if="!fr.loading && !fr.error && fr.result"
                    class="text-xs font-normal rounded-full px-2 py-0.5"
                    :class="fr.result.errors?.length ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'"
                  >
                    {{ fr.result.errors?.length ? fr.result.errors.length + ' ошибок' : 'OK' }}
                  </span>

                  <span v-if="fr.loading" class="text-xs font-normal text-gray-400 bg-gray-200 rounded-full px-2 py-0.5">
                    Проверяется...
                  </span>
                </span>

                <span class="text-gray-400 text-lg flex-shrink-0 ml-2">{{ fr.open ? '▲' : '▼' }}</span>
              </button>

              <!-- File accordion body -->
              <div v-if="fr.open" class="p-5">
                <!-- Loading state -->
                <div v-if="fr.loading" class="text-base text-gray-400">
                  Идёт проверка файла...
                </div>

                <!-- Error state -->
                <div v-else-if="fr.error" class="px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-base text-red-700">
                  {{ fr.error }}
                </div>

                <!-- Result -->
                <template v-else-if="fr.result">
                  <!-- Metrics -->
                  <div class="grid grid-cols-3 gap-3 mb-5">
                    <div
                      v-for="m in getMetrics(fr.result)"
                      :key="m.label"
                      class="bg-gray-50 border border-gray-100 rounded-xl px-4 py-3"
                    >
                      <div class="text-lg text-gray-400 mb-1">{{ m.label }}</div>
                      <div class="text-2xl font-semibold text-gray-900">{{ m.value }}</div>
                    </div>
                  </div>

                  <!-- No errors -->
                  <div
                    v-if="!fr.result.errors?.length"
                    class="px-4 py-3 rounded-lg bg-green-50 border border-green-200 text-base text-green-700"
                  >
                    Ошибок не найдено — документ полностью соответствует шаблону.
                  </div>

                  <!-- Error groups -->
                  <div v-else class="flex flex-col gap-2">
                    <div v-for="(group, key) in fr.groupedErrors" :key="key">
                      <div v-if="group.errors.length" class="border border-gray-100 rounded-xl overflow-hidden">
                        <button
                          @click="group.open = !group.open"
                          class="w-full flex items-center justify-between px-4 py-3 text-base font-medium
                                bg-gray-50 hover:bg-gray-100 transition-colors text-left"
                        >
                          <span class="flex items-center gap-2">
                            {{ group.label }}
                            <span class="text-lg font-normal bg-gray-200 text-gray-600 rounded-full px-2 py-0.5">
                              {{ group.errors.length }}
                            </span>
                          </span>
                          <span class="text-gray-400 text-lg">{{ group.open ? '▲' : '▼' }}</span>
                        </button>

                        <div v-if="group.open" class="p-3 flex flex-col gap-2 bg-white">
                          <template v-for="sev in ['critical', 'high', 'medium', 'low']" :key="sev">
                            <template v-if="bySev(group.errors, sev).length">
                              <div class="text-lg font-semibold uppercase tracking-widest text-gray-400 mt-1">
                                {{ sevEmoji(sev) }} {{ sev }}
                              </div>
                              <div
                                v-for="err in bySev(group.errors, sev)"
                                :key="err.description"
                                class="rounded-lg border border-gray-100 border-l-4 px-3 py-2.5 bg-gray-50"
                                :class="sevBorderClass(sev)"
                              >
                                <div class="text-base font-medium text-gray-800">{{ err.section || 'Общий' }}</div>
                                <div class="text-lg text-gray-500 mt-0.5 leading-relaxed">{{ err.description }}</div>
                              </div>
                            </template>
                          </template>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Download -->
                  <button
                    @click="downloadReport(fr)"
                    class="mt-4 text-base px-4 py-2 rounded-lg border border-gray-200 bg-white
                          hover:bg-gray-50 transition-colors text-gray-700"
                  >
                    Скачать отчёт (JSON)
                  </button>
                </template>
              </div>
            </div>
          </div>
        </template>

        <!-- Hint -->
        <p v-if="!fileResults.length && !loading" class="text-base text-gray-400 mt-4">
          Загрузите шаблон и один или несколько документов для запуска проверки.
        </p>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, defineComponent, h, onMounted } from 'vue'

// ── DropZone (single file, inline sub-component) ──────────────────────────────
const DropZone = defineComponent({
  name: 'DropZone',
  props: { label: String, icon: String, file: Object },
  emits: ['file-selected', 'file-removed'],
  setup(props, { emit }) {
    const dragOver = ref(false)
    const inputRef = ref(null)

    const onDrop = (e) => {
      dragOver.value = false
      const f = e.dataTransfer.files[0]
      if (f?.name.endsWith('.docx')) emit('file-selected', f)
    }
    const onFile = (e) => {
      const f = e.target.files[0]
      if (f) emit('file-selected', f)
    }
    const formatSize = (bytes) =>
      bytes < 1024 * 1024
        ? (bytes / 1024).toFixed(1) + ' КБ'
        : (bytes / 1024 / 1024).toFixed(1) + ' МБ'

    return () => {
      const base =
        'flex items-center justify-center rounded-xl border-2 border-dashed min-h-32 p-6 text-center cursor-pointer transition-all duration-150 '
      const state = dragOver.value
        ? 'border-blue-400 bg-blue-50'
        : props.file
        ? 'border-green-300 bg-green-50'
        : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'

      return h('div', {
        class: base + state,
        onDragover: (e) => { e.preventDefault(); dragOver.value = true },
        onDragleave: () => { dragOver.value = false },
        onDrop,
        onClick: () => inputRef.value?.click(),
      }, [
        h('input', { ref: inputRef, type: 'file', accept: '.docx', class: 'hidden', onChange: onFile }),
        props.file
          ? h('div', { class: 'flex flex-col items-center gap-1' }, [
              h('div', { class: 'text-2xl' }, '✅'),
              h('div', { class: 'text-base font-medium text-gray-800 break-all max-w-xs' }, props.file.name),
              h('div', { class: 'text-lg text-gray-400' }, formatSize(props.file.size)),
              h('button', {
                class: 'mt-2 text-lg px-3 py-1 rounded-md bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 transition-colors',
                onClick: (e) => { e.stopPropagation(); emit('file-removed') },
              }, 'Удалить'),
            ])
          : h('div', { class: 'flex flex-col items-center gap-1' }, [
              h('div', { class: 'text-2xl' }, props.icon),
              h('div', { class: 'text-base font-medium text-gray-700 mt-1' }, props.label),
              h('div', { class: 'text-lg text-gray-400 mt-0.5' }, '.docx — перетащите или нажмите'),
            ]),
      ])
    }
  },
})

// ── MultiDropZone (multiple files, inline sub-component) ──────────────────────
const MultiDropZone = defineComponent({
  name: 'MultiDropZone',
  props: { label: String, icon: String, files: Array },
  emits: ['files-added', 'file-removed'],
  setup(props, { emit }) {
    const dragOver = ref(false)
    const inputRef = ref(null)

    const onDrop = (e) => {
      dragOver.value = false
      const newFiles = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.docx'))
      if (newFiles.length) emit('files-added', newFiles)
    }
    const onFile = (e) => {
      const newFiles = Array.from(e.target.files)
      if (newFiles.length) emit('files-added', newFiles)
      e.target.value = ''
    }
    const formatSize = (bytes) =>
      bytes < 1024 * 1024
        ? (bytes / 1024).toFixed(1) + ' КБ'
        : (bytes / 1024 / 1024).toFixed(1) + ' МБ'

    return () => {
      const hasFiles = props.files && props.files.length > 0
      const base = 'rounded-xl border-2 border-dashed transition-all duration-150 '
      const state = dragOver.value
        ? 'border-blue-400 bg-blue-50'
        : hasFiles
        ? 'border-green-300 bg-green-50'
        : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'

      const children = []

      // Drop area (always visible)
      children.push(
        h('div', {
          class: 'flex flex-col items-center justify-center min-h-24 p-4 text-center cursor-pointer',
          onClick: () => inputRef.value?.click(),
          onDragover: (e) => { e.preventDefault(); dragOver.value = true },
          onDragleave: () => { dragOver.value = false },
          onDrop,
        }, [
          h('input', { ref: inputRef, type: 'file', accept: '.docx', multiple: true, class: 'hidden', onChange: onFile }),
          h('div', { class: 'text-2xl' }, hasFiles ? '➕' : props.icon),
          h('div', { class: 'text-base font-medium text-gray-700 mt-1' }, hasFiles ? 'Добавить ещё файлы' : props.label),
          h('div', { class: 'text-lg text-gray-400 mt-0.5' }, '.docx — перетащите или нажмите'),
        ])
      )

      // File list
      if (hasFiles) {
        children.push(
          h('div', { class: 'border-t border-gray-200 px-4 pb-3 flex flex-col gap-2' },
            props.files.map((f, i) =>
              h('div', {
                key: f.name + i,
                class: 'flex items-center justify-between gap-2 pt-2',
              }, [
                h('div', { class: 'flex items-center gap-2 min-w-0' }, [
                  h('span', { class: 'text-base' }, '📋'),
                  h('div', { class: 'min-w-0' }, [
                    h('div', { class: 'text-base text-gray-800 truncate' }, f.name),
                    h('div', { class: 'text-lg text-gray-400' }, formatSize(f.size)),
                  ]),
                ]),
                h('button', {
                  class: 'flex-shrink-0 text-lg px-2.5 py-1 rounded-md bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 transition-colors',
                  onClick: (e) => { e.stopPropagation(); emit('file-removed', i) },
                }, '✕'),
              ])
            )
          )
        )
      }

      return h('div', {
        class: base + state,
        onDragover: (e) => { e.preventDefault(); dragOver.value = true },
        onDragleave: () => { dragOver.value = false },
        onDrop,
      }, children)
    }
  },
})

// ── State ─────────────────────────────────────────────────────────────────────
const API_BASE_URL  = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

const authToken    = ref(localStorage.getItem('auth_token') || '')
const currentUser  = ref(null)
const authChecking = ref(Boolean(authToken.value))
const loginLoading = ref(false)
const loginError   = ref('')
const loginForm    = reactive({ username: '', password: '' })

const files         = reactive({ template: null, documents: [] })
const models        = ref([])
const templates     = ref([])
const selectedTemplate = ref('')
const model         = ref('')
const loading       = ref(false)
const progressLabel = ref('')
const globalError   = ref('')
const fileResults   = ref([])  // Array of { fileName, file, open, loading, error, result, groupedErrors }
const adminResetUser = ref('')
const adminResetLoading = ref(false)
const adminResetMessage = ref('')
const adminTemplateInput = ref(null)
const adminTemplateFile = ref(null)
const adminTemplateUploadLoading = ref(false)
const adminTemplateUploadMessage = ref('')

// ── File management ───────────────────────────────────────────────────────────
function onDocumentsAdded(newFiles) {
  for (const f of newFiles) {
    // Avoid duplicates by name
    if (!files.documents.find(d => d.name === f.name)) {
      files.documents.push(f)
    }
  }
}

function removeDocument(index) {
  files.documents.splice(index, 1)
}

function onTemplateFileSelected(file) {
  selectedTemplate.value = ''
  files.template = file
}

function onAdminTemplateFileSelected(event) {
  const file = event.target.files?.[0] || null
  adminTemplateUploadMessage.value = ''
  adminTemplateFile.value = file?.name.endsWith('.docx') ? file : null
  if (file && !adminTemplateFile.value) {
    adminTemplateUploadMessage.value = 'Можно загрузить только .docx'
  }
}

// ── Computed ──────────────────────────────────────────────────────────────────
const isAuthenticated = computed(() => Boolean(authToken.value && currentUser.value))
const hasTemplate = computed(() => Boolean(files.template || selectedTemplate.value))
const canRun = computed(() => hasTemplate.value && files.documents.length > 0 && Boolean(model.value))

const overallProgress = computed(() => {
  if (!fileResults.value.length) return 0
  const done = fileResults.value.filter(fr => !fr.loading).length
  return Math.round((done / fileResults.value.length) * 100)
})

// ── Helpers ───────────────────────────────────────────────────────────────────
const sevEmoji = (s) => ({ critical: '🔴', high: '🟠', medium: '🟡', low: '🟢' }[s] ?? '⚪')
const bySev    = (errs, sev) => errs.filter(e => e.severity === sev)
const sevBorderClass = (sev) => ({
  critical: 'border-l-red-500',
  high:     'border-l-orange-400',
  medium:   'border-l-yellow-400',
  low:      'border-l-green-400',
}[sev] ?? 'border-l-gray-300')

function modelOptionLabel(option) {
  if (option.usage_limit === null || option.usage_limit === undefined) {
    return option.name
  }
  return `${option.name} (${option.remaining ?? 0}/${option.usage_limit})`
}

function getMetrics(result) {
  const errs = result.errors ?? []
  return [
    { label: 'Ошибок всего',   value: errs.length },
    { label: 'Структурных',    value: errs.filter(e => e.error_type === 'structural').length },
    { label: 'Форматирования', value: errs.filter(e => e.error_type === 'formatting').length },
  ]
}

function buildGroupedErrors(errors) {
  return reactive({
    structural: { label: 'Структура',      errors: errors.filter(e => e.error_type === 'structural'), open: false },
    formatting: { label: 'Форматирование', errors: errors.filter(e => e.error_type === 'formatting'), open: false },
    content:    { label: 'Содержание',     errors: errors.filter(e => e.error_type === 'content'),    open: false },
    typography: { label: 'Типографика',    errors: errors.filter(e => e.error_type === 'typography'), open: false },
  })
}

// ── Actions ───────────────────────────────────────────────────────────────────
function clearAuth() {
  authToken.value = ''
  currentUser.value = null
  localStorage.removeItem('auth_token')
}

function authHeaders() {
  return authToken.value ? { Authorization: `Bearer ${authToken.value}` } : {}
}

function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const apiRoot = API_BASE_URL.endsWith('/api') ? API_BASE_URL : `${API_BASE_URL}/api`
  return `${apiRoot}${normalizedPath}`
}

async function authorizedFetch(url, options = {}) {
  const headers = { ...(options.headers || {}), ...authHeaders() }
  return fetch(url, { ...options, headers })
}

async function loadCurrentUser() {
  if (!authToken.value) {
    authChecking.value = false
    return
  }

  try {
    const res = await authorizedFetch(apiUrl('/auth/me'))
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    currentUser.value = await res.json()
    await loadAppConfig()
  } catch {
    clearAuth()
  } finally {
    authChecking.value = false
  }
}

async function loadAppConfig() {
  await Promise.all([loadModels(), loadTemplates()])
}

async function loadModels() {
  const res = await authorizedFetch(apiUrl('/models'))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

  models.value = data.models || []
  const hasSelectedModel = models.value.some((item) => item.id === model.value)
  if (!hasSelectedModel) {
    model.value = data.default_model || models.value[0]?.id || ''
  }
}

async function loadTemplates() {
  const res = await authorizedFetch(apiUrl('/templates'))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

  templates.value = data.templates || []
  if (selectedTemplate.value && !templates.value.some((item) => item.id === selectedTemplate.value)) {
    selectedTemplate.value = ''
  }
}

async function login() {
  loginLoading.value = true
  loginError.value = ''

  try {
    const res = await fetch(apiUrl('/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        username: loginForm.username,
        password: loginForm.password,
      }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

    authToken.value = data.access_token
    currentUser.value = data.user
    localStorage.setItem('auth_token', data.access_token)
    loginForm.password = ''
    await loadAppConfig()
  } catch (e) {
    loginError.value = e.message || 'Не удалось войти'
  } finally {
    loginLoading.value = false
  }
}

async function logout() {
  try {
    await authorizedFetch(apiUrl('/auth/logout'), { method: 'POST' })
  } finally {
    clearAuth()
  }
}

async function resetUsageLimits() {
  adminResetLoading.value = true
  adminResetMessage.value = ''

  try {
    const payload = {
      user_email: adminResetUser.value || null,
      model: null,
    }
    const res = await authorizedFetch(apiUrl('/admin/usage/reset'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    adminResetMessage.value = `Сброшено записей: ${data.reset_records ?? 0}`
    await loadModels()
  } catch (e) {
    adminResetMessage.value = e.message || 'Не удалось сбросить лимиты'
  } finally {
    adminResetLoading.value = false
  }
}

async function uploadAdminTemplate() {
  if (!adminTemplateFile.value) return

  adminTemplateUploadLoading.value = true
  adminTemplateUploadMessage.value = ''

  try {
    const fd = new FormData()
    fd.append('template_file', adminTemplateFile.value)
    const res = await authorizedFetch(apiUrl('/admin/templates'), { method: 'POST', body: fd })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

    adminTemplateUploadMessage.value = `Шаблон загружен: ${data.name}`
    adminTemplateFile.value = null
    if (adminTemplateInput.value) adminTemplateInput.value.value = ''
    await loadTemplates()
    selectedTemplate.value = data.id
    files.template = null
  } catch (e) {
    adminTemplateUploadMessage.value = e.message || 'Не удалось загрузить шаблон'
  } finally {
    adminTemplateUploadLoading.value = false
  }
}

async function runCheck() {
  loading.value     = true
  globalError.value = ''

  // Init result entries for all documents
  fileResults.value = files.documents.map(f => ({
    fileName:     f.name,
    file:         f,
    open:         false,
    loading:      true,
    error:        null,
    result:       null,
    groupedErrors: buildGroupedErrors([]),
  }))

  progressLabel.value = `Проверяем ${files.documents.length} документов...`

  for (const fr of fileResults.value) {
    await checkSingleFile(fr)
  }

  await loadModels().catch(() => {})
  loading.value       = false
  progressLabel.value = 'Готово'
}

async function checkSingleFile(fr) {
  try {
    const fd = new FormData()
    if (selectedTemplate.value) {
      fd.append('template_name', selectedTemplate.value)
    } else {
      fd.append('template_file', files.template)
    }
    fd.append('document_file',  fr.file)
    fd.append('model',     model.value)

    const res = await authorizedFetch(apiUrl('/validate-upload'), { method: 'POST', body: fd })
    if (res.status === 401) {
      clearAuth()
      throw new Error('Сессия истекла')
    }
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    if (data.error) throw new Error(data.error)

    fr.result        = data
    fr.groupedErrors = buildGroupedErrors(data.errors ?? [])
  } catch (e) {
    fr.error = 'Ошибка: ' + e.message
  } finally {
    fr.loading = false
  }
}

function downloadReport(fr) {
  if (!fr.result) return
  const report = {
    template:           selectedTemplate.value || files.template?.name,
    document:           fr.fileName,
    model:              model.value,
    result:             fr.result,
    timestamp:          new Date().toISOString(),
    checked_formatting: true,
  }
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const a = Object.assign(document.createElement('a'), {
    href:     URL.createObjectURL(blob),
    download: `report_${fr.fileName.replace('.docx', '')}_${Date.now()}.json`,
  })
  a.click()
  URL.revokeObjectURL(a.href)
}

onMounted(loadCurrentUser)
</script>
