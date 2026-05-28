import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Upload from './pages/Upload';
import ReviewQueue from './pages/ReviewQueue';
import Files from './pages/Files';
import FileDetail from './pages/FileDetail';
import Lookups from './pages/Lookups';

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/" element={<Navigate to="/upload" replace />} />
                      <Route path="/upload" element={<Upload />} />
                      <Route path="/review" element={<ReviewQueue />} />
                      <Route path="/files" element={<Files />} />
                      <Route path="/files/:id" element={<FileDetail />} />
                      <Route path="/lookups" element={<Lookups />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
