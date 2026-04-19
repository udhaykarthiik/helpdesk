import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { publicApi } from '../services/api';
import './KnowledgeArticle.css';

function KnowledgeArticle() {
    const { id } = useParams();
    const [article, setArticle] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [feedback, setFeedback] = useState(null);
    const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

    useEffect(() => {
        const fetchArticle = async () => {
            try {
                setLoading(true);
                const response = await publicApi.getArticle(id, { params: { public: true } });
                setArticle(response.data);
            } catch (err) {
                console.error('Error fetching article:', err);
                setError('Failed to load article. It may have been removed.');
            } finally {
                setLoading(false);
            }
        };
        
        fetchArticle();
    }, [id]);

    const handleFeedback = async (isHelpful) => {
        if (feedbackSubmitted) return;
        
        try {
            await publicApi.submitFeedback(id, {
                is_helpful: isHelpful,
                session_id: localStorage.getItem('session_id') || 'anonymous'
            });
            setFeedback(isHelpful);
            setFeedbackSubmitted(true);
            
            // Update article stats
            setArticle(prev => ({
                ...prev,
                helpful_count: prev.helpful_count + (isHelpful ? 1 : 0),
                not_helpful_count: prev.not_helpful_count + (isHelpful ? 0 : 1)
            }));
        } catch (err) {
            console.error('Error submitting feedback:', err);
        }
    };

    if (loading) {
        return <div className="loading">Loading article...</div>;
    }

    if (error || !article) {
        return (
            <div className="error-container">
                <h2>Article Not Found</h2>
                <p>{error || 'The article you\'re looking for doesn\'t exist.'}</p>
                <Link to="/kb" className="back-btn">← Back to Knowledge Base</Link>
            </div>
        );
    }

    return (
        <div className="article-container">
            <div className="article-header">
                <Link to="/kb" className="back-link">← Back to Knowledge Base</Link>
                <div className="article-meta">
                    <span className="article-category">{article.category_name}</span>
                    <span className="article-views">👁️ {article.views} views</span>
                </div>
                <h1 className="article-title">{article.title}</h1>
                {article.summary && (
                    <p className="article-summary">{article.summary}</p>
                )}
                <div className="article-tags">
                    {article.tags_list?.map(tag => (
                        <Link to={`/kb?tag=${tag}`} key={tag} className="tag">
                            #{tag}
                        </Link>
                    ))}
                </div>
            </div>

            <div className="article-content">
                {article.content.split('\n').map((paragraph, index) => {
                    if (paragraph.startsWith('# ')) {
                        return <h1 key={index}>{paragraph.substring(2)}</h1>;
                    } else if (paragraph.startsWith('## ')) {
                        return <h2 key={index}>{paragraph.substring(3)}</h2>;
                    } else if (paragraph.startsWith('### ')) {
                        return <h3 key={index}>{paragraph.substring(4)}</h3>;
                    } else if (paragraph.startsWith('- ')) {
                        return <li key={index}>{paragraph.substring(2)}</li>;
                    } else if (paragraph.trim() === '') {
                        return <br key={index} />;
                    } else {
                        return <p key={index}>{paragraph}</p>;
                    }
                })}
            </div>

            <div className="article-footer">
                <div className="article-helpfulness">
                    <p>Was this article helpful?</p>
                    <div className="feedback-buttons">
                        <button 
                            onClick={() => handleFeedback(true)}
                            disabled={feedbackSubmitted}
                            className={`feedback-btn yes-btn ${feedback === true ? 'selected' : ''}`}
                        >
                            👍 Yes ({article.helpful_count})
                        </button>
                        <button 
                            onClick={() => handleFeedback(false)}
                            disabled={feedbackSubmitted}
                            className={`feedback-btn no-btn ${feedback === false ? 'selected' : ''}`}
                        >
                            👎 No ({article.not_helpful_count})
                        </button>
                    </div>
                    {feedbackSubmitted && (
                        <p className="feedback-thanks">Thanks for your feedback!</p>
                    )}
                </div>

                <div className="article-help-stats">
                    <p>{article.helpful_percentage}% of people found this helpful</p>
                </div>
            </div>

            <div className="article-actions">
                <h3>Still need help?</h3>
                <div className="action-buttons">
                    <Link to="/ticket/new" className="action-btn primary">
                        Submit a Ticket
                    </Link>
                    <Link to="/" className="action-btn secondary">
                        Contact Support
                    </Link>
                </div>
            </div>
        </div>
    );
}

export default KnowledgeArticle;