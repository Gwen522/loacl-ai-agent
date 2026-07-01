<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{ (e: 'send', text: string): void }>()
const prop = defineProps<{ loading: boolean }>()

const text = ref('')

const handleSend = () => {
  const t = text.value.trim()
  if (!t || prop.loading) return
  emit('send', t)
  text.value = ''
}
</script>

<template>
  <div class="bar">
    <input
      v-model="text" @keyup.enter="handleSend"
      :disabled="loading" placeholder="输入消息，回车发送…"
    />
    <button @click="handleSend" :disabled="loading || !text.trim()">
      {{ loading ? '···' : '发送' }}
    </button>
  </div>
</template>

<style scoped>
.bar {
  padding: 16px 20px; background: #fff; border-top: 1px solid #eee;
  display: flex; gap: 10px;
}
input {
  flex: 1; padding: 12px 16px; border: 1px solid #ddd; border-radius: 24px;
  font-size: 15px; outline: none; transition: border .2s;
}
input:focus { border-color: #667eea; }
button {
  padding: 12px 26px; background: #667eea; color: #fff; border: none;
  border-radius: 24px; font-size: 15px; cursor: pointer; transition: opacity .2s;
}
button:disabled { opacity: .5; cursor: not-allowed; }
</style>
