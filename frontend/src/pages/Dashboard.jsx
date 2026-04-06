import { useState, useEffect } from 'react';
import { dashboardAPI } from '../api/client';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardAPI.get()
      .then(res => setData(res.data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Chargement...</p>;
  if (!data) return <p>Erreur de chargement du dashboard.</p>;

  const cards = [
    { label: 'Soignants actifs', value: data.total_active_staff, icon: '👤', color: '#3182ce' },
    { label: 'Services', value: data.total_services, icon: '🏥', color: '#38a169' },
    { label: "Absents aujourd'hui", value: data.absences_today, icon: '🏖️', color: '#d69e2e' },
    { label: "Gardes aujourd'hui", value: data.shifts_today, icon: '📅', color: '#805ad5' },
    { label: 'Gardes sous-couvertes', value: data.understaffed_shifts_today, icon: '⚠️', color: '#e53e3e' },
    { label: 'Certifications expirant (30j)', value: data.certifications_expiring_30d, icon: '📋', color: '#dd6b20' },
  ];

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Tableau de bord — {data.date}</h2>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
        gap: '1.5rem',
        marginTop: '1.5rem',
      }}>
        {cards.map((card, i) => (
          <div key={i} style={{
            background: '#fff',
            borderRadius: '12px',
            padding: '1.5rem',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            borderLeft: `4px solid ${card.color}`,
          }}>
            <div style={{ fontSize: '2rem' }}>{card.icon}</div>
            <div style={{
              fontSize: '2.2rem', fontWeight: 'bold',
              color: card.color, margin: '0.5rem 0',
            }}>
              {card.value}
            </div>
            <div style={{ color: '#666', fontSize: '0.9rem' }}>
              {card.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}