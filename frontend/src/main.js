import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)

// 禁用 Vue Devtools
app.config.devtools = false

app.mount('#app')
