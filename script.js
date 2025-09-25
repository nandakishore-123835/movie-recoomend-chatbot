// movie-chatbot/frontend/script.js

document.addEventListener('DOMContentLoaded', () => {
    const sendBtn = document.getElementById('send-btn');
    const userInput = document.getElementById('user-input');

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});

function addMessage(text, sender) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);
    
    // Use innerHTML to correctly render line breaks from the backend
    messageDiv.innerHTML = `<p>${text}</p>`;
    
    chatBox.appendChild(messageDiv);
    // Scroll to the bottom of the chat box
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const movieTitle = userInput.value.trim();

    if (movieTitle === '') return;

    // Display the user's message immediately
    addMessage(movieTitle, 'user');
    userInput.value = ''; // Clear the input field

    try {
        const response = await fetch('http://127.0.0.1:5000/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ movie: movieTitle })
        });

        const data = await response.json();

        // **KEY FIX**: Check the content of the response from the server
        if (data.response) {
            // If there's a 'response' field, display it (success or 'not found' message)
            const botResponse = data.response.replace(/\n/g, '<br>');
            addMessage(botResponse, 'bot');
        } else if (data.error) {
            // If there's an 'error' field, display that instead
            addMessage(`Error: ${data.error}`, 'bot');
        } else {
            // Fallback for unexpected response structure
            throw new Error('Received an invalid response from the server.');
        }

    } catch (error) {
        console.error('Error fetching recommendation:', error);
        // This message will now only show for network errors or major failures
        addMessage('Sorry, something went wrong. Please check the server connection and try again.', 'bot');
    }
}