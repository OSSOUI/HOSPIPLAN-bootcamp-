import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour le logging (debug)
client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ─── Staff ───
export const staffAPI = {
  list: (params) => client.get('/staff/', { params }),
  get: (id) => client.get(`/staff/${id}/`),
  create: (data) => client.post('/staff/', data),
  update: (id, data) => client.put(`/staff/${id}/`, data),
  delete: (id) => client.delete(`/staff/${id}/`),
  absences: (id) => client.get(`/staff/${id}/absences/`),
  assignments: (id) => client.get(`/staff/${id}/assignments/`),
  certifications: (id) => client.get(`/staff/${id}/certifications/`),
};

// ─── Shifts ───
export const shiftAPI = {
  list: (params) => client.get('/shifts/', { params }),
  get: (id) => client.get(`/shifts/${id}/`),
  create: (data) => client.post('/shifts/', data),
  update: (id, data) => client.put(`/shifts/${id}/`, data),
  delete: (id) => client.delete(`/shifts/${id}/`),
  assignments: (id) => client.get(`/shifts/${id}/assignments/`),
  eligibleStaff: (id) => client.get(`/shifts/${id}/eligible_staff/`),
};

// ─── Assignments ───
export const assignmentAPI = {
  list: (params) => client.get('/assignments/', { params }),
  create: (data) => client.post('/assignments/', data),
  delete: (id) => client.delete(`/assignments/${id}/`),
};

// ─── Absences ───
export const absenceAPI = {
  list: (params) => client.get('/absences/', { params }),
  create: (data) => client.post('/absences/', data),
  delete: (id) => client.delete(`/absences/${id}/`),
};

// ─── Référentiels ───
export const roleAPI = {
  list: () => client.get('/roles/'),
};

export const serviceAPI = {
  list: () => client.get('/services/'),
};

export const careUnitAPI = {
  list: (params) => client.get('/care-units/', { params }),
};

export const shiftTypeAPI = {
  list: () => client.get('/shift-types/'),
};

export const absenceTypeAPI = {
  list: () => client.get('/absence-types/'),
};

// ─── Dashboard ───
export const dashboardAPI = {
  get: () => client.get('/dashboard/'),
};

export default client;