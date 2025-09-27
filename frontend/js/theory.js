(() => {
    const messagesWrapper = document.querySelector('.messages-wrapper');
    const input = document.querySelector('.send-message-wrapper input');
    const sendButton = document.querySelector('.send-button');

    if (!messagesWrapper || !input || !sendButton) return;

    const pendingResponses = new Map();

    function scrollToBottom() {
        messagesWrapper.scrollTop = messagesWrapper.scrollHeight;
    }

    function createMessageElement(role, text, options = {}) {
        const wrapper = document.createElement('div');
        wrapper.className = `message message--${role}`;
        if (options.id) {
            wrapper.dataset.id = options.id;
        }

        const bubble = document.createElement('div');
        bubble.className = 'message__bubble';

        const content = document.createElement('div');
        content.className = 'message__text';
        content.textContent = text;
        bubble.appendChild(content);

        if (options.references && Array.isArray(options.references) && options.references.length) {
            const refsList = document.createElement('ul');
            refsList.className = 'message__refs';
            for (const ref of options.references) {
                const item = document.createElement('li');
                const label = ref.label || 'Reference';
                if (ref.url) {
                    const link = document.createElement('a');
                    link.href = ref.url;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    link.textContent = label;
                    item.appendChild(link);
                } else {
                    item.textContent = label;
                }
                if (ref.source && !item.textContent.includes(ref.source)) {
                    item.appendChild(document.createTextNode(` — ${ref.source}`));
                }
                refsList.appendChild(item);
            }
            bubble.appendChild(refsList);
        }

        wrapper.appendChild(bubble);
        messagesWrapper.appendChild(wrapper);
        scrollToBottom();
        return wrapper;
    }

    function updateMessageElement(element, text, options = {}) {
        if (!element) return;
        const content = element.querySelector('.message__text');
        if (content) {
            content.textContent = text;
        }

        const refsList = element.querySelector('.message__refs');
        if (refsList) {
            refsList.remove();
        }

        if (options.references && options.references.length) {
            const bubble = element.querySelector('.message__bubble');
            if (bubble) {
                const list = document.createElement('ul');
                list.className = 'message__refs';
                for (const ref of options.references) {
                    const item = document.createElement('li');
                    const label = ref.label || 'Reference';
                    if (ref.url) {
                        const link = document.createElement('a');
                        link.href = ref.url;
                        link.target = '_blank';
                        link.rel = 'noopener noreferrer';
                        link.textContent = label;
                        item.appendChild(link);
                    } else {
                        item.textContent = label;
                    }
                    if (ref.source && !item.textContent.includes(ref.source)) {
                        item.appendChild(document.createTextNode(` — ${ref.source}`));
                    }
                    list.appendChild(item);
                }
                bubble.appendChild(list);
            }
        }

        element.classList.toggle('message--error', Boolean(options.error));
        scrollToBottom();
    }

    function generateRequestId() {
        if (window.crypto?.randomUUID) {
            return window.crypto.randomUUID();
        }
        return `req_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    }

    function getFenForRequest() {
        try {
            return typeof get_current_fen === 'function' ? get_current_fen() : null;
        } catch (err) {
            console.warn('Unable to read current FEN', err);
            return null;
        }
    }

    function sendTheoryQuestion() {
        const message = input.value.trim();
        if (!message) {
            return;
        }

        const requestId = generateRequestId();
        createMessageElement('user', message, { id: `${requestId}-user` });
        input.value = '';
        input.focus();

        const placeholder = createMessageElement('assistant', 'Réflexion en cours...', { id: requestId });
        pendingResponses.set(requestId, placeholder);

        const payload = {
            question: message,
            fen: getFenForRequest(),
            request_id: requestId,
        };

        try {
            send_message('theory-question', payload);
        } catch (err) {
            console.error('Failed to send theory question', err);
            updateMessageElement(placeholder, 'Impossible d\'envoyer la question.', { error: true });
            pendingResponses.delete(requestId);
        }
    }

    sendButton.addEventListener('click', sendTheoryQuestion);
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendTheoryQuestion();
        }
    });

    // Welcome message for guidance
    createMessageElement(
        'assistant',
        "Pose une question sur la position actuelle ou sur un thème d'ouverture, milieu ou finale." +
        " Ajoute des détails si tu veux un conseil concret."
    );

    window.read_theory_answer = function readTheoryAnswer(data) {
        const payload = data || {};
        const requestId = payload.id;
        const target = requestId ? pendingResponses.get(requestId) : null;
        const references = Array.isArray(payload.references) ? payload.references : [];

        if (!target) {
            const text = payload.error ? `Assistant indisponible : ${payload.error}` : (payload.answer || '');
            createMessageElement(payload.error ? 'system' : 'assistant', text, {
                id: requestId || undefined,
                references,
                error: Boolean(payload.error),
            });
            return;
        }

        if (payload.error) {
            updateMessageElement(target, `Désolé, ${payload.error}`, {
                error: true,
            });
            if (typeof clear_advice_move === 'function') {
                clear_advice_move();
            }
        } else {
            updateMessageElement(target, payload.answer || 'Aucune réponse disponible.', {
                references,
            });
            if (payload.recommended_move && typeof show_advice_move === 'function') {
                try {
                    if (payload.recommended_move.showcase_fen)
                        draw_from_fen(payload.recommended_move.showcase_fen);

                    show_advice_move(payload.recommended_move);
                } catch (err) {
                    console.warn('Unable to display advice move', err);
                }
            }
        }

        pendingResponses.delete(requestId);
    };
})();
