import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
// import { agentApi } from '../services/api';
import './Dashboard.css';

function Dashboard() {
    const navigate = useNavigate();
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Get user from localStorage
        const userStr = localStorage.getItem('user');
        const token = localStorage.getItem('access_token');
        
        if (!userStr || !token) {
            navigate('/signin');
            return;
        }
        
        setUser(JSON.parse(userStr));
        setLoading(false);
    }, [navigate]);

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        navigate('/');
    };

    if (loading) {
        return <div className="loading">Loading...</div>;
    }

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <h1>Welcome, {user?.first_name || user?.username}!</h1>
                <button onClick={handleLogout} className="logout-btn">Logout</button>
            </div>
            
            <div className="dashboard-stats">
                <div className="stat-card">
                    <h3>Your Role</h3>
                    <p>Customer</p>
                </div>
                <div className="stat-card">
                    <h3>Email</h3>
                    <p>{user?.email}</p>
                </div>
                <div className="stat-card">
                    <h3>Member Since</h3>
                    <p>Just now</p>
                </div>
            </div>

            <div className="quick-actions">
                <h2>Quick Actions</h2>
                <div className="action-buttons">
                    <button onClick={() => navigate('/ticket/new')} className="action-btn">
                        Submit New Ticket
                    </button>
                    <button className="action-btn">
                        View My Tickets
                    </button>
                    <button className="action-btn">
                        Knowledge Base
                    </button>
                </div>
            </div>
        </div>
    );
}

export default Dashboard;