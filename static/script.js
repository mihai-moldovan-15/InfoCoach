// Scroll automat la ultimul mesaj
function scrollToBottom() {
    var chat = document.getElementById("chat-messages");
    if (chat) chat.scrollTop = chat.scrollHeight;
}

// Mesaje de așteptare
const messages = [
    "Se procesează întrebarea ta...",
    "Încă lucrez la răspuns...",
    "Verific resursele pentru cel mai bun răspuns...",
    "Aproape am terminat, mai ai puțină răbdare!"
];
let msgIndex = 0;
let intervalId = null;

function startWaitMessages() {
    const waitDiv = document.getElementById("wait-message");
    waitDiv.style.display = "block";
    waitDiv.textContent = messages[msgIndex];
    intervalId = setInterval(() => {
        msgIndex = (msgIndex + 1) % messages.length;
        waitDiv.textContent = messages[msgIndex];
    }, 2000);
    window.intervalId = intervalId;
    window.msgIndex = msgIndex;
}

function addMessage(content, isUser = false) {
    const chatMessages = document.getElementById("chat-messages");
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    if (isUser) {
        messageDiv.innerHTML = `<b>Tu:</b><br>${content}`;
    } else {
        messageDiv.innerHTML = `
            <b>InfoCoach:</b><br>
            ${content}
            <form class="feedback-form" action="/feedback" method="post">
                <input type="hidden" name="user_input" value="${document.getElementById('user-input').value}">
                <input type="hidden" name="ai_response" value="${content}">
                <input type="hidden" name="clasa" value="${document.getElementById('clasa').value}">
                <span>Acest răspuns a fost util?</span>
                <button type="submit" name="feedback" value="bun">✅ Da</button>
                <button type="submit" name="feedback" value="rau">❌ Nu</button>
            </form>
            <div id="feedback-message" style="display:none;">Mulțumim pentru feedback! 😊</div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function submitForm(event) {
    event.preventDefault();
    
    const form = document.getElementById('chat-form');
    const formData = new FormData(form);
    
    // Add user message to chat
    const userInput = document.getElementById('user-input').value;
    addMessage(userInput, true);
    
    // Clear input
    document.getElementById('user-input').value = '';
    
    // Show waiting message
    startWaitMessages();
    
    // Send request
    fetch('/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        // Create a temporary div to parse the HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Find the assistant's response
        const assistantMessage = doc.querySelector('.message.assistant');
        if (assistantMessage) {
            // Remove the user and assistant messages from the parsed HTML
            const userMessage = assistantMessage.previousElementSibling;
            if (userMessage) userMessage.remove();
            assistantMessage.remove();
            
            // Add the assistant's response to our chat
            addMessage(assistantMessage.innerHTML);
        }
        
        // Hide waiting message
        document.getElementById('wait-message').style.display = 'none';
        if (window.intervalId) {
            clearInterval(window.intervalId);
            window.intervalId = null;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('A apărut o eroare la trimiterea mesajului. Te rugăm să încerci din nou.');
        document.getElementById('wait-message').style.display = 'none';
        if (window.intervalId) {
            clearInterval(window.intervalId);
            window.intervalId = null;
        }
    });
    
    return false;
}

// Feedback AJAX
document.addEventListener('DOMContentLoaded', () => {
    // Add event delegation for feedback forms
    document.addEventListener('submit', (e) => {
        if (e.target.classList.contains('feedback-form')) {
            e.preventDefault();
            const formData = new FormData(e.target);
            fetch('/feedback', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    e.target.style.display = 'none';
                    const feedbackMsg = e.target.nextElementSibling;
                    if (feedbackMsg) feedbackMsg.style.display = 'block';
                } else {
                    alert('A apărut o eroare la trimiterea feedback-ului.');
                }
            })
            .catch(() => {
                alert('Nu s-a putut trimite feedback-ul. Verifică conexiunea.');
            });
        }
    });
    
    // Initial scroll to bottom
    scrollToBottom();
}); 