import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Reset CSS minimal
const globalStyles = `
  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f7fafc;
    color: #2d3748;
  }
  a { color: inherit; }
`;

const styleSheet = document.createElement('style');
styleSheet.innerText = globalStyles;
document.head.appendChild(styleSheet);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
