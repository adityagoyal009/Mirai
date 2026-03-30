const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = express();
const upload = multer({ storage: multer.memoryStorage() });
const CRED_PATH = path.join(os.homedir(), '.claude', '.credentials.json');

app.use(express.static('public'));
app.use(express.json());

function get_token() {
    try {
        if (!fs.existsSync(CRED_PATH)) return null;
        const creds = JSON.parse(fs.readFileSync(CRED_PATH, 'utf8'));
        return creds.claudeAiOauth?.accessToken;
    } catch (e) {
        return null;
    }
}

app.post('/analyze', upload.single('image'), async (req, res) => {
    const token = get_token();
    if (!token) {
        return res.status(401).json({ error: "No Claude Code token found. Please login using 'claude login'." });
    }

    if (!req.file) {
        return res.status(400).json({ error: "No image uploaded." });
    }

    const prompt = req.body.prompt || "Analyze this image in detail.";
    const base64Image = req.file.buffer.toString('base64');
    const mimeType = req.file.mimetype;

    try {
        const response = await fetch("https://api.anthropic.com/v1/messages", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "anthropic-beta": "oauth-2025-04-20",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                model: "claude-opus-4-6",
                max_tokens: 4096,
                messages: [
                    {
                        role: "user",
                        content: [
                            {
                                type: "image",
                                source: {
                                    type: "base64",
                                    media_type: mimeType,
                                    data: base64Image
                                }
                            },
                            {
                                type: "text",
                                text: prompt
                            }
                        ]
                    }
                ]
            })
        });

        if (!response.ok) {
            const error = await response.text();
            return res.status(response.status).json({ error });
        }

        const data = await response.json();
        res.json({ analysis: data.content[0].text });

    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

const PORT = 8501;
app.listen(PORT, () => {
    console.log(`Vision Solo web app running at http://localhost:${PORT}`);
});
