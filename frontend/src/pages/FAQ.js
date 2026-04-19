import React from 'react';
import './SimplePage.css';

function FAQ() {
    return (
        <div className="simple-page">
            <h1>Frequently Asked Questions</h1>
            <div className="faq-item">
                <h3>How do I reset my password?</h3>
                <p>Click on "Forgot Password" on the login page and follow the instructions.</p>
            </div>
            <div className="faq-item">
                <h3>How long does it take to get a response?</h3>
                <p>We typically respond within 24 hours during business days.</p>
            </div>
            <div className="faq-item">
                <h3>Can I track my ticket status?</h3>
                <p>Yes! Use the "Track Ticket" page with your email and ticket ID.</p>
            </div>
            <div className="faq-item">
                <h3>Is there a phone support option?</h3>
                <p>Yes, call us at 1-800-123-4567 during business hours.</p>
            </div>
        </div>
    );
}

export default FAQ;