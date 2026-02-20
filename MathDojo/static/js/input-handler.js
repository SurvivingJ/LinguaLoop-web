/**
 * InputHandler - Manages answer input fields
 */
class InputHandler {
    constructor(inputId, onSubmit) {
        this.input = document.getElementById(inputId);
        this.onSubmit = onSubmit;
        this.setupListeners();
    }

    /**
     * Setup event listeners
     */
    setupListeners() {
        if (!this.input) return;

        // Enter key to submit
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.submit();
            }
        });

        // Numeric only input (allow negative and decimal)
        this.input.addEventListener('input', (e) => {
            this.input.value = this.input.value.replace(/[^0-9.\-]/g, '');
        });
    }

    /**
     * Submit current value
     */
    submit() {
        const value = this.input.value.trim();

        if (value === '') return;

        const numericValue = value.includes('.') ? parseFloat(value) : parseInt(value, 10);

        if (!isNaN(numericValue) && this.onSubmit) {
            this.onSubmit(numericValue);
        }
    }

    /**
     * Clear input field
     */
    clear() {
        if (this.input) {
            this.input.value = '';
        }
    }

    /**
     * Focus input field
     */
    focus() {
        if (this.input) {
            this.input.focus();
        }
    }

    /**
     * Get current value
     */
    getValue() {
        if (!this.input) return null;
        const value = this.input.value.trim();
        return value === '' ? null : parseInt(value, 10);
    }

    /**
     * Disable input
     */
    disable() {
        if (this.input) {
            this.input.disabled = true;
        }
    }

    /**
     * Enable input
     */
    enable() {
        if (this.input) {
            this.input.disabled = false;
        }
    }
}
