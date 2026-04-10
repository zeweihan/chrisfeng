import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import Upload from '@/pages/Upload';
import ReportViewer from '@/pages/ReportViewer';
import Admin from '@/pages/Admin';

const AuthGuard = ({ children }: { children: React.ReactNode }) => {
  const isAuth = localStorage.getItem('token');
  if (!isAuth) return <Navigate to="/login" />;
  return <Layout>{children}</Layout>;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<AuthGuard><Dashboard /></AuthGuard>} />
        <Route path="/upload" element={<AuthGuard><Upload /></AuthGuard>} />
        <Route path="/report/:id" element={<AuthGuard><ReportViewer /></AuthGuard>} />
        <Route path="/admin" element={<AuthGuard><Admin /></AuthGuard>} />
      </Routes>
    </Router>
  );
}

export default App;
