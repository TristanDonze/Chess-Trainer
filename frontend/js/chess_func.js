const game_state = {
    turn: "w",
    en_passant: "-",
    halfmove_clock: 0,
    fullmove_number: 0,
    castling: {'K': true, 'Q': true, 'k': true, 'q': true},
    king_in_check: false,
    checkmate: null,
    draw: null,
    white_player: null,
    black_player: null,
    full_fen: null
}

var saved_possible_moves = {

}

function update_game_state(full_fen) {
    // ex: rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQ kq (3, 2) 0 1
    let [fen, turn, castling, en_passant, halfmove_clock, fullmove_number] = full_fen.split(" ");
    game_state.full_fen = full_fen;
    game_state.turn = turn;
    game_state.en_passant = en_passant;
    game_state.halfmove_clock = halfmove_clock;
    game_state.fullmove_number = fullmove_number;
    game_state.castling = {
        'K': castling.includes("K"),
        'Q': castling.includes("Q"),
        'k': castling.includes("k"),
        'q': castling.includes("q")
    }

    console.log(game_state)
}

async function draw_game(board_fen) {
    game_state.full_fen = board_fen;

    board = d3.select("svg#board");
    if (board.empty()) {
        d3.select(".board-container").append("svg").attr("id", "board");
        board = d3.select("svg#board");
    }
    board.selectAll("*").remove();

    d3.select(".white-player").text(game_state.white_player);
    d3.select(".black-player").text(game_state.black_player);

    // we want dynamic board size: the size of the board depends on the size of the window (css)
    // we want to keep the aspect ratio of the board

    board_size = board.node().getBoundingClientRect().width;
    square_size = parseInt((board_size) / 8) - 8;
    board.attr("square-size", square_size);
    board.attr("width", (square_size + 4) * 8 + 4);
    board.attr("height", (square_size + 4) * 8 + 4);
    board.style("width", `${board.attr("width")}px`);
    board.style("height", `${board.attr("height")}px`);

    const columns = "ABCDEFGH";
    const rows = "87654321";

    board_boxes = board.append("g").attr("id", "board-boxes");
    possible_move_draw = board.append("g").attr("id", "possible-moves");
    board.append("g").attr("id", "advice-layer");
    board_pieces = board.append("g").attr("id", "board-pieces");
    board_labels = board.append("g").attr("id", "board-labels");

    let defs = board.select("defs#advice-defs");
    if (defs.empty()) {
        defs = board.append("defs").attr("id", "advice-defs");
        defs.append("marker")
            .attr("id", "advice-arrow-head")
            .attr("viewBox", "0 0 10 10")
            .attr("refX", 8)
            .attr("refY", 5)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto-start-reverse")
            .append("path")
            .attr("d", "M 0 0 L 10 5 L 0 10 z")
            .attr("fill", "var(--accent-color, #4c6ef5)");
    }

    board_boxes.attr("width", board_size).attr("height", board_size);
    board_pieces.attr("width", board_size).attr("height", board_size);
    board_labels.attr("width", board_size).attr("height", board_size);
    possible_move_draw.attr("width", board_size).attr("height", board_size);

    // draw squares
    for (let i = 0; i < 8; i++) {
        for (let j = 0; j < 8; j++) {
            const boxId = `${columns[j]}${rows[i]}`;
            board_boxes.append("rect")
                .attr("x", j * (square_size + 4) + 4)
                .attr("y", i * (square_size + 4) + 4)
                .attr("width", square_size)
                .attr("height", square_size)
                .attr("fill", (i + j) % 2 == 0 ? "var(--white-box)" : "var(--black-box)")
                .attr("id", boxId)
                .attr("i-index", i)
                .attr("j-index", j)
                .attr("stroke", (i + j) % 2 == 0 ? "var(--white-box)" : "var(--black-box)")
                .attr("stroke-width", 4)
                .attr("color", (i + j) % 2 == 0 ? "white" : "black");
        }
    }

    // border labels
    for (let i = 0; i < 8; i++) {
        // Column letters (bottom)
        board_labels.append("text")
            .attr("x", i * (square_size + 4) + square_size - 4)
            .attr("y", 8 * (square_size + 4) - 2)
            .attr("text-anchor", "middle")
            .attr("font-size", "12px")
            .attr("font-weight", "bolder")
            .attr("fill", i % 2 == 0 ? "var(--white-box)" : "var(--black-box)")
            .text(columns[i]);

        // Row numbers (left side)
        board_labels.append("text")
            .attr("x", 14)
            .attr("y", i * (square_size + 4) + 16)
            .attr("text-anchor", "end")
            .attr("alignment-baseline", "middle")
            .attr("font-size", "14px")
            .attr("font-weight", "bolder")
            .attr("fill", i % 2 == 1 ? "var(--white-box)" : "var(--black-box)")
            .text(rows[i]);
    }


    // load pieces (auto check if already loaded)
    await load_pieces()

    // draw pieces
    // draw_piece("R", "A8");
    // draw_piece("N", "B1");
    // draw_piece("b", "C3");
    draw_from_fen(board_fen);
    clear_advice_move();
}

function get_current_fen() {
    return game_state.full_fen;
}

function clear_advice_move() {
    const board = d3.select("svg#board");
    if (board.empty()) return;
    board.select("g#advice-layer").selectAll("*").remove();
    board.selectAll("rect.advice-highlight").classed("advice-highlight", false);
}

function show_advice_move(move) {
    if (!move || !move.from || !move.to) return;

    const board = d3.select("svg#board");
    if (board.empty()) return;

    const adviceLayer = board.select("g#advice-layer");
    if (adviceLayer.empty()) return;

    const squareSize = parseFloat(board.attr("square-size"));
    const fromRect = board.select(`#${move.from}`);
    const toRect = board.select(`#${move.to}`);

    if (fromRect.empty() || toRect.empty()) return;

    const fromX = parseFloat(fromRect.attr("x")) + squareSize / 2;
    const fromY = parseFloat(fromRect.attr("y")) + squareSize / 2;
    const toX = parseFloat(toRect.attr("x")) + squareSize / 2;
    const toY = parseFloat(toRect.attr("y")) + squareSize / 2;

    adviceLayer.append("line")
        .attr("x1", fromX)
        .attr("y1", fromY)
        .attr("x2", toX)
        .attr("y2", toY)
        .attr("stroke", "var(--accent-color, #4c6ef5)")
        .attr("stroke-width", 8)
        .attr("stroke-linecap", "round")
        .attr("marker-end", "url(#advice-arrow-head)")

    adviceLayer.append("circle")
        .attr("cx", fromX)
        .attr("cy", fromY)
        .attr("r", Math.max(6, squareSize * 0.18))
        .attr("fill", "var(--accent-color, #4c6ef5)")
        .attr("fill-opacity", 0.25)
        .attr("stroke", "var(--accent-color, #4c6ef5)")
        .attr("stroke-width", 2);

    fromRect.classed("advice-highlight", true);
    toRect.classed("advice-highlight", true);
}

function show_advice_moves(moves) {
    clear_advice_move();
    if (!Array.isArray(moves) || moves.length === 0) return;
    moves.forEach(move => show_advice_move(move));
}

window.clear_advice_move = clear_advice_move;
window.show_advice_move = show_advice_move;

function draw_from_fen(fen) {
    board = d3.select("svg#board");
    board_pieces = board.select("g#board-pieces");
    board_pieces.selectAll("*").remove();

    const [pieces, turn] = fen.split(" ");
    const rows = pieces.split("/");
    const columns = "ABCDEFGH";

    for (let i = 0; i < 8; i++) {
        let j = 0;
        for (let char of rows[i]) {
            if (isNaN(char)) {
                draw_piece(char, `${columns[j]}${8-i}`);
                j++;
            }
            else {
                j += parseInt(char);
            }
        }
    }
}

async function load_pieces() {
    let data = await d3.xml("../media/chess_pieces.svg");

    let svg_pieces = d3.select(data).selectAll("svg g");

    let defs = d3.select("body").append("svg")
        .attr("id", "pieces-defs")
        .attr("width", 0)
        .attr("height", 0);

    svg_pieces.each(function() {
        defs.node().appendChild(this.cloneNode(true));
    });
}

function draw_piece(piece, box_id) {
    // piece == fen notation
    piece_svg = d3.select(`#pieces-defs g[fen="${piece}"]`).clone(true).node();

    pieces_layer = d3.select("svg#board g#board-pieces");
    box = d3.select(`#${box_id}`);

    width_scale = square_size / 45;
    height_scale = square_size / 45;

    pieces_layer.append(() => piece_svg)
        .attr("transform", `translate(${box.attr("x")}, ${box.attr("y")}) scale(${width_scale}, ${height_scale})`)
        .attr("initial-scale", `${width_scale}, ${height_scale}`)
        .attr("initial-pos", `translate(${box.attr("x")}, ${box.attr("y")})`)
        .attr("pos", box_id)
        .call(dragHandler);
}

function get_piece_color(piece_fen) {
    return piece_fen.charCodeAt(0) < 91 ? "w" : "b";
}

// Define drag behavior
const dragHandler = d3.drag()
    .on("start", function (event) {
        // check if it's the player's turn
        let piece = d3.select(this)
        if (game_state.turn != get_piece_color(piece.attr("fen"))) return;
        piece_id = piece.attr("fen") + piece.attr("pos");
        piece.raise()

        if (saved_possible_moves[piece_id] === undefined) {
            send_message("get-possible-moves", {
                fen: piece.attr("fen"),
                pos: piece.attr("pos")
            });

            wait_for_message("possible-moves", timeout=1000, only_content=true).then((data) => {
                if (data === null) {
                    piece.attr("transform", `${piece.attr("initial-pos")} scale(${piece.attr("initial-scale")})`);
                    return; // Timeout: error will be return by the server
                }
                saved_possible_moves[piece_id] = data.moves
                draw_possible_moves(piece)
            });
        }
        draw_possible_moves(piece);
    })
    .on("drag", function (event) {
        if (game_state.turn != get_piece_color(d3.select(this).attr("fen"))) return;
        drag_x = event.x - square_size / 2;
        drag_y = event.y - square_size / 2;

        drag_x = Math.max(-square_size, drag_x);
        drag_x = Math.min(drag_x, 8 * square_size );
        drag_y = Math.max(-square_size, drag_y);
        drag_y = Math.min(drag_y, 8 * square_size);

        d3.select(this)
            .attr("transform", `translate(${drag_x}, ${drag_y}) scale(${d3.select(this).attr("initial-scale")})`);
        
        d3.selectAll("rect.highlight").classed("highlight", false); // Remove all highlights
        nearest_square = get_nearest_square(event.x, event.y);
        nearest_square.classed("highlight", true).raise(); // Highlight nearest square

    })
    .on("end", function (event) {
        if (game_state.turn != get_piece_color(d3.select(this).attr("fen"))) return;
        d3.select("svg#board g#possible-moves").selectAll("*").remove();

        let piece = d3.select(this);
        piece_id = piece.attr("fen") + piece.attr("pos");

        if (saved_possible_moves[piece_id] !== undefined) {
            move_piece(saved_possible_moves[piece_id], event, piece);
            return;
        }

        send_message("get-possible-moves", {
            fen: d3.select(this).attr("fen"),
            pos: d3.select(this).attr("pos")
        });

        wait_for_message("possible-moves", timeout=1000, only_content=true).then((data) => {
            console.log(data)
            if (data === null) {
                d3.select(this).attr("transform", `${d3.select(this).attr("initial-pos")} scale(${d3.select(this).attr("initial-scale")})`);
                return; // Timeout: error will be return by the server
            }
            saved_possible_moves[piece_id] = data.moves;
            move_piece(data.moves, event, d3.select(this));
        }).catch((error) => {
            console.error(error)
        })
    });

function draw_possible_moves(piece) {
    piece_id = piece.attr("fen") + piece.attr("pos");
    if (saved_possible_moves[piece_id] === undefined) return;
    square_size = parseInt(d3.select("svg#board").attr("square-size"));

    possible_move_draw = d3.select("svg#board g#possible-moves");
    saved_possible_moves[piece_id].forEach((move) => {
        rect = d3.select(`rect#${move}`);
        possible_move_draw.append("circle")
            .attr("cx", parseInt(rect.attr("x")) + square_size / 2)
            .attr("cy", parseInt(rect.attr("y")) + square_size / 2)
            .attr("r", 10)
            .attr("fill", "gray")
            .attr("fill-opacity", 0.5)
    })
}

async function move_piece(moves, event, piece, no_confirmation = false, promote = undefined) {
    if (game_state.draw !== null) return

    if (no_confirmation) {
        nearest_square = event
    } else {
        let nearest_square = get_nearest_square(event.x, event.y)

        if (moves === null || !moves.includes(nearest_square.attr("id"))) {
            piece.attr("transform", `${piece.attr("initial-pos")} scale(${piece.attr("initial-scale")})`);
            Toast.warning("Invalid move: piece cannot move to that square.");
            if (game_state.king_in_check) {
                new Audio("../media/illegal.mp3").play();
                
                // get king position
                if (game_state.turn == "w") {
                    king = d3.select(`g#board-pieces g[fen="K"]`);
                }
                else {
                    king = d3.select(`g#board-pieces g[fen="k"]`);
                }
                // highlight king square for 2s
                king_id = king.attr("pos");
                king_square = d3.select(`rect#${king_id}`);
                king_square.classed("highlight", true);
                setTimeout(() => {
                    king_square.classed("highlight", false);
                }, 2000);
            }
            return;
        }
    }

    piece_on_square = d3.select(`g#board-pieces g[pos="${nearest_square.attr("id")}"]`);
    let killed_pawn = null;
    if (nearest_square.attr("id").toLowerCase() == game_state.en_passant) {
        if (piece.attr("fen").toLowerCase() == "p" && piece.attr("pos") != nearest_square.attr("id")) {
            direction = piece.attr("fen").charCodeAt(0) < 91 ? 1 : -1;
            pos = nearest_square.attr("id")[0] + (parseInt(nearest_square.attr("id")[1]) - direction);
            killed_pawn = d3.select(`g#board-pieces g[pos="${pos}"]`);
            if (killed_pawn.node() === piece.node())
                killed_pawn = null;
        }
    }

    // check if promotion
    let promote_piece_id = null
    if (!no_confirmation) {
        if (piece.attr("fen").toLowerCase() == "p" && (nearest_square.attr("id")[1] == "1" || nearest_square.attr("id")[1] == "8")) {
            promote_piece_id = await promote_popup(piece.attr("fen").charCodeAt(0) < 91 ? "w" : "b");
        }
    } else {
        promote_piece_id = promote !== undefined ? promote : null;
    }

    if (!no_confirmation) {
        send_message("move-piece", {
            piece: piece.attr("fen"),
            start: piece.attr("pos"),
            end: nearest_square.attr("id"),
            promote: promote_piece_id
        });
    
        confirmation = await wait_for_message("confirm-move", timeout=1000, only_content=true)
        if (confirmation === null) {
            piece.attr("transform", `${piece.attr("initial-pos")} scale(${piece.attr("initial-scale")})`);
            Toast.warning("Move not confirmed: timeout.");
            return;
        }

        game_state.king_in_check = confirmation.king_in_check;
        game_state.checkmate = confirmation.checkmate;
    }

    saved_possible_moves = {} // reset

    if (no_confirmation) {
        coords = get_square_absolute_position(nearest_square);
        snap_to_square(piece, coords[0], coords[1]);
    } else
        snap_to_square(piece, event.x, event.y);

    if (promote_piece_id !== null) {
        // remove pawn
        piece.remove();
        draw_piece(promote_piece_id, nearest_square.attr("id"));
    }

    // castling
    pos_x_idx = piece.attr("pos")[0].charCodeAt(0) - 'A'.charCodeAt(0)
    if (piece.attr("fen").toLowerCase() == "k" && Math.abs(nearest_square.attr("j-index") - pos_x_idx) == 2) {
        console.log("Castling")
        if (nearest_square.attr("i-index") == 0 || nearest_square.attr("i-index") == 7) {
            let rook_pos = nearest_square.attr("j-index") > pos_x_idx ? "H" : "A";
            let rook = d3.select(`g#board-pieces g[pos="${rook_pos}${piece.attr("pos")[1]}"]`);
            let rook_dest = nearest_square.attr("j-index") > pos_x_idx ? pos_x_idx + 1 : pos_x_idx - 1;
            rook_dest = String.fromCharCode('A'.charCodeAt(0) + rook_dest) + piece.attr("pos")[1];
            rook.attr("transform", `translate(${d3.select(`rect#${rook_dest}`).attr("x")}, ${d3.select(`rect#${rook_dest}`).attr("y")}) scale(${rook.attr("initial-scale")})`);
            rook.attr("pos", rook_dest);
            rook.attr("initial-pos", `translate(${d3.select(`rect#${rook_dest}`).attr("x")}, ${d3.select(`rect#${rook_dest}`).attr("y")})`);
            new Audio("../media/castle.mp3").play();
        }
    }

    if (!piece_on_square.empty() && piece_on_square !== piece) {
        // if piece of the same color, return to initial position: check if the both fen are uppercase or lowercase 
        is_upper = piece.attr("fen").charCodeAt(0) < 91;
        is_upper_piece = piece_on_square.attr("fen").charCodeAt(0) < 91;
        if (is_upper == is_upper_piece) {
            piece.attr("transform", `${piece.attr("initial-pos")} scale(${piece.attr("initial-scale")})`);
            Toast.warning("Invalid move: destination square is occupied by a piece of the same color.");
            return;
        }

        // if piece of different color, remove it
        piece_on_square.remove();
        
        if (game_state.king_in_check)
            new Audio("../media/move-check.mp3").play();
        else
            new Audio("../media/capture.mp3").play()

    } else {
        if (game_state.king_in_check)
            new Audio("../media/move-check.mp3").play();
        else if (killed_pawn !== null && !killed_pawn.empty()) {
            // remove killed pawn
            killed_pawn.remove();
            if (game_state.king_in_check)
                new Audio("../media/move-check.mp3").play();
            else
                new Audio("../media/capture.mp3").play()
        } 
        else
            new Audio("../media/move.mp3").play()
    }

    if (game_state.checkmate != null) {
        new Audio("../media/game-end.webm").play();
        end_game()
    }

    piece = piece;

        // light the previous square
    d3.selectAll("rect.moved").classed("moved", false);
    previous_square = d3.select(`rect#${piece.attr("pos")}`);
    previous_square.classed("moved", true);
    // highlight current box
    nearest_square.classed("moved", true);

    piece.attr("pos", nearest_square.attr("id"));
    piece.attr("initial-pos", `translate(${nearest_square.attr("x")}, ${nearest_square.attr("y")})`);
}

function get_square_absolute_position(rect) {
    square_size = parseInt(d3.select("svg#board").attr("square-size"));
    col = parseInt(rect.attr("j-index"));
    row = parseInt(rect.attr("i-index"));
    return [col * square_size + 4 * col + 4, row * square_size + 4 * row + 4];
}

function get_nearest_square(x, y, return_coords = false) {
    const square_size = parseInt(d3.select("svg#board").attr("square-size"));
    const col = Math.min(Math.round((x - square_size / 2) / square_size), 7)
    const row = Math.min(Math.round((y - square_size / 2) / square_size), 7);

    const snappedX = col * square_size + 4 * col + 4 + 0.5
    const snappedY = row * square_size + 4 * row + 4 - 0.5

    nearest_square = d3.select(`rect[i-index="${row}"][j-index="${col}"]`);
    if (nearest_square.empty()) {
        throw `Invalid square: ${col}, ${row}`;
    }
    if (return_coords) 
        return [snappedX, snappedY];
    return nearest_square;
}

// Function to snap piece to nearest square
function snap_to_square(piece, x, y) {
    const [snappedX, snappedY] = get_nearest_square(x, y, true);
    square_size = parseInt(d3.select("svg#board").attr("square-size"));
    piece.attr("transform", `translate(${snappedX}, ${snappedY}) scale(${piece.attr("initial-scale")})`);
}

function end_game() {
    loosing_king = d3.select(`g#board-pieces g[fen="${game_state.checkmate == "w" ? "K" : "k"}"]`);
    winning_king = d3.select(`g#board-pieces g[fen="${game_state.checkmate == "w" ? "k" : "K"}"]`);
    loosing_king_square = d3.select(`rect#${loosing_king.attr("pos")}`);
    winning_king_square = d3.select(`rect#${winning_king.attr("pos")}`);

    loosing_king_square.attr("stroke", "red").attr("stroke-width", 4);
    winning_king_square.attr("stroke", "green").attr("stroke-width", 4);
}

function stalemate() {
    king1 = d3.select(`g#board-pieces g[fen="K"]`);
    king2 = d3.select(`g#board-pieces g[fen="k"]`);
    king1_square = d3.select(`rect#${king1.attr("pos")}`);
    king2_square = d3.select(`rect#${king2.attr("pos")}`);

    new Audio("../media/game-end.webm").play();

    king1_square.attr("stroke", "yellow").attr("stroke-width", 4);
    king2_square.attr("stroke", "yellow").attr("stroke-width", 4);

    alert(game_state.draw)
}

function promote_popup(color) {
    ctn = `
        <h1>Promotion</h1>
        <p>Choose a piece to promote your pawn:</p>
        <div class="promotion-pieces">
            
        </div>
    `
    pop_up = PopUp.showcase(ctn).open()._wrapper
    pices = color == "w" ? ["Q", "R", "N", "B"] : ["q", "r", "n", "b"];
    pices.forEach((piece) => {
        // create new svg not a clone with d3
        svg = d3.select(pop_up).select(".promotion-pieces").append("svg").classed("promotion-piece", true).attr("id", piece).attr("width", 75 + 8).attr("height", 75 + 8);
        piece = d3.select(`#pieces-defs g[fen="${piece}"]`).clone(true).node();
        scale_factor = parseFloat(piece.getBoundingClientRect().width) / 75;
        d3.select(piece).attr("transform", `translate(4, 4) scale(${1/scale_factor})`).style("cursor", "pointer");
        svg.node().appendChild(piece);
    })

    return new Promise((resolve, reject) => {
        document.querySelectorAll(".promotion-piece").forEach((piece) => {
            piece.addEventListener("click", () => {
                // return piece id
                resolve(piece.id)
                pop_up.remove()
            })
        })
    })
}

function highlight_square(squares, color='blue') {
    switch(color) {
        case 'blue':
            color = '#4c6ef5';
            break;
        case 'red':
            color = '#f88272';
            break;
        case 'green':
            color = '#9bce8b';
            break;
        default:
            color = null;
            break;
    }

    if (color === null || squares === undefined) {
        d3.selectAll("rect[advice-highlight]").style("fill", null).attr("advice-highlight", null);
        return;
    }

    squares.forEach(square => {
        square = square.charAt(0).toUpperCase() + square.charAt(1);
        d3.select(`rect#${square}`).style("fill", color).attr("advice-highlight", true);
    });
}