import apiClient from './client';

// রেজিস্ট্রেশন যেমন ছিল তেমনই থাকবে (JSON)
export const registerUser = async (userData: any) => {
    const response = await apiClient.post('/register', userData);
    return response.data;
};

// লগইন আপডেট করুন (Form Data ফরম্যাটে)
export const loginUser = async (credentials: any) => {
    const response = await apiClient.post('/login', {
        email: credentials.email,
        password: credentials.password
    });
    return response.data;
};

// বর্তমান ইউজারের তথ্য আনার জন্য
export const fetchCurrentUser = async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
};

// ১. পাসওয়ার্ড রিসেট ইমেইল পাঠানো
export const sendForgotPasswordRequest = async (email: string) => {
    const response = await apiClient.post('/forgot-password', { email });
    return response.data;
};

// ২. নতুন পাসওয়ার্ড সেট করা
export const resetUserPassword = async (token: string, newPassword: string) => {
    const response = await apiClient.post('/reset-password', {
        token,
        new_password: newPassword
    });
    return response.data;
};
