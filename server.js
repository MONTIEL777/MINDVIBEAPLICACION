// server.js
import express from 'express';
import fetch from 'node-fetch';
import cors from 'cors';


const app = express();
const PORT = 3000;

// Mantén tu API key segura aquí
const apiKey = 'AIzaSyDzICOxy2E1YX4bmhh9sc7YnBqsguiYYPU';

app.use(cors());
app.use(express.json());

app.post('/chatbot', async (req, res) => {
    const userInput = req.body.input;

    const data = {
        contents: [{ role: "user", parts: [{ text: userInput }] }]
    };

    try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        const reply = result.candidates?.[0]?.content?.parts?.[0]?.text || "Lo siento, no entendí bien.";

        res.json({ response: reply });
    } catch (error) {
        console.error("Error al comunicar con Gemini:", error);
        res.status(500).json({ response: "Error del servidor" });
    }
});

app.listen(PORT, () => console.log(`Servidor activo en http://localhost:${PORT}`));
