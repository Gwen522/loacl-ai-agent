<script setup lang="ts">
import { ref, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'

interface Message {
  role: 'user' | 'ai'
  content: string
  thinking: string
  tools: string[]
}

const messages = ref<Message[]>([])
const loading = ref(false)
const mode = ref<'dev' | 'real' | 'clean'>('dev')
const msgEl = ref<HTMLElement>()

const modeLabel: Record<string, string> = { dev: '测试', real: '真实', clean: '清空重来' }

const scrollBottom = () => nextTick(() => {
  msgEl.value?.scrollTo({ top: msgEl.value.scrollHeight, behavior: 'smooth' })
})

const handleClear = () => {
  messages.value = []
}

const send = async (text: string) => {
  messages.value.push({ role: 'user', content: text, thinking: '', tools: [] })
  loading.value = true
  scrollBottom()

  const history = messages.value
    .filter(m => m.role === 'user' || (m.role === 'ai' && m.content))
    .slice(0, -1)
    .map(m => ({ role: m.role === 'ai' ? 'assistant' : 'user', content: m.content }))

  const ai: Message = { role: 'ai', content: '', thinking: '', tools: [] }
  messages.value.push(ai)

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history, mode: mode.value }),
    })
    const reader = res.body!.getReader()
    const dec = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      const lines = buf.split('\n\n')
      buf = lines.pop()!

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const evt = JSON.parse(line.slice(6))
        if (evt.type === 'token') ai.content += evt.data        // 流式直接进内容
        else if (evt.type === 'tool') ai.tools.push(evt.data)
        else if (evt.type === 'done') { if (!ai.content) ai.content = evt.data }
        else if (evt.type === 'error') ai.content = '出错: ' + evt.data
        scrollBottom()
      }
    }
  } catch (e: any) {
    ai.content = '请求失败: ' + e.message
  } finally {
    loading.value = false
    scrollBottom()
  }
}
</script>

<template>
  <div class="window">
    <div class="header">
      <span class="title">AI 助手</span>
      <div class="controls">
        <button v-for="m in (['dev', 'real', 'clean'] as const)" :key="m"
          :class="{ active: mode === m }" @click="mode = m">
          {{ modeLabel[m] }}
        </button>
        <button class="clear" @click="handleClear">清屏</button>
      </div>
    </div>
    <div class="body" ref="msgEl">
      <ChatMessage
        v-for="(m, i) in messages" :key="i"
        :role="m.role" :content="m.content"
        :thinking="m.thinking" :tools="m.tools"
      />
    </div>
    <ChatInput :loading="loading" @send="send" />
  </div>
</template>

<style scoped>
.window {
  width: 100%; max-width: 800px; height: 100vh;
  margin: 0 auto; display: flex; flex-direction: column;
  background: #fff; box-shadow: 0 0 60px rgba(0,0,0,.15);
}
.header {
  padding: 14px 20px; border-bottom: 1px solid #eee;
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}
.title { font-size: 17px; font-weight: 600; color: #333; }
.controls { display: flex; gap: 6px; }
.controls button {
  padding: 5px 12px; border: 1px solid #ddd; border-radius: 14px;
  font-size: 13px; background: #fff; cursor: pointer; transition: all .15s;
}
.controls button.active {
  background: #667eea; color: #fff; border-color: #667eea;
}
.controls button.clear { color: #999; }
.controls button.clear:hover { color: #e53e3e; border-color: #e53e3e; }
.body { flex: 1; overflow-y: auto; padding: 24px; background: #f7f8fa; }
</style>
