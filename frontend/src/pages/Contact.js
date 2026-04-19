import React from 'react';
import './SimplePage.css';

function Contact() {
    return (
        <div className="simple-page">
            <h1>Contact Us</h1>
            <div className="contact-info">
                <p><strong>Email:</strong> support@quickcart.com</p>
                <p><strong>Phone:</strong> 1-800-123-4567</p>
                <p><strong>Hours:</strong> Monday-Friday, 9AM - 6PM EST</p>
                <p><strong>Address:</strong> 123 Support Street, Coimbatore, India</p>
            </div>
        </div>
    );
}

export default Contact;