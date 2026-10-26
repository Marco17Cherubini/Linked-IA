<template>
  <div class="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 card-hover text-center">
    <div class="text-4xl mb-4">{{ icon }}</div>
    <h3 class="text-xl font-bold text-white mb-2">{{ title }}</h3>
    <p class="text-white/80 text-sm">{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  icon: String,
  title: String,
  description: String
})
</script>
