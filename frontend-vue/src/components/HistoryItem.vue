<template>
  <div class="bg-white/5 rounded-lg p-4 border border-white/10 hover:bg-white/10 transition">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="text-2xl">🕐</span>
        <div>
          <p class="text-white font-semibold">{{ item.date }}</p>
          <p class="text-white/70 text-sm">
            {{ item.article_count }} articoli | {{ item.analyzed_count }} analizzati
          </p>
        </div>
      </div>
      <button
        @click="toggleDetails"
        class="text-yellow-300 hover:text-yellow-400 text-sm font-semibold"
      >
        {{ showDetails ? 'Nascondi' : 'Dettagli' }}
      </button>
    </div>

    <div v-if="showDetails && details" class="mt-4 pt-4 border-t border-white/10 space-y-3">
      <div v-for="(article, idx) in details" :key="idx" class="text-white/90 text-sm">
        <p class="font-semibold mb-1">{{ article.title }}</p>
        <p v-if="article.report_nesso" class="text-white/70 text-xs bg-black/30 p-2 rounded">
          {{ article.report_nesso }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  item: Object
})

const details = ref(null)
const showDetails = ref(false)

const toggleDetails = async () => {
  if (!showDetails.value && !details.value) {
    try {
      const response = await fetch(`/api/article/${props.item.date}`)
      const data = await response.json()
      if (data.success) {
        details.value = data.articles
      }
    } catch (error) {
      console.error('Error loading details:', error)
    }
  }
  showDetails.value = !showDetails.value
}
</script>
