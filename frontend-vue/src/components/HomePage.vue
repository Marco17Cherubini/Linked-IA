<template>
  <div class="max-w-6xl mx-auto">
    <!-- Hero Section -->
    <div class="text-center mb-16">
      <h1 class="font-fugaz text-6xl text-white mb-4 drop-shadow-lg">
        Linked Intelligent Analyst
      </h1>
      <p class="text-xl text-white/90 mb-8 max-w-2xl mx-auto">
        Dove notizie e mercati si incontrano. Un sistema AI che analizza eventi geopolitici 
        e li collega ai movimenti dei mercati finanziari.
      </p>
      <router-link 
        to="/analysis"
        class="inline-block bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-bold px-8 py-4 rounded-lg text-lg transition transform hover:scale-105 shadow-xl"
      >
        Inizia Analisi →
      </router-link>
    </div>

    <!-- Features Grid -->
    <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
      <FeatureCard 
        icon="📰"
        title="Notizie Real-Time"
        description="RSS feeds e ricerca intelligente eventi storici"
      />
      <FeatureCard 
        icon="📊"
        title="Dati Mercato"
        description="5 indici principali con OHLCV e indicatori"
      />
      <FeatureCard 
        icon="🧠"
        title="AI Analysis"
        description="GPT-3.5 per nessi semantica-numerico"
      />
      <FeatureCard 
        icon="📈"
        title="Previsioni"
        description="Pattern storici e similarity analysis"
      />
    </div>

    <!-- Quick Stats -->
    <div v-if="stats" class="bg-white/10 backdrop-blur-md rounded-xl p-8 border border-white/20">
      <h2 class="text-2xl font-bold text-white mb-6">Statistiche Sistema</h2>
      <div class="grid md:grid-cols-3 gap-6">
        <StatCard label="Articoli Totali" :value="stats.total_articles" />
        <StatCard label="Date Analizzate" :value="stats.total_dates" />
        <StatCard label="Analisi Complete" :value="stats.analyzed_articles" />
      </div>
    </div>

    <!-- About Section -->
    <div class="mt-12 bg-white/10 backdrop-blur-md rounded-xl p-8 border border-white/20">
      <h2 class="text-2xl font-bold text-white mb-4">Come Funziona</h2>
      <div class="text-white/90 space-y-4">
        <StepItem number="1" text="Inserisci una data di interesse (YYYY-MM-DD)" />
        <StepItem number="2" text="Il sistema cerca notizie da feed RSS o via GPT" />
        <StepItem number="3" text="Scarica dati di mercato per 5 indici principali" />
        <StepItem number="4" text="Calcola 14 indicatori tecnici (ATR, volatility, momentum, ecc.)" />
        <StepItem number="5" text="Analizza i nessi tra eventi e movimenti di mercato" />
        <StepItem number="6" text="Genera previsioni basate su pattern storici simili" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import FeatureCard from './FeatureCard.vue'
import StatCard from './StatCard.vue'
import StepItem from './StepItem.vue'

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
