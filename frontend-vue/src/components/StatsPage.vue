<template>
  <div class="max-w-6xl mx-auto">
    <h1 class="font-fugaz text-4xl text-white mb-8 text-center">
      Statistiche Sistema
    </h1>

    <div v-if="!stats" class="text-center text-white">
      <p class="text-xl">Caricamento statistiche...</p>
    </div>

    <div v-else>
      <!-- Main Stats Grid -->
      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div class="bg-blue-500/20 border border-blue-400 backdrop-blur-md rounded-xl p-6">
          <div class="flex items-center gap-4">
            <div class="text-white text-4xl">💾</div>
            <div>
              <p class="text-white/70 text-sm">Articoli Totali</p>
              <p class="text-3xl font-bold text-white">{{ stats.total_articles }}</p>
            </div>
          </div>
        </div>
        <div class="bg-green-500/20 border border-green-400 backdrop-blur-md rounded-xl p-6">
          <div class="flex items-center gap-4">
            <div class="text-white text-4xl">📅</div>
            <div>
              <p class="text-white/70 text-sm">Date Analizzate</p>
              <p class="text-3xl font-bold text-white">{{ stats.total_dates }}</p>
            </div>
          </div>
        </div>
        <div class="bg-purple-500/20 border border-purple-400 backdrop-blur-md rounded-xl p-6">
          <div class="flex items-center gap-4">
            <div class="text-white text-4xl">📈</div>
            <div>
              <p class="text-white/70 text-sm">Analisi Complete</p>
              <p class="text-3xl font-bold text-white">{{ stats.analyzed_articles }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Date Range -->
      <div v-if="stats.date_range" class="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 mb-8">
        <h2 class="text-2xl font-bold text-white mb-4">Intervallo Temporale</h2>
        <div class="grid md:grid-cols-2 gap-6">
          <div class="text-white">
            <p class="text-white/70 mb-1">Prima Analisi</p>
            <p class="text-2xl font-bold text-yellow-300">{{ stats.date_range.earliest || 'N/A' }}</p>
          </div>
          <div class="text-white">
            <p class="text-white/70 mb-1">Ultima Analisi</p>
            <p class="text-2xl font-bold text-yellow-300">{{ stats.date_range.latest || 'N/A' }}</p>
          </div>
        </div>
      </div>

      <!-- Tracked Indices -->
      <div class="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
        <h2 class="text-2xl font-bold text-white mb-4">📊 Indici Monitorati</h2>
        <div class="grid md:grid-cols-5 gap-4">
          <div 
            v-for="(index, idx) in stats.indices_tracked" 
            :key="idx"
            class="bg-white/5 rounded-lg p-4 text-center border border-white/10"
          >
            <p class="text-white font-bold text-lg">{{ index }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stats = ref(null)

onMounted(async () => {
  try {
    const response = await fetch('/api/stats')
    const data = await response.json()
    if (data.success) {
      stats.value = data.stats
    }
  } catch (error) {
    console.error('Error fetching stats:', error)
  }
})
</script>
