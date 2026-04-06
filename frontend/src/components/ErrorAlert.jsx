export default function ErrorAlert({ error, onClose }) {
  if (!error) return null;

  // Extraire les violations si c'est une erreur de contrainte dure
  const violations = error?.response?.data?.violations || error?.violations || null;
  const message = error?.response?.data?.message || error?.message || 'Erreur inconnue';

  return (
    <div style={{
      background: '#fff5f5',
      border: '1px solid #fc8181',
      borderRadius: '8px',
      padding: '1rem 1.5rem',
      margin: '1rem 0',
      position: 'relative',
    }}>
      {onClose && (
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: '0.5rem', right: '0.8rem',
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: '1.2rem', color: '#999',
          }}
        >×</button>
      )}

      <p style={{ color: '#c53030', fontWeight: 'bold', margin: '0 0 0.5rem' }}>
        ❌ {message}
      </p>

      {violations && (
        <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem' }}>
          {violations.map((v, i) => (
            <li key={i} style={{ color: '#742a2a', marginBottom: '0.4rem' }}>
              <strong>[{v.code}]</strong> {v.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}