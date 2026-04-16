import { useState, useEffect } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { assignmentAPI } from '../api/client';
import ErrorAlert from '../components/ErrorAlert';

const localizer = momentLocalizer(moment);

export default function PlanningCalendar() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPlanning = async () => {
    try {
      setLoading(true);
      setError(null);

      const res = await assignmentAPI.list({ page_size: 200 });

      // Correction importante : gérer la pagination DRF
      const assignments = res.data.results || res.data;

      if (!Array.isArray(assignments)) {
        throw new Error("Format de données inattendu");
      }

      const formattedEvents = assignments.map((assignment) => ({
        id: assignment.id,
        title: `${assignment.staff_name} — ${assignment.shift_info?.shift_type || 'Garde'}`,
        start: new Date(assignment.shift_info.start),
        end: new Date(assignment.shift_info.end),
        resource: {
          staff: assignment.staff_name,
          unit: assignment.shift_info?.care_unit || '',
          type: assignment.shift_info?.shift_type || '',
        },
        color: getEventColor(assignment.shift_info?.shift_type || ''),
      }));

      setEvents(formattedEvents);
    } catch (err) {
      console.error("Erreur lors du chargement du planning :", err);
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const getEventColor = (type) => {
    if (type.includes('Nuit')) return '#8b5cf6';
    if (type.includes('Matin')) return '#10b981';
    if (type.includes('Après-midi')) return '#f59e0b';
    return '#3b82f6';
  };

  useEffect(() => {
    fetchPlanning();
  }, []);

  const eventStyleGetter = (event) => ({
    style: {
      backgroundColor: event.color,
      borderRadius: '6px',
      opacity: 0.95,
      color: 'white',
      border: 'none',
      padding: '4px 8px',
      fontSize: '0.85rem',
    },
  });

  return (
    <div style={{ padding: '20px' }}>
      <h2> Planning Général des Affectations</h2>
      <p style={{ color: '#555', marginBottom: '20px' }}>
        Visualisation des gardes et affectations sur un calendrier
      </p>

      <ErrorAlert error={error} onClose={() => setError(null)} />

      <div style={{ 
        height: '720px', 
        background: 'white', 
        padding: '15px', 
        borderRadius: '10px', 
        boxShadow: '0 4px 15px rgba(0,0,0,0.1)' 
      }}>
        {loading ? (
          <p style={{ textAlign: 'center', marginTop: '50px' }}>Chargement du planning...</p>
        ) : (
          <Calendar
            localizer={localizer}
            events={events}
            startAccessor="start"
            endAccessor="end"
            style={{ height: '100%' }}
            eventPropGetter={eventStyleGetter}
            views={['month', 'week', 'day']}
            defaultView="week"
            popup
            messages={{
              next: "Suivant",
              previous: "Précédent",
              today: "Aujourd'hui",
              month: "Mois",
              week: "Semaine",
              day: "Jour",
            }}
          />
        )}
      </div>

      <div style={{ marginTop: '15px', fontSize: '0.9rem', color: '#666' }}>
        <strong>Légende :</strong> 
        <span style={{ color: '#10b981' }}> ■ Matin </span> | 
        <span style={{ color: '#f59e0b' }}> ■ Après-midi </span> | 
        <span style={{ color: '#8b5cf6' }}> ■ Nuit </span>
      </div>
    </div>
  );
}