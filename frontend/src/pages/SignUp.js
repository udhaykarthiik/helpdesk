import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { publicApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './SignUp.css';

function SignUp() {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        first_name: '',
        last_name: '',
        role: 'customer'
    });

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [passwordError, setPasswordError] = useState('');

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        
        // Clear password error when typing
        if (e.target.name === 'password' || e.target.name === 'confirmPassword') {
            setPasswordError('');
        }
    };

    const validateForm = () => {
        if (formData.password !== formData.confirmPassword) {
            setPasswordError('Passwords do not match');
            return false;
        }
        if (formData.password.length < 8) {
            setPasswordError('Password must be at least 8 characters');
            return false;
        }
        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }

        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            // Remove confirmPassword before sending
            const { confirmPassword, ...registerData } = formData;
            
            console.log('Sending registration data:', registerData);
            
            const response = await publicApi.register(registerData);
            console.log('Registration response:', response.data);
            
            // Use AuthContext login function instead of direct localStorage
            login(response.data.user, {
                access: response.data.access,
                refresh: response.data.refresh
            });
            
            // Show success message
            setSuccess(`Welcome ${response.data.user.first_name || response.data.user.username}! Registration successful.`);
            
            // Wait 2 seconds then redirect based on role
            setTimeout(() => {
                const userRole = response.data.user?.role || 'customer';
                if (userRole === 'agent') {
                    navigate('/agent/dashboard');
                } else {
                    navigate('/my-tickets');
                }
            }, 2000);
            
        } catch (err) {
            console.error('Registration error:', err.response?.data);
            setError(err.response?.data?.error || 'Registration failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="signup-container">
            <div className="signup-card">
                <h2>Create Account</h2>
                <p className="subtitle">Join QuickCart Helpdesk</p>

                {error && (
                    <div className="error-message">
                        ❌ {error}
                    </div>
                )}

                {success && (
                    <div className="success-message">
                        ✅ {success}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="signup-form">
                    <div className="form-row">
                        <div className="form-group">
                            <label>First Name *</label>
                            <input
                                type="text"
                                name="first_name"
                                value={formData.first_name}
                                onChange={handleChange}
                                required
                                placeholder="John"
                            />
                        </div>

                        <div className="form-group">
                            <label>Last Name</label>
                            <input
                                type="text"
                                name="last_name"
                                value={formData.last_name}
                                onChange={handleChange}
                                placeholder="Doe"
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Username *</label>
                        <input
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            required
                            placeholder="johndoe"
                        />
                    </div>

                    <div className="form-group">
                        <label>Email *</label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            required
                            placeholder="john@example.com"
                        />
                    </div>

                    <div className="form-group">
                        <label>Password *</label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            placeholder="At least 8 characters"
                        />
                    </div>

                    <div className="form-group">
                        <label>Confirm Password *</label>
                        <input
                            type="password"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            required
                            placeholder="Re-enter your password"
                        />
                        {passwordError && (
                            <div className="password-error">{passwordError}</div>
                        )}
                    </div>

                    <div className="form-group">
                        <label>I am a:</label>
                        <div className="role-options">
                            <label className="role-label">
                                <input
                                    type="radio"
                                    name="role"
                                    value="customer"
                                    checked={formData.role === 'customer'}
                                    onChange={handleChange}
                                />
                                Customer
                            </label>
                            <label className="role-label">
                                <input
                                    type="radio"
                                    name="role"
                                    value="agent"
                                    checked={formData.role === 'agent'}
                                    onChange={handleChange}
                                />
                                Support Agent
                            </label>
                        </div>
                    </div>

                    <button 
                        type="submit" 
                        disabled={loading}
                        className="signup-btn"
                    >
                        {loading ? 'Creating Account...' : 'Sign Up'}
                    </button>
                </form>

                <p className="login-link">
                    Already have an account? <Link to="/signin">Sign In</Link>
                </p>
            </div>
        </div>
    );
}

export default SignUp;