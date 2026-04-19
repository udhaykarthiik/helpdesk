import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { agentApi } from '../services/api';
import './AgentTicketDetail.css';

function AgentTicketDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [ticket, setTicket] = useState(null);
    const [loading, setLoading] = useState(true);
    const [reply, setReply] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [status, setStatus] = useState('');
    const [showCanned, setShowCanned] = useState(false);
    const [cannedResponses, setCannedResponses] = useState([]);
    const [renderingCanned, setRenderingCanned] = useState(false);
    
    // ========== ATTACHMENT STATES ==========
    const [attachments, setAttachments] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploading, setUploading] = useState(false);

    useEffect(() => {
        fetchTicket();
        fetchCannedResponses();
        fetchAttachments();
    }, [id]);

    const fetchTicket = async () => {
        try {
            setLoading(true);
            const response = await agentApi.getTicket(id);
            setTicket(response.data);
            setStatus(response.data.status);
        } catch (err) {
            console.error('Error fetching ticket:', err);
            navigate('/agent/dashboard');
        } finally {
            setLoading(false);
        }
    };

    const fetchCannedResponses = async () => {
        try {
            const response = await agentApi.getCannedResponses();
            setCannedResponses(response.data);
        } catch (err) {
            console.error('Error fetching canned responses:', err);
        }
    };

    // ========== FETCH ATTACHMENTS ==========
    const fetchAttachments = async () => {
        try {
            const response = await agentApi.getAttachments(id);
            setAttachments(response.data);
        } catch (err) {
            console.error('Error fetching attachments:', err);
        }
    };

    // ========== HANDLE FILE UPLOAD ==========
    const handleFileUpload = async () => {
        if (!selectedFile) return;
        
        setUploading(true);
        try {
            await agentApi.addAttachment(id, selectedFile, 'agent');
            setSelectedFile(null);
            fetchAttachments();
            // Clear file input
            const fileInput = document.getElementById('file-input');
            if (fileInput) fileInput.value = '';
        } catch (err) {
            console.error('Error uploading file:', err);
            alert('Failed to upload file');
        } finally {
            setUploading(false);
        }
    };

    const handleStatusChange = async (newStatus) => {
        try {
            await agentApi.quickStatusChange(id, newStatus);
            setStatus(newStatus);
            setTicket({ ...ticket, status: newStatus });
        } catch (err) {
            console.error('Error updating status:', err);
        }
    };

    const handleAssignToMe = async () => {
        try {
            const response = await agentApi.quickAssignToMe(id);
            setTicket({ ...ticket, assigned_to_name: response.data.assigned_to });
        } catch (err) {
            console.error('Error assigning to self:', err);
        }
    };

    const handleResolve = async () => {
        try {
            await agentApi.quickResolve(id);
            setStatus('resolved');
            setTicket({ ...ticket, status: 'resolved' });
        } catch (err) {
            console.error('Error resolving ticket:', err);
        }
    };

    const handleAddConversation = async (e) => {
        e.preventDefault();
        if (!reply.trim()) return;

        setSubmitting(true);
        try {
            await agentApi.addConversation(id, {
                sender_type: 'agent',
                message: reply,
                is_internal_note: false
            });
            setReply('');
            fetchTicket();
        } catch (err) {
            console.error('Error sending reply:', err);
        } finally {
            setSubmitting(false);
        }
    };

    const handleAddInternalNote = async () => {
        if (!reply.trim()) return;

        setSubmitting(true);
        try {
            await agentApi.quickNote(id, reply);
            setReply('');
            fetchTicket();
        } catch (err) {
            console.error('Error adding note:', err);
        } finally {
            setSubmitting(false);
        }
    };

    const insertCannedResponse = async (cannedId, content) => {
        setRenderingCanned(true);
        try {
            const response = await agentApi.renderCannedResponse({
                canned_response_id: cannedId,
                ticket_id: parseInt(id)
            });
            const renderedContent = response.data.rendered_content;
            setReply(reply + '\n' + renderedContent);
        } catch (err) {
            console.error('Error rendering canned response:', err);
            setReply(reply + '\n' + content);
        } finally {
            setRenderingCanned(false);
            setShowCanned(false);
        }
    };

    if (loading) {
        return <div className="loading">Loading ticket...</div>;
    }

    if (!ticket) {
        return <div className="loading">Ticket not found</div>;
    }

    return (
        <div className="ticket-detail-container">
            <div className="ticket-detail-header">
                <button onClick={() => navigate('/agent/dashboard')} className="back-btn">
                    ← Back to Dashboard
                </button>
                <h1>Ticket #{ticket.id}: {ticket.title}</h1>
            </div>

            <div className="ticket-detail-grid">
                {/* Left Column - Ticket Info */}
                <div className="ticket-info-panel">
                    <div className="info-section">
                        <h3>Customer Information</h3>
                        <p><strong>Name:</strong> {ticket.customer_name}</p>
                        <p><strong>Email:</strong> {ticket.customer_email}</p>
                        {ticket.customer_is_vip && (
                            <p className="vip-badge">⭐ VIP Customer</p>
                        )}
                    </div>

                    <div className="info-section">
                        <h3>Ticket Details</h3>
                        <p><strong>Status:</strong> 
                            <select value={status} onChange={(e) => handleStatusChange(e.target.value)}>
                                <option value="new">New</option>
                                <option value="open">Open</option>
                                <option value="pending">Pending</option>
                                <option value="resolved">Resolved</option>
                                <option value="closed">Closed</option>
                            </select>
                        </p>
                        <p><strong>Priority:</strong> 
                            <span className={`priority-badge priority-${ticket.priority}`}>
                                {ticket.priority}
                            </span>
                        </p>
                        <p><strong>Channel:</strong> {ticket.channel}</p>
                        <p><strong>Created:</strong> {new Date(ticket.created_at).toLocaleString()}</p>
                        <p><strong>Assigned to:</strong> {ticket.assigned_to_name || 'Unassigned'}</p>
                    </div>

                    <div className="info-section">
                        <h3>Actions</h3>
                        <div className="action-buttons">
                            <button onClick={handleAssignToMe} className="action-btn assign">
                                Assign to Me
                            </button>
                            <button onClick={handleResolve} className="action-btn resolve">
                                Resolve Ticket
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right Column - Conversations */}
                <div className="conversations-panel">
                    <div className="conversations-header">
                        <h3>Conversation History</h3>
                        <button 
                            className="canned-btn"
                            onClick={() => setShowCanned(!showCanned)}
                            disabled={renderingCanned}
                        >
                            📋 Canned Responses {renderingCanned && '(Loading...)'}
                        </button>
                    </div>

                    {showCanned && (
                        <div className="canned-list">
                            <h4>Quick Templates:</h4>
                            {cannedResponses.map(cr => (
                                <button 
                                    key={cr.id}
                                    className="canned-item"
                                    onClick={() => insertCannedResponse(cr.id, cr.content)}
                                    disabled={renderingCanned}
                                >
                                    <strong>{cr.title}</strong> ({cr.shortcode})
                                </button>
                            ))}
                        </div>
                    )}

                    <div className="conversations-list">
                        {ticket.conversations?.map((conv, index) => (
                            <div key={conv.id || index} className={`message ${conv.sender_type}`}>
                                <div className="message-header">
                                    <span className="sender">
                                        {conv.sender_type === 'agent' ? '👤 Agent' : '👤 Customer'}
                                    </span>
                                    <span className="time">
                                        {new Date(conv.created_at).toLocaleString()}
                                    </span>
                                </div>
                                <div className="message-body">
                                    {conv.message.split('\n').map((line, i) => (
                                        <p key={i}>{line}</p>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* ========== ATTACHMENTS SECTION ========== */}
                    <div className="attachment-section">
                        <h4>Attachments</h4>
                        <div className="attachment-list">
                            {attachments.map(att => (
                                <div key={att.id} className="attachment-item">
                                    <a href={att.file_url} target="_blank" rel="noopener noreferrer">
                                        📎 {att.filename} ({att.file_size_display})
                                    </a>
                                    <span className="attachment-by">Uploaded by: {att.uploaded_by}</span>
                                </div>
                            ))}
                            {attachments.length === 0 && (
                                <div className="no-attachments">No attachments yet</div>
                            )}
                        </div>
                        
                        <div className="upload-section">
                            <input 
                                type="file" 
                                id="file-input"
                                onChange={(e) => setSelectedFile(e.target.files[0])}
                            />
                            <button 
                                onClick={handleFileUpload} 
                                disabled={!selectedFile || uploading}
                                className="upload-btn"
                            >
                                {uploading ? 'Uploading...' : 'Upload File'}
                            </button>
                        </div>
                    </div>

                    <div className="reply-form">
                        <h3>Reply to Customer</h3>
                        <textarea
                            value={reply}
                            onChange={(e) => setReply(e.target.value)}
                            placeholder="Type your reply here..."
                            rows="5"
                        />
                        <div className="reply-buttons">
                            <button 
                                onClick={handleAddConversation}
                                disabled={submitting || !reply.trim()}
                                className="send-btn"
                            >
                                {submitting ? 'Sending...' : 'Send Reply'}
                            </button>
                            <button 
                                onClick={handleAddInternalNote}
                                disabled={submitting || !reply.trim()}
                                className="note-btn"
                            >
                                Add Internal Note
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AgentTicketDetail;