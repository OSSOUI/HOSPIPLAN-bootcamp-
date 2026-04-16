import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../api/client';

export default function PlanningGenerator() {
  const navigate = useNavigate();
  
  const [form, setForm] = useState({
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    service_id: '',
  });
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await client.post('/plannings/generate/', {
        start_date: form.start_date,
        end_date: form.end_date,
        service_id: form.service_id || null,
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data || { message: 'Erreur lors de la génération' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2> Générateur Automatique de Planning</h2>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Générez automatiquement un planning optimal en respectant les contraintes dures
        tout en minimisant les contraintes molles.
      </p>

      <form onSubmit={handleGenerate} style={{
        background: 'white', padding: '20px', borderRadius: '10px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '20px'
      }}>
        <div style={{ display: 'grid', gap: '15px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Date de début
            </label>
            <input
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              style={inputStyle}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Date de fin
            </label>
            <input
              type="date"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              style={inputStyle}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? '#ccc' : '#10b981',
              color: 'white', padding: '12px 24px', border: 'none',
              borderRadius: '8px', fontSize: '16px', cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: 'bold', marginTop: '10px'
            }}
          >
            {loading ? ' Génération en cours...' : ' Générer le planning'}
          </button>
        </div>
      </form>

      {error && (
        <div style={errorStyle}>
           {error.message || 'Erreur lors de la génération'}
        </div>
      )}

      {result && (
        <div style={resultStyle}>
          <h3 style={{ marginTop: 0 }}>
            {result.success ? ' Succès' : ' Résultat partiel'}
          </h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div style={statBox}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#10b981' }}>
                {result.assignments_count}
              </div>
              <div>Gardes affectées</div>
            </div>
            
            <div style={statBox}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: result.uncovered_shifts > 0 ? '#e53e3e' : '#10b981' }}>
                {result.uncovered_shifts}
              </div>
              <div>Gardes non couvertes</div>
            </div>
            
            <div style={statBox}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#3182ce' }}>
                {result.total_shifts}
              </div>
              <div>Total des gardes</div>
            </div>
            
            <div style={statBox}>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#805ad5' }}>
                {result.quality_score}%
              </div>
              <div>Score de qualité</div>
            </div>
          </div>

          <p style={{ marginTop: '15px', color: '#666' }}>{result.message}</p>

          <button
            onClick={() => navigate('/planning')}
            style={{
              background: '#3182ce', color: 'white', padding: '10px 20px',
              border: 'none', borderRadius: '6px', cursor: 'pointer', marginTop: '10px'
            }}
          >
             Voir le planning
          </button>
        </div>
      )}
    </div>
  );
}

const inputStyle = {
  width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '14px'
};

const errorStyle = {
  background: '#fff5f5', border: '1px solid #fc8181', borderRadius: '8px',
  padding: '15px', color: '#c53030', marginBottom: '20px'
};

const resultStyle = {
  background: 'white', padding: '20px', borderRadius: '10px',
  boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
};

const statBox = {
  background: '#f7fafc', padding: '15px', borderRadius: '8px', textAlign: 'center'
};