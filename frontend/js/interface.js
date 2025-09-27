const { PopUp, Navigator, ContextMenu, EditableText, DataTable, Toast, LoadingScreen } = Toolbox;
const socket = new WebSocket("ws://127.0.0.1:5384");
const socket_data = {last_message: null};



// Interface funcs
function send_message(type, data = '', waiting_screen = false, msg = '') {
    if (waiting_screen) {
        LoadingScreen.show();  // active simplement l'écran
        LoadingScreen.update({
            main_steps: [{ title: msg || "Working...", progress: 0.0, info: "" }],
            detail: {}
        });
        waiting_for_response = true;
    }

    socket.send(JSON.stringify({
        type: type,
        data: data
    }));
}

async function send_file_in_chunks(file, folder = [], chunkSize = 1024 * 64, msg = '', show_loading = true) {
    const totalChunks = Math.ceil(file.size / chunkSize);
    const uploadId = Date.now().toString();

    const loading_progress_bar = d3.select("#loading-progress");

    if (show_loading) {
        LoadingScreen.show();
        LoadingScreen.update({
            main_steps: [{
                title: msg || "Uploading...",
                progress: 0.0,
                info: ""
            }],
            detail: {}
        });
    }

    socket.send(JSON.stringify({
        type: "start_chunked_upload",
        data: {
            upload_id: uploadId,
            folder: folder,
            filename: file.name.replaceAll('/', '_').replaceAll('\\', '_'),
            total_chunks: totalChunks
        }
    }));

    for (let offset = 0, chunkIndex = 0; offset < file.size; offset += chunkSize, chunkIndex++) {
        const chunk = file.slice(offset, offset + chunkSize);

        const base64data = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const uint8Array = new Uint8Array(e.target.result);
                const binaryString = Array.from(uint8Array).map(b => String.fromCharCode(b)).join('');
                resolve(btoa(binaryString));
            };
            reader.onerror = reject;
            reader.readAsArrayBuffer(chunk);
        });

        socket.send(JSON.stringify({
            type: "chunk",
            data: {
                upload_id: uploadId,
                chunk_index: chunkIndex,
                bin64: base64data
            }
        }));

        if (show_loading) {
            const percent = ((chunkIndex + 1) / totalChunks);
            LoadingScreen.update({
                main_steps: [{
                    title: msg || "Uploading...",
                    progress: percent,
                    info: `${Math.round(percent * 100)}%`
                }],
                detail: {
                    uploaded: `${chunkIndex + 1} / ${totalChunks} chunks`
                }
            });
        }
    }

    socket.send(JSON.stringify({
        type: "end_chunked_upload",
        data: {
            upload_id: uploadId
        }
    }));

    if (show_loading) LoadingScreen.hide()
}

async function wait_for_message(type, timeout = -1, only_content = false) {
    return new Promise((resolve, reject) => {
        let timeout_id = null
        if (timeout != -1) {
            timeout_id = setTimeout(() => {
                socket.removeEventListener("message", check_message)
                reject("Timeout");
            }, timeout);
        }

        function check_message(event) {
            try {
                message = JSON.parse(event.data);
            } catch (e) {
                console.error("Invalid JSON received:", event.data);
                return; // Ignore invalid messages
            }
            if (message && message.type == type) {
                if (timeout_id) clearTimeout(timeout_id);
                socket.removeEventListener("message", check_message);

                if (only_content && message.data && message.data.content) {
                    resolve(message.data.content);
                } else if (only_content && messsage.data) {
                    resolve(message.data);
                } else {
                    resolve(message);
                }
            }
        }

        socket.addEventListener("message", check_message);
    })
}

function wait_for_socket_ready() {
    return new Promise(resolve => {
        if (socket.readyState === WebSocket.OPEN) {
            resolve(); // socket déjà prêt
        } else {
            window.addEventListener("socket-ready", () => resolve(), { once: true });
        }
    });
}


// Sockets events
socket.onerror = (error) => {
    console.error("Error in WebSocket connection", error);
};

socket.onmessage = (event) => {
    content = read_message(event);
    socket_data.last_message = content;

    waiting_for_response = false;
};

socket.onopen = () => {
    
    LoadingScreen.hide()
    
    // Send a message to the server
    // socket.send(JSON.stringify({type: "info", data: { message: "Hello, server!" }}));
    window.dispatchEvent(new CustomEvent("socket-ready"));
};

socket.onclose = () => {
    message = `
        <div style="display: flex; flex-direction: column;">
            <span style="color: var(--danger-color); font-size: 1.2rem; margin-bottom: 10px;">Server socket closed, please refresh the page to reconnect.</span>
            <span style="font-style: italic; color: #888;">Make sure the python (backend) server is running. See README for more informations</span>
        </div>
    `
    // pop_up_showcase(message);
    PopUp.showcase(message)
    console.log("Disconnected from WebSocket server");
};
