document.addEventListener('DOMContentLoaded', () => {
    let conversationId = generateUUID();
    const chatMessages = document.getElementById('chatMessages');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const typingIndicator = document.getElementById('typingIndicator');
    const newChatBtn = document.getElementById('newChatBtn');
    const suggestedChips = document.querySelectorAll('.chip');
    const initialTime = document.getElementById('initialTime');

    if (initialTime) {
        initialTime.textContent = formatTime(new Date());
    }

    // Helper: generate simple ID
    function generateUUID() {
        return 'conv_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now().toString(36);
    }

    // Helper: format time in Arabic/local format
    function formatTime(date) {
        return date.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    }

    // Scroll chat to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }


    // Minimal Markdown renderer (bold / italic / lists / line breaks).
    // Everything is HTML-escaped FIRST, so model output cannot inject markup.
    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function renderMarkdown(text) {
        const safe = escapeHtml(text || '');
        const lines = safe.split('\n');
        let html = '';
        let inList = false;
        for (const rawLine of lines) {
            const line = rawLine.trim();
            const isItem = /^[-*\u2022]\s+/.test(line) || /^\d+\.\s+/.test(line);
            if (isItem) {
                if (!inList) { html += '<ul>'; inList = true; }
                const item = line.replace(/^([-*\u2022]|\d+\.)\s+/, '');
                html += '<li>' + inlineMd(item) + '</li>';
            } else {
                if (inList) { html += '</ul>'; inList = false; }
                if (line) html += '<p>' + inlineMd(line) + '</p>';
            }
        }
        if (inList) html += '</ul>';
        return html || '<p></p>';
    }

    function inlineMd(s) {
        return s
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
            .replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
    }

    // Append a message bubble to the chat
    function appendMessage(sender, text, products = null, isError = false) {
        const row = document.createElement('div');
        row.className = `message-row ${sender}`;

        const avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.textContent = sender === 'assistant' ? '✨' : '👤';

        const bubbleWrapper = document.createElement('div');
        bubbleWrapper.className = 'msg-bubble-wrapper';

        const bubble = document.createElement('div');
        bubble.className = isError ? 'msg-bubble error' : 'msg-bubble';
        if (isError) {
            bubble.textContent = text;
        } else {
            bubble.innerHTML = renderMarkdown(text);
        }

        bubbleWrapper.appendChild(bubble);

        // Render product cards if available
        if (products && Array.isArray(products) && products.length > 0) {
            const grid = document.createElement('div');
            grid.className = 'products-cards-grid';

            const visibleImageBudget = 8;
            products.forEach(p => {
                const card = document.createElement('div');
                card.className = 'product-card';

                if (p.image_url) {
                    const img = document.createElement('img');
                    img.className = 'product-card-img';
                    img.alt = p.name;
                    img.decoding = 'async';
                    // Do NOT lazy-load the first row: a newly sent reply must
                    // show its photos immediately, otherwise the answer looks
                    // broken until the user happens to scroll.
                    if (products.indexOf(p) >= visibleImageBudget) {
                        img.loading = 'lazy';
                    } else {
                        // warm the HTTP cache so the <img> paints synchronously
                        // from the already-decoded entry
                        const pre = new Image();
                        pre.decoding = 'async';
                        pre.src = p.image_url;
                    }
                    img.src = p.image_url;
                    img.addEventListener('error', () => { img.remove(); });
                    card.appendChild(img);
                }

                const body = document.createElement('div');
                body.className = 'product-card-body';

                const badge = document.createElement('span');
                badge.className = 'product-card-badge';
                badge.textContent = p.category_ar || p.category || '';

                const title = document.createElement('div');
                title.className = 'product-card-title';
                title.textContent = p.name;

                const meta = document.createElement('div');
                meta.className = 'product-card-meta';
                const bits = [];
                if (p.color) bits.push(p.color);
                if (p.brand) bits.push(p.brand);
                meta.textContent = bits.join(' \u00b7 ');

                const price = document.createElement('div');
                price.className = 'product-card-price';
                price.textContent = `${Math.round(p.price)} جنيه`;

                const reason = document.createElement('div');
                reason.className = 'product-card-reason';
                reason.textContent = p.reason || '';

                body.appendChild(badge);
                body.appendChild(title);
                if (meta.textContent) body.appendChild(meta);
                body.appendChild(price);
                if (reason.textContent) body.appendChild(reason);

                card.appendChild(body);
                grid.appendChild(card);
            });

            bubbleWrapper.appendChild(grid);
        }

        const timeSpan = document.createElement('span');
        timeSpan.className = 'msg-time';
        timeSpan.textContent = formatTime(new Date());
        bubbleWrapper.appendChild(timeSpan);

        row.appendChild(avatar);
        row.appendChild(bubbleWrapper);

        chatMessages.appendChild(row);
        scrollToBottom();
    }

    // Expose the bubble renderer for optional UI modules.
    window.AssistantUI = { appendMessage: appendMessage, scrollToBottom: scrollToBottom };

    // Send message to backend
    async function handleSendMessage(text) {
        const cleanText = text.trim();
        if (!cleanText) return;

        // Display user message
        appendMessage('user', cleanText);
        messageInput.value = '';
        messageInput.disabled = true;
        sendBtn.disabled = true;

        // Show typing indicator
        typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    message: cleanText
                })
            });

            if (!response.ok) {
                const error = new Error(`Server returned status ${response.status}`);
                error.status = response.status;
                try {
                    const payload = await response.json();
                    if (payload && payload.detail) error.detail = payload.detail;
                } catch (parseError) {
                    // Response had no JSON body: keep the generic message.
                }
                throw error;
            }

            const data = await response.json();
            if (data.conversation_id) {
                conversationId = data.conversation_id;
            }

            // Hide typing indicator
            typingIndicator.style.display = 'none';

            // Display assistant reply
            appendMessage('assistant', data.message, data.products);

        } catch (error) {
            console.error('Chat error:', error);
            typingIndicator.style.display = 'none';

            appendMessage('assistant', error.detail || 'حصلت مشكلة مؤقتة. جرّب تاني.', null, true);
        } finally {
            messageInput.disabled = false;
            sendBtn.disabled = false;
            messageInput.focus();
            scrollToBottom();
        }
    }

    // Form submit listener
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleSendMessage(messageInput.value);
    });

    // Suggested chip clicks
    suggestedChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const promptText = chip.getAttribute('data-text');
            if (promptText) {
                handleSendMessage(promptText);
            }
        });
    });

    // New Chat / Reset
    newChatBtn.addEventListener('click', async () => {
        try {
            if (conversationId) {
                await fetch('/api/chat/reset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ conversation_id: conversationId })
                });
            }
        } catch (e) {
            console.warn('Could not reset on server:', e);
        }

        // Reset frontend conversation
        conversationId = generateUUID();

        // Clear messages except welcome
        chatMessages.innerHTML = `
            <div class="message-row assistant">
                <div class="msg-avatar">✨</div>
                <div class="msg-bubble-wrapper">
                    <div class="msg-bubble">
                        <p class="welcome-title">أهلاً 👋</p>
                        <p>أهلاً بيك 👋 أنا المساعد بتاع المتجر. قولّي بتدور على إيه وأنا أرشّحلك من عندنا على طول — جاكيت، فستان، بنطلون، أي حاجة.</p>
                    </div>
                    <span class="msg-time"></span>
                </div>
            </div>
        `;
        messageInput.focus();
    });
});
