import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'your-api-key-here';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
  timeout: 30000,
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('Network Error:', error.message);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// API methods
export const api = {
  // Health check
  healthCheck: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Get current signal
  getCurrentSignal: async () => {
    const response = await apiClient.get('/api/v1/signal/current');
    return response.data;
  },

  // Get signal history
  getSignalHistory: async (start = null, end = null, limit = 100) => {
    const params = { limit };
    if (start) params.start = start;
    if (end) params.end = end;
    
    const response = await apiClient.get('/api/v1/signal/history', { params });
    return response.data;
  },

  // Run backtest
  runBacktest: async (config) => {
    const response = await apiClient.post('/api/v1/backtest', config);
    return response.data;
  },

  // Get backtest result
  getBacktestResult: async (backtestId) => {
    const response = await apiClient.get(`/api/v1/backtest/${backtestId}`);
    return response.data;
  },

  // Get orders
  getOrders: async (status = null, limit = 100) => {
    const params = { limit };
    if (status) params.status = status;
    
    const response = await apiClient.get('/api/v1/orders', { params });
    return response.data;
  },
};

export default apiClient;
