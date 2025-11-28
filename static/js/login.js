// login.js

// Configuration
const API_BASE_URL = 'http://localhost:5126/api';

// DOM Elements
const loginForm = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const isNewUserCheckbox = document.getElementById('isNewUser');
const submitBtn = document.getElementById('submitBtn');
const btnText = document.querySelector('.btn-text');
const btnLoader = document.querySelector('.btn-loader');
const messageDiv = document.getElementById('message');

// Show message helper (Bootstrap Alert compatible)
function showMessage(text, type = 'info') {
    messageDiv.textContent = text;
    messageDiv.className = `alert mt-3 ${type}`;
    messageDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            hideMessage();
        }, 5000);
    }
}

// Hide message helper
function hideMessage() {
    messageDiv.style.display = 'none';
}

// Set loading state
function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    btnText.style.display = isLoading ? 'none' : 'inline';
    btnLoader.style.display = isLoading ? 'inline-flex' : 'none';
}

// Validate email format
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Handle form submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessage();
    
    const email = emailInput.value.trim();
    const isNew = isNewUserCheckbox.checked;
    
    // Validation
    if (!email) {
        showMessage('Please enter your email address', 'error');
        emailInput.focus();
        return;
    }
    
    if (!isValidEmail(email)) {
        showMessage('Please enter a valid email address', 'error');
        emailInput.focus();
        return;
    }
    
    // Send login code
    setLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/send-login-code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                email: email,
                is_new: isNew
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === 'success') {
            showMessage(
                isNew 
                    ? 'Account created! Check your email for the login code.'
                    : 'Login code sent! Check your email.',
                'success'
            );
            
            // Store email in sessionStorage for verification page
            sessionStorage.setItem('loginEmail', email);
            
            // Redirect to verification page after 2 seconds
            setTimeout(() => {
                window.location.href = '/verify';
            }, 2000);
            
        } else {
            // Handle error response
            const errorMessage = data.message || data.error || 'Failed to send login code. Please try again.';
            showMessage(errorMessage, 'error');
        }
        
    } catch (error) {
        console.error('Login error:', error);
        showMessage('Network error. Please check your connection and try again.', 'error');
        
    } finally {
        setLoading(false);
    }
});

// Clear error message when user starts typing
emailInput.addEventListener('input', () => {
    if (messageDiv.classList.contains('error')) {
        hideMessage();
    }
});

// Auto-focus email input on page load
emailInput.focus();
