import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import StaffList from './pages/StaffList';
import StaffForm from './pages/StaffForm';
import ShiftList from './pages/ShiftList';
import AssignmentForm from './pages/AssignmentForm';
import AbsenceList from './pages/AbsenceList';
import PlanningCalendar from './pages/PlanningCalendar';   
import PlanningGenerator from './pages/PlanningGenerator';

export default function App() {
  return (
    <Router>
      <div style={{ minHeight: '100vh', background: '#f7fafc' }}>
        <Navbar />
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/staff" element={<StaffList />} />
            <Route path="/staff/new" element={<StaffForm />} />
            <Route path="/staff/:id/edit" element={<StaffForm />} />
            <Route path="/shifts" element={<ShiftList />} />
            <Route path="/assignments" element={<AssignmentForm />} />
            <Route path="/absences" element={<AbsenceList />} />
            <Route path="/planning" element={<PlanningCalendar />} />  
            <Route path="/generate" element={<PlanningGenerator />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}