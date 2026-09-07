import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // Cấu hình axios mặc định
    axios.defaults.withCredentials = true;
    axios.defaults.withXSRFToken = true;

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const response = await axios.get('/api/user');
                setUser(response.data.user);
            } catch (error) {
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        fetchUser();
    }, []);

    const login = async (email, password) => {
        await axios.get('/sanctum/csrf-cookie');
        const response = await axios.post('/api/login', { email, password });
        setUser(response.data.user);
    };

    const register = async (name, email, password, company) => {
        await axios.get('/sanctum/csrf-cookie');
        const response = await axios.post('/api/register', { name, email, password, company });
        setUser(response.data.user);
    };

    const logout = async () => {
        await axios.post('/api/logout');
        setUser(null);
    };

    const updateProfile = async (data) => {
        const response = await axios.post('/api/profile', data);
        setUser(response.data.user);
        return response.data;
    };

    return (
        <AuthContext.Provider value={{ user, login, register, logout, updateProfile, loading }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};
