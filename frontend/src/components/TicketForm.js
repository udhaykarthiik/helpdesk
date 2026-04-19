import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { publicApi } from '../services/api';
import './TicketForm.css';

function TicketForm() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        customer_name: '',
        customer_email: '',
        category: 'general',
        priority: 'medium'
    });

    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(null);
    const [error, setError] = useState(null);
    const [user, setUser] = useState(null);

    // Check if user is logged in
    useEffect(() => {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            const userData = JSON.parse(userStr);
            setUser(userData);
            setFormData(prev => ({
                ...prev,
                customer_name: `${userData.first_name} ${userData.last_name}`.trim() || userData.username,
                customer_email: userData.email
            }));
        }
    }, []);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            const response = await publicApi.createTicket(formData);
            setSuccess({
                ticketId: response.data.ticket_id,
                message: response.data.message
            });
            
            // Clear form
            setFormData({
                title: '',
                description: '',
                customer_name: user ? `${user.first_name} ${user.last_name}`.trim() || user.username : '',
                customer_email: user ? user.email : '',
                category: 'general',
                priority: 'medium'
            });

            // Scroll to top
            window.scrollTo(0, 0);

        } catch (err) {
            setError(err.response?.data?.error || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    const createAnother = () => {
        setSuccess(null);
    };

    return (
        <div className="ticket-form-container">
            <div className="form-header">
                <h1>Submit a Support Ticket</h1>
                <p>We'll get back to you within 24 hours</p>
            </div>
            
            {success && (
                <div className="success-card">
                    <div className="success-icon">✅</div>
                    <h2>Ticket #{success.ticketId} Created!</h2>
                    <p>{success.message}</p>
                    <div className="success-actions">
                        <button onClick={createAnother} className="btn-secondary">
                            Create Another Ticket
                        </button>
                        <button onClick={() => navigate('/')} className="btn-primary">
                            Go to Home
                        </button>
                    </div>
                </div>
            )}

            {error && (
                <div className="error-card">
                    <div className="error-icon">❌</div>
                    <p>{error}</p>
                </div>
            )}

            {!success && (
                <form onSubmit={handleSubmit} className="ticket-form">
                    {!user && (
                        <>
                            <div className="form-section">
                                <h3>Your Information</h3>
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Your Name *</label>
                                        <input
                                            type="text"
                                            name="customer_name"
                                            value={formData.customer_name}
                                            onChange={handleChange}
                                            required
                                            placeholder="John Doe"
                                            disabled={loading}
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label>Email Address *</label>
                                        <input
                                            type="email"
                                            name="customer_email"
                                            value={formData.customer_email}
                                            onChange={handleChange}
                                            required
                                            placeholder="john@example.com"
                                            disabled={loading}
                                        />
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    <div className="form-section">
                        <h3>Ticket Details</h3>
                        
                        <div className="form-row">
                            <div className="form-group">
                                <label>Category</label>
                                <select
                                    name="category"
                                    value={formData.category}
                                    onChange={handleChange}
                                    disabled={loading}
                                >
                                    <option value="general">General Question</option>
                                    <option value="billing">Billing Issue</option>
                                    <option value="technical">Technical Problem</option>
                                    <option value="account">Account Issue</option>
                                    <option value="order">Order Status</option>
                                    <option value="product">Product Question</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Priority</label>
                                <select
                                    name="priority"
                                    value={formData.priority}
                                    onChange={handleChange}
                                    disabled={loading}
                                >
                                    <option value="low">Low - General question</option>
                                    <option value="medium">Medium - Need help</option>
                                    <option value="high">High - Urgent issue</option>
                                    <option value="urgent">Urgent - System down</option>
                                </select>
                            </div>
                        </div>

                        <div className="form-group">
                            <label>Subject *</label>
                            <input
                                type="text"
                                name="title"
                                value={formData.title}
                                onChange={handleChange}
                                required
                                placeholder="Brief summary of your issue"
                                disabled={loading}
                            />
                        </div>

                        <div className="form-group">
                            <label>Description *</label>
                            <textarea
                                name="description"
                                value={formData.description}
                                onChange={handleChange}
                                required
                                rows="6"
                                placeholder="Please describe your issue in detail. Include any error messages, steps to reproduce, or relevant information."
                                disabled={loading}
                            />
                            <small className="field-hint">
                                Be as detailed as possible to help us resolve your issue faster.
                            </small>
                        </div>
                    </div>

                    <div className="form-actions">
                        <button 
                            type="submit" 
                            disabled={loading}
                            className="submit-btn"
                        >
                            {loading ? 'Submitting...' : 'Submit Ticket'}
                        </button>
                        <button 
                            type="button"
                            onClick={() => navigate('/')}
                            className="cancel-btn"
                            disabled={loading}
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            )}
        </div>
    );
}

export default TicketForm;