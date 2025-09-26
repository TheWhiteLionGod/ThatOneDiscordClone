document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const messageContainer = document.getElementById('message-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const channelLinks = document.querySelectorAll('.channel-link');
    const createChannelBtn = document.querySelector('.create-channel-btn');
    const createChannelModal = document.getElementById('create-channel-modal');
    const modalCloseBtn = createChannelModal.querySelector('.modal-close-btn');

    let currentChannelId = null;

    // Connect to WebSocket and handle channel joining
    socket.on('connect', () => {
        console.log('Connected to server via WebSocket.');
        // Auto-join the first channel on load
        if (channelLinks.length > 0) {
            channelLinks[0].click();
        }
    });

    // Handle messages broadcasted from the server
    socket.on('new_message', (data) => {
        const messageItem = createMessageElement(data.author, data.content, data.timestamp);
        messageContainer.appendChild(messageItem);
        messageContainer.scrollTop = messageContainer.scrollHeight;
    });

    // Handle initial message history when joining a channel
    socket.on('message_history', (data) => {
        messageContainer.innerHTML = '';
        data.messages.forEach(msg => {
            const messageItem = createMessageElement(msg.author, msg.content, msg.timestamp);
            messageContainer.appendChild(messageItem);
        });
        messageContainer.scrollTop = messageContainer.scrollHeight;
    });

    // Handle status messages from the server
    socket.on('status', (data) => {
        const statusItem = document.createElement('div');
        statusItem.classList.add('status-message');
        statusItem.textContent = data.msg;
        messageContainer.appendChild(statusItem);
        messageContainer.scrollTop = messageContainer.scrollHeight;
    });

    // Handle sending messages
    function sendMessage() {
        const msg = messageInput.value.trim();
        if (msg && currentChannelId) {
            socket.emit('send_message', { 'channel_id': currentChannelId, 'content': msg });
            messageInput.value = '';
        }
    }

    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Handle channel switching
    channelLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Leave previous channel
            if (currentChannelId) {
                socket.emit('leave_channel', { 'channel_id': currentChannelId });
            }
            
            // Join new channel
            const newChannelId = link.dataset.channelId;
            socket.emit('join_channel', { 'channel_id': newChannelId });
            currentChannelId = newChannelId;

            // Update active link and header
            document.querySelector('.channel-link.active')?.classList.remove('active');
            link.classList.add('active');
            document.querySelector('.chat-channel-name').textContent = link.textContent.trim();
        });
    });

    // Handle create channel modal
    createChannelBtn.addEventListener('click', () => {
        createChannelModal.classList.add('visible');
    });

    modalCloseBtn.addEventListener('click', () => {
        createChannelModal.classList.remove('visible');
    });

    createChannelModal.addEventListener('click', (e) => {
        if (e.target === createChannelModal) {
            createChannelModal.classList.remove('visible');
        }
    });

    // Helper function to create a message element
    function createMessageElement(author, content, timestamp) {
        const messageItem = document.createElement('div');
        messageItem.classList.add('message-item', 'animated');
        messageItem.innerHTML = `
            <div class="message-avatar"></div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-author">${author}</span>
                    <span class="message-timestamp">${timestamp}</span>
                </div>
                <div class="message-text">${content}</div>
            </div>
        `;
        return messageItem;
    }
});
