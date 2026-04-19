import React, { createContext, useState, useEffect, useContext } from 'react';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const checkAuthStatus = () => {
        const token = localStorage.getItem('access_token');
        const userStr = localStorage.getItem('user');
        
        if (token && userStr) {
            setIsLoggedIn(true);
            setUser(JSON.parse(userStr));
        } else {
            setIsLoggedIn(false);
            setUser(null);
        }
        setLoading(false);
    };

    useEffect(() => {
        checkAuthStatus();
        
        // Listen for storage changes
        window.addEventListener('storage', checkAuthStatus);
        window.addEventListener('authChange', checkAuthStatus);
        
        return () => {
            window.removeEventListener('storage', checkAuthStatus);
            window.removeEventListener('authChange', checkAuthStatus);
        };
    }, []);

    const login = (userData, tokens) => {
        localStorage.setItem('access_token', tokens.access);
        localStorage.setItem('refresh_token', tokens.refresh);
        localStorage.setItem('user', JSON.stringify(userData.user || userData));
        localStorage.setItem('user_role', userData.role || 'customer');
        
        setIsLoggedIn(true);
        setUser(userData.user || userData);
        
        // Dispatch event
        window.dispatchEvent(new Event('authChange'));
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('user_role');
        
        setIsLoggedIn(false);
        setUser(null);
        
        // Dispatch event
        window.dispatchEvent(new Event('authChange'));
    };

    return (
        <AuthContext.Provider value={{ isLoggedIn, user, loading, login, logout, checkAuthStatus }}>
            {children}
        </AuthContext.Provider>
    );
};