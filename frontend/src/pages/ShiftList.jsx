import { useState, useEffect } from 'react';
import { shiftAPI, serviceAPI } from '../api/client';

export default function ShiftList() {
  const [shifts, setShifts] = useState([]);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    service_id: '',
    date_from: new Date().toISOString().split('T')[0],
    date_to: '',
  });

  useEffect(() => {
    serviceAPI.list().then(res => setServices(res.data.results || res.data));
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = {};
    if (filters.service_id) params.service_id = filters.service_id;
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;

    shiftAPI.list(params)
      .then(res => setShifts(res.data.results || res.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const formatDateTime = (dt) => {
    const d = new Date(dt);
    return d.toLocaleDateString('fr-FR', {
      weekday: 'short', day: 'numeric', month: 'short',
    }) + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusColor = (shift) => {
    if (shift.current_staff_count >= shift.min_staff) return '#38a169';
    if (shift.current_staff_count > 0) return '#d69e2e';
    return '#e53e3e';
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2> Créneaux de garde</h2>

      {/* Filtres */}
      <div style={{ display: 'flex', gap: '1rem', margin: '1rem 0', flexWrap: 'wrap' }}>
        <select
          value={filters.service_id}
          onChange={e => setFilters(prev => ({ ...prev, service_id: e.target.value }))}
          style={inputStyle}
        >
          <option value="">Tous les services</option>
          {services.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        <input
          type="date"
          value={filters.date_from}
          onChange={e => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
          style={inputStyle}
        />
        <input
          type="date"
          value={filters.date_to}
          onChange={e => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
          style={inputStyle}
        />
      </div>

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
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Unité de soins</th>
              <th style={thStyle}>Début</th>
              <th style={thStyle}>Fin</th>
              <th style={thStyle}>Personnel</th>
              <th style={thStyle}>Certifications</th>
            </tr>
          </thead>
          <tbody>
            {shifts.map(s => (
              <tr key={s.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={tdStyle}>
                  <strong>{s.shift_type_name}</strong>
                  <br />
                  <small style={{ color: '#888' }}>{s.shift_type_duration}h</small>
                </td>
                <td style={tdStyle}>{s.care_unit_name}</td>
                <td style={tdStyle}>{formatDateTime(s.start_datetime)}</td>
                <td style={tdStyle}>{formatDateTime(s.end_datetime)}</td>
                <td style={tdStyle}>
                  <span style={{
                    color: getStatusColor(s),
                    fontWeight: 'bold',
                  }}>
                    {s.current_staff_count} / {s.min_staff}
                    {s.max_staff && ` (max ${s.max_staff})`}
                  </span>
                </td>
                <td style={tdStyle}>
                  {s.required_certifications?.length > 0
                    ? s.required_certifications.map((c, i) => (
                        <span key={i} style={{
                          background: '#fef5e7', color: '#c05621',
                          padding: '2px 6px', borderRadius: '8px',
                          fontSize: '0.75rem', marginRight: '3px',
                        }}>
                          {c}
                        </span>
                      ))
                    : <span style={{ color: '#aaa' }}>Aucune</span>
                  }
                </td>
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
const tdStyle = {
  padding: '0.7rem 1rem', fontSize: '0.9rem',
};