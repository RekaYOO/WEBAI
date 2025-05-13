<template>
  <div class="chat-container">
    <div class="conversations-sidebar">
      <button class="new-conversation-btn" @click="createNewConversation">新建对话</button>
      <div class="conversations-list">
        <div 
          v-for="conv in conversations" 
          :key="conv.id" 
          class="conversation-item"
          :class="{ active: currentConversationId === conv.id }"
          @click="switchConversation(conv.id)"
        >
          <span class="conversation-title">{{ conv.title }}</span>
          <button class="delete-btn" @click.stop="deleteConversation(conv.id)">×</button>
        </div>
      </div>
      <div class="model-selector">
        <div class="model-select-wrapper">
          <select v-model="selectedModel" :disabled="isLoading" class="model-select">
            <option v-for="model in availableModels" :key="model" :value="model">
              {{ model }}
            </option>
          </select>
          <span class="model-select-icon">▼</span>
        </div>
        <div class="streaming-toggle">
          <label class="toggle-switch">
            <input type="checkbox" v-model="isStreamingEnabled">
            <span class="toggle-slider"></span>
          </label>
          <span class="toggle-label">流式输出</span>
        </div>
      </div>
    </div>
    <div class="chat-main">
      <div class="nav-bar" v-if="isMobile">
        <div class="nav-left">
          <button class="menu-btn" @click="toggleSidebar">
            <span class="menu-icon">☰</span>
          </button>
          <button class="new-chat-btn" @click="createNewConversation">
            <span class="plus-icon">+</span>
          </button>
        </div>
        <div class="nav-title" v-if="currentConversationId">
          {{ getCurrentConversationTitle }}
        </div>
      </div>
      <div class="mobile-menu" v-if="showMobileMenu && isMobile" @click.self="toggleSidebar">
        <div class="menu-content" @click.stop>
          <div class="menu-section">
            <h3>历史对话</h3>
            <div class="menu-conversations">
              <div 
                v-for="conv in conversations" 
                :key="conv.id" 
                class="menu-conversation-item"
                :class="{ active: currentConversationId === conv.id }"
                @click="selectConversation(conv.id)"
              >
                <span class="conversation-title">{{ conv.title }}</span>
                <button class="delete-btn" @click.stop="deleteConversation(conv.id)">×</button>
              </div>
            </div>
          </div>
          <div class="menu-section">
            <h3>选择模型</h3>
            <select v-model="selectedModel" :disabled="isLoading" class="model-select">
              <option v-for="model in availableModels" :key="model" :value="model">
                {{ model }}
              </option>
            </select>
          </div>
        </div>
      </div>
      <div class="chat-messages" ref="messagesContainer">
        <div class="messages-container">
          <div v-for="(message, index) in messages" :key="index" class="message">
            <div class="message-wrapper" :class="{ 'user-message': message.isUser }">
              <div class="avatar" v-if="!message.isUser">
                <img src="@/assets/images/ai-avatar.jpg" alt="AI Avatar">
              </div>
              <div class="message-content">
                <div class="message-header">
                  <div v-if="!message.isUser && message.reasoning" class="reasoning-section">
                    <div class="reasoning-header" @click="toggleReasoning(index)">
                      <span>AI 思考过程</span>
                      <span class="toggle-icon">{{ message.showReasoning ? '▼' : '▶' }}</span>
                    </div>
                    <div v-show="message.showReasoning" class="reasoning-content" v-html="renderMarkdown(message.reasoning)"></div>
                  </div>
                  <button v-if="!message.isUser" class="copy-btn" @click="copyMessage(message.content, $event)" title="复制消息">📋</button>
                </div>
                <div class="message-content-wrapper">
                  <div class="message-text" v-html="renderMarkdown(message.content)"></div>
                  <div v-if="message.isStreaming && !message.isAnswering && isStreamingEnabled" class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="isLoading && !isStreamingEnabled" class="message">
            <div class="message-wrapper">
              <div class="avatar">
                <img src="@/assets/images/ai-avatar.jpg" alt="AI Avatar">
              </div>
              <div class="message-content ai-message loading">
                <div class="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="chat-input-container">
        <div class="chat-input-wrapper">
          <div class="chat-input">
            <input 
              type="text" 
              v-model="newMessage" 
              @keyup.enter="sendMessage"
              placeholder="输入消息..."
              :disabled="isLoading || !currentConversationId"
            >
            <button @click="sendMessage" :disabled="isLoading || !currentConversationId">发送</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked';

export default {
  name: 'Chat',
  data() {
    return {
      messages: [],
      newMessage: '',
      isLoading: false,
      apiUrl: 'http://localhost:5000/api',
      conversations: [],
      currentConversationId: null,
      availableModels: [],
      selectedModel: 'gpt-3.5-turbo',
      showMobileMenu: false,
      isMobile: window.innerWidth <= 768,
      isStreamingEnabled: true,
      currentStreamingMessage: '',
      shouldAutoScroll: true,
    }
  },
  created() {
    // 配置 marked
    marked.setOptions({
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false,
      sanitize: true,
      smartLists: true,
      smartypants: true,
      xhtml: true
    });
  },
  computed: {
    getCurrentConversationTitle() {
      const conversation = this.conversations.find(c => c.id === this.currentConversationId);
      return conversation ? conversation.title : '';
    }
  },
  mounted() {
    window.addEventListener('resize', this.checkMobile);
    const container = this.$refs.messagesContainer;
    if (container) {
      container.addEventListener('scroll', this.handleScroll);
    }
    this.loadConversations();
    this.loadAvailableModels();
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.checkMobile);
    const container = this.$refs.messagesContainer;
    if (container) {
      container.removeEventListener('scroll', this.handleScroll);
    }
  },
  methods: {
    renderMarkdown(content) {
      if (!content) return '';
      try {
        // 确保内容是字符串
        const text = String(content);
        // 渲染 markdown
        return marked(text);
      } catch (error) {
        console.error('Markdown 渲染错误:', error);
        return content;
      }
    },
    async loadConversations() {
      try {
        console.log('开始加载对话列表...');
        const response = await fetch(`${this.apiUrl}/conversations`);
        if (!response.ok) throw new Error('加载对话列表失败');
        const data = await response.json();
        console.log('获取到的对话列表数据：', data);
        this.conversations = data;
      } catch (error) {
        console.error('加载对话列表失败:', error);
        alert('加载对话列表失败，请刷新页面重试');
      }
    },
    async createNewConversation() {
      try {
        const response = await fetch(`${this.apiUrl}/conversations`, {
          method: 'POST'
        });
        if (!response.ok) throw new Error('创建对话失败');
        const data = await response.json();
        this.conversations.push(data);
        this.switchConversation(data.id);
      } catch (error) {
        console.error('Error:', error);
        alert('创建对话失败，请重试');
      }
    },
    async deleteConversation(conversationId) {
      if (!confirm('确定要删除这个对话吗？')) return;
      
      try {
        const response = await fetch(`${this.apiUrl}/conversations/${conversationId}`, {
          method: 'DELETE'
        });
        if (!response.ok) throw new Error('删除对话失败');
        
        this.conversations = this.conversations.filter(c => c.id !== conversationId);
        if (this.currentConversationId === conversationId) {
          this.currentConversationId = null;
          this.messages = [];
        }
      } catch (error) {
        console.error('Error:', error);
        alert('删除对话失败，请重试');
      }
    },
    async switchConversation(conversationId) {
      this.currentConversationId = conversationId;
      this.messages = [];
      this.newMessage = '';
      
      try {
        const response = await fetch(`${this.apiUrl}/conversations/${conversationId}/history`);
        if (!response.ok) throw new Error('加载对话历史失败');
        const history = await response.json();
        
        this.messages = history.map(entry => [
          { content: entry.user, isUser: true, timestamp: entry.timestamp },
          { 
            content: entry.ai, 
            reasoning: entry.reasoning,
            isUser: false, 
            timestamp: entry.timestamp,
            showReasoning: false
          }
        ]).flat();
        
        this.scrollToBottom();
      } catch (error) {
        console.error('Error:', error);
        alert('加载对话历史失败，请重试');
      }
    },
    toggleReasoning(index) {
      this.messages[index].showReasoning = !this.messages[index].showReasoning;
    },
    async loadAvailableModels() {
      try {
        const response = await fetch(`${this.apiUrl}/models`);
        if (!response.ok) throw new Error('加载可用模型失败');
        this.availableModels = await response.json();
        console.log('加载到的可用模型:', this.availableModels);
        
        // 从后端获取默认模型
        const defaultModelResponse = await fetch(`${this.apiUrl}/default_model`);
        if (defaultModelResponse.ok) {
          const defaultModel = await defaultModelResponse.json();
          this.selectedModel = defaultModel;
          console.log('设置默认模型:', defaultModel);
        }
      } catch (error) {
        console.error('加载可用模型失败:', error);
      }
    },
    async sendMessage() {
      if (!this.newMessage.trim() || this.isLoading || !this.currentConversationId) return;
      
      const message = this.newMessage;
      this.newMessage = '';
      this.isLoading = true;
      this.shouldAutoScroll = true;
      
      console.log('发送消息:', {
        message,
        model: this.selectedModel,
        conversationId: this.currentConversationId,
        streaming: this.isStreamingEnabled
      });
      
      // 添加用户消息
      this.messages.push({
        content: message,
        isUser: true,
        timestamp: new Date().toLocaleString()
      });
      
      try {
        const response = await fetch(`${this.apiUrl}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message,
            conversation_id: this.currentConversationId,
            model_name: this.selectedModel
          })
        });

        if (this.isStreamingEnabled) {
          // 流式输出模式
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let fullResponse = '';
          let fullReasoning = '';
          let isComplete = false;

          console.log('开始流式输出');

          // 添加一个空的AI消息用于流式更新
          this.messages.push({
            content: '',
            reasoning: '',
            isUser: false,
            timestamp: new Date().toLocaleString(),
            isStreaming: true,
            showReasoning: true
          });

          while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');
            
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              
              try {
                const data = JSON.parse(line.slice(6));
                
                switch (data.type) {
                  case 'reasoning':
                    fullReasoning += data.content;
                    console.log('收到思考片段:', data.content);
                    // 更新最后一条消息的思考内容
                    const currentMessage = this.messages[this.messages.length - 1];
                    currentMessage.reasoning = fullReasoning;
                    // 在每次更新内容后滚动到底部
                    this.$nextTick(() => {
                      if (this.shouldAutoScroll) {
                        this.scrollToBottom();
                      }
                    });
                    break;
                  case 'answer_start':
                    console.log('开始回答阶段');
                    // 更新最后一条消息的状态
                    const startMessage = this.messages[this.messages.length - 1];
                    startMessage.isAnswering = true;
                    break;
                  case 'answer':
                    fullResponse += data.content;
                    console.log('收到回答片段:', data.content);
                    // 更新最后一条消息的内容
                    const lastMessage = this.messages[this.messages.length - 1];
                    lastMessage.content = fullResponse;
                    if (fullResponse) {
                      lastMessage.isStreaming = false;
                    }
                    // 在每次更新内容后滚动到底部
                    this.$nextTick(() => {
                      if (this.shouldAutoScroll) {
                        this.scrollToBottom();
                      }
                    });
                    break;
                  case 'done':
                    isComplete = true;
                    console.log('流式输出完成', {
                      fullResponse,
                      fullReasoning,
                      messages: data.messages
                    });
                    // 更新对话列表
                    this.conversations = this.conversations.map(conv => 
                      conv.id === this.currentConversationId 
                        ? { ...conv, messages: data.messages }
                        : conv
                    );
                    break;
                  case 'error':
                    console.error('流式输出错误:', data.error);
                    throw new Error(data.error);
                }
              } catch (e) {
                console.error('解析数据失败:', e, '原始数据:', line);
                throw e;
              }
            }
          }
        } else {
          // 非流式输出模式
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let fullResponse = '';
          let fullReasoning = '';
          let isComplete = false;

          while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');
            
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              
              try {
                const data = JSON.parse(line.slice(6));
                
                switch (data.type) {
                  case 'reasoning':
                    fullReasoning += data.content;
                    break;
                  case 'answer':
                    fullResponse += data.content;
                    break;
                  case 'done':
                    isComplete = true;
                    // 添加完整的AI响应
                    this.messages.push({
                      content: fullResponse,
                      reasoning: fullReasoning,
                      isUser: false,
                      timestamp: new Date().toLocaleString(),
                      showReasoning: true
                    });
                    // 更新对话列表
                    this.conversations = this.conversations.map(conv => 
                      conv.id === this.currentConversationId 
                        ? { ...conv, messages: data.messages }
                        : conv
                    );
                    break;
                  case 'error':
                    console.error('流式输出错误:', data.error);
                    throw new Error(data.error);
                }
              } catch (e) {
                console.error('解析数据失败:', e, '原始数据:', line);
                throw e;
              }
            }
          }
        }

      } catch (error) {
        console.error('发送消息失败:', error);
        // 添加错误消息
        this.messages.push({
          content: `发送消息失败: ${error.message}`,
          isUser: false,
          isError: true,
          timestamp: new Date().toLocaleString()
        });
      } finally {
        this.isLoading = false;
        // 滚动到底部
        this.$nextTick(() => {
          if (this.shouldAutoScroll) {
            this.scrollToBottom();
          }
        });
      }
    },
    scrollToBottom() {
      const container = this.$refs.messagesContainer;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    },
    // 添加滚动事件处理
    handleScroll() {
      const container = this.$refs.messagesContainer;
      if (container) {
        // 如果用户向上滚动超过一定距离，禁用自动滚动
        const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
        this.shouldAutoScroll = isAtBottom;
      }
    },
    async copyMessage(content, event) {
      try {
        if (!event || !event.currentTarget) {
          console.error('复制失败: 事件对象无效');
          return;
        }

        // 移除HTML标签，只复制纯文本
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = content;
        const textToCopy = tempDiv.textContent || tempDiv.innerText;
        
        await navigator.clipboard.writeText(textToCopy);
        
        // 显示复制成功的提示
        const copyBtn = event.currentTarget;
        if (copyBtn) {
          const originalIcon = copyBtn.textContent;
          copyBtn.textContent = '✓';
          copyBtn.classList.add('copied');
          
          setTimeout(() => {
            if (copyBtn) {
              copyBtn.textContent = originalIcon;
              copyBtn.classList.remove('copied');
            }
          }, 2000);
        }
      } catch (err) {
        console.error('复制失败:', err);
        alert('复制失败，请重试');
      }
    },
    toggleSidebar() {
      this.showMobileMenu = !this.showMobileMenu;
      document.body.style.overflow = this.showMobileMenu ? 'hidden' : '';
    },
    selectConversation(id) {
      this.switchConversation(id);
      this.toggleSidebar();
    },
    checkMobile() {
      this.isMobile = window.innerWidth <= 768;
      if (!this.isMobile) {
        this.showMobileMenu = false;
      }
    }
  },
  watch: {
    messages: {
      handler() {
        this.$nextTick(() => {
          if (this.shouldAutoScroll) {
            this.scrollToBottom();
          }
        });
      },
      deep: true
    },
    selectedModel(newModel) {
      console.log('切换模型:', newModel);
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  overflow: hidden;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: #f8f9fa;
}

.conversations-sidebar {
  width: 280px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 15px;
  border-right: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
  flex-shrink: 0;
  height: 100%;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
}

.new-conversation-btn {
  width: 100%;
  padding: 12px;
  background: #007AFF;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 122, 255, 0.2);
}

.new-conversation-btn:hover {
  background: #0056b3;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 122, 255, 0.3);
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 8px;
}

.conversation-item {
  padding: 12px;
  background: #ffffff;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.conversation-item:hover {
  background: #f8f9fa;
  transform: translateX(4px);
  border-color: rgba(0, 122, 255, 0.2);
}

.conversation-item.active {
  background: #e3f2fd;
  border-left: 4px solid #007AFF;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.1);
}

.conversation-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: #333;
}

.delete-btn {
  background: none;
  border: none;
  color: #dc3545;
  font-size: 20px;
  cursor: pointer;
  padding: 0 5px;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.delete-btn:hover {
  color: #c82333;
  transform: scale(1.1);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  overflow: hidden;
  min-width: 0;
  height: 100%;
  position: relative;
}

.nav-bar {
  height: 56px;
  padding: 0 16px;
  background: #ffffff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 100;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  margin: 0 16px;
  flex: 1;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.menu-btn, .new-chat-btn {
  width: 40px;
  height: 40px;
  padding: 0;
  border: none;
  background: none;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #666;
  transition: all 0.2s ease;
}

.menu-btn:hover, .new-chat-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #333;
}

.menu-icon {
  font-size: 20px;
}

.plus-icon {
  font-size: 24px;
}

.mobile-menu {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  animation: fadeIn 0.2s ease;
}

.menu-content {
  width: 280px;
  height: 100%;
  background: #ffffff;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  padding: 16px;
  overflow-y: auto;
  animation: slideIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}

.menu-section {
  margin-bottom: 24px;
}

.menu-section h3 {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
  padding: 0 4px;
}

.menu-conversations {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.menu-conversation-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s ease;
}

.menu-conversation-item:hover {
  background: #e9ecef;
}

.menu-conversation-item.active {
  background: #e3f2fd;
  border-left: 3px solid #007AFF;
}

.model-selector {
  margin-top: auto;
  padding: 12px 0;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.model-select-wrapper {
  position: relative;
  width: 100%;
}

.model-select {
  width: 100%;
  padding: 12px 36px 12px 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: #ffffff;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  transition: all 0.2s ease;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}

.model-select-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #666;
  font-size: 12px;
}

.model-select:hover {
  border-color: #007AFF;
  background: #f8f9fa;
}

.model-select:focus {
  outline: none;
  border-color: #007AFF;
  box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.1);
}

.model-select:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  background: #f8f9fa;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  position: absolute;
  top: 52px;
  bottom: 80px;
  left: 0;
  right: 0;
  scroll-behavior: smooth;
  background: #f8f9fa;
}

.messages-container {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding-bottom: 20px;
}

.message {
  display: flex;
  flex-direction: column;
  width: 100%;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-wrapper {
  display: flex;
  margin-bottom: 20px;
  gap: 12px;
  max-width: 100%;
  width: fit-content;
}

.message-wrapper.user-message {
  flex-direction: row-reverse;
  margin-left: auto;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.message-content {
  position: relative;
  flex: 1;
  padding: 12px 16px;
  border-radius: 12px;
  background: #ffffff;
  max-width: 95%;
  min-width: 200px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

.message-wrapper.user-message .message-content {
  background: #007AFF;
  color: white;
  max-width: 95%;
  min-width: 200px;
  white-space: pre-line;
  overflow-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.2);
}

/* 思考过程样式优化 */
.reasoning-section {
  margin-bottom: 16px;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f9fa;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

.reasoning-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #e9ecef;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.reasoning-header:hover {
  background: #dee2e6;
}

.reasoning-header span {
  font-size: 13px;
  font-weight: 500;
  color: #495057;
}

.toggle-icon {
  font-size: 12px;
  color: #6c757d;
  transition: transform 0.2s ease;
}

.reasoning-content {
  padding: 12px 16px;
  background: #f8f9fa;
  color: #495057;
  font-size: 14px;
  line-height: 1.6;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  white-space: pre-wrap;
}

/* 暗色模式下的思考过程样式 */
@media (prefers-color-scheme: dark) {
  .reasoning-section {
    background: #2d2d2d;
    border-color: rgba(255, 255, 255, 0.1);
  }

  .reasoning-header {
    background: #3d3d3d;
    border-bottom-color: rgba(255, 255, 255, 0.1);
  }

  .reasoning-header:hover {
    background: #4d4d4d;
  }

  .reasoning-header span {
    color: #e9ecef;
  }

  .toggle-icon {
    color: #adb5bd;
  }

  .reasoning-content {
    background: #2d2d2d;
    color: #e9ecef;
    border-top-color: rgba(255, 255, 255, 0.1);
  }
}

/* 优化 markdown 样式 */
.message-text {
  margin-top: 8px;
  line-height: 1.6;
  font-size: 15px;
  color: inherit;
}

.message-text :deep(p) {
  margin: 0 0 1em 0;
  line-height: 1.6;
}

.message-text :deep(strong) {
  font-weight: 600;
}

.message-text :deep(em) {
  font-style: italic;
}

.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  margin: 1em 0 0.5em 0;
  line-height: 1.2;
  font-weight: 600;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 0.5em 0;
  padding-left: 2em;
}

.message-text :deep(li) {
  margin: 0.25em 0;
}

.message-text :deep(code) {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
}

.message-text :deep(pre) {
  background: rgba(0, 0, 0, 0.05);
  padding: 1em;
  border-radius: 5px;
  overflow-x: auto;
  margin: 1em 0;
}

.message-text :deep(pre code) {
  background: none;
  padding: 0;
  border-radius: 0;
  font-size: 0.9em;
}

.message-text :deep(blockquote) {
  margin: 1em 0;
  padding: 0.5em 1em;
  border-left: 4px solid rgba(0, 0, 0, 0.1);
  color: rgba(0, 0, 0, 0.6);
}

.message-text :deep(a) {
  color: #007AFF;
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
}

.message-text :deep(th),
.message-text :deep(td) {
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 0.5em;
}

.message-text :deep(th) {
  background: rgba(0, 0, 0, 0.05);
  font-weight: 600;
}

/* 暗色模式下的 markdown 样式 */
@media (prefers-color-scheme: dark) {
  .message-text :deep(code) {
    background: rgba(255, 255, 255, 0.1);
  }

  .message-text :deep(pre) {
    background: rgba(255, 255, 255, 0.1);
  }

  .message-text :deep(blockquote) {
    border-left-color: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.6);
  }

  .message-text :deep(th) {
    background: rgba(255, 255, 255, 0.1);
  }

  .message-text :deep(th),
  .message-text :deep(td) {
    border-color: rgba(255, 255, 255, 0.1);
  }
}

/* 移除可能冲突的样式 */
.message-wrapper.user-message .message-content {
  background: #007AFF;
  color: white;
  max-width: 95%;
  min-width: 200px;
  white-space: pre-line;
  overflow-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.2);
}

.message-wrapper.user-message .message-text {
  color: inherit;
}

.chat-input-container {
  padding: 15px;
  background: #ffffff;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 80px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.05);
}

.chat-input-wrapper {
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.chat-input {
  display: flex;
  gap: 10px;
  width: 100%;
}

input {
  flex: 1;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  font-size: 16px;
  min-width: 0;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

input:focus {
  outline: none;
  border-color: #007AFF;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.1);
}

input:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
}

button {
  padding: 12px 24px;
  background: #007AFF;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 122, 255, 0.2);
}

button:hover:not(:disabled) {
  background: #0056b3;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 122, 255, 0.3);
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
  box-shadow: none;
}

.loading {
  display: flex;
  align-items: center;
  min-height: 40px;
}

.loading-dots {
  display: inline-flex;
  gap: 4px;
  margin-left: 8px;
  vertical-align: middle;
}

.loading-dots span {
  width: 4px;
  height: 4px;
  background: currentColor;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* 滚动条样式 */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

/* 响应式布局 */
@media (min-width: 769px) {
  .chat-container {
    flex-direction: row;
  }

  .conversations-sidebar {
    display: flex;
    width: 280px;
    height: 100%;
  }

  .mobile-controls {
    display: none;
  }

  .mobile-dropdown {
    display: none;
  }
}

@media (max-width: 768px) {
  .chat-container {
    flex-direction: column;
  }

  .conversations-sidebar {
    display: none;
  }

  .mobile-controls {
    display: flex;
  }

  .mobile-dropdown {
    display: flex;
  }

  .nav-bar {
    padding: 0 12px;
  }

  .nav-title {
    font-size: 14px;
    margin: 0 8px;
  }

  .chat-messages {
    top: 56px;
  }

  .messages-container {
    max-width: 100%;
    padding: 0 12px;
  }
  
  .chat-input-wrapper {
    max-width: 100%;
    padding: 0 12px;
  }
  
  .message-content {
    max-width: 98%;
  }
}

/* 暗色模式支持 */
@media (prefers-color-scheme: dark) {
  .chat-container {
    background: #1a1a1a;
  }

  .conversations-sidebar,
  .chat-main,
  .nav-bar,
  .chat-input-container {
    background: #2d2d2d;
    border-color: rgba(255, 255, 255, 0.1);
  }

  .conversation-item {
    background: #2d2d2d;
    border-color: rgba(255, 255, 255, 0.1);
  }

  .conversation-item:hover {
    background: #3d3d3d;
  }

  .conversation-item.active {
    background: #1e3a5f;
  }

  .conversation-title {
    color: #ffffff;
  }

  .message-content {
    background: #2d2d2d;
    color: #ffffff;
  }

  input {
    background: #2d2d2d;
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.1);
  }

  input:focus {
    border-color: #007AFF;
  }

  .chat-messages {
    background: #1a1a1a;
  }
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.copy-btn {
  background: none;
  border: none;
  padding: 4px 8px;
  cursor: pointer;
  opacity: 0.5;
  transition: all 0.2s ease;
  border-radius: 4px;
  font-size: 16px;
  color: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  min-height: 24px;
}

.copy-btn:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.05);
}

.copy-btn.copied {
  opacity: 1;
  color: #28a745;
  background: rgba(40, 167, 69, 0.1);
}

.message-wrapper.user-message .copy-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.message-wrapper.user-message .copy-btn.copied {
  background: rgba(255, 255, 255, 0.2);
}

/* 暗色模式下的复制按钮样式 */
@media (prefers-color-scheme: dark) {
  .copy-btn:hover {
    background: rgba(255, 255, 255, 0.1);
  }
  
  .copy-btn.copied {
    background: rgba(40, 167, 69, 0.2);
  }
}

/* 移动端样式 */
.mobile-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 12px;
}

.mobile-btn {
  padding: 8px 12px;
  font-size: 14px;
  white-space: nowrap;
}

.menu-btn {
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  font-size: 20px;
  color: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.menu-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.mobile-dropdown {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 52px 12px 12px;
}

.dropdown-content {
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 280px;
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  padding: 16px;
}

.dropdown-section {
  margin-bottom: 20px;
}

.dropdown-section h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #495057;
}

.mobile-conversations {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.mobile-conversation-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.mobile-conversation-item:hover {
  background: #e9ecef;
}

.mobile-conversation-item.active {
  background: #e3f2fd;
  border-left: 4px solid #007AFF;
}

.mobile-model-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mobile-model-select:hover {
  border-color: #007AFF;
}

.mobile-model-select:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  background: #f8f9fa;
}

/* 暗色模式下的移动端样式 */
@media (prefers-color-scheme: dark) {
  .menu-btn:hover {
    background: rgba(255, 255, 255, 0.1);
  }

  .mobile-dropdown {
    background: rgba(0, 0, 0, 0.7);
  }

  .dropdown-content {
    background: #2d2d2d;
  }

  .dropdown-section h3 {
    color: #e9ecef;
  }

  .mobile-conversation-item {
    background: #3d3d3d;
    border-color: rgba(255, 255, 255, 0.1);
  }

  .mobile-conversation-item:hover {
    background: #4d4d4d;
  }

  .mobile-conversation-item.active {
    background: #1e3a5f;
  }

  .mobile-model-select {
    background: #2d2d2d;
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.1);
  }

  .mobile-model-select:disabled {
    background: #3d3d3d;
  }
}

/* 响应式布局优化 */
@media (max-width: 768px) {
  .chat-container {
    flex-direction: column;
  }

  .nav-bar {
    padding: 0 12px;
  }

  .nav-title {
    font-size: 14px;
    margin: 0 8px;
  }

  .chat-messages {
    top: 56px;
  }

  .messages-container {
    max-width: 100%;
    padding: 0 12px;
  }
  
  .chat-input-wrapper {
    max-width: 100%;
    padding: 0 12px;
  }
  
  .message-content {
    max-width: 98%;
  }
}

/* 流式输出开关样式 */
.streaming-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 20px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: .4s;
  border-radius: 20px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .toggle-slider {
  background-color: #007AFF;
}

input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.toggle-label {
  font-size: 14px;
  color: #666;
  user-select: none;
}

/* 暗色模式下的开关样式 */
@media (prefers-color-scheme: dark) {
  .streaming-toggle {
    background: rgba(255, 255, 255, 0.05);
  }

  .toggle-label {
    color: #e9ecef;
  }
}

/* 移动端样式适配 */
@media (max-width: 768px) {
  .streaming-toggle {
    margin-top: 8px;
    padding: 6px;
  }

  .toggle-label {
    font-size: 13px;
  }
}

/* 调整消息内容样式 */
.message-content-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-text {
  flex: 1;
}

.loading-dots {
  display: inline-flex;
  gap: 4px;
  margin-left: 8px;
  vertical-align: middle;
}

.loading-dots span {
  width: 4px;
  height: 4px;
  background: currentColor;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>

