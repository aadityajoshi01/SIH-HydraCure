const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://YOUR-BACKEND-DOMAIN.com';

window.API_BASE_URL = API_BASE_URL;
