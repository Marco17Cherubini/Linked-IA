<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="font-fugaz text-4xl text-white mb-8 text-center">
      Analisi Geopolitico-Finanziaria
    </h1>

    <!-- Analysis Form -->
    <div class="bg-white/10 backdrop-blur-md rounded-xl p-8 border border-white/20 mb-8">
      <form @submit.prevent="handleAnalyze" class="max-w-md mx-auto">
        <label class="block text-white font-semibold mb-2">
          Seleziona Data (YYYY-MM-DD)
        </label>
        <div class="flex gap-4">
          <input
            type="date"
            v-model="date"
            class="flex-1 px-4 py-3 rounded-lg border-2 border-white/30 bg-white/90 focus:outline-none focus:border-yellow-400 transition"
            required
          />
          <button
            type="submit"
            :disabled="loading"
            class="bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-bold px-8 py-3 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? 'Analisi...' : 'Analizza' }}
          </button>
        </div>
      </form>

      <!-- Loading State -->
      <div v-if="loading" class="mt-8 text-center">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-300 mb-4"></div>
        <p class="text-white">Analisi in corso... Questo può richiedere qualche minuto.</p>
        <div class="mt-4 space-y-2 text-white/70 text-sm">
          <p>→ Ricerca notizie...</p>
          <p>→ Download dati mercato...</p>
          <p>→ Calcolo indicatori...</p>
          <p>→ Analisi AI in corso...</p>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="mt-8 bg-red-500/20 border border-red-500 rounded-lg p-4">
        <p class="text-white font-semibold">Errore</p>
        <p class="text-white/80 text-sm">{{ error }}</p>
      </div>
    </div>

    <!-- Results -->
    <div v-if="result && result.success" class="space-y-6">
      <!-- Summary -->
      <div class="bg-green-500/20 border border-green-400 rounded-xl p-6">
        <h2 class="text-2xl font-bold text-white mb-4">✓ Analisi Completata</h2>
        <div class="grid md:grid-cols-3 gap-4 text-white">
          <div>
            <p class="text-white/70 text-sm">Data</p>
            <p class="font-semibold text-lg">{{ result.date }}</p>
          </div>
          <div>
            <p class="text-white/70 text-sm">Articoli Trovati</p>
            <p class="font-semibold text-lg">{{ result.articles_found }}</p>
          </div>
          <div>
            <p class="text-white/70 text-sm">Analisi Eseguite</p>
            <p class="font-semibold text-lg">{{ result.analysis?.length || 0 }}</p>
          </div>
        </div>
      </div>

      <!-- Articles -->
      <div v-if="result.articles && result.articles.length > 0" class="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
        <h3 class="text-2xl font-bold text-white mb-4">📈 Articoli e Analisi</h3>
        <div class="space-y-4">
          <ArticleCard 
            v-for="(article, idx) in result.articles" 
            :key="idx"
            :article="article"
            :analysis="result.analysis?.[idx]"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ArticleCard from './ArticleCard.vue'

const date = ref('')
const loading = ref(false)
const result = ref(null)
const error = ref(null)

const handleAnalyze = async () => {
  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ date: date.value }),
    })

    const data = await response.json()

    if (response.ok) {
      result.value = data
    } else {
      error.value = data.error || 'Errore durante l\'analisi'
    }
  } catch (err) {
    error.value = 'Errore di connessione al server'
    console.error(err)
  } finally {
    loading.value = false
  }
}
</script>
