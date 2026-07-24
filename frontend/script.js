(function () {
  'use strict';

  // ============================================
  // Elements
  // ============================================
  const chatColumn = document.getElementById('chatColumn');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  const fileInput = document.getElementById('fileInput');
  const modelSelect = document.getElementById('modelSelect');
  const modelDescription = document.getElementById('modelDescription');
  
  // Sidebar Elements
  const appSidebar = document.getElementById('appSidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const menuToggleBtn = document.getElementById('menuToggleBtn');
  const newChatBtn = document.getElementById('newChatBtn');
  const chatList = document.getElementById('chatList');
  const appMain = document.querySelector('.app-main');

  let currentChatId = null;

  // ============================================
  // Sidebar Logic
  // ============================================
  function toggleSidebar() {
    appSidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('active');
  }

  menuToggleBtn.addEventListener('click', toggleSidebar);
  sidebarOverlay.addEventListener('click', toggleSidebar);

  async function fetchChats() {
    try {
      const res = await fetch('/api/chats');
      if (!res.ok) return;
      const data = await res.json();
      renderChatList(data.chats);
    } catch (err) {
      console.error('Failed to load chats', err);
    }
  }

  function renderChatList(chats) {
    chatList.innerHTML = '';
    chats.forEach(chat => {
      const container = document.createElement('div');
      container.className = 'chat-item-container';
      container.style.display = 'flex';
      container.style.alignItems = 'center';
      
      const btn = document.createElement('button');
      btn.className = 'chat-item';
      btn.style.flex = '1';
      if (chat.id === currentChatId) btn.classList.add('active');
      btn.textContent = chat.title || 'New Chat';
      btn.addEventListener('click', () => {
        loadChat(chat.id);
        if (window.innerWidth < 768) {
          toggleSidebar();
        }
      });
      
      const delBtn = document.createElement('button');
      delBtn.className = 'icon-btn chat-delete-btn';
      delBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6 7H18M9 7V5C9 4.44772 9.44772 4 10 4H14C14.5523 4 15 4.44772 15 5V7M10 11V17M14 11V17M5 7L6 19C6 20.1046 6.89543 21 8 21H16C17.1046 21 18 20.1046 18 19L19 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      delBtn.style.padding = '8px';
      delBtn.style.marginLeft = '4px';
      delBtn.style.opacity = '0.6';
      
      delBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (confirm("Delete this chat?")) {
            try {
                await fetch(`/api/chats/${chat.id}`, { method: 'DELETE' });
                if (currentChatId === chat.id) {
                    newChatBtn.click();
                } else {
                    fetchChats();
                }
            } catch (err) {
                console.error("Failed to delete chat", err);
            }
        }
      });

      // Hover effects for the delete button
      delBtn.addEventListener('mouseenter', () => delBtn.style.opacity = '1');
      delBtn.addEventListener('mouseleave', () => delBtn.style.opacity = '0.6');
      
      container.appendChild(btn);
      container.appendChild(delBtn);
      chatList.appendChild(container);
    });
  }

  async function loadChat(chatId) {
    currentChatId = chatId;
    chatColumn.innerHTML = '';
    
    // Fetch chat history
    try {
      const res = await fetch(`/api/chats/${chatId}`);
      if (!res.ok) throw new Error('Failed to load chat');
      const data = await res.json();
      
      if (data.messages.length === 0) {
        showGreeting();
      } else {
        data.messages.forEach(msg => {
          // our DB stores 'assistant', render it as 'ai' for UI
          const role = msg.role === 'assistant' ? 'ai' : msg.role;
          appendMessage(role, msg.content, true);
        });
      }
      
      fetchChats();
      setTimeout(scrollToBottom, 50); // small delay to allow DOM to render
    } catch (err) {
      console.error(err);
      showGreeting();
    }
  }

  newChatBtn.addEventListener('click', async () => {
    currentChatId = null;
    chatColumn.innerHTML = '';
    showGreeting();
    fetchChats(); // removes active class
    if (window.innerWidth < 768) {
      toggleSidebar();
    }
  });

  // ============================================
  // Model descriptions
  // ============================================
  const MODEL_DESCRIPTIONS = {
    pluto: 'Ultra-powerful 70B AI for complex reasoning and tasks (Requires Internet).',
    pluto_lite: 'Fast 8B local AI for offline usage and absolute privacy.',
    echo: 'Autonomous desktop assistant for workflows and operations.'
  };

  function updateModelDescription() {
    const value = modelSelect.value;
    modelDescription.textContent = MODEL_DESCRIPTIONS[value] || '';
  }

  modelSelect.addEventListener('change', updateModelDescription);

  // ============================================
  // Auto-expanding textarea
  // ============================================
  const TEXTAREA_MAX_HEIGHT = 200;

  function autoExpand() {
    messageInput.style.height = 'auto';
    const newHeight = Math.min(messageInput.scrollHeight, TEXTAREA_MAX_HEIGHT);
    messageInput.style.height = newHeight + 'px';
    updateSendState();
  }

  messageInput.addEventListener('input', autoExpand);

  messageInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  function updateSendState() {
    const hasText = messageInput.value.trim().length > 0;
    sendBtn.disabled = !hasText;
  }

  // ============================================
  // Avatars
  // ============================================
  function avatarSVG(kind) {
    if (kind === 'user') {
      return `
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="16" cy="16" r="15" stroke="currentColor" stroke-width="1"/>
          <circle cx="16" cy="12.5" r="4.5" stroke="currentColor" stroke-width="1"/>
          <path d="M7.5 25C9 20.5 12 18.5 16 18.5C20 18.5 23 20.5 24.5 25" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
        </svg>`;
    }
    return `
      <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="16" r="15" stroke="currentColor" stroke-width="1"/>
        <circle cx="16" cy="16" r="4.5" fill="currentColor"/>
      </svg>`;
  }

  if (typeof marked !== 'undefined' && typeof hljs !== 'undefined') {
    marked.setOptions({
      highlight: function(code, lang) {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
      },
      breaks: true
    });
  }

  function appendMessage(role, text, skipScroll = false) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message ' + (role === 'user' ? 'user-message' : 'ai-message');

    const avatar = document.createElement('div');
    avatar.className = 'avatar ' + (role === 'user' ? 'avatar-user' : 'avatar-ai');
    avatar.setAttribute('aria-hidden', 'true');
    avatar.innerHTML = avatarSVG(role);

    const body = document.createElement('div');
    body.className = 'message-body';

    const author = document.createElement('div');
    author.className = 'message-author';
    author.textContent = role === 'user' ? 'You' : 'AskDeepakAI';

    const textEl = document.createElement('div');
    textEl.className = 'message-text markdown-body';
    if (typeof marked !== 'undefined') {
      textEl.innerHTML = marked.parse(text);
    } else {
      textEl.textContent = text;
    }

    body.appendChild(author);
    body.appendChild(textEl);
    wrapper.appendChild(avatar);
    wrapper.appendChild(body);
    chatColumn.appendChild(wrapper);

    if (!skipScroll) scrollToBottom();
    return wrapper;
  }

  function scrollToBottom() {
    appMain.scrollTo({
      top: appMain.scrollHeight,
      behavior: 'smooth'
    });
  }

  // ============================================
  // Send handling
  // ============================================
  async function handleSend() {
    const text = messageInput.value.trim();
    if (!text) return;

    // Create chat if this is the first message
    if (!currentChatId) {
      try {
        const res = await fetch('/api/chats', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: text.substring(0, 30) + '...' })
        });
        const data = await res.json();
        currentChatId = data.chat_id;
        
        // Remove greeting message if it exists
        chatColumn.innerHTML = '';
        fetchChats(); // refresh sidebar
      } catch (err) {
        console.error('Failed to create chat', err);
        return;
      }
    } else {
      // Check if greeting is there and clear it just in case
      const greeting = document.getElementById('greetingText');
      if (greeting) { chatColumn.innerHTML = ''; }
    }

    appendMessage('user', text);
    messageInput.value = '';
    autoExpand();
    messageInput.focus();

    const loadingWrapper = appendMessage('ai', 'Thinking...');

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          chat_id: currentChatId,
          prompt: text, 
          persona: modelSelect.value 
        })
      });
      
      if (!response.ok) throw new Error('Network error');
      const data = await response.json();
      
      loadingWrapper.remove();
      appendMessage('ai', data.response);
      fetchChats(); // To update title if it changed
    } catch (err) {
      console.error(err);
      loadingWrapper.remove();
      appendMessage('ai', 'Sorry, I encountered an error connecting to the backend.');
    }
  }

  sendBtn.addEventListener('click', handleSend);
  attachBtn.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', async function () {
    const files = Array.from(fileInput.files || []);
    if (!files.length) return;
    
    // Add loading indicator to the input while uploading
    const originalPlaceholder = messageInput.placeholder;
    messageInput.placeholder = 'Uploading...';
    messageInput.disabled = true;

    try {
      const formData = new FormData();
      formData.append('file', files[0]);

      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      
      const fileReference = `[Attached File: ${data.path}]`;
      messageInput.value += (messageInput.value ? '\n' : '') + fileReference;
      autoExpand();
    } catch (err) {
      console.error('File upload error:', err);
      alert('Failed to upload file.');
    } finally {
      messageInput.placeholder = originalPlaceholder;
      messageInput.disabled = false;
      fileInput.value = '';
    }
  });

  // ============================================
  // Init
  // ============================================
  function showGreeting() {
    const hour = new Date().getHours();
    let greeting = 'Good evening';
    if (hour >= 5 && hour < 12) greeting = 'Good morning';
    else if (hour >= 12 && hour < 18) greeting = 'Good afternoon';
    
    chatColumn.innerHTML = `
      <div class="message ai-message">
        <div class="avatar avatar-ai" aria-hidden="true">
          ${avatarSVG('ai')}
        </div>
        <div class="message-body">
          <div class="message-author">AskDeepakAI</div>
          <div class="message-text markdown-body" id="greetingText">${greeting}. What would you like to work through today?</div>
        </div>
      </div>
    `;
  }

  updateModelDescription();
  updateSendState();
  autoExpand();
  showGreeting();
  fetchChats();
})();
