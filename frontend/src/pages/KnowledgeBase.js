import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { publicApi } from '../services/api';
import './KnowledgeBase.css';

function KnowledgeBase() {
    const [articles, setArticles] = useState([]);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [featuredArticles, setFeaturedArticles] = useState([]);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            
            // Fetch categories
            const categoriesRes = await publicApi.getCategories();
            setCategories(categoriesRes.data);
            
            // Fetch all articles (public)
            const articlesRes = await publicApi.getKnowledgeArticles({ public: true });
            setArticles(articlesRes.data);
            
            // Fetch popular articles
            const popularRes = await publicApi.getKnowledgeArticles({ popular: true, limit: 3 });
            setFeaturedArticles(popularRes.data);
            
        } catch (err) {
            console.error('Error fetching knowledge base:', err);
            setError('Failed to load knowledge base. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e) => {
        setSearchTerm(e.target.value);
    };

    const handleCategoryChange = (categoryId) => {
        setSelectedCategory(categoryId);
    };

    // Filter articles based on search and category
    const filteredArticles = articles.filter(article => {
        const matchesSearch = searchTerm === '' || 
            article.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (article.summary && article.summary.toLowerCase().includes(searchTerm.toLowerCase()));
        
        const matchesCategory = selectedCategory === 'all' || article.category === parseInt(selectedCategory);
        
        return matchesSearch && matchesCategory;
    });

    if (loading) {
        return <div className="loading">Loading knowledge base...</div>;
    }

    return (
        <div className="kb-container">
            <div className="kb-header">
                <h1>Knowledge Base</h1>
                <p>Find answers to common questions and learn how to make the most of QuickCart</p>
            </div>

            <div className="kb-search-section">
                <input
                    type="text"
                    placeholder="Search for articles..."
                    value={searchTerm}
                    onChange={handleSearch}
                    className="kb-search-input"
                />
            </div>

            {error && (
                <div className="error-message">{error}</div>
            )}

            <div className="kb-content">
                <aside className="kb-sidebar">
                    <h3>Categories</h3>
                    <ul className="category-list">
                        <li>
                            <button
                                className={`category-btn ${selectedCategory === 'all' ? 'active' : ''}`}
                                onClick={() => handleCategoryChange('all')}
                            >
                                All Categories
                            </button>
                        </li>
                        {categories.map(category => (
                            <li key={category.id}>
                                <button
                                    className={`category-btn ${selectedCategory === category.id.toString() ? 'active' : ''}`}
                                    onClick={() => handleCategoryChange(category.id)}
                                >
                                    {category.name}
                                    <span className="article-count">({category.article_count})</span>
                                </button>
                            </li>
                        ))}
                    </ul>

                    {featuredArticles.length > 0 && (
                        <div className="featured-articles">
                            <h3>Popular Articles</h3>
                            <ul>
                                {featuredArticles.map(article => (
                                    <li key={article.id}>
                                        <Link to={`/kb/${article.id}`}>{article.title}</Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </aside>

                <main className="kb-main">
                    <div className="articles-header">
                        <h2>
                            {selectedCategory === 'all' 
                                ? 'All Articles' 
                                : categories.find(c => c.id === parseInt(selectedCategory))?.name || 'Articles'}
                        </h2>
                        <span className="article-count">{filteredArticles.length} articles</span>
                    </div>

                    {filteredArticles.length === 0 ? (
                        <div className="no-results">
                            <p>No articles found matching your criteria.</p>
                            <button onClick={() => {
                                setSearchTerm('');
                                setSelectedCategory('all');
                            }} className="clear-filters-btn">
                                Clear Filters
                            </button>
                        </div>
                    ) : (
                        <div className="articles-grid">
                            {filteredArticles.map(article => (
                                <Link to={`/kb/${article.id}`} key={article.id} className="article-card">
                                    <h3>{article.title}</h3>
                                    {article.summary && <p>{article.summary}</p>}
                                    <div className="article-meta">
                                        <span className="article-category">
                                            {categories.find(c => c.id === article.category)?.name || 'General'}
                                        </span>
                                        <span className="article-views">👁️ {article.views} views</span>
                                        <span className="article-helpful">👍 {article.helpful_percentage}% helpful</span>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}

export default KnowledgeBase;