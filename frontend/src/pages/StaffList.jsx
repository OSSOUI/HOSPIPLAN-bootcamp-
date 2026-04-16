import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { staffAPI } from '../api/client';
import ErrorAlert from '../components/ErrorAlert';

export default function StaffList() {
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const fetchStaff = () => {
    setLoading(true);
    staffAPI.list({ search })
      .then(res => {
        setStaff(res.data.results || res.data);
        setError(null);
      })
      .catch(err => setError(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStaff();
  }, [search]);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Désactiver ${name} ?`)) return;
    try {
      await staffAPI.delete(id);
      fetchStaff();
    } catch (err) {
      setError(err);
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2> Liste des Soignants</h2>
        <Link to="/staff/new">
          <button style={{
            background: '#3182ce', color: '#fff',
            border: 'none', borderRadius: '6px',
            padding: '0.6rem 1.2rem', cursor: 'pointer',
            fontSize: '1rem',
          }}>
            + Nouveau soignant
          </button>
        </Link>
      </div>

      <input
        type="text"
        placeholder="🔍 Rechercher par nom ou email..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{
          width: '100%', maxWidth: '400px',
          padding: '0.6rem 1rem', margin: '1rem 0',
          borderRadius: '6px', border: '1px solid #ddd',
          fontSize: '1rem',
        }}
      />

      <ErrorAlert error={error} onClose={() => setError(null)} />

      {loading ? (
        <p>Chargement...</p>
      ) : (
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          background: '#fff', borderRadius: '8px',
          overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        }}>
          <thead>
            <tr style={{ background: '#edf2f7' }}>
              <th style={thStyle}>Nom</th>
              <th style={thStyle}>Email</th>
              <th style={thStyle}>Téléphone</th>
              <th style={thStyle}>Rôles</th>
              <th style={thStyle}>Statut</th>
              <th style={thStyle}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {staff.map(s => (
              <tr key={s.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={tdStyle}>
                  <strong>{s.last_name} {s.first_name}</strong>
                </td>
                <td style={tdStyle}>{s.email}</td>
                <td style={tdStyle}>{s.phone || '—'}</td>
                <td style={tdStyle}>
                  {s.roles?.map((r, i) => (
                    <span key={i} style={{
                      background: '#ebf8ff', color: '#2b6cb0',
                      padding: '2px 8px', borderRadius: '12px',
                      fontSize: '0.8rem', marginRight: '4px',
                    }}>
                      {r}
                    </span>
                  ))}
                </td>
                <td style={tdStyle}>
                  <span style={{
                    color: s.is_active ? '#38a169' : '#e53e3e',
                    fontWeight: 'bold',
                  }}>
                    {s.is_active ? '● Actif' : '○ Inactif'}
                  </span>
                </td>
                <td style={tdStyle}>
                  <Link to={`/staff/${s.id}/edit`}>
                    <button style={btnSmall}>✏️</button>
                  </Link>
                  <button
                    style={{ ...btnSmall, color: '#e53e3e' }}
                    onClick={() => handleDelete(s.id, `${s.last_name} ${s.first_name}`)}
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const thStyle = {
  textAlign: 'left', padding: '0.8rem 1rem',
  fontSize: '0.85rem', color: '#4a5568',
};
const tdStyle = {
  padding: '0.7rem 1rem', fontSize: '0.9rem',
};
const btnSmall = {
  background: 'none', border: '1px solid #ddd',
  borderRadius: '4px', padding: '4px 8px',
  cursor: 'pointer', marginRight: '4px',
};