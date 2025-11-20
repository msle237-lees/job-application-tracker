import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Company API
export const getCompanies = () => api.get('/companies');
export const getCompany = (id) => api.get(`/companies/${id}`);
export const createCompany = (data) => api.post('/companies', data);
export const deleteCompany = (id) => api.delete(`/companies/${id}`);

// Application API
export const getApplications = () => api.get('/applications');
export const getApplication = (id) => api.get(`/applications/${id}`);
export const createApplication = (data) => api.post('/applications', data);
export const updateApplication = (id, data) => api.put(`/applications/${id}`, data);
export const deleteApplication = (id) => api.delete(`/applications/${id}`);

// Contact API
export const getContacts = () => api.get('/contacts');
export const createContact = (data) => api.post('/contacts', data);

// Stage API
export const getStages = () => api.get('/stages');
export const createStage = (data) => api.post('/stages', data);

// Analytics API
export const getAnalytics = () => api.get('/analytics');

export default api;
