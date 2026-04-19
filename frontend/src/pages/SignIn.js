import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { publicApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './SignIn.css';

function SignIn() {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [formData, setFormData] = useState({
        username: '',
        password: ''
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        // Clear error when typing
        setError(null);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!formData.username || !formData.password) {
            setError('Please fill in all fields');
            return;
        }

        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            console.log('Sending login data:', formData);
            
            const response = await publicApi.login(formData);
            console.log('Login response:', response.data);
            
            // Use AuthContext login function instead of direct localStorage
            login(response.data.user, {
                access: response.data.access,
                refresh: response.data.refresh
            });

            // Show success message
            setSuccess(`Welcome back, ${response.data.user.first_name || response.data.user.username}!`);

            // Redirect based on role
            setTimeout(() => {
                if (response.data.user.role === 'agent') {
                    navigate('/agent/dashboard');
                } else {
                    navigate('/my-tickets');
                }
            }, 1500);
            
        } catch (err) {
            console.error('Login error:', err.response?.data);
            if (err.response?.status === 401) {
                setError('Invalid username or password');
            } else {
                setError(err.response?.data?.error || 'Login failed. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="signin-container">
            <div className="signin-card">
                <h2>Welcome Back</h2>
                <p className="subtitle">Sign in to your QuickCart account</p>

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

                <form onSubmit={handleSubmit} className="signin-form">
                    <div className="form-group">
                        <label>Username or Email *</label>
                        <input
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            required
                            placeholder="johndoe or john@example.com"
                            disabled={loading}
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
                            placeholder="Enter your password"
                            disabled={loading}
                        />
                    </div>

                    <div className="form-options">
                        <label className="remember-me">
                            <input type="checkbox" /> Remember me
                        </label>
                        <Link to="/forgot-password" className="forgot-link">
                            Forgot Password?
                        </Link>
                    </div>

                    <button 
                        type="submit" 
                        disabled={loading}
                        className="signin-btn"
                    >
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <p className="signup-link">
                    Don't have an account? <Link to="/signup">Sign Up</Link>
                </p>

                <div className="demo-credentials">
                    <p className="demo-title">Demo Credentials:</p>
                    <p>Username: newuser123</p>
                    <p>Password: password123</p>
                </div>
            </div>
        </div>
    );
}

export default SignIn;