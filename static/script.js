// WebSocket connection handling
let ws;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 3000; // 3 seconds

function connectWebSocket() {
    try {
        // Always use wss:// except for localhost development
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        const protocol = isLocalhost && window.location.protocol === 'http:' ? 'ws://' : 'wss://';

        // Function to get the correct path for an image
        function getImagePath(filename) {
            const staticPath = '/static/';
            if (filename.startsWith(staticPath) || filename.startsWith('/static/')) {
                return filename;
            }
            return staticPath + filename;
        }

        // Track selected agent profile
        window.selectedAgent = {
            name: null,
            img: getImagePath('unknown.jpg'),
            class: 'unknown'
        };

        // Listen for agent selection from HTML (index.html calls this)
        window.setAgentProfile = function(name) {
            const agents = {
                'Erica': { img: getImagePath('gambar1.jpg'), class: 'erica' },
                'Daniel': { img: getImagePath('gambar2.jpg'), class: 'Daniel' },
                'Paivi': { img: getImagePath('gambar3.jpg'), class: 'Paivi' },
                'Unknown': { img: getImagePath('unknown.jpg'), class: 'unknown' }
            };
            const agent = agents[name] || agents['Unknown'];
            window.selectedAgent = {
                name: name,
                img: agent.img,
                class: agent.class
            };
        };

        const host = window.location.host;
        const wsUrl = `${protocol}${host}/ws`;
        console.log('Attempting to connect to WebSocket at', wsUrl);
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('WebSocket connection established');
            reconnectAttempts = 0; 
            const status = document.getElementById('connection-status');
            if (status) status.textContent = 'Connected';
        };

        ws.onerror = function(error) {
            console.error('WebSocket error:', error);
        };

        ws.onclose = function(event) {
            console.log('WebSocket connection closed:', event.code, event.reason);
            const status = document.getElementById('connection-status') || (function() {
                const s = document.createElement('div');
                s.id = 'connection-status';
                s.style.position = 'fixed';
                s.style.bottom = '10px';
                s.style.right = '10px';
                s.style.padding = '5px 10px';
                s.style.background = '#ff4444';
                s.style.color = 'white';
                s.style.borderRadius = '4px';
                s.style.zIndex = '1000';
                document.body.appendChild(s);
                return s;
            })();
            
            if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
                status.textContent = 'Reconnecting...';
                status.style.background = '#ffbb33';
                reconnectAttempts++;
                console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
                setTimeout(connectWebSocket, reconnectDelay);
            } else {
                status.textContent = 'Disconnected. Please refresh the page.';
                status.style.background = '#ff4444';
                if (event.code !== 1000) {
                    alert('Connection lost. Please refresh the page to continue.');
                }
            }
        };

        const messageHistory = [];

        ws.onmessage = async function(event) {
            console.log('Raw message received:', event.data);

            let msg;
            try {
                msg = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
                console.log('Parsed message object:', JSON.stringify(msg, null, 2));
            } catch (e) {
                console.error('Error parsing message:', e);
                msg = { content: String(event.data) };
            }

            const chatbox = document.getElementById('chatbox');

            // Show typing indicator for 3 seconds before displaying the actual message
            const typingContainer = document.createElement('div');
            typingContainer.className = 'typing bot';
            typingContainer.id = 'typing-indicator';
            typingContainer.innerHTML = `<span></span><span></span><span></span>`;
            chatbox.appendChild(typingContainer);
            chatbox.scrollTop = chatbox.scrollHeight;

            // Wait for 3 seconds before showing the actual message
            await new Promise(resolve => setTimeout(resolve, 3000));

            // Remove typing indicator
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }

            // Continue with existing message handling
            try {
                const messageContent = msg.content || msg.message || msg.text || '';
                const messageType = msg.type || '';
                const skipDuplicateCheck = ['buttons', 'campaign', 'benefits'].includes(messageType);
                if (!skipDuplicateCheck) {
                    const isDuplicate = messageHistory.some(m => {
                        const sameContent = m.content === messageContent.trim();
                        const sameType = m.type === messageType;
                        const recent = (Date.now() - m.timestamp) < 1000;
                        return sameContent && sameType && recent;
                    });
                    if (isDuplicate) {
                        console.log('Skipping duplicate message:', { type: messageType, content: messageContent });
                        return;
                    }
                }

                const messageId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
                const messageObj = {
                    id: messageId,
                    content: messageContent.trim(),
                    type: messageType,
                    timestamp: Date.now(),
                    raw: JSON.parse(JSON.stringify(msg))
                };
                messageHistory.unshift(messageObj);
                while (messageHistory.length > 10) messageHistory.pop();

                const container = document.createElement('div');
                container.className = 'bot';
                const defaultAgent = {
                    name: 'Unknown',
                    class: 'unknown',
                    img: getImagePath('unknown.jpg')
                };
                const agent = window.selectedAgent || defaultAgent;

                const profileContainer = document.createElement('div');
                profileContainer.style.display = 'flex';
                profileContainer.style.alignItems = 'center';

                const profilePic = document.createElement('span');
                profilePic.className = `profile-pic ${agent.class || 'unknown'}`;
                profilePic.style.backgroundImage = `url('${agent.img}')`;
                profilePic.title = agent.name || 'Unknown Agent';

                const nameSpan = document.createElement('span');
                nameSpan.textContent = agent.name || '';
                nameSpan.style.marginLeft = '8px';
                nameSpan.style.fontWeight = 'bold';

                profileContainer.appendChild(profilePic);
                profileContainer.appendChild(nameSpan);
                container.appendChild(profileContainer);

                // Error handling
                if (msg.type === 'error') {
                    if (msg.reset) chatbox.innerHTML = '';
                    const lastMessage = chatbox.lastElementChild;
                    if (!lastMessage || !lastMessage.classList.contains('error') || lastMessage.textContent !== msg.content) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'error';
                        errorDiv.textContent = msg.content;
                        container.appendChild(errorDiv);
                    }
                }

                // Button messages
                if (msg.buttons && Array.isArray(msg.buttons)) {
                    if (msg.content || msg.text || msg.message) {
                        const textDiv = document.createElement('div');
                        const messageText = msg.content || msg.text || msg.message;
                        let formattedContent = messageText
                            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                            .replace(/\*(.*?)\*/g, '<em>$1</em>')
                            .replace(/\n/g, '<br>');
                        textDiv.innerHTML = formattedContent;
                        container.appendChild(textDiv);
                    }

                    const buttonContainer = document.createElement('div');
                    buttonContainer.className = 'button-group';
                    msg.buttons.forEach((btn) => {
                        const button = document.createElement('button');
                        button.className = 'chat-button btn';
                        button.textContent = btn.label || btn;
                        if (btn.value) {
                            button.value = btn.value;
                            button.dataset.value = btn.value;
                        }
                        button.onclick = async function(e) {
                            e.stopPropagation();
                            const value = btn.value || btn.label || btn;
                            const label = btn.label || btn;
                            const buttons = buttonContainer.querySelectorAll('button');
                            buttons.forEach(btn => {
                                btn.disabled = true;
                                btn.style.opacity = '0.7';
                                btn.style.cursor = 'not-allowed';
                            });
                            const choiceMessage = document.createElement('div');
                            choiceMessage.className = 'user-choice';
                            choiceMessage.textContent = `You selected: ${label}`;
                            container.appendChild(choiceMessage);
                            chatbox.scrollTop = chatbox.scrollHeight;
                            const message = { type: 'choice', value, label, timestamp: Date.now() };
                            ws.send(JSON.stringify(message));
                        };
                        buttonContainer.appendChild(button);
                    });
                    container.appendChild(buttonContainer);
                }

                // Campaign messages
                else if (msg.type === 'campaign') {
                    const campaignCard = document.createElement('div');
                    campaignCard.className = 'campaign-card';
                    const title = document.createElement('h3');
                    title.textContent = msg.title || 'Campaign';
                    campaignCard.appendChild(title);
                    if (msg.description) {
                        const desc = document.createElement('p');
                        desc.textContent = msg.description;
                        campaignCard.appendChild(desc);
                    }
                    const learnMoreBtn = document.createElement('button');
                    learnMoreBtn.className = 'campaign-button';
                    learnMoreBtn.textContent = 'Learn More';
                    learnMoreBtn.onclick = () => {
                        alert(`More information about ${msg.title} will be shown here.`);
                    };
                    campaignCard.appendChild(learnMoreBtn);
                    container.appendChild(campaignCard);
                }

                // Regular text messages
                else if (msg.type !== 'buttons') {
                    const textDiv = document.createElement('div');
                    const content = msg.content || msg.message || msg.text || event.data;
                    let formattedContent = content
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\*(.*?)\*/g, '<em>$1</em>')
                        .replace(/\n/g, '<br>');
                    textDiv.innerHTML = formattedContent;
                    container.appendChild(textDiv);
                }

                // Add message to chatbox
                if (container.childNodes.length > 0) {
                    chatbox.appendChild(container);
                    chatbox.scrollTop = chatbox.scrollHeight;
                }

            } catch (error) {
                console.error('Error processing message:', error);
                const container = document.createElement('div');
                container.className = 'bot error';
                container.textContent = 'Error: Could not process message';
                chatbox.appendChild(container);
                chatbox.scrollTop = chatbox.scrollHeight;
            }
        };

    } catch (error) {
        console.error('Error creating WebSocket:', error);
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            console.log(`Retrying connection (${reconnectAttempts}/${maxReconnectAttempts})...`);
            setTimeout(connectWebSocket, reconnectDelay);
        }
    }
}

// Initial connection
connectWebSocket();

// Send user message
function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (message === '') return;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        alert('Not connected to server. Please refresh the page.');
        return;
    }

    const chatbox = document.getElementById('chatbox');
    const userContainer = document.createElement('div');
    userContainer.className = 'user';

    const userProfileSpan = document.createElement('span');
    userProfileSpan.className = 'user-profile you';
    userProfileSpan.innerHTML = `<img src='/static/you.png' alt='You' style='width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;'><span style='color:black;font-weight:bold;font-size:0.95em;margin-left:6px;vertical-align:middle;'>You</span>`;
    userContainer.appendChild(userProfileSpan);

    const userTextDiv = document.createElement('div');
    userTextDiv.className = 'user-text';
    userTextDiv.textContent = message;
    userContainer.appendChild(userTextDiv);

    chatbox.appendChild(userContainer);
    chatbox.scrollTop = chatbox.scrollHeight;

    input.value = '';
    ws.send(JSON.stringify({ text: message }));
}

// Active button submissions
const activeButtonSubmissions = new Set();

function sendChoice(value, label) {
    const clickId = `${value}-${Date.now()}`;
    if (activeButtonSubmissions.has(clickId)) return;
    activeButtonSubmissions.add(clickId);

    const chatbox = document.getElementById('chatbox');
    const userChoice = document.createElement('div');
    userChoice.className = 'user';
    userChoice.textContent = label;
    chatbox.appendChild(userChoice);
    chatbox.scrollTop = chatbox.scrollHeight;

    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.style.opacity = '0.7';
        btn.style.cursor = 'not-allowed';
    });

    if (ws && ws.readyState === WebSocket.OPEN) {
        const message = { type: 'choice', value, label, timestamp: Date.now() };
        ws.send(JSON.stringify(message));

        setTimeout(() => {
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            });
            setTimeout(() => {
                activeButtonSubmissions.delete(clickId);
            }, 1000);
        }, 1000);
    } else {
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        });
        activeButtonSubmissions.delete(clickId);
    }
}

// DOM ready
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendBtn');

    if (messageInput && sendButton) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });

        sendButton.addEventListener('click', function(e) {
            e.preventDefault();
            sendMessage();
        });
    }
});
