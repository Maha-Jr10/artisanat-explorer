// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();

        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Navbar scroll effect
window.addEventListener('scroll', function() {
    const navbar = document.getElementById('main-nav');
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
});

// Dynamic Navbar Active Link Functionality (as discussed previously)
document.addEventListener('DOMContentLoaded', function() {
    const sections = document.querySelectorAll('section[id], footer[id]'); // Corrected selector
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    function changeNavActiveClass() {
        let currentActiveSectionId = 'top';

        for (let i = sections.length - 1; i >= 0; i--) {
            const section = sections[i];
            const sectionId = section.getAttribute('id');
            const sectionRect = section.getBoundingClientRect();
            const offset = 100; // Adjust for fixed navbar height

            if (sectionRect.top <= offset && sectionRect.bottom > offset) {
                currentActiveSectionId = sectionId;
                break;
            }
        }

        if (window.scrollY === 0) {
            currentActiveSectionId = 'top';
        }

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${currentActiveSectionId}`) {
                link.classList.add('active');
            }
        });
    }

    window.addEventListener('scroll', changeNavActiveClass);
    changeNavActiveClass();

    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            navLinks.forEach(item => item.classList.remove('active'));
            this.classList.add('active');
        });
    });
});


// **MODIFIED: Simple Chatbot Logic to connect with Flask RAG system**
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Make sendMessage an async function to use await with fetch
async function sendMessage() {
    const userMessageText = userInput.value.trim();
    if (userMessageText === '') return; // Don't send empty messages

    // 1. Add user message to chat display
    const userMessageDiv = document.createElement('div');
    userMessageDiv.classList.add('message', 'user-message');
    userMessageDiv.textContent = userMessageText;
    chatMessages.appendChild(userMessageDiv);

    userInput.value = ''; // Clear input field
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom

    // 2. Show typing indicator
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom to show indicator

    try {
        // 3. Make an API call to your Flask backend
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json' // Indicate that you're sending JSON
            },
            body: JSON.stringify({ question: userMessageText }) // Send the user's question as JSON
        });

        // Check if the response was successful
        if (!response.ok) {
            // If not, throw an error with the status
            const errorText = await response.text(); // Get more details if available
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        // 4. Parse the JSON response from Flask
        const data = await response.json();
        const botResponse = data.response; // Extract the 'response' field

        // 5. Hide typing indicator
        typingIndicator.style.display = 'none';

        // 6. Add bot's response to chat display
        const botMessageDiv = document.createElement('div');
        botMessageDiv.classList.add('message', 'bot-message');
        // Use innerHTML because your Flask prompt suggests Markdown formatting,
        // which the browser will render.
        botMessageDiv.innerHTML = botResponse;
        chatMessages.appendChild(botMessageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom after bot response

    } catch (error) {
        // 7. Handle errors during the fetch request
        console.error('Error fetching bot response:', error);
        typingIndicator.style.display = 'none'; // Hide typing indicator even on error
        const errorMessageDiv = document.createElement('div');
        errorMessageDiv.classList.add('message', 'bot-message', 'error-message');
        errorMessageDiv.textContent = "Désolé, une erreur s'est produite lors de la communication avec l'IA. Veuillez réessayer plus tard.";
        chatMessages.appendChild(errorMessageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}