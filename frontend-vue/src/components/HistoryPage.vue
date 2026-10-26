<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="font-fugaz text-4xl text-white mb-8 text-center">
      Storico Analisi
    </h1>

    <!-- Search Bar -->
    <div class="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 mb-6">
      <input
        type="text"
        v-model="searchTerm"
        placeholder="Cerca per data..."
        class="w-full px-4 py-3 rounded-lg border-2 border-white/30 bg-white/90 focus:outline-none focus:border-yellow-400 transition"
      />
    </div>

    <!-- History List -->
    <div class="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
      <div v-if="loading" class="text-center text-white py-12">
        Caricamento storico...
      </div>
      <div v-else-if="filteredHistory.length === 0" class="text-center text-white/70 py-12">
        <p class="text-4xl mb-4">📄</p>
        <p>Nessuna analisi trovata</p>
      </div>
      <div v-else class="space-y-3">
        <HistoryItem 
          v-for="(item, idx) in filteredHistory" 
          :key="idx"
          :item="item"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import HistoryItem from './HistoryItem.vue'

const history = ref([])
const loading = ref(true)
const searchTerm = ref('')

const filteredHistory = computed(() => {
  return history.value.filter(item =>
    item.date.includes(searchTerm.value)
  )
})

onMounted(async () => {
  try {
    const response = await fetch('/api/history')
    const data = await response.json()
    if (data.success) {
      history.value = data.history
    }
  } catch (error) {
    console.error('Error fetching history:', error)
  } finally {
    loading.value = false
  }
})
</script>
