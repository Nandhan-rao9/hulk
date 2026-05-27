import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Upload from './pages/Upload';
import ReviewQueue from './pages/ReviewQueue';
import Files from './pages/Files';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/review" element={<ReviewQueue />} />
          <Route path="/files" element={<Files />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
