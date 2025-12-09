/**
 * Autonomous Agent Frontend
 * WebSocket-based chat interface
 */

class AgentChat {
    constructor() {
        this.ws = null;
        this.clientId = null;
        this.isConnected = false;
        this.isProcessing = false;
        this.currentAssistantMessage = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        
        // DOM elements
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.connectionStatus = document.getElementById('connectionStatus');
        this.welcomeMessage = document.getElementById('welcomeMessage');
        
        // Bind event handlers
        this.handleSend = this.handleSend.bind(this);
        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.handleReset = this.handleReset.bind(this);
        
        // Initialize
        this.init();
    }
    
    init() {
        // Event listeners
        this.sendBtn.addEventListener('click', this.handleSend);
        this.messageInput.addEventListener('keydown', this.handleKeyDown);
        this.messageInput.addEventListener('input', () => this.autoResize());
        this.resetBtn.addEventListener('click', this.handleReset);
        
        // Connect to WebSocket
        this.connect();
    }
    
    connect() {
        const wsUrl = `ws://${window.location.host}/chat`;
        this.updateConnectionStatus('connecting');
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
                this.updateInputState();
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket closed', event);
                this.isConnected = false;
                this.updateConnectionStatus('disconnected');
                this.updateInputState();
                
                // Attempt reconnection
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
                    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
                    setTimeout(() => this.connect(), delay);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error', error);
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleServerMessage(message);
                } catch (e) {
                    console.error('Failed to parse message', e);
                }
            };
        } catch (e) {
            console.error('Failed to connect', e);
            this.updateConnectionStatus('disconnected');
        }
    }
    
    handleServerMessage(message) {
        console.log('Received:', message.type, message);
        
        switch (message.type) {
            case 'connected':
                this.clientId = message.data?.client_id;
                console.log('Connected as', this.clientId);
                break;
                
            case 'processing_start':
                this.isProcessing = true;
                this.updateInputState();
                this.hideWelcome();
                this.showProcessingIndicator();
                break;
                
            case 'iteration_start':
                const iteration = message.data?.iteration || 1;
                if (iteration > 1) {
                    this.showIterationIndicator(iteration);
                }
                break;
                
            case 'text_delta':
                this.appendToAssistantMessage(message.content || '');
                break;
                
            case 'tool_start':
                this.showToolIndicator(message.data?.tool_name, 'running');
                break;
                
            case 'tool_call_complete':
                // Tool call parsed, waiting for execution
                break;
                
            case 'executing_tools':
                // About to execute tools
                break;
                
            case 'tool_result':
                this.updateToolIndicator(
                    message.data?.tool_name,
                    message.data?.success ? 'success' : 'error',
                    message.data?.time_ms
                );
                break;
                
            case 'complete':
                this.isProcessing = false;
                this.hideProcessingIndicator();
                this.finalizeAssistantMessage();
                this.updateInputState();
                break;
                
            case 'max_iterations':
                this.isProcessing = false;
                this.hideProcessingIndicator();
                this.appendToAssistantMessage('\n\n*[Reached maximum iterations]*');
                this.finalizeAssistantMessage();
                this.updateInputState();
                break;
                
            case 'error':
                this.isProcessing = false;
                this.hideProcessingIndicator();
                this.showError(message.content || 'An error occurred');
                this.updateInputState();
                break;
                
            case 'status':
                if (message.content === 'Conversation reset') {
                    this.clearMessages();
                }
                break;
                
            case 'ping':
                // Respond to server ping
                this.send({ type: 'ping' });
                break;
                
            case 'pong':
                // Server responded to our ping
                break;
        }
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
    
    handleSend() {
        const content = this.messageInput.value.trim();
        if (!content || !this.isConnected || this.isProcessing) return;
        
        // Add user message
        this.addUserMessage(content);
        
        // Send to server
        this.send({ type: 'chat', content });
        
        // Clear input
        this.messageInput.value = '';
        this.autoResize();
    }
    
    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.handleSend();
        }
    }
    
    handleReset() {
        if (!this.isConnected) return;
        this.send({ type: 'reset' });
    }
    
    addUserMessage(content) {
        this.hideWelcome();
        
        const messageEl = document.createElement('div');
        messageEl.className = 'message user';
        messageEl.innerHTML = `
            <div class="message-avatar">👤</div>
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(content)}</div>
            </div>
        `;
        this.messagesContainer.appendChild(messageEl);
        this.scrollToBottom();
    }
    
    showProcessingIndicator() {
        // Create assistant message container
        this.currentAssistantMessage = document.createElement('div');
        this.currentAssistantMessage.className = 'message assistant';
        this.currentAssistantMessage.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="message-text"></div>
                <div class="tool-indicators"></div>
            </div>
        `;
        this.messagesContainer.appendChild(this.currentAssistantMessage);
        
        // Show processing spinner
        const textEl = this.currentAssistantMessage.querySelector('.message-text');
        textEl.innerHTML = '<div class="processing-indicator"><div class="spinner"></div><span>Thinking...</span></div>';
        
        this.scrollToBottom();
    }
    
    hideProcessingIndicator() {
        if (this.currentAssistantMessage) {
            const processingEl = this.currentAssistantMessage.querySelector('.processing-indicator');
            if (processingEl) {
                processingEl.remove();
            }
        }
    }
    
    appendToAssistantMessage(content) {
        if (!this.currentAssistantMessage) {
            this.showProcessingIndicator();
        }
        
        // Remove processing indicator if present
        this.hideProcessingIndicator();
        
        const textEl = this.currentAssistantMessage.querySelector('.message-text');
        textEl.textContent += content;
        this.scrollToBottom();
    }
    
    finalizeAssistantMessage() {
        if (this.currentAssistantMessage) {
            const textEl = this.currentAssistantMessage.querySelector('.message-text');
            // Convert markdown-style formatting
            textEl.innerHTML = this.formatMessage(textEl.textContent);
        }
        this.currentAssistantMessage = null;
    }
    
    showToolIndicator(toolName, status) {
        if (!this.currentAssistantMessage) return;
        
        const toolsEl = this.currentAssistantMessage.querySelector('.tool-indicators');
        const toolEl = document.createElement('div');
        toolEl.className = 'tool-indicator';
        toolEl.dataset.tool = toolName;
        toolEl.innerHTML = `
            <div class="tool-icon">⚙️</div>
            <span class="tool-name">${toolName}</span>
            <span class="tool-status">${status === 'running' ? '⏳ Running...' : status}</span>
        `;
        toolsEl.appendChild(toolEl);
        this.scrollToBottom();
    }
    
    updateToolIndicator(toolName, status, timeMs) {
        if (!this.currentAssistantMessage) return;
        
        const toolEl = this.currentAssistantMessage.querySelector(`.tool-indicator[data-tool="${toolName}"]`);
        if (toolEl) {
            const statusEl = toolEl.querySelector('.tool-status');
            statusEl.className = `tool-status ${status}`;
            if (status === 'success') {
                statusEl.textContent = `✓ ${timeMs ? Math.round(timeMs) + 'ms' : 'Done'}`;
            } else {
                statusEl.textContent = '✗ Failed';
            }
        }
    }
    
    showIterationIndicator(iteration) {
        const iterEl = document.createElement('div');
        iterEl.className = 'iteration-indicator';
        iterEl.textContent = `Iteration ${iteration}`;
        this.messagesContainer.appendChild(iterEl);
        this.scrollToBottom();
    }
    
    showError(message) {
        const errorEl = document.createElement('div');
        errorEl.className = 'message assistant';
        errorEl.innerHTML = `
            <div class="message-avatar">⚠️</div>
            <div class="message-content" style="border-color: var(--error);">
                <div class="message-text" style="color: var(--error);">${this.escapeHtml(message)}</div>
            </div>
        `;
        this.messagesContainer.appendChild(errorEl);
        this.scrollToBottom();
    }
    
    clearMessages() {
        this.messagesContainer.innerHTML = '';
        this.showWelcome();
        this.currentAssistantMessage = null;
    }
    
    hideWelcome() {
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'none';
        }
    }
    
    showWelcome() {
        if (this.welcomeMessage) {
            this.welcomeMessage.style.display = 'block';
        }
    }
    
    updateConnectionStatus(status) {
        const dot = this.connectionStatus.querySelector('.status-dot');
        const text = this.connectionStatus.querySelector('.status-text');
        
        dot.className = 'status-dot ' + status;
        text.textContent = status === 'connected' ? 'Connected' : 
                          status === 'connecting' ? 'Connecting...' : 'Disconnected';
    }
    
    updateInputState() {
        this.sendBtn.disabled = !this.isConnected || this.isProcessing || !this.messageInput.value.trim();
        this.messageInput.disabled = !this.isConnected || this.isProcessing;
        this.resetBtn.disabled = !this.isConnected || this.isProcessing;
    }
    
    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 200) + 'px';
        this.updateInputState();
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatMessage(text) {
        // Simple markdown-like formatting
        let html = this.escapeHtml(text);
        
        // Bold: **text**
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        
        // Italic: *text*
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        
        // Code: `code`
        html = html.replace(/`(.+?)`/g, '<code>$1</code>');
        
        // Preserve line breaks
        html = html.replace(/\n/g, '<br>');
        
        return html;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.agentChat = new AgentChat();
});
