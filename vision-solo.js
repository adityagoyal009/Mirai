#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

const CRED_PATH = path.join(os.homedir(), '.claude', '.credentials.json');

async function get_token() {
    try {
        if (!fs.existsSync(CRED_PATH)) {
            console.error(`Error: Credentials file not found at ${CRED_PATH}`);
            console.error("Please login using 'claude login' first.");
            return null;
        }
        const creds = JSON.parse(fs.readFileSync(CRED_PATH, 'utf8'));
        return creds.claudeAiOauth?.accessToken;
    } catch (e) {
        console.error(`Error reading credentials: ${e.message}`);
        return null;
    }
}

function get_mime_type(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    };
    return map[ext] || 'image/jpeg';
}

async function analyze_image(imagePath, prompt = "Analyze this image in detail.") {
    const token = await get_token();
    if (!token) return;

    if (!fs.existsSync(imagePath)) {
        console.error(`Error: Image file not found at ${imagePath}`);
        return;
    }

    try {
        const imageBuffer = fs.readFileSync(imagePath);
        const base64Image = imageBuffer.toString('base64');
        const mimeType = get_mime_type(imagePath);

        console.log(`\x1b[36mSending request to Claude Opus 4.6 (${mimeType})...\x1b[0m`);

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
            const errorText = await response.text();
            console.error(`\x1b[31mAPI Error (${response.status}):\x1b[0m`, errorText);
            return;
        }

        const result = await response.json();
        console.log("\n\x1b[32m--- Claude Opus 4.6 Analysis ---\x1b[0m\n");
        console.log(result.content[0].text);
        console.log("\n\x1b[32m--------------------------------\x1b[0m");

    } catch (e) {
        console.error(`An error occurred: ${e.message}`);
    }
}

// CLI Entry Point
const [,, imgPath, ...promptParts] = process.argv;

if (!imgPath || imgPath === '--help' || imgPath === '-h') {
    console.log(`
\x1b[1mVision Solo\x1b[0m - Standalone Image Analysis via Claude Code Token

\x1b[1mUsage:\x1b[0m
  vision-solo <image_path> [prompt]

\x1b[1mExamples:\x1b[0m
  vision-solo screenshot.png
  vision-solo chart.jpg "What are the trends in this graph?"

\x1b[2mNote: Requires active login in 'claude' CLI.\x1b[0m
    `);
} else {
    const userPrompt = promptParts.length > 0 ? promptParts.join(' ') : "Analyze this image in detail.";
    analyze_image(imgPath, userPrompt);
}
