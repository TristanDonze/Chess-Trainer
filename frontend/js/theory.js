(() => {
  const messagesWrapper = document.querySelector('.messages-wrapper');
  const input = document.querySelector('.send-message-wrapper input');
  const sendButton = document.querySelector('.send-button');
  const audioToggleText = document.querySelector('.switch-to-text');
  const audioToggleAudio = document.querySelector('.switch-to-audio');
  if (!messagesWrapper || !input || !sendButton) return;

  const pendingResponses = new Map();
  let isAudioMode = false;
  let isRecording = false;
  let mediaRecorder = null;
  let audioChunks = [];

  function scrollToBottom() {
    messagesWrapper.scrollTop = messagesWrapper.scrollHeight;
  }

  function createMessageElement(role, text, options = {}) {
    const wrapper = document.createElement('div');
    wrapper.className = `message message--${role}`;
    if (options.id) wrapper.dataset.id = options.id;

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
    if (content) content.textContent = text;

    const refsList = element.querySelector('.message__refs');
    if (refsList) refsList.remove();

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
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
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
    if (isAudioMode) {
      handleAudioInput();
    } else {
      handleTextInput();
    }
  }

  function handleTextInput() {
    const message = input.value.trim();
    if (!message) return;

    const requestId = generateRequestId();
    createMessageElement('user', message, { id: `${requestId}-user` });
    input.value = '';
    input.focus();

    const placeholder = createMessageElement('assistant', '♟️ Thinking...', { id: requestId });
    pendingResponses.set(requestId, placeholder);

    const payload = { question: message, fen: getFenForRequest(), request_id: requestId };

    try {
      send_message('theory-question', payload);
    } catch (err) {
      console.error('Failed to send theory question', err);
      updateMessageElement(placeholder, "Unable to send the question.", { error: true });
      pendingResponses.delete(requestId);
    }
  }

  async function handleAudioInput() {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Audio recording is not supported in your browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      isRecording = true;
      audioChunks = [];
      
            // Try different audio formats for better compatibility
            let options = {};
            if (MediaRecorder.isTypeSupported('audio/webm')) {
                options = { mimeType: 'audio/webm' };
            } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                options = { mimeType: 'audio/mp4' };
            } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
                options = { mimeType: 'audio/ogg' };
            }
            
            mediaRecorder = new MediaRecorder(stream, options);
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = async () => {
                const mimeType = mediaRecorder.mimeType || 'audio/webm';
                const audioBlob = new Blob(audioChunks, { type: mimeType });
                await sendAudioMessage(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };      mediaRecorder.start();
      updateRecordingUI(true);
      
      // Auto-stop recording after 30 seconds
      setTimeout(() => {
        if (isRecording) {
          stopRecording();
        }
      }, 30000);
    } catch (err) {
      console.error('Error starting audio recording:', err);
      alert('Unable to access microphone. Please check your permissions.');
      isRecording = false;
      updateRecordingUI(false);
    }
  }

  function stopRecording() {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      isRecording = false;
      updateRecordingUI(false);
    }
  }

  function updateRecordingUI(recording) {
    if (recording) {
      sendButton.textContent = 'stop';
      sendButton.style.background = '#ff4444';
      input.placeholder = '🎤 Recording... Click stop when done';
      input.disabled = true;
    } else {
      sendButton.textContent = isAudioMode ? 'mic' : 'send';
      sendButton.style.background = '';
      input.placeholder = isAudioMode ? 'Click microphone to record question...' : 'Type your message...';
      input.disabled = isAudioMode;
    }
  }

  async function sendAudioMessage(audioBlob) {
    const requestId = generateRequestId();
    createMessageElement('user', '🎤 [Voice message]', { id: `${requestId}-user` });

    const placeholder = createMessageElement('assistant', '♟️ Processing audio...', { id: requestId });
    pendingResponses.set(requestId, placeholder);

    try {
      // Convert audio blob to base64 using FileReader
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result.split(',')[1]; // Remove data URL prefix
          resolve(result);
        };
        reader.onerror = reject;
        reader.readAsDataURL(audioBlob);
      });

      const payload = {
        audio: {
          b64: base64,
          mime: audioBlob.type || 'audio/webm'
        },
        fen: getFenForRequest(),
        request_id: requestId
      };

      send_message('theory-question-audio', payload);
    } catch (err) {
      console.error('Failed to send audio message:', err);
      updateMessageElement(placeholder, "Unable to process audio message.", { error: true });
      pendingResponses.delete(requestId);
    }
  }

  function setAudioMode(enabled) {
    isAudioMode = enabled;
    if (audioToggleText) {
      audioToggleText.classList.toggle('active', !enabled);
    }
    if (audioToggleAudio) {
      audioToggleAudio.classList.toggle('active', enabled);
    }
    updateRecordingUI(false);
  }

  sendButton.addEventListener('click', sendTheoryQuestion);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !isAudioMode) {
      event.preventDefault();
      sendTheoryQuestion();
    }
  });

  // Audio toggle event listeners
  if (audioToggleText) {
    audioToggleText.addEventListener('click', () => setAudioMode(false));
  }
  if (audioToggleAudio) {
    audioToggleAudio.addEventListener('click', () => setAudioMode(true));
  }

  // Initialize in text mode
  setAudioMode(false);

  createMessageElement(
    'assistant',
    "Ask any question about chess theory, I will provide detailed explanations and suggestions in order to help you improve!"
  );

  // ---- NEW: unify handling of new 'instructions' and legacy 'recommended_move'
  function normalizeInstructions(payload) {
    // New schema
    if (payload && payload.instructions) {
      const ins = payload.instructions;
      return {
        showcase_fen: ins.showcase_fen || null,
        red_squares: Array.isArray(ins.red_squares) ? ins.red_squares : [],
        green_squares: Array.isArray(ins.green_squares) ? ins.green_squares : [],
        moves: Array.isArray(ins.moves) ? ins.moves : [],
      };
    }
    // Legacy fallback
    const rm = payload?.recommended_move;
    if (rm) {
      const move =
        rm.uci && rm.uci !== 'N/A'
          ? [{ uci: rm.uci, san: rm.san, from: rm.from, to: rm.to, promotion: rm.promotion }]
          : [];
      return {
        showcase_fen: rm.showcase_fen || null,
        red_squares: Array.isArray(rm.red_squares) ? rm.red_squares : [],
        green_squares: Array.isArray(rm.green_squares) ? rm.green_squares : [],
        moves: move,
      };
    }
    return { showcase_fen: null, red_squares: [], green_squares: [], moves: [] };
  }

  window.read_theory_answer = function readTheoryAnswer(data) {
    const payload = data || {};
    const requestId = payload.id;
    const target = requestId ? pendingResponses.get(requestId) : null;
    const references = Array.isArray(payload.references) ? payload.references : [];

    if (!target) {
      const text = payload.error ? `Trainer unavailable : ${payload.error}` : (payload.answer || '');
      createMessageElement(payload.error ? 'system' : 'Trainer', text, {
        id: requestId || undefined,
        references,
        error: Boolean(payload.error),
      });
      return;
    }

    if (payload.error) {
      updateMessageElement(target, `Sorry, ${payload.error}`, { error: true });
      if (typeof clear_advice_move === 'function') clear_advice_move();
      if (typeof highlight_square === 'function') highlight_square(); // clear
      pendingResponses.delete(requestId);
      return;
    }

    updateMessageElement(target, payload.answer || 'Aucune réponse disponible.', { references });

    const instr = normalizeInstructions(payload);

    // Clear previous highlights/arrows if helpers exist
    if (typeof clear_advice_move === 'function') clear_advice_move();
    if (typeof highlight_square === 'function') highlight_square();

    if (instr.showcase_fen && typeof draw_from_fen === 'function') {
      draw_from_fen(instr.showcase_fen);
    }

    if (instr.moves && instr.moves.length) {
      if (typeof show_advice_moves === 'function') {
        // If you implemented a multi-move renderer
        show_advice_moves(instr.moves);
      } else if (typeof show_advice_move === 'function') {
        // Fallback: show only the first move
        show_advice_move(instr.moves[0]);
      }
    }

    if (Array.isArray(instr.red_squares) && instr.red_squares.length && typeof highlight_square === 'function') {
      highlight_square(instr.red_squares, 'red');
    }
    // if (Array.isArray(instr.green_squares) && instr.green_squares.length && typeof highlight_square === 'function') {
    //   highlight_square(instr.green_squares, 'green');
    // }

    pendingResponses.delete(requestId);
  };
})();
