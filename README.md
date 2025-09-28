# ♟️ MagnOSS – Your Open Source Chess Coach

Welcome to **MagnOSS**, our hackathon project built during **{Tech: Europe}**.
Think of it as your very own *Magnus Carlsen at home* – free, open source, and powered by AI.
---

### 🌐 Waitlist Registration: [https://magnoss.vercel.app/](https://magnoss.vercel.app/)  
### 🎥 Demo Youtube Video: [https://magnoss.vercel.app/demo](https://magnoss.vercel.app/demo)

---

## 🚀 What is MagnOSS?

MagnOSS is a web application designed to make learning chess **fun, interactive, and accessible to everyone**.
Instead of boring books, overly complex websites, or expensive private lessons, MagnOSS helps you improve your chess skills through **AI coaching, personalized analysis, and theory exploration**.

---

## ✨ Features

### 🧑‍🤝‍🧑 Play & Learn

* Play against our custom-built chess AI.
* After each game, a **virtual trainer** highlights key mistakes and explains alternative moves.
* Thanks to **text-to-speech**, the trainer actually *talks* to you.

### 🔗 Chess.com Integration

* Connect your **chess.com account**.
* Import and analyze your past games with the trainer.
* Interact with the analysis through **text or voice**.
* Track your growth in a **personal dashboard** powered by **D3.js**.

### 📚 Theory Mode

* Explore chess concepts like **openings, middlegame strategies, endgames, and tactics**.
* Learn through **interactive visuals**: arrows, colored boxes, and step-by-step guidance.
* Ask questions by text or voice and get clear, AI-powered explanations.

---

## 🛠️ Under the Hood

MagnOSS combines **traditional chess engines** with **cutting-edge AI**:

* **Stockfish** → for algorithmic move evaluation.
* **Custom RAG pipeline** → over 1,600 documents scraped with **Lightpandas + Puppeteer**.
* **Dust agent + OpenAI API** → to classify, filter, and tag chess knowledge (openings, tactics, endgames, etc.).
* **Custom-built UI** → from the chessboard to the trainer interface, everything is hand-crafted.

---

## 📦 Prerequisites

Before running MagnOSS, make sure you have:

* Python 3.x
* Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```
* **Stockfish**: download the binary from [stockfishchess.org](https://stockfishchess.org/download/) and set the correct path in `backend/models/stockfish.py`.
* A modern web browser (Chrome, Firefox, Edge, etc.).
* An `.env` file at `backend/src/rag/.env` containing:

  ```ini
  WEAVIATE_REST_ENDPOINT=your_weaviate_instance
  WEAVIATE_API_KEY=your_weaviate_api_key
  OPENAI_API_KEY=your_openai_api_key
  ```

---

## ▶️ Running the Project

1. **Run backend**

   ```bash
   cd backend
   python server.py
   ```

2. **Run frontend**

   ```bash
   cd frontend
   python -m http.server
   ```

3. **Open in browser**
   Go to [http://localhost:8000/](http://localhost:8000/)

---

## 🎯 Why MagnOSS?

We wanted to create a tool that:

* Feels like having a real coach by your side.
* Makes chess theory **visual and fun**.
* Is **open source**, so the community can improve and extend it.

---

## 🌍 Built at {Tech: Europe}

MagnOSS was designed and prototyped during the **{Tech: Europe} hackathon**.
Every line of code, every design choice, and every integration was made in just a few intense days of collaboration.

---

## 💡 What’s Next?

* Expanding the theory base with even more annotated games.
* Mobile-first version for training on the go.
* Multiplayer “coach vs coach” mode for fun sparring with friends.

---

## 🏆 Credits

Developed by Shashwat Sharma, Enzo Pinchon, Stepan Svirin and Tristan Donzé for **{Tech: Europe}** hackathon.
Special thanks to **OpenAI, Dust, Stockfish, and the chess.com community** for inspiration and tools.
