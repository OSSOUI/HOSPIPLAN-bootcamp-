import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();

  const links = [
    { to: '/', label: ' Dashboard' },
    { to: '/staff', label: ' Soignants' },
    { to: '/shifts', label: ' Gardes' },
    { to: '/planning', label: ' Planning' }, 
    { to: '/assignments', label: ' Affectations' },
    { to: '/absences', label: ' Absences' },
    { to: '/generate', label: ' Générer' },
  ];

  return (
    <nav style={{
      background: '#1a365d',
      padding: '0 2rem',
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    }}>
      <h1 style={{ color: '#fff', margin: '0.8rem 0', fontSize: '1.3rem' }}>
         HospiPlan
      </h1>
      <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '2rem' }}>
        {links.map(link => (
          <Link
            key={link.to}
            to={link.to}
            style={{
              color: location.pathname === link.to ? '#ffd700' : '#ccc',
              textDecoration: 'none',
              padding: '0.8rem 1rem',
              borderBottom: location.pathname === link.to
                ? '3px solid #ffd700' : '3px solid transparent',
              fontWeight: location.pathname === link.to ? 'bold' : 'normal',
              transition: 'all 0.2s',
            }}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}