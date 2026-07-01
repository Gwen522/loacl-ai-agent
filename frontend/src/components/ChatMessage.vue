<script setup lang="ts">
defineProps<{
  role: 'user' | 'ai'
  content: string
  thinking?: string
  tools?: string[]
}>()
</script>

<template>
  <div class="msg" :class="role">
    <div class="avatar">{{ role === 'user' ? '👤' : '🤖' }}</div>
    <div class="bubble">
      <div v-if="thinking" class="thinking">💭 {{ thinking }}</div>
      <div v-if="tools?.length" class="tools">
        <div v-for="t in tools" :key="t" class="tool">🔧 {{ t }}</div>
      </div>
      <div class="text">{{ content }}</div>
    </div>
  </div>
</template>

<style scoped>
.msg {
  display: flex; gap: 10px; margin-bottom: 20px;
  align-items: flex-start;
}
.msg.user { flex-direction: row-reverse; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; flex-shrink: 0;
  background: #e8e8ed;
}
.msg.user .avatar { background: #d6daf7; }
.bubble {
  max-width: 75%; padding: 14px 18px; border-radius: 14px;
  line-height: 1.7; word-break: break-word;
}
.msg.ai .bubble {
  background: #fff; color: #333;
  border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.msg.user .bubble {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff; border-bottom-right-radius: 4px;
}
.thinking {
  font-size: 12px; color: #999; font-style: italic;
  margin-bottom: 8px; white-space: pre-wrap;
}
.tools { margin-bottom: 8px; }
.tool {
  font-size: 11px; color: #d97706; background: #fef3c7;
  display: inline-block; padding: 2px 8px; border-radius: 8px;
  margin-right: 4px; margin-bottom: 2px;
}
.text { font-size: 15px; white-space: pre-wrap; }
</style>
