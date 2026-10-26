<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
    <!-- Navigation -->
    <nav class="bg-white/10 backdrop-blur-md border-b border-white/20">
      <div class="container mx-auto px-4 py-4">
        <div class="flex items-center justify-between">
          <router-link to="/" class="text-white font-fugaz text-2xl hover:text-yellow-300 transition">
            LinkedIA
          </router-link>
          <div class="flex gap-6">
            <router-link to="/" class="text-white hover:text-yellow-300 transition font-medium">
              Home
            </router-link>
            <router-link to="/analysis" class="text-white hover:text-yellow-300 transition font-medium">
              Analisi
            </router-link>
            <router-link to="/history" class="text-white hover:text-yellow-300 transition font-medium">
              Storico
            </router-link>
            <router-link to="/stats" class="text-white hover:text-yellow-300 transition font-medium">
              Statistiche
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="container mx-auto px-4 py-8">
      <router-view />
    </main>

    <!-- Footer -->
    <footer class="mt-16 pb-8 text-center text-white/80">
      <p class="text-sm">
        © 2025 LinkedIA - Linked Intelligent Analyst | Università del Piemonte Orientale
      </p>
    </footer>
  </div>
</template>

<script setup>
// App component
</script>

<style>
.router-link-active {
  color: #fbbf24 !important;
  font-weight: 600;
}
</style>
