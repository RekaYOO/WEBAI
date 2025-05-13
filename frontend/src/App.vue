<script>
import Chat from './components/Chat.vue'

export default {
  name: 'App',
  components: {
    Chat
  }
}
</script>

<template>
  <div class="app">
    <header>
      <h1>AI 对话助手</h1>
    </header>
    <main>
      <Chat />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  line-height: 1.6;
  color: #333;
}

.app {
  min-height: 100vh;
  background: #f8f9fa;
}

header {
  background: #007AFF;
  color: white;
  padding: 1rem;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
  font-size: 1.5rem;
  font-weight: 500;
}

main {
  padding: 20px;
}
</style>
