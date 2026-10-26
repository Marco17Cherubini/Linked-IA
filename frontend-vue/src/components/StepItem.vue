<template>
  <div class="flex items-start gap-4">
    <div class="bg-yellow-400 text-gray-900 rounded-full w-8 h-8 flex items-center justify-center font-bold flex-shrink-0">
      {{ number }}
    </div>
    <p class="pt-1">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({
  number: [Number, String],
  text: String
})
</script>
