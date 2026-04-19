import React from 'react';
import { Link } from 'react-router-dom';
import './Footer.css';

function Footer() {
    return (
        <footer className="footer">
            <div className="footer-container">
                <div className="footer-section">
                    <h3>QuickCart Helpdesk</h3>
                    <p>Your trusted support partner, available 24/7 to help you with any issues.</p>
                </div>

                <div className="footer-section">
                    <h4>Quick Links</h4>
                    <ul>
                        <li><Link to="/">Home</Link></li>
                        <li><Link to="/kb">Knowledge Base</Link></li>
                        <li><Link to="/track">Track Ticket</Link></li>
                        <li><Link to="/ticket/new">Submit Ticket</Link></li>
                    </ul>
                </div>

                <div className="footer-section">
                    <h4>Support</h4>
                    <ul>
                        <li><Link to="/contact">Contact Us</Link></li>
                        <li><Link to="/faq">FAQ</Link></li>
                        <li><Link to="/privacy">Privacy Policy</Link></li>
                        <li><Link to="/terms">Terms of Service</Link></li>
                    </ul>
                </div>

                <div className="footer-section">
                    <h4>Connect With Us</h4>
                    <div className="social-links">
                        <a href="https://facebook.com" target="_blank" rel="noopener noreferrer" className="social-link">📘</a>
                        <a href="https://twitter.com" target="_blank" rel="noopener noreferrer" className="social-link">🐦</a>
                        <a href="https://instagram.com" target="_blank" rel="noopener noreferrer" className="social-link">📷</a>
                        <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="social-link">💼</a>
                    </div>
                    <p className="contact-email">support@quickcart.com</p>
                    <p className="contact-phone">1-800-123-4567</p>
                </div>
            </div>
            
            <div className="footer-bottom">
                <p>&copy; 2026 QuickCart Helpdesk. All rights reserved.</p>
            </div>
        </footer>
    );
}

export default Footer;