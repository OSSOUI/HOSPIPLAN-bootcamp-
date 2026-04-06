import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { staffAPI, roleAPI } from '../api/client';
import ErrorAlert from '../components/ErrorAlert';

export default function StaffForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditing = Boolean(id);

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    is_active: true,
    role_ids: [],
  });
  const [roles, setRoles] = useState([]);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    roleAPI.list().then(res => setRoles(res.data.results || res.data));

    if (isEditing) {
      staffAPI.get(id).then(res => {
        const data = res.data;
        setForm({
          first_name: data.first_name,
          last_name: data.last_name,
          email: data.email,
          phone: data.phone || '',
          is_active: data.is_active,
          role_ids: [],
        });
      });
    }
  }, [id]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleRoleToggle = (roleId) => {
    setForm(prev => ({
      ...prev,
      role_ids: prev.role_ids.includes(roleId)
        ? prev.role_ids.filter(id => id !== roleId)
        : [...prev.role_ids, roleId],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (isEditing) {
        await staffAPI.update(id, form);
      } else {
        await staffAPI.create(form);
      }
      navigate('/staff');
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '600px' }}>
      <h2>{isEditing ? '✏️ Modifier' : '➕ Nouveau'} soignant</h2>

      <ErrorAlert error={error} onClose={() => setError(null)} />

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <label>Prénom *</label>
          <input
            name="first_name"
            value={form.first_name}
            onChange={handleChange}
            required
            style={inputStyle}
          />
        </div>

        <div>
          <label>Nom *</label>
          <input
            name="last_name"
            value={form.last_name}
            onChange={handleChange}
            required
            style={inputStyle}
          />
        </div>

        <div>
          <label>Email *</label>
          <input
            name="email"
            type="email"
            value={form.email}
            onChange={handleChange}
            required
            style={inputStyle}
          />
        </div>

        <div>
          <label>Téléphone</label>
          <input
            name="phone"
            value={form.phone}
            onChange={handleChange}
            style={inputStyle}
          />
        </div>

        <div>
          <label>
            <input
              name="is_active"
              type="checkbox"
              checked={form.is_active}
              onChange={handleChange}
            />
            {' '}Actif
          </label>
        </div>

        <div>
          <label>Rôles</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
            {roles.map(role => (
              <button
                key={role.id}
                type="button"
                onClick={() => handleRoleToggle(role.id)}
                style={{
                  padding: '0.4rem 0.8rem',
                  borderRadius: '20px',
                  border: '1px solid #3182ce',
                  background: form.role_ids.includes(role.id) ? '#3182ce' : '#fff',
                  color: form.role_ids.includes(role.id) ? '#fff' : '#3182ce',
                  cursor: 'pointer',
                }}
              >
                {role.name}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <button
            type="submit"
            disabled={saving}
            style={{
              background: '#3182ce', color: '#fff',
              border: 'none', borderRadius: '6px',
              padding: '0.7rem 2rem', cursor: 'pointer',
              fontSize: '1rem',
            }}
          >
            {saving ? 'Enregistrement...' : (isEditing ? 'Modifier' : 'Créer')}
          </button>
          <button
            type="button"
            onClick={() => navigate('/staff')}
            style={{
              background: '#eee', border: 'none',
              borderRadius: '6px', padding: '0.7rem 2rem',
              cursor: 'pointer',
            }}
          >
            Annuler
          </button>
        </div>
      </form>
    </div>
  );
}

const inputStyle = {
  width: '100%', padding: '0.6rem',
  borderRadius: '6px', border: '1px solid #ddd',
  fontSize: '1rem', marginTop: '0.3rem',
};