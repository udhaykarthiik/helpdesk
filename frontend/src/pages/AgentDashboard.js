import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
// eslint-disable-next-line no-unused-vars
import { agentApi } from '../services/api';
import './AgentDashboard.css';

function AgentDashboard() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState(null);
    const [tickets, setTickets] = useState([]);
    const [filter, setFilter] = useState('all');
    const [stats, setStats] = useState({
        total: 0,
        open: 0,
        pending: 0,
        resolved: 0,
        new: 0
    });

    useEffect(() => {
        // Check if user is logged in and is agent
        const userStr = localStorage.getItem('user');
        const token = localStorage.getItem('access_token');
        
        if (!userStr || !token) {
            navigate('/signin');
            return;
        }

        const userData = JSON.parse(userStr);
        if (userData.role !== 'agent') {
            navigate('/dashboard');
            return;
        }

        setUser(userData);
        fetchTickets();
    }, [navigate]);

    const fetchTickets = async () => {
        try {
            setLoading(true);
            // Fetch real tickets from API
            const response = await agentApi.getTickets();
            setTickets(response.data);
            
            // Calculate stats
            const newStats = {
                total: response.data.length,
                open: response.data.filter(t => t.status === 'open').length,
                pending: response.data.filter(t => t.status === 'pending').length,
                resolved: response.data.filter(t => t.status === 'resolved').length,
                new: response.data.filter(t => t.status === 'new').length
            };
            setStats(newStats);
        } catch (err) {
            console.error('Error fetching tickets:', err);
        } finally {
            setLoading(false);
        }
    };

    const filterTickets = (status) => {
        setFilter(status);
    };

    const getFilteredTickets = () => {
        if (filter === 'all') return tickets;
        return tickets.filter(t => t.status === filter);
    };

    if (loading) {
        return <div className="loading">Loading dashboard...</div>;
    }

    return (
        <div className="agent-dashboard">
            <div className="dashboard-header">
                <h1>Welcome back, {user?.first_name || user?.username}!</h1>
                <p className="agent-badge">Agent Dashboard</p>
            </div>

            <div className="stats-grid">
                <div className="stat-card total">
                    <h3>Total Tickets</h3>
                    <p className="stat-number">{stats.total}</p>
                </div>
                <div className="stat-card new">
                    <h3>New</h3>
                    <p className="stat-number">{stats.new || 0}</p>
                </div>
                <div className="stat-card open">
                    <h3>Open</h3>
                    <p className="stat-number">{stats.open}</p>
                </div>
                <div className="stat-card pending">
                    <h3>Pending</h3>
                    <p className="stat-number">{stats.pending}</p>
                </div>
                <div className="stat-card resolved">
                    <h3>Resolved</h3>
                    <p className="stat-number">{stats.resolved}</p>
                </div>
            </div>

            <div className="tickets-section">
                <div className="section-header">
                    <h2>All Tickets</h2>
                    <div className="filter-buttons">
                        <button 
                            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                            onClick={() => filterTickets('all')}
                        >
                            All ({stats.total})
                        </button>
                        <button 
                            className={`filter-btn ${filter === 'new' ? 'active' : ''}`}
                            onClick={() => filterTickets('new')}
                        >
                            New ({stats.new || 0})
                        </button>
                        <button 
                            className={`filter-btn ${filter === 'open' ? 'active' : ''}`}
                            onClick={() => filterTickets('open')}
                        >
                            Open ({stats.open})
                        </button>
                        <button 
                            className={`filter-btn ${filter === 'pending' ? 'active' : ''}`}
                            onClick={() => filterTickets('pending')}
                        >
                            Pending ({stats.pending})
                        </button>
                        <button 
                            className={`filter-btn ${filter === 'resolved' ? 'active' : ''}`}
                            onClick={() => filterTickets('resolved')}
                        >
                            Resolved ({stats.resolved})
                        </button>
                    </div>
                </div>

                <div className="tickets-table-container">
                    <table className="tickets-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Title</th>
                                <th>Customer</th>
                                <th>Status</th>
                                <th>Priority</th>
                                <th>Assigned To</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {getFilteredTickets().map(ticket => (
                                <tr key={ticket.id}>
                                    <td>#{ticket.id}</td>
                                    <td>{ticket.title}</td>
                                    <td>{ticket.customer_name}</td>
                                    <td>
                                        <span className={`status-badge status-${ticket.status}`}>
                                            {ticket.status}
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`priority-badge priority-${ticket.priority}`}>
                                            {ticket.priority}
                                        </span>
                                    </td>
                                    <td>{ticket.assigned_to_name || 'Unassigned'}</td>
                                    <td>{new Date(ticket.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <button 
                                            className="view-btn"
                                            onClick={() => navigate(`/agent/tickets/${ticket.id}`)}
                                        >
                                            View
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default AgentDashboard;