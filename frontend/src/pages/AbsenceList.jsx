import { useState, useEffect } from 'react';
import { absenceAPI, staffAPI, absenceTypeAPI } from '../api/client';
import ErrorAlert from '../components/ErrorAlert';

export default function AbsenceList() {
  const [absences, setAbsences] = useState([]);
  const [staffList, setStaffList] = useState([]);
  const [absenceTypes, setAbsenceTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    staff: '',
    absence_type: '',
    start_date: '',
    expected_end_date: '',
    is_planned: true,
  });

  const fetchAbsences = () => {
    setLoading(true);
    absenceAPI.list()
      .then(res => setAbsences(res.data.results || res.data))
      .catch(err => setError(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchAbsences();
    staffAPI.list({ page_size: 200 }).then(res => setStaffList(res.data.results || res.data));
    absenceTypeAPI.list().then(res => setAbsenceTypes(res.data.results || res.data));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await absenceAPI.create(form);
      setShowForm(false);
      setForm({ staff: '', absence_type: '', start_date: '', expected_end_date: '', is_planned: true });
      fetchAbsences();
    } catch (err) {
      setError(err);
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2> Absences</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            background: '#d69e2e', color: '#fff',
            border: 'none', borderRadius: '6px',
            padding: '0.6rem 1.2rem', cursor: 'pointer',
          }}
        >
          {showForm ? 'Annuler' : '+ Déclarer une absence'}
        </button>
      </div>

      <ErrorAlert error={error} onClose={() => setError(null)} />

      {showForm && (
        <form onSubmit={handleSubmit} style={{
          background: '#fff', padding: '1.5rem', borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)', margin: '1rem 0',
          display: 'flex', flexWrap: 'wrap', gap: '1rem',
        }}>
          <select
            value={form.staff}
            onChange={e => setForm(prev => ({ ...prev, staff: e.target.value }))}
            required
            style={inputStyle}
          >
            <option value="">Soignant...</option>
            {staffList.map(s => (
              <option key={s.id} value={s.id}>{s.last_name} {s.first_name}</option>
            ))}
          </select>

          <select
            value={form.absence_type}
            onChange={e => setForm(prev => ({ ...prev, absence_type: e.target.value }))}
            required
            style={inputStyle}
          >
            <option value="">Type d'absence...</option>
            {absenceTypes.map(at => (
              <option key={at.id} value={at.id}>{at.name}</option>
            ))}
          </select>

          <input
            type="date"
            value={form.start_date}
            onChange={e => setForm(prev => ({ ...prev, start_date: e.target.value }))}
            required
            style={inputStyle}
          />
          <input
            type="date"
            value={form.expected_end_date}
            onChange={e => setForm(prev => ({ ...prev, expected_end_date: e.target.value }))}
            required
            style={inputStyle}
          />

          <label>
            <input
              type="checkbox"
              checked={form.is_planned}
              onChange={e => setForm(prev => ({ ...prev, is_planned: e.target.checked }))}
            />
            {' '}Planifiée
          </label>

          <button type="submit" style={{
            background: '#38a169', color: '#fff',
            border: 'none', borderRadius: '6px',
            padding: '0.5rem 1.5rem', cursor: 'pointer',
          }}>
            Enregistrer
          </button>
        </form>
      )}

      {loading ? (
        <p>Chargement...</p>
      ) : (
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          background: '#fff', borderRadius: '8px',
          overflow: 'hidden', boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
          marginTop: '1rem',
        }}>
          <thead>
            <tr style={{ background: '#edf2f7' }}>
              <th style={thStyle}>Soignant</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Début</th>
              <th style={thStyle}>Fin prévue</th>
              <th style={thStyle}>Fin réelle</th>
              <th style={thStyle}>Planifiée</th>
            </tr>
          </thead>
          <tbody>
            {absences.map(a => (
              <tr key={a.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={tdStyle}>{a.staff_name}</td>
                <td style={tdStyle}>{a.absence_type_name}</td>
                <td style={tdStyle}>{a.start_date}</td>
                <td style={tdStyle}>{a.expected_end_date}</td>
                <td style={tdStyle}>{a.actual_end_date || '—'}</td>
                <td style={tdStyle}>{a.is_planned ? '✓ Oui' : '✗ Non'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const inputStyle = {
  padding: '0.5rem', borderRadius: '6px',
  border: '1px solid #ddd', fontSize: '0.9rem',
};
const thStyle = {
  textAlign: 'left', padding: '0.8rem 1rem',
  fontSize: '0.85rem', color: '#4a5568',
};
const tdStyle = { padding: '0.7rem 1rem', fontSize: '0.9rem' };