
function read_message(event) {
    message_data = JSON.parse(event.data);
    console.log("Received message from server", message_data);
    
    switch (message_data.type) {
        case "ping":
            send_pong()
            break
    
        case "pop-up":
            read_popup_message(message_data.data.content);
            break;
        
        case "error": message_data.data.content['type'] = 'server-error'
        case "toast":
            read_toast_message(message_data.data.content);
            break;

        case "navigation":
            read_navigation_message(message_data.content);
            break

        case "loading":
            read_loading_message(message_data.data.content);
            break;

        case "game-started":
            read_game_started(message_data.data.content);
            break;
        case "confirm-move":
            game_state.turn = game_state.turn === "w" ? "b" : "w";
            read_confirm_move(message_data.data.content);
            break;
        case "ai-move":
            game_state.turn = game_state.turn === "w" ? "b" : "w";
            read_ai_move(message_data.data.content);
            break;
        default:
            return message_data
    }

    return message_data
}

function send_pong() {
    send_message('pong')
}

function read_popup_message(message) {
    PopUp.confirm(message.content, {
        on_yes: () => (message.callback ? window[data.callback]() : null)
    }).open();
}

function read_toast_message(message) {
    if (message.type == 'server-error') {
        Toast.error(message.content, 6000);
        LoadingScreen.hide()
    
    } else
        Toast.info(`${message.type} - ${message.content}`); // TODO: update dynamically
}

function read_navigation_message(message) {
    const { mode, url, params, target } = message.content;

    if (mode === "reload") {
        const currentUrl = new URL(window.location.href);
        if (params && typeof params === 'object') {
            Object.entries(params).forEach(([k, v]) => {
                currentUrl.searchParams.set(k, v);
            });
        }
        window.location.href = currentUrl.toString();
    }

    else if (mode === "redirect" && url) {
        window.location.href = url;
    }

    else if (mode === "back") {
        window.history.back();
    }

    else if (mode === "open" && url) {
        const t = target || '_blank';
        window.open(url, t);
    }
}

function read_loading_message(message) {
    // message.content should contain { action, main_steps, detail }
    const action = message.action;
    if (action === "show") {
        LoadingScreen.show();
        LoadingScreen.update(message);
    } else if (action === "update") {
        LoadingScreen.update(message);
    } else if (action === "hide") {
        LoadingScreen.hide();
    }
}


function read_game_started(data) {
    // data
    draw_game(data.FEN);
    update_game_state(data.FEN);
    LoadingScreen.hide();
    new Audio('../media/game-start.mp3').play();
}

function read_confirm_move(data) {
    // data
    game_state.king_in_check = data.king_in_check;
    game_state.checkmate = data.checkmate;
    game_state.draw = data.draw;
    if (game_state.draw) stalemate();
    update_game_state(data.FEN);
}

function read_ai_move(data) {
    // data

    game_state.king_in_check = data.king_in_check;
    game_state.checkmate = data.checkmate;
    game_state.draw = data.draw;
    if (game_state.draw !== null) stalemate();

    update_game_state(data.FEN);
    piece = d3.select(`svg#board #board-pieces [pos="${data.from}"]`);
    promote = data.promote === undefined || data.promote === null ? undefined : (game_state.turn === "w" ? data.promote.toLowerCase() : data.promote.toUpperCase());
    let rect = d3.select(`svg#board #board-boxes #${data.to}`);
    move_piece(null, rect, piece, true, promote);
}
