<template>
  <div class="text-center">
    <div class="text-4xl font-bold text-yellow-300 mb-2">{{ value }}</div>
    <div class="text-white/80">{{ label }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: String,
  value: [Number, String]
})
</script>
