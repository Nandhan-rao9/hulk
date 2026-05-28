import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, User, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
      navigate('/upload');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-radial flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex h-16 w-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-600 items-center justify-center mb-4 shadow-lg">
            <span className="text-white font-bold text-2xl">B</span>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-brand-600 to-brand-500 bg-clip-text text-transparent">
            Breathe ESG
          </h1>
          <p className="text-muted-foreground mt-2">
            Emissions Data Management Platform
          </p>
        </div>

        {/* Login Card */}
        <Card className="shadow-xl border-2">
          <CardHeader>
            <CardTitle>Sign In</CardTitle>
            <CardDescription>Enter your credentials to access your account</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/50 flex items-start space-x-2">
                  <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-destructive">{error}</div>
                </div>
              )}

              <div>
                <label htmlFor="username" className="block text-sm font-medium mb-2">
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-input bg-background focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                    required
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-input bg-background focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
                    required
                  />
                </div>
              </div>

              <Button
                type="submit"
                size="lg"
                className="w-full"
                isLoading={loading}
              >
                Sign In
              </Button>
            </form>

            {/* Demo Credentials */}
            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-900 rounded-lg">
              <div className="text-sm text-blue-900 dark:text-blue-100 font-medium mb-3">
                Demo Credentials
              </div>
              <div className="text-xs text-blue-800 dark:text-blue-200 space-y-3">
                {/* Acme Manufacturing */}
                <div className="space-y-1">
                  <div className="font-semibold text-blue-900 dark:text-blue-100">Acme Manufacturing Ltd</div>
                  <div className="grid grid-cols-2 gap-2 ml-2">
                    <div>
                      <div className="font-medium">Admin:</div>
                      <div className="text-[10px] font-mono">acme_admin / admin123</div>
                    </div>
                    <div>
                      <div className="font-medium">Analyst:</div>
                      <div className="text-[10px] font-mono">acme_analyst / analyst123</div>
                    </div>
                  </div>
                </div>

                {/* TechCorp Industries */}
                <div className="space-y-1">
                  <div className="font-semibold text-blue-900 dark:text-blue-100">TechCorp Industries</div>
                  <div className="grid grid-cols-2 gap-2 ml-2">
                    <div>
                      <div className="font-medium">Admin:</div>
                      <div className="text-[10px] font-mono">tech_admin / admin123</div>
                    </div>
                    <div>
                      <div className="font-medium">Analyst:</div>
                      <div className="text-[10px] font-mono">tech_analyst / analyst123</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-muted-foreground">
          <p>Secure emissions data management for enterprises</p>
        </div>
      </div>
    </div>
  );
}
