<template>
  <div class="bg-white/5 rounded-lg p-4 border border-white/10">
    <h4 class="text-xl font-semibold text-white mb-2">{{ article.Titolo }}</h4>
    <p class="text-white/70 text-sm mb-2">
      <strong>Data:</strong> {{ article.Data }} | <strong>Fonti:</strong> {{ article.Fonti }}
    </p>
    
    <div v-if="expanded" class="mt-4 space-y-3">
      <div v-if="article.Corpo">
        <p class="text-white/90 text-sm">{{ article.Corpo }}</p>
      </div>
      
      <div v-if="article.prezzi && Object.keys(article.prezzi).length > 0">
        <p class="text-yellow-300 font-semibold text-sm mb-1">Prezzi di Mercato:</p>
        <div class="bg-black/30 p-3 rounded text-xs text-white/80 font-mono">
          <pre>{{ JSON.stringify(article.prezzi, null, 2) }}</pre>
        </div>
      </div>

      <div v-if="article.addons && Object.keys(article.addons).length > 0">
        <p class="text-yellow-300 font-semibold text-sm mb-1">Indicatori Tecnici:</p>
        <div class="bg-black/30 p-3 rounded text-xs text-white/80 font-mono">
          <pre>{{ JSON.stringify(article.addons, null, 2) }}</pre>
        </div>
      </div>

      <div v-if="analysis && analysis.report_nesso">
        <p class="text-green-300 font-semibold text-sm mb-1">📊 Report Nesso:</p>
        <div class="bg-black/30 p-3 rounded text-sm text-white/90">
          {{ analysis.report_nesso }}
        </div>
      </div>
    </div>

    <button
      @click="expanded = !expanded"
      class="mt-3 text-yellow-300 hover:text-yellow-400 text-sm font-semibold"
    >
      {{ expanded ? '▲ Nascondi dettagli' : '▼ Mostra dettagli' }}
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  article: Object,
  analysis: Object
})

const expanded = ref(false)
</script>
