import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { staffAPI, shiftAPI, assignmentAPI } from '../api/client';
import ErrorAlert from '../components/ErrorAlert';

export default function AssignmentForm() {
  const navigate = useNavigate();

  const [staffList, setStaffList] = useState([]);
  const [shiftList, setShiftList] = useState([]);
  const [selectedStaff, setSelectedStaff] = useState('');
  const [selectedShift, setSelectedShift] = useState('');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [saving, setSaving] = useState(false);
  const [eligibleInfo, setEligibleInfo] = useState(null);

  useEffect(() => {
    staffAPI.list({ page_size: 200 })
      .then(res => setStaffList(res.data.results || res.data));

    const today = new Date().toISOString().split('T')[0];
    shiftAPI.list({ date_from: today })
      .then(res => setShiftList(res.data.results || res.data));
  }, []);

  // Quand on sélectionne un shift, charger les éligibles
  useEffect(() => {
    if (selectedShift) {
      shiftAPI.eligibleStaff(selectedShift)
        .then(res => setEligibleInfo(res.data))
        .catch(() => setEligibleInfo(null));
    } else {
      setEligibleInfo(null);
    }
  }, [selectedShift]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      await assignmentAPI.create({
        staff_id: parseInt(selectedStaff),
        shift_id: parseInt(selectedShift),
      });
      setSuccess('Affectation créée avec succès !');
      setSelectedStaff('');
      setSelectedShift('');
      setEligibleInfo(null);
    } catch (err) {
      // Extraire les erreurs de contraintes dures
      const responseData = err.response?.data;
      if (responseData) {
        // DRF peut imbriquer les erreurs de différentes manières
        const violations =
          responseData.violations ||
          responseData.non_field_errors?.[0]?.violations ||
          null;

        if (violations) {
          setError({
            message: 'Affectation refusée — contraintes dures violées.',
            violations: violations,
          });
        } else {
          setError(err);
        }
      } else {
        setError(err);
      }
    } finally {
      setSaving(false);
    }
  };

  const formatShift = (s) => {
    const d = new Date(s.start_datetime);
    return `${s.shift_type_name} — ${s.care_unit_name} — ${d.toLocaleDateString('fr-FR')} ${d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`;
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '800px' }}>
      <h2> Nouvelle Affectation</h2>
      <p style={{ color: '#666' }}>
        Affectez un soignant à un créneau de garde. Les contraintes dures
        seront vérifiées automatiquement.
      </p>

      <ErrorAlert error={error} onClose={() => setError(null)} />

      {success && (
        <div style={{
          background: '#f0fff4', border: '1px solid #68d391',
          borderRadius: '8px', padding: '1rem 1.5rem', margin: '1rem 0',
        }}>
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{
        display: 'flex', flexDirection: 'column', gap: '1.5rem',
        background: '#fff', padding: '2rem', borderRadius: '12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)', marginTop: '1rem',
      }}>
        {/* Sélection du créneau */}
        <div>
          <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '0.5rem' }}>
            Créneau de garde *
          </label>
          <select
            value={selectedShift}
            onChange={e => setSelectedShift(e.target.value)}
            required
            style={{ ...inputStyle, width: '100%' }}
          >
            <option value="">-- Choisir un créneau --</option>
            {shiftList.map(s => (
              <option key={s.id} value={s.id}>
                {formatShift(s)} [{s.current_staff_count}/{s.min_staff}]
              </option>
            ))}
          </select>
        </div>

        {/* Info d'éligibilité */}
        {eligibleInfo && (
          <div style={{
            background: '#ebf8ff', borderRadius: '8px',
            padding: '1rem', fontSize: '0.9rem',
          }}>
            <strong>
              {eligibleInfo.eligible_count} soignant(s) éligible(s)
            </strong> sur {eligibleInfo.total_checked} vérifiés.

            {eligibleInfo.eligible.length > 0 && (
              <div style={{ marginTop: '0.5rem' }}>
                <em>Éligibles :</em>{' '}
                {eligibleInfo.eligible.map(e => e.name).join(', ')}
              </div>
            )}
          </div>
        )}

        {/* Sélection du soignant */}
        <div>
          <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '0.5rem' }}>
             Soignant *
          </label>
          <select
            value={selectedStaff}
            onChange={e => setSelectedStaff(e.target.value)}
            required
            style={{ ...inputStyle, width: '100%' }}
          >
            <option value="">-- Choisir un soignant --</option>
            {staffList.filter(s => s.is_active).map(s => {
              // Indiquer si éligible
              const isEligible = eligibleInfo?.eligible?.some(e => e.id === s.id);
              const isIneligible = eligibleInfo?.ineligible?.some(e => e.id === s.id);

              return (
                <option
                  key={s.id}
                  value={s.id}
                  style={{
                    color: isIneligible ? '#e53e3e' : isEligible ? '#38a169' : '#000',
                  }}
                >
                  {isEligible ? '✓ ' : isIneligible ? '✗ ' : ''}
                  {s.last_name} {s.first_name}
                  {s.roles?.length > 0 && ` (${s.roles.join(', ')})`}
                </option>
              );
            })}
          </select>
        </div>

        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            type="submit"
            disabled={saving || !selectedStaff || !selectedShift}
            style={{
              background: saving ? '#a0aec0' : '#38a169',
              color: '#fff', border: 'none', borderRadius: '6px',
              padding: '0.7rem 2rem', cursor: 'pointer',
              fontSize: '1rem', fontWeight: 'bold',
            }}
          >
            {saving ? 'Vérification en cours...' : '✓ Affecter'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/shifts')}
            style={{
              background: '#eee', border: 'none',
              borderRadius: '6px', padding: '0.7rem 2rem',
              cursor: 'pointer',
            }}
          >
            Retour
          </button>
        </div>
      </form>
    </div>
  );
}

const inputStyle = {
  padding: '0.6rem', borderRadius: '6px',
  border: '1px solid #ddd', fontSize: '1rem',
};